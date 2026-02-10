'''
Created on 31 Mar 2025

connector for the remote sewobe RESTfull API

@author: matze
'''
import requests,json
import DBTools
from DBTools import OSTools
from TsvDBCreator import DBAccess,SetUpTSVDB
from datetime import datetime
from collections import Counter
#from time import sleep
#from enum import Enum

CODE_OK=200
REST_BASE_URL = "https://manager23.sewobe.de/"
OSTools.setupRotatingLogger("Sewobe", True)
Log = DBTools.Log

class RestConnector():
    session=None
    lastError=None
    
    def __init__(self):
        self._credentials()
    
    def login(self):
        function = "REST_LOGIN"
        app = "restlogin"
        login_url = f"{REST_BASE_URL}applikation/{app}/api/{function}" 
        payload = {
            "USERNAME_REST": RestConnector.USERNAME,
            "PASSWORT_REST": RestConnector.PASSWORD
        }
        response = requests.post(login_url, data=payload)
        if self._checkResponse(response):
            return self._saveSession(response)
        else:
            return False
    def _credentials(self):
        path = OSTools.getLocalPath(__file__)
        cfg = OSTools.joinPathes(path, "data", "sewbode.json")
        with open(cfg, "r") as jr:
            dic = json.load(jr)
            RestConnector.USERNAME=dic["USER"]
            RestConnector.PASSWORD=dic["PWD"]
    '''
    def _testGetCountries(self): #just an example on how to retrieve data
        function="GET_LAENDER"
        app="adressen"
        data_url = f"{REST_BASE_URL}applikation/{app}/api/{function}"
        params = {"SESSION": self.session}  # Matches PHP's ?SESSION=[SESSION]
        data_response = requests.get(data_url, params=params)
        if self._checkResponse(data_response):
            print(data_response.json())
     
    def _getUser(self):   
        function="GET_USER"
        app="benutzer"
        data_url = f"{REST_BASE_URL}applikation/{app}/api/{function}"
        params = {"SESSION": self.session}
        data_response = requests.get(data_url, params=params)
        if self._checkResponse(data_response):
            print(data_response.json())


    def _someBullshit(self): #same as members, post, not get
        function="SUCHE_INDIV_PLATZHALTER"
        app="auswertungen"
        checkGroup = []
        payload = {"AUSWERTUNG_ID":6,"PH6":1} #unklar was 6 und PH6:1 bedeuted
        data_url = f"{REST_BASE_URL}applikation/{app}/api/{function}"
        params = {"SESSION": self.session}
        data_response = requests.post(data_url, json=payload,params=params)
        if self._checkResponse(data_response):
            raw = data_response.json()
            entries = raw["ERGEBNIS"].values()
            for dic in entries:
                data = dic["DATENSATZ"]
                mid=data["MITGLIEDSNUMMER"]
                gender = data["ANREDE"]
                nn = data["NACHNAME"]
                fn = data["VORNAME"]
                mf = data["MULTIFELD_3"]# str
                endv = data['AUSTRITT(VEREIN)'] #STR  2099-12-31
                geb= data['GEBURTSDATUM'] #STR  2099-12-31
                abt = data['ABTEILUNGSNAME']
                enda = data['AUSTRITT(ABTEILUNG)'] #str: 2099-12-31  
                print(f"{mid}) {nn}/{fn} Geb: {geb} gender: {gender} Code: {mf} Abt: {abt} EOL: {endv}")
        if mf:
            checkGroup.append(mf)    
    '''
            
    def members(self):
        function="SUCHE_INDIV"
        app="auswertungen"
        data_url = f"{REST_BASE_URL}applikation/{app}/api/{function}"
        params = {"SESSION": self.session, "AUSWERTUNG_ID":6}
        data_response = requests.get(data_url,params=params)
        if self._checkResponse(data_response):
            raw = data_response.json()["ERGEBNIS"]
            if len(raw)==0:
                Log.error("No data avaliable-SERVERE Error - exiting")
                return None
            errCode = raw["STATUSCODE"]
            if errCode < 0:
                Log.error("Error %d message: %s",errCode,raw["STATUS"] )
                return None

            return self.createModel(raw)
        return None
    
    def _mkDate(self,dateString):
        if len(dateString) == 0 or dateString.startswith("00"):
            dateString="1969-07-16" #Moon landing Apollo 11
        return datetime.strptime(dateString, '%Y-%m-%d').date().isoformat() 
    
    def createModel(self,jsonDic):
        sMembers= {} #key=id, value. A TsvMember with its Abteilungs-data (definedfrom Sewobe)
        mbrCount =0        
        entries = jsonDic.values()
        for dic in entries:
            data = dic["DATENSATZ"]
            mid=data["MITGLIEDSNUMMER"]
            section = data['ABTEILUNGSNAME']
            payDate = self._mkDate(data['AUSTRITT(ABTEILUNG)']) #str: 2099-12-31  
            ###we are creating aor appending a TsvMember. We do not pass all vars to a new method - not nice code
            mbr = sMembers.get(mid,None)
            if not mbr:
                anr = data["ANREDE"]
                gender = "M" if anr=="Herr" else "F"
                nn = data["NACHNAME"]
                fn = data["VORNAME"]
                access = data["MULTIFELD_3"]# str
                #endv = self._mkdate(data['AUSTRITT(VEREIN)']) #STR  2099-12-31
                birthdate= self._mkDate(data['GEBURTSDATUM']) #STR  2099-12-31
                    
                mbr=TsvMember(mid,fn,nn,access,gender,birthdate)
                sMembers[mid]=mbr
                mbrCount += 1

            mbr.addPay(payDate,section) 
        Log.info("Read %d entries from REST",mbrCount)
        return sMembers #dict of TsvMembers - read from Sewobe
        
        
    def printMembers(self,memberList):
        for mbr in memberList:
            print(mbr.display())
        '''
        for dic in entries:
            data = dic["DATENSATZ"]
            mid=data["MITGLIEDSNUMMER"]
            gender = data["ANREDE"]
            nn = data["NACHNAME"]
            fn = data["VORNAME"]
            mf = data["MULTIFELD_3"]# str
            endv = data['AUSTRITT(VEREIN)'] #STR  2099-12-31
            geb= data['GEBURTSDATUM'] #STR  2099-12-31
            abt = data['ABTEILUNGSNAME']
            enda = data['AUSTRITT(ABTEILUNG)'] #str: 2099-12-31  
                   
        print(f"{mid}) {nn}/{fn} Geb: {geb} gender: {gender} Code: {mf} Abt: {abt} EOL: {endv}")
        '''
    
    #Test routine for implementation - prevent hi traffic
    def dumpMbrJson(self):    
        function="SUCHE_INDIV"
        app="auswertungen"
        data_url = f"{REST_BASE_URL}applikation/{app}/api/{function}"
        params = {"SESSION": self.session, "AUSWERTUNG_ID":6}
        data_response = requests.get(data_url,params=params)
        ''' POST TEST
        payload = {"AUSWERTUNG_ID":6}
        data_url = f"{REST_BASE_URL}applikation/{app}/api/{function}"
        params = {"SESSION": self.session}
        data_response = requests.post(data_url, json=payload,params=params)
        '''
        if self._checkResponse(data_response):
            raw = data_response.json()
            errCode = raw["STATUSCODE"]
            if errCode < 0:
                print("Error %d message: %s"%(errCode,raw["STATUS"] ))
                return
            erg = raw["ERGEBNIS"] 
            path = OSTools.getLocalPath(__file__)
            target = OSTools.joinPathes(path, "Sewobe", "data.json") 
            with open(target, "w") as f:
                json.dump(erg, f)
            
            self.createModel(erg)
    
    #Test routine for implementation - prevent hi traffic            
    def readMbrJson(self):
        path = OSTools.getLocalPath(__file__)
        source = OSTools.joinPathes(path, "Sewobe", "data.json") 
        with open(source) as f:
            raw = json.load(f)
        return raw
        
    def _saveSession(self,response):     
        try:
            self.session = response.json().get("SESSION")   
        except ValueError:
            Log.error("Login response is not JSON: %s", response.text)
            return False
        return True
    
    def _checkResponse(self,response):    
        code = response.status_code
        if code != CODE_OK:
            Log.error("Error response:%s", response.text)
            self.lastError = response.text
            return False
        return True
        
