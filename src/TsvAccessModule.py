'''
Created on Apr 2, 2023
Reads some input, checks with remote db and gives a sign (RED=forbidden, GREEN=acess allowed
"Zugangskontrolle auf RASPI"
@author: matze
'''
import time, socket, signal, sys,threading
import DBTools
from DBTools import OSTools
from TsvDBCreator import SetUpTSVDB
from datetime import datetime, date, timedelta
from threading import Timer
from ast import literal_eval
import TsvDBCreator

'''
os.uname():
posix.uname_result(sysname='Linux', nodename='raspi3a', release='6.1.29-2-rpi-ARCH', version='#1 SMP Thu May 25 05:35:29 MDT 2023', machine='armv7l')
data[4] > armv7l
'''
import RaspiTools
from RaspiTools import RaspberryGPIO, MFRC522Reader,LED7,Clock


# import smtplib
# from email.message import EmailMessage
OSTools.setupRotatingLogger("TSVAccess", True)
Log = DBTools.Log


class RFIDAccessor():
    HOUR_START=8
    HOUR_END=22
    def __init__(self,invertGPIO):
        self.eastereggs = [2229782266]
        self.writeTimer=None
        # we might use a time between 8 and 22:00self.latestLocCheck=None
        self.condLock = threading.Condition()
        if RaspiTools.RASPI:
            self.gate = RaspberryGPIO(invertGPIO)
            self.reader = MFRC522Reader()
        else:
            self.gate = RaspberryFAKE()
            self.reader = RFCUSB() 
        if RaspiTools.LEDS:
            self.ledCounter=LED7()
            self.ledCounter.clear()
            self.clock=Clock(self.ledCounter.tm)
            self.clock.runAsync()
        else:
            self.ledCounter=None
        
    
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
        
    #TODO in order to change that, we need to check periodically if the config has changed        
    def readLocation(self):
        table1 = self.dbSystem.LOCATIONTABLE
        table2 = self.dbSystem.CONFIGTABLE
        host = socket.gethostname()
        stmt = "select activity,paySection,groups,grace_time,mode from %s loc JOIN %s conf where loc.config_id=conf.config_id and loc.host_name='%s'"%(table1,table2,host)
        rows = self.db.select(stmt)
        if len(rows) == 0:
            raise Exception("No location data - exiting")
        data = rows[0]
        self.activity = data[0]
        self.paySection = data[1]
        self.groups = literal_eval(data[2])
        self.gracetime = data[3]
        self.configShared=data[4]==self.dbSystem.CONFIG_MODE_SHARED

    def _controlLocation(self):
        while self.running:
            now = datetime.now()

            if now.hour >= self.HOUR_END or now.hour < self.HOUR_START:
                goal = now.replace(hour=self.HOUR_START,minute=0,second=0,microsecond=0)                
                if now > goal:
                    goal = goal + timedelta(days=1)  
                dur = (goal-now).seconds                 
            else:
                dur=120

            with self.condLock:
                Log.info("Next location check in %d sec",dur)
                self.condLock.wait(dur)
            if self.running:
                self.readLocation()
        print("Ctrl thread stopped")    
        
    def runDeamon(self):
        self.running = True
        if self.configShared:
            threading.Thread(target=self._controlLocation, name="LocationChecker").start()
            Log.info("Deamon started")
        else:
            Log.info("Static config - no location poll")
        while self.running:
            try:
                rfid = self.reader.read_id()  # int -blocking
                self.verifyAccess(rfid)  
                self.__syncWriteTimer()  
            except KeyboardInterrupt:
                print("Exit")
                return
            except Exception as ex:
                self.gate.signalAlarm()
                Log.error("Read error RFID :%s", str(ex), exc_info=1)
                self._waitForConnection()
                rfid = 0
            
            time.sleep(0.5)

    
    def verifyAccess(self, rfid):
        # we just read the number... 
        if rfid:
            if rfid in self.eastereggs:
                Log.info("Master check %s",rfid)
                if self.ledCounter:
                    self.ledCounter.text("CHEF") 
                self.db.ensureConnection()
                if self.db.isConnected():
                    self.gate.welcome1()
                else:
                    self.gate.signalAlarm()                  
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
        
    def __syncWriteTimer(self):
        if self.writeTimer is None:
            return
        self.writeTimer.join()
        self.writeTimer=None 
        
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
        self.writeTimer=Timer(0, self.__forkWriteAccess, [key,prepaidCount])
        self.writeTimer.start()
        
        return True        

    def __forkWriteAccess(self, key,prepaidCount):
        now = datetime.now().isoformat()
        table = self.dbSystem.TIMETABLE
        stmt = "SELECT mitglied_id,access_date from " + table + " where mitglied_id=" + str(key) + " AND TIMESTAMPDIFF(SECOND,access_date,NOW()) <= " + str(self.gracetime)
        timerows = self.db.select(stmt) 
        if len(timerows) == 0: 
            #gracetime period is over, checkout/recheck in possible
            data = []
            data.append((key, now,self.activity))
            self.db.insertMany(table, ('mitglied_id', 'access_date', 'location'), data)
            if prepaidCount >0: #Dieters Sauna special
                self.voidPrepaid(key, prepaidCount)
                self._showCounter(prepaidCount-1)
        else:
            self.gate.tickGracetime()
            Log.info("Gracetime CKI from %d origin time:%s",timerows[0][0],timerows[0][1])
            if prepaidCount >0:
                self._showCounter(prepaidCount)
    
    def checkPrepaid(self,count):
        if self.paySection in TsvDBCreator.PREPAID_INDICATOR:
            Log.info("Abo count: %d [%s]",count,self.paySection)
            return count>0
        return True

    def voidPrepaid(self,mid,count):
        stmt="UPDATE %s set prepaid=%d where mitglied_id=%d and section='%s'"%(self.dbSystem.BEITRAGTABLE,count-1,mid,self.paySection)
        self.db.select(stmt) 
    
    def _showCounter(self,count):
        if not self.ledCounter:
            return
        self.clock.stop()
        self.ledCounter.number(count)
        time.sleep(3)
        self.clock.runAsync()
        
     
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

    def shutDown(self):
        self.running=False
        with self.condLock:            
            self.condLock.notify_all()
        self.dbSystem.close()
        if self.ledCounter:
            self.clock.stop()
            self.ledCounter.text("StOP")
            del self.ledCounter
            del self.clock #rm all TM instances!

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
        text = input("USB>>")
        print("Entered:",text)
        return int(text)


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
    argv = sys.argv
    invertGPIO=False
    if len(argv)>1:
        invertGPIO="-i" == argv[1]      
    try:
        ACCESSOR = RFIDAccessor(invertGPIO)
        if ACCESSOR.connect():
            ACCESSOR.runDeamon()
        else:
            Log.warning("Error not connected")
    except Exception as ex:
        Log.exception("Error in main:")
    except SystemExit as se:
        Log.warning("System exit")
    finally:
        ACCESSOR.shutDown()  
        RaspiTools.cleanup()
        Log.info("Accessor clean shut down")     
    # a.sendMail("das hat nicht gefunzt")
