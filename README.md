# overlay4shim

This project is intended to help people who want to put a layer with ANT data over the video recorded by Shimano Camera. 
It is intended for those who use linux and therefore, cannot use the software provided by Shimano.

The python script generates a sequence of png images to be used with OpenShot, that video editor will put it all together video and
sequence achiving thus a video with overlay.

I hope it can be helpful.

Python requirements:
- Version >= 2.7
- Modules gir1.2-rsvg-2.0 python-rsvg for svg processing
- Module python-lxml for XML processing
- Module python-dateutil for date processing
- pip install pudb for debugging purposes (it is optional)
