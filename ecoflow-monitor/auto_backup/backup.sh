#!/bin/bash
TIMESTAMP=$(date +"%F")
BACKUP_DIR="/home/ecoflow/auto_backup/$TIMESTAMP"
mkdir -p $BACKUP_DIR

docker run --rm --volumes-from prometheus -v $BACKUP_DIR:/backup ubuntu tar cvf /backup/prometheus-backup.tar /prometheus
docker run --rm --volumes-from grafana -v $BACKUP_DIR:/backup ubuntu tar cvf /backup/grafana-backup.tar /var/lib/grafana
