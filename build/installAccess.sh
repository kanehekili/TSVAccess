#!/bin/bash
#check if sudo
if [ "$EUID" -ne 0 ] ; then
  echo "Sorry, but you are not root. Use sudo to run"
  exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "We are here:${DIR}"
sudo mkdir -p /opt/TSVAccess;
sudo mkdir -p /opt/TSVAccess/data;
path1="$(dirname "$DIR")"
path2="$path1/src"
cd $path2
#echo "DGB:${path1} and: ${path2} == $(pwd)"
sudo cp DBTools.py TsvDBCreator.py RaspiTools.py TsvAccessModule.py /opt/TSVAccess/;
echo "######################################################################"
echo "#                  Ensure you have installed:                        #"                     
echo "#    debian/ubuntu/mint:                                             #"
echo "#    arch &derivates:                                                #"
echo "######################################################################"
echo "!config and mail json manually"
echo "App installed."
