'''
Created on Apr 1, 2023
Generates the basic structure of a TSV database
@author: matze
security
pip3 install python-dotenv
from dotenv import load_dotenv
import os 

load_dotenv()
print(os.environ.get('secretUser'))
print(os.environ.get('secretKey'))
print(os.environ.get('secretHost'))
'''

import DBTools
from DBTools import Connector, OSTools
import csv,re,socket
from datetime import datetime,timedelta
import json, getopt, sys
from enum import Enum
import traceback
from collections import Counter
import smtplib,ssl
from email.message import EmailMessage
from ast import literal_eval

# codes found on migration
ACCESSCODES = ["GROUP","ÜL","FFA","KR","JUGGLING","UKR"]

# Allowed access rooms: Display only
LOC_KRAFTRAUM = "Kraftraum"
LOC_SPIEGELSAAL="Spiegelsaal"
LOC_MZR="MZR"
LOC_SAUNA="Sauna"
LOC_NORD="HalleNord"
LOC_DOJO="Dojo"

ALL_LOCATIONS=[LOC_KRAFTRAUM,LOC_SPIEGELSAAL,LOC_MZR,LOC_NORD,LOC_SAUNA,LOC_DOJO]

#Use for Zugangstable & Auswertung  
ACTIVITY_KR="Kraftraum"
ACTIVITY_GYM = "GroupFitnesse"
ACTIVITY_SPINNING="Spinning"
#ACTIVITY_TRAMPO="Trompoline"
ACTIVITY_SAUNA="Sauna"


#these are currently possible sections: 
#Counter({'Hauptverein': 4420, 'Turnen': 1438, 'Fit & Fun': 1392, 'Handball': 528, 'Basketball': 431, 'Aufnahmegebühr': 428, 'Leichtathletik': 401, 'Fußball': 356, 'Schwimmen': 300, 'Volleyball': 293, 'Kindersport': 263, 'Tanzsport': 243, 'Skisport': 217, 'Ju-Jutsu': 164, 'Aikido': 151, 'Tischtennis': 145, 'Judo': 132, 'Ringen': 98, 'Taekwondo': 89, 'Badminton': 86, 'Rugby': 79, 'Fechten': 63, 'Rock`n`Roll': 62, 'Kegeln': 39, 'Kyudo': 22, 'Kurs': 7, 'Behind,Versehrte': 4})
##Allowed "Beitrags" sections
SECTION_FIT='Fit & Fun'
SECTION_LA='Leichtathletik'
#SECTION_KURS='Kurs' ??
SECTION_SAUNA="Sauna" #for prepaid
PREPAID_INDICATOR=[SECTION_SAUNA]  



'''
The payment section
+-------------+---------------------+------------------+---------+
| mitglied_id | payuntil_date       | section          | prepaid |
+-------------+---------------------+------------------+---------+
|         211 | 2014-12-31 00:00:00 | Turnen           |       0 |
|         211 | 2020-12-31 00:00:00 | Skisport         |       0 |
|         225 | 2020-12-31 00:00:00 | Fit & Fun        |       0 |
|       18908 | NULL                | Sauna            |       9 |
+-------------+---------------------+------------------+---------+

will be defined per device via Location and Konfig:
+------------+-----------+
| host_name  | config_id |
+------------+-----------+
| msi        |         0 |
| tsvaccess1 |         0 |
| tsvaccess2 |         3 |
+------------+-----------+
The Konfig table
+-----------+-------------+-----------+----------------+--------------------+------------+
| config_id | room        | activity  | paySection     | groups             | grace_time |
+-----------+-------------+-----------+----------------+--------------------+------------+
|         0 | Kraftraum   | Kraftraum | Fit & Fun      | ['KR','ÜL','UKR']  |        120 |
|         1 | Spiegelsaal | GroupFitness| Fit & Fun    | [GROUP]            |       3600 |
|         2 | Spiegelsaal | Spinning  | Leichtathletik | []                 |       3600 | < no control
|         3 | Sauna       | Sauna     | Sauna          | []                 |       3600 | <Taged as prepaid
+-----------+-------------+-----------+----------------+--------------------+------------+
room: GUI 
activity: This col will be written into the Zugang Table (TsvAccess and TsvAuswertung
So configs can be dedicated to serveral (access)clients
paysection: Where you check if payment is ok. 
If paysection is Sauna: count down own "prepaid" in Beitrag   
To add 10 "points" into ABO (== Sauna) execute:
insert into BEITRAG (mitglied_id, payuntil_date, section, prepaid) values(18908,NULL,"Sauna",10); ->use the insertMany!
'''

