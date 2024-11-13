'''
Created on Apr 3, 2023

@author: matze
'''
from DBTools import Connector
from datetime import datetime, timedelta
#from faker import Faker
import json
from TsvAccessModule import RaspberryFAKE
import smtplib,ssl
from email.message import EmailMessage

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

# testCount:
'''
 List the users that are present at a certain hour and day (usually today.
 First entry is always a check in, second a checkout. So either select the morning or the afternoon batch ascending by date
 Return the rows in date descending order (latest checkin is first) 
'''

class AccessRow():
    def __init__(self,dbRow):
        self.id=dbRow[0]
        self.da=dbRow[4] #datetime
        self.data=dbRow
        self.checked=True
    
    def hour(self):
        return self.da.hour()
    
    def checkInTimeString(self):
        return datetime.strftime(self.da,"%H:%M")
    
    def toggleChecked(self,acDate):
        self.checked=not self.checked
        self.da=acDate
        
    def __lt__(self, other):
        return self.da < other.da
    
    def __gt__(self, other):
        return self.da > other.da

class CountRow():
    #SELECT mitglied_id,access_date
    MAX_PREVVAIL=4
    def __init__(self,dbRow,breaktime):
        self.id=dbRow[0]
        self.breakTime=breaktime
        #self.da=dbRow[1] #datetime
        self.checkArray=[None,None,None,None] #0=morning CKI, 1 morning CKO, 2 Aftern CKi. 3 Aftn cko
        self._checkin(dbRow[1])
        self.data=dbRow
        self.checked=True
    
    def _checkin(self,rowDate):
        if rowDate.hour < self.breakTime:
            self.checkArray[0]=rowDate
        else:
            self.checkArray[2]=rowDate

    def _setInternal(self,rowDate,idx):
            if self.checkArray[idx] is None:
                self.checkArray[idx]=rowDate
            else:
                self.checkArray[idx+1]=rowDate
                
    def _checkDate(self,rowDate):
        if rowDate.hour < self.breakTime:
            self._setInternal(rowDate, 0)
        else:
            self._setInternal(rowDate, 2)
        
        
    def updateAccess(self,row):
        self._checkDate(row[1])
    
    #crude: either 1x or twice a day. 
    def accessCount(self):
        cnt=0
        ctxIndx=[0,2]
        for idx in ctxIndx:
            if self.checkArray[idx] is not None:
                cnt+=1
        return cnt
    
    #crude: if cki but not cko we assume 4 hours
    
    def _calcPartHours(self,idx):
        hours=0
        if self.checkArray[idx] is not None:
            if self.checkArray[idx+1] is None:
                hours = CountRow.MAX_PREVVAIL
            else:
                hours = self.checkArray[idx+1].hour-self.checkArray[idx].hour
        return hours
    
    def cumulatedHours(self):
        hours1= self._calcPartHours(0)
        hours2=self._calcPartHours(2)
        return hours1+hours2
          
    
def testAccessNow():
    #Morning
    db=openConnector()
    mbrTable= "Mitglieder"
    timetable= "Zugang"
    endHour="13";
    location="Kraftraum"
    members={}
    #stmt ="SELECT id,first_name,last_name,picpath,access_date FROM "+mbrTable+" m JOIN "+timetable+" z ON m.id = z.mitglied_id WHERE DATE(z.access_date) = CURDATE() AND ((HOUR(z.access_date) < "+endHour+" AND HOUR(CURTIME()) < "+endHour+") OR (HOUR(z.access_date) >= "+endHour+" AND HOUR(CURTIME()) >= "+endHour+") and location='"+location+"')  ORDER By z.access_date DESC"
    stmt ="SELECT id,first_name,last_name,picpath,access_date FROM "+mbrTable+" m JOIN "+timetable+" z ON m.id = z.mitglied_id WHERE DATE(z.access_date) = CURDATE() and location='"+location+"'  ORDER By z.access_date ASC"
    rows = db.select(stmt)
    for row in rows:
        mid = row[0]
        acr= members.get(mid,None)
        if acr is None:
            members[mid]=AccessRow(row)
        else:
            members[mid].toggleChecked(row[4])
    
    present =[item for item in members.values() if item.checked]    
    present.sort(reverse=True)
    print("Row count:",len(rows)," mbr count:",len(members)," present count:",len(present))
    for mbr in present:
        print(mbr.data)
    db.close()

