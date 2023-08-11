'''
Created on Apr 2, 2023
Reads some input, checks with remote db and gives a sign (RED=forbidden, GREEN=acess allowed
"Zugangskontrolle auf RASPI"
@author: matze
'''
import time, socket, signal, sys
import DBTools
from DBTools import OSTools
from TsvDBCreator import SetUpTSVDB
from datetime import datetime, date
from threading import Timer
from ast import literal_eval
import TsvDBCreator

'''
os.uname():
posix.uname_result(sysname='Linux', nodename='raspi3a', release='6.1.29-2-rpi-ARCH', version='#1 SMP Thu May 25 05:35:29 MDT 2023', machine='armv7l')
data[4] > armv7l
'''

try:
    import RPi.GPIO as GPIO  # @UnresolvedImport
    from mfrc522 import SimpleMFRC522  # @UnresolvedImport
    RASPI = True
except Exception:
    print("no GPIOS installed")
    RASPI = False

# import smtplib
# from email.message import EmailMessage
OSTools.setupRotatingLogger("TSVAccess", True)
Log = DBTools.Log


# TODO take this into consideration:
# https://www.raspberrypi-spy.co.uk/2018/02/rc522-rfid-tag-read-raspberry-pi/
class RFIDAccessor():

    def __init__(self):
        self.eastereggs = [2229782266]
        if RASPI:
            self.gate = RaspberryGPIO()
            self.reader = MFRC522Reader()
        else:
            self.gate = RaspberryFAKE()
            self.reader = RFCUSB() 
    
    def connect(self):
        self.dbSystem = SetUpTSVDB(SetUpTSVDB.DATABASE)
        self._waitForConnection()
        self.readLocation()
        return self.dbSystem.isConnected()
    
    def _waitForConnection(self):
        while not self.dbSystem.isConnected():
            time.sleep(10)
            Log.warning("Reconnect to database")
            self.dbSystem.connectToDatabase(SetUpTSVDB.DATABASE)    
        
        self.db = self.dbSystem.db        
    def readLocation(self):
        table1 = self.dbSystem.LOCATIONTABLE
        table2 = self.dbSystem.CONFIGTABLE
        host = socket.gethostname()
        stmt = "select activity,paySection,groups,grace_time from %s loc JOIN %s conf where loc.config_id=conf.config_id and loc.host_name='%s'"%(table1,table2,host)
        rows = self.db.select(stmt)
        if len(rows) == 0:
            raise Exception("No location data - exiting")
        data = rows[0]
        self.activity = data[0]
        self.paySection = data[1]
        self.groups = literal_eval(data[2])
        self.gracetime = data[3]
        
    def runDeamon(self):
        self.running = True
        Log.info("Deamon started")
        #TODO: change of location is not known! we need to check every x seconds between 8:00 and 22:00 -so that's about a hearbeat #use on locs that a changeable
        while self.running:
            try:
                rfid = self.reader.read_id()  # int
                self.verifyAccess(rfid)    
            except KeyboardInterrupt:
                print("Exit")
                return
            except Exception as ex:
                self.gate.signalAlarm()
                Log.error("Read error RFID :%s", str(ex), exc_info=1)
                self._waitForConnection()
                rfid = 0
            
            time.sleep(1)
    
    def verifyAccess(self, rfid):
        # we just read the number... 
        if rfid:
            if rfid in self.eastereggs:
                self.gate.welcome1()
                return
            #rfid & paysection must fit ->if section in PREPAID-> decrease count
            stmt = "SELECT id,access,flag,payuntil_date,prepaid from " + self.dbSystem.MAINTABLE + " m JOIN " + self.dbSystem.BEITRAGTABLE + " b ON m.id=b.mitglied_id where m.uuid=" + str(rfid) + " and b.section='" + self.paySection + "'"
            rows = self.db.select(stmt)
            if len(rows) > 0:
                # | id    | access | flag | payuntil_date       |
                res = self.validateRow(rfid, rows[0])  # highlander - we can have only one row per uuid
            else:
                res = False
            if res:
                self.gate.signalAccess()
                Log.info("Access:%d", rfid)
            else:
                self.gate.signalForbidden()
                Log.info("Reject:%d", rfid)
        else:
            Log.warning("Invalid token %s", rfid)    
        
    def validateRow(self, rfid, row):
        if row is None or len(row) == 0:
            Log.warning("Invalid id %d" % (rfid))
            return False
        # get prim key from the row array
        key = row[0]
        access = row[1]
        flag = row[2]
        eolDate = row[3]
        prepaidCount=row[4]
        if not self.checkValidity(eolDate, flag, access):
            return False
        if not self.checkPrepaid(prepaidCount): 
            return False
        # Allowd. That person needs an entry
        Timer(0, self.__forkWriteAccess, [key,prepaidCount]).start()
        
        return True        

    def __forkWriteAccess(self, key,prepaidCount):
        # location = self.dbSystem.LOCATION
        now = datetime.now().isoformat()
        table = self.dbSystem.TIMETABLE
        stmt = "SELECT mitglied_id,access_date from " + table + " where mitglied_id=" + str(key) + " AND TIMESTAMPDIFF(SECOND,access_date,NOW()) <= " + str(self.gracetime)
        
        Log.debug("Search time db:%s", stmt)
        timerows = self.db.select(stmt) 
        Log.debug("Access rows:%s", timerows)
        if len(timerows) == 0: 
            data = []
            data.append((key, now,self.activity))
            self.db.insertMany(table, ('mitglied_id', 'access_date', 'location'), data)
        if prepaidCount >0: #Dieters Sauna special
            self.voidPrepaid(key, prepaidCount)
    
    def checkPrepaid(self,count):
        if self.paySection in TsvDBCreator.PREPAID_INDICATOR:
            return count>0
        return True

    def voidPrepaid(self,mid,count):
        stmt="UPDATE %s set prepaid=%d where mitglied_id=%d and section='%s'"%(self.dbSystem.BEITRAGTABLE,count-1,mid,self.paySection)
        self.db.select(stmt) 
     
    def checkValidity(self, eolDate, flag, access):
        if eolDate:
            now = date.today()
            if eolDate.date() < now:
                Log.warning("Member EOL")
                return False

        if flag is not None:
            if flag > 0:
                Log.warning("Member has been flagged!")
                return False
        
        if access:
            if len(self.groups) == 0:
                Log.debug("Access %s meets empty group", access)
                return True 
            ok = access in self.groups
            if not ok:
                Log.warning("Wrong group:%s in:%s", access, self.groups)
            return ok    
        return False

