"""Store a guest-local PIN in LockSettingsService, without the host gatekeeper.

One UI's gatekeeper and weaver stay read-only. The guest's PIN is a salted
SHA-256 in /data/system/oneos_pin, checked by LockSettingsService itself.
The screen lock is only as strong as the guest's /data, which is the point:
it works on any firmware and never touches the phone's credential store.

Usage: guest_local_pin.py <smali root dir>
Prints the smali_* directory it changed.
"""
import os
import sys

PIN = r'''    move/from16 v0, p3

    if-nez v0, :oneos_pin_set_native

    move-object/from16 v1, p1

    if-eqz v1, :oneos_pin_set_native

    invoke-virtual {v1}, Lcom/android/internal/widget/LockscreenCredential;->isNone()Z

    move-result v0

    if-nez v0, :oneos_pin_set_none

    invoke-virtual {v1}, Lcom/android/internal/widget/LockscreenCredential;->getType()I

    move-result v0

    const/4 v2, 0x3

    if-ne v0, v2, :oneos_pin_set_native

    invoke-virtual {v1}, Lcom/android/internal/widget/LockscreenCredential;->getCredential()[B

    move-result-object v0

    invoke-static {v0}, Lcom/android/server/locksettings/OneOsPin;->store([B)Z

    move-result v0

    const/4 v2, 0x0

    move-object/from16 v3, p0

    invoke-direct {v3, v2}, Lcom/android/server/locksettings/LockSettingsService;->invalidateCredentialTypeCaches(I)V

    return v0

    :oneos_pin_set_none
    invoke-static {}, Lcom/android/server/locksettings/OneOsPin;->clear()Z

    move-result v0

    const/4 v2, 0x0

    move-object/from16 v3, p0

    invoke-direct {v3, v2}, Lcom/android/server/locksettings/LockSettingsService;->invalidateCredentialTypeCaches(I)V

    return v0

    :oneos_pin_set_native
'''

VERIFY = r'''    move-object/from16 v0, p1

    move/from16 v1, p2

    if-eqz v0, :oneos_pin_verify_native

    invoke-virtual {v0}, Lcom/android/internal/widget/LockscreenCredential;->isNone()Z

    move-result v2

    if-nez v2, :oneos_pin_verify_native

    if-nez v1, :oneos_pin_verify_native

    invoke-virtual {v0}, Lcom/android/internal/widget/LockscreenCredential;->getType()I

    move-result v2

    const/4 v3, 0x3

    if-ne v2, v3, :oneos_pin_verify_native

    invoke-static {}, Lcom/android/server/locksettings/OneOsPin;->exists()Z

    move-result v2

    if-eqz v2, :oneos_pin_verify_native

    invoke-virtual {v0}, Lcom/android/internal/widget/LockscreenCredential;->getCredential()[B

    move-result-object v0

    invoke-static {v0}, Lcom/android/server/locksettings/OneOsPin;->verify([B)Z

    move-result v2

    if-eqz v2, :oneos_pin_verify_bad

    move-object/from16 v3, p3

    if-eqz v3, :oneos_pin_verify_unlock

    :try_start_oneos_cb
    invoke-interface {v3}, Lcom/android/internal/widget/ICheckCredentialProgressCallback;->onCredentialVerified()V
    :try_end_oneos_cb

    .catch Landroid/os/RemoteException; {:try_start_oneos_cb .. :try_end_oneos_cb} :catch_oneos_cb

    :catch_oneos_cb
    :oneos_pin_verify_unlock
    invoke-direct {p0, v1}, Lcom/android/server/locksettings/LockSettingsService;->setDeviceUnlockedForUser(I)V

    iget-object v3, p0, Lcom/android/server/locksettings/LockSettingsService;->mStrongAuth:Lcom/android/server/locksettings/LockSettingsStrongAuth;

    invoke-virtual {v3, v1}, Lcom/android/server/locksettings/LockSettingsStrongAuth;->reportSuccessfulStrongAuthUnlock(I)V

    const/4 v3, 0x1

    invoke-direct {p0, v3, v1}, Lcom/android/server/locksettings/LockSettingsService;->notifyLockSettingsStateListeners(ZI)V

    sget-object v0, Lcom/android/internal/widget/VerifyCredentialResponse;->OK:Lcom/android/internal/widget/VerifyCredentialResponse;

    return-object v0

    :oneos_pin_verify_bad
    sget-object v0, Lcom/android/internal/widget/VerifyCredentialResponse;->OTHER_ERROR:Lcom/android/internal/widget/VerifyCredentialResponse;

    return-object v0

    :oneos_pin_verify_native
'''

