"""Send the guest's SMS to the number the network can route.

ColorOS's Google Messages keeps two forms of a recipient: the display form
and the string it hands SmsManager. On the 0.4.59 guest (S25U, Partner IL) the
send form kept a stray character and the national trunk 0 after the country
code: the provider rows and the app's participant say "ז+9720501234567" (and
"9720541234567" for the other test), while the canonical address and One UI's
own row for the same contact say "+972501234567". SmsDispatchersController
puts that string in the PDU and in the IMS MESSAGE URI unchanged, so Partner
IL's IMS answers SIP 404 "Called User Unknown" (the same 404 One UI gets; One
UI then falls back to CS and the network accepts its clean number) and the CS
fallback sends a number the network does not know. The guest still reports
the text as sent: the radio sent the PDU, and 0.4.58's
guest_sms_invalid_response.py counts Samsung's empty SEND_SMS answer as sent.

SmsDispatchersController$PendingRequest (the object every text, multipart and
data send is built from) now normalizes its destAddr. The string is reduced to
its dialable portion, then rewritten as E.164 in the network's country (then
the SIM's, then the locale's). A valid national number is formatted directly.
An international number that still carries the national trunk 0 after the
country code is retried with that 0 removed, which is the form Partner IL
routes: "ז+9720501234567" -> "+972501234567", "9720541234567" ->
"+972541234567". A number that is already valid is never changed (Italy keeps
its leading 0). Short codes, emergency numbers, MMI/USSD strings (*, #) and
anything PhoneNumberUtils cannot parse are left exactly as the app sent them.

Usage: guest_sms_destination.py <smali root dir>
Prints the smali_* directories (dex files) it changed, one per line.
"""
import os
import re
import sys

CLASS = "com/android/internal/telephony/SmsDispatchersController$PendingRequest.smali"
MARK = "oneosNormalizeSmsDestination"
ANCHOR = re.compile(
    r"\s*iput-object p5, p0, "
    r"Lcom/android/internal/telephony/SmsDispatchersController\$PendingRequest;->"
    r"destAddr:Ljava/lang/String;$"
)

CALL = f"""
    # OneOS: the app can hand us a destination the network cannot route; send
    # the E.164 form instead (guest_sms_destination.py).
    invoke-static {{p5}}, Lcom/android/internal/telephony/SmsDispatchersController$PendingRequest;->{MARK}(Ljava/lang/String;)Ljava/lang/String;

    move-result-object p5
"""

