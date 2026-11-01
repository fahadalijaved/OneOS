package com.oneos.camera;

import android.hardware.camera2.CameraDevice;
import android.os.IBinder;
import android.os.Parcel;
import android.util.Log;
import java.lang.reflect.Field;

/**
 * CameraDevice.setParameters(String) for One UI's camera in a guest whose
 * framework has no such method (scamera_sdk_util.jar's setSamsungParameter
 * calls it). On One UI it is one call on the device's binder, transaction 13
 * of android.hardware.camera2.ICameraDeviceUser with the string, answered by
 * One UI's cameraserver, which the guest shares. Without it the camera's
 * Samsung parameters never reached the HAL and configuring its streams
 * failed (Nothing OS run 15: "Camera 20: Error configuring streams: Function
 * not implemented (-38)").
 *
 * Loaded from /system/framework, so the framework's own fields are open to it:
 * CameraDeviceImpl.mRemoteDevice (ICameraDeviceUserWrapper) and its
 * mRemoteDevice (ICameraDeviceUser).
 */
public final class SamsungParams {
    private static final String TAG = "OneOSCamera";
    private static final String DESCRIPTOR = "android.hardware.camera2.ICameraDeviceUser";
    private static final int TRANSACTION_SET_PARAMETERS = 13;

    private SamsungParams() {}

    public static void set(CameraDevice device, String parameters) {
        if (device == null) return;
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            Object wrapper = field(device, "mRemoteDevice");
            Object user = field(wrapper, "mRemoteDevice");
            IBinder binder = (IBinder) user.getClass().getMethod("asBinder").invoke(user);
            data.writeInterfaceToken(DESCRIPTOR);
            data.writeString(parameters);
            binder.transact(TRANSACTION_SET_PARAMETERS, data, reply, 0);
            reply.readException();
        } catch (Throwable t) {
            Log.e(TAG, "setSamsungParameter failed", t);
        } finally {
            data.recycle();
            reply.recycle();
        }
    }

    private static Object field(Object o, String name) throws ReflectiveOperationException {
        if (o == null) throw new NoSuchFieldException(name + " of null");
        for (Class<?> c = o.getClass(); c != null; c = c.getSuperclass()) {
            try {
                Field f = c.getDeclaredField(name);
                f.setAccessible(true);
                return f.get(o);
            } catch (NoSuchFieldException e) {
                // the superclass then
            }
        }
        throw new NoSuchFieldException(name + " in " + o.getClass().getName());
    }
}
