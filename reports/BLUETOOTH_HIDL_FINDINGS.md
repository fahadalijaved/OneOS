# Bluetooth Audio (A2DP) HIDL 2.1 Findings on Galaxy S22 (SM8450 / `s-8450`)

## Summary
Bluetooth A2DP audio fails in Android 17 guests (Nothing OS 5.0 `nothingos5-asteroids`, One UI 9.5) on Galaxy S22 Snapdragon (`SM-S901U`, `r0q`, `SM8450` / `taro`, One UI 8.0 / SDK 36) because the vendor audio HAL (`audio.service_6`) only registers Samsung's **HIDL 2.1** Bluetooth audio factory (`vendor.samsung.hardware.bluetooth.audio@2.1::ISehBluetoothAudioProvidersFactory/default`), whereas `oneos_btaudio.cpp` only bridges Samsung's **AIDL** factory (`ISehBluetoothAudioProviderFactory`) and `oneos_switch.sh` previously missed SKU-specific VINTF manifests (`/vendor/etc/vintf/manifest_taro.xml`).

---

## 1. Root Causes Identified

### A. VINTF Manifest Path (`manifest_taro.xml`)
On SM8450 (`taro`, `ro.boot.product.vendor.sku=taro`), the Bluetooth audio HAL is declared in:
- `/vendor/etc/vintf/manifest_taro.xml` (line 524):
  ```xml
  <hal format="hidl">
      <name>vendor.samsung.hardware.bluetooth.audio</name>
      <version>2.1</version>
      <interface>
          <name>ISehBluetoothAudioProvidersFactory</name>
          <instance>default</instance>
      </interface>
      ...
  </hal>
  ```
`oneos_switch.sh` previously only searched `/vendor/etc/vintf/manifest/*.xml` and `/vendor/etc/vintf/manifest.xml`, causing it to miss `manifest_${BT_SKU}.xml` and report:
`Bluetooth audio bridge: not needed (no vendor manifest declares Samsung's Bluetooth audio HAL)`.

### B. HIDL 2.1 Only (No AIDL Factory)
Live `lshal` / `hwservicemanager` inspection on `SM-S901U` confirms `audio.service_6` (`PID 1513` in One UI, `PID 8884` in guest) registers:
- `vendor.samsung.hardware.bluetooth.audio@2.1::ISehBluetoothAudioProvidersFactory/default`
- `vendor.samsung.hardware.bluetooth.a2dp@1.0::ISehBluetoothAudioOffload/default`
- `vendor.samsung.hardware.bluetooth.a2dpsink@1.0::ISehBluetoothA2dpSinkProvidersFactory/default`

It does **not** register any AIDL `IBluetoothAudioProviderFactory` or `ISehBluetoothAudioProviderFactory`.

---

## 2. Guest Failure Trace (`oneos-logs-17a96e8bbab01392.zip`)
1. `com.android.bluetooth` (`PID 25878`) logs:
   - `HalVersionManager: No supported HAL version` (`hal_version_manager.cc:226`)
   - `GetHalTransport: HAL Transport: UNKNOWN` (`hal_version_manager.cc:108`)
   - `btif_a2dp_source_startup: Failed to setup the bluetooth audio HAL` (`btif_a2dp_source.cc:451`)
2. When an A2DP headset (`Josh's Buds`, `AAC 44100 Stereo`) connects, `AHAL` opens `bt-a2dp` (`PAL_DEVICE_OUT_BLUETOOTH_A2DP`, `SLIM-DEV1-RX-7`), and `PAL: Bluetooth: startPlayback` fails in a loop with `ret=-38` (`ENOSYS`).
3. Setting `persist.bluetooth.a2dp_offload.disabled=true` does **not** bypass this because `com.android.bluetooth` still requires `IBluetoothAudioProvider(s)Factory` for `A2DP_SOFTWARE_ENCODING_DATAPATH`.

---

## 3. On-Device Libraries & ABI Findings (Termux `llvm-nm` / `llvm-objdump`)
Inspection of `/vendor/lib64/` on `SM-S901U` confirmed:
- Present on device:
  - `/vendor/lib64/android.hardware.bluetooth.audio@2.0.so`
  - `/vendor/lib64/android.hardware.bluetooth.audio@2.1.so`
  - `/vendor/lib64/hw/android.hardware.bluetooth.audio@2.0-impl.so`
  - `/vendor/lib64/vendor.samsung.hardware.bluetooth.audio@2.0.so`
  - `/vendor/lib64/vendor.samsung.hardware.bluetooth.audio@2.1.so`
- `vendor.samsung.hardware.bluetooth.audio@2.0` / `@2.1` (`ISehBluetoothAudioProvidersFactory`, `ISehBluetoothAudioProvider`, `ISehBluetoothAudioPort`) are **1:1 ABI / transaction-ID mirrors** of AOSP `android.hardware.bluetooth.audio@2.0` / `@2.1` (e.g., `getProviderCapabilities_2_1` uses transaction ID `0x4` in `BpHwSehBluetoothAudioProvidersFactory`, with `codec_type=7` SSC in capabilities).

---

## 4. Recommended Upstream Fix for `oneos_btaudio`
1. **Keep `oneos_switch.sh` checking `/vendor/etc/vintf/manifest_${BT_SKU}.xml`** (included in this PR/patch).
2. **Add HIDL 2.1 -> AIDL (or HIDL 2.1 -> AOSP HIDL 2.1) bridge support** in `switcher/native/oneos_btaudio.cpp` (compiled against AOSP `libhidlbase` / `android.hardware.bluetooth.audio@2.1` headers rather than raw `BHwBinder` vtable shims):
   - Register `android.hardware.bluetooth.audio.IBluetoothAudioProviderFactory/default` (AIDL, via `AServiceManager_addService` + `guest_bt_audio` VINTF fragment) **or** `android.hardware.bluetooth.audio@2.1::IBluetoothAudioProvidersFactory/default` (HIDL, if VINTF-declared).
   - Forward `getProviderCapabilities`, `openProvider`, `startSession`, `streamStarted`, `streamSuspended`, `updateAudioConfiguration`, and `endSession` to `vendor.samsung.hardware.bluetooth.audio@2.1::ISehBluetoothAudioProvidersFactory/default` using the identical AOSP `@2.1` transaction IDs and Parcel layouts.
3. Once the HIDL bridge is in place, enable `apm_bt` for `SM8450` in `guest_prepare.sh` (`apm_a2dp`). Until then, `guest_prepare.sh` intentionally leaves `apm_bt` off on `SM8450` to avoid `PAL: Bluetooth: startPlayback ret=-38` loops.
