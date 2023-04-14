'''
Created on Apr 1, 2023
Generates the basic structure of a TSV database
@author: matze
'''
'''
security
pip3 install python-dotenv
from dotenv import load_dotenv
import os 

load_dotenv()
print(os.environ.get('secretUser'))
print(os.environ.get('secretKey'))
print(os.environ.get('secretHost'))
'''

from DBTools import Connector
import csv
from datetime import datetime
import json

#TODO 
ACCESSCODES=[]

class SetUpTSVDB():
    #TODO this stuff belongs to env->getenv or hidden file
    #HOST="192.168.2.82" #"T410Arch.fritz.box"
    with open("data/.config.json","r") as jr:
        dic = json.load(jr)
        HOST=dic["HOST"]
        DATABASE=dic["DB"]
        USER = dic["USER"]             
        PASSWORD = dic["PASSWORD"]        
        MAINTABLE=dic["MAINTABLE"] 
        TIMETABLE=dic["TIMETABLE"] 
        GRACETIME=dic["GRACETIME"]   # hours gracetime to prevent any double check in
        ACCESS=dic["ACCESSPOINT"] #Controlpoint

    TABLE1= """
    CREATE OR REPLACE TABLE Mitglieder (
      id INT PRIMARY KEY,
      first_name VARCHAR(100),
      last_name VARCHAR(100),
      entry_date DATETIME,
      exit_date DATETIME,
      uuid VARCHAR(100)
      )
    """
        
    TABLE2="""
        CREATE OR REPLACE TABLE Zugang (
          mitglied_id INT,
          access_date DATETIME,
          FOREIGN KEY(mitglied_id) REFERENCES Mitglieder(id) ON DELETE CASCADE
        )
        """ 

    def __init__(self,dbName):
        try:
            self.db = Connector(self.HOST,self.USER,self.PASSWORD)
            self.db.connect(dbName)
        except Connector.DBError as sqlError:
            self.db=None
            print(sqlError)

    def isConnected(self):
        return self.db.connected

    def resetDatabase(self):
        self.db.dropDatabase(self.DATABASE)
        self.db.close()
        #finsihed - reconnect!
    
    def setupDatabase(self):
        self.db.createDatabase(self.DATABASE)
        self.db.close()
        self.db.connect(self.DATABASE)
        self.db.createTable(self.TABLE1)
        self.db.createTable(self.TABLE2)
        self.db.close()    

    '''
    import from a CSV file 
    '''
    def importCSV(self,filename):
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

def basicSetup():
    s = SetUpTSVDB("")
    s.resetDatabase()
    s.db.connect("")
    s.setupDatabase()    

def testcsv():
    s = SetUpTSVDB("TsvDB")
    s.importCSV("/home/matze/JWSP/python/TSVAccess/tsv.csv")    

if __name__ == '__main__':
    testcsv()
    pass
