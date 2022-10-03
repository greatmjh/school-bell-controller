from RPi import GPIO
import os
import logging
from controlbuttons import ControlButton
from bells import LocalBell,RemoteBell
import tomli

#constants
CONFIG_LOCATION = "../config/config.toml"

def parseConfig():
    #parse the TOML into a dict
    configDict = None
    try:
        dirname = os.path.dirname(__file__)
        with open(os.path.join(dirname, CONFIG_LOCATION), "rb") as f:
            configDict = tomli.load(f)
    except tomli.TOMLDecodeError:
        logging.error("Unable to decode configuration file.")
        exit()
    
    
    #load any bells
    bells = {}
    if "bells" in configDict:
        if "local" in configDict["bells"]:
            for localBell in configDict["bells"]["local"]:
                try:
                    bellName = localBell
                    bellPin = configDict["bells"]["local"][bellName]["pin"]
                    activeLow = configDict["bells"]["local"][bellName]["active_low"]

                    bells[bellName] = LocalBell(bellName, bellPin, activeLow)
                except KeyError:
                    logging.warning("Missing data on bell %s. Skipping...", localBell)
        
        if "remote" in configDict["bells"]:
            for remoteBell in configDict["bells"]["remote"]:
                try:
                    bellName = remoteBell
                    bellIP = configDict["bells"]["remote"][bellName]["remote_ip"]
                    bellPort = configDict["bells"]["remote"][bellName]["remote_port"]
                    bellSecret = configDict["bells"]["remote"][bellName]["remote_secret"]

                    bells[bellName] = RemoteBell(bellName, bellIP, bellPort, bellSecret)
                except KeyError:
                    logging.warning("Missing data on bell %s. Skipping...", remoteBell)

        
    #load any fns
    functions = {}
    try:
        functions = configDict["functions"]
    except KeyError:
        logging.warning("No functions in config file.")
    functions["STOP"] = {"sequence" : [-1]}

    #load any buttons
    buttons = {}
    if "controlbuttons" in configDict:
        for button in configDict["controlbuttons"]:
            if not button.isnumeric():
                logging.warning("Invalid button pin: %s. Skipping...", button)
                continue
            try:
                btnPin = int(button)
                #add bells to object
                btnBells = []
                for bell in configDict["controlbuttons"][button]["affecting_bells"]:
                    btnBells.append(bells[bell])
                #btnBells = configDict["controlbuttons"][button]["affecting_bells"]
                btnSequence = functions[configDict["controlbuttons"][button]["function"]]["sequence"]

                buttons[button] = ControlButton(btnPin, btnSequence, btnBells)
            except KeyError:
                logging.warning("Missing data on button %s. Skipping...", button)

    return buttons, functions, bells



def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(threadName)s: %(message)s')
    #parse the config file into bell, button, and function objects
    buttons, functions, bells = parseConfig()
    while(True):
        pass



if __name__ == "__main__":
    main()

GPIO.cleanup()