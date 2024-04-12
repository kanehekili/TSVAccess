#! /usr/bin/env python3
import cv2, v4l2ctl,re

class VidCam():
	def __init__(self,vid,port,isIntrinsic):
		self.v4lDevice=vid
		self.port = int(port)
		self.isInternal=isIntrinsic
		
	def deviceName(self):
		return self.v4lDevice.name
	
	#Posix path like /dev/video0
	def devicePath(self):
		return self.v4lDevice.device
	

class VideoSearch():
	def __init__(self):
		self.data=[]
	
	def addCamData(self,vid,port,isIntrinsic):
		entry=VidCam(vid,port,isIntrinsic)
		self.data.append(entry)
		
	def cameraIntrinsic(self):
		return next((cam for cam in self.data if cam.isInternal),None)
		
	def cameraExternal(self):
		return next((cam for cam in self.data if not cam.isInternal),None)

def searchCams():
	reIndex=re.compile("[0-9]+")
	reLocation = re.compile("Integrated")
	devIter = v4l2ctl.V4l2Device.iter_devices()
	result=VideoSearch()
	
	for vid in devIter:
		if v4l2ctl.V4l2Capabilities.VIDEO_CAPTURE in vid.capabilities:
			port = reIndex.search(str(vid.device))
			loc=reLocation.search(vid.name)
			isIntrinsic=loc is not None
			result.addCamData(vid, port.group()[0], isIntrinsic)
	return result
						
#-----Just testing -------------
def search1():
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
		
		
def searchV4():	
	reIndex=re.compile("[0-9]+")
	reLocation = re.compile("Integrated")
	devIter = v4l2ctl.V4l2Device.iter_devices()
	for vid in devIter:
		if v4l2ctl.V4l2Capabilities.VIDEO_CAPTURE in vid.capabilities:
			print("Name:",vid.name)
			print("PORT:",vid.device)
			print("Buffertypes:",vid.supported_buffer_types)
			gen=vid.iter_buffer_formats(vid.supported_buffer_types[0])
			for buffer in gen:
				print(">> buf:",buffer)
			port = reIndex.search(str(vid.device))
			loc=reLocation.search(vid.name)
			isIntegrated=loc is not None
			print("Found port:",port.group()[0]," is intern:",isIntegrated)


	
if __name__ == '__main__':
	searchV4()	