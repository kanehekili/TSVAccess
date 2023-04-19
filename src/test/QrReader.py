'''
Created on Apr 14, 2023

@author: matze
'''



# -*- coding: utf-8 -*-
"""
Created on Tue Oct 7 11:41:42 2018

@author: Caihao.Cui
"""

#pip install pyzbar
import pyzbar.pyzbar as pyzbar
import numpy as np
import cv2
import time

def decode(im) : 
    # Find barcodes and QR codes
    decodedObjects = pyzbar.decode(im)
    # Print results
    for obj in decodedObjects:
        print('Type : ', obj.type)
        print('Data : ', obj.data,'\n')     
    return decodedObjects

def testQrComplex():
    # get the webcam:  
    cap = cv2.VideoCapture(0)
    cap.set(3,640)
    cap.set(4,480)
    #160.0 x 120.0
    #176.0 x 144.0
    #320.0 x 240.0
    #352.0 x 288.0
    #640.0 x 480.0
    #1024.0 x 768.0
    #1280.0 x 1024.0
    time.sleep(2)
    
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    while(cap.isOpened()):
        # Capture frame-by-frame
        ret, frame = cap.read()
        # Our operations on the frame come here
        im = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
             
        decodedObjects = decode(im)
    
        for decodedObject in decodedObjects: 
            points = decodedObject.polygon
         
            # If the points do not form a quad, find convex hull
            if len(points) > 4 : 
                hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                hull = list(map(tuple, np.squeeze(hull)))
            else : 
                hull = points;
             
            # Number of points in the convex hull
            n = len(hull)     
            # Draw the convext hull
            for j in range(0,n):
                cv2.line(frame, hull[j], hull[ (j+1) % n], (255,0,0), 3)
    
            x = decodedObject.rect.left
            y = decodedObject.rect.top
    
            print(x, y)
    
            print('Type : ', decodedObject.type)
            print('Data : ', decodedObject.data,'\n')
    
            barCode = str(decodedObject.data)
            cv2.putText(frame, barCode, (x, y), font, 1, (0,255,255), 2, cv2.LINE_AA)
                   
        # Display the resulting frame
        cv2.imshow('frame',frame)
        key = cv2.waitKey(1)
        if key & 0xFF == ord('q'):
            break
        elif key & 0xFF == ord('s'): # wait for 's' key to save 
            cv2.imwrite('Capture.png', frame)    
        
    cap.release()
    cv2.destroyAllWindows() 


def testQRCode():
    camera_id = 0
    delay = 1
    window_name = 'OpenCV QR Code'
    
    qcd = cv2.QRCodeDetector()
    cap = cv2.VideoCapture(camera_id)
    cap.set(3,640)
    cap.set(4,480)    
    time.sleep(2)
    
    while True:
        ret, frame = cap.read()
    
        if ret:
            ret_qr, decoded_info, points, _ = qcd.detectAndDecodeMulti(frame)
            if ret_qr:
                for s, p in zip(decoded_info, points):
                    if s:
                        print(s)
                        color = (0, 255, 0)
                    else:
                        color = (0, 0, 255)
                    frame = cv2.polylines(frame, [p.astype(int)], True, color, 8)
            cv2.imshow(window_name, frame)
    
        if cv2.waitKey(delay) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    
def testQRCode2():
    camera_id = 0
    delay = 1
    window_name = 'OpenCV QR Code'
    
    qcd = cv2.QRCodeDetector()
    cap = cv2.VideoCapture(camera_id)
    cap.set(3,640)
    cap.set(4,480)    
    time.sleep(2)
    
    while True:
        ret, frame = cap.read()
    
        if ret:
            decoded_info, points, _ = qcd.detectAndDecode(frame)
            if points is not None:
                for s, p in zip(decoded_info, points):
                    if s:
                        print(s)
                        color = (0, 255, 0)
                    else:
                        color = (0, 0, 255)
                    frame = cv2.polylines(frame, [p.astype(int)], True, color, 8)
            cv2.imshow(window_name, frame)
    
        if cv2.waitKey(delay) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()    

#https://tutorials-raspberrypi.de/raspberry-pi-barcode-scanner-qr-mit-kamera-selber-bauen/
# schlecht und liegt auf opencv drauf imutils in to die TONNE
#using pyzbar
def testFast():
    cap = cv2.VideoCapture(0)
    cap.set(3,640)
    cap.set(4,480)
    time.sleep(2)
    
    while(cap.isOpened()):
        # Capture frame-by-frame
        ret, frame = cap.read()
        if ret:
            # Our operations on the frame come here
            im = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            decodedObjects = pyzbar.decode(im)

            for decodedObject in decodedObjects: 
                print('Data : ', str(decodedObject.data))


    cap.release()
    cv2.destroyAllWindows()    


if __name__ == '__main__':
    testQRCode()
    #testFast()
    pass