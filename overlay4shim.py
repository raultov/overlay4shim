
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

# Other constants
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

# Read tcx file    
doc= etree.parse(sys.argv[1])
namespace = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'

i = 0
intervalFound = False
trackpointNodes = doc.xpath('//ns:Trackpoint', namespaces={'ns': namespace})
selectedNodes = []

for trackpoint in trackpointNodes:
	d = dateutil.parser.parse(trackpoint.find('.//ns:Time', namespaces={'ns': namespace}).text)
	d = d.astimezone(to_zone)

	if d >= beginningDate and d <= endingDate:
		intervalFound = True
		selectedNodes.append(trackpoint)

	if d > endingDate:
		break

	i = i + 1
    
if intervalFound == False:
    print 'Files ', sys.argv[1], ' and ', sys.argv[2], ' do not match because of the dates'
    sys.exit()
    
# PNGs creation
with open(sys.argv[3], 'r') as svgFile:
    svgData=svgFile.read().replace('\n', '')

i = 0
j = 0
k = 1
h = 0
m = 0
total = int((endingDate - beginningDate).total_seconds())
baseFolder = 'output'
currentNode = selectedNodes[0] if len(selectedNodes) > 0 else None
currentDate = beginningDate
nextDate = 	dateutil.parser.parse(currentNode.find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone) if currentNode != None else None
previousTrackPoint = None
distanceAcc = 0.0
newNode = True
img64 = None
while i < total and len(selectedNodes) > 0:

	lengthInterval = int((nextDate - currentDate).total_seconds())
	
	if m > lengthInterval:
		# Move to the next interval
		m = 0
		j = j + 1
		currentDate = nextDate
		
		if j < len(selectedNodes):
			previousTrackPoint = selectedNodes[j-1]
			nextDate = dateutil.parser.parse(selectedNodes[j].find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone)
			newNode = True
		else:
			nextDate = endingDate
			j = j - 1
                    
	currentNode = selectedNodes[j]
	
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
	m = m + 1
	newNode = False