'''
import cv2
class QRAccessor():

    def __init__(self):
        OSTools.setupRotatingLogger("TSVAccess", True)
        
        if RASPI:
            self.gate = RaspberryGPIO()
        else:
            self.gate = RaspberryFAKE()
    
    def connect(self):
        self.dbSystem = SetUpTSVDB(SetUpTSVDB.DATABASE)
        self.db = self.dbSystem.db
        return self.dbSystem.isConnected()
    
    # This is a daemon that should run permantenly.
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
                    # for s, p in zip(decoded_info, points):
                        if s:
                            print(s)
                            self.verifyAccess(s)
                        else:
                            print("read failed")
                            playSound(True)

                time.sleep(delay)
                
    def verifyAccess(self, data):
        # check if the id is in the DB
        tokens = data.split(",")
        if len(tokens) == 0:
            print("no valid tokens")
            return False
        print("Access to:", tokens)
        # could be no number.
        key = tokens[0]
        if key.isnumeric():
            stmt = "SELECT * from " + self.dbSystem.MAINTABLE + " where id=" + key
            row = self.db.select(stmt)
            res = self.validateRow(key, row)
        else:
            res = False
            print("Invalid card")
        if res:
            self.accessOK()
            return True
        
        self.accessForbidden()
        return False

    def validateRow(self, key, row):
        if row is None or len(row) == 0:
            print("Invalid id %s" % (key))
            return False
        
        # TODO Check kennzeichen in the fields -> needs config based on gate.
        print("Access OK - no fields checked")
        # Allowd. That person needs an entry
        table = self.dbSystem.TIMETABLE
        location = self.dbSystem.LOCATION
        now = datetime.now().isoformat()
        stmt = "SELECT mitglied_id,access_date from " + table + " where mitglied_id=" + key + " AND access_date >= DATE(NOW()) + INTERVAL -" + self.dbSystem.GRACETIME + " hour"
        Log.debug("Search time db:%s", stmt)
        timerows = self.db.select(stmt) 
        if len(timerows) == 0:
            data = []
            data.append((key, now, location))
            self.db.insertMany(table, ('mitglied_id', 'access_date', 'location'), data)
        
        return True

    def accessOK(self):
        self.gate.signalAccess()  # GREEN LED

    def accessForbidden(self):
        self.gate.signalForbidden()  # RED LED
 '''       


