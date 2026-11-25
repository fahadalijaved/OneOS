package c5;

/**
 * Clean-room ABI-compatible shim for Tab S9 FE (One UI 9.0, SamsungCamera 17.0.00.89)'s
 * OneUiVersion enum (c5.m). Loaded via worker_wrapper_compat shared-library dependency
 * ahead of SamsungCamera.apk so ro.build.version.oneui=90500 (One UI 9.5) maps cleanly
 * to V9_0 instead of throwing IllegalArgumentException in CameraApplication.onCreate.
 */
public enum m {
    V1_0(-1, 100000, 280100),
    V1_1(-1, 100100, 280100),
    V1_2(-1, 100200, 280200),
    V1_5(-1, 100500, 280300),
    V2_0(-1, 110000, 290100),
    V2_1(-1, 110100, 290200),
    V2_5(-1, 110500, 290300),
    V3_0(-1, 120000, 300100),
    V3_1(-1, 120100, 300100),
    V3_1_1(30101, 120500, 300200),
    V4_0(40000, 130000, 310100),
    V4_1(40100, 130100, 310100),
    V4_1_1(40101, 130500, 320100),
    V5_0(50000, 140000, 330100),
    V5_1(50100, 140100, 330100),
    V5_1_1(50101, 140500, 330200),
    V6_0(60000, 150000, 340100),
    V6_1(60100, 150100, 340100),
    V6_1_1(60101, 150500, 340200),
    V7_0(70000, 160000, 350100),
    V7_1(70100, 160100, 350200),
    V8_0(80000, 170000, 360100),
    V8_5(80500, 170500, 360200),
    V9_0(90000, 180000, 370100);

    private final int mOneUiVersionCode;
    private final int mSeApiVersionCode;
    private final int mSepVersionCode;

    m(int oneUiVersionCode, int sepVersionCode, int seApiVersionCode) {
        this.mOneUiVersionCode = oneUiVersionCode;
        this.mSepVersionCode = sepVersionCode;
        this.mSeApiVersionCode = seApiVersionCode;
    }

    public static m a(int versionCode) {
        for (m v : values()) {
            if (versionCode != -1 && v.mOneUiVersionCode == versionCode) {
                return v;
            }
        }
        if (versionCode >= 90000) {
            return V9_0;
        }
        throw new IllegalArgumentException("get : argument is invalid - " + versionCode);
    }

    public final boolean b(m other) {
        return this.mOneUiVersionCode >= other.mOneUiVersionCode;
    }

    public final boolean c(m other) {
        return this.mOneUiVersionCode > other.mOneUiVersionCode;
    }
}