HELPER_SMALI = f"""
.method public static blacklist {MARK}(Ljava/lang/String;)Ljava/lang/String;
    .locals 8

    if-eqz p0, :oneos_dest_as_is

    # MMI/USSD and anything with * or # is not a phone number to rewrite.
    const/16 v0, 0x2a

    invoke-virtual {{p0, v0}}, Ljava/lang/String;->indexOf(I)I
    move-result v0

    if-ltz v0, :oneos_dest_as_is

    const/16 v0, 0x23

    invoke-virtual {{p0, v0}}, Ljava/lang/String;->indexOf(I)I
    move-result v0

    if-ltz v0, :oneos_dest_as_is

    invoke-static {{p0}}, Landroid/telephony/PhoneNumberUtils;->extractNetworkPortion(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v0

    if-eqz v0, :oneos_dest_as_is

    invoke-virtual {{v0}}, Ljava/lang/String;->isEmpty()Z
    move-result v1

    if-nez v1, :oneos_dest_as_is

    # Region for national numbers: the network's country, then the SIM's,
    # then the system locale's.
    invoke-static {{}}, Landroid/telephony/TelephonyManager;->getDefault()Landroid/telephony/TelephonyManager;
    move-result-object v1

    invoke-virtual {{v1}}, Landroid/telephony/TelephonyManager;->getNetworkCountryIso()Ljava/lang/String;
    move-result-object v1

    if-eqz v1, :oneos_dest_sim_country

    invoke-virtual {{v1}}, Ljava/lang/String;->isEmpty()Z
    move-result v2

    if-eqz v2, :oneos_dest_sim_country

    goto :oneos_dest_region

    :oneos_dest_sim_country
    invoke-static {{}}, Landroid/telephony/TelephonyManager;->getDefault()Landroid/telephony/TelephonyManager;
    move-result-object v1

    invoke-virtual {{v1}}, Landroid/telephony/TelephonyManager;->getSimCountryIso()Ljava/lang/String;
    move-result-object v1

    if-eqz v1, :oneos_dest_locale_country

    invoke-virtual {{v1}}, Ljava/lang/String;->isEmpty()Z
    move-result v2

    if-eqz v2, :oneos_dest_locale_country

    goto :oneos_dest_region

    :oneos_dest_locale_country
    invoke-static {{}}, Ljava/util/Locale;->getDefault()Ljava/util/Locale;
    move-result-object v1

    invoke-virtual {{v1}}, Ljava/util/Locale;->getCountry()Ljava/lang/String;
    move-result-object v1

    :oneos_dest_region
    invoke-static {{v0, v1}}, Landroid/telephony/PhoneNumberUtils;->formatNumberToE164(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    move-result-object v2

    if-eqz v2, :oneos_dest_try_plus

    goto :oneos_dest_done

    :oneos_dest_try_plus
    # "9720541234567": the international form without the plus.
    const/4 v3, 0x0

    invoke-virtual {{v0, v3}}, Ljava/lang/String;->charAt(I)C
    move-result v3

    const/16 v4, 0x2b

    if-ne v3, v4, :oneos_dest_drop_zero

    new-instance v3, Ljava/lang/StringBuilder;

    const-string v4, "+"

    invoke-direct {{v3, v4}}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {{v3, v0}}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {{v3}}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0

    invoke-static {{v0, v1}}, Landroid/telephony/PhoneNumberUtils;->formatNumberToE164(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    move-result-object v2

    if-eqz v2, :oneos_dest_drop_zero

    goto :oneos_dest_done

    :oneos_dest_drop_zero
    # The national trunk 0 after the country code: "+9720501234567".
    # Country codes are one to three digits, so the 0 can only sit at 2..4.
    const/4 v3, 0x2

    :oneos_dest_zero_loop
    const/4 v4, 0x5

    if-ge v3, v4, :oneos_dest_zero_len

    goto :oneos_dest_done

    :oneos_dest_zero_len
    invoke-virtual {{v0}}, Ljava/lang/String;->length()I
    move-result v4

    if-ge v3, v4, :oneos_dest_zero_try

    goto :oneos_dest_done

    :oneos_dest_zero_try
    invoke-virtual {{v0, v3}}, Ljava/lang/String;->charAt(I)C
    move-result v4

    const/16 v5, 0x30

    if-ne v4, v5, :oneos_dest_zero_next

    new-instance v4, Ljava/lang/StringBuilder;

    invoke-direct {{v4, v0}}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {{v4, v3}}, Ljava/lang/StringBuilder;->deleteCharAt(I)Ljava/lang/StringBuilder;

    invoke-virtual {{v4}}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v4

    invoke-static {{v4, v1}}, Landroid/telephony/PhoneNumberUtils;->formatNumberToE164(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    move-result-object v2

    if-nez v2, :oneos_dest_zero_next

    goto :oneos_dest_done

    :oneos_dest_zero_next
    add-int/lit8 v3, v3, 0x1

    goto :oneos_dest_zero_loop

    :oneos_dest_done
    if-eqz v2, :oneos_dest_left_as_is

    invoke-virtual {{v2, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v3

    if-nez v3, :oneos_dest_return

    const-string v3, "OneOS-SMS"

    new-instance v4, Ljava/lang/StringBuilder;

    const-string v5, "SMS destination normalized: "

    invoke-direct {{v4, v5}}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {{v4, p0}}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string v5, " -> "

    invoke-virtual {{v4, v5}}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {{v4, v2}}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {{v4}}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v4

    invoke-static {{v3, v4}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    :oneos_dest_return
    return-object v2

    :oneos_dest_left_as_is
    const-string v3, "OneOS-SMS"

    new-instance v4, Ljava/lang/StringBuilder;

    const-string v5, "SMS destination left as is: "

    invoke-direct {{v4, v5}}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {{v4, p0}}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {{v4}}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v4

    invoke-static {{v3, v4}}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    :oneos_dest_as_is
    return-object p0
.end method
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
        heads = [k for k, l in enumerate(lines) if ANCHOR.match(l)]
        if len(heads) != 1:
            sys.exit(f"{d}/{CLASS}: destAddr assignment found {len(heads)} times, expected 1")
        k = heads[0]
        lines[k:k] = CALL.split("\n")
        lines.append(HELPER_SMALI)
        open(path, "w").write("\n".join(lines))
        changed.add(d)
        print(f"{d}/{CLASS}: PendingRequest destAddr normalized to E.164", file=sys.stderr)
    if not changed:
        sys.exit("SmsDispatchersController$PendingRequest not found")
    for d in sorted(changed):
        print(d)


if __name__ == "__main__":
    main(sys.argv[1])
