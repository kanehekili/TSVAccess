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
PORT=22


def connectSSH(server):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=SSHUSER, password=SSHPWD, look_for_keys=False, allow_agent=False, port=PORT)
    print("Connected")
    return client

def backup(file,target):
    try:
        sshClient=connectSSH(SERVER)
        with SCPClient(sshClient.get_transport()) as scp:
            scp.put(file, target)
        print("copied:%s to target:%s"%(file,target))
    except Exception:
        print("SCP failure")
        traceback.print_exc()
        exit(1)      

if __name__ == '__main__':
    argv = sys.argv
    if len(argv)<3:
        print("State local full path filename and remote target path")
        exit(1) 
    backup(argv[1], argv[2])