TYPE = r'''    move/from16 v0, p1

    if-nez v0, :oneos_pin_type_native

    invoke-static {}, Lcom/android/server/locksettings/OneOsPin;->exists()Z

    move-result v1

    if-eqz v1, :oneos_pin_type_none

    const/4 v1, 0x3

    return v1

    :oneos_pin_type_none
    const/4 v1, -0x1

    return v1

    :oneos_pin_type_native
'''

HELPER = r'''.class public final Lcom/android/server/locksettings/OneOsPin;
.super Ljava/lang/Object;

.field private static final FILE:Ljava/lang/String; = "/data/system/oneos_pin"

.method public constructor <init>()V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method private static hash([B[B)[B
    .locals 2

    const-string v0, "SHA-256"

    invoke-static {v0}, Ljava/security/MessageDigest;->getInstance(Ljava/lang/String;)Ljava/security/MessageDigest;

    move-result-object v0

    invoke-virtual {v0, p0}, Ljava/security/MessageDigest;->update([B)V

    invoke-virtual {v0, p1}, Ljava/security/MessageDigest;->update([B)V

    invoke-virtual {v0}, Ljava/security/MessageDigest;->digest()[B

    move-result-object v0

    return-object v0
.end method

.method public static exists()Z
    .locals 2

    new-instance v0, Ljava/io/File;

    const-string v1, "/data/system/oneos_pin"

    invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-virtual {v0}, Ljava/io/File;->exists()Z

    move-result v0

    return v0
.end method

.method public static clear()Z
    .locals 2

    new-instance v0, Ljava/io/File;

    const-string v1, "/data/system/oneos_pin"

    invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-virtual {v0}, Ljava/io/File;->delete()Z

    move-result v0

    if-nez v0, :oneos_pin_clear_ok

    invoke-static {}, Lcom/android/server/locksettings/OneOsPin;->exists()Z

    move-result v0

    if-nez v0, :oneos_pin_clear_ok

    const/4 v0, 0x0

    return v0

    :oneos_pin_clear_ok
    const/4 v0, 0x1

    return v0
.end method

.method public static store([B)Z
    .locals 7

    :try_start_0
    const/16 v0, 0x10

    new-array v1, v0, [B

    new-instance v2, Ljava/security/SecureRandom;

    invoke-direct {v2}, Ljava/security/SecureRandom;-><init>()V

    invoke-virtual {v2, v1}, Ljava/security/SecureRandom;->nextBytes([B)V

    invoke-static {v1, p0}, Lcom/android/server/locksettings/OneOsPin;->hash([B[B)[B

    move-result-object v3

    const/4 v4, 0x2

    invoke-static {v1, v4}, Landroid/util/Base64;->encodeToString([BI)Ljava/lang/String;

    move-result-object v1

    invoke-static {v3, v4}, Landroid/util/Base64;->encodeToString([BI)Ljava/lang/String;

    move-result-object v3

    new-instance v5, Ljava/lang/StringBuilder;

    invoke-direct {v5}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v5, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string v1, ":"

    invoke-virtual {v5, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v5, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v5}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    new-instance v3, Ljava/io/FileOutputStream;

    new-instance v5, Ljava/io/File;

    const-string v6, "/data/system/oneos_pin"

    invoke-direct {v5, v6}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-direct {v3, v5}, Ljava/io/FileOutputStream;-><init>(Ljava/io/File;)V

    invoke-virtual {v1}, Ljava/lang/String;->getBytes()[B

    move-result-object v1

    invoke-virtual {v3, v1}, Ljava/io/FileOutputStream;->write([B)V

    invoke-virtual {v3}, Ljava/io/FileOutputStream;->getFD()Ljava/io/FileDescriptor;

    move-result-object v1

    invoke-virtual {v1}, Ljava/io/FileDescriptor;->sync()V

    invoke-virtual {v3}, Ljava/io/FileOutputStream;->close()V
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    const/4 v0, 0x1

    return v0

    :catch_0
    const/4 v0, 0x0

    return v0
.end method

.method public static verify([B)Z
    .locals 8

    :try_start_0
    new-instance v0, Ljava/io/File;

    const-string v1, "/data/system/oneos_pin"

    invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-virtual {v0}, Ljava/io/File;->exists()Z

    move-result v1

    if-eqz v1, :catch_0

    new-instance v1, Ljava/io/BufferedReader;

    new-instance v2, Ljava/io/InputStreamReader;

    new-instance v3, Ljava/io/FileInputStream;

    invoke-direct {v3, v0}, Ljava/io/FileInputStream;-><init>(Ljava/io/File;)V

    invoke-direct {v2, v3}, Ljava/io/InputStreamReader;-><init>(Ljava/io/InputStream;)V

    invoke-direct {v1, v2}, Ljava/io/BufferedReader;-><init>(Ljava/io/Reader;)V

    invoke-virtual {v1}, Ljava/io/BufferedReader;->readLine()Ljava/lang/String;

    move-result-object v1

    const-string v2, ":"

    invoke-virtual {v1, v2}, Ljava/lang/String;->split(Ljava/lang/String;)[Ljava/lang/String;

    move-result-object v1

    array-length v2, v1

    const/4 v3, 0x2

    if-ne v2, v3, :catch_0

    const/4 v2, 0x0

    aget-object v2, v1, v2

    invoke-static {v2, v3}, Landroid/util/Base64;->decode(Ljava/lang/String;I)[B

    move-result-object v2

    const/4 v4, 0x1

    aget-object v1, v1, v4

    invoke-static {v1, v3}, Landroid/util/Base64;->decode(Ljava/lang/String;I)[B

    move-result-object v1

    invoke-static {v2, p0}, Lcom/android/server/locksettings/OneOsPin;->hash([B[B)[B

    move-result-object v2

    invoke-static {v2, v1}, Ljava/security/MessageDigest;->isEqual([B[B)Z

    move-result v1
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    return v1

    :catch_0
    const/4 v1, 0x0

    return v1
.end method
'''

