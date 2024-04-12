'''
Created on Jun 23, 2023

@author: matze
Experimental - not productive!
'''


import evdev

RFC522="IC Reader"
#user must be in group "input" !
class RFIDReaderEvDev():
    def __init__(self,readerType):
        self._locatePath(readerType)
        
    def _locatePath(self,readerType):
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        self.devPath = None
        for device in devices:
            if readerType in device.name:
                self.devPath=device.path
                print("Locate dev:",device.name)    
                return
        print("Warning - no device found")
    
    def readOnce(self):
        if not self.devPath:
            return  
        device = evdev.InputDevice(self.devPath)
        code=''
        scancodes = { 
                # Scancode: ASCIICode 
                0: None, 1: u'ESC', 2: u'1', 3: u'2', 4: u'3', 5: u'4', 6: u'5', 7: u'6', 8: u'7', 9: u'8', 
                10: u'9', 11: u'0', 12: u'-', 13: u'=', 14: u'BKSP', 15: u'TAB', 16: u'q', 17: u'w', 18: u'e', 19: u'r', 
                20: u't', 21: u'y', 22: u'u', 23: u'i', 24: u'o', 25: u'p', 26: u'[', 27: u']', 28: u'CRLF', 29: u'LCTRL', 
                30: u'a', 31: u's', 32: u'd', 33: u'f', 34: u'g', 35: u'h', 36: u'j', 37: u'k', 38: u'l', 39: u';', 
                40: u'"', 41: u'`', 42: u'LSHFT', 43: u'\\', 44: u'z', 45: u'x', 46: u'c', 47: u'v', 48: u'b', 49: u'n', 
                50: u'm', 51: u',', 52: u'.', 53: u'/', 54: u'RSHFT', 56: u'LALT', 57: u' ', 100: u'RALT' 
            } 
        device.grab()
        while True:  
            print("StartLoop")      
            for event in device.read_loop():
                if event.type == evdev.ecodes.EV_KEY:
                    data = evdev.categorize(event)
                    print(data)
                    if data.keystate == 1 and data.scancode != 42:
                        if(data.scancode == 28):
                            #we have rfid
                            device.ungrab()
                            return(code)
                        #print("add scan:",data.scancode,">",scancodes[data.scancode])
                        
                        code += scancodes[data.scancode]

'''
#this is raspi stuff:

import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

class RC522Reader():
    def __init__(self):
        self.reader = SimpleMFRC522()
        
    def readBlocked(self):
        return self.reader.read()

    def shutDown(self):
        GPIO.cleanUp()

'''

class SimpleKBDReader():
    def __init__(self):
        pass
    
    def readOnce(self):
        txt=input()
        return txt


if __name__ == '__main__':
    r=RFIDReaderEvDev(RFC522)
    #r=SimpleKBDReader()
    code= r.readOnce()
    print("Exit:",code)
    exit(0)
    