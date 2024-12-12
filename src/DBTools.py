'''
Created on Mar 30, 2023

@author: matze
'''
import mysql.connector as mysql
import os,sys
from itertools import tee
import gzip,time
import logging
from logging.handlers import RotatingFileHandler
import subprocess
from subprocess import Popen

class Connector():
    DBError=mysql.Error
    
    def __init__(self,host,user,pwd):
        self.dbConnection = None
        self.dbName=None
        #https://pynative.com/python-mysql-database-connection/
        #mariadb: show variables like 'collation%';
        self.mariah_config = {
            'user': user,
            'password': pwd,
            'host': host,
            'port': 3306,
            'ssl_disabled': True,
            'autocommit':True,
            'collation':'utf8mb3_general_ci',
            'raise_on_warnings': True
        }

    def connect(self, dbName):
        self.mariah_config['database'] = dbName
        try:
            self.dbConnection=mysql.connect(**self.mariah_config)
            self.dbConnection.auto_reconnect = True
            self.dbName=dbName
            Log.info("Connected to:%s", self.dbConnection.get_server_info())
        except mysql.Error as sqlError:
            Log.warning("Connect: %s",sqlError)
            self.dbConnection = None

    def _getCursor(self):
        try:
            if not self.isConnected():
                Log.warning("Cursor reconnect!")
                self.connect(self.dbName)

            cursor = self.dbConnection.cursor()
            return cursor
        except:
            Log.warning("Cursor reconnect fallback!")
            self.connect(self.dbName)
            time.sleep(1)
            if self.dbConnection:
                return self.dbConnection.cursor() #no recursion now
            raise Exception("No database connection in cursor")

    def _getCursorWithReconnect(self, run=1): #Test -not productive
        try:
            self.dbConnection.ping(reconnect=True, attempts=3, delay=5)
        except mysql.Error as err:
            Log.warning("Cursor reconnect fails: %s",str(err))
            if run ==1:
                Log.warning("Can't reconnect")
                raise Exception("No database in get cursor")
            self.connect(self.dbName)
        return self.dbConnection.cursor()

    def ensureConnection(self):
        retries=5
        while retries >0:
            retries -=1
            try:
                self._getCursor()
                return
            except:
                Log.warning("connect failed, retry:%d",retries)
                time.sleep(2)

    def isConnected(self):
        if self.dbConnection is None:
            return False
        return self.dbConnection.is_connected()

    def pingHost(self):
        host = self.mariah_config["host"]
        hostUp = os.system(f"ping -c 10 {host} >/dev/null 2>&1") == 0
        if not hostUp:
            Log.warning("Ping failed - Server not online")
            return False
        return True


    def createDatabase(self,dbName):
        try:
            create_db_query = "CREATE DATABASE "+dbName
            #with self.dbConnection.cursor() as cursor:
            with self._getCursor() as cursor:
                cursor.execute(create_db_query)
        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            Log.debug("CREATE DB:%s"%(sqlError)) 
                

    def dropDatabase(self,dbName):
        try:
            drop_query = "DROP DATABASE "+dbName
            with self._getCursor() as cursor:
                cursor.execute(drop_query)
        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            Log.debug("DROP DB:%s"%(sqlError)) 


    def dropTable(self,tableName):
        drop_table_query = "DROP TABLE "+tableName
        with self._getCursor() as cursor:
            cursor.execute(drop_table_query)

    def showTables(self):
        query="SHOW TABLES"
        with self._getCursor() as cursor:
            cursor.execute(query)
            tNames=[]
            for item in cursor:
                tNames.append(item[0])
            
            for tx in tNames:
                tQuery = "SHOW COLUMNS FROM "+tx
                cursor.execute(tQuery)
                for item in cursor:
                    Log.debug("Table %s field:%s"%(tx,item))
    
    
    '''
    sql = "INSERT INTO updates (ID, insert_datetime, egroup, job_state) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE insert_datetime = VALUES(insert_datetime), egroup = VALUES(egroup), job_state = VALUES(job_state);"
    mycursor.executemany(sql, jobUpdatesList)
    '''
    def insertMany(self,table,fields,dataSaveArray):
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

            Log.debug(query)                
            with self._getCursor() as cursor:
                res=cursor.executemany(query, dataSaveArray)
                self.dbConnection.commit()
                if res is not None:
                    Log.debug("insert:> %s <",res)

        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            Log.warn("INSERT:%s",sqlError) 

    def createTable(self,stmt):
        try:
            with self._getCursor() as cursor:
                cursor.execute(stmt)
                self.dbConnection.commit()     
        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            Log.debug("CREATE TABLE:%s"%(sqlError)) 
            

    def showDatabases(self):
        show_db_query = "SHOW DATABASES"
        with self._getCursor() as cursor:
            cursor.execute(show_db_query)
            for db in cursor:
                Log.debug(db)

    def deleteEntry(self,table,fn,condition):
        try:
            cond = str(condition)
            stmt ="DELETE FROM "+table+" WHERE "+fn+" = " + cond 
            Log.debug(stmt)
            with self._getCursor() as cursor:
                cursor.execute(stmt)        
                self.dbConnection.commit()
        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            Log.debug("DELETE ROW: %s"%(sqlError))     
    

    def select(self,stmt):
        try:
            Log.info(stmt)  
            with self._getCursor() as cursor:
                cursor.execute(stmt)
                return cursor.fetchall()
        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            Log.warn("SELECT: %s"%(sqlError))     

                           
    def close(self):
        if self.dbConnection is not None:
            self.dbConnection.close()

class OSTools():
    #singleton, class methods only

    @classmethod
    def getLocalPath(cls,fileInstance):
        return os.path.dirname(os.path.realpath(fileInstance))
    
    @classmethod
    def fileExists(cls, path):
        return os.path.isfile(path)
    
    @classmethod
    def setMainWorkDir(cls,dirpath):
        os.chdir(dirpath)  #changes the "active directory" 
    
    @classmethod    
    def getActiveDirectory(cls):
        return os.getcwd()
    
    #@classmethod
    #def username(cls):
    #    return pwd.getpwuid(os.getuid()).pw_name 
    
    @classmethod
    def joinPathes(cls,*pathes):
        res=pathes[0]
        for _,tail in cls.__pairwise(pathes):
        #for a, b in tee(pathes):
            res = os.path.join(res, tail)
        return res
    
    def getHomeDirectory(self):
        return os.path.expanduser("~")
    
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
        '''
        Note: desktop file are opened by current user - active directory can not be used (Permissions) 
        '''
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
            #level=logging.INFO,
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s : %(message)s'
        )


    @classmethod
    def setLogLevel(cls,levelString):
        if levelString == "Debug":
            level = logging.DEBUG
        elif levelString == "Info":
            level = logging.INFO
        elif levelString == "Warning":
            level = logging.WARNING
        elif levelString == "Error":
            level = logging.ERROR
            
        Log.setLevel(level)
        for handler in logging.getLogger().handlers:
            handler.setLevel(level)

    #will not work in windows
    @classmethod
    def checkIfInstanceRunning(cls,moduleName):
        process = Popen(["ps aux |grep -v grep | grep "+moduleName],shell=True,stdout=subprocess.PIPE)
        result = process.communicate()
        rows = result[0].decode('utf8').splitlines()
        instanceCount =0
        for line in rows:
            if line:
                instanceCount+=1
        return instanceCount > 1


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