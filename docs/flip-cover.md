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

## Cover rotation and touch

The cover panel is mounted at 90 degrees (One UI's display info reports it as
748x720, `installOrientation 1`), while the guest's SurfaceFlinger reports it
as 720x748 at rotation 0 and lays a phone UI out sideways. `oneos_switch.sh`
puts the cover's logical display at user rotation 1 (90 degrees). HyperOS
records `wm user-rotation` but only applies it when the display is also fixed
to the user rotation, so both are set:

    wm fixed-to-user-rotation -d <id> enabled
    wm user-rotation -d <id> lock 1

A lid event resets the rotation to 0, and the cover's display id changes with
every lid event, so a keeper in `oneos_switch.sh` watches the guest's device
state, finds the display whose size is the cover's (720x748 or 748x720) and
re-applies both after each change. It also re-asserts the user rotation if
HyperOS resets it after the lid event. The inner panel (1080x2640) is never
touched. `ONEOS_GUEST_COVER_ROTATION=off` disables the keeper.

The guest's InputReader still maps the panel's raw 720x748 axes, so a touch
lands 90 degrees clockwise from the finger while the UI is upright.
`oneos_touch_rotate` (`switcher/native/oneos_touch_rotate.c`) grabs
`sec_touchscreen2` (read-only otherwise: every event is passed through) and
makes a uinput touchscreen with the panel's name, so the guest's
`input-port-associations.xml` still selects the cover display. X/Y are turned
one quarter in the raw 0..4095 space; multitouch slots, tracking ids and
pressure are copied unchanged. The direction is read from
`data/oneos_touch_rotate_dir` on every `SYN_REPORT`: `cw` goes with user
rotation 1. `ONEOS_GUEST_COVER_TOUCH=0` disables it. An inset panel active
area can be stretched over the whole display with
`ONEOS_GUEST_COVER_CAL="xmin xmax ymin ymax"`; unset keeps the full raw range.

## Still open

- **Cover UI edges.** HyperOS's phone UI may leave the panel's extreme edges
  without content or touch targets; the remapper only aligns the axes. On the
  Z Flip7 FE the raw touch IC's active area read 350..3765 / 241..3847, and
  stretching it with `ONEOS_GUEST_COVER_CAL` did not make the UI edges respond,
  so this is a UI-layout question, not the input mapping.
- **Samsung Camera on the cover.** The Flip still takes `samcam_bar.tar` (the
  bar phone's set) plus the A-series resolution-lookup guards. The rear camera
  works after setting the camera preference `facing` to 0, but the app resets
  it to 1 on the next launch and opens camera 1 (front). The front HAL then
  never returns a frame (`Camera2-FrameProcessorBase: Connection timed out
  (-110)`, `[Cam1] ... no response for 55 s`) and can wedge the guest. The
  cover preview still needs a folded test with the rear camera; do not switch
  to the front camera until the HAL is fixed.
- **System UI.** The notification/control panel background and the wallpaper
  stay black in HyperOS. The guest's `/storage/emulated/0` FUSE mount read
  "Transport endpoint is not connected" while `mediaprovider` was still
  running; the wallpaper window stayed `isOnScreen=false mDrawState=4` and
  the launcher's blur pass logged "nothing to draw". MiWallpaper, the media
  provider and the storage mount are the first things to check.
- **Do not restart the guest `vold`.** On the Z Flip7 FE, `setprop ctl.restart
  vold` in the guest ended in `VolumeManager::shutdown()` and took the whole
  phone down (panic/reboot). A media-provider restart or a FUSE remount is the
  safer path; a boot-time check in the session scripts should catch the dead
  mount without touching vold.
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
5. `cover_rotation.log` and `touch_rotate.log`, and `dumpsys input` for both
   `sec_touchscreen2` devices (the panel and the virtual one). Touch the
   centre and each edge after a fold.
6. Whether the cover is lit, whether touch works there, and whether the guest
   switches back to the inner panel on unfold.

The first Flip session is the source of truth: this form is untested on a
phone until then.