LOCKSETTINGS = os.path.join(
    "com", "android", "server", "locksettings", "LockSettingsService.smali"
)

SET_ANCHOR = """.method private setLockCredentialInternal(Lcom/android/internal/widget/LockscreenCredential;Lcom/android/internal/widget/LockscreenCredential;IZ)Z
    .locals 10
    .param p1, "credential"    # Lcom/android/internal/widget/LockscreenCredential;
    .param p2, "savedCredential"    # Lcom/android/internal/widget/LockscreenCredential;
    .param p3, "userId"    # I
    .param p4, "isLockTiedToParent"    # Z
"""

VERIFY_ANCHOR = """.method private doVerifyCredential(Lcom/android/internal/widget/LockscreenCredential;ILcom/android/internal/widget/ICheckCredentialProgressCallback;I)Lcom/android/internal/widget/VerifyCredentialResponse;
    .locals 14
    .param p1, "credential"    # Lcom/android/internal/widget/LockscreenCredential;
    .param p2, "userId"    # I
    .param p3, "progressCallback"    # Lcom/android/internal/widget/ICheckCredentialProgressCallback;
    .param p4, "flags"    # I
"""

TYPE_ANCHOR = """.method private getCredentialTypeInternal(I)I
    .locals 3
    .param p1, "userId"    # I
"""

FRP_CALL = "    invoke-direct {v1}, Lcom/android/server/locksettings/LockSettingsService;->enforceFrpNotActive()V"

FRP_SKIP = """    # OneOS: the guest shares the phone's FRP partition; do not gate guest credentials on it
    nop"""


def replace_once(src, anchor, addition, name):
    if src.count(anchor) != 1:
        sys.exit(f"{name}: anchor found {src.count(anchor)} times")
    return src.replace(anchor, anchor + "\n" + addition, 1)


def replace_text_once(src, old, new, name):
    if src.count(old) != 1:
        sys.exit(f"{name}: text found {src.count(old)} times")
    return src.replace(old, new, 1)


def main(root):
    path = os.path.join(root, "smali_classes2", LOCKSETTINGS)
    if not os.path.isfile(path):
        sys.exit(f"{path}: not found")
    src = open(path).read()
    if "OneOsPin" in src:
        sys.exit(f"{path}: already patched")
    src = replace_once(src, SET_ANCHOR, PIN, "setLockCredentialInternal")
    src = replace_once(src, VERIFY_ANCHOR, VERIFY, "doVerifyCredential")
    src = replace_once(src, TYPE_ANCHOR, TYPE, "getCredentialTypeInternal")
    src = replace_text_once(src, FRP_CALL, FRP_SKIP, "enforceFrpNotActive call")
    open(path, "w").write(src)

    helper = os.path.join(root, "smali_classes2", "com", "android", "server",
                          "locksettings", "OneOsPin.smali")
    if os.path.exists(helper):
        sys.exit(f"{helper}: already exists")
    open(helper, "w").write(HELPER)
    print("smali_classes2")


if __name__ == "__main__":
    main(sys.argv[1])
