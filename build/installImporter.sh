#!/bin/bash
#check if sudo
if [ "$EUID" -ne 0 ] ; then
  echo "Sorry, but you are not root. Use sudo to run"
  exit 1
fi
#copy desktop to /usr/share applications
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "We are here:${DIR}"
sudo cp $DIR/resources/*.desktop /usr/share/applications;
sudo mkdir -p /opt/TSVAccess;
sudo mkdir -p /opt/TSVAccess/data;
sudo mkdir -p /opt/TSVAccess/web/static;
path1="$(dirname "$DIR")"
path2="$path1/src"
cd $path2
#echo "Dbg:${path1} and: ${path2} == $(pwd)"
sudo cp DBTools.py TsvDBCreator.py XlsImporter.py /opt/TSVAccess/;
cd "$path2/web/static"
sudo cp *.png /opt/TSVAccess/web/static/
echo "######################################################################"
echo "#                  Ensure you have installed:                        #"                     
echo "#    debian/ubuntu/mint: python3-pyqt6,openpyxl                      #"
echo "#    arch &derivates:    python-pyqt6,  python-openpyxl              #"
echo "######################################################################"
echo "!config json manually"
echo "App installed."
