#!/system/bin/sh
SKIPMOUNT=false
PROPFILE=false
POSTFSDATA=false
LATESTARTSERVICE=true

ui_print "****************************************"
ui_print "*   OneOS Switcher & SU Bridge Helper  *"
ui_print "*      Mualiy.net & Fahad Ali Team     *"
ui_print "****************************************"
ui_print "- Target: Samsung One UI & MysticGSI   "
ui_print "- Features: SwapOUT, SwapIN, ManuelSU  "
ui_print "- WebUI: Enabled (KernelSU & MMRL)     "

# Create persistent storage dir in /data/adb
mkdir -p /data/adb/oneos_helper/backup
mkdir -p /data/adb/oneos_helper/webroot
chmod 755 /data/adb/oneos_helper
chmod 700 /data/adb/oneos_helper/backup

# Copy scripts and webroot to working directory as well
cp -a "$MODPATH"/scripts/* /data/adb/oneos_helper/ 2>/dev/null
cp -a "$MODPATH"/webroot/* /data/adb/oneos_helper/webroot/ 2>/dev/null
chmod 755 /data/adb/oneos_helper/*.sh 2>/dev/null

# Set permissions for module files
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/service.sh" 0 0 0755
set_perm_recursive "$MODPATH/scripts" 0 0 0755 0755
set_perm_recursive "$MODPATH/system/bin" 0 0 0755 0755

ui_print "- Kurulum basariyla tamamlandi!"
ui_print "- Modul yonetiminden WebUI'yi acabilirsiniz."
