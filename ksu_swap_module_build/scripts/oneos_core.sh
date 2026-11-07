#!/system/bin/sh
# OneOS Switcher & Superuser Bridge Helper Engine
# Author: Mualiy.net & Fahad Ali Team
# Architecture: KernelSU & Android 12+ (Samsung One UI / MysticGSI / Treble)

ACTION="$1"
BASE_DIR="/data/adb/oneos_helper"
CONFIG_FILE="$BASE_DIR/config.json"
BACKUP_DIR="$BASE_DIR/backup"
LOG_FILE="$BASE_DIR/helper.log"
KSU_DIR="/data/adb/ksu"
KSU_PROFILES_DIR="/data/adb/ksu/profile"
KSU_ALLOWLIST_FILE="/data/adb/ksu/.allowlist"
MANAGER_DATA="/data/data/me.weishu.kernelsu/databases"

mkdir -p "$BASE_DIR" "$BACKUP_DIR"
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

backup_su() {
    log "INFO" ">>> [STEP 1/3] Başlatılıyor: KernelSU Süper Kullanıcı İzinleri Yedekleme..."
    rm -rf "$BACKUP_DIR/profile"
    rm -f "$BACKUP_DIR/.allowlist"
    rm -rf "$BACKUP_DIR/manager_db"
    mkdir -p "$BACKUP_DIR/profile"
    
    local backed_up=0
    
    # 1. /data/adb/ksu/profile/ JSON yedekleri
    if [ -d "$KSU_PROFILES_DIR" ]; then
        log "CMD" "cp -a $KSU_PROFILES_DIR/. $BACKUP_DIR/profile/"
        cp -a "$KSU_PROFILES_DIR"/. "$BACKUP_DIR/profile/" 2>/dev/null
        local count=$(ls -1 "$BACKUP_DIR/profile" 2>/dev/null | wc -l)
        log "INFO" "-> KernelSU Profil dizininden $count adet uygulama profili yedeklendi."
        backed_up=1
    else
        log "WARN" "-> $KSU_PROFILES_DIR dizini henüz mevcut değil veya boş."
    fi

    # 2. KernelSU .allowlist dosyası
    if [ -f "$KSU_ALLOWLIST_FILE" ]; then
        log "CMD" "cp -a $KSU_ALLOWLIST_FILE $BACKUP_DIR/.allowlist"
        cp -a "$KSU_ALLOWLIST_FILE" "$BACKUP_DIR/.allowlist" 2>/dev/null
        log "INFO" "-> KernelSU kernel .allowlist dosyası başarıyla arşivlendi."
        backed_up=1
    fi

    # 3. KernelSU Manager SQLite Veritabanı
    if [ -d "$MANAGER_DATA" ]; then
        mkdir -p "$BACKUP_DIR/manager_db"
        log "CMD" "cp -a $MANAGER_DATA/. $BACKUP_DIR/manager_db/"
        cp -a "$MANAGER_DATA"/. "$BACKUP_DIR/manager_db/" 2>/dev/null
        log "INFO" "-> KernelSU Manager yerel veritabanı (me.weishu.kernelsu) yedeklendi."
        backed_up=1
    fi

    echo "$(date '+%s')" > "$BACKUP_DIR/backup_timestamp"
    log "SUCCESS" "[BAŞARILI] Superuser izinleri ve veritabanı tam snapshot olarak arşivlendi!"
    return 0
}

