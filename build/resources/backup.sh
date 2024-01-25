#!/bin/bash
LOG_FILE=/tmp/backup.log
exec > >(tee ${LOG_FILE}) 2>&1
mariadb-dump --all-databases > /mnt/drive1/TSVPIC/db.dump
DIR="$(cd "$(dirname "$0")" && pwd)"
sh $DIR/sync.sh
echo "backup done"
