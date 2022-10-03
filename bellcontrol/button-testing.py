from RPi import GPIO
import logging
from controlbuttons import ControlButton
from bells import LocalBell,RemoteBell
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(threadName)s: %(message)s')
GPIO.setmode(GPIO.BCM)

lb = LocalBell("Bell-18", 18)
rb = RemoteBell("RB", "192.168.0.50", 80, "password")
ring = ControlButton(25, [2000], [rb,lb])
fire = ControlButton(23, [1000, 1000, 1000, 1000, 1000], [rb,lb])

try:
	while True:
		pass
finally:
	GPIO.cleanup()
