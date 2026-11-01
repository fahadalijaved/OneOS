# Credits

OneOS is built on other people's work. This file lists it, with the terms it
comes under. OneOS's own code is licensed under the Apache License 2.0 (`LICENSE`, `NOTICE`).

## OneLineage, by WeWaffles

<https://github.com/WeWaffles/OneLineage>

The container hot-switch that OneOS is built on: staging a GSI on a rooted
Samsung phone, pivoting into it with its own zygote and system_server, and
handing the screen back to One UI. `switcher/` began as an unmodified copy of
OneLineage (`afa0fee`). OneOS's session scripts started from OneLineage's:

| OneOS | Started from (OneLineage) |
| --- | --- |
| `switcher/assets/guest_prepare.sh` | `master_prepare.sh` |
| `switcher/assets/guest_start.sh` | `master_inner.sh` |
| `switcher/assets/oneos_switch.sh` | `switch_to_lineage.sh` |
| `switcher/assets/return_to_oneui.sh` | `return_to_oneui.sh` |

`switcher/README.md` is OneLineage's own README, kept as its credit.
`switcher/assets/zygote_exec` is OneOS's build of `switcher/native/zygote_launcher.c`.
OneLineage's own Android app is not part of this repository.

OneLineage has no license file. WeWaffles gave written permission (2026-10-24)
to publish OneOS on top of OneLineage with full credit, here and in the app's
About screen. That permission covers this publication; it is not a license for
third parties to reuse the OneLineage-derived files.

## Galaxy Z Fold8 support, by Josh Skinner

<https://github.com/thatjoshguy67>, [pull request #1](https://github.com/fahadalijaved/OneOS/pull/1)
(Apache-2.0, as a contribution to this repository).

Josh brought OneOS to the Galaxy Z Fold8 (SM-F971B) and tested it there:
the `n6-f8` set and `scripts/make-fold8-coloros.py` (cover display, Quick
Settings, AOD, widgets, taskbar, Pocket Studio), the Google snapshot that became
`switcher/assets/guest_google.sh`, `switcher/assets/fold8_coloros.sh`, and the
hinge work: Samsung's folding-angle sensor relay
(`switcher/patches/fold8-coloros/OneOSAngleRelay.java`), the half-open device
state, the reveal and closing animations, and the Pixel side
(`switcher/assets/fold8_pixel.sh`, `switcher/patches/fold8-pixel/`,
`scripts/make-fold8-pixel.py`). The Z Fold8 Ultra uses his hinge relay, the
Pixel SystemUI adapter and the half-open state as well.

## MysticGSI

<https://github.com/MysticGSI/mysticgsi>, Apache License 2.0,
Copyright 2024-2026 The MysticGSI Authors (Romashka, hpdevfox).

OneOS's guest images are built with MysticGSI. MysticGSI and the way OneOS
drives it are not part of this repository; what is here is how OneOS patches a
built image (`scripts/make-overlays.sh`, `switcher/patches/`). MysticGSI
includes work from the TrebleDroid project by Pierre-Hugues Husson (phh) and
contributors (<https://github.com/TrebleDroid>), credited by MysticGSI's NOTICE.

## The app's libraries

Used by `app-android/` (versions in `app-android/gradle/libs.versions.toml`):

| Library | License | Copyright / source |
| --- | --- | --- |
| SESL: `io.github.oneuiproject.sesl` core, appcompat, material, recyclerview, preference (and indexscroll, picker-basic and others they bring) | MIT | Copyright (c) 2022 Yanndroid & BlackMesa123; <https://github.com/OneUIProject>. Based on AndroidX and Material Components for Android (Apache-2.0) |
| `io.github.oneuiproject:design` (oneui-design) | MIT | Copyright (c) 2022 Yanndroid & BlackMesa123 |
| `io.github.oneuiproject:icons` (oneui-icons, the `ic_oui_*` icons) | MIT | Copyright (c) 2022 Yanndroid & BlackMesa123 |
| `com.android.tools.smali:smali-dexlib2` | BSD 3-Clause | Google LLC and Ben Gruver; <https://github.com/google/smali> |
| AndroidX (activity, annotation, lifecycle, transition, cardview, loader, ...) | Apache-2.0 | The Android Open Source Project |
| Kotlin standard library | Apache-2.0 | JetBrains s.r.o. and Kotlin contributors |
| Guava, failureaccess | Apache-2.0 | The Guava Authors |
| ZXing core | Apache-2.0 | ZXing authors |
| JSR 305 annotations | Apache-2.0 | <https://github.com/findbugsproject/findbugs> |
| Gradle Wrapper (`gradle/wrapper/gradle-wrapper.jar`) | Apache-2.0 | Gradle Inc. |
| JUnit 4 (tests only, not shipped) | EPL-1.0 | JUnit team |

The MIT License of the OneUIProject libraries:

```
MIT License

Copyright (c) 2022 Yanndroid & BlackMesa123

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Works with (not bundled)

OneOS needs root on the phone and uses the root manager's own tools at run
time; none of them is in this repository or in the app:
[KernelSU](https://github.com/tiann/KernelSU) and KernelSU Next,
[Magisk](https://github.com/topjohnwu/Magisk) and
[APatch](https://github.com/bmax121/APatch) (all GPL-3.0).

## Trademarks and firmware

Not affiliated with Samsung, Google, OPPO or OnePlus. Galaxy and One UI are
trademarks of Samsung Electronics; Android and Pixel of Google LLC; ColorOS of
OPPO. No system images, vendor firmware or patched vendor files are in this
repository; `switcher/patches/host_installd.txt` and the probe fixtures under
`app-android/core/model/src/test/resources/` list interface facts (method
names, transaction codes, build properties) read from phones for
interoperability.
