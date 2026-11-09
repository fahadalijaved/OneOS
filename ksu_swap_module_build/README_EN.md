# OneOS Switcher & Superuser Bridge Helper Module (KernelSU)

[![KernelSU](https://img.shields.io/badge/KernelSU-Supported-brightgreen.svg)](https://kernelsu.org/)
[![Platform](https://img.shields.io/badge/Platform-Samsung%20One%20UI%20%7C%20MysticGSI-blue.svg)](https://github.com/fahadalijaved/OneOS)
[![Author](https://img.shields.io/badge/Maintainer-Mualiy.net%20%26%20Fahad%20Ali%20Team-orange.svg)](http://Mualiy.net)
[![License](https://img.shields.io/badge/License-GPLv3-yellow.svg)](LICENSE)

An essential companion module for [OneOS](https://github.com/fahadalijaved/OneOS) running on rooted Samsung Galaxy devices with KernelSU / KernelSU Next / APatch / MMRL.

This module resolves the **two critical stability and security roadblocks** when hot-switching between Samsung One UI and guest GSI systems (e.g. ColorOS, PixelOS, NothingOS, AOSP):

1. **Dead Userdata / FBE Keystore Corruption:** Prevents fatal encryption lockouts when entering guest systems by gracefully disabling lockscreen credentials beforehand and restoring them upon return.
2. **Superuser Grant Loss & Strict Override:** Eliminates root permission drops when returning to One UI by enforcing a bit-for-bit snapshot restore of the KernelSU allowlist and app profiles (strict override guarantee).

---

## ⚡ The Problems & How This Module Solves Them

### 1. File-Based Encryption (FBE) & Lockscreen Lockout (Dead Userdata)
* **The Root Cause:** Samsung's proprietary Gatekeeper, Keystore, and Knox framework tie storage encryption keys directly to the lockscreen credential (PIN/Password). When hot-switching to an untrusted guest GSI without removing the screen lock, the guest environment cannot authenticate against the Samsung hardware keystore, resulting in unmountable storage, bootloops, or permanent userdata corruption ("Dead Userdata").
* **The Solution (`SwapOUT`):**
  - Clears the active PIN/Password using native Android framework hooks (`locksettings clear --old ****`).
  - Sets the lockscreen to **None** (`locksettings set-disabled true`) or **Swipe** mode according to user preference.
  - Purges transient Gatekeeper cache tokens so the guest OS boots safely without encryption conflicts.
* **The Return (`SwapIN`):**
  - Re-arms the lockscreen and re-applies your saved numerical PIN or alphanumeric password (`locksettings set-pin/password ****`).
  - Re-enables full Android security and Knox-compatible FBE protection instantly.

### 2. Loss of Superuser Grants & Strict Snapshot Override
* **The Root Cause:** KernelSU manages root grants across `/data/adb/ksu/profile/`, `/data/adb/ksu/.allowlist`, and its Manager database. During multi-ROM hot-switching, daemon resets often wipe granted UIDs, forcing users to re-grant root to dozens of applications.
* **The Solution (Strict Override Guarantee):**
  - **Snapshot:** Backs up all JSON application profiles, kernel UID tables, and Manager databases.
  - **Strict Override:** When restoring, the target profile directory is cleanly wiped prior to writing the backup. **If 5 apps had root at backup time, but 6 exist prior to restore, the restore strictly overwrites the state back to the original 5.**
  - Triggers a clean `ksud profile reload` and daemon sync without requiring a full device reboot.

---

## 🖥️ Modern WebUI Dashboard

The module includes a fully responsive WebUI accessible directly from the **KernelSU Manager** / **MMRL** module card:

* **First-Run Onboarding Wizard:**
  - Setup screen prompts for numerical PIN, alphanumeric password, or passwordless mode.
  - Masked password input (`****`) with an SVG toggle eye (Show/Hide).
  - All action buttons remain locked until initial setup is completed; once configured, the wizard is dismissed permanently.
* **Core Action Cards:**
  - **🚀 SwapOUT:** Full SU snapshot + Lockscreen removal -> Phone is 100% ready for guest OS switch.
  - **🏠 SwapIN:** Strict SU override restore + Lockscreen re-engagement -> Phone is secure and back in One UI.
  - **🛡️ ManuelSUBak:** Standalone one-tap backup of current root grants without modifying lockscreen state.
* **Interactive Live Console:**
  - Real-time logging displaying every executed shell command, exit code, and status report.
  - Switchable between **Advanced Mode (Verbose code output)** and **Basic Mode (Summary only)**.
* **Themes & Personalization:**
  - **OneUI (Default):** Tailored to match Samsung One UI design guidelines (AMOLED black, One UI blue, smooth rounded corners).
  - **Material 3 Expressive:** Modern Google Pixel styling with dynamic tonal palettes.
  - **MiuiX (HyperOS-like):** Compact cards with crisp typography and subtle blur effects.
  - **One-tap Light / Dark Mode Toggle** on the top-left navigation bar.

---

## 📥 Installation

1. Download the latest `OneOS_Switcher_SU_Bridge_v1.2.0.zip` from [Releases](../../releases).
2. Open **KernelSU Manager** (or KernelSU Next, APatch, MMRL).
3. Navigate to **Modules** -> **Install** and select the ZIP file.
4. Reboot your phone to initialize the service and permissions.
5. Tap **WebUI** on the module card to launch the control dashboard.

---

## ⌨️ CLI / Terminal Usage

For advanced users, automation, or custom OneOS switcher script integration, a companion binary is available via root shell:

```bash
# Prepare for Guest OS switch (Backup SU & Disable Lockscreen)
su -c oneos-bridge swapout

# Restore upon returning to One UI (Restore SU Override & Enable PIN)
su -c oneos-bridge swapin

# Take an instant standalone Superuser snapshot
su -c oneos-bridge manuelsubak

# Inspect current configuration and backup status (JSON output)
su -c oneos-bridge status

# View the execution log
su -c oneos-bridge log
```

---

## 🧩 Dependencies

**Zero external dependencies required!**
* No external Python, Node.js, or heavy binaries needed.
* Works 100% natively using Android's built-in `toybox`, `/system/bin/sh`, Android framework `locksettings`, and KernelSU's native userspace `ksud` / WebUI JavaScript bridge.

---

## 👥 Credits & Authors

* **Maintainer & Developer:** [Mualiy.net](http://Mualiy.net)
* **OneOS Core Project:** [Fahad Ali](https://github.com/fahadalijaved) & Team
* **Upstream Acknowledgements:**
  - WeWaffles (*OneLineage container concept*)
  - The MysticGSI Authors & phh (*TrebleDroid / GSI foundations*)
  - KernelSU Team (*Kernel-assisted root & WebUI bridge*)
