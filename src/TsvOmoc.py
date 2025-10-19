'''
Created on Oct 3, 2025

@author: matze

The omoc rest implementation. Used by the TsvAuswertung, but could be used as standalone,
if TsvDBCreator is integrated... 
See @BarModel how to create DB and the connector... 
'''
import DBTools,requests
from datetime import datetime,timedelta,time
from TsvDBCreator import SetUpTSVDB

Log = DBTools.Log

class OmocRest():
    FILTER_SZ = ["TSV Sportzentrum","TSV Stadion"]
    FILTER_ZOTZE=["TSV Zotzenmühlweg"]
    FILTER_HALLEN=["Hardtschule","Röntgenschule","Jahnhalle-Halle","Ammerschule-Halle","FOS/BOS-Halle"]
    LAST_CHECK=None
    def __init__(self,safeConnector): #this is the Barmodel, that has a safe atomic select
        self._initCredentials(safeConnector)
        
    
    def _initCredentials(self,sc):
        stmt="select * from %s"%(SetUpTSVDB.OMOCTABLE)
        rows = sc.atomicSelect(stmt)
        if len(rows)==0:
            Log.warning("No omoc config - aborting")
            return
        data=rows[0]
        kennung= data[0]
        self.key = data[1]
        self.pwd =data[2]
        self.url = data[3]%(kennung)

    
    def getCurrent(self,full=False,search=None): 
        now = datetime.now()
        datestr = now.strftime("%d%m%Y")
        if OmocRest.LAST_CHECK and OmocResult.CACHED_RESULT:
            td = now-self.LAST_CHECK
            if td.seconds < 4*60*60:
                Log.info("Sending cached result")
                return OmocResult.CACHED_RESULT 
        #datestr = "16102025"
        params = {    
            "datumvon": datestr,
            "datumbis": datestr,
            "uhrzeitvon": "0700",
            "uhrzeitbis": "2200"
        }
        result = requests.get(self.url, params=params, auth=(self.key, self.pwd))
        OmocResult.CACHED_RESULT = OmocResult().parse(result.json(),full,search)
        OmocRest.LAST_CHECK = now
        return OmocResult.CACHED_RESULT

        

class OmocResult():
    CACHED_RESULT=None
    def __init__(self):
        pass
 
    def parse(self,omocJson,full=False,roomSearch=None):
        events=[]
        data = omocJson["data"]
        for entry in data:
            evt = OmocEvent()
            if evt.inRoom(entry,roomSearch):
                evt.parse(entry,full)
                events.append(evt)
        return events
    
