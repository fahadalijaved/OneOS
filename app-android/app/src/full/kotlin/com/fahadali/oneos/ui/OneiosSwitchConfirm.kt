package com.fahadali.oneos.ui

import android.content.res.ColorStateList
import android.view.LayoutInflater
import android.view.View
import android.widget.Button
import android.widget.CheckBox
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.annotation.DrawableRes
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosSystem
import com.fahadali.oneos.session.OneiosJob

/**
 * Switch to iOS 27? (docs/oneios.md, "In the app"): the Android systems' Switch confirm
 * (dialog_switch, home_way_tile, home_switch_ack), with the ways back of an iOS session as its tiles
 * (OneiOS's oneos/interface.md, section 6, and docs/oneios.md, "Getting back to One UI"): Volume Up +
 * Volume Down for 3 s, the same keys while iOS is still starting (a return asked during the switch
 * wins), One UI coming back by itself when iOS never shows, and Power + Volume Down. Three boxes:
 * "I have read how to get back" and the experimental tick (root's `switch` gets it, as before) every
 * time, and on a phone that is not the Galaxy S24 Ultra the device warning (the owner, 2026-11-16:
 * another phone may try it, told what to expect). Switch is on only with all. On a phone whose profile offers it
 * ([OneiosJob.takeoverOffered]: the Galaxy S24 Ultra, the Galaxy S26 Ultra) one more box, unticked every time and not
 * needed for Switch: the Android takeover's toggle with its warning ([OneiosSystem.TAKEOVER_WARNING]; docs/oneios.md,
 * "Android takeover"). Then [OneiosJob.switch]:
 * the same root verbs and preflight as before; a refusal comes back in plain words on the switching screen.
 */
internal object OneiosSwitchConfirm {
    fun show(a: AppCompatActivity) {
        val s = OneiosJob.state
        if (s.busy) return
        if (!s.flow.ready) {
            // Root's last check no longer passes (the page shows why): check again instead of asking.
            OneiosJob.refresh(a)
            return
        }
        val inflater = LayoutInflater.from(a)
        val view = inflater.inflate(R.layout.dialog_switch, null)
        val title = a.getString(R.string.confirm_switch_title, a.getString(R.string.oneios_short))
        view.findViewById<TextView>(R.id.switch_title).text = title
        view.accessibilityPaneTitle = title
        view.findViewById<TextView>(R.id.switch_message).text = a.getString(R.string.oneios_switch_message)
        val notes = listOfNotNull(s.flow.runtimeLine?.let { a.getString(R.string.oneios_switch_note_runtime, it) }, s.flow.imageLine?.let { a.getString(R.string.oneios_switch_note_image, it) })
        view.findViewById<TextView>(R.id.switch_notes).apply {
            text = notes.joinToString("\n")
            visibility = if (notes.isEmpty()) View.GONE else View.VISIBLE
        }

        // The ways back to One UI, always listed, the keys first (they are the usual way).
        val ways = listOf(
            Way(R.drawable.ic_home_back_keys, a.getString(R.string.home_sheet_back_keys), a.getString(R.string.oneios_back_keys_line), primary = true),
            Way(R.drawable.ic_home_back_keys, a.getString(R.string.oneios_back_starting), a.getString(R.string.oneios_back_starting_line)),
            Way(R.drawable.ic_oneos_row_last_time, a.getString(R.string.oneios_back_by_itself), a.getString(R.string.oneios_back_by_itself_line)),
            Way(R.drawable.ic_home_back_power, a.getString(R.string.oneios_back_stuck), a.getString(R.string.oneios_back_stuck_line)),
        )
        view.findViewById<TextView>(R.id.switch_ways_title).setText(R.string.oneios_ways_four)
        val wayList = view.findViewById<LinearLayout>(R.id.switch_ways)
        for (w in ways) {
            val tile = inflater.inflate(R.layout.home_way_tile, wayList, false)
            tile.findViewById<View>(R.id.way_chip).setBackgroundResource(if (w.primary) R.drawable.home_way_chip_primary_bg else R.drawable.home_way_chip_bg)
            tile.findViewById<ImageView>(R.id.way_icon).apply {
                setImageResource(w.icon)
                imageTintList = ColorStateList.valueOf(a.getColor(if (w.primary) R.color.home_way_icon_on_primary else R.color.home_way_icon))
            }
            tile.findViewById<TextView>(R.id.way_title).text = w.title
            tile.findViewById<TextView>(R.id.way_line).text = w.line
            wayList.addView(tile)
        }

        // Both boxes, every time (the One UI check box of the Switch sheet).
        val ackList = view.findViewById<LinearLayout>(R.id.switch_acks)
        val readBox = (inflater.inflate(R.layout.home_switch_ack, ackList, false) as CheckBox).apply {
            setText(R.string.oneios_ack_read)
            ackList.addView(this)
        }
        val experimentalBox = (inflater.inflate(R.layout.home_switch_ack, ackList, false) as CheckBox).apply {
            text = a.getString(R.string.oneios_ack)
            ackList.addView(this)
        }
        val deviceBox = if (OneiosJob.state.offered == false) {
            (inflater.inflate(R.layout.home_switch_ack, ackList, false) as CheckBox).apply {
                text = a.getString(R.string.oneios_not_this_phone_ack)
                ackList.addView(this)
            }
        } else null
        // The Android takeover: a toggle, never a condition of Switch; off unless ticked now.
        val takeoverBox = if (OneiosJob.takeoverOffered == true) {
            (inflater.inflate(R.layout.home_switch_ack, ackList, false) as CheckBox).apply {
                text = "${OneiosSystem.TAKEOVER_TITLE}: ${OneiosSystem.TAKEOVER_WARNING}"
                isChecked = false
                ackList.addView(this)
            }
        } else null
        ackList.visibility = View.VISIBLE

        val dialog = AlertDialog.Builder(a).setView(view).create()
        val go = view.findViewById<Button>(R.id.switch_go)
        go.setText(R.string.oneios_switch)
        fun update() {
            go.isEnabled = readBox.isChecked && experimentalBox.isChecked && (deviceBox?.isChecked ?: true)
        }
        readBox.setOnCheckedChangeListener { _, _ -> update() }
        experimentalBox.setOnCheckedChangeListener { _, _ -> update() }
        deviceBox?.setOnCheckedChangeListener { _, _ -> update() }
        update()
        view.findViewById<Button>(R.id.switch_cancel).setOnClickListener { dialog.dismiss() }
        go.setOnClickListener {
            if (!readBox.isChecked || !experimentalBox.isChecked || deviceBox?.isChecked == false) return@setOnClickListener
            if (OneiosJob.state.busy) return@setOnClickListener
            dialog.dismiss()
            // The experimental tick is what root's switch verb takes; the read box only gates this button.
            OneiosJob.switch(a, experimentalBox.isChecked, deviceBox?.isChecked == true, takeover = takeoverBox?.isChecked == true)
            if (OneiosJob.state.busy) a.startActivity(OneiosSwitchActivity.intent(a))
        }
        dialog.show()
    }

    private class Way(@DrawableRes val icon: Int, val title: String, val line: String, val primary: Boolean = false)
}
