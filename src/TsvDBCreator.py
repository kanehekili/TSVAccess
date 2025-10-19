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
import re,socket
from datetime import datetime,timedelta
import json, getopt, sys
from enum import Enum
import traceback,mimetypes
import smtplib,ssl,struct
from email.message import EmailMessage
from ast import literal_eval
import csv

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
'''
collection of usable statements
'''
def halfDayStatement(dateField,daysplit):
    return f"""DATE({dateField}) = CURDATE() AND 
         ((TIME({dateField}) < '{daysplit}' AND CURTIME() <= '{daysplit}') 
         OR 
         (TIME({dateField}) >= '{daysplit}' AND CURTIME() >= '{daysplit}'))"""
    

'''
End of collection
'''


class DBAccess():
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
        
    def __init__(self):
        self.log = DBTools.Log

    def connectToDatabase(self):
        try:
            db = Connector(self.HOST, self.USER, self.PASSWORD)
            db.connect(self.DATABASE)
        except Connector.DBError as sqlError:
            db = None
            self.log.warning(sqlError)
        return db

    def isConnected(self,db):
        if db:
            return db.isConnected()
        return False

    def close(self,db):
        if db:
            db.close()

    def sendEmail(self,db,subject,isMsg,messageText):
        mailer = TSVMailer(db)
        if not mailer.isConnected:
            return
        if isMsg:
            to=mailer.defaultReceipient
            origin=""
        else:
            to=mailer.adminReceipient
            origin=socket.gethostname()

        fn=to.split('.')[0]
        fullMessage="Griasdi %s,\n\n%s\n%s\n%s"%(fn,messageText,origin,mailer.footer)
        sendTo=[to]
        mailer.sendEmail(sendTo, subject, fullMessage)
        
    def genericEmail(self,db,subject,text,recipientList,attachment=None ): #attachment: (ioBuffer, filename) 
        mailer = TSVMailer(db)
        if not mailer.isConnected:
            return
        mailer.sendEmail(recipientList, subject, text,attachment)

'''
Encoder class for converting datetime entries into json - example at Scrap.py
'''
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat() #ISO 8601: YYYY-MM-DDTHH:MM:SS
            # return obj.strftime("%Y-%m-%d %H:%M:%S") #individual alternative 
        return super().default(obj)
        
'''
Mailer for this project:
Reads connection data from a table in TSVDB
Writes text + footer (which is currently not used) 
Accepts attachments as io.BytesIO (aka image) plus filename as a tuple
'''        
class TSVMailer:
    def __init__(self,db):
        self.isConnected=False
        self._getCredentials(db)
        
    def _getCredentials(self,db):
        if not db:
            self.log.warning("Mail failure, no valid database")
            return
        stmt="select * from %s"%(SetUpTSVDB.MAILTABLE)
        rows = db.select(stmt)
        if len(rows)==0:
            self.log.warning("No mail config - aborting")
            return
        self.isConnected=True
        data=rows[0]
        self.smtp_server = data[0]
        self.port = data[1]
        self.sender=data[2]
        self.password =data[3]
        self.defaultReceipient=data[4]
        self.adminReceipient=data[5]
        self.footer=data[6]
               
    def sendEmail(self,recipientList,subject,text,attachment=None):
        to = ",".join(recipientList)
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = to
        
        msg.set_content(text)
        if attachment:
            buffer= attachment[0]
            buffer.seek(0)
            binaryData= buffer.read()
            # Guess MIME type or use 'application/octet-stream'
            maintype, _, subtype = (mimetypes.guess_type(attachment[1])[0] or 'application/octet-stream').partition("/")
            msg.add_attachment(binaryData,maintype=maintype, subtype=subtype, filename=attachment[1])
        DBTools.Log.info("Sending email to %s content:\n %s\n--------------------------------------------------------------",to, text)    
        try:
            context = ssl.create_default_context()  
            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.starttls(context=context)
                server.login(self.sender, self.password)
                server.send_message(msg) 
        except:
            DBTools.Log.error("Mail could not be sent! Server:%s port:%s from:%s pwd: %s ",self.smtp_server, self.port,self.sender,self.password)
        
                
