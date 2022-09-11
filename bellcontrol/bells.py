import time
import threading
import queue
import logging

import RPi.GPIO as GPIO

import requests

# define a base class for all bells, which can store a name and has template
# methods for getting the name, ringing, and stopping
class _Bell:
    def _ringThreadFun(self):
        #locals in thread
        ringing = False
        finishTime = time.time()
        #main control loop
        while True:
            if self._startEvent.is_set(): #the bell needs to turn on
                self._startEvent.clear()
                ringTime = self._rtQueue.get()
                finishTime = time.time() + (ringTime / 1000)
                ringing = True
                self._turnOn(ringTime)

            if self._stopEvent.is_set(): #the bell is told to turn off
                self._stopEvent.clear()
                ringing = False
                self._turnOff()
            
            if (time.time() > finishTime) and ringing: #the bell has finished ringing
                ringing = False
                self._turnOff()

    def __init__(self, bellName):
        #setup member variables
        self._name = bellName
        self._startEvent = threading.Event()
        self._stopEvent = threading.Event()
        self._rtQueue = queue.Queue()
        self._ringThread = threading.Thread(target=self._ringThreadFun,
                                            daemon=True)
        #start the ringing thread
        self._ringThread.start()

    def getName(self):
        return self._name

    def ring(self, ringTime): # function to ring bell
        logging.info("%s starting to ring for %i milliseconds", 
                     self.getName(),
                     ringTime)
        self._rtQueue.put(ringTime)
        self._startEvent.set()

    def stop(self):
        logging.info("%s forcibly stopped", self.getName())
        self._stopEvent.set()

# define a class for bells connected to the RPi's local GPIO pins
class LocalBell(_Bell):
    def __init__(self, bellName, bellPin, activeLow=False):
        # call the superclass's initialiser function
        _Bell.__init__(self, bellName)
        # set member variables
        self._pin = bellPin
        # setup the GPIO pin
        GPIO.setup(bellPin, GPIO.OUT)
        # setup definitions of on and off
        if (activeLow):
            self._BELL_ON = GPIO.LOW
            self._BELL_OFF = GPIO.HIGH
        else:
            self._BELL_ON = GPIO.HIGH
            self._BELL_OFF = GPIO.LOW

    def _turnOn(self):
        logging.debug("GPIO%i turning on", self._pin)
        GPIO.output(self._pin, self._BELL_ON)
    
    def _turnOff(self):
        logging.debug("GPIO%i turning off", self._pin)
        GPIO.output(self._pin, self._BELL_OFF)

class RemoteBell(_Bell):
    def _netThreadFun(self):
        while True:
            queueData = self._netTimeQueue.get()
            if queueData >= 0:
                ringTime = queueData
                #prepare request
                params = {'t': ringTime,
                          'secret': self._bellSecret}
                logging.debug("%s placing ring request for %ims",
                              self.getName(),
                              ringTime)
                #place request
                req = requests.get(url="http://{ip}/on".format(ip=self._bellIP),
                                   params=params)
                #check if it worked
                if req.status_code != 204:
                    logging.warning("%s failed to send request. Code: %i",
                                    self.getName(), req.status_code)
                    logging.debug(req.text)
            else:
                #prepare request
                params = {'secret': self._bellSecret}
                logging.debug("%s placing stop request",
                              self.getName())
                #place request
                req = requests.get(url="http://{ip}/off".format(ip=self._bellIP),
                                   params=params)
                if req.status_code != 204:
                    logging.warning("%s failed to send request. Code: %i",
                                    self.getName(), req.status_code)
                    logging.debug(req.text)
                
    def __init__(self, bellName, bellIP, bellSecret):
        #call superclass initialiser
        _Bell.__init__(self, bellName)
        #set member variables
        self._bellIP = bellIP
        self._bellSecret = bellSecret
        #setup network thread queue and events
        self._netTimeQueue = queue.Queue()
        #setup network thread
        self._networkThread = threading.Thread(target=self._netThreadFun, 
                                               daemon=True)
        self._networkThread.start()

    def _turnOnTD(self, ringTime):
        logging.debug("%s turning on over network")
        self._netTimeQueue.put(ringTime)

    def _turnOff(self):
        logging.debug("%s turning off over network")
        self._netTimeQueue.put(-1)
        
