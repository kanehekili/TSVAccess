'''
Created on Apr 2, 2023
Reads some input, checks with remote db and gives a sign (RED=forbidden, GREEN=acess allowed
"Zugangskontrolle auf RASPI"
@author: matze
'''
import cv2
import subprocess,os,time
import DBTools
from DBTools import OSTools
from TsvDBCreator import SetUpTSVDB
from datetime import datetime
from threading import Timer
from _datetime import date
'''
os.uname():
posix.uname_result(sysname='Linux', nodename='raspi3a', release='6.1.29-2-rpi-ARCH', version='#1 SMP Thu May 25 05:35:29 MDT 2023', machine='armv7l')
data[4] > armv7l
'''

try:
    import RPi.GPIO as GPIO #@UndefinedVariable
    from mfrc522 import SimpleMFRC522
    RASPI=True
except Exception:
    print("no GPIOS installed")
    RASPI=False

#import smtplib
#from email.message import EmailMessage
OSTools.setupRotatingLogger("TSVAccess",True)
Log = DBTools.Log

class RFIDAccessor():
    def __init__(self):
        #OSTools.setupRotatingLogger("TSVAccess",True)
        if RASPI:
            self.gate=RaspberryGPIO()
            self.reader=SimpleMFRC522()
        else:
            self.gate=RaspberryFAKE()
            self.reader=RFCUSB() 
    
    def connect(self):
        self.dbSystem = SetUpTSVDB(SetUpTSVDB.DATABASE)
        while not self.dbSystem.isConnected():
            time.sleep(10)
            Log.warning("Reconnect to database")
            self.dbSystem.connectToDatabase(SetUpTSVDB.DATABASE)    
            
        self.db=self.dbSystem.db
        return self.dbSystem.isConnected()
        
    def runDeamon(self):
        self.running=True
        while self.running:
            print("start reading")
            #prim,text = self.reader.read() #(int,text)
            try:
                rfid= self.reader.read_id() #int
                if RASPI:
                    rfid=self._convert(rfid)
            except KeyboardInterrupt:
                print("Exit")
                return
            except:
                Log.warning("Read error RFID")
                rfid=0
            self.verifyAccess(rfid)
            time.sleep(1)
    
    def _convert(self,bigInt):
        if not bigInt:
            return 0
        rbytes = bigInt.to_bytes(5)
        tmp = rbytes[:-1][::-1]
        return int.from_bytes(tmp)
    
     
    def verifyAccess(self,rfid):
        #we just read the number... 
        if rfid:
            stmt="SELECT * from "+self.dbSystem.MAINTABLE+" where uuid="+str(rfid)
            rows = self.db.select(stmt)
            if len(rows)>0:
                res = self.validateRow(rfid,rows[0]) #highlander - we can have only one row per uuid
            else:
                res=False
            if res:
                self.gate.signalAccess()
                Log.info("Access:%d",rfid)
            else:
                self.gate.signalForbidden()
                Log.info("Reject:%d",rfid)
        else:
            Log.warning("Invalid token %s",rfid)    
        
    def validateRow(self,rfid,row):
        if row is None or len(row)==0:
            Log.warning("Invalid id %d"%(rfid))
            return False
        
        #get prim key from the row array
        key = row[0]
        eolDate=row[3]
        access=row[4]
        if not self.checkValidity(eolDate,access):
            return False
        #Allowd. That person needs an entry
        table= self.dbSystem.TIMETABLE
        location=self.dbSystem.LOCATION
        now = datetime.now().isoformat()
        stmt = "SELECT mitglied_id,access_date from "+table+" where mitglied_id="+str(key)+" AND TIMESTAMPDIFF(SECOND,access_date,NOW()) <= "+self.dbSystem.GRACETIME
        
        Log.debug("Search time db:%s",stmt)
        timerows=self.db.select(stmt) 
        Log.debug("Access rows:%s",timerows)
        if len(timerows)==0:
            data=[]
            data.append((key,now,location))
            self.db.insertMany(table, ('mitglied_id','access_date','location'), data)
        
        return True        
     
    def checkValidity(self,eolDate,access):
        if eolDate:
            now = date.today()
            if eolDate < now:
                Log.warning("Member EOL")
                return False
        
        if access:
            allowed = SetUpTSVDB.ACCESS
            ok= access in allowed
            if not ok:
                Log.warning("Wrong group:%s in:%s",access,allowed)
            return ok    
        return False

