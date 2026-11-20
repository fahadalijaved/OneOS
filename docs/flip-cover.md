# The Galaxy Z Flip's cover screen

The Flip is a foldable with two panels, but its cover is a small phone-sized
screen, not a Fold's second large panel. OneOS gives it a form of its own
(`ONEOS_GUEST_FORM=flip`) instead of the bar phone's settings; the form is
written by `SessionEnv` and checked by `oneos_root.sh`.

## What the form turns on

| Session setting | Flip value | Why |
| --- | --- | --- |
| `ONEOS_GUEST_FORM` | `flip` | The scripts know it is a foldable. |
| `ONEOS_GUEST_FOLD` | `layout` | `guest_start.sh` writes the two-panel display layout. |
| `ONEOS_COVER_TSP` | `1` | The cover's touch IC is switched on with the lid. |
| `ONEOS_GUEST_FOLD_CONTINUE` | `1` | A fold does not lock the guest on the cover. |
| `ONEOS_GUEST_UNFOLD_PORTRAIT` | `1` | The inner panel is portrait (ColorOS's back-gesture feature). |
| `ONEOS_GUEST_COMPACT_WINDOW` | `0` | A Flip's inner panel is a plain phone. |
| `ONEOS_GUEST_WALLPAPER_GRID` | `0` | The Cover is not a Fold's inner screen; no 8x2 grid. |

`oneos_switch.sh` keeps `GUEST_FOLD_FORM=0` for a Flip: the fold line and the
inner-panel density path are for a book fold (a vertical hinge). A Flip's
hinge is horizontal, and its inner panel is a normal phone panel; the cover
gets its own density in `guest_prepare.sh`.

## Panels, ports and density

`oneos_switch.sh` records the smaller default-capable internal panel in
`host_cover_display` as `<uniqueId> <port> <width> <height> <xdpi>`, for a Flip
as well as a Fold. `guest_prepare.sh`:

- writes the cover's `forcedDensity` into the guest's `display_settings.xml`
  (`ONEOS_GUEST_COVER_DENSITY=off|auto|<dpi>`, default auto);
- leaves the two panel ports in the staged `/data` (`oneos_cover_port`,
  `oneos_inner_port`) for `guest_start.sh`. A Flip's vendor
  `input-port-associations.xml` does not have to name `sec_touchscreen2`; the
  host's own display dump is the fallback. The Fold's 147/148 is the last
  fallback only.

`guest_start.sh` hides One UI's display layout, reads the guest
SurfaceFlinger's display ids for those ports and writes a layout that puts
Samsung's device state 0 (lid closed) on the cover and the other states on the
inner panel. It also keeps the lit panel's backlight on while the boot
animation runs, and `guest_props.sh` puts the animation on the cover when the
phone starts folded.

## HyperOS 4 Global

HyperOS's DeviceStateProviderImpl reads its own
`device_state_configuration.xml`, whose states wait for Xiaomi's hinge sensor
(`xiaomi.sensor.fold_status`). A Galaxy has no such sensor. On a Fold and now
on a Flip, `guest_prepare.sh` binds a copy whose 0 (CLOSED) and 3 (OPENED)
states use Samsung's lid switch; the other Xiaomi states stay request-only.
`guest_start.sh` writes the matching display layout.

## Still open

- **Cover orientation.** The cover panel's rotation is not read yet. A Flip
  started folded may lay the guest out sideways until the panel's rotation is
  applied.
- **Samsung Camera on the cover.** The Flip still takes `samcam_bar.tar` (the
  bar phone's set) until a Flip set is built from the phone; camera start and
  the cover preview need a session log.
- **Cover UI.** HyperOS's own cover UI is made for Xiaomi's fold; the guest
  currently gets its phone UI at the cover's density. Widgets, AOD and a
  FlexWindow-like layer are a later compatibility app, not part of this form.

## What a test should record

1. `adb shell dumpsys SurfaceFlinger --display-id` (the two ports and ids).
2. `adb shell cmd device_state print-state` and `dumpsys device_state` with
   the phone open and closed.
3. `adb shell dumpsys display` (the cover's size, density and rotation).
4. `/data/local/tmp/oneos/diag_display/display.txt`, `diag_displays.txt` and
   the session's `all.log` around the fold and the camera start.
5. Whether the cover is lit, whether touch works there, and whether the guest
   switches back to the inner panel on unfold.

The first Flip session is the source of truth: this form is untested on a
phone until then.
