#!/bin/bash
#check if sudo
if [ "$EUID" -ne 0 ] ; then
  echo "Sorry, but you are not root. Use sudo to run"
  exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "We are here:${DIR}"
mkdir -p /opt/TSVAccess;
mkdir -p /opt/TSVAccess/data;
path1="$(dirname "$DIR")"
path2="$path1/src"
cd $path2
#echo "DGB:${path1} and: ${path2} == $(pwd)"
cp DBTools.py TsvDBCreator.py RaspiTools.py TsvAccessModule.py RegModel.py /opt/TSVAccess/;
echo "######################################################################"
echo "#                  Ensure you have installed:                        #"                     
echo "#    pip install RPi.GPIO spidev mfrc522 (raspberrypi-tm1637)        #"
echo "#    pacman -Syu  python-mysql-connector                             #"
echo "######################################################################"
echo "!set config manually"
echo "App installed."
