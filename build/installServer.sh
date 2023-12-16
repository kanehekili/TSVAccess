#!/bin/bash
#check if sudo
if [ "$EUID" -ne 0 ] ; then
  echo "Sorry, but you are not root. Use sudo to run"
  exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "We are here:${DIR}"
mkdir -p /opt/taserver;
mkdir -p /opt/taserver/data;
path1="$(dirname "$DIR")"
path2="$path1/src"
cd $path2
cp DBTools.py TsvDBCreator.py TsvAuswertung.py /opt/taserver/;
cp -r web /opt/taserver/
echo "######################################################################"
echo "#                  Ensure you have installed (arch arm):             #"                     
echo "#   python-mysql-connector                                           #"
echo "#   pip install flask,pandas,plotly                                  #"
echo "######################################################################"
echo "!config and mail json manually"
echo "App installed."
