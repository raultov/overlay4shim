import cairo
import rsvg
import csv
import sys
from lxml import etree
import datetime, dateutil.parser, dateutil.tz

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

if len(sys.argv) < 4:
    print 'usage: ',sys.argv[0], ' <file.tcx> <file.csv> <template.svg>'
    sys.exit()   
    
    
# Read csv file
with open(sys.argv[2], 'rb') as f:
    reader = csv.reader(f)
    rowsCsv = list(reader)    
    
to_zone = dateutil.tz.tzlocal()    
beginningDate = datetime.datetime(int(rowsCsv[1][YEAR]), int(rowsCsv[1][MONTH]), int(rowsCsv[1][DAY]), int(rowsCsv[1][HOUR]), int(rowsCsv[1][MINUTE]), int(rowsCsv[1][SECOND]), tzinfo=to_zone)
    
# Read tcx file    
doc= etree.parse(sys.argv[1])
namespace = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'

#from_zone = dateutil.tz.tzutc()


i = 0
dateFound = False
for trackpoint in doc.xpath('//ns:Trackpoint', namespaces={'ns': namespace}):
	# Iterate over attributes of datafield
	d = dateutil.parser.parse(trackpoint.find('.//ns:Time', namespaces={'ns': namespace}).text)
	#d = d.replace(tzinfo=from_zone)
	d = d.astimezone(to_zone)

	if d > beginningDate:
		print beginningDate.strftime('%m/%d/%Y %H:%M:%S')
		print d.strftime('%m/%d/%Y %H:%M:%S')
		print i
		dateFound = True
		break
	
	i = i + 1
	
if dateFound == False:
	print 'Files ', sys.argv[1], ' and ', sys.argv[2], ' do not match'
	sys.exit()

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
    
    


