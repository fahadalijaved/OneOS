package com.fahadali.oneos.ui

import android.app.Activity
import android.os.CountDownTimer
import android.text.SpannableString
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import androidx.appcompat.app.AlertDialog
import com.fahadali.oneos.R

/**
 * Turning on "Switch with a screen lock set" (0.5.17, owner): a red warning first, and its button waits 5 seconds
 * before it can be pressed, so nobody turns it on by a reflex tap. Recent Samsung firmware blocks Download Mode
 * while a lock is set, so a session that goes wrong can leave a phone whose only way back is a factory reset.
 * [onAnswer] gets true only after "I understand the risk"; Cancel, Back and a tap outside give false.
 */
object LockRiskDialog {
    private const val WAIT_MS = 5_000L

    fun show(activity: Activity, onAnswer: (Boolean) -> Unit) {
        val red = activity.getColor(R.color.verdict_block)
        fun redText(id: Int) = SpannableString(activity.getString(id)).apply {
            setSpan(ForegroundColorSpan(red), 0, length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
        var answered = false
        val dialog = AlertDialog.Builder(activity)
            .setTitle(redText(R.string.lock_risk_title))
            .setMessage(redText(R.string.lock_risk_message))
            .setPositiveButton(activity.getString(R.string.lock_risk_accept_wait, (WAIT_MS / 1000).toInt())) { _, _ -> answered = true; onAnswer(true) }
            .setNegativeButton(android.R.string.cancel, null)
            .setOnDismissListener { if (!answered) onAnswer(false) }
            .create()
        var timer: CountDownTimer? = null
        dialog.setOnShowListener {
            val accept = dialog.getButton(AlertDialog.BUTTON_POSITIVE)
            accept.isEnabled = false
            accept.setTextColor(red)
            timer = object : CountDownTimer(WAIT_MS, 250) {
                override fun onTick(left: Long) {
                    accept.text = activity.getString(R.string.lock_risk_accept_wait, ((left + 999) / 1000).toInt())
                }
                override fun onFinish() {
                    accept.text = activity.getString(R.string.lock_risk_accept)
                    accept.isEnabled = true
                }
            }.start()
        }
        dialog.setOnCancelListener { timer?.cancel() }
        dialog.show()
    }
}