class OmocFormatter():
    INTERVAL=4 # 4 hours
    def __init__(self, omocEvents):
        self.resultDic={}
        self.generate(omocEvents)

    def get_time_bounds(self,courses, current_time=None):
        """
        Return start_min, end_min for dynamic schedule,
        rounded to nearest 15 minutes, clipped at current_time.
        """
        if current_time is None:
            current_time = datetime.now().time()
        now_min = current_time.hour * 60 + current_time.minute
    
        if not courses:
            # no courses → schedule starts at current time, round down to 15
            start_min = (now_min // 15) * 15
            end_min = start_min + 60  # show 1 hour by default
            return start_min, end_min
    
        # Courses exist
        min_start = min(c["start"].hour * 60 + c["start"].minute for c in courses)
        max_end = max(c["end"].hour * 60 + c["end"].minute for c in courses)
    
        # Clip start to max(current_time, earliest course)
        start_min = max(min_start, now_min)
        start_min = (start_min // 15) * 15
    
        # Round up end to nearest 15
        end_min = ((max_end + 14) // 15) * 15
    
        # Safety: if no future courses, still show at least 1 hour
        if start_min >= end_min:
            end_min = start_min + 60
    
        return start_min, end_min


    def assign_slots(self,courses, current_time=None):
        """Assign slot_index and compute display_start for visual clipping."""
        if current_time is None:
            current_time = datetime.now().time()
        now_min = current_time.hour * 60 + current_time.minute
    
        # Sort courses by start
        courses = sorted(courses, key=lambda c: (c["start"], c["end"]))
        slots_end_time = []
    
        for course in courses:
            # slot index
            placed = False
            for idx, end_time in enumerate(slots_end_time):
                if end_time <= course["start"]:
                    course["slot_index"] = idx
                    slots_end_time[idx] = course["end"]
                    placed = True
                    break
            if not placed:
                course["slot_index"] = len(slots_end_time)
                slots_end_time.append(course["end"])
    
            # display_start = max(start, now)
            start_min = course["start"].hour * 60 + course["start"].minute
            end_min = course["end"].hour * 60 + course["end"].minute
            course["display_start"] = max(start_min, now_min)
            course["display_end"] = end_min
    
        return courses

    def generatetest(self,omocEvents):
        now = datetime.now()
        start = now.time()
        start = time(8,0) #FAKE
        
        # Replace this with real DB query
        sample = [
            {"name": "Math", "room": "101", "start": time(9, 0), "end": time(9, 45)},
            {"name": "Physics", "room": "202", "start": time(9, 15), "end": time(10, 15)},
            {"name": "Biology", "room": "303", "start": time(9, 30), "end": time(10, 0)},
            {"name": "anhang", "M2": "101", "start": time(9, 45), "end": time(10, 30)},
        ]
        
        data = self.assign_slots(sample,start)
        day_start, day_end = self.get_time_bounds(sample,start)
        self.resultDic["rooms"]=data
        self.resultDic["start"] = day_start
        self.resultDic["end"] = day_end

    def generate(self,omocEvents):
        now = datetime.now()
        start= now.time()
        end_dt = now + timedelta(hours=4)
        end = end_dt.time()
        #start = time(8,0) #FAKE
        #end = time(23,59)#Fake
        
        if start > end:
            end = time(23, 59, 59)
        
        rawData=[]
        for evt in omocEvents:
            if evt.timeTo >= start and evt.timeFrom < end:            
                dic ={}
                dic['room']=evt.rooms[0]
                dic['name']=evt.title
                dic['start'] = evt.timeFrom
                dic['end'] = evt.timeTo
                rawData.append(dic)
                
        data = self.assign_slots(rawData,start)
        day_start, day_end = self.get_time_bounds(rawData,start)
        self.resultDic["rooms"]=data
        self.resultDic["start"] = day_start
        self.resultDic["end"] = day_end        
    
'''
idcode > 4dffece78a
buchungsnummer > 003232
veranstaltungskurztitel > Schulsport
termintyp > S
buchung_vom > Wed, 26 Mar 2025 08:58:43 GMT
buchung_geandert_am > Wed, 26 Mar 2025 09:06:46 GMT
datum_von > Thu, 02 Oct 2025 00:00:00 GMT
datum_von_timestamp > 1759356000
datum_bis > Thu, 02 Oct 2025 00:00:00 GMT
datum_bis_timestamp > 1759356000
datum_von_gesamt > Tue, 16 Sep 2025 00:00:00 GMT
datum_von_gesamt_timestamp > 1757973600
datum_bis_gesamt > Thu, 30 Jul 2026 00:00:00 GMT
datum_bis_gesamt_timestamp > 1785448799
uhrzeit_von > 07:35
uhrzeit_bis > 16:35
terminliste_gesamt > 16.09.25 07:35 - 16:35; 18.09.25 07:35 - 16:35; 22.09.25 07:35 - 16:35; 23.09.25 07:35 - 16:35; 25.09.25 07:35 - 16:35; 29.09.25 07:35 - 16:35; 30.09.25 07:35 - 16:35; 02.10.25 07:35 - 16:35; 06.10.25 07:35 - 16:35; 07.10.25 07:35 - 16:35; 09.10.25 07:35 - 16:35; 13.10.25 07:35 - 16:35; 14.10.25 07:35 - 16:35; 16.10.25 07:35 - 16:35; 20.10.25 07:35 - 16:35; 21.10.25 07:35 - 16:35; 23.10.25 07:35 - 16:35; 27.10.25 07:35 - 16:35; 28.10.25 07:35 - 16:35; 30.10.25 07:35 - 16:35; 10.11.25 07:35 - 16:35; 11.11.25 07:35 - 16:35; 13.11.25 07:35 - 16:35; 17.11.25 07:35 - 16:35; 18.11.25 07:35 - 16:35; 20.11.25 07:35 - 16:35; 24.11.25 07:35 - 16:35; 25.11.25 07:35 - 16:35; 27.11.25 07:35 - 16:35; 01.12.25 07:35 - 16:35; 02.12.25 07:35 - 16:35; 04.12.25 07:35 - 16:35; 08.12.25 07:35 - 16:35; 09.12.25 07:35 - 16:35; 11.12.25 07:35 - 16:35; 15.12.25 07:35 - 16:35; 16.12.25 07:35 - 16:35; 18.12.25 07:35 - 16:35; 08.01.26 07:35 - 16:35; 12.01.26 07:35 - 16:35; 13.01.26 07:35 - 16:35; 15.01.26 07:35 - 16:35; 19.01.26 07:35 - 16:35; 20.01.26 07:35 - 16:35; 22.01.26 07:35 - 16:35; 26.01.26 07:35 - 16:35; 27.01.26 07:35 - 16:35; 29.01.26 07:35 - 16:35; 02.02.26 07:35 - 16:35; 03.02.26 07:35 - 16:35; 05.02.26 07:35 - 16:35; 09.02.26 07:35 - 16:35; 10.02.26 07:35 - 16:35; 12.02.26 07:35 - 16:35; 23.02.26 07:35 - 16:35; 24.02.26 07:35 - 16:35; 26.02.26 07:35 - 16:35; 02.03.26 07:35 - 16:35; 03.03.26 07:35 - 16:35; 05.03.26 07:35 - 16:35; 09.03.26 07:35 - 16:35; 10.03.26 07:35 - 16:35; 12.03.26 07:35 - 16:35; 16.03.26 07:35 - 16:35; 17.03.26 07:35 - 16:35; 19.03.26 07:35 - 16:35; 23.03.26 07:35 - 16:35; 24.03.26 07:35 - 16:35; 26.03.26 07:35 - 16:35; 13.04.26 07:35 - 16:35; 14.04.26 07:35 - 16:35; 16.04.26 07:35 - 16:35; 20.04.26 07:35 - 16:35; 21.04.26 07:35 - 16:35; 23.04.26 07:35 - 16:35; 27.04.26 07:35 - 16:35; 28.04.26 07:35 - 16:35; 30.04.26 07:35 - 16:35; 04.05.26 07:35 - 16:35; 05.05.26 07:35 - 16:35; 07.05.26 07:35 - 16:35; 11.05.26 07:35 - 16:35; 12.05.26 07:35 - 16:35; 18.05.26 07:35 - 16:35; 19.05.26 07:35 - 16:35; 21.05.26 07:35 - 16:35; 08.06.26 07:35 - 16:35; 09.06.26 07:35 - 16:35; 11.06.26 07:35 - 16:35; 15.06.26 07:35 - 16:35; 16.06.26 07:35 - 16:35; 18.06.26 07:35 - 16:35; 22.06.26 07:35 - 16:35; 23.06.26 07:35 - 16:35; 25.06.26 07:35 - 16:35; 29.06.26 07:35 - 16:35; 30.06.26 07:35 - 16:35; 02.07.26 07:35 - 16:35; 06.07.26 07:35 - 16:35; 07.07.26 07:35 - 16:35; 09.07.26 07:35 - 16:35; 13.07.26 07:35 - 16:35; 14.07.26 07:35 - 16:35; 16.07.26 07:35 - 16:35; 20.07.26 07:35 - 16:35; 21.07.26 07:35 - 16:35; 23.07.26 07:35 - 16:35; 27.07.26 07:35 - 16:35; 28.07.26 07:35 - 16:35; 30.07.26 07:35 - 16:35; 
terminliste_gesamt_timestamp > [[1758000900,1758033300],[1758173700,1758206100],[1758519300,1758551700],[1758605700,1758638100],[1758778500,1758810900],[1759124100,1759156500],[1759210500,1759242900],[1759383300,1759415700],[1759728900,1759761300],[1759815300,1759847700],[1759988100,1760020500],[1760333700,1760366100],[1760420100,1760452500],[1760592900,1760625300],[1760938500,1760970900],[1761024900,1761057300],[1761197700,1761230100],[1761546900,1761579300],[1761633300,1761665700],[1761806100,1761838500],[1762756500,1762788900],[1762842900,1762875300],[1763015700,1763048100],[1763361300,1763393700],[1763447700,1763480100],[1763620500,1763652900],[1763966100,1763998500],[1764052500,1764084900],[1764225300,1764257700],[1764570900,1764603300],[1764657300,1764689700],[1764830100,1764862500],[1765175700,1765208100],[1765262100,1765294500],[1765434900,1765467300],[1765780500,1765812900],[1765866900,1765899300],[1766039700,1766072100],[1767854100,1767886500],[1768199700,1768232100],[1768286100,1768318500],[1768458900,1768491300],[1768804500,1768836900],[1768890900,1768923300],[1769063700,1769096100],[1769409300,1769441700],[1769495700,1769528100],[1769668500,1769700900],[1770014100,1770046500],[1770100500,1770132900],[1770273300,1770305700],[1770618900,1770651300],[1770705300,1770737700],[1770878100,1770910500],[1771828500,1771860900],[1771914900,1771947300],[1772087700,1772120100],[1772433300,1772465700],[1772519700,1772552100],[1772692500,1772724900],[1773038100,1773070500],[1773124500,1773156900],[1773297300,1773329700],[1773642900,1773675300],[1773729300,1773761700],[1773902100,1773934500],[1774247700,1774280100],[1774334100,1774366500],[1774506900,1774539300],[1776058500,1776090900],[1776144900,1776177300],[1776317700,1776350100],[1776663300,1776695700],[1776749700,1776782100],[1776922500,1776954900],[1777268100,1777300500],[1777354500,1777386900],[1777527300,1777559700],[1777872900,1777905300],[1777959300,1777991700],[1778132100,1778164500],[1778477700,1778510100],[1778564100,1778596500],[1779082500,1779114900],[1779168900,1779201300],[1779341700,1779374100],[1780896900,1780929300],[1780983300,1781015700],[1781156100,1781188500],[1781501700,1781534100],[1781588100,1781620500],[1781760900,1781793300],[1782106500,1782138900],[1782192900,1782225300],[1782365700,1782398100],[1782711300,1782743700],[1782797700,1782830100],[1782970500,1783002900],[1783316100,1783348500],[1783402500,1783434900],[1783575300,1783607700],[1783920900,1783953300],[1784007300,1784039700],[1784180100,1784212500],[1784525700,1784558100],[1784612100,1784644500],[1784784900,1784817300],[1785130500,1785162900],[1785216900,1785249300],[1785389700,1785422100]]
anzahl_stunden_gesamt > 990.00
vorname > 
name > 
name_firma > 
raumliste > Landkreis Jahnhalle-Halle Süd, Landkreis Jahnhalle-Halle Mitte, Landkreis Jahnhalle-Halle Nord
raumliste_ids > 7702,7703,7710

'idcode': '4d9a952c0c', 'buchungsnummer': '003359', 'veranstaltungskurztitel': 'Reha-Wirbelsäule', 
'termintyp': 'S', 'buchung_vom': 'Wed, 26 Mar 2025 11:04:12 GMT', 'buchung_geandert_am': 'Tue, 17 Jun 2025 14:44:34 GMT', 
'datum_von': 'Thu, 02 Oct 2025 00:00:00 GMT', 'datum_von_timestamp': 1759356000, 'datum_bis': 'Thu, 02 Oct 2025 00:00:00 GMT', 
'datum_bis_timestamp': 1759356000, 'datum_von_gesamt': 'Thu, 18 Sep 2025 00:00:00 GMT', 
'datum_von_gesamt_timestamp': 1758146400, 'datum_bis_gesamt': 'Thu, 30 Jul 2026 00:00:00 GMT', 
'datum_bis_gesamt_timestamp': 1785448799, 'uhrzeit_von': '19:00', 'uhrzeit_bis': '20:00', '
terminliste_gesamt': '18.09.25 19:00 - 20:00; 25.09.25 19:00 - 20:00; 02.10.25 19:00 - 20:00; 09.10.25 19:00 - 20:00; 16.10.25 19:00 - 20:00; 23.10.25 19:00 - 20:00; 30.10.25 19:00 - 20:00; 13.11.25 19:00 - 20:00; 20.11.25 19:00 - 20:00; 27.11.25 19:00 - 20:00; 04.12.25 19:00 - 20:00; 11.12.25 19:00 - 20:00; 18.12.25 19:00 - 20:00; 08.01.26 19:00 - 20:00; 15.01.26 19:00 - 20:00; 22.01.26 19:00 - 20:00; 29.01.26 19:00 - 20:00; 05.02.26 19:00 - 20:00; 12.02.26 19:00 - 20:00; 26.02.26 19:00 - 20:00; 05.03.26 19:00 - 20:00; 12.03.26 19:00 - 20:00; 19.03.26 19:00 - 20:00; 26.03.26 19:00 - 20:00; 16.04.26 19:00 - 20:00; 23.04.26 19:00 - 20:00; 30.04.26 19:00 - 20:00; 07.05.26 19:00 - 20:00; 21.05.26 19:00 - 20:00; 11.06.26 19:00 - 20:00; 18.06.26 19:00 - 20:00; 25.06.26 19:00 - 20:00; 02.07.26 19:00 - 20:00; 09.07.26 19:00 - 20:00; 16.07.26 19:00 - 20:00; 23.07.26 19:00 - 20:00; 30.07.26 19:00 - 20:00; ', 'terminliste_gesamt_timestamp': '[[1758214800,1758218400],[1758819600,1758823200],[1759424400,1759428000],[1760029200,1760032800],[1760634000,1760637600],[1761238800,1761242400],[1761847200,1761850800],[1763056800,1763060400],[1763661600,1763665200],[1764266400,1764270000],[1764871200,1764874800],[1765476000,1765479600],[1766080800,1766084400],[1767895200,1767898800],[1768500000,1768503600],[1769104800,1769108400],[1769709600,1769713200],[1770314400,1770318000],[1770919200,1770922800],[1772128800,1772132400],[1772733600,1772737200],[1773338400,1773342000],[1773943200,1773946800],[1774548000,1774551600],[1776358800,1776362400],[1776963600,1776967200],[1777568400,1777572000],[1778173200,1778176800],[1779382800,1779386400],[1781197200,1781200800],[1781802000,1781805600],[1782406800,1782410400],[1783011600,1783015200],[1783616400,1783620000],[1784221200,1784224800],[1784826000,1784829600],[1785430800,1785434400]]', 
'anzahl_stunden_gesamt': '37.00', 'vorname': 'Manuel', 'name': 'Schöpf', 'name_firma': 'Geschäftsstellenleiter', 
'raumliste': 'TSV Sportzentrum-Mehrzweckraum Altbau', 'raumliste_ids': '7720'}
>>TSV Sportzentrum

'''
   
class OmocEvent():
    KEYS =["idcode","veranstaltungskurztitel","datum_von_timestamp","uhrzeit_von","uhrzeit_bis","raumliste"]
    OPTKEYS=["vorname","name","name_firma"]
    def __init__(self):
        self.id=0
        self.title="n.a"
        self.dayDate = None
        self.timeFrom=None
        self.timeTo=None
        self.rooms=[]
        self.optional = False

    def parse(self,aDic,optional=False):
        self.saveEntry(aDic)
        if optional:
            self.saveOptional(aDic)
    
    def inRoom(self,aDic,roomList):
        if roomList is None:
            return True
        myRooms = aDic[OmocEvent.KEYS[5]]
        
        for item in roomList:
            if item in myRooms:
                return True
        return False
        
    def saveEntry(self,aDic):
        self.id = aDic[OmocEvent.KEYS[0]]
        self.title = aDic[OmocEvent.KEYS[1]]
        ts = int(aDic[OmocEvent.KEYS[2]])
        self.dayDate = datetime.fromtimestamp(ts).date()
        formatCode="%H:%M"
        self.timeFrom = datetime.strptime(aDic[OmocEvent.KEYS[3]],formatCode).time()
        self.timeTo = datetime.strptime(aDic[OmocEvent.KEYS[4]],formatCode).time()
        self.rooms = aDic[OmocEvent.KEYS[5]].split(',')   
        
    def saveOptional(self,aDic):
        self.optional = True
        self.firstName = aDic[OmocEvent.OPTKEYS[0]]
        self.lastName = aDic[OmocEvent.OPTKEYS[1]]
        self.company = aDic[OmocEvent.OPTKEYS[2]]   
        
    def __str__(self):
        if self.optional:
            return f'OmocEvent<{self.title}:{self.dayDate} ({self.timeFrom} > {self.timeTo}) | {self.firstName} {self.lastName} [{self.company}]  = {self.rooms}>'
            
        return f'OmocEvent<{self.title}:{self.dayDate} ({self.timeFrom} > {self.timeTo}) = {self.rooms}>'         
 
if __name__ == '__main__':
    pass