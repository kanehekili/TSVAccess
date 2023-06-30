'''
Created on Apr 3, 2023
Show graphs per Month or year.
@author: matze
'''
#https://www.geeksforgeeks.org/create-a-bar-chart-from-a-dataframe-with-plotly-and-flask/
#https://github.com/alanjones2/Flask-Plotly/tree/main/plotly
#using  plotly and flask. 
#pip install flask,plotly,pandas
from flask import Flask, render_template
import pandas as pd
import json
import plotly
import plotly.express as px
import plotly.graph_objs as go
from datetime import datetime,timedelta
import random
from DBTools import OSTools
from TsvDBCreator import SetUpTSVDB
import DBTools
import sys
import TsvDBCreator

OSTools.setupRotatingLogger("TSVAuswertung",True)
Log = DBTools.Log

app= Flask(__name__,
            static_url_path='', 
            static_folder='web/static',
            template_folder='web/templates')


@app.route('/'+TsvDBCreator.KRAFTRAUM)
def statisticsKraftraum():
    dates,counts= barModel.plainhistory(TsvDBCreator.KRAFTRAUM)# count members over time
    
    
    #chat gpt -it forgot to tell about the index.html - hence we have a second one:
    '''
    data = [go.Bar(x=dates, y=counts)]
    layout = go.Layout(title='Besucher pro Tag', xaxis=dict(title='Datum'), yaxis=dict(title='Anzahl'))
    fig = go.Figure(data=data, layout=layout)
    plot_div = fig.to_html(full_html=False)
        
    return render_template('index2.html', plot_div=plot_div)
    '''
    #This results in exact the same bar. Only the index.html is different. 
    data = [go.Bar(
       x = dates, 
       y = counts,
       marker_color='#FFA500'
    )]
    layout = go.Layout(title="Nutzung "+TsvDBCreator.KRAFTRAUM,xaxis=dict(title="Datum"),yaxis=dict(title="Besucher"))
    fig = go.Figure(data=data,layout=layout)
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    logo_path = "tsv_logo_100.png"
    dynamic_location = TsvDBCreator.KRAFTRAUM
    return render_template('index.html', graphJSON=graphJSON,logo_path=logo_path, dynamic_location=dynamic_location)
    
   

@app.route('/fancy')   #just colorfull fake 
def plot():
    fakeDAta= barModel.pandaData()
    df = pd.DataFrame(fakeDAta,
                  columns=['Datum','Besucher'],index=range(0,len(fakeDAta)))
                  
 
    # Create Bar chart
    fig = px.bar(df, y='Besucher', x='Datum',color="Datum", barmode='group') #ground==besides
    #no good fig = px.scatter(df, y='Besucher', x='Datum')
    #fig.update_xaxes(type='category')
    fig.update_traces(width=1000*3600*24*0.8)
    # Create graphJSON
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('index.html', graphJSON=graphJSON)

@app.route('/') #later access to all - now just a demo 
def plotFigTestWorking():
    #data=[ ["12/4/2023", 50],["13/4/2023", 25],["14/4/2023", 54],["15/4/2023", 32]]
    dates, access =  barModel.rawData()
    #dates = ["12/4/42023","13/4/2023","14/4/2023","15/4/2023"]
    #access = [23,17,35,29]
    data = [go.Bar(
       y = access,
       x = dates,
       marker_color='#FFA500'
    )]
    fig = go.Figure(data=data)
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('index.html', graphJSON=graphJSON)

@app.route('/accessKR') #Access kraftraum
def whoIsThere():
    people = barModel.currentVisitorPictures(TsvDBCreator.KRAFTRAUM)
    logo_path = "tsv_logo_100.png"
    dynamic_location = TsvDBCreator.KRAFTRAUM    
    return render_template('access.html', people=people,logo_path=logo_path, dynamic_location=dynamic_location)

#hook to more acees sites
 
class BarModel():
    def __init__(self):
        self._connectToDB()

    def _connectToDB(self):
        self.dbSystem = SetUpTSVDB(SetUpTSVDB.DATABASE)
        self.db=self.dbSystem.db
        if not self.dbSystem.isConnected():
            Log.warning("DB connecton failed")
    
    def pandaData(self):#demo
        #data=[ ["12/4/2023", 50],["13/4/2023", 25],["14/4/2023", 54],["15/4/2023", 32]]
        data=[]
        now=datetime.now()
        delta = timedelta(days=1)
        start = now - timedelta(days=68)
        while start <=now:
            dbTime=start.date().isoformat()
            cnt=random.randint(0,250)
            data.append([dbTime,cnt])
            start=start+delta          
        return data

    def rawData(self):#demo
        now=datetime.now()
        delta = timedelta(days=1)
        start = now - timedelta(days=68)
        fakeData=[]
        fakeValue=[]
        while start <=now:
            dbTime=start.isoformat()
            fakeData.append(dbTime)
            fakeValue.append(random.randint(0,250))
            start=start+delta        
        
        return(fakeData,fakeValue)
    
    def plainhistory(self,location):
        #simmply count woo was there when...
        timetable= self.dbSystem.TIMETABLE
        stmt = "SELECT access_date from "+timetable+" where location='"+location+"'"
        rows = self.db.select(stmt)    
        #chat GPT - does that work?
        datetime_dict = {}
        for row in rows:
            #date_str = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d')
            date_str = row[0].strftime('%Y-%m-%d')
            if date_str in datetime_dict:
                datetime_dict[date_str] += 1
            else:
                datetime_dict[date_str] = 1
        
        # Create a Plotly bar chart
        x_values = list(datetime_dict.keys())
        y_values = list(datetime_dict.values())
        return (x_values,y_values)
    
    def currentVisitorPictures(self,location):
        mbrTable= self.dbSystem.MAINTABLE
        timetable= self.dbSystem.TIMETABLE
        picFolder="TSPIC/"
        #TODO da muss noch die location aus m selectiert werden
        stmt ="SELECT first_name,last_name,picpath,access_date FROM "+mbrTable+" m JOIN "+timetable+" z ON m.id = z.mitglied_id WHERE DATE(z.access_date) = CURDATE() AND ((HOUR(z.access_date) < 12 AND HOUR(CURTIME()) < 12) OR (HOUR(z.access_date) >= 12 AND HOUR(CURTIME()) >= 12) and location='"+location+"')  ORDER By z.access_date DESC"
        #raw test stmt ="SELECT first_name,last_name,picpath,access_date FROM "+mbrTable+" m JOIN "+timetable+" z ON m.id = z.mitglied_id" 
        rows = self.db.select(stmt)
        print("ROWS:",rows)
        people = [{'name': fn+" "+name+"("+datetime.strftime(accDate,"%H:%M")+")", 'image_path': picFolder+picpath} for fn, name, picpath,accDate in rows]
        return people

        
def main():
    global Log
    global barModel
    wd = OSTools().getLocalPath(__file__)
    OSTools.setMainWorkDir(wd)
    Log = DBTools.Log
    OSTools.setupRotatingLogger("TSVAuswertung", True)
    barModel=BarModel()
    app.run(debug=True, host='0.0.0.0', port=5001)    

if __name__ == '__main__':
    sys.exit(main())
    #r=SimpleBarRenderer(m)
    #r.app.run(debug=True, host='0.0.0.0', port=5001)
    