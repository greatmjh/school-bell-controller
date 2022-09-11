from RPi import GPIO
from bells import LocalBell, RemoteBell
import time
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(threadName)s: %(message)s')
GPIO.setmode(GPIO.BCM)
lb = LocalBell("Bell-18", 18)
lb2 = LocalBell("Bell-25", 25)
nb = RemoteBell("Net-Bell", "10.1.4.210", "password")

try:
	logging.debug("Before 1st ring")
	nb.ring(1000)
	logging.debug("After 1st ring")
	time.sleep(2000)
	logging.debug("Before 2nd ring")
	nb.ring(1000)
	logging.debug("After 2nd ring")
	time.sleep(2000)
	logging.debug("Before 3rd ring")
	nb.ring(1000)
	logging.debug("After 3rd ring")
	time.sleep(1000)
finally:
	print("before cleanup")
	GPIO.cleanup()
	print("after cleanup")