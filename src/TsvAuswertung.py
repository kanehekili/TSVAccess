#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Created on Apr 3, 2023
Show graphs per Month or year.
@author: matze
'''
# https://www.geeksforgeeks.org/create-a-bar-chart-from-a-dataframe-with-plotly-and-flask/
# https://github.com/alanjones2/Flask-Plotly/tree/main/plotly
# using  plotly and flask. 
from flask import Flask, render_template, request  # , has_request_context, session, url_for
import werkzeug
import json
import plotly
#import plotly.express as px
import plotly.graph_objs as go
from datetime import datetime, timedelta
import random
from DBTools import OSTools
from TsvDBCreator import SetUpTSVDB
import DBTools
import sys, os
import TsvDBCreator
import time

OSTools.setupRotatingLogger("TSVAuswertung", True)
Log = DBTools.Log
werkzeug.serving._log_add_style = False
app = Flask(__name__,
            static_url_path='',
            static_folder='web/static',
            template_folder='web/templates')

'''
** Kraftraum Section = TsvDBCreator.ACTIVITY_KR
'''


@app.route('/' + TsvDBCreator.ACTIVITY_KR)
def statisticsKraftraum():
    return statisticsTemplate(TsvDBCreator.ACTIVITY_KR,TsvDBCreator.LOC_KRAFTRAUM)


@app.route('/accessKR')  # Access kraftraum
def visitorsKraftraum():
    # https://stackoverflow.com/questions/58996870/update-flask-web-page-with-python-script
    #people = barModel.currentVisitorPictures(TsvDBCreator.ACTIVITY_KR, 150)  # checkout after 150 mins
    people = barModel.currentVisitorPictures(TsvDBCreator.ACTIVITY_KR)  
    logo_path = "tsv_logo_100.png"
    dynamic_activity = TsvDBCreator.ACTIVITY_KR   
    pv='/' 
    return render_template('access.html', parentView=pv, people=people, logo_path=logo_path, dynamic_activity=dynamic_activity, location_count=len(people))

    
@app.route('/' + TsvDBCreator.ACTIVITY_KR + "Usage")
def testVerweilzeitKraftraum():
    # TODO -under construction
    dates, counts = barModel.dailyHoursUsage(TsvDBCreator.ACTIVITY_KR)  # reside time per hour     
    data = [go.Bar(
       x=dates,
       y=counts,
       marker_color='#FFA500'
    )]
    layout = go.Layout(title="Verweilzeit " + TsvDBCreator.ACTIVITY_KR, xaxis=dict(title="Stunde"), yaxis=dict(title="Anzahl"))
    fig = go.Figure(data=data, layout=layout)
    fig.update_xaxes(showgrid=True, nticks=24, tickmode="auto")
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    logo_path = "tsv_logo_100.png"
    dynamic_activity = TsvDBCreator.ACTIVITY_KR
    return render_template('index.html', graphJSON=graphJSON, logo_path=logo_path, dynamic_activity=dynamic_activity)        

'''
Group section
'''
'''
@app.route('/' + TsvDBCreator.ACTIVITY_GYM)
def statisticsGroupFitnesse():
    return statisticsTemplate(TsvDBCreator.ACTIVITY_GYM)
