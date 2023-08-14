'''
Created on Apr 3, 2023
Show graphs per Month or year.
@author: matze
'''
# https://www.geeksforgeeks.org/create-a-bar-chart-from-a-dataframe-with-plotly-and-flask/
# https://github.com/alanjones2/Flask-Plotly/tree/main/plotly
# using  plotly and flask. 
# pip install flask,plotly,pandas
from flask import Flask, render_template,request#, has_request_context, session, url_for
from werkzeug.utils import secure_filename
import pandas as pd
import json
import plotly
import plotly.express as px
import plotly.graph_objs as go
from datetime import datetime, timedelta
import random
from DBTools import OSTools
from TsvDBCreator import SetUpTSVDB
import DBTools
import sys,os
import TsvDBCreator

OSTools.setupRotatingLogger("TSVAuswertung", True)
Log = DBTools.Log

app = Flask(__name__,
            static_url_path='',
            static_folder='web/static',
            template_folder='web/templates')


@app.route('/' + TsvDBCreator.ACTIVITY_KR)
def statisticsKraftraum():
    #TODO
    dates, counts = barModel.countPeoplePerDay(TsvDBCreator.ACTIVITY_KR)  # count members over time
    
    # chat gpt -it forgot to tell about the index.html - hence we have a second one:
    '''
    data = [go.Bar(x=dates, y=counts)]
    layout = go.Layout(title='Besucher pro Tag', xaxis=dict(title='Datum'), yaxis=dict(title='Anzahl'))
    fig = go.Figure(data=data, layout=layout)
    plot_div = fig.to_html(full_html=False)
        
    return render_template('index2.html', plot_div=plot_div)
    '''
    # This results in exact the same bar. Only the index.html is different. 
    data = [go.Bar(
       x=dates,
       y=counts,
       marker_color='#FFA500'
    )]
    layout = go.Layout(title="Nutzung " + TsvDBCreator.ACTIVITY_KR, xaxis=dict(title="Datum"), yaxis=dict(title="Besucher"))
    fig = go.Figure(data=data, layout=layout)
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    logo_path = "tsv_logo_100.png"
    dynamic_location = TsvDBCreator.ACTIVITY_KR
    return render_template('index.html', graphJSON=graphJSON, logo_path=logo_path, dynamic_location=dynamic_location)

    
@app.route('/' + TsvDBCreator.ACTIVITY_KR + "Usage")
def verweilzeitKraftraum():
    #TODO
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
    dynamic_location = TsvDBCreator.ACTIVITY_KR
    return render_template('index.html', graphJSON=graphJSON, logo_path=logo_path, dynamic_location=dynamic_location)        


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
    dynamic_location = TsvDBCreator.ACTIVITY_KR
    return render_template('index.html', graphJSON=graphJSON, logo_path=logo_path, dynamic_location=dynamic_location)

#@app.route('/', methods=['GET', 'POST'])
@app.route('/')
def dashboard():
    logo_path = "tsv_logo_100.png"
    return render_template('dashboard.html',logo_path=logo_path)
    
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
    dynamic_location = TsvDBCreator.KRAFTRAUM
    return render_template('index.html', graphJSON=graphJSON, logo_path=logo_path, dynamic_location=dynamic_location)
'''

@app.route('/accessKR')  # Access kraftraum
def whoIsThere():
    #https://stackoverflow.com/questions/58996870/update-flask-web-page-with-python-script
    people = barModel.currentVisitorPictures(TsvDBCreator.ACTIVITY_KR)
    logo_path = "tsv_logo_100.png"
    dynamic_location = TsvDBCreator.ACTIVITY_KR    
    return render_template('access.html', people=people, logo_path=logo_path, dynamic_location=dynamic_location)

# hook to more acees sites

#save or retrieve pictures for Registration 
@app.route("/TSVPIC/<picture_name>",methods=['GET', 'POST'])
def manage_picture(picture_name):
    """Used to send the requested picture from the pictures folder."""
    picture_path="TSVPIC/"+picture_name #TODO -get configured
    if request.method =='GET':
        Log.debug("Read pic:%s",picture_name)
        return app.send_static_file(picture_path)
    elif request.method =='POST':
        file = request.files['file']
        Log.debug("Save pic:%s",picture_path)
        try:
            file.save(app.static_folder+"/"+picture_path)
        except:
            Log.exception("Save picture failed")
            return None
        return "200"
        
#@app.route("/savePic")
#def savePicture():


# model for the access row part - checkin/checkout
class AccessRow():

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
        self.db = self.dbSystem.db
        if not self.dbSystem.isConnected():
            Log.warning("DB connecton failed")
        self.getMapping()
    
    def getMapping(self):
        stmt="select * from Konfig"
        rows = self.db.select(stmt)
        self.configMapping={}
        #Known rooms: Kraftraum,Spiegelsaal,Sauna
        for entry in rows:#room>activity = dic value for getting access 
            self.configMapping[entry[0]]=entry[1]
            
    
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
    def countPeoplePerDay(self, location):
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
        members = self.__collectCountRows(location)
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
    def dailyHoursUsage(self, location):
        members = self.__collectCountRows(location)
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
    def __collectCountRows(self, location):
        timetable = self.dbSystem.TIMETABLE
        breakTime = 13
        members = {}
        stmt = "SELECT mitglied_id,access_date from " + timetable + " where location='" + location + "'"
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
    
    # show pic and names of those that are curently in the location
    def currentVisitorPictures(self, location):
        mbrTable = self.dbSystem.MAINTABLE
        timetable = self.dbSystem.TIMETABLE
        daysplit = "13"  # time between morning and afternoon
        members = {}
        picFolder = "TSVPIC/"#TODO use config now
        stmt = "SELECT id,first_name,last_name,picpath,access_date FROM " + mbrTable + " m JOIN " + timetable + " z ON m.id = z.mitglied_id WHERE DATE(z.access_date) = CURDATE() AND ((HOUR(z.access_date) < " + daysplit + " AND HOUR(CURTIME()) < " + daysplit + ") OR (HOUR(z.access_date) > " + daysplit + " AND HOUR(CURTIME()) > " + daysplit + ") and location='" + location + "')  ORDER By z.access_date DESC"
        # print(stmt) 
        rows = self.db.select(stmt)
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
        
        present = [item for item in members.values() if item.checked]     
        # people = [{'name': fn+" "+name+"("+datetime.strftime(accDate,"%H:%M")+")", 'image_path': picFolder+picpath} for fn, name, picpath,accDate in rows]
        people = []
        for row in present:
            people.append({'name': row.data[1] + " " + row.data[2] + "(" + row.checkInTimeString() + ")", 'image_path': picFolder + row.data[3]}) 
        # people = [{'name': fn+" "+name+"("+datetime.strftime(accDate,"%H:%M")+")", 'image_path': picFolder+picpath} for id,fn, name, picpath,accDate in present]
        Log.info("Checked in:%d", len(people))
        return people

        
def main():
    #global Log
    global barModel
    wd = OSTools().getLocalPath(__file__)
    OSTools.setMainWorkDir(wd)
    #Log = DBTools.Log
    #OSTools.setupRotatingLogger("TSVAuswertung", True)
    barModel = BarModel()
    app.run(debug=False, host='0.0.0.0', port=5001)    


if __name__ == '__main__':
    sys.exit(main())
    # r=SimpleBarRenderer(m)
    # r.app.run(debug=True, host='0.0.0.0', port=5001)
    
