# Fixed path environment for the private installd candidate

The captured ColorOS `init.environ.rc` exports three paths under `on early-init`.
The packaged OneOS 0.4.57 `zygote_exec` independently contains the same values
in its name/default table. The fixed initializer uses those source values for
the three selected Samsung installd globals reads.

| Variable | Value | ColorOS export line | OneOS table VA | Samsung getenv VA |
| --- | --- | ---: | --- | --- |
| `ANDROID_ROOT` | `/system` | 4 | `0x2db370` | `0x743d8` |
| `ANDROID_DATA` | `/data` | 6 | `0x2db380` | `0x743c4` |
| `ASEC_MOUNTPOINT` | `/mnt/asec` | 12 | `0x2db420` | `0x7496c` |

The OneOS launcher uses these values when the inherited values are missing or
empty. The actual guest runtime environment is unobserved. The held Samsung
`init.rc` imports `/init.environ.rc` at line 7 and creates `/mnt/asec` with mode
0755 and owner root:system at line 325. No `init.environ.rc` member appears in
the captured Samsung partition index, so the original Samsung export values
remain unproved. Original installd passes the ASEC getenv result directly to
`strlen` on the inspected path. See the [native launch profile](guest-native-launch-profile.md).

The new [C initializer](../compat/native/guest_installd_environment.h) supplies
three literal entries and the terminating null pointer for a future private
launcher. It takes no caller values and reads no process environment.

```c
char *const envp[] = ONEOS_GUEST_INSTALLD_PATH_ENVIRONMENT;
```

The real child still has to admit its Samsung code and interpreter objects at
`/system`, the held private data object at `/data`, and a source-owned guest
directory for `/mnt/asec`. The unchanged OneOS 0.4.58 preparer imports the host
`/mnt` hierarchy at line 1231. Applying the initializer to that mount profile
would leave ASEC ownership unresolved. The selected globals cover only these
three paths. The full pre-exec environment, credentials and capabilities, exec
context, loader cohort, and endpoint lifetime remain separate inputs.

`python -B tools/prepare_guest_installd_environment.py` rehashes six fixed
inputs, decodes the actual three ELF pointer pairs from file-backed load
segments, compares both captured source producers and checks the C initializer
bytes. The [inventory](../inventory/guest-installd-environment.json) records the
saved passing source check. The component remains unselected. This check did
not compile or run the initializer, launcher, OEM daemon or phone code.
