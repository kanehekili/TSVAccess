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
from datetime import datetime
import json, getopt, sys
from enum import Enum
import traceback
from collections import Counter
import smtplib,ssl
from email.message import EmailMessage

# codes found on migration
ACCESSCODES = ["GROUP","ÜL","FFA","KR","JUGGLING","UKR"]

# Allowed access locations: Display only
LOC_KRAFTRAUM = "Kraftraum"
LOC_SPIEGELSAAL="Spiegelsaal"
LOC_MZR="MZR"
LOC_SAUNA="Sauna"
LOC_NORD="HalleNord"
LOC_DOJO="Dojo"

#Use for Zugangstable &   
ACTIVITY_KR="Kraftraum"
ACTIVITY_GYM = "Gym"
ACTIVITY_SPINNING="Spinning"
ACTIVITY_TRAMPO="Trompoline"
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

will be defined per device via location and Konfig:
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
|         1 | Spiegelsaal | Gym       | Fit & Fun      | [GROUP]            |       3600 |
|         2 | Spiegelsaal | Spinning  | Leichtathletik | []                 |       3600 | < no control
|         3 | Sauna       | Sauna     | Sauna          | []                 |       3600 | <Taged as prepaid
+-----------+-------------+-----------+----------------+--------------------+------------+
room: GUI 
activity: This col will be written into the Zugang Table (TsvAccess and TsvAuswertung
So configs can be dedicated to serveral (access)clients
paysection: Where you check if payment is ok. 
If paysection is abo: count down own "prepaid" in Beitrag   
To add 10 "points" into ABO (== Sauna) execute:
insert into BEITRAG (mitglied_id, payuntil_date, section, prepaid) values(18908,NULL,"Sauna",10); ->use the insertMany!
'''

#Profile conplan   
#﻿Adressnummer Geschlecht Nachname Vorname Multifeld 3 AustrittsDatum GebDatum BeitragBis Abteilungsname
    
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
    #TODO used ALTER TABLE to add a new column     
    TABLE2 = """
        CREATE OR REPLACE TABLE Zugang (
          mitglied_id INT,
          access_date DATETIME,
          location VARCHAR(100),
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
        host_name VARCHAR(50) PRIMARY KEY,
        config_id SMALLINT UNSIGNED
     )   
    """
    #mode: currently only SHARED: Shold check for alternating locations
    CONFIG_MODE_SHARED=1
    CONFIGTABLE="Konfig"
    TABLE5 ="""
        CREATE OR REPLACE TABLE Konfig (
        config_id INT PRIMARY KEY,  
        room VARCHAR(50),
        activity VARCHAR(50),
        paySection VARCHAR(50),
        groups VARCHAR(150),
        grace_time SMALLINT UNSIGNED,
        mode TINYINT UNSIGNED
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
       mitglied_id INT PRIMARY KEY,
       register_date DATETIME
    )   
    """
    
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

    def _fillLocationTable(self):
        #list the correlations:
        #select host_name,room,activity,paySection,groups from Location loc JOIN Konfig conf where loc.config_id=conf.config_id;
        # singel use: ... and loc.host_name="msi" (room is only for GUI!)
        self.db.createTable(self.TABLE4)
        self.db.createTable(self.TABLE5)
                
        table=self.CONFIGTABLE
        fields = ('config_id', 'room', 'activity',"paySection","groups", "grace_time","mode")
        entries=[]
        entries.append((0,LOC_KRAFTRAUM,ACTIVITY_KR,SECTION_FIT, "['KR','ÜL','UKR']",120,0))
        entries.append((1,LOC_SPIEGELSAAL,ACTIVITY_GYM,SECTION_FIT, "[GROUP]",3600,self.CONFIG_MODE_SHARED))
        entries.append((2,LOC_SPIEGELSAAL,ACTIVITY_SPINNING,SECTION_LA, "[]",3600,self.CONFIG_MODE_SHARED))
        entries.append((3,LOC_SAUNA,ACTIVITY_SAUNA,SECTION_SAUNA,"[]",3600*4,0)) #Login every 4 hours, no logout
        self.db.insertMany(table, fields, entries)
        
        table = self.LOCATIONTABLE
        fields = ('host_name', 'config_id')
        entries=[]
        entries.append(("tsvaccess1",0))
        entries.append(("tsvaccess2",3))
        entries.append(("msi",0))
        self.db.insertMany(table, fields, entries)     
    
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
        self._fillLocationTable()
        self._fillMailTable()
        self.close()


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
        entry.display()
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
