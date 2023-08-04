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
import csv
from datetime import datetime
import json, getopt, sys
from enum import Enum
import threading, time

# TODO 
ACCESSCODES = []


    # Profile TSV-Access 2
    # Adressdaten,Geschlecht,Nachname,Vorname,Mutli3,Austrittsdatum,GebDatum 
class Fields(Enum):
    ID = 0
    GENDER = 1
    NAME = 2
    VORNAME = 3
    ACCESS = 4
    EOLDATE = 5
    BDATE = 6
    #FLAG?
    
# Allowed access locations:
KRAFTRAUM = "Kraftraum"
YOGA = "Yoga"
# to be defined 

class GROUPS(Enum):
    Group = 0
    ÜL = 1
    FFA = 2
    KR = 3
    Juggling = 4
    UKR =5



class SetUpTSVDB():
    path = OSTools.getLocalPath(__file__)
    cfg = OSTools.joinPathes(path, "data", ".config.json")
    with open(cfg, "r") as jr:
        dic = json.load(jr)
        HOST = dic["HOST"]
        DATABASE = dic["DB"]
        USER = dic["USER"]             
        PASSWORD = dic["PASSWORD"]    
        GRACETIME = dic["GRACETIME"]  # seconds gracetime to prevent any double check in
        #---------- ssh only -----------
        PICPATH = dic["PICPATH"]  # path to scp -RegisterModule only
        SSHUSER = dic["SSHUSR"]
        SSHPWD=dic["SSHPWD"]
        
        #--- deprected ->DB Location ---
        LOCATION = dic["LOCATION"] #only location Accessmodule -> to database!!!
        ACCESS = dic["ACCESSPOINTS"]  # Controlpoint -< DB Only

    MAINTABLE ="Mitglieder"
    TABLE1 = """
    CREATE OR REPLACE TABLE Mitglieder (
      id INT PRIMARY KEY,
      first_name VARCHAR(100),
      last_name VARCHAR(100),
      eol_date DATETIME,
      access VARCHAR(100),
      gender VARCHAR(1),
      birth_date DATETIME,
      picpath VARCHAR(100),
      uuid INT UNSIGNED,
      flag SMALLINT UNSIGNED 
      )
    """

    TIMETABLE="Zugang"        
    TABLE2 = """
        CREATE OR REPLACE TABLE Zugang (
          mitglied_id INT,
          access_date DATETIME,
          location VARCHAR(100),
          FOREIGN KEY(mitglied_id) REFERENCES Mitglieder(id) ON DELETE CASCADE
        )
        """ 
    LOCATIONTABLE="Location"
    TABLE3 = """
        CREATE OR REPLACE TABLE Location (
        host_name VARCHAR(50),
        room VARCHAR(100),
        groups VARCHAR(250),
        grace_time SMALLINT UNSIGNED
        )
        """  
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
            print(sqlError)
            return False
        self._intrepidSockets()
        return True

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
        self.db.createTable(self.TABLE1)
        self.db.createTable(self.TABLE2)
        self.db.createTable(self.TABLE3)
        self.db.close()    

    '''
    import from a CSV file 
    def testImportCSV(self,filename):
        data=[]
        with open(filename,encoding='utf-8-sig') as csvfile:
            reader= csv.reader(csvfile, delimiter=';', quotechar='|')
            for line in reader:
                print(line)
                mid = line[0]
                fn=line[1]
                nn=line[2]
                ed=line[3]
                dt=datetime.strptime(ed, '%d.%m.%Y')
                fmt=dt.date().isoformat()
                dingens=(mid,fn,nn,fmt)
                data.append(dingens)
                #gather and do some stuff
        table="Mitglieder"
        fields=('id','first_name','last_name','entry_date')
        self.db.insertMany(table,fields,data)
        self.db.close()     
    '''

    # ﻿Vorname $Nachname $AustrittsDatum $Multifeld 3 $Beitragsname $Beitragshöhe $BeitragBis $Anrede $GebDatum    
    def updateDatabase(self, data):
        table = "Mitglieder"
        fields = ('id', 'first_name', 'last_name', "eol_date", "access", "gender", "birth_date")
        self.db.insertMany(table, fields, data)
        self.db.close()            


    def _intrepidSockets(self):
        t=threading.Thread(target=self.heartbeat())
        t.start()

    def heartbeat(self):
        while True:
            time.sleep(3600*6)
            try:
                self.db.select("Select 1")
                self.log.info("Heartbeat")
            except:
                self.connectToDatabase(self.databaseName)

def basicSetup():
    s = SetUpTSVDB(SetUpTSVDB.DATABASE)
    s.resetDatabase()
    s.db.connect("")
    s.setupDatabase()    


def displayImportFindings(doublets, multiSet, mbrCount):
    print("Imported %d members" % (mbrCount))
    print ("Multi Field:")
    for key, cnt in multiSet.items():
        print(key + ":", cnt)
    
    print("Doubletten:")    
    for key, cnt in doublets.items():
        if cnt > 1:
            print("%s Einträge %d" % (key, cnt))
        

def importCSV(filename):
    # = SetUpTSVDB("TsvDB")
    # Profile TSV-Access 2
    # Adressdaten,Geschlecht,Nachname,Vorname,Mutli3,Austrittsdatum,GebDatum  
    # validate
    # filename="/home/matze/git/TSVAccess/tsv.csv"
    data = []
    doublets = {}
    multiSet = {}
    mbrCount=0
    with open(filename, encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile, delimiter='$', quotechar='|')
        for line in reader:
            # print(line)
            isHeader = "Vorname" in line
            if isHeader:
                continue
            conplanID=line[Fields.ID.value]
            fn = line[Fields.VORNAME.value]
            nn = line[Fields.NAME.value]
            tmpDate = line[Fields.EOLDATE.value]
            if len(tmpDate) > 0:
                eol = datetime.strptime(tmpDate, '%d.%m.%Y').date().isoformat()
            else:
                eol = None
                
            access = ''
            zugang = line[Fields.ACCESS.value].split(' ')
            if len(zugang) >= 1:
                access = zugang[0]
            
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
            
            dbKey = "%s %s,%s" % (fn, nn, birthdate)
            
            if doublets.get(dbKey, None) is None:
                doublets[dbKey] = 1
            else:
                doublets[dbKey] += 1
                print("Ignoring doublet:%s EOL %s" % (dbKey, eol))
            
            rowTuple = (conplanID, fn, nn, eol, access, gender, birthdate)  # last is a possible token id
            print(">>", rowTuple)
            data.append(rowTuple) 
            mbrCount += 1
    
    displayImportFindings(doublets, multiSet, mbrCount)
    return data

#TODO if we get only membes ,reomve those who are  in the database but not in the list...    
def persistCSV(fn):
    s = SetUpTSVDB("TsvDB")
    data = importCSV(fn)
    #todo a.symmetric_difference(b) - two sets of ids! (not arrays)
    s.updateDatabase(data)

    
def parseOptions(args):
    
    try:
        opts, args = getopt.getopt(args[1:], "p:v:r", ["persist=", "verify=", "reset"])
        if len(opts) == 0:
            print("Use -p, -r or -v")
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
        else:
            printUsage()

def printUsage():
    print("Creator commands: \n"\
          "\t-p filename > verify & persist a csv file (--persist)\n"\
          "\t-v filename > verify csv file and check for inconsistencies (--verify)\n"\
          "\t-r > reset the database (--reset) \n")
    

if __name__ == '__main__':
    sys.exit(parseOptions(sys.argv))
