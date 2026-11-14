PRODUCT_PACKAGES += \
    android.hardware.biometrics.face-service.facehal \
    libfacehal_jni \
    libfacehal_payload_cxx_shared \
    libfacehal_payload_jni_stfaceunlock_api \
    libfacehal_payload_tensorflowlite \
    libfacehal_payload_tensorflowlite_gpu_delegate

PRODUCT_VENDOR_PROPERTIES += \
    persist.vendor.facehal.enabled=1
