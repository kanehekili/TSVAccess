'''
Created on Aug 2, 2025

@author: matze
'''
from TsvDBCreator import DBAccess
from TsvAuswertung import BarModel
import TsvDBCreator
import json,io,getopt, sys
from datetime import datetime
import paramiko
import logging
logging.getLogger("paramiko").setLevel(logging.INFO)

from pathlib import Path
import TsvAuswertung


class HandballMembersWeekly():
    RECEIPIENTS = ["mathias.wegmann@tsv-weilheim.com","sylvester.wolf@handamball.de"]
    #RECEIPIENTS = ["mathias.wegmann@tsv-weilheim.com"]
    def __init__(self):
        self.dbSystem=DBAccess()
        self.db = self.dbSystem.connectToDatabase()
    
    def run(self):
        stmt="select first_name, last_name, gender, birth_date, b.section, b.payuntil_date from Mitglieder m join BEITRAG b where m.id=b.mitglied_id and b.section='Handball' and (payuntil_date > CURDATE() or payuntil_date is Null)"
        rows = self.db.selectAsJson(stmt)
        self.db.close()
        ''' works- but we want buffer
        with open("handball.json", "w") as f:
            json.dump(rows, f, indent=2, cls=TsvDBCreator.DateTimeEncoder)
        '''
        jString = json.dumps(rows, indent=2, cls=TsvDBCreator.DateTimeEncoder)
        buffer = io.BytesIO(jString.encode("utf-8"))
        
        attachment = (buffer,"handball.json")
        msg = "Aktueller Stand der Mitglieder Handball. HandballMembersWeekly Service des TSV Access Systems"
        subject = "Handball Status - TSVAccess"
        self.dbSystem.genericEmail(self.db, subject, msg, self.RECEIPIENTS,attachment)

'''
Idea: send the current count of users in Kraftraum every 15 mins to Datenliebe -> TSV website
'''

class DatenliebeBasic():        
    def __init__(self):
        self.dbSystem=DBAccess()
        self.db = self.dbSystem.connectToDatabase()
        self.ts = datetime.now().strftime("%y.%m.%d_%H.%M.%S")
    
    #main run - overwrite getFilename and runQuery...   
    def run(self):
        data = self.runQuery()
        fn = self.getFilename()+self.ts+".json"
        self._sendJson(fn,data)
        self.db.close()
        
    #expect a base filename. TS and ending is added here 
    def getFilename(self):
        return "test"       
    
    #we expect a valid json dict    
    def runQuery(self):
        #rows = self.db.selectAsJson(stmt)
        data = {"Entry1":"Value1","Entry2":"Value2"}
        return json.dumps(data)
    
    def _sendJson(self,filename, json_data):
        SCRIPT_DIR = Path(__file__).parent
        config_path = "%s/data/.config.json" % SCRIPT_DIR
        config = json.loads(Path(config_path).read_text())
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=config['DL_Host'],
                username=config['DL_User'],
                password=config['DL_Pwd']
            )
            
            sftp = ssh.open_sftp()
            # Convert JSON to string and send as file
            json_str = json.dumps(json_data)
            with sftp.file(f"/access/{filename}", 'w') as f:
                f.write(json_str)
            
            sftp.close()
            ssh.close()
            return True
            
        except Exception as e:
            print(f"DL Service Error: {e}")
            return False    
        
class DatenliebeCurrent(DatenliebeBasic):
    def __init__(self):
        DatenliebeBasic.__init__(self)
    
    def runQuery(self):
        #date_condition="2025-08-01"
        #time_condition="11:15:00"        
        stmt = f"""
        SELECT COUNT(*) as total_count
        FROM (
            SELECT mitglied_id
            FROM Zugang 
            WHERE activity = 'Kraftraum'
              AND DATE(access_date) = CURDATE()
              AND (
                (CURTIME() <= '13:30:00' AND TIME(access_date) <= CURTIME())
                OR
                (CURTIME() > '13:30:00' AND TIME(access_date) > '13:30:00' AND TIME(access_date) <= CURTIME())
              )
            GROUP BY mitglied_id
            HAVING COUNT(*) = 1
        ) AS sub;
        """
        #stmt = self.__testStatement()
        result = self.db.select(stmt)
        if result:
            count= result[0][0]
        else:
            count=0
        data={}
        data["current"]=count
        return json.dumps(data)
    
    def getFilename(self):
        return "current"     
        
    def __testStatement(self):
        test_date = "2025-06-01"
        test_time = "11:15:00"

        test_time_obj = datetime.strptime(test_time, '%H:%M:%S').time()
        cutoff_time = datetime.strptime('13:30:00', '%H:%M:%S').time()
        
        if test_time_obj <= cutoff_time:
            # Before 13:30 - count morning entries only
            stmt = f"""
            SELECT COUNT(*) as total_count
            FROM (
                SELECT mitglied_id
                FROM Zugang 
                WHERE activity = 'Kraftraum'
                  AND DATE(access_date) = '{test_date}'
                  AND TIME(access_date) <= '{test_time}'
                GROUP BY mitglied_id 
                HAVING COUNT(*) = 1
            ) as morning_visitors
            """
        else:
            # After 13:30 - count afternoon entries only  
            stmt = f"""
            SELECT COUNT(*) as total_count
            FROM (
                SELECT mitglied_id
                FROM Zugang 
                WHERE activity = 'Kraftraum'
                  AND DATE(access_date) = '{test_date}'
                  AND TIME(access_date) > '13:30:00'
                  AND TIME(access_date) <= '{test_time}'
                GROUP BY mitglied_id 
                HAVING COUNT(*) = 1
            ) as afternoon_visitors
            """
        return stmt    

'''
Idea: send the median values of the last year in Kraftraum every week to Datenliebe -> TSV website
'''
class DatenliebeMedian(DatenliebeBasic):
    def __init__(self):
        DatenliebeBasic.__init__(self)

    def runQuery(self):
        bm = BarModel()
        res = bm.collectBlockUsage('Kraftraum',TsvAuswertung.MODE_MEDIAN)
        #{'9-12': [31, 36, 27, 23, 35, 17, 21], '15-18': [24, 25, 23, 24, 24, 17, 16], '18-20': [27, 30, 26, 25, 21, 8, 10], '20-22': [16, 17, 13, 11, 9, 1, 1]}
        return json.dumps(res)  
    
    def getFilename(self):
        return "weekly" 

def parseOptions(args):
    
    try:
        opts, args = getopt.getopt(args[1:], "hab", ["handballMembers","dl_daily","dl_weekly"])
        if len(opts) == 0:
            printUsage()
    except getopt.GetoptError:
        printUsage()
        sys.exit(2)
    
    for o, a in opts:
        if o in ("-h", "--handballMembers"):
            HandballMembersWeekly().run()
        elif o in ("-a","--dl_daily"):
            DatenliebeCurrent().run()
        elif o in ("-b","--dl_weekly"):
            DatenliebeMedian().run()        
        else:
            printUsage()

def printUsage():
    print("External service commands: \n"\
          "\t-h > (--handballMembers) \n"
          "\t-a > (--dl_daily) Every 15 min \n"
          "\t-b > (--dl_weekly) Weekly median \n"
          "This module contains multiple services - so a switch is mandatory\n"
          )

if __name__ == '__main__':
    sys.exit(parseOptions(sys.argv))
