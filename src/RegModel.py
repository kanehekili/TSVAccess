'''
Created on Nov 21, 2023

@author: matze
'''
import TsvDBCreator
from TsvDBCreator import SetUpTSVDB
import DBTools
from datetime import datetime,timedelta
import requests
from ast import literal_eval

Log = DBTools.Log

'''
We need controllers for mode register (you search for names and have a camera)
and mode rfid (you have a registered user and search it with the rfid token)
'''
class RegisterController():
    def __init__(self,ui):
        self.mainFrame=ui

    def handleRFIDChanged(self,str_RFID):
        self.mainFrame.verifyRFID(str_RFID)

    def supportsCamera(self):
        return True

    def setInitialFocus(self):
        self.mainFrame.ui_SearchEdit.setFocus()
        #self.mainFrame.ui_SearchEdit.setStyleSheet("QComboBox,QComboBox::editable { background: rgb(0,160,0); color:white}");
        self.mainFrame.ui_SearchEdit.setStyleSheet("QComboBox { padding: 2px; border-radius: 4px; border: 2px solid rgb(0,160,0);}");

class RFIDController(RegisterController):
    def __init__(self, ui):
        RegisterController.__init__(self,ui)        

    #slot if rfid search is active (mode)
    def handleRFIDChanged(self,str_RFID):
        #String may have a leading zero.
        try:
            tmp=int(str_RFID)
        except:
            self.mainFrame.searchWithRFID(str_RFID)
            return
        clean=str(tmp)
        self.mainFrame.searchWithRFID(clean)

    def supportsCamera(self):
        return False

    def setInitialFocus(self):
        self.mainFrame.ui_RFID.setFocus()
        #self.mainFrame.ui_RFID.setStyleSheet("QLineEdit { background: rgb(0,160,0); color:white}");
        self.mainFrame.ui_RFID.setStyleSheet("QLineEdit {padding: 2px; border-radius: 4px; border: 2px solid rgb(0,160,0); }");


