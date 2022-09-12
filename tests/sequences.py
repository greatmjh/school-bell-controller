from RPi import GPIO
import logging
from bellcontrol.bells import LocalBell

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(threadName)s: %(message)s')
GPIO.setmode(GPIO.BCM)
lb = LocalBell("Bell-18", 18)

try:
	lb.runSequence([1000, 1000, 1000])
finally:
	GPIO.cleanup()