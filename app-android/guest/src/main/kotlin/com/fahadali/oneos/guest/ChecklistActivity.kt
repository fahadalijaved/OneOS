package com.fahadali.oneos.guest

import android.app.Activity
import android.os.Bundle
import android.text.Editable
import android.text.InputFilter
import android.text.InputType
import android.text.TextWatcher
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.io.IOException

/**
 * How's it going? (0.4.30): one row per item (Works, Problem, Didn't try) and
 * a note, saved as the user taps ([Checklist]). Plain framework UI like the
 * rest of this app; nothing leaves the phone from here: OneOS sends it with
 * the logs from One UI when the user taps Send to the OneOS team.
 */
class ChecklistActivity : Activity() {
    private val answers = mutableMapOf<String, String>()
    private var note = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Checklist.read(this).let { answers += it.items; note = it.note }
        val pad = dp(24)
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad, pad, pad)
        }
        column.addView(text(getString(R.string.checklist_title), 24f, top = 0))
        column.addView(text(getString(R.string.checklist_intro), 15f, top = dp(8), secondary = true))
        for ((id, label) in Checklist.ITEMS) {
            column.addView(text(getString(label), 17f, top = dp(20)))
            val group = RadioGroup(this).apply { orientation = RadioGroup.HORIZONTAL }
            val options = listOf(Checklist.WORKS to R.string.answer_works, Checklist.PROBLEM to R.string.answer_problem, Checklist.NOT_TRIED to R.string.answer_not_tried)
            for ((value, labelRes) in options) {
                val b = RadioButton(this).apply {
                    this.id = View.generateViewId()
                    text = getString(labelRes)
                    tag = value
                    setPadding(0, 0, dp(12), 0)
                }
                group.addView(b)
                if ((answers[id] ?: Checklist.NOT_TRIED) == value) b.isChecked = true
            }
            group.setOnCheckedChangeListener { g, checked ->
                val v = g.findViewById<RadioButton>(checked)?.tag as? String ?: return@setOnCheckedChangeListener
                if (v == Checklist.NOT_TRIED) answers.remove(id) else answers[id] = v
                save()
            }
            column.addView(group)
        }
        column.addView(text(getString(R.string.checklist_note), 17f, top = dp(24)))
        val edit = EditText(this).apply {
            setText(note)
            hint = getString(R.string.checklist_note_hint)
            filters = arrayOf(InputFilter.LengthFilter(Checklist.NOTE_MAX))
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
            minLines = 3
            gravity = Gravity.TOP or Gravity.START
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) = Unit
                override fun afterTextChanged(s: Editable?) {
                    note = s?.toString().orEmpty()
                }
            })
        }
        column.addView(edit)
        column.addView(text(getString(R.string.checklist_saved), 14f, top = dp(16), secondary = true))
        val scroll = ScrollView(this).apply {
            addView(column)
            // Edge to edge (target 35+), as MainActivity.
            setOnApplyWindowInsetsListener { v, insets ->
                val b = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout() or WindowInsets.Type.ime())
                v.setPadding(b.left, b.top, b.right, b.bottom)
                insets
            }
        }
        setContentView(scroll)
    }

    // The note is saved when the screen goes away (and each tap saves the rest at once).
    override fun onPause() {
        save()
        super.onPause()
    }

    private fun save() {
        try {
            Checklist.save(this, Checklist.Answers(answers.toMap(), note))
        } catch (e: IOException) {
            Toast.makeText(this, getString(R.string.checklist_not_saved, e.message ?: e.javaClass.simpleName), Toast.LENGTH_LONG).show()
        }
    }

    private fun text(s: String, sp: Float, top: Int, secondary: Boolean = false): TextView = TextView(this).apply {
        text = s
        setTextSize(TypedValue.COMPLEX_UNIT_SP, sp)
        if (secondary) {
            val a = obtainStyledAttributes(intArrayOf(android.R.attr.textColorSecondary))
            setTextColor(a.getColorStateList(0))
            a.recycle()
        }
        layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { topMargin = top }
    }

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()
}
