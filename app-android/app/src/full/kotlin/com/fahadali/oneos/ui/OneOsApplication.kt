package com.fahadali.oneos.ui

class OneOsApplication : android.app.Application() {
    init {
        // Tester builds (-Poneos.a17OnA16=true) only. Here, in the constructor, because the findings provider is
        // created before onCreate and Profiles.BUILT_IN is built from the flag the first time anything reads it.
        com.fahadali.oneos.core.model.Experimental.a17OnA16 = com.fahadali.oneos.BuildConfig.A17_ON_A16
        com.fahadali.oneos.core.model.Experimental.colorOsOnA16 = com.fahadali.oneos.BuildConfig.COLOROS_ON_A16
    }

    override fun onCreate() {
        super.onCreate()
        androidx.appcompat.app.AppCompatDelegate.setDefaultNightMode(androidx.appcompat.app.AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM)
    }
}