class Registration():
    SAVEPIC = "/tmp/tsv.screenshot.png"   

    def __init__(self):
        # self.accesscodes = []
        self.borders = []
        self.aaTransponders = []
        self.memberList=None
        self.configs=None #a Konfig instance containing KonfigEntry 
        

    def connect(self):
        self.dbSystem = SetUpTSVDB(SetUpTSVDB.DATABASE)
        self.db = self.dbSystem.db
        if self.dbSystem.isConnected():
            self.readAATransponders()
            self.configs = self.readConfigurations()
            return True
        return False
    
    def readAATransponders(self):
        stmt = "Select uuid from %s" % (SetUpTSVDB.ASSAABLOY)
        rows = self.db.select(stmt)
        for uuid in rows:
            self.aaTransponders.append(uuid[0]) 
        Log.info("Loaded AA Transponders:%d", len(self.aaTransponders))
    
    #Membercontrol
    def readConfigurations(self):
        fields=','.join(Konfig.FIELD_DEF)
        stmt = "SELECT " + fields + " from " + self.dbSystem.CONFIGTABLE
        res = self.db.select(stmt)
        return Konfig(res)
    
    def containsLegacyAA(self, rfid):
        return rfid in self.aaTransponders
    
    # reads the list and passes it to the caller...
    def getMembers(self):
        fields = ','.join(Mitglied.FIELD_DEF)  # FIELD_DEF=('id','first_name','last_name','access','birth_date,picpath,uuid,flag') 
        # stmt = "SELECT id,first_name,last_name from " + self.dbSystem.MAINTABLE
        stmt = "SELECT " + fields + " from " + self.dbSystem.MAINTABLE
        self.memberList = []
        res = self.db.select(stmt)
        for titem in res:
            # id(int) (str) (str) (str) date! int
            m = Mitglied(titem[0], titem[1], titem[2], titem[3], titem[4], titem[6])
            m.picpath = titem[5]
            m.setFlag(titem[7])
            self.memberList.append(m)
        return self.memberList
    
    #used by memberControl
    def todaysAccessDateStrings(self, mbrID, location):
        table = self.dbSystem.TIMETABLE
        stmt= "select access_date from %s where mitglied_id =%d and location='%s' and DATE(access_date) = CURDATE();"%(table,mbrID,location)  
        #stmt= "select access_date from %s where mitglied_id =%d and location='%s' and DATE(access_date) < CURDATE();"%(table,mbrID,location)
        rows = self.db.select(stmt)
        timeData=[]
        for row in rows:
            timeData.append(datetime.strftime(row[0],' %H:%M '))
        return timeData
    
    #kind of manual cki - MemberControl
    def saveAccessDate(self,mbr,accessDate,locConfig):
        table = self.dbSystem.TIMETABLE
        data = []
        data.append((mbr.id, accessDate,locConfig.activity))
        self.db.insertMany(table, ('mitglied_id', 'access_date', 'location'), data)
    
    def updateMember(self, mbr):
        table = self.dbSystem.MAINTABLE
        fields = Mitglied.FIELD_SAVE_DEF
        data = mbr.dataSaveArray()
        Log.info("Saving member:%s", str(data[0]))
        self.db.insertMany(table, fields, data)
        self.updateAboData(mbr)
        self.updateAccessData(mbr)
        self.updateRFIDAbrechnung(mbr)
    
    def updateAboData(self, mbr):
        section = mbr.abo[0]
        if section is None:
            return
        oldCount = mbr.currentAbo[1]
        newCount = mbr.abo[1]
        fields = ('mitglied_id', 'section', 'prepaid')
        data = [(mbr.id, section, oldCount + mbr.abo[1])]
        Log.info("Update ABO prepaid count from %s , %d +%d", section, oldCount, newCount)
        if newCount > 0:  # stays 0 if old has been changed
            msg = "Mitglied Nr %d (%s %s) \nhat heute ein 10er Abo bestellt - als Erinnerung zum abbuchen \U0001f604" % (mbr.id, mbr.firstName, mbr.lastName)
            self.dbSystem.sendEmail("Sauna Abo Daten", True, msg)
            
        self.db.insertMany(self.dbSystem.BEITRAGTABLE, fields, data)

    def updateAccessData(self, mbr):
        if mbr.initalAccess == mbr.access:  # no change
            return
        key = mbr.access
        if key is None or len(key) == 1:
            return
        # only create a section if KR or group -notfall
        # section lesen - nur wenn notig und nicht leer
        stmt = "select paySection from Konfig where groups like '%%%s%%'" % (key) 
        rows = self.db.select(stmt)
        if len(rows) < 1:
            return;
        section = rows[0][0]
        fields = ('mitglied_id', 'section')
        data = [(mbr.id, section)]
        self.db.insertMany(self.dbSystem.BEITRAGTABLE, fields, data)
        mbr.initalAccess = mbr.access
     
    def updateRFIDAbrechnung(self, mbr):
        if mbr.initialRFID == mbr.rfid:
            return
        now = datetime.now().isoformat()
        data = []
        data.append((now, mbr.id))
        self.db.insertMany(self.dbSystem.REGISTERTABLE, ('register_date', 'mitglied_id'), data)
        Log.info("Dispensing NEW Chip %d to member %d",mbr.rfid,mbr.id)
        mbr.initialRFID = mbr.rfid

    def readAboData(self, mbr):
        section = TsvDBCreator.PREPAID_INDICATOR[0]  # currently only one
        stmt = "select prepaid from BEITRAG where mitglied_id=%d and section='%s'" % (mbr.id, section)
        rows = self.db.select(stmt)
        if len(rows) == 0:
            Log.debug("No Abo data")
            return
        mbr.currentAbo = (section, rows[0][0])
        Log.info("Abo count:%d", rows[0][0])
    
    def mailError(self, msg):
        self.dbSystem.sendEmail("Registration Error Msg", False, msg)
    
    # beware_ connection could be broken
    def savePicture(self, member):
        self.db.ensureConnection() 
        saved = Registration.SAVEPIC       
        targetPath = SetUpTSVDB.PICPATH
        pic = member.lastName + "-" + member.primKeyString() + ".png"
        
        host = SetUpTSVDB.HOST
        response = None
        try:
            reqUrl = "http://%s:5001/%s/%s" % (host, targetPath, pic)     
            Log.info("Saving picture :%s" % (reqUrl)) 
            # reqUrl="http://localhost:5001/TSVPIC/"+pic #works!
            response = requests.post(reqUrl, files={'file':open(saved, 'rb')})
        except:
            Log.error("Pic server not available:")
            return False;
        saveOK = response != None and response.status_code == 200
        if saveOK:
            member.picpath = pic
        return saveOK 
     
    '''scp example - for other use..    
    def savePicture2(self, member):
        saved = Registration.SAVEPIC
        data = member.lastName + "-" + member.primKeyString() + ".png"
        targetPath = SetUpTSVDB.PICPATH
        member.picpath = data
        try:
            with SCPClient(self.sshClient.get_transport()) as scp:
                place = targetPath + data
                Log.info("Saving picture :%s" % (data))
                scp.put(saved, place)
        except Exception:
            Log.exception("SCP failure")
            return False
        return True           
    '''
      
    def loadPicture(self, member):
        self.db.ensureConnection()
        targetPath = SetUpTSVDB.PICPATH
        pic = member.picpath
        host = SetUpTSVDB.HOST
        reqUrl = "http://%s:5001/%s/%s" % (host, targetPath, pic)
        Log.debug("Load url:%s", reqUrl)
        try:
            pic = requests.get(reqUrl).content
        except:
            Log.error("Picture Server not present")
            return None
        return pic

    #used by member control
    def isValidAccess(self,mbr,cfgEntry):
        Log.info("Validation for:%d section:%s",mbr.id,cfgEntry.paySection)
        if cfgEntry.activity == TsvDBCreator.ACTIVITY_SAUNA:
            if mbr.currentAbo[0] is None:
                self.readAboData(mbr)
                if mbr.currentAbo[0] is None:
                    mbr.currentAbo=("Empty",0)
            Log.info("Abo data %s count %d",mbr.currentAbo[0],mbr.currentAbo[1])
            return mbr.currentAbo[0]==cfgEntry.paySection and mbr.currentAbo[1]>0
        # ÜL,KR in Group?
        return mbr.access in cfgEntry.groups
 
    def verifyRfid(self, rfidString, testId):
        # check if rfid  alreay exists ->False
        stmt = "SELECT id from " + self.dbSystem.MAINTABLE + " where uuid=" + rfidString
        res = self.db.select(stmt)
        if len(res) > 0:
            if res[0][0] == testId:
                return True  # it belongs to him..
            Log.warning("User %d already has RFID key:%s", res[0][0], rfidString)
            return False
        return True
    
    
