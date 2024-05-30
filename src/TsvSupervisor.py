'''
Created on 15 Apr 2024
Basic check of availability of the access devices. Sends mail on failure.
Later we might feed a dashbord
@author: matze
'''

import os, DBTools, time
from TsvDBCreator import SetUpTSVDB

ACCESSPOINTS ={"192.168.178.113":"tsvaccess1",
"192.168.178.99":"tsvaccess2",
"192.168.178.175":"tsvaccess3",
"192.168.178.172":"tsvaccess4",
"192.168.178.184":"tsvaccess5",
"192.168.178.188":"tsvaccess6"
#,"localhost":"me"
}
FREQ=60 #Check frequency in seconds

DBTools.OSTools.setupRotatingLogger("TSVSupervisor", True)
Log = DBTools.Log

tsvDB = SetUpTSVDB(SetUpTSVDB.DATABASE)

class Monitor():
    def __init__(self):
        self.devices=[]
        for ip,hn in ACCESSPOINTS.items():
            self.devices.append(Device(ip,hn))
            

    def checkDevice(self,hostnameOrIP):
        isUp  = os.system(f"ping -c 1 {hostnameOrIP}"+ "> /dev/null 2>&1") == 0
        return isUp
    
    def checkAll(self):
        #faulty=[]
        data =[]
        for dev in self.devices:
            changed = dev.statusChange(self.checkDevice(dev.ip))
            #if dev.isFailReport():
            #    faulty.append(dev.hostname)
            if changed:
                Log.info("Device %s online:%s",dev.hostname,dev.isOnline())
                dev.addStatusString(data)    

        #if faulty:
        #    Log.info("Sending mail: %s",faulty)
        if data:
            txt =", ".join(data)
            Log.info("Sending mail:%s",txt)
            self.prepareMail(txt)
            
    def prepareMail(self,failNames):
        txt = " Warnung\n Folgende Geräte haben den Zustand geändert: \n\n %s\n\n Sent by TSVSupervisor"%(failNames)
        tsvDB.sendEmail("Device offline warning",False,txt)  

    def runDeamon(self):
        self.running = True
        while self.running:
            self.checkAll()
            time.sleep(FREQ) 

class Device():
    def __init__(self,ip,hostname):
        self.ip = ip
        self.hostname=hostname
        self._pingSuccess = True
        self._msgSent=False
    
    def statusChange(self,pingOK):
        currPing = self._pingSuccess
        currMsg = self._msgSent
        self._pingSuccess = pingOK
        if pingOK:
            self._msgSent=False
        statusChanged = currPing != self._pingSuccess or currMsg != self._msgSent
        return statusChanged
            
    def isFailReport(self):
        if self._pingSuccess:
            return False
        if not self._msgSent:
            self._msgSent=True
            return True
        return False
    
    def addStatusString(self,data):
        txt = self.hostname+" online:"+str(self._pingSuccess)
        data.append(txt)
    
    def isOnline(self):
        return self._pingSuccess
    
if __name__ == '__main__':
    m = Monitor()
    m.runDeamon()