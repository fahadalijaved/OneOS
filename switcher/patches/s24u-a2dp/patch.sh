#!/system/bin/sh
# Galaxy S24 Ultra A2DP session patch for Android 17 AOSP-family guests.
# guest_prepare.sh sources this file from apm_copy(). This module owns the
# device/image selection and the staged XML transformation; the generic caller
# only dispatches to it and consumes the resulting APM_NOTE/APM_ADDED fields.

oneos_s24u_a2dp_matches() {
    [ "$1" = s-ultra-8650 ] || return 1
    case "$2" in
        pixel9proxl-komodo|pixelos17-onyx|lineage24-infiniti|infinityx41-findx9u) ;;
        *) return 1 ;;
    esac
    [ "$3" = SM-S928B ] && [ "$4" = SM8650 ]
}

oneos_s24u_a2dp_matches_stage() {
    [ -f "$STAGE/.oneos_stage" ] || return 1
    s24u_profile=$(sed -n 's/^  "profile": "\([a-z0-9-]*\)",$/\1/p' "$STAGE/.oneos_stage" | head -n 1)
    s24u_image=$(sed -n 's/^  "image": "\([a-z0-9-]*\)",$/\1/p' "$STAGE/.oneos_stage" | head -n 1)
    oneos_s24u_a2dp_matches "$s24u_profile" "$s24u_image" "$(getprop ro.product.model)" "$(getprop ro.soc.model)"
}

oneos_s24u_a2dp_has_bt_library() {
    for s24u_dir in /vendor/lib64/hw /vendor/lib/hw /odm/lib64/hw /odm/lib/hw; do
        for s24u_lib in "$s24u_dir"/audio.bluetooth.*.so; do
            [ -f "$s24u_lib" ] && return 0
        done
    done
    return 1
}

# Add a vendor policy module include to the staged policy copy. This is the
# actual device fix: the A2DP ports belong to Samsung's software Bluetooth
# module instead of Qualcomm's primary PAL/offload path.
oneos_s24u_a2dp_add_module_include() {
    s24u_policy=$1
    s24u_module=$2
    [ -f "$s24u_policy" ] && [ ! -L "$s24u_policy" ] || return 1
    s24u_tmp="$s24u_policy.s24u-a2dp.$$"
    rm -f "$s24u_tmp"
    if awk -v inc="$s24u_module" '
        function blank(n, s) { s = ""; while (n-- > 0) s = s " "; return s }
        { doc = doc $0 "\n" }
        END {
            w = doc
            while ((i = index(w, "<!--")) > 0) {
                j = index(substr(w, i), "-->"); if (!j) exit 1
                w = substr(w, 1, i - 1) blank(j + 2) substr(w, i + j + 2)
            }
            if (!index(w, "xmlns:xi=")) exit 1
            p = index(w, "</modules>")
            if (!p || index(substr(w, p + 1), "</modules>")) exit 1
            b = p; while (b > 1 && substr(doc, b - 1, 1) != "\n") b--
            ind = substr(doc, b, p - b); lead = ""
            if (ind !~ /^[ \t]*$/) { ind = "    "; lead = "\n" ind }
            printf "%s", substr(doc, 1, p - 1) lead "    <!-- OneOS S24 Ultra A2DP: Samsung software Bluetooth route -->\n" ind "    <xi:include href=\"" inc "\"/>\n" ind substr(doc, p)
        }' "$s24u_policy" > "$s24u_tmp" &&
       [ "$(grep -c "<xi:include href=\"$s24u_module\"/>" "$s24u_tmp")" = 1 ]; then
        cat "$s24u_tmp" > "$s24u_policy" || { rm -f "$s24u_tmp"; return 1; }
        rm -f "$s24u_tmp"
        return 0
    fi
    rm -f "$s24u_tmp"
    return 1
}

# Called by guest_prepare.sh's apm_copy <vendor policy> <stage copy> <add outputs>.
# Return 2 when this device/image does not match (the caller uses generic A2DP
# handling); return 0 once this module has handled the decision, including a
# safe refusal that must not fall through to Qualcomm's failing primary route.
oneos_s24u_a2dp_apm_a2dp() {
    oneos_s24u_a2dp_matches_stage || return 2

    if [ "${ONEOS_GUEST_APM_A2DP:-1}" != 1 ]; then
        APM_NOTE="S24 Ultra A2DP patch: A2DP outputs disabled by ONEOS_GUEST_APM_A2DP"
        return 0
    fi

    # An image that already supplies its own A2DP route owns that policy. Do
    # not append Samsung's module or manufacture the primary PAL route.
    s24u_apm_inc=$($BB grep -o 'href="/[^" ]*"' "$2" | $BB sed -e 's/^href="//' -e 's/"$//')
    if $BB grep -qs 'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP' "$2" $s24u_apm_inc; then
        APM_NOTE="S24 Ultra A2DP patch: guest policy already defines A2DP; left unchanged"
        return 0
    fi

    s24u_bt=/vendor/etc/bluetooth_audio_policy_configuration.xml
    case "$(tr '\n\t' '  ' < "$2" | sed -n 's/.*<audioPolicyConfiguration[^>]* version="\([0-9.]*\)".*/\1/p')" in
        7.*)
            if [ -f "${s24u_bt%.xml}_7_0.xml" ] && $BB grep -qs 'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP"' "${s24u_bt%.xml}_7_0.xml"; then
                s24u_bt="${s24u_bt%.xml}_7_0.xml"
            fi ;;
    esac

    if [ ! -f "$s24u_bt" ] || ! $BB grep -qs 'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP"' "$s24u_bt" ||
       ! oneos_s24u_a2dp_has_bt_library ||
       ! $BB grep -rqs -E 'ISehBluetoothAudioProviderFactory|IBluetoothAudioProviderFactory' /vendor/etc/vintf/; then
        APM_NOTE="S24 Ultra A2DP patch: Samsung software Bluetooth policy/module unavailable; primary PAL route not added"
        return 0
    fi

    if oneos_s24u_a2dp_add_module_include "$2" "$s24u_bt"; then
        APM_NOTE="Bluetooth A2DP outputs added with the vendor's Bluetooth module (${s24u_bt##*/}); S24 Ultra patch selects software A2DP and bypasses Qualcomm offload"
        APM_ADDED=1
    else
        APM_NOTE="S24 Ultra A2DP patch: policy include was rejected; primary PAL route not added"
    fi
    return 0
}

# The service bridge has a separate phase because it runs on the host after
# VINTF setup. Keep the selector here so unsupported guests use the normal mode.
oneos_s24u_a2dp_bridge_args() {
    oneos_s24u_a2dp_matches "$@" || return 0
    printf '%s\n' --watch-replacements
}