#Profile conplan   
#﻿Adressnummer Geschlecht Nachname Vorname Multifeld 3 AustrittsDatum GebDatum BeitragBis Abteilungsname
#TODO deprecated    
class Fields(Enum):
    ID = 0
    GENDER = 1
    NAME = 2
    VORNAME = 3
    ACCESS = 4
    EOLDATE = 5 #not relevant
    BDATE = 6
    SECDATE=7
    SECTION=8

'''
class GROUPS(Enum):
    Group = 0
    ÜL = 1
    FFA = 2
    KR = 3
    Juggling = 4
    UKR =5
'''

class SetUpTSVDB():
    path = OSTools.getLocalPath(__file__)
    cfg = OSTools.joinPathes(path, "data", ".config.json")
    with open(cfg, "r") as jr:
        dic = json.load(jr)
        HOST = dic["HOST"]
        DATABASE = dic["DB"]
        USER = dic["USER"]             
        PASSWORD = dic["PASSWORD"]    
        #---------- RegisterModule only -----------
        PICPATH = dic.get("PICPATH",None)
        
    MAINTABLE ="Mitglieder"
    TABLE1 = """
    CREATE OR REPLACE TABLE Mitglieder (
      id INT PRIMARY KEY,
      first_name VARCHAR(100),
      last_name VARCHAR(100),
      access VARCHAR(100),
      gender VARCHAR(1),
      birth_date DATETIME,
      picpath VARCHAR(100),
      uuid INT UNSIGNED,
      flag SMALLINT UNSIGNED DEFAULT 0
      )
    """

    TIMETABLE="Zugang"   
    #Extended: ALTER TABLE Zugang ADD room varchar(50) NOT NULL DEFAULT "Kraftraum";
    #Extended: ALTER TABLE Zugang CHANGE location activity VARCHAR(100) NOT NULL;
    TABLE2 = """
        CREATE OR REPLACE TABLE Zugang (
          mitglied_id INT,
          access_date DATETIME,
          activity VARCHAR(100),
          room VARCHAR(50),
          FOREIGN KEY(mitglied_id) REFERENCES Mitglieder(id) ON DELETE CASCADE
        )
        """
    BEITRAGTABLE="BEITRAG"
    TABLE3="""
        CREATE OR REPLACE TABLE BEITRAG (
          mitglied_id INT NOT NULL,
          payuntil_date DATETIME,
          section VARCHAR(100) NOT NULL,
          prepaid SMALLINT UNSIGNED DEFAULT 0,
          FOREIGN KEY(mitglied_id) REFERENCES Mitglieder(id) ON DELETE CASCADE,
          CONSTRAINT PK_BEITRAG PRIMARY KEY(mitglied_id,section)
        )
    """        

    LOCATIONTABLE="Location"
    #host at a room (Kraftraum,Spiegelsaal,Sauna) with activity(=Fit&Fun,Kurs,Sauna?)>part of Section? und groups=(KR;ÜL,UKR)
    #host connected with exactly one configuration 
    TABLE4 = """
        CREATE OR REPLACE TABLE Location (
        id TINYINT UNSIGNED PRIMARY KEY,
        host_name VARCHAR(50),
        config TINYINT
     )   
    """
    CONFIGTABLE="Konfig"
    TABLE5="""
        CREATE OR REPLACE TABLE Konfig (
        config_id TINYINT PRIMARY KEY,  
        room VARCHAR(50),
        activity VARCHAR(50),
        paySection VARCHAR(50),
        groups VARCHAR(150),
        grace_time SMALLINT UNSIGNED,
        weekday TINYINT,
        from_Time TIME,
        to_Time TIME
        )
    """
    
    ASSAABLOY="AssaAbloy"
    TABLE6 ="""
    CREATE OR REPLACE TABLE AssaAbloy (
       uuid VARCHAR(50) PRIMARY KEY,
       remark VARCHAR(50)
    )
    """    

    MAILTABLE="MailConfig"
    TABLE7 ="""
    CREATE OR REPLACE TABLE MailConfig (
       server VARCHAR(50),
       port SMALLINT UNSIGNED,
       sender VARCHAR(50),
       passwd VARCHAR(50),
       mailTo VARCHAR(50),
       mailErr VARCHAR(50),
       addText VARCHAR(150)
    )
    """    
    #will be set whenever a "new" token has been issued - just for Abrechnung
    REGISTERTABLE="RegisterList"
    TABLE8="""
    CREATE OR REPLACE TABLE RegisterList (
       register_date DATETIME,
       mitglied_id INT
    )   
    """
    #overview for abos
    ABOTABLE="AboList"
    TABLE9= """
    CREATE OR REPLACE TABLE AboList (
      mitglied_id INT NOT NULL,
      buy_date DATETIME,
      section VARCHAR(100)
    )
    """
    
    #select per month: 
    #SELECT * from RegisterList where month(register_date)=9; (September)
    
    ######
    # HOOK
    #ALTER TABLE could add a column, while replace does not !
    #alter table mitglieder add column hugox smallint unsinged (or whatever) default xyz;
    ######
    
    
    def __init__(self, dbName):
        self.databaseName=dbName
        self.log = DBTools.Log
        self.connectToDatabase(dbName)
        
        
    def connectToDatabase(self, dbName):
        try:
            self.db = Connector(self.HOST, self.USER, self.PASSWORD)
            self.db.connect(dbName)
        except Connector.DBError as sqlError:
            self.db = None
            self.log.warning(sqlError)

    def isConnected(self):
        return self.db.isConnected()

    def resetDatabase(self):
        try:
            self.db.dropDatabase(self.DATABASE)
        except:
            self.log.warning("No reset - new DB?")
        self.db.close()
    
    def setupDatabase(self):
        self.db.createDatabase(self.DATABASE)
        self.db.close()
        self.db.connect(self.DATABASE)
        self.defineDatabases()

    def defineDatabases(self): 
        self.db.createTable(self.TABLE1)
        self.db.createTable(self.TABLE2)
        self.db.createTable(self.TABLE3)
        self.db.createTable(self.TABLE4)
        self.db.createTable(self.TABLE5)
        self.db.createTable(self.TABLE6)
        self.db.createTable(self.TABLE7)
        self.db.createTable(self.TABLE8)
        self.db.close()        

    def DEPRECATED_fillLocationTable(self):
        #list the correlations:
        #select host_name,room,activity,paySection,groups from Location loc JOIN Konfig conf where loc.config_id=conf.config_id;
        #TODO update: one room can have 2 activities at the same time. Table needs -weekday -start-end... 
        #No start-end at location = always
        #At a location we may have many activities 
        #modeshared=TsvAccess starts daemon. Replace with time schedule! So Locationtable may have more than one config! 
        self.db.createTable(self.TABLE4)
        self.db.createTable(self.TABLE5)
                
        table=self.CONFIGTABLE
        fields = ('config_id', 'room', 'activity',"paySection","groups", "grace_time","mode")
        entries=[]
        entries.append((0,LOC_KRAFTRAUM,ACTIVITY_KR,SECTION_FIT, "['KR','ÜL','FFA']",900,0))
        entries.append((1,LOC_SPIEGELSAAL,ACTIVITY_GYM,SECTION_FIT, "['KR','ÜL','FFA','GROUP']",3600,0))
        entries.append((2,LOC_NORD,ACTIVITY_GYM,SECTION_FIT, "['KR','ÜL','FFA','GROUP']",3600,0))
        entries.append((3,LOC_SAUNA,ACTIVITY_SAUNA,SECTION_SAUNA,"[]",3600*4,0)) #Login every 4 hours, no logout
        self.db.insertMany(table, fields, entries)
        
        table = self.LOCATIONTABLE
        fields = ('host_name', 'config_id')
        entries=[]
        entries.append(("tsvaccess1",0))
        entries.append(("tsvaccess2",3))
        entries.append(("tsvaccess3",1))
        entries.append(("tsvaccess4",2))
        entries.append(("msi",0))
        self.db.insertMany(table, fields, entries)     
    
    
    def _fillLocationTable(self):
        #list the correlations:
        #select host_name,room,activity,paySection,groups from Location loc JOIN Konfig conf where loc.config_id=conf.config_id;
        #No start-end at location = always
        #At a location we may have multi activities 
        # 0=Montag,1=Dienstag,2=Mittwoch,3=Donnerstag,4=Freitag,5=Samstag,6=Sonntag
        self.db.createTable(self.TABLE4)
        self.db.createTable(self.TABLE5)
                
        table=self.CONFIGTABLE
        fields = ('config_id', 'room', 'activity',"paySection","groups", "grace_time","weekday","from_Time", "to_Time")
        entries=[]
        entries.append((0,LOC_KRAFTRAUM,ACTIVITY_KR,SECTION_FIT, "['KR','ÜL','FFA']",900,None,None,None))
        entries.append((1,LOC_KRAFTRAUM,ACTIVITY_GYM,SECTION_FIT, "['KR','ÜL','FFA','GROUP']",7200,0,"08:45:00","09:30:00"))
        entries.append((2,LOC_KRAFTRAUM,ACTIVITY_GYM,SECTION_FIT, "['KR','ÜL','FFA','GROUP']",7200,3,"08:45:00","09:30:00"))
        entries.append((3,LOC_NORD,ACTIVITY_GYM,SECTION_FIT, "['KR','ÜL','FFA','GROUP']",7200,None,None,None))
        entries.append((4,LOC_SPIEGELSAAL,ACTIVITY_GYM,SECTION_FIT, "['KR','ÜL','FFA','GROUP']",7200,None,None,None))
        entries.append((5,LOC_DOJO,ACTIVITY_GYM,SECTION_FIT, "['KR','ÜL','FFA','GROUP']",7200,None,None,None))
        entries.append((6,LOC_SAUNA,ACTIVITY_SAUNA,SECTION_SAUNA,"[]",3600*4,None,None,None)) #Login every 4 hours, no logout
        entries.append((7,"TEST",ACTIVITY_GYM,SECTION_FIT, "['KR','ÜL','FFA','GROUP']",120,5,"19:00:00","23:59:59"))
        self.db.insertMany(table, fields, entries)
        
        table = self.LOCATIONTABLE
        fields = ('id','host_name', 'config')
        entries=[]
        entries.append((1,"tsvaccess1",0)) #KR
        entries.append((2,"tsvaccess1",1)) #KR Group MO
        entries.append((3,"tsvaccess1",2)) #KR Group DO
        entries.append((4,"tsvaccess2",6)) #Sauna 
        entries.append((5,"tsvaccess3",3)) #Nord
        entries.append((6,"tsvaccess4",4)) #Spiegelsaal
        entries.append((7,"tsvaccess5",5)) #Dojo
        entries.append((8,"tsvaccess6",7)) #Pending
        #entries.append((9,"msi",0))
        #entries.append((10,"msi",7))
        self.db.insertMany(table, fields, entries)  
        print(" Accesspoints need to be restarted after update !")
    
    
    def _fillMailTable(self):
        self.db.createTable(self.TABLE7)
        
        path = OSTools.getLocalPath(__file__)
        cfg = OSTools.joinPathes(path, "data", "mail.json")
        with open(cfg, "r") as jr:
            dic = json.load(jr)
            server=dic["MAILSERVER"]
            port=dic["MAILPORT"]
            passwd=dic["MAILPWD"]
            mailTo=dic["MAILTO"]
            mailErr=dic["MAILERROR"]
            sender=dic["MAILSENDER"]
            
        fields=('server','port','sender','passwd','mailTo','mailErr','addText')
        data=[(server,port,sender,passwd,mailTo,mailErr,"TSV Access")]    
        table=self.MAILTABLE
        self.db.insertMany(table, fields, data)
        
        
    def updateDatabase(self,tsvMembers):
        self.updateMembers()
        self._fillLocationTable()
        self._fillMailTable()
        self.close()

    def updateMembers(self,tsvMembers):
        table = self.MAINTABLE
        fields = ('id', 'first_name', 'last_name', "access", "gender", "birth_date")
        main=[]
        sections=[]
        for mbr in tsvMembers:
            main.append(mbr.baseData)
            sections.extend(mbr.sectionData())
        self.db.insertMany(table, fields, main)

        fields=("mitglied_id", "payuntil_date","section")
        table=self.BEITRAGTABLE
        self.db.insertMany(table, fields, sections)
                


    def close(self):
        if self.db:
            self.db.close()


    def sendEmail(self,subject,isMsg,messageText):
        stmt="select * from %s"%(self.MAILTABLE)
        rows = self.db.select(stmt)
        #'server'0,'port'1,'sender'2,'passwd'3,'mailTo'4,'mailErr'5,'addText'6)
        if len(rows)==0:
            self.log.warning("No mail config - aborting")
            return
        data=rows[0]
        smtp_server = data[0]
        port = data[1]
        sender=data[2]
        password =data[3] 
        if isMsg:
            to=data[4]
            origin=""
        else:
            to=data[5]
            origin=socket.gethostname()
            
        footer=data[6]
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = to
        fn=to.split('.')[0]
        fullMessage="Griasdi %s,\n\n%s\n%s\n%s"%(fn,messageText,origin,footer)
        
        msg.set_content(fullMessage)
        try:
            context = ssl.create_default_context()  
            with smtplib.SMTP(smtp_server, port) as server:
                server.starttls(context=context)
                server.login(sender, password)
                server.send_message(msg) 
        except:
            DBTools.Log.error("Mail could not be sent!")

