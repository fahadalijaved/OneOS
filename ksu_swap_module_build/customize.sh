SKIPMOUNT=false
PROPFILE=false
POSTFSDATA=false
LATESTARTSERVICE=true

ui_print "****************************************"
ui_print "*        OneOS SwBridge IO v2.0        *"
ui_print "*   Mualiy.net & Fahad Ali Team (TR)   *"
ui_print "****************************************"
ui_print "- Core: Ultra-Fast SwOUT / SwIN Bridge"
ui_print "- Zero Overhead, Lockscreen & Encryption Manager"

# Persistent config directory
mkdir -p /data/adb/oneos_helper/webroot
chmod 755 /data/adb/oneos_helper

# Sync scripts & webroot
cp -a "$MODPATH"/scripts/* /data/adb/oneos_helper/ 2>/dev/null
cp -a "$MODPATH"/webroot/* /data/adb/oneos_helper/webroot/ 2>/dev/null
chmod 755 /data/adb/oneos_helper/*.sh 2>/dev/null

# Clean up any stale symlinks
rm -f /data/adb/modules/oneos_switcher_su_bridge 2>/dev/null

# Permissions
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/service.sh" 0 0 0755
set_perm_recursive "$MODPATH/scripts" 0 0 0755 0755
set_perm_recursive "$MODPATH/system/bin" 0 2000 0755 0755

ui_print "- Kurulum tamamlandi!"
