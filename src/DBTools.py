'''
Created on Mar 30, 2023

@author: matze
'''
import mysql.connector as mysql
import datetime


class Connector():
    DBError=mysql.Error
    
    def __init__(self,host,user,pwd):
        self.HOST=host
        self.USER=user
        self.PASSWORD=pwd
        

    def connect(self, dbName):
        try:
            self.dbConnection=mysql.connect(host=self.HOST,database=dbName, user=self.USER, password=self.PASSWORD)
            print("Connected to:", self.dbConnection.get_server_info())
        except mysql.Error as sqlError:
            print(sqlError)

    def createDatabase(self,dbName):
        try:
            create_db_query = "CREATE DATABASE "+dbName
            with self.dbConnection.cursor() as cursor:
                cursor.execute(create_db_query)
        except mysql.Error as sqlError:
            print(sqlError)
                

    def dropDatabase(self,dbName):
        try:
            drop_query = "DROP DATABASE "+dbName
            with self.dbConnection.cursor() as cursor:
                cursor.execute(drop_query)
        except mysql.Error as sqlError:
            print(sqlError)


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
            print(sqlError)

    def createTable(self,stmt):
        try:
            with self.dbConnection.cursor() as cursor:
                cursor.execute(stmt)
                self.dbConnection.commit()     
        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            print(sqlError)
            

    def showDatabases(self):
        show_db_query = "SHOW DATABASES"
        with self.dbConnection.cursor() as cursor:
            cursor.execute(show_db_query)
            for db in cursor:
                print(db)

    def deleteEntry(self,table,fn,condition):
        cond = str(condition)
        stmt ="DELETE FROM "+table+" WHERE "+fn+" = " + cond 
        with self.dbConnection.cursor() as cursor:
            cursor.execute(stmt)        
            self.dbConnection.commit()
    

    def select(self,stmt):
        try:
            with self.dbConnection.cursor() as cursor:
                cursor.execute(stmt)
                return cursor.fetchall()
        except mysql.Error as sqlError:
            self.dbConnection.rollback()
            print(sqlError)     

                           
    def close(self):
        if self.dbConnection is not None:
            self.dbConnection.close()


if __name__ == '__main__':
    pass