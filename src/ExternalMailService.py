'''
Created on Aug 2, 2025

@author: matze
'''
from TsvDBCreator import DBAccess
import TsvDBCreator
import json,io,getopt, sys


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


def parseOptions(args):
    
    try:
        opts, args = getopt.getopt(args[1:], "h", ["handballMembers"])
        if len(opts) == 0:
            printUsage()
    except getopt.GetoptError:
        printUsage()
        sys.exit(2)
    
    for o, a in opts:
        if o in ("-h", "--handballMembers"):
            HandballMembersWeekly().run()
        else:
            printUsage()

def printUsage():
    print("External service commands: \n"\
          "\t-h > (--handballMembers) \n"
          "This module may contain multiple services - so a switch is mandatory\n"
          )

if __name__ == '__main__':
    sys.exit(parseOptions(sys.argv))
