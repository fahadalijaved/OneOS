package com.oplus.settings.feature.fingerprint;

import android.os.Looper;
import androidx.lifecycle.Lifecycle;
import com.appleexploit.oneos.security.transport.FingerprintEnrollmentPreferenceBindCapture;
import com.appleexploit.oneos.security.transport.FingerprintEnrollmentPreferenceFeed.Listener;
import com.appleexploit.oneos.security.transport.FingerprintEnrollmentPreferenceFeedBinding;
import com.appleexploit.oneos.security.transport.FingerprintEnrollmentPreferenceReportOwner.SubjectSource;
import com.oplus.settings.feature.fingerprint.OplusFingerprintSettings.FingerprintSettingsFragment;

/** Prepares a passive display binding for the exact created Settings fragment. */
public final class OneOsFingerprintDisplaySource {
    private OneOsFingerprintDisplaySource() {}

    /** Retain the returned binding before start and close it when the fragment or subject retires. */
    public static FingerprintEnrollmentPreferenceFeedBinding prepare(FingerprintSettingsFragment fragment,
            SubjectSource source, Object subject, Listener listener, CharSequence title,
            CharSequence unavailable, CharSequence reportedEmpty) {
        Looper main = Looper.getMainLooper();
        if (main == null || Looper.myLooper() != main || fragment == null
                || fragment.getClass() != FingerprintSettingsFragment.class
                || source == null || subject == null || listener == null) return null;
        if (!fragment.getLifecycle().getCurrentState().isAtLeast(Lifecycle.State.CREATED)) return null;

        FingerprintEnrollmentPreferenceBindCapture capture = fragment.oneos$getPreferenceBind();
        if (capture == null || !capture.isForFragment(fragment)) return null;
        return new FingerprintEnrollmentPreferenceFeedBinding(
                capture, source, subject, listener, title, unavailable, reportedEmpty);
    }
}