'''

@app.route('/' + TsvDBCreator.ACTIVITY_GYM+"SKR")
def statisticsGFRoom1():
    return statisticsTemplate(TsvDBCreator.ACTIVITY_GYM,TsvDBCreator.LOC_KRAFTRAUM,pv='/groupStatistics')

@app.route('/' + TsvDBCreator.ACTIVITY_GYM+"SDOJO")
def statisticsGFRoom2():
    return statisticsTemplate(TsvDBCreator.ACTIVITY_GYM,TsvDBCreator.LOC_DOJO,pv='/groupStatistics')

@app.route('/' + TsvDBCreator.ACTIVITY_GYM+"SNORD")
def statisticsGFRoom3():
    return statisticsTemplate(TsvDBCreator.ACTIVITY_GYM,TsvDBCreator.LOC_NORD,pv='/groupStatistics')

@app.route('/' + TsvDBCreator.ACTIVITY_GYM+"SSUED")
def statisticsGFRoom4():
    return statisticsTemplate(TsvDBCreator.ACTIVITY_GYM,TsvDBCreator.LOC_SPIEGELSAAL,pv='/groupStatistics')



@app.route('/accessGYM_KR')  
def visitorsGroupFitnesse():
    people = barModel.currentVisitorPictures(TsvDBCreator.ACTIVITY_GYM,TsvDBCreator.LOC_KRAFTRAUM,60)
    logo_path = "tsv_logo_100.png"
    act = TsvDBCreator.ACTIVITY_GYM +" Kraftraum"
    pv='/groupRooms'
    return render_template('access.html', parentView=pv, people=people, logo_path=logo_path, dynamic_activity=act, location_count=len(people))

@app.route('/accessGYM_Spiegelsaal') 
def visitorsGFS():
    people = barModel.currentVisitorPictures(TsvDBCreator.ACTIVITY_GYM,TsvDBCreator.LOC_SPIEGELSAAL,60)
    logo_path = "tsv_logo_100.png"
    act = TsvDBCreator.ACTIVITY_GYM+" Spiegelsaal"
    pv='/groupRooms'
    return render_template('access.html', parentView=pv, people=people, logo_path=logo_path, dynamic_activity=act, location_count=len(people))

@app.route('/accessGYM_Dojo')  # Access kraftraum TODO: mit Raum!
def visitorsGFD():
    people = barModel.currentVisitorPictures(TsvDBCreator.ACTIVITY_GYM,TsvDBCreator.LOC_DOJO,60)
    logo_path = "tsv_logo_100.png"
    act = TsvDBCreator.ACTIVITY_GYM+" Dojo"
    pv='/groupRooms'
    return render_template('access.html', parentView=pv, people=people, logo_path=logo_path, dynamic_activity=act, location_count=len(people))

@app.route('/accessGYM_Nord')  # Access kraftraum TODO: mit Raum!
def visitorsGFN():
    people = barModel.currentVisitorPictures(TsvDBCreator.ACTIVITY_GYM,TsvDBCreator.LOC_NORD,60)
    logo_path = "tsv_logo_100.png"
    act = TsvDBCreator.ACTIVITY_GYM +" Nord" 
    pv='/groupRooms'
    return render_template('access.html', parentView=pv, people=people, logo_path=logo_path, dynamic_activity=act, location_count=len(people))


'''
SAUNA SECTION -> TsvDBCreator.ACTIVITY_SAUNA == Sauna
'''


@app.route('/' + TsvDBCreator.ACTIVITY_SAUNA)
def statisticsSauna():
    return statisticsTemplate(TsvDBCreator.ACTIVITY_SAUNA,TsvDBCreator.LOC_SAUNA)


@app.route('/accessSA')  # Access kraftraum
def visitorsSauna():
    people = barModel.currentVisitorPictures(TsvDBCreator.ACTIVITY_SAUNA)
    logo_path = "tsv_logo_100.png"
    pv='/'
    return render_template('access.html', parentView=pv, people=people, logo_path=logo_path, dynamic_activity=TsvDBCreator.ACTIVITY_SAUNA, location_count=len(people))

# hook to more sites

'''
Root and tools
'''


@app.route('/')
def dashboard():
    logo_path = "tsv_logo_100.png"
    #Zugang
    entries=(('accessKR','Kraftraum '),('accessSA','Sauna '),('groupRooms','Group '))
    listDataLeft=[]
    for entry in entries:
        data = {"href":entry[0],"title":entry[1]}
        listDataLeft.append(data)
    
    #Statistik
    entries=(('Kraftraum','Kraftraum '),('Sauna','Sauna '),('groupStatistics','Group '))
    listDataRight=[]
    for entry in entries:
        data = {"href":entry[0],"title":entry[1]}
        listDataRight.append(data)    
    
    #Technik
    entries=(('config','Konfig'),('registrationS','Chips'),('aboList','Abos'),('sectionS','Abteilungen'))   
    listData=[] 
    for entry in entries:
        data = {"href":entry[0],"title":entry[1]}
        listData.append(data) 
    return render_template('dashboard2.html', logo_path=logo_path, headerRight="Statistik",listDataRight=listDataRight, headerLeft="Aktiv",listDataLeft=listDataLeft, headerBottom="Sonstiges",listData=listData)

@app.route('/groupRooms')
def groupRooms():
    logo_path = "tsv_logo_100.png"
    entries=(('accessGYM_KR','Kraftraum'),('accessGYM_Spiegelsaal','Spiegelsaal'),('accessGYM_Dojo','Dojo'),('accessGYM_Nord','Nord'))
    listData=[]
    for entry in entries:
        data = {"href":entry[0],"title":entry[1]}
        listData.append(data)
     
    return render_template('sublist.html', logo_path=logo_path, listData=listData,sublistheader="TSV Group Aktiv")

@app.route('/groupStatistics')
def groupStatistics():
    logo_path = "tsv_logo_100.png"
    entries=((TsvDBCreator.ACTIVITY_GYM+'SKR','Kraftraum'),(TsvDBCreator.ACTIVITY_GYM+'SSUED','Spiegelsaal'),(TsvDBCreator.ACTIVITY_GYM+'SDOJO','Dojo'),(TsvDBCreator.ACTIVITY_GYM+'SNORD','Nord'))
    listData=[]
    for entry in entries:
        data = {"href":entry[0],"title":entry[1]}
        listData.append(data)
     
    return render_template('sublist.html', logo_path=logo_path, listData=listData,sublistheader="TSV Group Statistik")    

# save or retrieve pictures for Registration 
@app.route("/TSVPIC/<picture_name>", methods=['GET', 'POST'])
def manage_picture(picture_name):
    """Used to send the requested picture from the pictures folder."""
    picture_path = "TSVPIC/" + picture_name  # TODO -get configured
    if request.method == 'GET':
        Log.debug("Read pic:%s", picture_name)
        return app.send_static_file(picture_path)
    elif request.method == 'POST':
        file = request.files['file']
        Log.debug("Save pic:%s", picture_path)
        try:
            file.save(app.static_folder + "/" + picture_path)
        except:
            Log.exception("Save picture failed")
            return None
        return "200"


# subcall:
def statisticsTemplate(activity,room=TsvDBCreator.LOC_KRAFTRAUM,pv='/'):
    dates, counts = barModel.countPeoplePerDay(activity,room)  # count members over time
    data = [go.Bar(
       x=dates,
       y=counts,
       text=counts,
       textposition='auto',
       marker_color='#FFA500'
    )]
    deltaRoom = activity if activity == room else activity+"-"+room 
    layout = go.Layout(title="Nutzung " + deltaRoom, xaxis=dict(title="Datum"), yaxis=dict(title="Besucher"))
    fig = go.Figure(data=data, layout=layout)
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    logo_path = "tsv_logo_100.png"
    return render_template('index.html', graphJSON=graphJSON, logo_path=logo_path, dynamic_activity=activity,parentView=pv)    


@app.route('/sectionS', methods=["GET", "POST"])
def drawSectionMembers(): 
    sections, counts = barModel.countSectionMembers()  # list members per abteilung
    data = [go.Bar(
       x=sections,
       y=counts,
       text=counts,
       textposition='auto',
       marker_color='#FFA500'
    )]
    layout = go.Layout(title="Abteilungen und deren Mitglieder", xaxis=dict(title="Abteilung"), yaxis=dict(title="Mitglieder"))
    fig = go.Figure(data=data, layout=layout)
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    logo_path = "tsv_logo_100.png"
    return render_template('index.html', graphJSON=graphJSON, logo_path=logo_path, dynamic_activity="Gesamt",parentView="/") 


@app.route('/config', methods=["GET", "POST"])
# https://www.digitalocean.com/community/tutorials/how-to-use-web-forms-in-a-flask-application
# basic: https://plainenglish.io/blog/how-to-create-a-basic-form-in-python-flask-af966ee493fa
def manageConfiguration():
    logo_path = "tsv_logo_100.png"
    configHeaders = ['ID', 'Raum', 'Aktivität', 'Abteilung', 'Merkmale',"Gracetime","Wochentag", "Von" ,"Bis"]
    fields = ['config_id', 'room', 'activity', 'paySection', 'groups','gracetime', 'weekday','from_Time','to_Time']
    configData = []
    configRows = barModel.configTable()
    for row in configRows:
        entry = {}
        for idx in range(0, len(fields)):
            entry[fields[idx]] = row[idx]
        configData.append(entry)
    
    # just open a form
    locHeaders = ['Gerät', 'Konfigurations-IDs']
    fields = ['host_name', 'config_id']
    locRows = barModel.locationTable()
    hostRows={}
    for row in locRows:
        cfg=hostRows.get(row[0],[])
        cfg.append(row[1])
        hostRows[row[0]]=cfg
    
    locData = []
    for host,cfg in hostRows.items():
        entry = {}
        entry[fields[0]]=host
        entry[fields[1]]=', '.join(str(idx) for idx in cfg) #elegant from int to string ;-)
        locData.append(entry)
    
    return render_template('config.html', logo_path=logo_path, configHeaders=configHeaders, configData=configData, locHeaders=locHeaders, locData=locData)


@app.route('/registrationS', methods=["GET", "POST"])
def showChipRegistration():
    logo_path = "tsv_logo_100.png"
    chipHeaders = ['LFD.Nr', 'ID', 'Datum', 'Nachname', 'Burtstag', 'Merkmal', 'Chip']
    fields = ['id', 'date', 'name', 'bday', 'access', 'RFID']  # feldnamen
    configData = []
    dataRows = barModel.registerTable()
    lfd = 1
    for row in dataRows:
        entry = {}
        entry['lfd'] = lfd
        for idx in range(0, 6):
            entry[fields[idx]] = row[idx]
        configData.append(entry)
        lfd += 1
    
    return render_template('register.html', logo_path=logo_path, chipHeaders=chipHeaders, chipData=configData)

@app.route('/aboList', methods=["GET", "POST"])
def showAboSales():
    logo_path = "tsv_logo_100.png"
    headers = ['Datum','ID','Nachname', 'Vorname', 'Abo Typ']
    fields = ['date','id','name', 'firstname', 'section']  # feldnamen
    configData = []
    dataRows = barModel.aboTable()
    for row in dataRows:
        entry = {}
        for idx in range(0, len(headers)):
            entry[fields[idx]] = row[idx]
        configData.append(entry)

    
    return render_template('abolist.html', logo_path=logo_path, aboHeaders=headers, aboData=configData)

'''
Test or demo routines

