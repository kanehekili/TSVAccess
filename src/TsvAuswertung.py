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
import DBTools
import sys

'''
@app.route('/')
def barPlotly():
   # Students data available in a list of list
    students = [['Akash', 34, 'Sydney', 'Australia'],
                ['Rithika', 30, 'Coimbatore', 'India'],
                ['Priya', 31, 'Coimbatore', 'India'],
                ['Sandy', 32, 'Tokyo', 'Japan'],
                ['Praneeth', 16, 'New York', 'US'],
                ['Praveen', 17, 'Toronto', 'Canada']]
     
    # Convert list to dataframe and assign column values
    df = pd.DataFrame(students,
                      columns=['Name', 'Age', 'City', 'Country'],
                      index=['a', 'b', 'c', 'd', 'e', 'f'])
     
    # Create Bar chart
    fig = px.bar(df, x='Name', y='Age', color='City', barmode='group')
     
    # Create graphJSON
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('index.html', graphJSON=graphJSON)

'''
app= Flask(__name__,
            static_url_path='', 
            static_folder='web/static',
            template_folder='web/templates')


@app.route('/fancy')    
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

def plotAccess():
    pass

@app.route('/')
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

'''
myPlot.on('plotly_relayout',(e)=>{
    var zoom_level = e['mapbox.zoom'];
    if (zoom_level < initialZoom){
      layout.mapbox.zoom = initialZoom
      layout.mapbox.center = {lat: initialLat, lon: initialLon}
      Plotly.relayout(myPlot, layout)
    }
  })
'''


   
'''
class SimpleBarRenderer():
    def __init__(self,barModel):
        self.barModel=barModel
        self.app=self._defineFlask()
        
    def _defineFlask(self):
        return Flask(__name__,
            static_url_path='', 
            static_folder='web/static',
            template_folder='web/templates'
        )
    
    @app.route('/')    
    def plot(self):
        df = pd.DataFrame(self.barModel.accessData(),
                      columns=['Date', 'Count'],
                      index=['a', 'b', 'c', 'd', 'e', 'f'])
     
        # Create Bar chart
        fig = px.bar(df, x='Besucher', y='Datum', barmode='group')
     
        # Create graphJSON
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        return render_template('index.html', graphJSON=graphJSON)
'''

class BarModel():
    def __iniit__(self):
        self.db=self._connectToDB()

    def _connectToDB(self):
        pass #do sth
    
    def pandaData(self):
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

    def rawData(self):
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
    