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
cp ExternalMailService.py /opt/tsvserver/;
cd $path3
cp -u tsvExternal* /etc/systemd/system/;
exec systemctl enable tsvExternalHandballMembers.timer;
exec systemctl start tsvExternalHandballMembers.timer;
exec systemctl enable tsvExternalDLDaily.timer;
exec systemctl start tsvExternalDL.timer;
exec systemctl enable tsvExternalDLWeekly.timer;
exec systemctl start tsvExternalDLWeekly.timer;
echo "#########################################################################"
echo "#                  Ensure you have installed                            #"                     
echo "#   the "installServer" script                                          #"
echo "#   This installs all external services												          #"
echo "#########################################################################"
echo "External service installed."