class Converter():
    def __init__(self): #key=PK, value=TsvMemeber
        self._connectDB()
        
    def _connectDB(self):
        self.dbSystem = DBAccess()
        self.db = self.dbSystem.connectToDatabase()
        return self.db.isConnected()        
    
    def _readFlags(self):
        stmt="select id,flag from %s"%(SetUpTSVDB.MAINTABLE)
        return self.db.select(stmt)

    ''' full cleanup of old members
    def cleanUp(self):
        TsvDBCreator.eliminateDeadMembers(self):
    '''

    def convert(self,memberDict):
        lostMemberIDs=self.syncFlags(memberDict)
        for pk in lostMemberIDs:
            stmt="UPDATE Mitglieder set flag=1 where id=%d"%(pk)
            self.db.select(stmt)
        data = memberDict.values()
        self.updateMembers(data)
        

    def updateMembers(self,tsvMembers):
        table = SetUpTSVDB.MAINTABLE
        fields = ('id', 'first_name', 'last_name', "access", "gender", "birth_date", "flag")
        main=[]
        sections=[]
        for mbr in tsvMembers:
            main.append(mbr.baseData)
            sections.extend(mbr.sectionData())
        self.db.insertMany(table, fields, main)

        fields=("mitglied_id", "payuntil_date","section")
        table=SetUpTSVDB.BEITRAGTABLE
        self.db.insertMany(table, fields, sections)

    #Statistics. We should create a DB and add some data:
    '''
    def makeImportFindings(self, sections,multiSet, mbrCount,rogue):
        txt=[]
        txt.append("<h2>Import Statistik</h2>")
        txt.append("<ul><li>Importiert:%d</li>" % (mbrCount))
        for key, cnt in multiSet.items():
            txt.append("<li>%s:%d</li>"%(key,cnt))
        txt.append("<li>Nicht im Hauptverein:%d</li>"%(len(rogue)))
        txt.append("<li>Statistik Abteilungen:</li>")
        c = Counter(sections)
        txt.append("<ul>")
        for entry in c:
            txt.append("<li>%s %d</li>"%(entry,c[entry]))
        txt.append("</ul>")
        txt.append("</ul>")
        self.findingsImport=txt
    '''

    def syncFlags(self,memberDict):
        rows=self._readFlags()
        ids = [data[0] for data in rows] #int
        existingMemberCount = len(ids)
        currIds=[int(mbr.getID()) for mbr in memberDict.values()]
        currentMemberCount = len(currIds)
        Log.info("Analyze actual members:%d vs old/unpurged members: %d",currentMemberCount,existingMemberCount)
        revoked=[]
       
        for idFlag in rows: #0=id, 1=flag - data of existing members.
            mbrID = idFlag[0]
            flag = idFlag[1]  #DO NOT overwrite that flag if it has been set? Can be Manual or EOL
            
            if not mbrID in currIds:
                existingMemberCount-=1
                if flag == 0: #not flagged yet
                    Log.info("Member lost:%d",mbrID)
                    revoked.append(mbrID)     
            else:
                validMbr = memberDict.get(str(mbrID),None)
                if validMbr:
                    validMbr.setFlag(flag) #Save the old flag!
                    if flag==1:
                        existingMemberCount-=1
        #the other way:
        newCount=0
        for cid in currIds:
            if not cid in ids:
                newCount+=1
                Log.info("%d) New Member:%d",newCount,cid)
        Log.info("New member count:%d checksum:%d",newCount,(existingMemberCount+newCount))
        return revoked  

    def close(self):
        self.dbSystem.close(self.db)

#Member represents the json data from Sewobe - NOT the data from TSVAcess! 
class TsvMember():
    PAYOK="-"
    def __init__(self,cpid,fn,ln,access,gender,birthdate):
        self.baseData=[cpid,fn,ln,access,gender,birthdate,0]
        self.payData={} # section-> paydate. output must be array of tuple(secion,paydate)
    
    def getID(self):
        return self.baseData[0]
    
    def getName(self):        
        return self.baseData[2]
    
    def getAccess(self):
        return self.baseData[3]

    def setFlag(self,flag):
        self.baseData[6] = flag
        
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
        return self.baseData,">",self.payData

def main():
    rc = RestConnector()
    if rc.login():
        result = rc.members()
        c=Converter()
        c.convert(result)
        c.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        Log.exception("Error in main:")    
    