def basicSetup():
    s = SetUpTSVDB(SetUpTSVDB.DATABASE)
    s.resetDatabase()
    s.db.connect("")
    s.setupDatabase()    

def updateScheme():
    s = SetUpTSVDB(SetUpTSVDB.DATABASE)
    s.defineDatabases()

def displayImportFindings(sections, multiSet, mbrCount,rogue):
    print("Imported %d members" % (mbrCount))
    print ("Multi Field:")
    for key, cnt in multiSet.items():
        print(key + ":", cnt)
    print("Sections:",Counter(sections))
    print("Those do not have Hauptverein entries:\n %s"%(rogue))
        

def importCSV(filename):
    # Profile TSVAccess -> NAch adressdaten suchen Dialog!
    # Adressdaten,Geschlecht,Nachname,Vorname,Mutli3,Austrittsdatum,GebDatum,BeitragBis,Abteilungg  
    # validate
    # filename="/home/matze/git/TSVAccess/ExportTSV.csv"
    data = {} #dic of id-> TsvMember
    multiSet = {}
    sections=[]
    rogue=[]
    mbrCount=0    
    with open(filename, encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile, delimiter='$', quotechar='|')
        for line in reader:
            # print(line)
            isHeader = "Vorname" in line
            if isHeader:
                continue
            conplanID=line[Fields.ID.value]
            mbr = data.get(conplanID,None)
            if not mbr:
                fn = line[Fields.VORNAME.value]
                nn = line[Fields.NAME.value]
                access = ''
                zugang = line[Fields.ACCESS.value].split(' ')
                if len(zugang) >= 1:
                    access = zugang[0].upper()
            
                tmpGender = line[Fields.GENDER.value]
                if tmpGender.startswith("w"):
                    gender = "F"
                else:
                    gender = "M"
                
                tmpDate = line[Fields.BDATE.value]
                if len(tmpDate) > 0:
                    birthdate = datetime.strptime(tmpDate, '%d.%m.%Y').date().isoformat()
                else:
                    birthdate = None

                if multiSet.get(access, None) is None:
                    multiSet[access] = 1
                else:
                    multiSet[access] += 1
                #cpid,fn,ln,access,gender,birthdate
                mbr=TsvMember(conplanID,fn,nn,access,gender,birthdate)
                data[conplanID]=mbr
                mbrCount += 1
                
            #--done -now the section data
            tmpDate=line[Fields.SECDATE.value]
            if len(tmpDate) > 0:
                payDate = datetime.strptime(tmpDate, '%d.%m.%Y').date().isoformat()
            else:
                payDate= TsvMember.PAYOK
                
            section= line[Fields.SECTION.value] #not empty
            mbr.addPay(payDate,section)                
            
    for entry in data.values():
        #entry.display()
        xxxsec=entry.sections()
        sections.extend(xxxsec)
        if "Hauptverein" not in xxxsec:
            rogue.append((entry.getID(),entry.getName()))
        
    displayImportFindings(sections,multiSet, mbrCount,rogue) 
    return list(data.values()) #array of TsvMembers        
    

