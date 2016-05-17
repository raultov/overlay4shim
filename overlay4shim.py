import cairo
import rsvg
import csv
import sys
from lxml import etree
import datetime, dateutil.parser, dateutil.tz
import os

from pudb import set_trace; set_trace()

# CSV constants
YEAR = 0
MONTH = 1
DAY = 2
HOUR = 3
MINUTE = 4
SECOND = 5
SPEED = 6
CADENCE = 7
POWER = 8
HEART_RATE = 9

# Ohter constants
MAX_RANGE_FIRST_SCANNING = 10
MIN_MATCHING_RATIO = 0.3
MAX_PNG_FILES_PER_FOLDER = 499

if len(sys.argv) < 4:
    print 'usage: ',sys.argv[0], ' <file.tcx> <file.csv> <template.svg>'
    sys.exit()   
    
    
# Read csv file
with open(sys.argv[2], 'rb') as f:
    reader = csv.reader(f)
    rowsCsv = list(reader)
    
# Erase CSV header
rowsCsv.pop(0)
n = len(rowsCsv) - 1
    
to_zone = dateutil.tz.tzlocal()    
beginningDate = datetime.datetime(int(rowsCsv[0][YEAR]), int(rowsCsv[0][MONTH]), int(rowsCsv[0][DAY]), int(rowsCsv[0][HOUR]), int(rowsCsv[0][MINUTE]), int(rowsCsv[0][SECOND]), tzinfo=to_zone)
endingDate = datetime.datetime(int(rowsCsv[n][YEAR]), int(rowsCsv[n][MONTH]), int(rowsCsv[n][DAY]), int(rowsCsv[n][HOUR]), int(rowsCsv[n][MINUTE]), int(rowsCsv[n][SECOND]), tzinfo=to_zone)

beginningDateSub60 = beginningDate - datetime.timedelta(seconds=5)
endingDatePlus60 = endingDate + datetime.timedelta(seconds=5)
    
# Read tcx file    
doc= etree.parse(sys.argv[1])
namespace = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'

i = 0
intervalFound = False
trackpointNodes = doc.xpath('//ns:Trackpoint', namespaces={'ns': namespace})
candidateNodes = []

for trackpoint in trackpointNodes:
	d = dateutil.parser.parse(trackpoint.find('.//ns:Time', namespaces={'ns': namespace}).text)
	d = d.astimezone(to_zone)

	if d >= beginningDateSub60 and d < endingDatePlus60:
		intervalFound = True
		candidateNodes.append(trackpoint)

	if d >= endingDatePlus60:
		break

	i = i + 1
    
if intervalFound == False:
    print 'Files ', sys.argv[1], ' and ', sys.argv[2], ' do not match because of the dates'
    sys.exit()

i = 0
j = 0
firstNodeFound = False
selectedNodes = []
previousTrackPoint = None

while i < len(candidateNodes):
	candidate = candidateNodes[i]

	dateCandidate = dateutil.parser.parse(candidate.find('.//ns:Time', namespaces={'ns': namespace}).text)
	dateCandidate = dateCandidate.astimezone(to_zone)

	heartRateCandidate = int(candidate.find('.//ns:HeartRateBpm//ns:Value', namespaces={'ns': namespace}).text)

	if firstNodeFound == False:
		j = 0
		#while j < MAX_RANGE_FIRST_SCANNING and j < len(rowsCsv):
                while j < len(rowsCsv):                    
                    
                        rowsCsvDate = datetime.datetime(int(rowsCsv[j][YEAR]), int(rowsCsv[j][MONTH]), int(rowsCsv[j][DAY]), int(rowsCsv[j][HOUR]), int(rowsCsv[j][MINUTE]), int(rowsCsv[j][SECOND]), tzinfo=to_zone)
                        secondsDiff = abs((rowsCsvDate - dateCandidate).total_seconds())
                        diff = 3
                        if secondsDiff <=1:
                            diff = 5
                        elif secondsDiff <= 2:
                            diff = 4
                        
			if abs(int(rowsCsv[j][HEART_RATE]) - heartRateCandidate) <= diff:
				firstNodeFound = True
				# Append current candidate to the list of selected Nodes
				selectedNodes.append([candidate, j])	
				
				if i - 1 >= 0:
                                    previousTrackPoint = candidateNodes[i-1]
				
				break

			j = j + 1
	else:
		datePreviousCandidate = dateutil.parser.parse(candidateNodes[i-1].find('.//ns:Time', namespaces={'ns': namespace}).text)
		datePreviousCandidate = datePreviousCandidate.astimezone(to_zone)
		j = j + int((dateCandidate - datePreviousCandidate).total_seconds())

		if j >= len(rowsCsv):
			break
			
		# Append current candidate to the list of selected Nodes
		selectedNodes.append([candidate, j])			

		#print j, ' ', dateCandidate, ' ', rowsCsv[j][HEART_RATE]

		if j - 1 >= 0:
			heartRatePreviousRow = int(rowsCsv[j-1][HEART_RATE])
		else:
			heartRatePreviousRow = int(row[HEART_RATE])

		heartRateRow = int(rowsCsv[j][HEART_RATE])

		if j + 1 <len(rowsCsv):
			heartRateNextRow = int(rowsCsv[j+1][HEART_RATE])
		else:
			heartRateNextRow = int(row[HEART_RATE])
			
                rowsCsvDate = datetime.datetime(int(rowsCsv[j][YEAR]), int(rowsCsv[j][MONTH]), int(rowsCsv[j][DAY]), int(rowsCsv[j][HOUR]), int(rowsCsv[j][MINUTE]), int(rowsCsv[j][SECOND]), tzinfo=to_zone)			
                secondsDiff = abs((rowsCsvDate - dateCandidate).total_seconds())
                diff = 3
                if secondsDiff <=1:
                    diff = 5
                elif secondsDiff <= 2:
                    diff = 4			

		if abs(heartRateCandidate - heartRateRow) <= diff:
			j = j
		elif abs(heartRateCandidate -  heartRatePreviousRow) <= diff:
			j = j - 1
		elif abs(heartRateCandidate - heartRateNextRow) <= diff:
			j = j + 1
		else:
                        ratio = float(j) / len(rowsCsv)
                        
                        if ratio < MIN_MATCHING_RATIO and heartRateRow != 0 and heartRateNextRow != 0 and heartRatePreviousRow != 0:
                        #if heartRateRow != 0 and heartRateNextRow != 0 and heartRatePreviousRow != 0:
                            firstNodeFound = False
                            # Clear list of selected Nodes
                            selectedNodes = []

	i = i + 1
        
