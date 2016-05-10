import cairo
import rsvg
import csv
import sys
from lxml import etree
import datetime, dateutil.parser, dateutil.tz

#from pudb import set_trace; set_trace()

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


beginningDateSub60 = beginningDate - datetime.timedelta(seconds=60)
endingDatePlus60 = endingDate + datetime.timedelta(seconds=60)
    
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
        #print beginningDateSub60.strftime('%m/%d/%Y %H:%M:%S')
        #print d.strftime('%m/%d/%Y %H:%M:%S')
        #print i
        intervalFound = True
        candidateNodes.append(trackpoint)

    if d >= endingDatePlus60:
        break

    i = i + 1
    
if intervalFound == False:
    print 'Files ', sys.argv[1], ' and ', sys.argv[2], ' do not match because of the dates'
    sys.exit()

#sequenceFound = False
#sequenceStartIndex = 0
#previousCandidate = candidateNodes[0]
#followingSequence = False
i = 0
j = 0
firstNodeFound = False
selectedNodes = []

while i < len(candidateNodes):
	candidate = candidateNodes[i]

	dateCandidate = dateutil.parser.parse(candidate.find('.//ns:Time', namespaces={'ns': namespace}).text)
	dateCandidate = dateCandidate.astimezone(to_zone)

	heartRateCandidate = int(candidate.find('.//ns:HeartRateBpm//ns:Value', namespaces={'ns': namespace}).text)

	if firstNodeFound == False:
		j = 0
		while j < MAX_RANGE_FIRST_SCANNING and j < len(rowsCsv):
			if int(rowsCsv[j][HEART_RATE]) == heartRateCandidate:
				firstNodeFound = True
				break
			j = j + 1
	else:
		datePreviousCandidate = dateutil.parser.parse(candidateNodes[i-1].find('.//ns:Time', namespaces={'ns': namespace}).text)
		datePreviousCandidate = datePreviousCandidate.astimezone(to_zone)
		j = j + int((dateCandidate - datePreviousCandidate).total_seconds())

		if j >= len(rowsCsv):
			break
			
		# Append current candidate to the list of selected Nodes
		selectedNodes.append(candidate)			

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

		if heartRateCandidate == heartRateRow or heartRateCandidate == heartRateRow - 1 or heartRateCandidate == heartRateRow + 1:
			j = j
		elif heartRateCandidate == heartRatePreviousRow or heartRateCandidate == heartRatePreviousRow - 1 or heartRateCandidate == heartRatePreviousRow + 1:
			j = j - 1
		elif heartRateCandidate == heartRateNextRow or heartRateCandidate == heartRateNextRow -1 or heartRateCandidate == heartRateNextRow + 1:
			j = j + 1
		else:
			firstNodeFound = False
			# Clear list of selected Nodes
			selectedNodes = []

	i = i + 1

print j

i = 0
while i < len(selectedNodes):
	selectedNode = selectedNodes[i]
	dateNode = dateutil.parser.parse(selectedNode.find('.//ns:Time', namespaces={'ns': namespace}).text)
	dateNode = dateNode.astimezone(to_zone)
	
	print i, ' ', dateNode
	
	i = i + 1
    
'''
    if followingSequence == True:
        datePreviousCandidate = dateutil.parser.parse(candidateNodes[i-1].find('.//ns:Time', namespaces={'ns': namespace}).text)
        datePreviousCandidate = datePreviousCandidate.astimezone(to_zone)
        j = j + int((dateCandidate - datePreviousCandidate).total_seconds())
        sequenceFound = True
    else:
        j = 0
        sequenceFound = False
        
    followingSequence = False

    while j < len(rowsCsv):
        row = rowsCsv[j]
        #dateRow = datetime.datetime(int(row[YEAR]), int(row[MONTH]), int(row[DAY]), int(row[HOUR]), int(row[MINUTE]), int(row[SECOND]), tzinfo=to_zone)
        if j - 1 >= 0:
            heartRatePreviousRow = int(rowsCsv[j-1][HEART_RATE])
        else:
            heartRatePreviousRow = int(row[HEART_RATE])
            
        heartRateRow = int(row[HEART_RATE])
        
        if j + 1 <len(rowsCsv):
            heartRateNextRow = int(rowsCsv[j+1][HEART_RATE])
        else:
            heartRateNextRow = int(row[HEART_RATE])
        
        if heartRateRow == heartRateCandidate or heartRateRow == heartRatePreviousRow or heartRateRow == heartRateNextRow:
            followingSequence = True
            break
    
        
        j = j + 1
        
    i = i + 1
        
print sequenceFound      
'''
    


#        for attrib in df.attrib:
#       print '@' + attrib + '=' + df.attrib[attrib]

        # subfield is a child of datafield, and iterate
    #subfields = df.getchildren()
    #for subfield in subfields:
    #   print 'Value=' + subfield.text

    
'''    

with open(sys.argv[3], 'r') as svgFile:
    svgData=svgFile.read().replace('\n', '')

i = 1
lastSpeed = '0'
lastCadence = '0'
lastHeartRate = '0'

while i < len(rows):
    row = rows[i]
    
    if row[SPEED] == '' or row[SPEED] == '0':
        speed = lastSpeed
    else:
        speed = row[SPEED]
    lastSpeed = speed
    
    if row[CADENCE] == '' or row[CADENCE] == '0':
        cadence = lastCadence
    else:
        cadence = row[CADENCE]
    lastCadence = cadence
    
    if row[HEART_RATE] == '' or row[HEART_RATE] == '0':
        heartRate = lastHeartRate
    else:
        heartRate = row[HEART_RATE]
    lastHeartRate = heartRate
    
    svgDataMod = svgData.replace("SPEED", speed)
    svgDataMod = svgDataMod.replace("CADENCE", cadence)
    svgDataMod = svgDataMod.replace("HEART", heartRate)
    
    img = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1280,720)
    ctx = cairo.Context(img)
    
    handle = rsvg.Handle(None, svgDataMod)
    handle.render_cairo(ctx)

    img.write_to_png("myfile%d.png" % i)  
    print "row %d: %s" % (i,row)
    i = i + 1
''' 
    
    


