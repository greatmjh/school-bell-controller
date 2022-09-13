from RPi import GPIO
import logging
from controlbuttons import ControlButton
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(threadName)s: %(message)s')
GPIO.setmode(GPIO.BCM)

cb = ControlButton(23, "asdasd", ["asd", "def"], None)

try:
	time.sleep(1000)
finally:
	GPIO.cleanup()