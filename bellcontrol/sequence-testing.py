from RPi import GPIO
import logging
from bells import LocalBell, RemoteBell
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(threadName)s: %(message)s')
GPIO.setmode(GPIO.BCM)
#b = LocalBell("Bell-18", 18)
b = RemoteBell("RB", "10.1.4.210", 80, "password")

try:
	b.runSequence([1000, 1000, 1000, 1000, 1000])
	time.sleep(10)
	b.runSequence([1000])
	while True: pass
finally:
	GPIO.cleanup()