class QRAccessor():
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
        location=self.dbSystem.LOCATION
        now = datetime.now().isoformat()
        stmt = "SELECT mitglied_id,access_date from "+table+" where mitglied_id="+key+" AND access_date >= DATE(NOW()) + INTERVAL -"+self.dbSystem.GRACETIME+" hour"
        Log.debug("Search time db:%s",stmt)
        timerows=self.db.select(stmt) 
        if len(timerows)==0:
            data=[]
            data.append((key,now,location))
            self.db.insertMany(table, ('mitglied_id','access_date','location'), data)
        
        return True

    def accessOK(self):
        self.gate.signalAccess()#GREEN LED

    def accessForbidden(self):
        self.gate.signalForbidden()#RED LED
        
        

class RaspberryGPIO():
    PINGREEN=2
    PINRED=3

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.PINGREEN, GPIO.OUT)
        GPIO.setup(self.PINRED, GPIO.OUT)
        self.reset() #GPIOS start on hi... 
        self.timer = None
        '''
        using GPIOS:
        o o
        o o
        o x -GND
        o o                
        o o
        x x -Grau(17)-Lila(18)        
        |--| usb==unten
    
        Relais
        o x 5V Yello
        x o GPIO2 Red
        x o GPIO3 Orange
        o o                
        X o -GND Green
        o o         
        |--| usb==unten
        
        '''
    def signalAccess(self):
        GPIO.output(self.PINGREEN, True)
        GPIO.output(self.PINRED, False)
        self._restartTimer()        
        
    def signalForbidden(self):
        GPIO.output(self.PINRED, True)        
        GPIO.output(self.PINGREEN, False)
        self._restartTimer()
        
    
    #TODO needs timer
    def reset(self):
        GPIO.output(self.PINRED, True)
        GPIO.output(self.PINGREEN, True)
            
    def _restartTimer(self):
        if self.timer:
            self.timer.cancel()
        self.timer=Timer(5,self.reset)
        self.timer.start()        

'''
        RFID READER
        x o 3.3V red
        o o
        o x -GND black
        o o                
        o o
        o o
        o o
        o o
        o o
        x o SPio Mosi - Green   
        x x SPIO Miso - Orange / GPIO 25(RST) Blue
        x x SPIO CLK -  brown  / SPI CSO Yellow     
        |--| usb==unten
'''    
   
    

class RaspberryFAKE():
    def __init__(self):
        self.timer = None    
    
    def signalAccess(self):
        print("GREEN LIGHT") 
        self._restartTimer()

    def signalForbidden(self):
        print("RED LIGHT")        
        self._restartTimer()

    def reset(self):
        print("RESET LIGHT")
        
            
    def _restartTimer(self):
        if self.timer:
            self.timer.cancel()
        self.timer=Timer(5,self.reset) 
        self.timer.start()
        
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

#TODO - we might put this in a generic module for the RegisterModule
class RFCUSB():
    def __init__(self):
        pass
    
    def read_id(self):
        text=input()
        return int(text)

   
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
    try:
        a=RFIDAccessor()
        if a.connect():
            a.runDeamon()
        else:
            Log.warning("Error not connected")
    except:
        Log.exception("Error in main:")
    finally:
        if RASPI:
            GPIO.cleanup()
        
        
    #a.sendMail("das hat nicht gefunzt")
