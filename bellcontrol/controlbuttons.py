import logging
import time
import threading
import queue

from RPi import GPIO

class ControlButton:
    def _btnThreadFun(self):
        buttonDown = False
        while True:
            if not buttonDown and GPIO.input(self._pin) == GPIO.LOW:
                #the button was released and now pressed
                time.sleep(0.020) #debounce for 20ms
                buttonDown = True
                logging.debug("Button on pin %i pushed down", self._pin)

            if buttonDown and GPIO.input(self._pin) == GPIO.HIGH:
                #the button was pushed down and now released
                time.sleep(0.020) #debounce for 20ms
                buttonDown = False
                logging.debug("Button on pin %i released", self._pin)

    
    def __init__(self, gpioPin, sequenceName, bellNames, feedbackQueue):
        #setup members
        self._pin = gpioPin
        self._seqName = sequenceName
        self._bellNames = bellNames
        self._feedbackQueue = feedbackQueue
        #setup gpio pin with pull-up
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        #setup button thread
        self._btnThread = threading.Thread(target=self._btnThreadFun,
                                           daemon=True)
        self._btnThread.start()