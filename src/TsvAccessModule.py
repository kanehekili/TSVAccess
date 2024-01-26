'''
Created on Apr 2, 2023
Reads some input, checks with remote db and gives a sign (RED=forbidden, GREEN=acess allowed
"Zugangskontrolle auf RASPI"
@author: matze
'''
import time, socket, signal, sys,threading
import DBTools
from DBTools import OSTools
from TsvDBCreator import SetUpTSVDB,Konfig
from datetime import datetime, date, timedelta
from threading import Timer
import TsvDBCreator

'''
os.uname():
posix.uname_result(sysname='Linux', nodename='raspi3a', release='6.1.29-2-rpi-ARCH', version='#1 SMP Thu May 25 05:35:29 MDT 2023', machine='armv7l')
data[4] > armv7l
'''
import RaspiTools
from RaspiTools import RaspberryGPIO, MFRC522Reader,LED7,Clock,RaspberryFAKE


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
            self.gate.signalBrokenConnection()
            time.sleep(10)
            Log.warning("Reconnect to database")
            self.dbSystem.connectToDatabase(SetUpTSVDB.DATABASE)    
        
        self.db = self.dbSystem.db        
        
    def readLocation(self):
        table1 = self.dbSystem.LOCATIONTABLE
        table2 = self.dbSystem.CONFIGTABLE
        host = socket.gethostname()
        fields=','.join(Konfig.FIELD_DEF)
        stmt = "select %s from %s conf join %s loc where loc.host_name='%s' and conf.config_id =loc.config order by(conf.config_id)"%(fields,table2,table1,host)
        #stmt = "select activity,paySection,groups,grace_time,mode from %s loc JOIN %s conf where loc.config_id=conf.config_id and loc.host_name='%s'"%(table1,table2,host)
        rows = self.db.select(stmt)
        if len(rows) == 0:
            raise Exception("No location data - exiting")

        self.configData = Konfig(rows)
        Log.info("Station info:%s room:%s",host,self.configData.configs[0].room) 
        for entry in self.configData.configs:
            Log.info("  %d) activity:%s paysection:%s groups:%s grace:%s weekday:%s from:%s to:%s",entry.id,entry.activity,entry.paySection,entry.groups,entry.graceTime,str(entry.weekday),str(entry.startTime),str(entry.endTime))

    def runDeamon(self):
        self.running = True
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
            ps = Konfig.asDBString(self.configData.allPaySections())
            stmt ="SELECT id,access,flag,payuntil_date,prepaid from %s m join %s b ON m.id=b.mitglied_id where m.uuid='%s' and b.section in (%s)"%(self.dbSystem.MAINTABLE,self.dbSystem.BEITRAGTABLE,str(rfid),ps) 
            rows = self.db.select(stmt)
            if len(rows) > 0:
                # | id    | access | flag | payuntil_date       |
                res = self.validateRow(rfid, rows[0])  # highlander - we can have only one row per uuid
            else:
                res = False
                Log.info("Denied: No rows")
            if res:
                self.gate.signalAccess()
                Log.info("--- Access:%d ---", rfid)
            else:
                self.gate.signalForbidden()
                Log.info("--- Reject:%d ---", rfid)
        else:
            Log.warning("--- Invalid token %s ---", rfid)   
        
    def __syncWriteTimer(self):
        if self.writeTimer is None:
            return
        self.writeTimer.join()
        self.writeTimer=None 
        
    def validateRow(self, rfid, row):
        if row is None or len(row) == 0:
            Log.warning("Invalid id %d",rfid)
            return False
        # get prim key from the row array
        key = row[0]
        access = row[1]
        flag = row[2]
        eolDate = row[3]
        prepaidCount=row[4]
        cEntry=self.configData.configForUserGroup(access)
        if not cEntry:
            Log.warning("No valid config at current time found for: %d in group %s",rfid,access)
            #handle as gracetime/fake checkout if already checked in today
            if self.hasCheckedInToday(key):
                Log.info("Checked in, faking grace exit")
                self.gate.tickGracetime()
                return True
            return False
        Log.info("Config: %d) %s - %s -%s",cEntry.id,cEntry.activity,cEntry.paySection,cEntry.groups)
        if not self.checkValidity(eolDate, flag, access,cEntry.groups):
            return False
        if not self.checkPrepaid(prepaidCount,cEntry.paySection): 
            return False
        # Allowd. That person needs an entry
        self.writeTimer=Timer(0, self.__forkWriteAccess, [key,prepaidCount,cEntry])
        self.writeTimer.start()
        
        return True        

    def __forkWriteAccess(self, key,prepaidCount,cEntry):
        now = datetime.now().isoformat()
        table = self.dbSystem.TIMETABLE
        #UPDATE? to row count in order to see whether cki or cko. Use the "pause" which part of day to select...
        stmt = "SELECT mitglied_id,access_date from %s where mitglied_id=%s AND activity='%s' AND TIMESTAMPDIFF(SECOND,access_date,NOW()) <= %s"%(table,str(key),cEntry.activity,str(cEntry.graceTime))
        timerows = self.db.select(stmt) 
        if len(timerows) == 0: 
            #gracetime period is over, checkout/recheck in possible
            data = []
            data.append((key, now,cEntry.activity,cEntry.room))
            self.db.insertMany(table, ('mitglied_id', 'access_date', 'activity', 'room'), data)
            if prepaidCount >0: #Dieters Sauna special
                self.voidPrepaid(key, prepaidCount,cEntry.paySection)
                self._showCounter(prepaidCount-1)
        else:
            self.gate.tickGracetime()
            Log.info("Gracetime CKI from %d origin time:%s",timerows[0][0],timerows[0][1])
            if prepaidCount >0:
                self._showCounter(prepaidCount)
    
    def checkPrepaid(self,count,paySection):
        if paySection in TsvDBCreator.PREPAID_INDICATOR:
            Log.info("Abo count: %d [%s]",count,paySection)
            return count>0
        return True

    #kann nur was aus dem PREPAID_INDICATOR sein = Sauna
    def voidPrepaid(self,mid,count,paySection):
        stmt="UPDATE %s set prepaid=%d where mitglied_id=%d and section='%s'"%(self.dbSystem.BEITRAGTABLE,count-1,mid,paySection)
        self.db.select(stmt) 
    
    def hasCheckedInToday(self,key):
        dx = Konfig.asDBString(self.configData.allActivities())
        table = self.dbSystem.TIMETABLE
        stmt = "select count(*) from %s where mitglied_id=%s and DATE(access_date) = CURDATE() and activity in (%s)"%(table,key,dx)
        rows=self.db.select(stmt)
        return rows[0][0]>0 
    
    def _showCounter(self,count):
        if not self.ledCounter:
            return
        self.clock.stop()
        self.ledCounter.number(count)
        time.sleep(3)
        self.clock.runAsync()
        
     
    def checkValidity(self, eolDate, flag, access,allowedGroups):
        if eolDate:
            now = date.today()
            if eolDate.date() < now:
                Log.warning("Member EOL")
                return False

        if flag is not None:
            if flag > 0:
                Log.warning("Member has been flagged!")
                return False
        #no access and empty group is fine
        if len(allowedGroups) == 0:
            Log.debug("Empty access group")
            return True
        if access: 
            ok = access in allowedGroups
            if not ok:
                Log.warning("Wrong group:%s in:%s", access, allowedGroups)
            return ok    
        Log.warning("None access for required group")
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
