'''
Created on Apr 2, 2023
Reads some input, checks with remote db and gives a sign (RED=forbidden, GREEN=acess allowed
"Zugangskontrolle auf RASPI"
@author: matze
'''
import cv2
import subprocess,os,time
from DBTools import Connector
import smtplib
from email.message import EmailMessage

class Accessor():
    def __init__(self):
        pass
    
    #This is a daemon that should run permantenly.
    def runDeamon(self):
        camera_id = 0
        delay = 1    
        qcd = cv2.QRCodeDetector()
        cap = cv2.VideoCapture(camera_id)    
        while True:
            ret, frame = cap.read()
        
            if ret:
                ret_qr, decoded_info, points, _ = qcd.detectAndDecodeMulti(frame)
                state=None
                if ret_qr:
                    for s, p in zip(decoded_info, points):
                        if s:
                            print(s)
                            state=True
                        else:
                            state=False
                            print("not recognized")
                if state is not None:
                    playSound(state)
                time.sleep(delay)
                
    def fetchData(self,data):
        #check if the id is in the DB
        pass

    def sendMail(self,msgtext):
        sender="mat.wegmann@gmail.com"
        msg = EmailMessage()
        msg['Subject']="Zugangsfehler TSV"
        msg['From']="Tsv@weilheim.de"
        msg['To']="mat.wegmann@gmail.com"
        msg.set_content(msgtext)
        smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        smtp_server.login(sender, "wontworkanyhow")
        smtp_server.sendmail(sender, sender, msg.as_string())
        smtp_server.quit()


def testQRCode():
    camera_id = 0
    delay = 1
    window_name = 'OpenCV QR Code'
    
    qcd = cv2.QRCodeDetector()
    cap = cv2.VideoCapture(camera_id)
    
    while True:
        ret, frame = cap.read()
    
        if ret:
            ret_qr, decoded_info, points, _ = qcd.detectAndDecodeMulti(frame)
            state=None
            if ret_qr:
                for s, p in zip(decoded_info, points):
                    if s:
                        print(s)
                        state=True
                        color = (0, 255, 0)
                    else:
                        color = (0, 0, 255)
                        state=False
                    frame = cv2.polylines(frame, [p.astype(int)], True, color, 8)
            cv2.imshow(window_name, frame)
            if state is not None:
                playSound(state)
    
        if cv2.waitKey(delay) & 0xFF == ord('q'):
            break
    
    cv2.destroyWindow(window_name)

   
def playSound(ok):
    base= os.path.dirname(os.path.abspath(__file__)) 
    #base = os.path.dirname(home)
    if ok:
        fn = base+"/sounds/good.mp3"
    else:
        fn = base+"/sounds/error.mp3"
    cmd=["/usr/bin/mpg123",fn]
    res= subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
    #print(res[0])
    #print(res[1]) 

if __name__ == '__main__':
    a=Accessor()
    #a.runDeamon()
    a.sendMail("das hat nicht gefunzt")
    pass