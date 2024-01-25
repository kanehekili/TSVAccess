#!/bin/bash
SSHUSER="your user"
SSHPWD="your password"
SERVER="your server"
echo "starting rsync process"
rsync -rtpogvu --rsh="/usr/bin/sshpass -p $SSHPWD ssh -o StrictHostKeyChecking=no -l $SSHUSER" /mnt/drive1/TSVPIC $SSHUSER@$SERVER::Backup/
