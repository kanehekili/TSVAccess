#! /usr/bin/env python3
import os,cv2
best=(-1,-1) #indx,w*h
for i in range(8,-1,-1):
	rval=None
	vc = cv2.VideoCapture(i,cv2.CAP_V4L2)
	if vc.isOpened():
		rval, frame = vc.read()
	if rval:
		height, width, bytesPerComponent = frame.shape #numpyArray
		print("Camera ",i, "ok:",width,">",height)
		quality=width*height
		if best[1]<quality:
			best=(i,quality)
			print("best indx:",i)
		#break
	else:
		print("Camera ",i, "found, no read")
	res=best[0]

print("Best (and latest) cam:",res)
if res > 0:
	vc = cv2.VideoCapture(res,cv2.CAP_V4L2)
else:
	print("vid0 is best")