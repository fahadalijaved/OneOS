#!/system/bin/sh
MODDIR=${0%/*}
BASE_DIR="/data/adb/oneos_helper"

mkdir -p "$BASE_DIR/webroot"
chmod 755 "$BASE_DIR"

cp -a "$MODDIR"/scripts/* "$BASE_DIR/" 2>/dev/null
cp -a "$MODDIR"/webroot/* "$BASE_DIR/webroot/" 2>/dev/null
chmod 755 "$BASE_DIR"/*.sh 2>/dev/null

rm -f /data/adb/modules/oneos_switcher_su_bridge 2>/dev/null

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [BOOT] OneOS SwBridge IO ready." >> "$BASE_DIR/helper.log"
