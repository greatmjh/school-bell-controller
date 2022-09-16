import logging
import time
import threading


from RPi import GPIO

class ControlButton:
    def _handleButtonPress(self):
        #when a button press is detected, loop through bells and tell them to ring
        for bell in self._bellNames:
            if self._sequence == [-1]: #if the button is used to stop bells, stop them
                logging.info("Button %i stopped bell %s",
                             self._pin,
                             bell.getName())
                bell.stopSequence()
            else: #otherwise, run the sequence
                logging.info("Button %i triggered fn %s on bell %s",
                            self._pin,
                            self._sequence,
                            bell.getName())
                bell.runSequence(self._sequence)
            

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
                self._handleButtonPress()

    
    def __init__(self, gpioPin, sequence, bellNames):
        #setup members
        self._pin = gpioPin
        self._sequence = sequence
        self._bellNames = bellNames
        #setup gpio pin with pull-up
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        #setup button thread
        self._btnThread = threading.Thread(target=self._btnThreadFun,
                                           daemon=True,
                                           name=str(gpioPin) + "-btnctl")
        self._btnThread.start()
