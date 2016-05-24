import cairo
import rsvg
import csv
import sys
from lxml import etree
import datetime, dateutil.parser, dateutil.tz
import os
import urllib2
import base64
from time import sleep

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
MAX_PNG_FILES_PER_FOLDER = 499
OPEN_STREET_MAP_QUERY = 'http://render.openstreetmap.org/cgi-bin/export?bbox=$MINLON,$MINLAT,$MAXLON,$MAXLAT&scale=6914&format=png'
LAT_DIFF = 0.00095
LON_DIFF = 0.00145

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
candidates = []
lastDate = dateutil.parser.parse(trackpointNodes[0].find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone) if len(trackpointNodes) > 0 else None

for trackpoint in trackpointNodes:
	d = dateutil.parser.parse(trackpoint.find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone)

	if d >= beginningDateSub60 and d < endingDatePlus60:
		intervalFound = True
		
		r = int((d - lastDate).total_seconds())
		i = 1
		date = lastDate
		while i < r:
                    #TODO
                    candidates.append([date, 0])
                    date = date + datetime.timedelta(0,1)
                    i = i + 1
                    
                lastDate = d

	if d >= endingDatePlus60:
		break

'''    
if intervalFound == False:
    print 'Files ', sys.argv[1], ' and ', sys.argv[2], ' do not match because of the dates'
    sys.exit()

i = 0
j = 0
selectedNodes = []
previousTrackPoint = None

        
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
previousTrackPoint = None
distanceAcc = 0.0
newNode = True
img64 = None
while i < len(rowsCsv) and len(selectedNodes) > 0:
	
	if i >= selectedNodes[0][1]:
		# The first node has been overtaken
		if j + 1 < len(selectedNodes):
			nextIndex = selectedNodes[j+1][1]
                
		if i >= nextIndex and j + 1 < len(selectedNodes):
			previousTrackPoint = selectedNodes[j][0]
			newNode = True
			j = j + 1
                    
	currentNode = selectedNodes[j][0]
	
	if newNode == True:
		lon = float(currentNode.find('.//ns:Position//ns:LongitudeDegrees', namespaces={'ns': namespace}).text)
		lat = float(currentNode.find('.//ns:Position//ns:LatitudeDegrees', namespaces={'ns': namespace}).text)
		#print "{0}, {1}".format(lon, lat)
		query = OPEN_STREET_MAP_QUERY.replace("$MINLAT", str(lat-LAT_DIFF))
		query = query.replace("$MAXLAT", str(lat+LAT_DIFF))
		query = query.replace("$MINLON", str(lon-LON_DIFF))
		query = query.replace("$MAXLON", str(lon+LON_DIFF))
		print query
		img = urllib2.urlopen(query).read()
		img64 = base64.b64encode(img)
		sleep(0.5)
		#print "img64:", img64
            
	dateNode = dateutil.parser.parse(currentNode.find('.//ns:Time', namespaces={'ns': namespace}).text)
	dateNode = dateNode.astimezone(to_zone)
	heartRate = currentNode.find('.//ns:HeartRateBpm//ns:Value', namespaces={'ns': namespace}).text
	
	speed = 0
	distance = 0.0
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
	
	heightNode = currentNode.find('.//ns:AltitudeMeters', namespaces={'ns': namespace})
	heightFloat = float(heightNode.text)
	height = "{:.1f}".format(heightFloat)
	
	if newNode == True:
		distanceAcc = distanceAcc + distance
            
	distanceStr = "{:.1f}".format(distanceAcc)
	
	print i, ' ', dateNode, ' ', heartRate, ' ', speed, ' ', cadence, ' ', height, ' ', distanceStr
	
	svgDataMod = svgData.replace("SPEED", str(speed))
	svgDataMod = svgDataMod.replace("CADENCE", cadence)
	svgDataMod = svgDataMod.replace("HEART", heartRate)
	svgDataMod = svgDataMod.replace("HEIGHT", height)
	svgDataMod = svgDataMod.replace("DISTANCE", distanceStr)
	svgDataMod = svgDataMod.replace("IMAGEMAP64", img64)

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

	h = h + 1
	i = i + 1
	newNode = False
		
'''
# Function to calculate the cost of an specified array when comparing it against the optimum one

def calculateCost(candidates, base, begin):
    
    cost = 0.0
    r = 0
    
    i = 0
    j = begin
    n = len(base)
    while i < n:
        print ''

    return cost
    













    
    
    
    


