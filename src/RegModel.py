'''
Created on Nov 21, 2023

@author: matze
'''
import TsvDBCreator
from TsvDBCreator import SetUpTSVDB, Konfig, DBAccess
import DBTools
from datetime import datetime,date
import requests

Log = DBTools.Log

'''
We need controllers for mode register (you search for names and have a camera)
and mode rfid (you have a registered user and search it with the rfid token)
'''

#Registr new. Do not allow Abo change, only 10er tickets
class RegisterController():

    def __init__(self, ui):
        self.mainFrame = ui
        self.allowsAboCarryover=False

    def handleRFIDChanged(self, str_RFID):
        self.mainFrame.verifyRFID(str_RFID)

    def supportsCamera(self):
        return True

    def setInitialFocus(self):
        self.mainFrame.ui_SearchEdit.setFocus()
        # self.mainFrame.ui_SearchEdit.setStyleSheet("QComboBox,QComboBox::editable { background: rgb(0,160,0); color:white}");
        self.mainFrame.ui_SearchEdit.setStyleSheet("QComboBox { padding: 2px; border-radius: 4px; border: 2px solid rgb(0,160,0);}");

    def mainTitle(self):
        return "Registrierung für TSV Mitglieder"
    
    def getAppIcon(self):
        return './web/static/tsv_logo_100.png'

#Bearbeitung && Abo Control
class RFIDController(RegisterController):

    def __init__(self, ui):
        RegisterController.__init__(self, ui)  
        self.allowsAboCarryover=True      

    # slot if rfid search is active (mode)
    def handleRFIDChanged(self, str_RFID):
        # String may have a leading zero.
        try:
            tmp = int(str_RFID)
        except:
            self.mainFrame.searchWithRFID(str_RFID)
            return
        clean = str(tmp)
        self.mainFrame.searchWithRFID(clean)

    def supportsCamera(self):
        return False

    def setInitialFocus(self):
        self.mainFrame.ui_RFID.setFocus()
        # self.mainFrame.ui_RFID.setStyleSheet("QLineEdit { background: rgb(0,160,0); color:white}");
        self.mainFrame.ui_RFID.setStyleSheet("QLineEdit {padding: 2px; border-radius: 4px; border: 2px solid rgb(0,160,0); }");

    def mainTitle(self):
        return "Bearbeitung/Suche TSV Mitglieder"
    
    def getAppIcon(self):
        return './web/static/TSV-check.png'

