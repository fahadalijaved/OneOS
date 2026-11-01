package com.fahadali.oneos.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.WindowInsets
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import com.fahadali.oneos.R
import com.fahadali.oneos.core.device.FactProbe
import com.fahadali.oneos.core.model.RootKind
import com.fahadali.oneos.core.model.RootRules
import com.fahadali.oneos.core.root.RootProbe
import dev.oneuiproject.oneui.R as OuiIcons

/** Figma's welcome → prerequisites → before-you-start flow. It never relaxes the switching gates. */
class OnboardingActivity : AppCompatActivity() {
    private var hasResumed = false
    private var page = 0
    private var welcomeSpring: androidx.dynamicanimation.animation.SpringAnimation? = null
    private var welcomeFade: android.animation.ObjectAnimator? = null
    private val animationHandler = android.os.Handler(android.os.Looper.getMainLooper())
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        page = savedInstanceState?.getInt("page") ?: 0
        setContentView(R.layout.activity_onboarding)
        findViewById<View>(R.id.onboarding_root).setOnApplyWindowInsetsListener { v, insets ->
            val b = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            v.setPadding(b.left, b.top, b.right, b.bottom)
            insets
        }
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { if (page > 0) { page--; render(animate = true) } else finish() }
        })
        findViewById<Button>(R.id.onboarding_next).setOnClickListener {
            if (page < 2) { page++; render(animate = true) }
            else {
                BeforeYouStart.acknowledge(this)
                startActivity(Intent(this, LauncherActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP))
                finish()
            }
        }
        render()
    }
    override fun onResume() {
        super.onResume()
        if (page != 0 || hasResumed) render()
        hasResumed = true
    }
    override fun onStop() {
        findViewById<AnimatedTitleView>(R.id.onboarding_title).cancel()
        animationHandler.removeCallbacksAndMessages(null)
        welcomeSpring?.cancel(); welcomeFade?.cancel()
        super.onStop()
    }
    override fun onSaveInstanceState(outState: Bundle) { outState.putInt("page", page); super.onSaveInstanceState(outState) }
    private fun render(animate: Boolean = false) {
        val rows = findViewById<LinearLayout>(R.id.onboarding_rows)
        rows.removeAllViews()
        findViewById<View>(R.id.onboarding_icon).visibility = if (page == 0) View.VISIBLE else View.GONE
        val scroll = findViewById<ScrollView>(R.id.onboarding_card_scroll)
        scroll.visibility = if (page == 0) View.GONE else View.VISIBLE
        val width = (412 * resources.displayMetrics.density).toInt()
        scroll.layoutParams = (scroll.layoutParams as android.widget.FrameLayout.LayoutParams).apply {
            this.width = minOf(width, resources.displayMetrics.widthPixels - (48 * resources.displayMetrics.density).toInt())
        }
        findViewById<AnimatedTitleView>(R.id.onboarding_title).setTitle(getString(when(page) {
            0 -> R.string.onboarding_welcome
            1 -> R.string.onboarding_prerequisites
            else -> R.string.before_title
        }))
        findViewById<Button>(R.id.onboarding_next).setText(if (page == 0) R.string.onboarding_start else R.string.before_continue)
        animatePage(animate)
        if (page == 0) return
        rows.layoutParams = rows.layoutParams.apply { height = ((if (page == 1) 300 else 350) * resources.displayMetrics.density * resources.configuration.fontScale).toInt() }
        supportFragmentManager.beginTransaction().replace(R.id.onboarding_rows,
            OnboardingPreferenceFragment().apply { arguments = Bundle().apply { putInt("page", page) } }
        ).commitNow()
    }
    /** Reused from Twidget: per-letter title reveal, spring button entrance, and quiet step fades. */
    private fun animatePage(animate: Boolean) {
        val title = findViewById<AnimatedTitleView>(R.id.onboarding_title)
        val button = findViewById<Button>(R.id.onboarding_next)
        val overlay = findViewById<View>(R.id.onboarding_settle_overlay)
        animationHandler.removeCallbacksAndMessages(null)
        welcomeSpring?.cancel(); welcomeFade?.cancel()
        overlay.animate().cancel()
        if (page == 2) {
            if (animate) { overlay.alpha = 0f; overlay.animate().alpha(1f).setStartDelay(150).setDuration(1100).setInterpolator(android.view.animation.DecelerateInterpolator()).start() }
            else overlay.alpha = 1f
        } else overlay.alpha = 0f
        if (page == 0) {
            title.prepare()
            button.alpha = 0f; button.visibility = View.INVISIBLE
            title.onAnimationFinished = {
                animationHandler.postDelayed({
                    if (page != 0 || isFinishing || isDestroyed) return@postDelayed
                    val offset = findViewById<View>(R.id.onboarding_root).height * .08f
                    button.visibility = View.VISIBLE; button.translationY = offset
                    welcomeSpring = androidx.dynamicanimation.animation.SpringAnimation(button, androidx.dynamicanimation.animation.DynamicAnimation.TRANSLATION_Y, 0f).apply {
                        spring = androidx.dynamicanimation.animation.SpringForce(0f).apply { stiffness = 100f; dampingRatio = .65f }
                        setStartValue(offset); start()
                    }
                    welcomeFade = android.animation.ObjectAnimator.ofFloat(button, View.ALPHA, 0f, 1f).apply {
                        duration = 667; interpolator = android.view.animation.PathInterpolator(.17f, .17f, .83f, .83f); start()
                    }
                }, 180)
            }
            title.post { if (page == 0 && !isFinishing && !isDestroyed) title.play() }
        } else {
            title.finish(); title.onAnimationFinished = null
            button.visibility = View.VISIBLE; button.alpha = 1f; button.translationY = 0f
            if (animate) {
                val content = findViewById<View>(R.id.onboarding_card_scroll)
                content.alpha = 0f; content.translationY = 18 * resources.displayMetrics.density
                content.animate().alpha(1f).translationY(0f).setDuration(320).setInterpolator(android.view.animation.DecelerateInterpolator()).start()
                button.alpha = 0f; button.translationY = 12 * resources.displayMetrics.density
                button.animate().alpha(1f).translationY(0f).setStartDelay(60).setDuration(280).setInterpolator(android.view.animation.DecelerateInterpolator()).start()
            }
        }
    }

}