def updateAssaAbloy(filename):
    #filename="/home/matze/Documents/TSV/AssaAbloy/Tranponder1.txt"
    '''
    Text is created with:
    pdfgrep Valid SCALA-transponders.pdf >Tranponder1.txt
    pdfgrep Blocked SCALA-transponders.pdf >>Tranponder1.txt
    '''
    s = SetUpTSVDB(SetUpTSVDB.DATABASE)
    blocked=[]
    active=[]
    final=[]
    with open(filename,'r', encoding='utf-8') as file:
        data=file.readlines()
        for line in data:
            token2 = "$".join(re.split("\s+", line.strip(), flags=re.UNICODE))
            token=token2.split("$")
            if token[0]=='Valid':
                val=token[1][:8].replace('ﬀ',"ff")
                active.append(val)
                rfid=_convertMSB(val)#str
                print(">%s = %d"%(val,rfid))
                final.append((str(rfid),val))
            else:
                blocked.append(token[1])

    fields=('uuid','remark')
    s.db.createTable(SetUpTSVDB.TABLE6)
    s.db.insertMany(SetUpTSVDB.ASSAABLOY, fields, final)
    s.close()                     
    print("Detected %d valid and %d blocked"%(len(active),len(blocked)))
    for x in blocked:
        if x in active:
            print("Blocked & active:%s"%(x))


