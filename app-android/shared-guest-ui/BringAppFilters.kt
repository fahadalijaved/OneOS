package com.fahadali.oneos.shared

import android.content.Context
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.LinearLayout
import androidx.appcompat.widget.AppCompatSpinner
import androidx.appcompat.widget.SearchView
import com.fahadali.oneos.core.model.BringApps.Filter

class BringAppFilters(
    context: Context,
    hint: CharSequence,
    filterLabel: CharSequence,
    options: List<String>,
    initialFilter: Filter,
    initialQuery: String,
    onChange: (Filter, String) -> Unit,
) : LinearLayout(context) {
    init {
        orientation = VERTICAL
        val inset = (12 * resources.displayMetrics.density).toInt()
        setPaddingRelative(inset, 0, inset, 0)
        val search = SearchView(context).apply {
            setIconifiedByDefault(false)
            queryHint = hint
            setQuery(initialQuery, false)
            clearFocus()
        }
        val types = AppCompatSpinner(context).apply {
            contentDescription = filterLabel
            adapter = ArrayAdapter(context, android.R.layout.simple_spinner_item, options).apply {
                setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
            }
            setSelection(initialFilter.ordinal)
        }
        addView(search, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        addView(types, LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT))

        var filter = initialFilter
        var query = initialQuery
        types.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>, view: View?, position: Int, id: Long) {
                val selected = Filter.entries[position]
                if (selected == filter) return
                filter = selected
                onChange(filter, query)
            }

            override fun onNothingSelected(parent: AdapterView<*>) = Unit
        }
        search.setOnQueryTextListener(object : SearchView.OnQueryTextListener {
            override fun onQueryTextChange(newText: String): Boolean {
                query = newText
                onChange(filter, query)
                return true
            }

            override fun onQueryTextSubmit(text: String): Boolean {
                search.clearFocus()
                return true
            }
        })
    }
}