#Definition and creation of TSV Tables. This class should not be instantiated in prod - just for creation or db manipulation
class SetUpTSVDB():
        
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
    #Extended: removed line: FOREIGN KEY(mitglied_id) REFERENCES Mitglieder(id) ON DELETE CASCADE
    #we want zugangs data keep forever - statistics... 
    ''' We need to alter the Zugang table, in order to delete members, but not their behaviour and counts
    1) SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS WHERE TABLE_NAME = 'Zugang' AND CONSTRAINT_TYPE = 'FOREIGN KEY';
    gets the contraint key : Zugang_ibfk_1
    2) ALTER TABLE Zugang DROP FOREIGN KEY Zugang_ibfk_1;  -- Replace with actual name
    '''    
    TABLE2 = """
        CREATE OR REPLACE TABLE Zugang (
          mitglied_id INT,
          access_date DATETIME,
          activity VARCHAR(100),
          room VARCHAR(50)
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
    
    OMOCTABLE="OmocConfig"
    TABLE11 = """
    CREATE OR REPLACE TABLE OmocConfig (
    id VARCHAR(50),
    token VARCHAR(50),
    passwd VARCHAR(50),
    url VARCHAR(100)
    )
    """
    
    #will be set whenever a "new" token has been issued - just for Abrechnung
    #Alter table RegisterList add uuid INT UNSIGNED NOT NULL DEFAULT 0;
    #fix zeros: update RegisterList r inner join Mitglieder m on r.mitglied_id = m.id set r.uuid=m.uuid where r.uuid=0;
    REGISTERTABLE="RegisterList"
    TABLE8="""
    CREATE OR REPLACE TABLE RegisterList (
       register_date DATETIME,
       mitglied_id INT,
       uuid INT UNSIGNED NOT NULL
    )   
    """
    #select per month: 
    #SELECT * from RegisterList where month(register_date)=9; (September)
    
    #overview for abos
    ABOTABLE="AboList"
    TABLE9= """
    CREATE OR REPLACE TABLE AboList (
      mitglied_id INT NOT NULL,
      buy_date DATETIME,
      section VARCHAR(100)
    )
    """

    KURSTABLE="Kurslist"
    TABLE10="""
    CREATE OR REPLACE TABLE Kurslist (
      kurs_id TINYINT PRIMARY KEY,
      display_Name VARCHAR(50) NOT NULL,
      paySection VARCHAR(50) NOT NULL,      
      activity VARCHAR(50) NOT NULL,
      room VARCHAR(50) NOT NULL,
      weekday TINYINT NOT NULL,
      from_Time TIME NOT NULL,
      to_Time TIME NOT NULL
    )    
    """
    
    ######
    # HOOK
    #ALTER TABLE could add a column, while replace does not !
    #alter table mitglieder add column hugox smallint unsinged (or whatever) default xyz;
    ######
    
    
    def __init__(self, dbAccess):
        self.dbAccess = dbAccess
        self.log = DBTools.Log
        self.db = self.dbAccess.connectToDatabase()
        
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
        self.db.createTable(self.TABLE9)
        self.db.createTable(self.TABLE10)
        self.db.close()        

    def _fillConfigTable(self):
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
        entries.append((0,LOC_KRAFTRAUM,ACTIVITY_KR,SECTION_FIT, "['KR','ÜL']",900,None,None,None))
        entries.append((1,LOC_KRAFTRAUM,ACTIVITY_GYM,SECTION_FIT, "['GROUP']",2700,0,"08:45:00","09:30:00"))
        entries.append((2,LOC_KRAFTRAUM,ACTIVITY_GYM,SECTION_FIT, "['GROUP']",2700,3,"08:45:00","09:30:00"))
        entries.append((3,LOC_NORD,ACTIVITY_GYM,SECTION_FIT, "['KR','ÜL','GROUP']",2700,None,None,None))
        entries.append((4,LOC_SPIEGELSAAL,ACTIVITY_GYM,SECTION_FIT, "['KR','ÜL','GROUP']",2700,None,None,None))
        entries.append((5,LOC_DOJO,ACTIVITY_GYM,SECTION_FIT, "['KR','ÜL','GROUP']",2700,None,None,None))
        entries.append((6,LOC_SAUNA,ACTIVITY_SAUNA,SECTION_SAUNA,"[]",14400*4,None,None,None)) #Login every 4 hours, no logout
        entries.append((7,LOC_KRAFTRAUM,ACTIVITY_KR,SECTION_FIT, "['SKR0','SKR03','SKR05','SKR035']",900,0,"15:15:00","17:45:00")) #add 15mins delta start/end
        entries.append((8,LOC_KRAFTRAUM,ACTIVITY_KR,SECTION_FIT, "['SKR3','SKR03','SKR035']",900,3,"15:15:00","17:45:00")) #add 15mins delta start/end
        entries.append((9,LOC_KRAFTRAUM,ACTIVITY_KR,SECTION_FIT, "['SKR5','SKR05','SKR035']",900,5,"09:45:00","12:15:00")) #add 15mins delta start/end       
        self.db.insertMany(table, fields, entries)
        
        table = self.LOCATIONTABLE
        fields = ('id','host_name', 'config')
        entries=[]
        #Currently offline and used as test device
        #entries.append((1,"tsvaccess1",0)) #KR with ampel
        #entries.append((2,"tsvaccess1",1)) #FIT Group MO
        #entries.append((3,"tsvaccess1",2)) #FIT Group DO
        #entries.append((15,"tsvaccess1",10)) #Special Fri
        #entries.append((16,"tsvaccess1",11)) #Special Sa
        entries.append((4,"tsvaccess2",6)) #Sauna backup 
        entries.append((5,"tsvaccess3",3)) #Nord
        entries.append((6,"tsvaccess4",6)) #Sauna with 7-LED
        entries.append((7,"tsvaccess5",5)) #Dojo with ampel
        entries.append((8,"tsvaccess6",4)) #spiegel with ampel
        #The new Kraftraum device - replacing tsvaccess1
        entries.append((9,"tsvaccess7",0))  #KR with ampel
        entries.append((10,"tsvaccess7",1)) #FIT Group MO
        entries.append((11,"tsvaccess7",2)) #FIT Group DO
        entries.append((12,"tsvaccess7",7)) #Special Sa
        entries.append((13,"tsvaccess7",8)) #Special Mo
        entries.append((14,"tsvaccess7",9)) #Special Do
        
        #entries.append((9,"msi",0))
        #entries.append((10,"msi",7))
        self.db.insertMany(table, fields, entries)  
        print(" Accesspoints need to be restarted after update !")
    
    def _fillCourseTable(self,rows):
        DayTranslate={"Mo":0,"Di":1,"Mi":2, "Do":3,"Fr":4,"Sa":5,"So":6}
        self.db.createTable(self.TABLE10)
        table=self.KURSTABLE
        fields = ('kurs_id','paySection','display_Name','activity','room',"weekday","from_Time", "to_Time")
        entries=[]
        cnt=0
        for row in rows:
            dbRow=[cnt,SECTION_FIT]
            weekday = DayTranslate[row[3]]
            row[3]=weekday
            dbRow.extend(row)
            if len(dbRow) != len(fields):
                print("Row failed:",row)
            else:
                entries.append(dbRow)
                cnt +=1
        #entries.append((0,SECTION_FIT,ACTIVITY_GYM, "Dojo",0,"08:45:00","09:30:00"))
        self.db.insertMany(table, fields, entries)  
        print(" Course Table updated !")
    
    '''
    Read from csv. Usually csv has a trailing delimiter that is interpreted as empty column. IF the last entry is missing 
    set hasTrailingDelimiter to False
    We expect ';' as delimiter.
    '''
    def _importFromCSV(self,pathName,hasTrailingDelimiter=True):
        entries=[]
        
        with open(pathName,"r", encoding='utf-8') as csvfile:
        #with open(pathName,"r",newline="") as csvfile:            
            reader = csv.reader(csvfile, delimiter=';')
            for row in reader:
                rowLen = len(row)-1 if hasTrailingDelimiter else len(row) 
                if len(row[0])>1 and row[0][1] != '#':
                    entries.append(row[:rowLen])
        return entries
    
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
    
    def _fillOmocTable(self):
        self.db.createTable(self.TABLE11)
        
        path = OSTools.getLocalPath(__file__)
        cfg = OSTools.joinPathes(path, "data", "omoc.json")
        with open(cfg, "r") as jr:
            dic = json.load(jr)
            uid=dic["USERID"]
            token=dic["TOKEN"]
            passwd=dic["PASSWD"]
            url=dic["URL"]

            
        fields=('id','token','passwd','url')
        data=[(uid,token,passwd,url)]    
        table=self.OMOCTABLE
        self.db.insertMany(table, fields, data)
        
    
    def eliminateDeadMembers(self):
        wd = DBAccess.path;
        picHook=OSTools.joinPathes("web","static") #flask legacy
        picFolder = DBAccess.PICPATH
        fullPath=OSTools.joinPathes(wd,picHook,picFolder)
        #We might have to check if payuntil_date is not null???
        stmt = "SELECT id,picpath FROM Mitglieder m WHERE m.flag = 1"
        rows = self.db.select(stmt)
        count = len(rows)
        print("Found ",count, "entries")
        for data in rows:
            mbrid = data [0]
            picid = data[1]
            if picid:
                pic = OSTools.joinPathes(fullPath,picid)
                ok = OSTools.removeFile(pic)
                #if ok:
                #stmt = "DELETE from Mitglieder where id = %s;"%(mbrid)
                print("deleted %s pic %s success:%s "%(mbrid,pic,ok))

        stmt = "DELETE from Mitglieder where flag =1";
        self.db.select(stmt)
        
        
def basicSetup(dbAccess):
    s = SetUpTSVDB(dbAccess)
    s.resetDatabase()
    s.db.connect("")
    s.setupDatabase()    

def updateScheme(dbAccess):
    s = SetUpTSVDB(dbAccess)
    s.defineDatabases()

def updateAssaAbloy(dbAccess,filename):
    #filename="/home/matze/Documents/TSV/AssaAbloy/Tranponder1.txt"
    '''
    Text is created with:
    pdfgrep Valid SCALA-transponders.pdf >Tranponder1.txt
    pdfgrep Blocked SCALA-transponders.pdf >>Tranponder1.txt
    '''
    s = SetUpTSVDB(dbAccess)
    blocked=[]
    active=[]
    final=[]
    with open(filename,'r', encoding='utf-8') as file:
        data=file.readlines()
        for line in data:
            token2 = "$".join(re.split(r"\s+", line.strip(), flags=re.UNICODE))
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
    self.db.close()                     
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

    
'''
    The Konfig table
+-----------+-------------+---------------+------------+----------------------+------------+---------+-----------+----------+
| config_id | room        | activity      | paySection | groups               | grace_time | weekday | from_Time | to_Time  |
+-----------+-------------+---------------+------------+----------------------+------------+---------+-----------+----------+
|         0 | Kraftraum   | Kraftraum     | Fit & Fun  | ['KR','ÜL']          |        900 |    NULL | NULL      | NULL     |
|         1 | Kraftraum   | GroupFitnesse | Fit & Fun  | ['GROUP']            |       2700 |       0 | 08:45:00  | 09:30:00 |
|         2 | Kraftraum   | GroupFitnesse | Fit & Fun  | ['GROUP']            |       2700 |       3 | 08:45:00  | 09:30:00 |
|         3 | HalleNord   | GroupFitnesse | Fit & Fun  | ['KR','ÜL','GROUP']  |       2700 |    NULL | NULL      | NULL     |
|         4 | Spiegelsaal | GroupFitnesse | Fit & Fun  | ['KR','ÜL','GROUP']  |       2700 |    NULL | NULL      | NULL     |
|         5 | Dojo        | GroupFitnesse | Fit & Fun  | ['KR','ÜL','GROUP']  |       2700 |    NULL | NULL      | NULL     |
|         6 | Sauna       | Sauna         | Sauna      | []                   |      57600 |    NULL | NULL      | NULL     | <- no group
|         7 | Kraftraum   | Kraftraum     | Fit & Fun  | ['SKR']              |        900 |       0 | 15:15:00  | 17:45:00 |
|         8 | Kraftraum   | Kraftraum     | Fit & Fun  | ['SKR']              |        900 |       3 | 15:15:00  | 17:45:00 |
|         9 | Kraftraum   | Kraftraum     | Fit & Fun  | ['SKR']              |        900 |       5 | 09:45:00  | 12:15:00 |
+-----------+-------------+---------------+------------+----------------------+------------+---------+-----------+----------+
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
        return next((c for c in self.configs if c.isValidForGroup(group) and c.isValidInTime()),None) 
    
    def configForUserGroupAndRoom(self,group,room):
        return next((c for c in self.configs if c.isValidForGroup(group) and c.isValidInTime() and c.room==room),None)

    
            
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


def updateConfigTable(dbAccess):

    target=dbAccess.HOST
    res = input("Change config on server ***%s***? [Y/N]"%(target))
    if not (res == "Y"):
        print("Abort")
        return
    s = SetUpTSVDB(dbAccess)
    try:
        s._fillConfigTable()
    except Exception:
        traceback.print_exc()
    finally:
        s.db.close()
#TODO switchLocation(host,loctableID)    
'''
#Kurs;Aktivität;Raum;Wochentag;Von;Bis;
Faszien;GroupFitnesse;Spiegelsaal;Mo;9:00;10:00;
'''
def updateCoursesTable(dbAccess, filepath):
    target=dbAccess.HOST
    res = input("Change Kurse on server ***%s***? [Y/N]"%(target))
    if not (res == "Y"):
        print("Abort")
        return
    s = SetUpTSVDB(dbAccess)
    try:
        entries = s._importFromCSV(filepath)
        s._fillCourseTable(entries)
    except Exception:
        traceback.print_exc()
    finally:
        s.db.close()

def updateMailTable(dbAccess):
    s = SetUpTSVDB(dbAccess)
    try:
        s._fillMailTable()
    except Exception:
        traceback.print_exc()
    finally:
        s.db.close()

def updateOmocTable(dbAccess):
    s = SetUpTSVDB(dbAccess)
    try:
        s._fillOmocTable()
    except Exception:
        traceback.print_exc()
    finally:
        s.db.close()    
        
#Convert the big endian to little endian, which assa abloy needs    
def rfidFromTableToAssaAbloy(decimalString):
    decimal = int(decimalString)
    packed_num = struct.pack('>I', decimal)
    unpacked_num = struct.unpack('<I', packed_num)
    res = hex(unpacked_num[0])
    print("Big Int Decimal %d to AA little engine:%s"%(decimal,res))

#remove memebers with flag=1. Remove their pictures as well.
def cleanDeadMembers(dbAccess):
    s = SetUpTSVDB(dbAccess)
    s.eliminateDeadMembers()
    
    
def parseOptions(args):
    
    try:
        opts, args = getopt.getopt(args[1:], "drkmost:c:g:", ["deleteMembers","convert","reset", "updateLocation", "updateMail","updateOmoc" "updateScheme","transponder","groupCourses"])
        if len(opts) == 0:
            printUsage()
    except getopt.GetoptError:
        printUsage()
        sys.exit(2)
    
    dbAccess = DBAccess()
    
    for o, a in opts:
        if o in ("-r", "--reset"):
            basicSetup(dbAccess)
        elif o in ("-k", "--updateKonfig"):
            updateConfigTable(dbAccess)
        elif o in ("-g", "--groupCourses"):
            updateCoursesTable(dbAccess,a)    
        elif o in ("-m", "--updateMail"):
            updateMailTable(dbAccess)      
        elif o in ("-o", "--updateOmoc"):
            updateOmocTable(dbAccess)            
        elif o in ("-s", "--updateScheme"):
            updateScheme(dbAccess) #Removes data from Zutritt and Beitrag! 
        elif o in ("-t", "--transponder"):
            updateAssaAbloy(dbAccess,a)
        elif o in ("-c", "--convert"):
            rfidFromTableToAssaAbloy(a)
        elif o in ("-d", "--deleteMembers"):
            cleanDeadMembers(dbAccess)
        else:
            printUsage()

def printUsage():
    print("Creator commands: \n"\
          "\t-r > !reset the database! (--reset) \n"
          "\t-k > update konfig (--updateKonfig) \n"
          "\t-g filename > update Courses (--groupCourses) \n"
          "\t-m > update the mail credentials (--updateMail) \n"
          "\t-o > update the omoc credentials (--updateOmoc) \n"
          "\t-s > !update the database! (--updateScheme) \n"
          "\t-t filename > read transponder (--transponder) \n"
          "\t-c decimal rfid > convert rfid to AA (--convert) \n"
          "\t-d > delete Members (--deleteMembers) \n"
          )
    

if __name__ == '__main__':
    sys.exit(parseOptions(sys.argv))
