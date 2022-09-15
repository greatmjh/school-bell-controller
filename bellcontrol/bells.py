import time
import threading
import queue
import logging

import RPi.GPIO as GPIO

import requests

# define a base class for all bells, which can store a name and has template
# methods for getting the name, ringing, and stopping
class _Bell:
    def _seqMgrThreadFun(self):
        while True:
            logging.debug("Waiting for sequence to get sent")
            currentSequence = self._seqQueue.get()
            logging.debug("Sequence being processed")
            if self._seqStopEvent.is_set:
                self._seqStopEvent.clear()
            if currentSequence is not None:
                #a queue has been loaded
                bellOn = True #the bell starts turned on
                forceStop = False #for when the sequence needs to be forcibly stopped
                for currentDelay in currentSequence: #loop through the sequence
                    if bellOn: #if the bell is supposed to be on for this delay cycle, turn it on
                        self._ringForTime(currentDelay)
                    #wait until the cycle is over
                    finishTime = time.time() + (currentDelay / 1000)
                    while time.time() < finishTime:
                        if self._seqStopEvent.is_set(): #if a force stop comes through
                            self._seqStopEvent.clear()
                            forceStop = True #set flag to exit main loop
                            break #exit this loop
                    #switch to the opposite cycle (from bell on to waiting)
                    bellOn = not bellOn
                    #if the force stop flag is called, stop the bell and break
                    if (forceStop):
                        self._stopRinging()
                        break

    def __init__(self, bellName):
        #setup members
        self._name = bellName
        #setup sequence management thread
        self._seqMgrThread = threading.Thread(target=self._seqMgrThreadFun,
                                              daemon=True,
                                              name=(self.getName() + "-seq"))
        self._seqQueue = queue.Queue()
        self._seqStopEvent = threading.Event()
        
        #start sequence management thread
        self._seqMgrThread.start()

    def getName(self):
        return self._name

    def runSequence(self, sequence):
        self._seqQueue.put(sequence)

    def stopSequence(self, sequence):
        self._seqStopEvent.set()


# define a class for bells connected to the RPi's local GPIO pins
class LocalBell(_Bell):
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
                self._turnOn()

            if self._stopEvent.is_set(): #the bell is told to turn off
                self._stopEvent.clear()
                ringing = False
                self._turnOff()
            
            if (time.time() > finishTime) and ringing: #the bell has finished ringing
                ringing = False
                self._turnOff()

    def __init__(self, bellName, bellPin, activeLow=False):
        # call the superclass's initialiser function
        _Bell.__init__(self, bellName)
        # set member variables
        self._startEvent = threading.Event()
        self._stopEvent = threading.Event()
        self._rtQueue = queue.Queue()
        self._ringThread = threading.Thread(target=self._ringThreadFun,
                                            daemon=True,
                                            name=(self.getName() + "-gpio"))
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
        
        #start the ringing thread
        self._ringThread.start()

    def _turnOn(self):
        logging.debug("GPIO%i turning on", self._pin)
        GPIO.output(self._pin, self._BELL_ON)
    
    def _turnOff(self):
        logging.debug("GPIO%i turning off", self._pin)
        GPIO.output(self._pin, self._BELL_OFF)

    def _ringForTime(self, ringTime): # function to ring bell
        logging.info("%s starting to ring for %i milliseconds", 
                     self.getName(),
                     ringTime)
        self._rtQueue.put(ringTime)
        self._startEvent.set()

    def _stopRinging(self):
        logging.info("%s forcibly stopped", self.getName())
        self._stopEvent.set()        

class RemoteBell(_Bell):
    def _netThreadFun(self):
        while True:
            logging.debug("At top of loop")
            queueData = self._netTimeQueue.get()
            logging.debug("Received queue data")
            if queueData >= 0: #turning the bell on for a specific time
                ringTime = queueData
                #prepare request
                params = {'t': ringTime,
                          'secret': self._bellSecret}
                logging.debug("%s placing ring request for %ims",
                              self.getName(),
                              ringTime)
                #place request
                req = requests.get(url="http://{ip}:{port}/on".format(
                                                                     ip=self._bellIP,
                                                                     port=self._bellPort),
                                   params=params)
                #check if it worked
                if req.status_code != 204:
                    logging.warning("%s failed to send request. Code: %i",
                                    self.getName(), req.status_code)
                    logging.debug(req.text)
            else: #turning the bell off
                #prepare request
                params = {'secret': self._bellSecret}
                logging.debug("%s placing stop request",
                              self.getName())
                #place request
                req = requests.get(url="http://{ip}:{port}/off".format(
                                                                     ip=self._bellIP,
                                                                     port=self._bellPort),
                                   params=params)
                if req.status_code != 204:
                    logging.warning("%s failed to send request. Code: %i",
                                    self.getName(), req.status_code)
                    logging.debug(req.text)
                
    def __init__(self, bellName, bellIP, bellPort, bellSecret):
        #call superclass initialiser
        _Bell.__init__(self, bellName)
        #set member variables
        self._bellIP = bellIP
        self._bellPort = bellPort
        self._bellSecret = bellSecret
        #setup network thread queue and events
        self._netTimeQueue = queue.Queue()
        self._netEvent = threading.Event()
        #setup network thread
        self._networkThread = threading.Thread(target=self._netThreadFun, 
                                               daemon=True,
                                               name=(self.getName() + "-net"))
        self._networkThread.start()

    def _ringForTime(self, ringTime):
        logging.info("%s turning on over network for %ims", 
                     self.getName(),
                     ringTime)
        self._netTimeQueue.put(ringTime)

    def _stopRinging(self):
        logging.info("%s turning off over network", self.getName)
        self._netTimeQueue.put(-1)