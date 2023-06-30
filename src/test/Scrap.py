'''
Created on Apr 3, 2023

@author: matze
'''
from DBTools import Connector
from datetime import datetime, timedelta
from faker import Faker
import json
from TsvAccessModule import RaspberryFAKE
'''
def setupDB():
    c=Connector()
    c.connect("")
    c.createDatabase("TsvDB")   
    c.showDatabases()
    c.close()
    c.connect("TsvDB")
    c.createTable(TABLES1)
    c.createTable(TABLES2)
    c.showTables()
    c.close()
'''

def openConnector(dbName="TsvDB"):
    HOST="T410Arch.fritz.box"
    USER = "pyuser"
    PASSWORD = "bertiga7"
    db = Connector(HOST,USER,PASSWORD)
    db.connect(dbName)
    return db        


def deleteDB():
    c= openConnector(dbName="") 
    c.dropDatabase("TsvDB")
    c.close()
    
def connectDB():
    c=openConnector()
    c.showDatabases()
    c.close()
        

def fakeData():
    #an example on how to fill
    '''
    Table Mitglieder field:('id', 'int(11)', 'NO', 'PRI', None, '')
    Table Mitglieder field:('first_name', 'varchar(100)', 'YES', '', None, '')
    Table Mitglieder field:('last_name', 'varchar(100)', 'YES', '', None, '')
    Table Mitglieder field:('entry_date', 'datetime', 'YES', '', None, '')
    Table Mitglieder field:('exit_date', 'datetime', 'YES', '', None, '')
    Table Mitglieder field:('uuid', 'varchar(100)', 'YES', '', None, '')
    Table Zugang field:('mitglied_id', 'int(11)', 'YES', 'MUL', None, '')
    Table Zugang field:('access_date', 'datetime', 'YES', '', None, '')
    '''
    table="Mitglieder"
    fields=('id','first_name','last_name','entry_date','exit_date','uuid')
    ts=datetime(2009,5,5).date().isoformat()
    data= [
        (23,'Hudo','Wert',ts,None,"1234dcab6789ba234"),
        (24,'Karl','Schmock2',ts,None,"8978ff894599")
    ]
    c=openConnector()
    #c.dropTable("Mitglieder")
    #c.dropTable("Zugang")
    #c.createTable(TABLES1)
    #c.createTable(TABLES2)
    c.insertMany(table,fields,data)
    #add zugang
    now=datetime.now().isoformat()
    zug=[(23,now),(24,now)]
    c.insertMany("Zugang", ('mitglied_id','access_date'), zug)
    
    #c.testInsertSimple(table,fields,data)
    c.deleteEntry("Mitglieder", "id", 24)
    c.close()

def showTables():
    c=openConnector()
    c.showTables()
    c.close()



def testCreateAccessData():
    c=openConnector()
    now=datetime.now()
    delta = timedelta(days=1)
    start = now - timedelta(days=68)
    fakeData=[]
    while start <=now:
        dbTime=start.isoformat()
        fakeData.append((1234,dbTime))
        fakeData.append((1236,dbTime))
        start=start+delta
     
    c.insertMany("Zugang", ('mitglied_id','access_date'), fakeData)
    c.close()


def testSelect():
    stmt = "SELECT * from Mitglieder"
    c=openConnector()
    rows = c.select(stmt)
    stmt = "SELECT * from Zugang"
    accRows = c.select(stmt)
    for info in rows:
        print(info)
    for info in accRows:
        print(info) 
 
    c.close()

def testSelectRowComplete():
    stmt="SELECT id, last_name,access_date from Mitglieder INNER JOIN Zugang on Mitglieder.id=Zugang.mitglied_id"
    c=openConnector()
    rows = c.select(stmt)
    for info in rows:
        print(info)
    c.close()    


def testTimeSpan():
    table="Zugang"
    key=str(1236)
    test=datetime(2023, 4, 3, 23, 3, 32).isoformat()
    
    #stmt = "SELECT mitglied_id,access_date from "+table+" where mitglied_id="+key+" AND access_date <= Date_Sub(now(),interval 2 hour)"
    #stmt = "SELECT mitglied_id,access_date from "+table+" where mitglied_id="+key+" AND access_date <= Date_Sub(NOW(),interval 3 day)"
    stmt = "SELECT mitglied_id,access_date from "+table+" where mitglied_id="+key+" AND access_date >= DATE(NOW()) + INTERVAL -12 DAY"
    print(stmt)
    #stmt = "SELECT mitglied_id,access_date from "+table
    c=openConnector()
    rows = c.select(stmt)
    for info in rows:
        print(info)
    c.close()    

