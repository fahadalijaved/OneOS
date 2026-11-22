"""ColorOS raise to wake on a Galaxy (0.5.32): OplusGestureUI.apk's ScreenOffGestureService through OneOSLift.

ScreenOffGestureService wakes the screen for a tilt detector event whose value is 0, OPPO's lift; a Galaxy's Tilt
Detector sends 1.0 for every tilt, which the service takes for "put down", so raise to wake never woke the screen
(S24 FE, ColorOS X9U IN, report 44afc238). Three changes, each found by the log strings around it (the class and
member names are obfuscated and differ between builds):

1. the method logging "registerTiltSensor + sensorType = ": its SensorManager.registerListener call goes through
   OneOSLift.register, which arms the phone's pick-up gesture sensor instead where it can;
2. the method logging "unRegisterTiltSensor": its SensorManager.unregisterListener call through
   OneOSLift.unregister;
3. the listener logging "onSensorChanged value = ": the value it compares with 0 (the lift) is
   OneOSLift.value(event), 0 for another maker's tilt event.

OneOSLift.smali goes into the dex of ScreenOffGestureService. Any change not found: nothing is changed, an error,
exit 1 (make-overlays.sh then builds no patched APK).

Usage: coloros_lift_wake.py <smali root dir of OplusGestureUI.apk> [<OneOSLift.smali>]
Prints the smali_* directories (dex files) it changed, one per line.
"""
import os
import re
import shutil
import sys

HELPER = "Lcom/oplus/gesture/server/OneOSLift;"
MARK = "# OneOS: raise to wake on a Galaxy (OneOSLift)"
REGISTER = re.compile(r"^(\s*)invoke-virtual \{([vp]\d+), ([vp]\d+), ([vp]\d+), ([vp]\d+)\}, "
                      r"Landroid/hardware/SensorManager;->registerListener\(Landroid/hardware/SensorEventListener;"
                      r"Landroid/hardware/Sensor;I\)Z$", re.M)
UNREGISTER = re.compile(r"^(\s*)invoke-virtual \{([vp]\d+), ([vp]\d+)\}, "
                        r"Landroid/hardware/SensorManager;->unregisterListener\(Landroid/hardware/SensorEventListener;\)V$",
                        re.M)
# iget-object vA, vE, SensorEvent;->values ; aget vA, vA, vI ; const/4 vZ, 0x0 ; Float.compare(vA, vZ)
VALUE = re.compile(r"^(\s*)iget-object ([vp]\d+), ([vp]\d+), Landroid/hardware/SensorEvent;->values:\[F\n(?:\s*\n)*"
                   r"\s*aget \2, \2, [vp]\d+\n((?:\s*\n)*\s*const/4 ([vp]\d+), 0x0\n(?:\s*\n)*"
                   r"\s*invoke-static \{\2, \5\}, Ljava/lang/Float;->compare\(FF\)I\n)", re.M)


def methods(text):
    """(start, end) of each method body in a smali file."""
    return [(m.start(), m.end()) for m in re.finditer(r"^\.method .*?^\.end method\n", text, re.M | re.S)]


def in_method(text, needle, pattern, repl, what):
    """Applies pattern -> repl once inside the one method containing needle; returns the new text."""
    hits = [(a, b) for a, b in methods(text) if needle in text[a:b]]
    if len(hits) != 1:
        raise ValueError(f"{what}: {len(hits)} methods log {needle!r}")
    a, b = hits[0]
    body, n = pattern.subn(repl, text[a:b])
    if n != 1:
        raise ValueError(f"{what}: {n} calls in the method")
    return text[:a] + body + text[b:]


def main(root, helper):
    service = listener = None
    for d, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith(".smali"):
                continue
            p = os.path.join(d, f)
            s = open(p, encoding="utf-8").read()
            if '"registerTiltSensor + sensorType = "' in s and '"unRegisterTiltSensor"' in s:
                if service:
                    raise ValueError(f"two classes register the tilt sensor: {service}, {p}")
                service = (p, s)
            if '"onSensorChanged value = "' in s and '"tilt sensor report unknown value = "' in s:
                if listener:
                    raise ValueError(f"two tilt listeners: {listener}, {p}")
                listener = (p, s)
    if not service or not listener:
        raise ValueError("ScreenOffGestureService's tilt sensor code not found")
    if MARK in service[1] or MARK in listener[1]:
        raise ValueError("already patched")

    s = service[1]
    s = in_method(s, '"registerTiltSensor + sensorType = "', REGISTER,
                  lambda m: f"{m.group(1)}{MARK}\n{m.group(1)}invoke-static {{{m.group(2)}, {m.group(3)}, {m.group(4)}, {m.group(5)}}}, "
                            f"{HELPER}->register(Landroid/hardware/SensorManager;Landroid/hardware/SensorEventListener;"
                            f"Landroid/hardware/Sensor;I)Z", "register")
    s = in_method(s, '"unRegisterTiltSensor"', UNREGISTER,
                  lambda m: f"{m.group(1)}invoke-static {{{m.group(2)}, {m.group(3)}}}, "
                            f"{HELPER}->unregister(Landroid/hardware/SensorManager;Landroid/hardware/SensorEventListener;)V",
                  "unregister")
    lp, ls = listener
    if lp == service[0]:
        ls = s
    ls = in_method(ls, '"onSensorChanged value = "', VALUE,
                   lambda m: f"{m.group(1)}{MARK}\n{m.group(1)}invoke-static/range {{{m.group(3)} .. {m.group(3)}}}, "
                             f"{HELPER}->value(Landroid/hardware/SensorEvent;)F\n\n{m.group(1)}move-result {m.group(2)}\n{m.group(4)}",
                   "lift value")
    if lp == service[0]:
        s = ls
    else:
        open(lp, "w", encoding="utf-8").write(ls)
    open(service[0], "w", encoding="utf-8").write(s)

    rel = lambda p: os.path.relpath(p, root).split(os.sep)[0]
    hdir = rel(service[0])
    dest = os.path.join(root, hdir, "com", "oplus", "gesture", "server")
    os.makedirs(dest, exist_ok=True)
    shutil.copy(helper, os.path.join(dest, "OneOSLift.smali"))
    print("raise to wake: tilt sensor through OneOSLift (register, unregister, lift value)", file=sys.stderr)
    for c in sorted({hdir, rel(lp)}):
        print(c)


if __name__ == "__main__":
    try:
        main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else
             os.path.join(os.path.dirname(os.path.abspath(__file__)), "OneOSLift.smali"))
    except ValueError as e:
        print(f"coloros_lift_wake: {e}; nothing changed", file=sys.stderr)
        sys.exit(1)
