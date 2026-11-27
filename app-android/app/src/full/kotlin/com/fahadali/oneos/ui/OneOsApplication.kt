package com.fahadali.oneos.ui

import com.fahadali.oneos.session.UpdateCheck

class OneOsApplication : android.app.Application() {
    override fun onCreate() {
        super.onCreate()
        androidx.appcompat.app.AppCompatDelegate.setDefaultNightMode(androidx.appcompat.app.AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM)
        UpdateCheck.run(this)
    }
}
