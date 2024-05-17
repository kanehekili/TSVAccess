'''
Created on 15 Apr 2024
Basic check of availability of the access devices
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
}
DBTools.OSTools.setupRotatingLogger("TSVSupervisor", True)
Log = DBTools.Log

tsvDB = SetUpTSVDB(SetUpTSVDB.DATABASE)

class Monitor():
    def __init__(self):
        self.mailedAPs=[]

    def checkDevice(self,hostnameOrIP):
        isUp  = os.system(f"ping -c 1 {hostnameOrIP}") == 0
        return isUp
    
    def checkAll(self):
        faulty=[]
        for ip,hostname in ACCESSPOINTS.items():
            if not self.checkDevice(ip):
                faulty.append(hostname)
        #that is shit:
        a = set(faulty)
        b =set(self.mailedAPs)
        
        self.mailedAPs = list(a-b)
        print("a faulty",faulty)
        print("b alreday sent:",b)
        print("result data to be mailed",self.mailedAPs)
        
        if self.mailedAPs:
            faultyNames =",".join(self.mailedAPs)
            if faultyNames:
                print("TEST:",faultyNames)
            else:
                print("still faulty but no change")
            #self.prepareMail(faultyNames)
            
    def prepareMail(self,failNames):
        tsvDB.sendEmail("Device offline warning",False,failNames)  

    def runDeamon(self):
        self.running = True
        while self.running:
            self.checkAll()
            time.sleep(2.0) 
            print("test run ")

if __name__ == '__main__':
    m = Monitor()
    m.runDeamon()