restore_su() {
    log "INFO" ">>> [STEP 1/4] Başlatılıyor: KernelSU Süper Kullanıcı İzinlerini Geri Yükleme..."
    if [ ! -f "$BACKUP_DIR/backup_timestamp" ]; then
        log "ERROR" "[HATA] Kayıtlı bir Superuser yedeği bulunamadı! İşlem durduruluyor."
        return 1
    fi

    # 1. Eski profilleri tamamen temizle (KESİN OVERRIDE GARANTİSİ)
    # Yedekten sonra 5 uygulama 6'ya çıkmış olsa bile tamamen sıfırlanıp 5'e düşürülür!
    log "INFO" "-> Mevcut profiller ve izinler sıfırlanıyor (Strict Override Mode)..."
    if [ -d "$KSU_PROFILES_DIR" ]; then
        log "CMD" "rm -rf $KSU_PROFILES_DIR/*"
        rm -rf "$KSU_PROFILES_DIR"/*
    fi
    mkdir -p "$KSU_PROFILES_DIR"
    chmod 755 "$KSU_PROFILES_DIR"

    if [ -d "$BACKUP_DIR/profile" ]; then
        log "CMD" "cp -a $BACKUP_DIR/profile/. $KSU_PROFILES_DIR/"
        cp -a "$BACKUP_DIR/profile"/. "$KSU_PROFILES_DIR/" 2>/dev/null
        chmod 644 "$KSU_PROFILES_DIR"/* 2>/dev/null
        local res_count=$(ls -1 "$KSU_PROFILES_DIR" 2>/dev/null | wc -l)
        log "INFO" "-> $res_count adet profil geri yüklendi ve izinler 644 yapıldı."
    fi

    # 2. .allowlist dosyasını override et
    if [ -f "$BACKUP_DIR/.allowlist" ]; then
        log "CMD" "cp -a $BACKUP_DIR/.allowlist $KSU_ALLOWLIST_FILE"
        cp -a "$BACKUP_DIR/.allowlist" "$KSU_ALLOWLIST_FILE" 2>/dev/null
        chmod 600 "$KSU_ALLOWLIST_FILE"
        log "INFO" "-> .allowlist kernel listesi geri yüklendi."
    fi

    # 3. Manager veritabanı override
    if [ -d "$BACKUP_DIR/manager_db" ] && [ -d "$MANAGER_DATA" ]; then
        log "CMD" "cp -a $BACKUP_DIR/manager_db/. $MANAGER_DATA/"
        cp -a "$BACKUP_DIR/manager_db"/. "$MANAGER_DATA/" 2>/dev/null
        chmod 660 "$MANAGER_DATA"/* 2>/dev/null
        log "INFO" "-> KernelSU Manager SQLite veritabanı snapshot üzerine yazıldı."
    fi

    # 4. ksud daemon & Manager yenileme (ksud refresh / pkill)
    log "INFO" ">>> [STEP 2/4] KernelSU Daemon (ksud) ve Manager servisi yenileniyor..."
    if command -v ksud >/dev/null 2>&1; then
        log "CMD" "ksud profile reload"
        ksud profile reload 2>/dev/null || ksud service restart 2>/dev/null
    elif [ -f "/data/adb/ksud" ]; then
        log "CMD" "/data/adb/ksud profile reload"
        /data/adb/ksud profile reload 2>/dev/null || /data/adb/ksud service restart 2>/dev/null
    fi

    # ksud process yenile & Manager arayüzünü resetle
    pkill -f ksud 2>/dev/null || true
    pkill -f me.weishu.kernelsu 2>/dev/null || true
    log "SUCCESS" "[BAŞARILI] Superuser izinleri yedeğin birebir kopyası olarak geri yüklendi!"
    return 0
}

swap_out() {
    log "INFO" "========================================="
    log "INFO" "🚀 [SWAP-OUT] GUEST ROM'A GEÇİŞ İŞLEMİ BAŞLADI"
    log "INFO" "========================================="
    
    # Adım 1: Root ve SuperUser Yedekleme
    backup_su
    if [ $? -ne 0 ]; then
        log "ERROR" "Yedekleme başarısız olduğu için SwapOUT durduruldu!"
        return 1
    fi

    # Adım 2: Lockscreen / Şifreleme Kaldırma
    local pin=$(get_config_val "pin")
    local auth_type=$(get_config_val "auth_type")
    local swapout_mode=$(get_config_val "swapout_mode")
    [ -z "$swapout_mode" ] && swapout_mode="none"

    log "INFO" ">>> [STEP 2/3] Güvenlik & Kilit Ekranı Şifrelemesi Kaldırılıyor..."
    
    if [ -n "$pin" ] && [ "$auth_type" != "none" ]; then
        log "CMD" "locksettings clear --old ****"
        local out=$(locksettings clear --old "$pin" 2>&1)
        log "INFO" "locksettings yanıtı: $out"
    else
        log "INFO" "Şifresiz mod aktif. locksettings clear çağrılıyor..."
        locksettings clear 2>&1
    fi

    if [ "$swapout_mode" = "none" ]; then
        log "INFO" "-> Kilit modu 'NONE' (Tamamen Devre Dışı) yapılıyor..."
        log "CMD" "locksettings set-disabled true"
        locksettings set-disabled true 2>&1
    else
        log "INFO" "-> Kilit modu 'SWIPE' (Kaydırarak Aç) yapılıyor..."
        log "CMD" "locksettings set-disabled false"
        locksettings set-disabled false 2>&1
    fi

    # Userdata anahtar artıklarını temizle
    log "INFO" ">>> [STEP 3/3] Userdata kilit anahtarı önbellekleri temizleniyor..."
    rm -f /data/system/gatekeeper.password.key /data/system/gatekeeper.pattern.key 2>/dev/null
    
    log "SUCCESS" "========================================="
    log "SUCCESS" "✨ [SWAP-OUT TAMAMLANDI] Güvenlik şifrelemesi kaldırıldı!"
    log "SUCCESS" "⚠️ OneOS üzerinden diğer sisteme (ColorOS/PixelOS/NothingOS) güvenle geçebilirsiniz."
    log "SUCCESS" "========================================="
    return 0
}

swap_in() {
    log "INFO" "========================================="
    log "INFO" "🏠 [SWAP-IN] ONE UI'A DÖNÜŞ VE RESTORE BAŞLADI"
    log "INFO" "========================================="

    # Adım 1: Superuser Geri Yükleme
    restore_su
    if [ $? -ne 0 ]; then
        log "WARN" "Superuser restore uyarısı, kilit aktivasyonuna devam ediliyor..."
    fi

    # Adım 2: Ekran Kilidi & PIN Yeniden Aktif Etme
    log "INFO" ">>> [STEP 3/4] Ekran Kilidi ve FBE Şifreleme Koruması Yeniden Kuruluyor..."
    local pin=$(get_config_val "pin")
    local auth_type=$(get_config_val "auth_type")

    log "CMD" "locksettings set-disabled false"
    locksettings set-disabled false 2>&1

    if [ -n "$pin" ] && [ "$auth_type" != "none" ]; then
        if [ "$auth_type" = "password" ]; then
            log "INFO" "-> Alfanümerik Şifre yeniden uygulanıyor..."
            log "CMD" "locksettings set-password ****"
            locksettings set-password "$pin" 2>&1
        else
            log "INFO" "-> Sayısal PIN yeniden uygulanıyor..."
            log "CMD" "locksettings set-pin ****"
            locksettings set-pin "$pin" 2>&1
        fi
        log "SUCCESS" "-> Ekran kilidi ve şifreleme başarıyla tekrar kilitlendi!"
    else
        log "INFO" "-> Şifresiz profil tanımlandığı için PIN kurulmadı."
    fi

    log "INFO" ">>> [STEP 4/4] Sistem servisleri ve UI yeniden senkronize ediliyor..."
    log "SUCCESS" "========================================="
    log "SUCCESS" "🎉 [SWAP-IN TAMAMLANDI] One UI cihazınız güvenli ve tam rootlu haline döndü!"
    log "SUCCESS" "========================================="
    return 0
}

manual_su_bak() {
    log "INFO" "========================================="
    log "INFO" "🛡️ [MANUEL SU BAK] ANLIK SUPERUSER YEDEKLEMESİ"
    log "INFO" "========================================="
    backup_su
    log "SUCCESS" "Manuel SU yedeği başarıyla tamamlandı. Dosyalar $BACKUP_DIR altında güncellendi."
}

case "$ACTION" in
    swapout)
        swap_out
        ;;
    swapin)
        swap_in
        ;;
    manuelsubak)
        manual_su_bak
        ;;
    restore)
        restore_su
        ;;
    status)
        local configured="false"
        [ -f "$CONFIG_FILE" ] && configured="true"
        local b_cnt=0
        [ -d "$BACKUP_DIR/profile" ] && b_cnt=$(ls -1 "$BACKUP_DIR/profile" 2>/dev/null | wc -l)
        local a_cnt=0
        [ -d "$KSU_PROFILES_DIR" ] && a_cnt=$(ls -1 "$KSU_PROFILES_DIR" 2>/dev/null | wc -l)
        local auth_t=$(get_config_val "auth_type")
        local theme=$(get_config_val "theme")
        local smode=$(get_config_val "swapout_mode")
        local lmode=$(get_config_val "log_mode")
        [ -z "$auth_t" ] && auth_t="pin"
        [ -z "$theme" ] && theme="oneui"
        [ -z "$smode" ] && smode="none"
        [ -z "$lmode" ] && lmode="advanced"
        echo "{\"configured\":$configured,\"auth_type\":\"$auth_t\",\"theme\":\"$theme\",\"swapout_mode\":\"$smode\",\"log_mode\":\"$lmode\",\"backup_count\":$b_cnt,\"active_count\":$a_cnt}"
        ;;
    log)
        if [ -f "$LOG_FILE" ]; then
            cat "$LOG_FILE"
        else
            echo "Henüz log kaydı yok."
        fi
        ;;
    clearlog)
        > "$LOG_FILE"
        echo "[CLEAR] Log temizlendi."
        ;;
    *)
        echo "Kullanım: $0 {swapout|swapin|manuelsubak|restore|status|log|clearlog}"
        exit 1
        ;;
esac
exit 0
