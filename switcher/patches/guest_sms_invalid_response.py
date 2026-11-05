"""Count an SMS the modem sent as sent, although Samsung's radio HAL gives no result.

Samsung's radio HAL (libsec-ril, Qualcomm and Exynos) answers every guest
SEND_SMS without a SendSmsResult payload. Its response glue then does what
AOSP's ril_service makeSendSmsResult does: it logs "RILC: Invalid response:
NULL" and, when the RIL said RIL_E_SUCCESS, turns the answer into
RadioError.INVALID_RESPONSE (66). So every SMS the modem sent ("RILD: SMS
message send SUCCESS", "QmiWmsGetSmsResult: received: SUCCESS") reaches the
guest as "RILJ: < SEND_SMS error 66", SMSDispatcher.handleSendComplete marks it
failed (RESULT_RIL_INVALID_RESPONSE, 125), and the messaging app shows "not
sent" for a text the recipient got. Reports 2026-10-30..11-05: 49 guest
SEND_SMS answered 66 in 20 sessions (ColorOS, Infinity-X, Pixel, Nothing OS;
Snapdragon and Exynos), every one right after the modem's success ("RILD: SMS
message send SUCCESS" or "RILD: SendSMS Result: 0x0"), and not one SEND_SMS
in any report answered without an error. 0.4.40 report 190a9dcd (S25U, Partner IL):
the CS resend after Samsung IMS's fallback (status 4 on SIP 404); 0.4.31
report f68bef2a (A57): "SMS fails to send ondevice but interestingly the
recipient recieved". A failed send keeps its real error (49 NETWORK_ERR,
39 SYSTEM_ERR, 10 SMS_SEND_FAIL_RETRY): only 66 means "success without a payload".

MessagingResponse.responseSms (sendSms, sendSmsExpectMore, sendImsSms and the
CDMA variants all end there) now sets RadioResponseInfo.error from 66 to 0
before the request is processed, and logs it once per send (tag OneOS-SMS).
The guest then reports the SMS as sent with message reference 0 (no delivery
report match, as with any RIL that gives none).

Usage: guest_sms_invalid_response.py <smali root dir>
Prints the smali_* directories (dex files) it changed, one per line.
"""
import os
import re
import sys

CLASS = "com/android/internal/telephony/MessagingResponse.smali"
HEADER = re.compile(r"^\.method private (?:\S+ )?responseSms\(Landroid/hardware/radio/RadioResponseInfo;"
                    r"Landroid/hardware/radio/messaging/SendSmsResult;\)V$")
MARK = "oneos_sms_payload_ok"

PATCH = f"""
    # OneOS: Samsung's radio HAL answers SEND_SMS without a result payload, so a
    # sent SMS arrives as INVALID_RESPONSE (66); count it as sent
    # (guest_sms_invalid_response.py).
    iget v0, p1, Landroid/hardware/radio/RadioResponseInfo;->error:I

    const/16 v1, 0x42

    if-ne v0, v1, :{MARK}

    const/4 v0, 0x0

    iput v0, p1, Landroid/hardware/radio/RadioResponseInfo;->error:I

    const-string v0, "OneOS-SMS"

    const-string v1, "SEND_SMS error 66 (the radio sent it, no result payload): counted as sent"

    invoke-static {{v0, v1}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    :{MARK}
"""


def main(root):
    changed = set()
    for d in sorted(os.listdir(root)):
        path = os.path.join(root, d, CLASS)
        if not (d.startswith("smali") and os.path.isfile(path)):
            continue
        text = open(path).read()
        if MARK in text:
            sys.exit(f"{d}/{CLASS}: already patched")
        lines = text.split("\n")
        heads = [k for k, l in enumerate(lines) if HEADER.match(l)]
        if len(heads) != 1:
            sys.exit(f"{d}/{CLASS}: responseSms(RadioResponseInfo, SendSmsResult) found {len(heads)} times")
        i = heads[0]
        end = next(k for k in range(i, len(lines)) if lines[k] == ".end method")
        body = lines[i:end]
        # The method must read RadioResponseInfo.error (the check this patch
        # runs ahead of) and must not already write it.
        reads = [l for l in body if re.match(r"\s*iget \w+, p1, Landroid/hardware/radio/RadioResponseInfo;->error:I$", l)]
        if len(reads) != 1:
            sys.exit(f"{d}/{CLASS}: responseSms reads RadioResponseInfo.error {len(reads)} times, expected 1")
        if any("iput" in l and "RadioResponseInfo;->error:I" in l for l in body):
            sys.exit(f"{d}/{CLASS}: responseSms already writes RadioResponseInfo.error")
        locs = [k for k in range(i, end) if re.match(r"\s*\.locals (\d+)$", lines[k])]
        if len(locs) != 1:
            sys.exit(f"{d}/{CLASS}: responseSms has {len(locs)} .locals lines")
        k = locs[0]
        n = int(lines[k].split()[-1])
        if n < 2:
            # The block runs first, before the method sets any register; it needs two.
            lines[k] = "    .locals 2"
        lines[k + 1:k + 1] = PATCH.split("\n")
        open(path, "w").write("\n".join(lines))
        changed.add(d)
        print(f"{d}/{CLASS}: responseSms counts SEND_SMS error 66 as sent", file=sys.stderr)
    if not changed:
        sys.exit("MessagingResponse not found")
    for d in sorted(changed):
        print(d)


if __name__ == "__main__":
    main(sys.argv[1])
