#!/usr/bin/env python3
'''
Created on Aug 14, 2023

@author: matze
'''
import paramiko
from scp import SCPClient
import sys,traceback

SSHUSER = ""
SSHPWD = ""
SERVER = ""

'''
bash:
#!/bin/bash
LOG_FILE=/tmp/backup.log
exec > >(tee ${LOG_FILE}) 2>&1

mariadb-dump --all-databases > /mnt/drive1/TSVPIC/db.dump
tar zcvf /mnt/drive1/backup.tar.gz /mnt/drive1/TSVPIC
DIR="$(cd "$(dirname "$0")" && pwd)"
$DIR/CopySCP.py /mnt/drive1/backup.tar.gz /volume1/Backup/
echo "backup done" 
'''


def connectSSH(server):
    # DBTools.logging.getLogger("paramiko").setLevel(DBTools.logging.WARNING)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=SSHUSER, password=SSHPWD, look_for_keys=False, allow_agent=False)
    print("Connected")
    return client


def backup(file, target):
    try:
        sshClient = connectSSH(SERVER)
        with SCPClient(sshClient.get_transport()) as scp:
            scp.put(file, target)
            print("copied:%s to target:%s" % (file, target))
            exit(1)
    except Exception:
        print("SCP failure")
        traceback.print_exc()
        exit(1)      


if __name__ == '__main__':
    argv = sys.argv
    if len(argv) < 3:
        print("State local full path filename and remote target path")
        exit(1) 
    backup(argv[1], argv[2])
    