@app.route('/fancy')  # just colorfull fake with pandas. Think twice using the library 
def plot():
    fakeDAta = barModel.pandaData()
    df = pd.DataFrame(fakeDAta,
                  columns=['Datum', 'Besucher'], index=range(0, len(fakeDAta)))
 
    # Create Bar chart
    fig = px.bar(df, y='Besucher', x='Datum', color="Datum", barmode='group')  # ground==besides
    # no good fig = px.scatter(df, y='Besucher', x='Datum')
    # fig.update_xaxes(type='category')
    fig.update_traces(width=1000 * 3600 * 24 * 0.8)
    # Create graphJSON
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    logo_path = "tsv_logo_100.png"
    dynamic_activity = TsvDBCreator.ACTIVITY_KR
    return render_template('index.html', graphJSON=graphJSON, logo_path=logo_path, dynamic_activity=dynamic_activity)
'''

@app.route('/ratio')  # Access kraftraum
def testRatio():
    people = barModel.testRatio()
    logo_path = "tsv_logo_100.png"
    dynamic_activity = TsvDBCreator.ACTIVITY_KR
    pv='/'    
    return render_template('access.html', parentView=pv, people=people, logo_path=logo_path, dynamic_activity=dynamic_activity)

'''
@app.route('/')  # TODO lead to avalaibale pages ==Dashboard
def plotFigTestWorking():
    # data=[ ["12/4/2023", 50],["13/4/2023", 25],["14/4/2023", 54],["15/4/2023", 32]]
    dates, access = barModel.rawData()
    # dates = ["12/4/42023","13/4/2023","14/4/2023","15/4/2023"]
    # access = [23,17,35,29]
    data = [go.Bar(
       y=access,
       x=dates,
       marker_color='#FFA500'
    )]
    fig = go.Figure(data=data)
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    logo_path = "tsv_logo_100.png"
    dynamic_activity = TsvDBCreator.KRAFTRAUM
    return render_template('index.html', graphJSON=graphJSON, logo_path=logo_path, dynamic_activity=dynamic_activity)
