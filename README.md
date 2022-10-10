# School Bell Controller
A python program to manage and control school bells at two physical locations.
This repo contains contains the server, which runs on a Raspberry Pi or similar single-board computer, and which can control both local bells connected to both its GPIO pins and remote bells connected to WiFi connected microcontrollers running compatible software.

## Requirements
### Hardware
- A single board computer with Raspberry Pi compatible GPIO pins
- A relay or other method of switching a bell connected to a 3.3 volt GPIO pin

### Software
- A python interpreter to run the code. Tested with Python 3.9.2
- Python packages `rpi-gpio`, `tomli`, and `requests`

## Installation
Ensure that python is downloaded and up to date:
```
$ sudo apt update
$ sudo apt upgrade
$ sudo apt install python3 python3-pip
```

Ensure that you time zone is set correctly
```
$ sudo timedatectl set-timezone Africa/Johannesburg
```

Optionally create a secondary user on the Raspberry Pi to run the daemon. Ensure it is part of the GPIO group.
```
$ sudo adduser bell
$ sudo usermod -aG gpio bell
```

Transfer the code onto the Raspberry Pi.
If the Raspberry Pi is being used over SSH, use a program such as WinSCP to transfer the extracted repository to `/home/bell/bellctl`. Use the bell user credentials just set up instead of your own here to avoid permission issues.

If the Raspberry Pi is being used as a desktop, simply download the repository, extract it, and transfer it to the bell user with the following commands:
```
$ sudo cp -r /path/to/repo /home/bell/bellctl
$ sudo chown -R bell /home/bell/bellctl
```

Log in as the bell user, download pipenv in order to run the virtual environment, and configure the PATH variable
```
$ sudo su - bell
$ pip install rpi-gpio
$ pip install tomli
$ pip install requests
```

Modify the configuration file to your needs. (Read config documentation further below)
```
$ cd bellctl
$ nano config/config.toml
```

Run the daemon and test functionality
```
$ python bellcontrol/bellcontrol.py
```


Go back to your user and create a systemd service to automatically start and stop the daemon
```
$ exit
$ sudo nano /etc/systemd/system/bellctl.service
```
Paste the following in and save. Ensure that `ExecStart` is set to the actual path of `launch.sh`
```
[Unit]
Description=School Bell Controller
After=network.target
StartLimitIntervalSec=0[Service]

[Service]
Type=simple
Restart=always
RestartSec=1
User=bell
ExecStart=/usr/bin/python /home/bell/bellctl/bellcontrol/bellcontrol.py

[Install]
WantedBy=multi-user.target
```

Enable and start the service
```
$ sudo systemctl daemon-reload
$ sudo systemctl enable --now bellctl
```

## The configuration file
The configuration file is split into three main parts, `bells`, `functions`, and `controlbuttons`. 

The first part, `bells`, is split into two parts `local` and `remote`. `local` contains definitions for bells that are connected directly to the GPIO pins, while `remote` contains definitons of remote ESP8266 boards with bells connected to them. These can be renamed and copy-pasted however many times necessary, as long as a different name (the `LOCALBELL` in `bells.local.LOCALBELL` or `REMOTEBELL` in `bells.remote.REMOTEBELL`) is applied.

The second part, `functions`, contains on-off sequences the bells follow. These are specified in an array of delays in miliseconds. For example, the sequence `[2000]` will turn the bell on for 2 seconds and do nothing further, and the sequence `[4000, 3000, 4000, 3000, 4000]` will turn the bell on for 4 seconds 3 times, with a 3 second break in between. These can be renamed and copy-pasted however many times necessary, as long as a different name (the `RING` in `functions.RING`) is applied.

The third part, `controlbuttons` contains definitions for physical buttons connected to GPIO which trigger specific sequences on specific bells. This works a bit differently, since buttons do not have a name assigned to them, just the GPIO pin number. As such, the `24` in `[controlbuttons.24]` refers to the pin in which the button is connected, in BCM numbering. The `function` element must contain the *name* of an existing function that the button runs, and `affecting_bells` must be an **array** of bell names that will be affected by the button. **Buttons must be connected between the GPIO pin and _ground_ in order to work**

## Software triggers
As this daemon provides no form of internal schedules, it is recommended to use an external program to trigger the bell. In order to trigger the daemon, a file must be placed in the `triggers` directory with the name being the name of the function being run and the contents being a list of bells that the function must be run on, delimited by semicolons. This can be done in a single command as follows: (bell names are `BELL1` and `BELL2` and the function name is `FUNCTIONNAME`)
```
$ echo BELL1,BELL2 > /path/to/repo/triggers/FUNCTIONNAME
```

### Cron
This trigger functionality can be automated using cron, a built-in schedulting application. To configure, run the command `crontab -e` while logged in as the bell user. The online tool https://crontab.guru can help with setting these schedules correctly.

An example configuration could look like this:
```
$ crontab -e

...
...

45 7 * * 1-5 /usr/bin/echo LOCAL,REMOTE > /home/bell/bellctl/triggers/RING #school starts
45 10 * * 1-5 /usr/bin/echo REMOTE > /home/bell/bellctl/triggers/RING #HS first break starts
15 11 * * 1-5 /usr/bin/echo REMOTE > /home/bell/bellctl/triggers/RING #HS first break ends
#etc...
```