def generateJsonConfig():
    dic = {}
    dic["HOST"]="The dbhost"
    dic["DB"]="TsvDB"        
    dic["USER"]= "someUser"
    dic["PASSWORD"] = "passwort"
    dic["MAINTABLE"]="Mitglieder"
    dic["TIMETABLE"]="Zugang"
    dic["GRACETIME"]= "2"      #two hours gracetime to prevent any double checking
    dic["ACCESSPOINTS"]=("FF","FC","DE","STH")
    dic["PICPATH"]=("/path/to/scp")
    with open("../data/.config.json","w") as jf:
        json.dump(dic,jf) 


'''
way to paint ?
def testGraph():
    import pandas as pd
    from datetime import datetime, timedelta
    from random import choices, random
    import matplotlib.pyplot as plt
    
    
    
    ## create random date list
    date_diff_days = choices(range(1,20), k = 50)
    dates = [datetime.now().date() - timedelta(days=i) for i in date_diff_days]
    
    
    ## compute repeated times
    d = dict()
    for date in dates:
        d[date] = d[date] = d[date]+1 if date in d else 1
    df = pd.DataFrame({'date': list(d.keys()),
                      'repeated' : list(d.values())})
    df = df.sort_values(['date'])
    
    
    ## plot the timeseries data
    plt.plot_date(x = df['date'], y = df['repeated'])
    labels = [str(i.day) + '/'+ str(i.month) + '/'+str(i.year) for i in df['date']]
    plt.xticks(ticks=df['date'],labels=labels, rotation=90)
    plt.show()
'''

def rand_name():
    fake = Faker('de_DE')
    for n in range(1000):
        data=[n+24,fake.first_name(),fake.last_name() ]
        print(data)

def testTimer():
    ok=True
    tx=RaspberryFAKE()
    while ok:
        res=input("\n>>")
        if 'g' in res:
            tx.signalAccess()
        if 'r' in res:
            tx.signalForbidden()
        if 'q' in res:
            ok=False

'''
res:
13893217165 Raspi
11001111 00000110 01101010 11100011 01
33C19AB8D
03,3C,19,AB,8D raspi

2870557699  usbreader  10 Zeichen
AB 19 3C 03
->convert: 03 3c 19 AB was ist 8D?

rc522 uid:
uid> 03 hex 03  (usb4)==1byte
uid> 60 hex 3C  (usb3)
uid> 25 hex 19  (usb2)
uid> 171 hex AB (usb1)
uid> 141 hex 8D -not used!


'''
def calcRFID():
    uids=[3,60,25,171,141]
    print("soll:",2870557699)
    print("rfid rc522 ist:",13893217165)
    n=0
    for i in range(0,len(uids)):
        n = n * 256 + uids[i]
    print(n)
    
    x=0
    scm=[3,60,25,171]
    for i in reversed(range(0,len(scm))):
        print(scm[i])
        x = x * 256 + scm[i]
    print("umbau uids:",x)
    
    ist=13893217165 #usb reader ->convert to ist rc522!
    #wiegehts wieter?
    ba=ist.to_bytes(5, byteorder = 'little')
    print("little:",ba)
    ba=ist.to_bytes(5) #default=big
    print("big:",hex(ba[0]),hex(ba[1]),hex(ba[2]),hex(ba[3]),hex(ba[4]))
    test= ba[:-1][::-1]
    
    print("rev:",test," >",int.from_bytes(test))
    print("soll:",hex(ba[3]),hex(ba[2]),hex(ba[1]),hex(ba[0]))
        
    

if __name__ == '__main__':
    #generateJsonConfig()
    calcRFID()
    #testTimer()
    #testSelectRowComplete()
    #testTimeSpan()
    #rand_name()
    #testSelect()
    #testCreateAccessData()
    pass