def testDailyCount():
    db=openConnector()
    table="Zugang"
    location="Kraftraum"
    breakTime=12
    members={}
    stmt = "SELECT mitglied_id,access_date from "+table+" where location='"+location+"'"
    rows = db.select(stmt)
    for row in rows:
        print(row)
        mid = row[0]
        theDayKey=row[1].strftime('%Y/%m/%d')
        acr= members.get(theDayKey,None)
        if acr is None:
            members[theDayKey]={}

        cr=members[theDayKey].get(mid,None)
        if cr is None:
            cr=members[theDayKey][mid]=CountRow(row,breakTime)
        else:
            members[theDayKey][mid].updateAccess(row)    
        
        
    #We need date as key and count as value
    for key, aDay in members.items():
        for theid, countRow in aDay.items():
            print("%s>id: %d count: %d hours:%d"%(key,theid,countRow.accessCount(),countRow.cumulatedHours()))
    
    for key, aDay in members.items():
        cnt=0
        for cr in aDay.values():
            cnt+=cr.accessCount()
        print("key:",key," cnt:",cnt)
    
    db.close()
    
def countBlockUsage():
    table="Zugang"
    room="Kraftraum"
    startHour = 9
    endHour = 12
    weekday=0
    stmt = "SELECT DATE(access_date) AS aDate, COUNT(DISTINCT mitglied_id) AS cnt FROM %s WHERE room = '%s' AND HOUR(access_date) >= %d AND HOUR(access_date) < %d AND WEEKDAY(access_date) = %d GROUP BY DATE(access_date) ORDER BY DATE(access_date)"%(table,room,startHour,endHour,weekday)
    c=openConnector()
    rows = c.select(stmt)
    for info in rows:
        print(info)
    #(datetime.date(2024, 5, 13), 22)    
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
''' Fake not installed anymore
def rand_name():
    fake = Faker('de_DE')
    for n in range(1000):
        data=[n+24,fake.first_name(),fake.last_name() ]
        print(data)
'''
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
        
def nextDay():
    real = datetime.now()
    
    fakeNow = real.replace(day= 1, hour=7,minute=50,second=0,microsecond=0)
    #fakeNow = real.replace(hour=1,minute=0,second=0,microsecond=0)
    #fakeNow = real  
    print("Now:",fakeNow)
    
    if fakeNow.hour >= 22 or fakeNow.hour < 8:
        goal = fakeNow.replace(hour=8,minute=0,second=0,microsecond=0)
        print("goal1:",goal)
        if fakeNow > goal:
            print("Now is larger")
            goal = goal + timedelta(days=1)
        print(goal) 
        secs = (goal-fakeNow).seconds
        print(secs,(goal-fakeNow))
    else:
        print("No action")

def sendEmail():
    port = 587  # For starttls
    smtp_server = "myServer"
    password = "mypwd"

    msg = EmailMessage()
    msg['Subject'] = "Sauna Abo"
    msg['From'] = "sender"
    msg['To'] = "receip"
    msg.set_content("Mitglied %s hat 10 Sauna Punkte gekauft"%("Hugo"))

    context = ssl.create_default_context()  
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        server.login("sender", password)
        server.send_message(msg)
         

if __name__ == '__main__':
    #testAccessNow()
    #testDailyCount()
    #generateJsonConfig()
    #calcRFID()
    #testTimer()
    #testSelectRowComplete()
    #testTimeSpan()
    #rand_name()
    #testSelect()
    #testCreateAccessData()
    #nextDay()
    #sendEmail()
    countBlockUsage()
    pass