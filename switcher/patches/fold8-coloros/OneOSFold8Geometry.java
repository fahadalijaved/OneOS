/** Fold8/Find N6 dimensions. Keep the selected grid and inner-screen defaults. */
public final class OneOSFold8Geometry {
    private static Class<?> overlayClass;
    private static Object transaction;

    private static void add(String name, String target, String[] resources, float[] cover, float[] inner) throws Exception {
        Object builder = Class.forName("android.content.om.FabricatedOverlay$Builder")
                .getConstructor(String.class, String.class, String.class)
                .newInstance("com.android.shell", name, target);
        Object overlay = builder.getClass().getMethod("build").invoke(builder);
        java.lang.reflect.Method dimension = overlayClass.getMethod("setResourceValue", String.class, float.class, int.class, String.class);
        for (int i = 0; i < resources.length; i++) {
            dimension.invoke(overlay, target + ":dimen/" + resources[i], cover[i], 1, null);
            dimension.invoke(overlay, target + ":dimen/" + resources[i], inner[i], 1, "sw600dp");
        }
        transaction.getClass().getMethod("registerFabricatedOverlay", overlayClass).invoke(transaction, overlay);
        Object identifier = overlayClass.getMethod("getIdentifier").invoke(overlay);
        transaction.getClass().getMethod("setEnabled", Class.forName("android.content.om.OverlayIdentifier"), boolean.class, int.class)
                .invoke(transaction, identifier, true, 0);
    }

    public static void main(String[] args) throws Exception {
        overlayClass = Class.forName("android.content.om.FabricatedOverlay");
        transaction = Class.forName("android.content.om.OverlayManagerTransaction$Builder").getConstructor().newInstance();
        add("OneOSCoverGridSpacing", "com.android.launcher",
                new String[]{"diffCellHeightWithCellWidth", "diffCellHeightWithCellWidth4x5"},
                new float[]{-8, 14}, new float[]{8, 30});
        add("OneOSCoverQSSpacing", "com.android.systemui",
                new String[]{"qs_panel_bottom_area_height", "qs_panel_gesture_zone_height"},
                new float[]{34, 14}, new float[]{36, 16});
        add("OneOSColorBar48", "android",
                new String[]{"status_bar_height_default", "status_bar_height_portrait", "status_bar_height_landscape"},
                new float[]{48, 48, 48}, new float[]{48, 48, 48});
        Object binder = Class.forName("android.os.ServiceManager").getMethod("getService", String.class).invoke(null, "overlay");
        Object service = Class.forName("android.content.om.IOverlayManager$Stub")
                .getMethod("asInterface", Class.forName("android.os.IBinder")).invoke(null, binder);
        Class.forName("android.content.om.IOverlayManager")
                .getMethod("commit", Class.forName("android.content.om.OverlayManagerTransaction"))
                .invoke(service, transaction.getClass().getMethod("build").invoke(transaction));
        System.out.println("Cover geometry overlays enabled; sw600dp values preserve inner-screen geometry.");
    }
}
