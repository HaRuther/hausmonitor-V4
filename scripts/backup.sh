#!/bin/sh
set -eu
mkdir -p backups
stamp=$(date +%Y%m%d-%H%M%S)
sqlite3 data/hausmonitor.db ".backup 'backups/hausmonitor-$stamp.db'"
tar -czf "backups/uploads-$stamp.tar.gz" data/uploads
find backups -type f -mtime +90 -delete