def _convertMSB(hexStr):
    if not hexStr:
        return 0
    tmpBytes=bytes.fromhex(hexStr)
    tmp=bytearray(tmpBytes)
    tmp.reverse()
    return int.from_bytes(tmp)

class TsvMember():
    PAYOK="-"
    def __init__(self,cpid,fn,ln,access,gender,birthdate):
        self.baseData=(cpid,fn,ln,access,gender,birthdate)
        self.payData={} # section-> paydate. output must be array of tuple(secion,paydate)
    
    def getID(self):
        return self.baseData[0]
    
    def getName(self):        
        return self.baseData[2]
    
    def getAccess(self):
        return self.baseData[3]

    #if that section is already there and with empty pay - it it invalid - latest pay counts, empty rules
    def addPay(self,payDate,section):
        pd = self.payData.get(section,None)
        if not pd:
            self.payData[section]=payDate
            return
        #tricky
        if pd == TsvMember.PAYOK:
            return #payok rules
        
        if pd < payDate:
            self.payData[section]=payDate            
    
    def sectionData(self):
        data=[]
        for key,pd in self.payData.items():
            if pd == TsvMember.PAYOK:
                pd=None 
            data.append((self.getID(),pd,key))
        return data
     
     
    def sections(self):
        return self.payData.keys()    
    
    def display(self):
        print(self.baseData,">",self.payData)    
    
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
    FIELD_DEF=["activity","paySection","groups","grace_time", "weekday","from_Time","to_Time","room","config_id"]

    @classmethod
    def asDBString(cls,aSet):
        return ','.join(map(("'{0}'").format,aSet))
    
    def __init__(self,rows):
        self.configs=[]
        for row in rows:
            self.configs.append(KonfigEntry(row))
            print("KonfigList:",row)
    
    def entryAt(self,indx):
        print("retrun konfig at:",indx)
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
        return next((c for c in self.configs if c.isValidForGroup(group) and c.isValidInTime()),None) 
    

    
            
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
        self.id=row[8]#int

    def __toTime(self,td):
        if td is None:
            return None
        if td.days == 1: #only 24h=0:0 - just to make sure
            td=td-timedelta(seconds=1)
        return (datetime.min+td).time()
    
    def isValidForGroup(self,aGroup):
        if len(self.groups)==0:
            return True
        return aGroup in self.groups
    
    def isValidInTime(self):
        now=datetime.now()
        currTime=now.time()

        if self.weekday:
            if now.weekday()!= self.weekday: #Mon=0, Sun=6
                print("wrong weekday:",self.weekday)
                return False
        
        if not self.startTime or not self.endTime:
            return True
        return currTime >= self.startTime and currTime <= self.endTime


