'''
Created on Aug 24, 2023

@author: matze
'''

from time import sleep, localtime
from threading import Timer

try:
    from tm1637 import TM1637 # @UnresolvedImport
    LEDS=True
except Exception:
    LEDS=False
    print("no TM1637 LED installed")

try:    
    import RPi.GPIO as GPIO  # @UnresolvedImport
    from mfrc522 import SimpleMFRC522  # @UnresolvedImport
    RASPI = True
except Exception:
    print("no GPIOS installed")
    RASPI = False


class RaspberryGPIO():
    PINGREEN = 2
    PINORANGE = 3
    PINRED = 17
    PINSIGNAL = 27
    LIGHTON = False
    LIGHTOFF = True  # depends how we cable the relais

    def __init__(self,invertGPIO):
        if invertGPIO:
            RaspberryGPIO.LIGHTON=True
            RaspberryGPIO.LIGHTOFF=False
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.PINGREEN, GPIO.OUT)
        GPIO.setup(self.PINRED, GPIO.OUT)
        GPIO.setup(self.PINORANGE, GPIO.OUT)
        GPIO.setup(self.PINSIGNAL, GPIO.OUT)
        self.reset()  # GPIOS start on hi... 
        self.timer = None
        '''
        using GPIOS:
        o o
        o o
        o x -GND
        o o                
        o o
        x x -Grau(17)-Lila(18)        
        |--| usb==unten
    
        Relais
        o x 5V Red
        x o GPIO2 Blue   ->Green light (OK)
        x o GPIO3 yello   -> yello (WARN)
        o o                
        X o -GND Green  
        x o GPIO 17 orange  -> red (NO ACCESS)
        x o GPIO27  brown   ->signal (NO ACCESS)       
        |--| usb==unten
        
        '''

    def signalAccess(self):
        self.reset()
        GPIO.output(self.PINGREEN, self.LIGHTON)
        self._restartTimer()        
        
    def signalForbidden(self):
        self.reset()
        GPIO.output(self.PINRED, self.LIGHTON)        
        GPIO.output(self.PINSIGNAL, self.LIGHTON)
        self._restartTimer()
    
    def signalAlarm(self):
        self.reset()
        GPIO.output(self.PINORANGE, self.LIGHTON)
        self._restartTimer()
    
    #mark if gracetime still in place (=no action)
    def tickGracetime(self):
        GPIO.output(self.PINORANGE, self.LIGHTON)
        sleep(0.5)
        GPIO.output(self.PINORANGE, self.LIGHTOFF)
        
    def welcome1(self):
        self.reset()
        GPIO.output(self.PINGREEN, self.LIGHTON)
        sleep(0.3)
        GPIO.output(self.PINORANGE, self.LIGHTON) 
        sleep(0.05)
        GPIO.output(self.PINGREEN, self.LIGHTOFF)
        sleep(0.3)
        GPIO.output(self.PINRED, self.LIGHTON)
        sleep(0.05)
        GPIO.output(self.PINORANGE, self.LIGHTOFF)
        sleep(0.3)
        GPIO.output(self.PINORANGE, self.LIGHTON)
        sleep(0.05)
        GPIO.output(self.PINRED, self.LIGHTOFF)
        sleep(0.3)
        GPIO.output(self.PINGREEN, self.LIGHTON)
        sleep(0.05)
        GPIO.output(self.PINORANGE, self.LIGHTOFF)
        sleep(0.3)
        GPIO.output(self.PINGREEN, self.LIGHTOFF)
    
    # TODO needs timer
    def reset(self):
        GPIO.output(self.PINRED, self.LIGHTOFF)  # true=off, false=ON
        GPIO.output(self.PINGREEN, self.LIGHTOFF)
        GPIO.output(self.PINORANGE, self.LIGHTOFF)
        GPIO.output(self.PINSIGNAL, self.LIGHTOFF)        
            
    def _restartTimer(self):
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(5, self.reset)
        self.timer.start()        

'''
        RFID READER
        x o 3.3V red
        o o
        o x -GND black
        o o                
        o o
        o o
        o o
        o o
        o o
        x o SPio Mosi - Green   
        x x SPIO Miso - Orange / GPIO 25(RST) Blue
        x x SPIO CLK -  brown  / SPI CSO Yellow     
        |--| usb==unten
'''    
# changed due to 100% CPU
class MFRC522Reader():

    def __init__(self):
        self.mfrc = SimpleMFRC522()
        
    def read_id(self):
        rfid = None
        while not rfid:
            data = self.mfrc.read_id_no_block()
            if data:
                return self._convert(data)
            sleep(0.3)
    
    def _convert(self, bigInt):
        if not bigInt:
            return 0
        rbytes = bigInt.to_bytes(5)
        tmp = rbytes[:-1][::-1]  # little to big endian
        return int.from_bytes(tmp)


'''
o x Pin 4 = 5V
...
o x Ground (Pin 34)
o o
o x 20 DIO (Pin 38)
o x 21 CLK (Pin 40)
|--| usb==unten
'''



DIO=20
CLK=21 #Using the lower GPIOS

class LED7:
    def __init__(self):
        self.tm = TM1637(CLK,DIO) 
    
    def text(self,aString):
        if len(aString)>4:
            aString=aString[:4]
        self.tm.show(aString)
    
    def clear(self):
        self.tm.write([0, 0, 0, 0])
       
    #int    
    def number(self,nbr):
        self.tm.number(nbr)
    
    #int int with ":"   
    def numbers(self,hours,seconds):
        self.tm.numbers(hours,seconds)
           
    #int: Only between 0 and 7 [0,3,7] is visible
    def brightness(self,lum):
        if lum>7:
            lum=7
        self.tm.brightness(lum)

class Clock:
    def __init__(self, tm1637):
        self.tm=tm1637
        self.show_colon = False
        self.ct=None

    def run(self):
        while True:
            self.showTime()
            sleep(1)

    def runAsync(self):
        self.ct=RepeatTimer(1,self.showTime)
        self.tm.brightness(1)
        self.ct.start()

    def stop(self):
        if self.ct is not None:
            self.ct.cancel()
            self.tm.write([0, 0, 0, 0])
            self.tm.brightness(4)     
            self.ct.join()       
        self.ct=None
            
    def showTime(self):
        t = localtime()
        self.show_colon = not self.show_colon
        self.tm.numbers(t.tm_hour, t.tm_min, self.show_colon)
        

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def cleanup():
    if RASPI:
        GPIO.cleanup()

if __name__ == '__main__':
    pass