# TSVAccess
Area access for the TSV Weilheim

The TSV Weilheim is one of largest "Sportvereine" in the bavarian "Oberland". This project implements an access system to certain areas (like fitnesse == gym) using embedded devices (raspi) and linux servers. 
Currently the means of idendification is RFID. Basically two devices are used: a Keyboard emitting USB RFID reader and the RC522 RFID reader for arduino and raspbery pi.


## TsvRegisterModule
This module ist used for the registration of members. It can be used in conjunction of an existing member database, but users can be created without it.
The module will register a photo, the name and a unique id (primary key). This app may run on an office device - not yet tested on windows since it uses the Qt5 widget kit, opencv and python 

###Dependencies Debian
* python-mysql-connector (use pip)
* python3-opencv
* python3-opencv-data (haarcascade)
* python3-qt5

###Dependencies Arch
* python-pyqt5
* python-opencv
* python-mysql-connector

Only a member checked in with this module will be able to access the system!
![Screenshot](https://github.com/kanehekili/TSVAccess/blob/main/TSV-Register.png)

This software uses head (not face) recognition (see green rectangle) to get uniform portraits. The UI language is german, no current plan to use NLS. It needs a private ssh key to connect to a ssh server for saving the photos.

## TsvAccessModule
This app runs on a Raspberry pi (3a), currently controlling a 2 channel relais for lights (Access,non access). Connected ot it is a RC522 RFID reader, which delivers the token uid that has been registered in the TSVREgisterModule.
![Screenshot](https://github.com/kanehekili/TSVAccess/blob/main/Hardware1.jpg)

### Dependencies (Arch Armhf)
* python-mysql-connector
* pip3 install RPi.GPIO
* pip3 install spidev
* pip3 install mfrc522
(might use  --break-system-packages on pip calls)

Test spi (RFID access)
lsmod | grep spi
should list spidev und spi_bcm2835

!DO NOT USE the read method from SimpleMFRC522 - it will render your device unusable.  Use the "no_block" methods and sleep for 0.3 secs



## TsvAuswertungsModule 
A python flask server, that provides html data:
 * Who is currently on the premises
 * Statistics about how many many have been visiting
 * uses flask, plotly and (optional - not decided yet) pandas

###Dependencies
* python-mysql-connector
* pip install flask,pandas,plotly

#### Only needed for backup:
* pip install scp  
* pip install paramiko


## TsvDBCreator
The database module. Uses mysqlconnection and has been tested with mariadb. Offers dabasebase setup and control via the DBTools.py, which is the interface to the underlying database systen

## DBTools
Technical database abstraction for the mysql.connector. This is the place to change the database backend 

## The configuration
The data/ directory contains the config.json file. This file configures access to the database, passwords and locations:

 * "HOST": "DBHOST"
 * "DB": "TsvDB"
 * "USER": "aUSER"
 * "PASSWORD": "PWD"
 * "PICPATH": "usr@host:/where/ever/you/go/TSVPIC/"

## Location and access
The "Location" table contains all of the locations and activities, as well as the allowd access codes and Gracetime.
Registered hosts can be reconfigured by setting another location entry.
(eg. Access in room A with course B ist changed to room B and course C) 
