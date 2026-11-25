package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

/**
 * Set up iOS 27 was a screen of its own until the redesign of 2026-11-25 (docs/oneios.md, "UI (2026-11-25)"): the
 * same five steps as iOS 27's page, a second time. Its steps, the download's and the import's bytes and Stop are now
 * the page's checklist ([OneiosActivity]); this name stays only so that what still opens it (an old back stack, a
 * notification posted by an older build) lands on the page.
 */
class OneiosSetupActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startActivity(OneiosActivity.intent(this).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP))
        finish()
    }

    companion object {
        fun intent(ctx: Context): Intent = OneiosActivity.intent(ctx)
    }
}
