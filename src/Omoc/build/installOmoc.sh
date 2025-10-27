#!/bin/bash
#check if sudo
if [ "$EUID" -ne 0 ] ; then
  echo "Sorry, but you are not root. Use sudo to run"
  exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "We are here:${DIR}"
mkdir -p /opt/omocKiosk;
path1="$(dirname "$DIR")"
path2="$path1/src"
path3="$path1/build/resources"
cd $path2
cp OmocKiosk.py /opt/omocKiosk/;
cd $path3
cp -u omoc* /etc/systemd/system/;
exec systemctl enable omocKiosk.timer;
exec systemctl enable omocKiosk.service;
echo "############################################################################"
echo "#                  Ensure you have installed                               #"
echo "#  apt install python3-pip python3-dev python3-setuptools libffi-dev      \#"
echo "#  libjpeg-dev libpng-dev libcairo2 libcairo2-dev libpango1.0-0           \#"
echo "# libpango1.0-dev libfreetype6-dev liblcms2-dev libwebp-dev poppler-utils \#"
echo "#                                                                          #"
echo "#pip3 install weasyprint pdf2image pillow requests  --break-system-packages#"
echo "############################################################################"
echo "OmocKisok service installed.
