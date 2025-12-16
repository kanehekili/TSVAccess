'''
Created on 31 Mar 2025

connector for the remote sewobe RESTfull API

@author: matze
'''
import requests,json
from DBTools import OSTools

CODE_OK=200
REST_BASE_URL = "https://manager23.sewobe.de/"
#APP_ADRESS = "adressen"              # For data endpoint

class RestConnector():
    session=None
    lastError=None
    USERNAME = "xxx"
    PASSWORD = "xxx"
    
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
    
    def testGetCountries(self): #just an example on how to retrieve data
        function="GET_LAENDER"
        app="adressen"
        data_url = f"{REST_BASE_URL}applikation/{app}/api/{function}"
        params = {"SESSION": self.session}  # Matches PHP's ?SESSION=[SESSION]
        data_response = requests.get(data_url, params=params)
        if self._checkResponse(data_response):
            print(data_response.json())
     
    def getUser(self):   
        function="GET_USER"
        app="benutzer"
        data_url = f"{REST_BASE_URL}applikation/{app}/api/{function}"
        params = {"SESSION": self.session}
        data_response = requests.get(data_url, params=params)
        if self._checkResponse(data_response):
            print(data_response.json())
        
        
    def _saveSession(self,response):     
        try:
            self.session = response.json().get("SESSION")   
            print("session saved")
        except ValueError:
            print("Login response is not JSON:", response.text)
            return False
        return True
    
    def _checkResponse(self,response):    
        code = response.status_code
        if code != CODE_OK:
            print("Error response:", response.text)
            self.lastError = response.text
            return False
        return True
        

if __name__ == '__main__':
    rc = RestConnector()
    if rc.login():
        #rc.testGetCountries()
        rc.getUser()
    pass