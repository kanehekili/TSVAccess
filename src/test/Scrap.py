'''
Created on Apr 3, 2023

@author: matze
'''
from DBTools import Connector
from datetime import datetime, timedelta,date
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

'''
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

if __name__ == '__main__':
    testSelectRowComplete()
    #testSelect()
    #testCreateAccessData()
    pass