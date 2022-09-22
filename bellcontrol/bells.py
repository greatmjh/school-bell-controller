import time
import threading
import queue
import logging

import RPi.GPIO as GPIO

import requests
import urllib3

# define a base class for all bells, which can store a name and has template
# methods for getting the name, ringing, and stopping
class _Bell:
    def __init__(self, bellName):
        #setup members
        self._name = bellName
                
    def getName(self):
        return self._name

# define a class for bells connected to the RPi's local GPIO pins
class LocalBell(_Bell):
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
                        self._turnOn()
                    else:
                        self._turnOff()
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
                        self._turnOff()
                        break
            #when the sequence is finished, turn the bell off
            self._turnOff()

    def __init__(self, bellName, bellPin, activeLow=False):
        # call the superclass's initialiser function
        _Bell.__init__(self, bellName)

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

        #setup sequence management thread
        self._seqMgrThread = threading.Thread(target=self._seqMgrThreadFun,
                                              daemon=True,
                                              name=(self.getName() + "-seq"))
        self._seqQueue = queue.Queue()
        self._seqStopEvent = threading.Event()

        #start sequence management thread
        self._seqMgrThread.start()

    def _turnOn(self):
        logging.debug("GPIO%i turning on", self._pin)
        GPIO.output(self._pin, self._BELL_ON)
    
    def _turnOff(self):
        logging.debug("GPIO%i turning off", self._pin)
        GPIO.output(self._pin, self._BELL_OFF)

    def runSequence(self, sequence):
        logging.debug("%s starting sequence.", self.getName())
        self._seqQueue.put(sequence)

    def stopSequence(self):
        logging.debug("%s stopping sequence.", self.getName())
        self._seqStopEvent.set()

class RemoteBell(_Bell):
    def _seqMgrThreadFun(self):
        while True:
            #logging.debug("Waiting for sequence to get sent")
            try:
                currentSequence = self._seqQueue.get_nowait()
                if self._seqStopEvent.is_set:
                    self._seqStopEvent.clear()
                #convert the sequence into a string
                seqString = ""
                for i in currentSequence:
                    seqString = seqString + str(i) + " "
                #trim the trailing +
                seqString.rstrip(" ")
                #send the sequence over the network to the bell
                #prepare request
                params = {'s': seqString,
                          'secret': self._bellSecret}
                logging.debug("%s placing sequence request for %s",
                              self.getName(),
                              seqString)
                #place request
                try:
                    req = requests.get(url="http://{ip}:{port}/seq".format(
                                                                        ip=self._bellIP,
                                                                        port=self._bellPort),
                                    params=params)
                    #check if it worked
                    if req.status_code != 204:
                        logging.warning("%s failed to send request. Code: %i",
                                        self.getName(), req.status_code)
                        logging.debug(req.text)
                except requests.exceptions.ConnectionError:
                    logging.warning("Unable to connect to remote")
                
            except queue.Empty:
                #the queue is empty, this is normal
                pass
            
            if self._seqStopEvent.is_set():
                self._seqStopEvent.clear()
                params = {'secret': self._bellSecret}
                logging.debug("%s placing stop request",
                              self.getName())
                #place request
                try:
                    req = requests.get(url="http://{ip}:{port}/off".format(
                                                                        ip=self._bellIP,
                                                                        port=self._bellPort),
                                    params=params)
                    if req.status_code != 204:
                        logging.warning("%s failed to send request. Code: %i",
                                        self.getName(), req.status_code)
                        logging.debug(req.text)                

                except requests.exceptions.ConnectionError:
                    logging.warning("Unable to connect to remote")
                

    def __init__(self, bellName, bellIP, bellPort, bellSecret):
        #call superclass initialiser
        _Bell.__init__(self, bellName)
        #set member variables
        self._bellIP = bellIP
        self._bellPort = bellPort
        self._bellSecret = bellSecret
        #setup sequence management thread
        self._seqMgrThread = threading.Thread(target=self._seqMgrThreadFun,
                                              daemon=True,
                                              name=(self.getName() + "-seq"))
        self._seqQueue = queue.Queue()
        self._seqStopEvent = threading.Event()

        #start sequence management thread
        self._seqMgrThread.start()

    def _ringForTime(self, ringTime):
        self.runSequence([ringTime])
        
    def runSequence(self, sequence):
        logging.debug("%s starting sequence.", self.getName())
        self._seqQueue.put(sequence)

    def stopSequence(self):
        logging.debug("%s stopping sequence.", self.getName())
        self._seqStopEvent.set()