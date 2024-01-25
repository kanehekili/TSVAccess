# TSVAccess  ![Screenshot](https://github.com/kanehekili/TSVAccess/blob/main/src/web/static/tsv_logo_100.png)
Area access for the TSV Weilheim

The TSV Weilheim is one of largest "Sportvereine" in the bavarian "Oberland". This project implements an access system to certain areas (like fitnesse == gym) using embedded devices (raspi) and linux servers. 
Currently the means of identification is RFID. Basically two devices are used: a Keyboard emitting USB RFID reader and the RC522 RFID reader for arduino and raspbery pi.

The "access" devices are configurable. Therefore it is possible to have one or more devices in the system, that control different "courses or activities".

This is a Linux project. No windoze support.

## TsvRegisterModule
This module ist used for the registration of members. It can be used in conjunction of an existing member database, but users can be created without it. <br />
The module will register a photo, the name and a unique id (primary key). This app may run on an office device - it may run on windows but not much effort has been put into it. 

### Dependencies Debian
* python-mysql-connector (use pip - debian stuff is too old)
* python3-opencv
* python3-opencv-data (haarcascade)
* python3-qt6
* pip install requests
* pip install v4l2ctl

### Dependencies Arch
* python-pyqt6
* python-opencv
* python-mysql-connector
* python-requests
* pip install v4l2ctl (might use --break-system-packages since it does not exist)

The Registration app has been written in QT6. To get the original design in GTK env you need to:
* install qt6gtk2
* Select a theme that supports gtk2
* install gtk-engine-murrine (depending on your theme)
* Set in /etc/environment:
  QT_QPA_PLATFORMTHEME=gtk2
(depends on your distro)

There is a basic support for windows, but not currently tested nor in any way supported.

Only a member once checked in with this module will be able to access the system!
![Screenshot](https://github.com/kanehekili/TSVAccess/blob/main/Register.png)

This software uses head (not face) recognition (see green rectangle) to get uniform portraits. The UI language is german, no current plan to use NLS.

### The Abo dialog
For some events we sell Abos - here a 10x ticket for using the sauna. The Abo dialog provides two lines:
* Check if an Abo is requested - a mail will go out for the accountant responsible charging.
* Alter the current visits or set up how many visits have already been paid bevor using this system.
![Screenshot](https://github.com/kanehekili/TSVAccess/blob/main/Abodialog.png)

Last but not least: The bottom line enables you to block any member to access anything. 

## TsvAccessModule
This app runs on a Raspberry pi (3a), currently controlling a 3 channel relais for lights (Access,non access and special states). <br /> Connected ot it is a RC522 RFID reader, which delivers the token uid that has been registered in the TSVeEgisterModule.
![Screenshot](https://github.com/kanehekili/TSVAccess/blob/main/Hardware1.jpg)
There is a variant, that uses a LED 7-Segment display to show time and the count of an abo. 

### The big room solution
![Screenshot](https://github.com/kanehekili/TSVAccess/blob/main/ampel.jpg)

### The sauna solution
![Screenshot](https://github.com/kanehekili/TSVAccess/blob/main/Sauna.jpg)

### The simple LED solution
![Screenshot](https://github.com/kanehekili/TSVAccess/blob/main/SimpleAccess.png)

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

It usually resides in the "server" which is comprised of the database service and the "Auswertung". All "access" devices are connected to this server.

This module runs, together with mariadb on an plain Raspi 2:
![Screenshot](https://github.com/kanehekili/TSVAccess/blob/main/server.jpg)


### Dependencies
* python-mysql-connector
* pip install flask,(pandas?),plotly
* pandas will be perished in favour of dash (under contruction)

#### Only needed for backup (in progress - switch to rsync)
Pure rysnc implementation.
A timer based service will copy the database and the recorded pictures to another server - to ensure redundancy.  <br />
pacman -S rsync must be installed. <br />
backup.sh will call sync.sh triggered by the backup systemd service which is triggered by a backup timer service... 

## TsvDBCreator
The database module. Uses mysqlconnection and has been tested with mariadb. Offers dabasebase setup and control via the DBTools.py, which is the interface to the underlying database system. <br />
In addition the creator provides email-tools and scripts for merging "Conplan" data into the intrinsic database.

## DBTools
Technical database abstraction for the mysql.connector. This is the place to change the database backend 

## Ximporter
In order to import data from a retro software that is not able to provide any REST bindings, Ximporter has been created. It reads a propriaty XLS file and imports it into our system. Select a xls file (this feature needs to be adapted to the provider) to import it into the database.  <br />
Due to some restraints on the given infrastructure - this code works on windows.. (but looks a lot uglier)

Ximporter has been written for "Conplan" and will have to be adapted for other backends.

![Screenshot](https://github.com/kanehekili/TSVAccess/blob/main/Ximporter.png)


## The configuration
The data/ directory contains the config.json file. This file configures access to the database, passwords and locations:

 * "HOST": "DBHOST"
 * "DB": "TsvDB"
 * "USER": "aUSER"
 * "PASSWORD": "PWD"
 * "PICPATH": "PATH in static/"

## Location and access
The "Location" table contains all of the locations and activities, as well as the allowed access codes and Gracetime. <br /> redundancy
Each entry defines a room, the activity and the paysection with their access ids. Additional time data can be used to reduce access times to certain days and time in a week.

An access device therefore can have one or more locations defined.