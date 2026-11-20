#!/system/bin/sh
# OneOS Switcher & SwBridge IO Engine v2.0 Final
# Author: Mualiy.net & Fahad Ali Team (MuhammedAliTR)
# Function: Pure & Ultra-Fast Lockscreen Management (SwOUT / SwIN)
# No root manipulation, no database locks, no background service overhead.

ACTION="$1"
BASE_DIR="/data/adb/oneos_helper"
CONFIG_FILE="$BASE_DIR/config.json"
LOG_FILE="$BASE_DIR/helper.log"

mkdir -p "$BASE_DIR"
touch "$LOG_FILE"
chmod 700 "$BASE_DIR"

log() {
    local level="$1"
    local msg="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $msg" >> "$LOG_FILE"
    echo "[$level] $msg"
}

get_config_val() {
    local key="$1"
    if [ -f "$CONFIG_FILE" ]; then
        grep -o "\"$key\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" "$CONFIG_FILE" | head -n 1 | sed 's/.*:[[:space:]]*"\(.*\)"/\1/'
    fi
}

# --- SWOUT: HIZLICA ŞİFRE VE KİLİDİ KALDIRIR ---
swout() {
    log "INFO" "========================================="
    log "INFO" "🚀 [SwOUT] Kilit ve Şifreleme Kaldırılıyor..."
    log "INFO" "========================================="

    local pin=$(get_config_val "pin")
    local auth_type=$(get_config_val "auth_type")
    local swapout_mode=$(get_config_val "swapout_mode")
    [ -z "$swapout_mode" ] && swapout_mode="none"

    if [ -n "$pin" ] && [ "$auth_type" != "none" ]; then
        log "CMD" "locksettings clear --old ****"
        locksettings clear --old "$pin" 2>&1
    else
        locksettings clear 2>&1
    fi

    if [ "$swapout_mode" = "none" ]; then
        locksettings set-disabled true 2>&1
        log "SUCCESS" "-> Kilit tamamen devre dışı bırakıldı (NONE)."
    else
        locksettings set-disabled false 2>&1
        log "SUCCESS" "-> Kilit kaydırma moduna alındı (SWIPE)."
    fi

    # Gatekeeper kilit artıklarını temizle
    rm -f /data/system/gatekeeper.password.key /data/system/gatekeeper.pattern.key 2>/dev/null

    log "SUCCESS" "========================================="
    log "SUCCESS" "✨ [SwOUT BAŞARILI] Şifre kaldırıldı, güvenle geçiş yapabilirsiniz!"
    log "SUCCESS" "========================================="
    return 0
}

# --- SWIN: ŞİFREYİ GERİ KOYAR ---
swin() {
    log "INFO" "========================================="
    log "INFO" "🏠 [SwIN] Ekran Kilidi ve PIN Geri Yükleniyor..."
    log "INFO" "========================================="

    local pin=$(get_config_val "pin")
    local auth_type=$(get_config_val "auth_type")

    locksettings set-disabled false 2>&1

    if [ -n "$pin" ] && [ "$auth_type" != "none" ]; then
        if [ "$auth_type" = "password" ]; then
            locksettings set-password "$pin" 2>&1
            log "SUCCESS" "-> Alfanümerik şifre başarıyla geri kondu."
        else
            locksettings set-pin "$pin" 2>&1
            log "SUCCESS" "-> Sayısal PIN başarıyla geri kondu."
        fi
    else
        log "INFO" "-> Şifresiz mod seçili olduğu için PIN konulmadı."
    fi

    log "SUCCESS" "========================================="
    log "SUCCESS" "🎉 [SwIN BAŞARILI] Şifreniz aktif hale getirildi!"
    log "SUCCESS" "========================================="
    return 0
}

status_info() {
    local configured="false"
    [ -f "$CONFIG_FILE" ] && configured="true"

    local auth_t=$(get_config_val "auth_type")
    local theme=$(get_config_val "theme")
    local smode=$(get_config_val "swapout_mode")
    local lang=$(get_config_val "lang")
    [ -z "$auth_t" ] && auth_t="pin"
    [ -z "$theme" ] && theme="oneui"
    [ -z "$smode" ] && smode="none"
    [ -z "$lang" ] && lang="auto"

    echo "{\"configured\":$configured,\"auth_type\":\"$auth_t\",\"theme\":\"$theme\",\"swapout_mode\":\"$smode\",\"lang\":\"$lang\"}"
}

case "$ACTION" in
    swout|swapout)
        swout
        ;;
    swin|swapin)
        swin
        ;;
    status)
        status_info
        ;;
    log)
        [ -f "$LOG_FILE" ] && cat "$LOG_FILE" || echo "Henüz log kaydı yok."
        ;;
    clearlog)
        > "$LOG_FILE"
        echo "[CLEAR] Log temizlendi."
        ;;
    *)
        echo "Kullanım: $0 {swout|swin|status|log|clearlog}"
        exit 1
        ;;
esac
exit 0