#TODO if we get only members ,remove those who are  in the database but not in the list...    
def persistCSV(fn):
    OSTools.setLogLevel("Debug")
    s = SetUpTSVDB("TsvDB")
    try:
        data = importCSV(fn)
        #todo a.symmetric_difference(b) - two sets of ids! (not arrays)
        lostMembers=symDiff(data, s)
        for pk in lostMembers:
            #we should flag it. Otherwise the accessdata is gone
            #s.db.deleteEntry(SetUpTSVDB.MAINTABLE, "id", pk)
            stmt="UPDATE Mitglieder set flag=1 where id=%d"%(pk)
            s.db.select(stmt)
        s.updateDatabase(data)
    except Exception:
        traceback.print_exc()
    finally:
        s.close()

def symDiff(importData,connection):
    stmt="select id from %s"%(SetUpTSVDB.MAINTABLE)
    rows=connection.db.select(stmt)
    ids = [data[0] for data in rows] #int
    currIds=[int(mbr.getID()) for mbr in importData]
    diff=[]
    for indb in ids:
        if not indb in currIds:
            print("!Member lost:%d -will be flagged!"%(indb))
            diff.append(indb)     
    #the other way:
    for cid in currIds:
        if not cid in ids:
            print("New Member:%d"%(cid))
    return diff


