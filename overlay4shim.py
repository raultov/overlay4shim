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

# Other constants
MAX_PNG_FILES_PER_FOLDER = 499
OPEN_STREET_MAP_QUERY = 'http://render.openstreetmap.org/cgi-bin/export?bbox=$MINLON,$MINLAT,$MAXLON,$MAXLAT&scale=6914&format=png'
LAT_DIFF = 0.00095
LON_DIFF = 0.00145

def main():
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

	beginningDateSub60 = beginningDate - datetime.timedelta(seconds=20)
	endingDatePlus60 = endingDate + datetime.timedelta(seconds=20)

	# Read tcx file    
	doc= etree.parse(sys.argv[1])
	namespace = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'

	i = 0
	intervalFound = False
	trackpointNodes = doc.xpath('//ns:Trackpoint', namespaces={'ns': namespace})
	candidates = []

	while i < len(trackpointNodes):
		d = dateutil.parser.parse(trackpointNodes[i].find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone)

		if d >= beginningDateSub60 and d < endingDatePlus60:
			intervalFound = True

			nextDate = dateutil.parser.parse(trackpointNodes[i+1].find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone) if i + 1 < len(trackpointNodes) else d

			r = int((nextDate - d).total_seconds())

			heartRate = trackpointNodes[i].find('.//ns:HeartRateBpm//ns:Value', namespaces={'ns': namespace}).text
			candidates.append([trackpointNodes[i], int(heartRate)])

			j = 1
			while j < r:
				#d = d + datetime.timedelta(0,1)
				candidates.append([None, 0])
				j = j + 1

		if d >= endingDatePlus60:
			break

		i = i + 1

	if intervalFound == False:
		print 'Files ', sys.argv[1], ' and ', sys.argv[2], ' do not match because of the dates'
		sys.exit()

	i = 0
	minCost = float("inf")
	minCostIndex = 0
	while i < len(candidates) and i < len(candidates) - len(rowsCsv):

		cost = calculateCost(candidates, rowsCsv, i)
		if cost < minCost:
			minCost = cost
			minCostIndex = i

		i = i + 1

	selectedNodes = []
	firstSelectedNode = None
	i = minCostIndex
	j = 0
	while j < len(rowsCsv):
		selectedNodes.append(candidates[i][0])
		if firstSelectedNode == None and candidates[i][0] != None:
			firstSelectedNode = candidates[i][0]

		i = i + 1
		j = j + 1


	# PNGs creation
	with open(sys.argv[3], 'r') as svgFile:
		svgData=svgFile.read().replace('\n', '')

	if firstSelectedNode != None:
		currentValidNode = firstSelectedNode
		previousValidNode = None
		baseFolder = 'output'
		distanceAcc = 0.0
		newNode = True
		img64 = None
		h = 0
		k = 1
		i = 0

		while i < len(selectedNodes):

			if selectedNodes[i] != None:
				previousValidNode = currentValidNode
				currentValidNode = selectedNodes[i]
				newNode = True

			if newNode == True:
				# Download image when there a new valid node or at the beginning still there is no previous valid Node
				lon = float(currentValidNode.find('.//ns:Position//ns:LongitudeDegrees', namespaces={'ns': namespace}).text)
				lat = float(currentValidNode.find('.//ns:Position//ns:LatitudeDegrees', namespaces={'ns': namespace}).text)
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

			dateNode = dateutil.parser.parse(currentValidNode.find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone)
			heartRate = currentValidNode.find('.//ns:HeartRateBpm//ns:Value', namespaces={'ns': namespace}).text

			speed = 0
			distance = 0.0
			if previousValidNode != None:
				currentDistance = float(currentValidNode.find('.//ns:DistanceMeters', namespaces={'ns': namespace}).text)
				previousDistance = float(previousValidNode.find('.//ns:DistanceMeters', namespaces={'ns': namespace}).text)
				distance = currentDistance - previousDistance

				currentTime = dateutil.parser.parse(currentValidNode.find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone)
				previousTime = dateutil.parser.parse(previousValidNode.find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone)
				timePassed = float((currentTime - previousTime).total_seconds())
				speed = int((distance / timePassed) * 3.6) if timePassed != 0.0 else 0.0

			cadenceNode = currentValidNode.find('.//ns:Cadence', namespaces={'ns': namespace})
			cadence = cadenceNode.text if cadenceNode != None else '0'

			heightNode = currentValidNode.find('.//ns:AltitudeMeters', namespaces={'ns': namespace})
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

			img.write_to_png(currentFolder + "/myfile_%d.png" % h)          

			newNode = False
			h = h + 1
			i = i + 1

# Function to calculate the cost of an specified array when comparing it against the optimum one
def calculateCost(candidates, base, begin):

	cost = 0.0

	i = 0
	j = begin
	computedRegisters = 0
	
	while i < len(base) and j < len(candidates):

		baseHeartRate = int(base[i][HEART_RATE])

		if baseHeartRate != 0 and candidates[j][1] != 0:
			diff = abs(baseHeartRate - candidates[j][1])
			cost = cost + diff
			computedRegisters = computedRegisters + 1

		i = i + 1
		j = j + 1

	return cost / computedRegisters

if __name__ == '__main__':
	main()













    
    
    
    