class Registration():
    SAVEPIC = "/tmp/tsv.screenshot.png"   
    NOT_FOUND="Picture not found"
    CHECKABLE_ACTIVITY=[TsvDBCreator.LOC_KRAFTRAUM] #only these activities need a checkout!

    def __init__(self):
        # self.accesscodes = []
        self.borders = []
        self.aaTransponders = []
        self.memberList = None
        self.configs = None  # a Konfig instance containing KonfigEntry 

    def connect(self):
        self.dbSystem = DBAccess() 
        self.db = self.dbSystem.connectToDatabase()
        if self.dbSystem.isConnected(self.db):
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
    
    # Membercontrol
    def readConfigurations(self):
        fields = ','.join(Konfig.FIELD_DEF)
        stmt = "SELECT " + fields + " from " + SetUpTSVDB.CONFIGTABLE
        res = self.db.select(stmt)
        return Konfig(res)
    
    def containsLegacyAA(self, rfid):
        return rfid in self.aaTransponders
    
    # reads the list and passes it to the caller...
    def getMembers(self):
        fields = ','.join(Mitglied.FIELD_DEF)  # FIELD_DEF=('id','first_name','last_name','access','birth_date,picpath,uuid,flag') 
        # stmt = "SELECT id,first_name,last_name from " + self.dbSystem.MAINTABLE
        stmt = "SELECT " + fields + " from " + SetUpTSVDB.MAINTABLE
        self.memberList = []
        res = self.db.select(stmt)
        for titem in res:
            # id(int) (str) (str) (str) date! int
            m = Mitglied(titem[0], titem[1], titem[2], titem[3], titem[4], titem[6])
            m.picpath = titem[5]
            m.setFlag(titem[7])
            self.memberList.append(m)
        return self.memberList
    
    # used by memberControl
    def todaysAccessDateStrings(self, mbrID, activity,room):
        table = SetUpTSVDB.TIMETABLE
        daysplit = "13:30:00"  # see TsvAuswertung
        stmt = "select access_date from %s where mitglied_id =%d and activity='%s' and room='%s' AND %s" % (table, mbrID, activity, room,TsvDBCreator.halfDayStatement("access_date",daysplit))
        rows = self.db.select(stmt)
        timeData = []
        for row in rows:
            timeData.append(datetime.strftime(row[0], ' %H:%M '))
        return timeData
    
    # kind of manual cki - MemberControl
    def saveAccessDate(self, mbr, accessDate, locConfig):
        table = SetUpTSVDB.TIMETABLE
        data = []
        data.append((mbr.id, accessDate, locConfig.activity, locConfig.room))
        self.db.insertMany(table, ('mitglied_id', 'access_date', 'activity', 'room'), data)
    
    def updateMember(self, mbr):
        table = SetUpTSVDB.MAINTABLE
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
            # TODO mit Link auf aktuelle Seite
            self.dbSystem.sendEmail(self.db,"Sauna Abo Daten", True, msg)
            self._insertAboData(mbr)
            
        self.db.insertMany(SetUpTSVDB.BEITRAGTABLE, fields, data)
        # TODO: data saved - so mbr.abo should be reset - can't we use a flag and add the stuff in dialog? 

    def _insertAboData(self, mbr):
        now = datetime.now().isoformat()
        fields = ('mitglied_id', 'buy_date', 'section')
        section = mbr.abo[0]
        data = [(mbr.id, now, section)]
        self.db.insertMany(SetUpTSVDB.ABOTABLE, fields, data)

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
        self.db.insertMany(SetUpTSVDB.BEITRAGTABLE, fields, data)
        mbr.initalAccess = mbr.access
     
    def updateRFIDAbrechnung(self, mbr):
        if mbr.initialRFID == mbr.rfid:
            return
        now = datetime.now().isoformat()
        data = []
        data.append((now, mbr.id, mbr.rfid))
        self.db.insertMany(SetUpTSVDB.REGISTERTABLE, ('register_date', 'mitglied_id', 'uuid'), data)
        if mbr.rfid is None:
            Log.info("Chip of member %d has been deleted",mbr.id)
        else:
            Log.info("Dispensing NEW Chip %d to member %d", mbr.rfid, mbr.id)
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
    
    def accessTypes(self):
        stmt = "select distinct access from %s" % (SetUpTSVDB.MAINTABLE)
        rows = self.db.select(stmt)
        return [access[0] for access in rows if len(access[0])>1]
    
    def mailError(self, msg):
        self.dbSystem.sendEmail(self.db,"Registration Error Msg", False, msg)
    
    # beware_ connection could be broken
    def savePicture(self, member):
        self.db.ensureConnection() 
        saved = Registration.SAVEPIC       
        targetPath = DBAccess.PICPATH
        pic = member.lastName + "-" + member.primKeyString() + ".png"
        
        host = DBAccess.HOST
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
        targetPath = DBAccess.PICPATH
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
        targetPath = DBAccess.PICPATH
        pic = member.picpath
        host = DBAccess.HOST
        #HTTPS: reqUrl = "https://%s:5001/%s/%s" % (host, targetPath, pic)
        reqUrl = "http://%s:5001/%s/%s" % (host, targetPath, pic)
        Log.debug("Load url:%s", reqUrl)
        try:
            req= requests.get(reqUrl,verify=False)
            code = req.status_code
            pic = req.content
            #https://de.wikipedia.org/wiki/HTTP-Statuscode#Liste_der_HTTP-Statuscodes
            if code >= 400:
                Log.error("Picture Server replies: %d",code)
                return self.NOT_FOUND
        except:
            Log.error("Picture Server not present")
            return None
        return pic

    # used by member control
    def isValidAboAccess(self, mbr, cfgEntry):
        Log.info("Validation for:%d section:%s", mbr.id, cfgEntry.paySection)
        if cfgEntry.activity == TsvDBCreator.ACTIVITY_SAUNA:
            if mbr.currentAbo[0] is None:
                self.readAboData(mbr)
                if mbr.currentAbo[0] is None:
                    mbr.currentAbo = ("Empty", 0)
            Log.info("Abo data %s count %d", mbr.currentAbo[0], mbr.currentAbo[1])
            if mbr.currentAbo[0] == cfgEntry.paySection and mbr.currentAbo[1] > 0:
                return (True,f"Abo: {mbr.currentAbo[1]}")
            else:
                return (False,"Keine Sauna Abo Punkte -Neu kaufen!")
        return (True,"OK")
    
    def haveFeesBeenPaid(self,mbr,paySections):
        #needs to be live! if not mbr.fees:
        payStr = Konfig.asDBString({paySections})
        stmt = MemberFees.STMT%(mbr.id,payStr)
        res = self.db.select(stmt)
        mbr.saveMemberFees(res)
        return self._checkValidFee(mbr, paySections)    
        
 
    def _checkValidFee(self,mbr,paysection):
        #Sauna has prepaid, not payuntil
        eolDate = mbr.fees.payUntilForSection(paysection)
        reason=[]
        if eolDate:
            now = date.today()
            if eolDate.date() < now:
                Log.warning("Member EOL")
                reason.append("Kein Beitrag")
        if mbr.fees.isBlocked(paysection):
            Log.warning("Member blocked")
            reason.append("Gesperrt!")

        if len(reason) == 0:
            return None
        mbr.fees.reason = ','.join(reason)
        return mbr.fees

 
    def verifyRfid(self, rfidString, testId):
        # check if rfid  alreay exists ->False
        stmt = "SELECT id from " + SetUpTSVDB.MAINTABLE + " where uuid=" + rfidString
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
        self.initalAccess = access  # KR,GROUP;ÜL etc
        self.initialRFID = rfid_int  # rfid token          
        self.update(mid_int, fn, ln, access, birthdate, rfid_int)
        self.fees=None
        
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
    
    def saveMemberFees(self,rows):
        self.fees=MemberFees(self,rows)
    
    # data to save, no birthday        
    def dataSaveArray(self):
        row = []
        inner = (self.id, self.firstName, self.lastName, self.access, self.picpath, self.rfid, self.flag)  # birthdate is read only
        row.append(inner)
        return row


# Will be created on demand
class MemberFees():
    STMT = "select section,payuntil_date,prepaid,flag from BEITRAG join Mitglieder on id = mitglied_id where id = '%s' and section in (%s)"
    #STMT = "select section,payuntil_date,prepaid from BEITRAG where mitglied_id='%s' and section in (%s)"

    def __init__(self, member, rows):
        self.member = member
        self.feeRows = {}  # section->payuntil,prepaid
        self._setupRows(rows)
        self.reason =""
        
    def payUntilForSection(self, sectionName):
        data = self.feeRows.get(sectionName, None)
        if data: 
            return data[0]
        return None
    
    #unused!
    def prepaidForSection(self, sectionName):
        data = self.feeRows.get(sectionName, None)
        if data: 
            return data[1]
        return None

    def isBlocked(self,sectionName):
        data = self.feeRows.get(sectionName, None)
        if data: 
            return data[2]==1
        return False

    def printReason(self):
        return self.reason;

    def _setupRows(self, rowList):
        for row in rowList:
            key = row[0]
            #paiduntil->0, prepaid->1, blocked->2
            data = row[1:]
            self.feeRows[key] = data
         
             
if __name__ == '__main__':
    pass