def updateLocationTable():
    s = SetUpTSVDB("TsvDB")
    try:
        s._fillLocationTable()
    except Exception:
        traceback.print_exc()
    finally:
        s.close()
#TODO switchLocation(host,loctableID)    

def updateMailTable():
    s = SetUpTSVDB("TsvDB")
    try:
        s._fillMailTable()
    except Exception:
        traceback.print_exc()
    finally:
        s.close()
    
def parseOptions(args):
    
    try:
        opts, args = getopt.getopt(args[1:], "p:v:rlmst:", ["persist=", "verify=", "reset", "updateLocation", "updateMail" "updateScheme","transponder"])
        if len(opts) == 0:
            printUsage()
    except getopt.GetoptError as err:
        printUsage()
        sys.exit(2)
    
    for o, a in opts:
        if o in ("-r", "--reset"):
            basicSetup()
        elif o in ("-p", "--persist"):
            persistCSV(a)
        elif o in ("-v", "--verify"):
            importCSV(a)
        elif o in ("-l", "--updateLocation"):
            updateLocationTable()
        elif o in ("-m", "--updateMail"):
            updateMailTable()            
        elif o in ("-s", "--updateScheme"):
            updateScheme() #Removes data from Zutritt and Beitrag! 
        elif o in ("-t", "--transponder"):
            updateAssaAbloy(a)
        else:
            printUsage()

def printUsage():
    print("Creator commands: \n"\
          "\t-p filename > verify & persist a csv file (--persist)\n"\
          "\t-v filename > verify csv file and check for inconsistencies (--verify)\n"\
          "\t-r > !reset the database! (--reset) \n"\
          "\t-l > update location (--updateLocation) \n"\
          "\t-s > !update the database! (--updateScheme) \n"
          "\t-t filename > read transponder (--transponder) \n"
          )
    

if __name__ == '__main__':
    sys.exit(parseOptions(sys.argv))
