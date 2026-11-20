/**
 * OneOS (0.5.17): one key=value pair to AudioFlinger through the guest's own AudioSystem.setParameters, so the
 * binder call number is always this build's. guest_start.sh sent `service call media.audio_flinger 18`, which is
 * setParameters only in some builds (OxygenOS 16 on the A17: 20; a tester's module found it): there the Bluetooth
 * stream recovery and the call SIM slot did nothing. Run in the guest: app_process ... OneOSAudioParam "key=value".
 * Exits non-zero when the call could not be made, so the script can fall back.
 */
public final class OneOSAudioParam {
    public static void main(String[] args) throws Exception {
        if (args.length != 1 || !args[0].matches("[A-Za-z0-9_.]{1,64}=[A-Za-z0-9_.,-]{0,64}")) {
            System.out.println("usage: OneOSAudioParam key=value");
            System.exit(2);
        }
        Class<?> as = Class.forName("android.media.AudioSystem");
        int r = (Integer) as.getMethod("setParameters", String.class).invoke(null, args[0]);
        System.out.println("AudioSystem.setParameters " + args[0] + ": " + r);
        System.exit(r == 0 ? 0 : 1);
    }
}
