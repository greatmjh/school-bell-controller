from RPi import GPIO
import os
import logging
import time
import shutil
import glob

from controlbuttons import ControlButton
from bells import LocalBell,RemoteBell

import tomli

#constants
CONFIG_LOCATION = "../config/config.toml"
TRIGGER_FOLDER = "../triggers/"

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
                    #create the object
                    bells[bellName] = LocalBell(bellName, bellPin, activeLow)
                except KeyError: #data doesnt exist in config
                    logging.warning("Missing data on bell %s. Skipping...", localBell)
        
        if "remote" in configDict["bells"]:
            for remoteBell in configDict["bells"]["remote"]:
                try:
                    bellName = remoteBell
                    bellIP = configDict["bells"]["remote"][bellName]["remote_ip"]
                    bellPort = configDict["bells"]["remote"][bellName]["remote_port"]
                    bellSecret = configDict["bells"]["remote"][bellName]["remote_secret"]
                    #create the object
                    bells[bellName] = RemoteBell(bellName, bellIP, bellPort, bellSecret)
                except KeyError: #data doesnt exist in config
                    logging.warning("Missing data on bell %s. Skipping...", remoteBell)

        
    #load any fns
    functions = {}
    try:
        functions = configDict["functions"]
    except KeyError:
        logging.warning("No functions in config file.")
    #add the default STOP function
    functions["STOP"] = {"sequence" : [-1]}

    #load any buttons
    buttons = {}
    if "controlbuttons" in configDict:
        for button in configDict["controlbuttons"]:
            if not button.isnumeric(): #buttons must be defined as their GPIO pin numbers
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

def delContents(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s: %(message)s')
    #parse the config file into bell, button, and function objects
    buttons, functions, bells = parseConfig()
    #prepare for file scanning
    currentDir = os.path.dirname(__file__)
    triggerDirAbs = os.path.join(currentDir, TRIGGER_FOLDER)
    #create the trigger directory if it doesn't exits
    try:
        os.mkdir(triggerDirAbs)
    except FileExistsError:
        pass
    delContents(triggerDirAbs)
    #main file scannning loop
    while(True):
        time.sleep(0.05) #only poll for files every 50ms
        triggerDirContents = os.listdir(triggerDirAbs)
        for relName in triggerDirContents:
            absName = os.path.join(triggerDirAbs, relName)
            if not os.path.isfile(absName):
                logging.warning("Detected directory %s in trigger folder. Deleting...", relName)
                shutil.rmtree(absName)
                continue

            #check if the file is a valid fn
            if not relName in functions:
                logging.warning("Found invalid fn %s in trigger dir. Deleting...", relName)
                os.remove(absName)
            
            #load the actual sequence
            sequence = functions[relName]["sequence"]

            #now that we know the file is a valid fn, load the contents
            fileContents = ""
            with open(absName, "r") as f:
                fileContents = f.read()
            
            #parse the contents into a list of bells
            fileContents = fileContents.strip()
            bellList = fileContents.split(",")

            #run the function on all the bells
            for i in bellList:
                logging.info("File triggered fn %s on bell %s", sequence, i)
                bells[i].runSequence(sequence)

            #delete the file
            os.remove(absName)




if __name__ == "__main__":
    main()

GPIO.cleanup()