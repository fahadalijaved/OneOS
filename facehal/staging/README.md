# Runtime libraries

`system_ext/lib64/facehal/` takes four Samsung libraries and the JNI shim the
HAL loads at runtime. They are vendor blobs, so git does not carry them; a
checkout has the directory empty.

| File | SHA-256 |
| --- | --- |
| `libc++_shared.so` | `95f1dd493ef287b4cf6befba91bc4f994235fffe768dd055bbb10c81854de694` |
| `libfacehal_jni.so` | `042cb2f414888fce962fc74ed00de97161837f6fa8e3e16511bf7df08df7c199` |
| `libjni_stfaceunlock_api.so` | `c1824b6ef157352f2ea117ade8319ba3e02f5d193f0047ad6f31e2948452d12b` |
| `libtensorflowlite_gpu_delegate.so` | `c516c7be3e6d42af942d8753ecc2a2be31215779f34b8b7e746ca6672b52fc9c` |
| `libtensorflowlite.so` | `ca085b6abfa19ee8c5d836efd1d93c180c101b450dbdb8d00064e154d790ad9b` |

Samsung's SM-S938B vendor image supplies the first four. `libfacehal_jni.so`
can also be built from `native/JniGraphicsShim.cpp`; the prebuilt matches the
shim deployed in `staging/`.

The session copies this directory to `data/local/tmp/facehal` in guest data,
where `guest_start.sh` starts `bin/hw/android.hardware.biometrics.face-service.facehal`
with `LD_LIBRARY_PATH` and `FACEHAL_ALGORITHM_LIBRARY` pointing at it.
