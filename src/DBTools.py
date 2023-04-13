'''
Created on Mar 30, 2023

@author: matze
'''
import mysql.connector as mysql
import os,sys
from itertools import tee
import gzip
import logging
from logging.handlers import RotatingFileHandler
import subprocess

class Connector():
    DBError=mysql.Error
    
    def __init__(self,host,user,pwd):
        self.HOST=host
        self.USER=user
        self.PASSWORD=pwd
        self.connected = False
        

    def connect(self, dbName):
        try:
            self.dbConnection=mysql.connect(host=self.HOST,database=dbName, user=self.USER, password=self.PASSWORD)
            print("Connected to:", self.dbConnection.get_server_info())
            self.connected =True
        except mysql.Error as sqlError:
            self.connected =False
            print(sqlError)

    def createDatabase(self,dbName):
        try:
            create_db_query = "CREATE DATABASE "+dbName
            with self.dbConnection.cursor() as cursor:
                cursor.execute(create_db_query)
        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            print("CREATE DB:%s"%(sqlError)) 
                

    def dropDatabase(self,dbName):
        try:
            drop_query = "DROP DATABASE "+dbName
            with self.dbConnection.cursor() as cursor:
                cursor.execute(drop_query)
        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            print("DROP DB:%s"%(sqlError)) 


    def dropTable(self,tableName):
        drop_table_query = "DROP TABLE "+tableName
        with self.dbConnection.cursor() as cursor:
            cursor.execute(drop_table_query)

    def showTables(self):
        '''
        >>> show_table_query = "DESCRIBE movies"
        >>> with connection.cursor() as cursor:
        ...     cursor.execute(show_table_query)
        ...     # Fetch rows from last executed query
        ...     result = cursor.fetchall()
        ...     for row in result:
        ...         print(row)        
        '''
        query="SHOW TABLES"
        with self.dbConnection.cursor() as cursor:
            cursor.execute(query)
            tNames=[]
            for item in cursor:
                tNames.append(item[0])
            
            for tx in tNames:
                tQuery = "SHOW COLUMNS FROM "+tx
                cursor.execute(tQuery)
                for item in cursor:
                    print("Table %s field:%s"%(tx,item))
    
    
    '''
sql = "INSERT INTO updates (ID, insert_datetime, egroup, job_state) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE insert_datetime = VALUES(insert_datetime), egroup = VALUES(egroup), job_state = VALUES(job_state);"
mycursor.executemany(sql, jobUpdatesList)
    '''
    def insertMany(self,table,fields,dataArray):
        try:
            fieldNames = str(fields) #these are tuples. 
            start=0
            query = []
            query.append("INSERT INTO ")
            query.extend(table)
            query.append(fieldNames)
            query.append(" VALUES (")
            for item in fields:
                if start==0:
                    query.append("%s")
                    start=1
                else:
                    query.append(",%s")
            query.append(")")
            query.append(" ON DUPLICATE KEY UPDATE ")
            start=0
            for item in fields:
                if start>0:
                    query.append(",")
                else:
                    start=1    
                query.append(item+"= VALUES("+item+")")
            
            query = "".join(query).replace("'","")

            print(query)                
            with self.dbConnection.cursor() as cursor:
                res=cursor.executemany(query, dataArray)
                print(res)
                self.dbConnection.commit()

        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            print("INSERT:%s"%(sqlError)) 

    def createTable(self,stmt):
        try:
            with self.dbConnection.cursor() as cursor:
                cursor.execute(stmt)
                self.dbConnection.commit()     
        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            print("CREATE TABLE:%s"%(sqlError)) 
            

    def showDatabases(self):
        show_db_query = "SHOW DATABASES"
        with self.dbConnection.cursor() as cursor:
            cursor.execute(show_db_query)
            for db in cursor:
                print(db)

    def deleteEntry(self,table,fn,condition):
        try:
            cond = str(condition)
            stmt ="DELETE FROM "+table+" WHERE "+fn+" = " + cond 
            with self.dbConnection.cursor() as cursor:
                cursor.execute(stmt)        
                self.dbConnection.commit()
        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            print("DELETE ROW: %s"%(sqlError))     
    

    def select(self,stmt):
        try:
            with self.dbConnection.cursor() as cursor:
                cursor.execute(stmt)
                return cursor.fetchall()
        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            print("SELECT: %s"%(sqlError))     

                           
    def close(self):
        if self.dbConnection is not None:
            self.dbConnection.close()

class OSTools():
    #singleton, class methods only

    @classmethod
    def getLocalPath(cls,fileInstance):
        return os.path.dirname(os.path.realpath(fileInstance))
    
    @classmethod
    def setMainWorkDir(cls,dirpath):
        os.chdir(dirpath)  #changes the "active directory" 
    
    @classmethod    
    def getActiveDirectory(cls):
        return os.getcwd()
    
    @classmethod
    def joinPathes(cls,*pathes):
        res=pathes[0]
        for _,tail in cls.__pairwise(pathes):
        #for a, b in tee(pathes):
            res = os.path.join(res, tail)
        return res
    
    @classmethod
    def ensureDirectory(cls, path, tail=None):
        # make sure the target dir is present
        if tail is not None:
            path = os.path.join(path, tail)
        if not os.access(path, os.F_OK):
            try:
                os.makedirs(path)
                os.chmod(path, 0o777) 
            except OSError as osError:
                logging.log(logging.ERROR, "target not created:" + path)
                logging.log(logging.ERROR, "Error: " + str(osError.strerror))
    
    @classmethod
    def __pairwise(cls,iterable):
        a, b = tee(iterable)
        next(b, None)
        return list(zip(a, b))    
    #logging rotation & compression
    @classmethod
    def compressor(cls,source, dest):
        with open(source,'rb') as srcFile:
            data=srcFile.read()
            bindata = bytearray(data)
            with gzip.open(dest,'wb') as gz:
                gz.write(bindata)
        os.remove(source)
    
    @classmethod
    def namer(self,name):
        return name+".gz"

    @classmethod
    def setupRotatingLogger(cls,logName,logConsole):
        logSize=5*1024*1024 #5MB
        if logConsole: #aka debug/development
            folder = OSTools.getActiveDirectory()    
        else:
            folder= OSTools.joinPathes(OSTools().getHomeDirectory(),".config",logName)
            OSTools.ensureDirectory(folder)
        logPath = OSTools.joinPathes(folder,logName+".log") 
        fh= RotatingFileHandler(logPath,maxBytes=logSize,backupCount=5)
        fh.rotator=OSTools.compressor
        fh.namer=OSTools.namer
        logHandlers=[]
        logHandlers.append(fh)
        if logConsole:
            logHandlers.append(logging.StreamHandler(sys.stdout))    
        logging.basicConfig(
            handlers=logHandlers,
            #level=logging.INFO
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s : %(message)s'
        )

    @classmethod
    def setLogLevel(cls,levelString):
        if levelString == "Debug":
            Log.setLevel(logging.DEBUG)
        elif levelString == "Info":
            Log.setLevel(logging.INFO)
        elif levelString == "Warning":
            Log.setLevel(logging.WARNING)
        elif levelString == "Error":
            Log.setLevel(logging.ERROR)

Log=logging.getLogger("TSV")

'''
class RunExternal():
    def __init__(self):
        self.lastMsg=None
        self.lastError=None
        pass
    
    #execute non shell command using []
    def execute(self,cmd):
        self.lastMsg,self.lastError = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        return (self.lastMsg,self.lastError)
'''
def runExternal(cmd):
    lastMsg,lastError = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    return (lastMsg,lastError)
            
    
    


if __name__ == '__main__':
    pass