class Mitglied():
    FIELD_DEF = ('id', 'first_name', 'last_name', 'access', 'birth_date', 'picpath', 'uuid', 'flag')
    FIELD_SAVE_DEF = ('id', 'first_name', 'last_name', 'access', 'picpath', 'uuid', 'flag')

    #                  id(int) (str) (str) (str) date!      int
    def __init__(self, mid_int, fn, ln, access, birthdate, rfid_int):  # id, firstname, lastname, DOB, access1, access2
        # special handling
        self.picpath = None
        self.flag = 0
        self.abo = (None, 0)  # TsvDBCrator SECTION, count (str,int)
        self.currentAbo = (None, 0)  # TsvDBCrator SECTION, count (str,int)  
        self.initalAccess = access
        self.initialRFID = rfid_int           
        self.update(mid_int, fn, ln, access, birthdate, rfid_int)
        
    def searchName(self):
        return self.lastName + " " + self.firstName

    def setFlag(self, aFlag):
        if aFlag is None:
            self.flag = 0
        else:
            self.flag = aFlag

    def update(self, mid_int, fn, ln, access, birthdate, rfid_int):
        self.id = mid_int  # This is int
        self.firstName = fn
        self.lastName = ln
        self.access = access
        self.birthdate = birthdate  # This is a date
        self.rfid = rfid_int  # Must be int for faster search
    
    # TODO error; Wrong datatype if no saved and retireved.
    # Todo: no check if rfid is unique 
    def birthdayString(self):
        if self.birthdate is None:
            return ""
        return datetime.strftime(self.birthdate, '%d.%m.%Y')
    
    def asDBDate(self, stringDate):
        if len(stringDate) < 6:
            return None
        return datetime.strptime(stringDate, '%d.%m.%Y')
    
    def primKeyString(self):
        return str(self.id)

    def rfidString(self):
        if self.rfid:
            return str(self.rfid)
        return None
    
    # data to save, no birthday        
    def dataSaveArray(self):
        row = []
        inner = (self.id, self.firstName, self.lastName, self.access, self.picpath, self.rfid, self.flag)  # birthdate is read only
        row.append(inner)
        return row
    
    '''
    The Konfig table
    +-----------+-------------+-----------+----------------+--------------------+------------+
    | config_id | room        | activity  | paySection     | groups             | grace_time |
    +-----------+-------------+-----------+----------------+--------------------+------------+
    |         0 | Kraftraum   | Kraftraum | Fit & Fun      | ['KR','ÜL','UKR']  |        120 |
    |         1 | Spiegelsaal | GroupFitness| Fit & Fun    | [GROUP]            |       3600 |
    |         2 | Spiegelsaal | Spinning  | Leichtathletik | []                 |       3600 | < no control
    |         3 | Sauna       | Sauna     | Sauna          | []                 |       3600 | <Taged as prepaid
    +-----------+-------------+-----------+----------------+--------------------+------------+
    '''    