# PNGs creation
with open(sys.argv[3], 'r') as svgFile:
    svgData=svgFile.read().replace('\n', '')

i = 0
j = 0
k = 1
h = 0
baseFolder = 'output'
nextIndex = selectedNodes[0][1] if len(selectedNodes) > 0 else 0
currentNode = selectedNodes[0][0] if len(selectedNodes) > 0 else None
while i < len(rowsCsv) and len(selectedNodes) > 0:
	
	if i >= selectedNodes[0][1]:
		# The first node has been overtaken
		if j + 1 < len(selectedNodes):
					nextIndex = selectedNodes[j+1][1]
                
		if i >= nextIndex and j + 1 < len(selectedNodes):
			previousTrackPoint = selectedNodes[j][0]
			j = j + 1
                    
	currentNode = selectedNodes[j][0]
		
	dateNode = dateutil.parser.parse(currentNode.find('.//ns:Time', namespaces={'ns': namespace}).text)
	dateNode = dateNode.astimezone(to_zone)
	heartRate = currentNode.find('.//ns:HeartRateBpm//ns:Value', namespaces={'ns': namespace}).text
	
	speed = 0
	if previousTrackPoint != None:
		currentDistance = float(currentNode.find('.//ns:DistanceMeters', namespaces={'ns': namespace}).text)
		previousDistance = float(previousTrackPoint.find('.//ns:DistanceMeters', namespaces={'ns': namespace}).text)
		distance = currentDistance - previousDistance

		currentTime = dateutil.parser.parse(currentNode.find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone)
		previousTime = dateutil.parser.parse(previousTrackPoint.find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone)
		timePassed = float((currentTime - previousTime).total_seconds())

		speed = int((distance / timePassed) * 3.6)
            
	cadenceNode = currentNode.find('.//ns:Cadence', namespaces={'ns': namespace})
	cadence = cadenceNode.text if cadenceNode != None else '0'
	
	print i, ' ', dateNode, ' ', heartRate, ' ', speed, ' ', cadence
	
	svgDataMod = svgData.replace("SPEED", str(speed))
	svgDataMod = svgDataMod.replace("CADENCE", cadence)
	svgDataMod = svgDataMod.replace("HEART", heartRate)

	img = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1280,720)
	ctx = cairo.Context(img)

	handle = rsvg.Handle(None, svgDataMod)
	handle.render_cairo(ctx)
		
	if h > MAX_PNG_FILES_PER_FOLDER:
		k = k + 1
		h = 0
		print 'Moving to new folder'
		
	currentFolder = baseFolder + str(k)
	if not os.path.exists(currentFolder):
		os.makedirs(currentFolder)		

	img.write_to_png(currentFolder + "/myfile%d.png" % h)          

	if h <= MAX_PNG_FILES_PER_FOLDER:
		h = h + 1

	i = i + 1


    
    


