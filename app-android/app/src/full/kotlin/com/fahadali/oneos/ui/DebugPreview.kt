package com.fahadali.oneos.ui

import android.content.Context
import com.fahadali.oneos.BuildConfig

/** Off by default, local to debug builds; this never changes any real setup or launch gate. */
internal object DebugPreview {
    private const val PREFS = "oneos_debug"
    private const val KEY = "setup_preview"
    fun enabled(context: Context): Boolean = BuildConfig.DEBUG && context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY, false)
    fun setEnabled(context: Context, enabled: Boolean) {
        if (BuildConfig.DEBUG) context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(KEY, enabled).apply()
    }
}
