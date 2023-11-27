'''
Created on Aug 7, 2023
This module reads input from some GPIO thrice. The button must have been pressed 3x in 3 secs and will lead to a power down. Resistor is 220Ohms
Connect to 3.3V (Pin O1 or 17) and an arbitary GPIO (BCM) which is to be be passed.... 
@author: matze
'''
import RPi.GPIO as GPIO #@UnresolvedImport
class RaspiButton():
    def __init__(self,gpio, func):
        self.pin=gpio
        self.func=func
        self.runDaemon()
    
    
    def _setup(self):
        #https://raspberrypihq.com/use-a-push-button-with-raspberry-pi-gpio/
        pass
    
        
    def runDaemon(self):
        #we need to be a simple thread
        pass


if __name__ == '__main__':
    pass