#!/bin/bash
LOG_FILE=/tmp/backup.log
exec > >(tee ${LOG_FILE}) 2>&1

mariadb-dump --all-databases > /mnt/drive1/TSVPIC/db.dump
tar zcvf /mnt/drive1/backup.tar.gz /mnt/drive1/TSVPIC
DIR="$(cd "$(dirname "$0")" && pwd)"
$DIR/CopySCP.py /mnt/drive1/backup.tar.gz /volume1/Backup/
echo "backup done"