class RaspberryGPIO():
    PINGREEN = 2
    PINORANGE = 3
    PINRED = 17
    PINSIGNAL = 27
    LIGHTON = False
    LIGHTOFF = True  # depends how we cable the relais

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.PINGREEN, GPIO.OUT)
        GPIO.setup(self.PINRED, GPIO.OUT)
        GPIO.setup(self.PINORANGE, GPIO.OUT)
        GPIO.setup(self.PINSIGNAL, GPIO.OUT)
        self.reset()  # GPIOS start on hi... 
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
        o x 5V Red
        x o GPIO2 Blue   ->Green light (OK)
        x o GPIO3 yello   -> yello (WARN)
        o o                
        X o -GND Green  
        x o GPIO 17 orange  -> red (NO ACCESS)
        x o GPIO27  brown   ->signal (NO ACCESS)       
        |--| usb==unten
        
        '''

    def signalAccess(self):
        self.reset()
        GPIO.output(self.PINGREEN, self.LIGHTON)
        self._restartTimer()        
        
    def signalForbidden(self):
        self.reset()
        GPIO.output(self.PINRED, self.LIGHTON)        
        GPIO.output(self.PINSIGNAL, self.LIGHTON)
        self._restartTimer()
    
    def signalAlarm(self):
        self.reset()
        GPIO.output(self.PINORANGE, self.LIGHTON)
        self._restartTimer()
    
    def welcome1(self):
        self.reset()
        GPIO.output(self.PINGREEN, self.LIGHTON)
        time.sleep(0.3)
        GPIO.output(self.PINORANGE, self.LIGHTON) 
        time.sleep(0.05)
        GPIO.output(self.PINGREEN, self.LIGHTOFF)
        time.sleep(0.3)
        GPIO.output(self.PINRED, self.LIGHTON)
        time.sleep(0.05)
        GPIO.output(self.PINORANGE, self.LIGHTOFF)
        time.sleep(0.3)
        GPIO.output(self.PINORANGE, self.LIGHTON)
        time.sleep(0.05)
        GPIO.output(self.PINRED, self.LIGHTOFF)
        time.sleep(0.3)
        GPIO.output(self.PINGREEN, self.LIGHTON)
        time.sleep(0.05)
        GPIO.output(self.PINORANGE, self.LIGHTOFF)
        time.sleep(0.3)
        GPIO.output(self.PINGREEN, self.LIGHTOFF)
    
    # TODO needs timer
    def reset(self):
        GPIO.output(self.PINRED, self.LIGHTOFF)  # true=off, false=ON
        GPIO.output(self.PINGREEN, self.LIGHTOFF)
        GPIO.output(self.PINORANGE, self.LIGHTOFF)
        GPIO.output(self.PINSIGNAL, self.LIGHTOFF)        
            
    def _restartTimer(self):
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(5, self.reset)
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

    def welcome1(self):
        print("Welcome")

    def signalAlarm(self):
        print("ORANGE LIGHT")
        self._restartTimer()

    def reset(self):
        print("RESET LIGHT")
            
    def _restartTimer(self):
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(5, self.reset) 
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


class RFCUSB():

    def __init__(self):
        pass
    
    def read_id(self):
        text = input()
        return int(text)


# changed due to 100% CPU
class MFRC522Reader():

    def __init__(self):
        self.mfrc = SimpleMFRC522()
        
    def read_id(self):
        rfid = None
        while not rfid:
            data = self.mfrc.read_id_no_block()
            if data:
                return self._convert(data)
            time.sleep(0.3)
    
    def _convert(self, bigInt):
        if not bigInt:
            return 0
        rbytes = bigInt.to_bytes(5)
        tmp = rbytes[:-1][::-1]  # little to big endian
        return int.from_bytes(tmp)

'''   
def playSound(ok):
    base = os.path.dirname(os.path.abspath(__file__)) 
    # base = os.path.dirname(home)
    if ok:
        fn = base + "/sounds/good.mp3"
    else:
        fn = base + "/sounds/error.mp3"
    cmd = ["/usr/bin/mpg123", fn]
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
'''


def handleSignals(*_args):
    sys.exit(1)  # -> leads to finally
    

if __name__ == '__main__':
    global ACCESSOR
    signal.signal(signal.SIGINT, handleSignals) 
    signal.signal(signal.SIGTERM, handleSignals)
    signal.signal(signal.SIGHUP, handleSignals)        
    try:
        ACCESSOR = RFIDAccessor()
        if ACCESSOR.connect():
            ACCESSOR.runDeamon()
        else:
            Log.warning("Error not connected")
    except Exception as ex:
        Log.exception("Error in main:")
    except SystemExit as se:
        Log.warning("System exit")
    finally:
        if RASPI:
            GPIO.cleanup()
        ACCESSOR.dbSystem.close()  
        Log.info("Accessor clean shut down")     
    # a.sendMail("das hat nicht gefunzt")
