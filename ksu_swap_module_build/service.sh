#!/system/bin/sh
# OneOS Helper Background Service
# Triggered at late_start boot stage

MODDIR=${0%/*}
BASE_DIR="/data/adb/oneos_helper"

mkdir -p "$BASE_DIR/backup"
mkdir -p "$BASE_DIR/webroot"
chmod 755 "$BASE_DIR"

# Ensure core scripts are synchronized
cp -a "$MODDIR"/scripts/* "$BASE_DIR/" 2>/dev/null
cp -a "$MODDIR"/webroot/* "$BASE_DIR/webroot/" 2>/dev/null
chmod 755 "$BASE_DIR"/*.sh 2>/dev/null

# Log boot init
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [BOOT] OneOS Helper service initialized successfully." >> "$BASE_DIR/helper.log"
