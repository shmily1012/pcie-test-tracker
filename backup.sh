#!/bin/bash
DB_PATH="./data/db/pcie_tracker.db"
BACKUP_DIR="./data/backups"
mkdir -p "$BACKUP_DIR"
cp "$DB_PATH" "$BACKUP_DIR/pcie_tracker_$(date +%Y%m%d_%H%M%S).db"
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
echo "Backup complete. $(ls -1 $BACKUP_DIR | wc -l) backups retained."
