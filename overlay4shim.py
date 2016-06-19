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
import signal
import argparse

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

# Other constants
MAX_PNG_FILES_PER_FOLDER = 499
OPEN_STREET_MAP_QUERY = 'http://render.openstreetmap.org/cgi-bin/export?bbox=$MINLON,$MINLAT,$MAXLON,$MAXLAT&scale=6914&format=png'
LAT_DIFF = 0.00095
LON_DIFF = 0.00145
VIDEO_OUTPUT_WIDTH = 1280
VIDEO_OUTPUT_HEIGH = 720

def main():

	parser = argparse.ArgumentParser()
	parser.add_argument("-v", "--version", action="version", version="%(prog)s 2.0")
	parser.add_argument("-c", "--csv", help="CSV file to search STARTING and ENDING times")
	parser.add_argument("-s", "--start", help="Video start time yyyy-mm-dd-HH:MM:SS")
	parser.add_argument("-e", "--end", help="Video end time yyyy-mm-dd-HH:MM:SS")
	parser.add_argument("tcx_file", help="TCX file")
	parser.add_argument("svg_file", help="SVG template")
	args = parser.parse_args()

	if (args.start != None and args.end == None) or (args.start == None and args.end != None):
		print "Must specify start and end dates"
		sys.exit()
		
	if (args.start and args.csv) or (args.start == None and args.csv == None):
		print "Must specify either CSV file or starting and ending times"
		sys.exit()

	# Ctrl+c handler
	signal.signal(signal.SIGINT, signal_handler)
	
	n = 0
	beginningDateLimit = None
	endingDateLimit = None
	# Dates to local time
	to_zone = dateutil.tz.tzlocal()
	rowsCsv = None
	
	if args.csv:
		# Read csv file
		with open(sys.argv[2], 'rb') as f:
			reader = csv.reader(f)
			rowsCsv = list(reader)
			
		# Erase CSV header
		rowsCsv.pop(0)
		n = len(rowsCsv)
		m = n - 1

		beginningDate = datetime.datetime(int(rowsCsv[0][YEAR]), int(rowsCsv[0][MONTH]), int(rowsCsv[0][DAY]), int(rowsCsv[0][HOUR]), int(rowsCsv[0][MINUTE]), int(rowsCsv[0][SECOND]), tzinfo=to_zone)
		endingDate = datetime.datetime(int(rowsCsv[m][YEAR]), int(rowsCsv[m][MONTH]), int(rowsCsv[m][DAY]), int(rowsCsv[m][HOUR]), int(rowsCsv[m][MINUTE]), int(rowsCsv[m][SECOND]), tzinfo=to_zone)

		beginningDateLimit = beginningDate - datetime.timedelta(seconds=60)
		endingDateLimit = endingDate + datetime.timedelta(seconds=60)
	else:
		try:
			beginningDateLimit = datetime.datetime.strptime(args.start, '%Y-%m-%d-%H:%M:%S').replace(tzinfo=to_zone)
			endingDateLimit = datetime.datetime.strptime(args.end, '%Y-%m-%d-%H:%M:%S').replace(tzinfo=to_zone)
			n = int((endingDateLimit - beginningDateLimit).total_seconds())
			
			if (n <= 0):
				print "Ending time must be newer than beginning time"
				sys.exit()
		except ValueError:
			print "Date format must be yyyy-mm-dd-HH:MM:SS"
			sys.exit()
			
	# Read tcx file    
	doc= etree.parse(args.tcx_file)
	namespace = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'

	i = 0
	intervalFound = False
	trackpointNodes = doc.xpath('//ns:Trackpoint', namespaces={'ns': namespace})
	candidates = []

	while i < len(trackpointNodes):
		# Loop over all trackpoints to select a subset delimited by beginningDate and endingDate
		# Put a trackpoint or None object for every second into the candidates array
		d = dateutil.parser.parse(trackpointNodes[i].find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone)

		if d >= beginningDateLimit and d < endingDateLimit:
			intervalFound = True

			nextDate = dateutil.parser.parse(trackpointNodes[i+1].find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone) if i + 1 < len(trackpointNodes) else d

			r = int((nextDate - d).total_seconds())

			heartRate = trackpointNodes[i].find('.//ns:HeartRateBpm//ns:Value', namespaces={'ns': namespace}).text
			candidates.append([trackpointNodes[i], int(heartRate)])

			j = 1
			while j < r:
				# Put None where there is no tcx trackpoint in order to fill empty spaces into the candidates array
				candidates.append([None, 0])
				j = j + 1

		if d >= endingDateLimit:
			break

		i = i + 1

	if intervalFound == False:
		print 'Could not find video interval of time in tcx data'
		sys.exit()
		
	selectedNodes = []
	firstSelectedNode = None

	if args.csv:
		i = 0
		minCost = float("inf")
		minCostIndex = 0
		while i < len(candidates) and i < len(candidates) - n:
			# Find the index where begins the set of candidates with less cost
			cost = calculateCost(candidates, rowsCsv, i)
			if cost < minCost:
				minCost = cost
				minCostIndex = i

			i = i + 1

		i = minCostIndex
		j = 0
		while j < n:
			# Starting from the index calculated above, put the set with minimum cost into a new array called selectedNodes
			selectedNodes.append(candidates[i][0])
			if firstSelectedNode == None and candidates[i][0] != None:
				# Store the first node in a variable called firstSelectedNode
				firstSelectedNode = candidates[i][0]

			i = i + 1
			j = j + 1
	else:
		i = 0
		while i < n:
			selectedNodes.append(candidates[i][0])
			if firstSelectedNode == None and candidates[i][0] != None:
				# Store the first node in a variable called firstSelectedNode
				firstSelectedNode = candidates[i][0]
			
			i = i + 1

	# PNGs creation
	# Read svg template
	with open(args.svg_file, 'r') as svgFile:
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
				# Download image when there is a new valid node or at the beginning there is still no previous valid Node
				if currentValidNode.find('.//ns:Position//ns:LongitudeDegrees', namespaces={'ns': namespace}) != None and currentValidNode.find('.//ns:Position//ns:LatitudeDegrees', namespaces={'ns': namespace}) != None:
					lon = float(currentValidNode.find('.//ns:Position//ns:LongitudeDegrees', namespaces={'ns': namespace}).text)
					lat = float(currentValidNode.find('.//ns:Position//ns:LatitudeDegrees', namespaces={'ns': namespace}).text)
					query = OPEN_STREET_MAP_QUERY.replace("$MINLAT", str(lat-LAT_DIFF))
					query = query.replace("$MAXLAT", str(lat+LAT_DIFF))
					query = query.replace("$MINLON", str(lon-LON_DIFF))
					query = query.replace("$MAXLON", str(lon+LON_DIFF))
					print query
					img = urllib2.urlopen(query).read()
					img64 = base64.b64encode(img)
					# Sleep 500 ms to avoid openstreetmap server gets overloaded
					sleep(0.5)

			dateNode = dateutil.parser.parse(currentValidNode.find('.//ns:Time', namespaces={'ns': namespace}).text).astimezone(to_zone)
			heartRate = currentValidNode.find('.//ns:HeartRateBpm//ns:Value', namespaces={'ns': namespace}).text

			speed = 0
			distance = 0.0
			if previousValidNode != None:
				# Taking the previous Node and the current one, calculate speed and distance 
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
				# Calculate total distance
				distanceAcc = distanceAcc + distance

			distanceStr = "{:.1f}".format(distanceAcc)

			print i, ' ', dateNode, ' ', heartRate, ' ', speed, ' ', cadence, ' ', height, ' ', distanceStr

			# Set data values in the template
			svgDataMod = svgData.replace("SPEED", str(speed))
			svgDataMod = svgDataMod.replace("CADENCE", cadence)
			svgDataMod = svgDataMod.replace("HEART", heartRate)
			svgDataMod = svgDataMod.replace("HEIGHT", height)
			svgDataMod = svgDataMod.replace("DISTANCE", distanceStr)
			svgDataMod = svgDataMod.replace("IMAGEMAP64", img64)

			img = cairo.ImageSurface(cairo.FORMAT_ARGB32, VIDEO_OUTPUT_WIDTH, VIDEO_OUTPUT_HEIGH)
			ctx = cairo.Context(img)

			handle = rsvg.Handle(None, svgDataMod)
			handle.render_cairo(ctx)

			# Openshot does not work well when number of images is greater than 500 therefore, a new folder is created each time that 
			# the number of images overpasses 499
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

# Function to calculate the cost of an specified array when comparing it with the array base coming from a CSV data
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

def signal_handler(signal, frame):
	print('You pressed Ctrl+C!')
	sys.exit(0)

if __name__ == '__main__':
	main()













    
    
    
    


