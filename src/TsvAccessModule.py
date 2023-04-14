'''
Created on Apr 2, 2023
Reads some input, checks with remote db and gives a sign (RED=forbidden, GREEN=acess allowed
"Zugangskontrolle auf RASPI"
@author: matze
'''
import cv2
import subprocess,os,time
from DBTools import OSTools
from TsvDBCreator import SetUpTSVDB
from datetime import datetime
from threading import Timer

try:
    import RPi.GPIO as GPIO #@UndefinedVariable
    RASPI=True
except Exception:
    print("no GPIOS installed")
    RASPI=False

#import smtplib
#from email.message import EmailMessage

class Accessor():
    def __init__(self):
        OSTools.setupRotatingLogger("TSVAccess",True)
        if RASPI:
            self.gate=RaspberryGPIO()
        else:
            self.gate=RaspberryFAKE()
    
    def connect(self):
        self.dbSystem = SetUpTSVDB(SetUpTSVDB.DATABASE)
        self.db=self.dbSystem.db
        return self.dbSystem.isConnected()
    
    #This is a daemon that should run permantenly.
    def runDeamon(self):
        camera_id = 0
        delay = 0.4    
        qcd = cv2.QRCodeDetector()
        cap = cv2.VideoCapture(camera_id)    
        while True:
            ret, frame = cap.read()
            if ret:
                #ret_qr, decoded_info, _, _ = qcd.detectAndDecodeMulti(frame)
                ret_qr, decoded_info, _, _ = qcd.detectAndDecodeMulti(frame)
                if ret_qr:
                    for s in decoded_info:
                    #for s, p in zip(decoded_info, points):
                        if s:
                            print(s)
                            self.verifyAccess(s)
                        else:
                            print("read failed")
                            playSound(True)

                time.sleep(delay)
                
    def verifyAccess(self,data):
        #check if the id is in the DB
        tokens =data.split(",")
        if len(tokens)==0:
            print("no valid tokens")
            return False
        print("Access to:",tokens)
        #could be no number.
        key =tokens[0]
        if key.isnumeric():
            stmt="SELECT * from "+self.dbSystem.MAINTABLE+" where id="+key
            row = self.db.select(stmt)
            res=self.validateRow(key,row)
        else:
            res=False
            print("Invalid card")
        if res:
            self.accessOK()
            return True
        
        self.accessForbidden()
        return False


    def validateRow(self, key,row):
        if row is None or len(row)==0:
            print("Invalid id %s"%(key))
            return False
        
        #TODO Check kennzeichen in the fields -> needs config based on gate.
        print("Access OK - no fields checked")
        #Allowd. That person needs an entry
        table= self.dbSystem.TIMETABLE
        now = datetime.now().isoformat()
        stmt = "SELECT mitglied_id,access_date from "+table+" where mitglied_id="+key+" AND access_date >= DATE(NOW()) + INTERVAL -"+self.dbSystem.GRACETIME+" hour"
        print("Search time db:",stmt)
        timerows=self.db.select(stmt) 
        print("Access rows:",timerows)
        if len(timerows)==0:
            data=[]
            data.append((key,now))
            self.db.insertMany(table, ('mitglied_id','access_date'), data)
        
        return True

    def accessOK(self):
        self.gate.signalAccess()#GREEN LED

    def accessForbidden(self):
        self.gate.signalForbidden()#RED LED
        
        

class RaspberryGPIO():
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.OUT)
        GPIO.setup(18, GPIO.OUT)
        self.timer = Timer(5,self.reset)
        '''
        using GPIOS:
        o o
        o o
        o x -GND
        o o                
        o o
        x x -Grau(17)-Lila(18        
        |--| usb==unten

        '''
    def signalAccess(self):
        GPIO.output(18, True)
        GPIO.output(17, False)
        self.timer.cancel()
        self.timer.start()
        
        
    def signalForbidden(self):
        GPIO.output(17, True)        
        GPIO.output(18, False)
        self.timer.cancel()
        self.timer.start()
        
    
    #TODO needs timer
    def reset(self):
        GPIO.output(18, False)
        GPIO.output(17, False)
            

class RaspberryFAKE():
    def signalAccess(self):
        print("GREEN LIGHT")    

    def signalForbidden(self):
        print("RED LIGHT")        
    
    '''
    Not working wih gmail
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
    '''

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
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
    #print(res[0])
    #print(res[1]) 

if __name__ == '__main__':
    #testQRCode()
    
    a=Accessor()
    if a.connect():
        a.runDeamon()
    else:
        print("Error not connected")
    #a.sendMail("das hat nicht gefunzt")
    