class Konfig():
    FIELD_DEF=["activity","paySection","groups","grace_time", "weekday","from_Time","to_Time","room"]
    def __init__(self,rows):
        self.configs=[]
        for row in rows:
            self.configs.append(KonfigEntry(row))
    
    def entryAt(self,indx):
        return self.configs[indx]   
    
    def allActivities(self):
        return set([c.activity for c in self.configs])
    
    '''
    def configEntryByActivity(self,cfgName):
        return next((c for c in self.configs if c.activity==cfgName),None)
    '''
    
    def allPaySections(self):
        return set([c.paySection for c in self.configs])
    
    
    def configForUserGroup(self,group):
        return next((c for c in self.configs if group in c.groups and c.isValidInTime()),None) 
    
            
class KonfigEntry():
    def __init__(self,row):
        self.activity=row[0]
        self.paySection=row[1]
        self.groups=literal_eval(row[2])   
        self.graceTime=row[3] #int
        self.weekday=row[4] #int 0=Monday, 6=Sunday
        self.startTime=self.__toTime(row[5]) #timedelta to time
        self.endTime=self.__toTime(row[6])#timedelta to time
        self.room=row[7]

    def __toTime(self,td):
        if td is None:
            return None
        if td.days == 1: #only 24h=0:0 - just to make sure
            td=td-timedelta(seconds=1)
        return (datetime.min+td).time()
    
    def isValidInTime(self):
        now=datetime.now()
        currTime=now.time()

        if self.weekday:
            if now.weekday()!= self.weekday: #Mon=0, Sun=6
                print("wrong weekday:",self.weekday)
                return False
        
        if not self.startTime or not self.endTime:
            return True

        print("test:",currTime," start:",self.startTime," end:",self.endTime)     
        return currTime >= self.startTime and currTime <= self.endTime

if __name__ == '__main__':
    pass