'''


# model for the access row part - checkin/checkout
class AccessRow():
    dwellMinutes = -1  # we dont care

    def __init__(self, dbRow):
        self.id = dbRow[0]
        self.da = dbRow[4]  # datetime
        self.data = dbRow
        self.checked = True
    
    def hour(self):
        return self.da.hour()
    
    def checkInTimeString(self):
        return datetime.strftime(self.da, "%H:%M")
    
    def toggleChecked(self, acDate):
        self.checked = not self.checked
        self.da = acDate
    
    def isInPlace(self):
        if not self.checked:
            return False  # has gone
        if AccessRow.dwellMinutes < 0:
            return self.checked
        now = datetime.now()
        delta = now - self.da
        secs = delta.total_seconds()
        mins = secs / 60
        return mins < AccessRow.dwellMinutes
        
    def __lt__(self, other):
        return self.da < other.da
    
    def __gt__(self, other):
        return self.da > other.da


class CountRow():
    # SELECT mitglied_id,access_date
    MAX_PREVVAIL = 4

    def __init__(self, dbRow, breaktime):
        self.id = dbRow[0]
        self.breakTime = breaktime
        # self.da=dbRow[1] #datetime
        self.checkArray = [None, None, None, None]  # 0=morning CKI, 1 morning CKO, 2 Aftern CKi. 3 Aftn cko
        self._checkin(dbRow[1])
        self.data = dbRow
        self.checked = True
    
    def _checkin(self, rowDate):
        if rowDate.hour < self.breakTime:
            self.checkArray[0] = rowDate
        else:
            self.checkArray[2] = rowDate

    def _setInternal(self, rowDate, idx):
            if self.checkArray[idx] is None:
                self.checkArray[idx] = rowDate
            else:
                self.checkArray[idx + 1] = rowDate
                
    def _checkDate(self, rowDate):
        if rowDate.hour < self.breakTime:
            self._setInternal(rowDate, 0)
        else:
            self._setInternal(rowDate, 2)
        
    def updateAccess(self, row):
        self._checkDate(row[1])
    
    # crude: either 1x or twice a day. 
    def accessCount(self):
        cnt = 0
        ctxIndx = [0, 2]
        for idx in ctxIndx:
            if self.checkArray[idx] is not None:
                cnt += 1
        return cnt
    
    # crude: if cki but not cko we assume 4 hours
    
    def _calcPartHours(self, idx):
        hours = 0
        if self.checkArray[idx] is not None:
            if self.checkArray[idx + 1] is None:
                hours = CountRow.MAX_PREVVAIL
            else:
                hours = self.checkArray[idx + 1].hour - self.checkArray[idx].hour
        return hours
    
    def cumulatedHours(self):
        hours1 = self._calcPartHours(0)
        hours2 = self._calcPartHours(2)
        return hours1 + hours2
    
    def morningData(self):
        # return the morning start date and the partial hours
        if self.checkArray[0] is None:
            return None
        return (self.checkArray[0], self._calcPartHours(0))
    
    def afternoonData(self):
        # return the morning start date and the partial hours
        if self.checkArray[2] is None:
            return None
        return (self.checkArray[2], self._calcPartHours(2))
        
 
class BarModel():

    def __init__(self):
        self._connectToDB()

    def _connectToDB(self):
        self.dbSystem = SetUpTSVDB(SetUpTSVDB.DATABASE)
        self._waitForConnection()
        if not self.dbSystem.isConnected():
            Log.warning("DB connecton terminally failed")
        #self.getMapping()
    
    def _waitForConnection(self):
        cnt = 0
        while not self.dbSystem.isConnected() and cnt < 10:
            Log.warning("DB connection failed. Retry in 10 secs")
            time.sleep(10)
            Log.warning("Reconnect to database")
            self.dbSystem.connectToDatabase(SetUpTSVDB.DATABASE)
            cnt += 1    
        
        self.db = self.dbSystem.db  
    
    '''
    def getMapping(self):
        stmt = "select * from Konfig"
        rows = self.db.select(stmt)
        self.configMapping = {}
        # Known rooms: Kraftraum,Spiegelsaal,Sauna
        for entry in rows:  # room>activity = dic value for getting access 
            self.configMapping[entry[0]] = entry[1]
    '''
    '''        
    def pandaData(self):  # demo
        # data=[ ["12/4/2023", 50],["13/4/2023", 25],["14/4/2023", 54],["15/4/2023", 32]]
        data = []
        now = datetime.now()
        delta = timedelta(days=1)
        start = now - timedelta(days=68)
        while start <= now:
            dbTime = start.date().isoformat()
            cnt = random.randint(0, 250)
            data.append([dbTime, cnt])
            start = start + delta          
        return data
    '''

    def rawData(self):  # demo
        now = datetime.now()
        delta = timedelta(days=1)
        start = now - timedelta(days=68)
        fakeData = []
        fakeValue = []
        while start <= now:
            dbTime = start.isoformat()
            fakeData.append(dbTime)
            fakeValue.append(random.randint(0, 250))
            start = start + delta        
        
        return(fakeData, fakeValue)
    
    # TODO respect checkin/checkout there is a gracetime 0r 120 seconds between check in and checkout
    def countPeoplePerDay(self, activity,room):
        '''
        timetable= self.dbSystem.TIMETABLE
        breakTime=13
        members={}
        stmt = "SELECT mitglied_id,access_date from "+timetable+" where location='"+location+"'"
        rows = self.db.select(stmt)    
        for row in rows:
            #date_str = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d')
            date_str = row[1].strftime('%Y-%m-%d')
            mid = row[0]
            acr= members.get(date_str,None)
            if acr is None:
                members[date_str]={}
    
            cr=members[date_str].get(mid,None)
            if cr is None:
                cr=members[date_str][mid]=CountRow(row,breakTime)
            else:
                members[date_str][mid].updateAccess(row)    
        '''
        members = self.__collectCountRows(activity,room)
        countValues = []
        for aDay in members.values():  # id->cr list
            cnt = 0
            for cr in aDay.values():  # cr->list
                cnt += cr.accessCount()
            countValues.append(cnt)
        
        # Create a Plotly bar chart
        x_values = list(members.keys())
        y_values = list(countValues)
        return (x_values, y_values)
    
    # What? Average usage per person? average usage per day? This cumulates... and is wrong!
    def dailyHoursUsage(self, activity):
        members = self.__collectCountRows(activity)
        hourlyCount = {}
        # go from 9:00 to 12, 14 to 22:00
        # startHour=9
        # endHour=22
        preCount = 0
        postCount = 0
        theHourDict = {}
        daysCount = len(members.keys())
        # note: We need hours not days. Iterate over the days and collect the mean access time
        for idCrDict in members.values():
            for cr in idCrDict.values():
                pre = cr.morningData()  # date->hour count tuple)
                post = cr.afternoonData()
                if pre:
                    hrs = theHourDict.get(pre[0].hour, 0)
                    theHourDict[pre[0].hour] = hrs + pre[1]
                if post:
                    hrs = theHourDict.get(post[0].hour, 0)
                    theHourDict[post[0].hour] = hrs + post[1]
        # todo calc means over the days    
        # Create a Plotly bar chart
        x_values = list(theHourDict.keys())
        y_values = list(theHourDict.values())
        return (x_values, y_values)        
    
    # returns a {date-> {id -> rowCount} ] double dict 
    def __collectCountRows(self, activity,room):
        timetable = self.dbSystem.TIMETABLE
        breakTime = 13
        members = {}
        #stmt = "SELECT mitglied_id,access_date from " + timetable + " where activity='" + activity + "'"
        stmt = "SELECT mitglied_id,access_date from %s where activity='%s' and room='%s'"%(timetable,activity,room)
        rows = self.db.select(stmt)    
        for row in rows:
            # date_str = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d')
            date_str = row[1].strftime('%Y-%m-%d')
            mid = row[0]
            acr = members.get(date_str, None)
            if acr is None:
                members[date_str] = {}
    
            cr = members[date_str].get(mid, None)
            if cr is None:
                cr = members[date_str][mid] = CountRow(row, breakTime)
            else:
                members[date_str][mid].updateAccess(row)    
        return members
    
    def countSectionMembers(self):
        payTable = self.dbSystem.BEITRAGTABLE
        mbrTable = self.dbSystem.MAINTABLE
        stmt = "SELECT section , COUNT(section) AS CountOf from %s join %s on id=mitglied_id where flag=0 and (payuntil_date > CURDATE() or payuntil_date is Null) GROUP BY section  ORDER BY COUNT(section) DESC" % (payTable,mbrTable)
        rows = self.db.select(stmt)
        x_values = []
        y_values = []    
        for row in rows:
            x_values.append(row[0])
            y_values.append(row[1])
        return (x_values, y_values)
        
    # show pic and names of those that are curently in the activity +#TOSO AND ROOM
    def currentVisitorPictures(self, activity,room = None, dwellMinutes=-1):
        mbrTable = self.dbSystem.MAINTABLE
        timetable = self.dbSystem.TIMETABLE
        daysplit = "13"  # time between morning and afternoon
        members = {}
        AccessRow.dwellMinutes = dwellMinutes  # Automatic checkout, negative means: we don't care (Sauna)
        picFolder = self.dbSystem.PICPATH + "/"
        if not room:
            stmt = "SELECT id,first_name,last_name,picpath,access_date FROM " + mbrTable + " m JOIN " + timetable + " z ON m.id = z.mitglied_id WHERE DATE(z.access_date) = CURDATE() AND ((HOUR(z.access_date) < " + daysplit + " AND HOUR(CURTIME()) < " + daysplit + ") OR (HOUR(z.access_date) >= " + daysplit + " AND HOUR(CURTIME()) >= " + daysplit + ")) and activity='" + activity + "' ORDER By z.access_date DESC"
        else:
            stmt = "SELECT id,first_name,last_name,picpath,access_date FROM " + mbrTable + " m JOIN " + timetable + " z ON m.id = z.mitglied_id WHERE DATE(z.access_date) = CURDATE() AND ((HOUR(z.access_date) < " + daysplit + " AND HOUR(CURTIME()) < " + daysplit + ") OR (HOUR(z.access_date) >= " + daysplit + " AND HOUR(CURTIME()) >= " + daysplit + ")) and activity='" + activity + "' AND room='" + room+ "' ORDER By z.access_date DESC"
            
        rows = self.db.select(stmt)
        if rows is None:
            Log.warning("Picture retrieval failed")
            return [{'name':"Fehler - bitte umgehend melden!",'image_path': 'halt.png'}]
        Log.info("Visitor rows:%d", len(rows))
        for row in rows:
            mid = row[0]
            acr = members.get(mid, None)
            if acr is None:
                # Log.debug("Visitor add: %d",mid)
                members[mid] = AccessRow(row)
            else:
                members[mid].toggleChecked(row[4])
                # Log.debug("Visitor toggle: %s",members[mid].checked)
        
        present = [item for item in members.values() if item.isInPlace()]     
        # people = [{'name': fn+" "+name+"("+datetime.strftime(accDate,"%H:%M")+")", 'image_path': picFolder+picpath} for fn, name, picpath,accDate in rows]
        people = []
        for row in present:
            people.append({'name': row.data[1] + " " + row.data[2] + "(" + row.checkInTimeString() + ")", 'image_path': picFolder + row.data[3]}) 
        # people = [{'name': fn+" "+name+"("+datetime.strftime(accDate,"%H:%M")+")", 'image_path': picFolder+picpath} for id,fn, name, picpath,accDate in present]
        Log.info("Checked in:%d", len(people))
        return people

    def configTable(self):
        stmt = "SELECT * from Konfig"
        return self.db.select(stmt)
    
    def registerTable(self):
        # list only NON Assa Abloy keys
        stmt = "select id,register_date,last_name,CAST(birth_date AS DATE),access,r.uuid from Mitglieder m LEFT JOIN AssaAbloy a on a.uuid=m.uuid join RegisterList r on m.id=r.mitglied_id where a.uuid IS NULL and month(register_date)>month(CURDATE())-3 ORDER BY r.register_date ASC"
        return self.db.select(stmt)
    
    def aboTable(self):
        stmt = "select a.buy_date,m.id,m.last_name,m.first_name,a.section from AboList a join Mitglieder m on m.id=a.mitglied_id;"
        return self.db.select(stmt)
    
    def locationTable(self):
        stmt = "Select host_name,config from Location"
        return self.db.select(stmt)

    def testRatio(self):
        people = []
        picFolder = "TSVPIC/"
        pics = "/home/matze/Pictures/TSPIC"
        for filename in os.listdir(pics):
            print(filename)
            people.append({'name':filename, 'image_path':picFolder + filename})
        return people

        
def main():
    # global Log
    global barModel
    wd = OSTools().getLocalPath(__file__)
    OSTools.setMainWorkDir(wd)
    # Log = DBTools.Log
    # OSTools.setupRotatingLogger("TSVAuswertung", True)
    barModel = BarModel()
    #app.run(debug=False, host='0.0.0.0', port=5001,ssl_context=('data/tsvcert.pem', 'data/tsvkey.pem'))
    app.run(debug=False, host='0.0.0.0', port=5001)
    


if __name__ == '__main__':
    sys.exit(main())
    # r=SimpleBarRenderer(m)
    # r.app.run(debug=True, host='0.0.0.0', port=5001)
    
