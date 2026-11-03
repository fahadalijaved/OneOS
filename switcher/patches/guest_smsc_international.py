"""Give the guest's SMS the service centre number as an international number.

Samsung's radio HAL answers getSmscAddress in the modem's AT form, for example
"972xxxxxxxx",145 (145: an international number, 129: unknown). One UI's
telephony reads that form; AOSP's does not: SMSDispatcher hands the string to
SmsMessage.getSubmitPdu, whose PhoneNumberUtils.extractNetworkPortion keeps
the digits up to the comma and drops the type, so every SMS the guest sends
names the service centre as an unknown-type number. Over IMS the network then
rejects it (0.4.38 report 381b2236, Partner IL: SIP 404 Called User Unknown on
sip:972...). IccSmsInterfaceManager.getSmscAddressFromIccEf (the one place the
dispatchers and SmsManager.getSmscAddress read it) now returns the number
alone, with a leading + when the type is 145. An answer without a comma
(another HAL's plain "+972...") is returned unchanged.

Usage: guest_smsc_international.py <smali root dir>
Prints the smali_* directories (dex files) it changed, one per line.
"""
import os
import re
import sys

CLASS = "com/android/internal/telephony/IccSmsInterfaceManager.smali"
HEADER = re.compile(r"^\.method public (?:\S+ )?getSmscAddressFromIccEf\(Ljava/lang/String;\)Ljava/lang/String;$")
HELPER = "oneosSmscAddress"

HELPER_SMALI = f"""
.method private static {HELPER}(Ljava/lang/String;)Ljava/lang/String;
    .locals 4

    # OneOS: the modem's AT form (number in quotes, comma, type) as a plain
    # number, + in front for type 145 (guest_smsc_international.py).
    if-eqz p0, :oneos_as_is

    const-string v0, ","

    invoke-virtual {{p0, v0}}, Ljava/lang/String;->lastIndexOf(Ljava/lang/String;)I

    move-result v0

    if-ltz v0, :oneos_as_is

    add-int/lit8 v1, v0, 0x1

    invoke-virtual {{p0, v1}}, Ljava/lang/String;->substring(I)Ljava/lang/String;

    move-result-object v1

    invoke-virtual {{v1}}, Ljava/lang/String;->trim()Ljava/lang/String;

    move-result-object v1

    const-string v2, "145"

    invoke-virtual {{v2, v1}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v2

    const/4 v3, 0x0

    invoke-virtual {{p0, v3, v0}}, Ljava/lang/String;->substring(II)Ljava/lang/String;

    move-result-object v1

    const-string v3, "\\""

    const-string v0, ""

    invoke-virtual {{v1, v3, v0}}, Ljava/lang/String;->replace(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Ljava/lang/String;

    move-result-object v1

    invoke-virtual {{v1}}, Ljava/lang/String;->trim()Ljava/lang/String;

    move-result-object v1

    invoke-virtual {{v1}}, Ljava/lang/String;->isEmpty()Z

    move-result v0

    if-nez v0, :oneos_as_is

    if-eqz v2, :oneos_plain

    const-string v3, "+"

    invoke-virtual {{v1, v3}}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z

    move-result v0

    if-nez v0, :oneos_plain

    invoke-virtual {{v3, v1}}, Ljava/lang/String;->concat(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v1

    :oneos_plain
    return-object v1

    :oneos_as_is
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
        if HELPER in text:
            sys.exit(f"{d}/{CLASS}: already patched")
        lines = text.split("\n")
        heads = [k for k, l in enumerate(lines) if HEADER.match(l)]
        if len(heads) != 1:
            sys.exit(f"{d}/{CLASS}: getSmscAddressFromIccEf found {len(heads)} times")
        i = heads[0]
        end = next(k for k in range(i, len(lines)) if lines[k] == ".end method")
        rets = [k for k in range(i, end) if re.match(r"\s*return-object (\w+)$", lines[k])]
        # The result return: check-cast <r>, Ljava/lang/String; then return-object <r>.
        hits = []
        for k in rets:
            r = lines[k].split()[-1]
            j = k - 1
            while lines[j].strip() == "" or lines[j].lstrip().startswith(".line"):
                j -= 1
            if lines[j].strip() == f"check-cast {r}, Ljava/lang/String;":
                hits.append((k, r))
        if len(hits) != 1:
            sys.exit(f"{d}/{CLASS}: expected one String result return, found {len(hits)}")
        k, r = hits[0]
        lines[k:k] = [
            f"    invoke-static {{{r}}}, Lcom/android/internal/telephony/IccSmsInterfaceManager;->{HELPER}(Ljava/lang/String;)Ljava/lang/String;",
            "",
            f"    move-result-object {r}",
            "",
        ]
        lines.append(HELPER_SMALI)
        open(path, "w").write("\n".join(lines))
        changed.add(d)
        print(f"{d}/{CLASS}: getSmscAddressFromIccEf returns the number, + for type 145", file=sys.stderr)
    if not changed:
        sys.exit("IccSmsInterfaceManager not found")
    for d in sorted(changed):
        print(d)


if __name__ == "__main__":
    main(sys.argv[1])
