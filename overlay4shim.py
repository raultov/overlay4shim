import cairo
import rsvg
import csv
import sys

if len(sys.argv) < 3:
    print 'usage: ',sys.argv[0], ' <file.csv> <template.svg>'
    sys.exit()

with open(sys.argv[1], 'rb') as f:
    reader = csv.reader(f)
    rows = list(reader)

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

with open(sys.argv[2], 'r') as svgFile:
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
    
    
    


