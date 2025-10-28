#!/bin/bash
#check if sudo
if [ "$EUID" -ne 0 ] ; then
  echo "Sorry, but you are not root. Use sudo to run"
  exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "We are here:${DIR}"
mkdir -p /opt/tsvserver;
mkdir -p /opt/tsvserver/data;
path1="$(dirname "$DIR")"
path2="$path1/src"
path3="$path1/build/resources"
cd $path2
cp DBTools.py TsvDBCreator.py TsvAuswertung.py TsvOmoc.py /opt/tsvserver/;
cp -r web /opt/tsvserver/
cd $path3
cp -u tsvauswertung.service /etc/systemd/system/;
cp -u tsvbackup.* /etc/systemd/system/;
echo "######################################################################"
echo "#                  Ensure you have installed (arch arm):             #"                     
echo "#   python-mysql-connector, rsync ,sshpass                           #"
echo "#   pip install flask,plotly, openpyxl                               #"
echo "######################################################################"
echo "!set .config.json manually - enable & start tsv services"
echo "!set mail and omoc credentials with TsvDBCreator"
echo "App installed."
