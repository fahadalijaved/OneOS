package com.fahadali.oneos.guest

import android.os.Bundle
import android.view.View
import android.view.WindowInsets
import android.view.Menu
import android.view.MenuItem
import androidx.appcompat.widget.PopupMenu
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.SearchView
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.recyclerview.widget.SimpleItemAnimator
import com.fahadali.oneos.core.model.GuestRootPermissions as Permissions
import dev.oneuiproject.oneui.layout.ToolbarLayout
import dev.oneuiproject.oneui.utils.applyEdgeToEdge

/** Guest-only root access: recycled native app cards, search and independent filters. */
class GuestRootActivity:AppCompatActivity() {
    private lateinit var model:RootPermissionsModel
    private lateinit var adapter:RootPermissionAdapter
    private lateinit var list:RecyclerView
    private lateinit var search:SearchView
    private val voiceSearch=registerForActivityResult(androidx.activity.result.contract.ActivityResultContracts.StartActivityForResult()) { result ->
        if(result.resultCode==RESULT_OK)result.data?.getStringArrayListExtra(android.speech.RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()?.let {
            search.setQuery(it,false);search.clearFocus()
        }
    }
    private var query=""
    private var access=Permissions.Access.ALL
    private var kind=Permissions.Kind.USER
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState);applyEdgeToEdge();setContentView(R.layout.activity_guest_root)
        model=ViewModelProvider(this)[RootPermissionsModel::class.java]
        query=savedInstanceState?.getString("query").orEmpty()
        access=Permissions.Access.entries.getOrElse(savedInstanceState?.getInt("access") ?: 0){Permissions.Access.ALL}
        kind=Permissions.Kind.entries.getOrElse(savedInstanceState?.getInt("kind") ?: 0){Permissions.Kind.USER}
        val toolbar=findViewById<ToolbarLayout>(R.id.root_toolbar)
        toolbar.setTitle(getString(R.string.root_permissions_title));toolbar.showNavigationButtonAsBack=true
        toolbar.setNavigationButtonOnClickListener { onBackPressedDispatcher.onBackPressed() }
        toolbar.setAdaptiveMarginProvider(dev.oneuiproject.oneui.widget.AdaptiveCoordinatorLayout.MARGIN_PROVIDER_ZERO);toolbar.setEdgeInsetHorizontal(0f)
        toolbar.setOnApplyWindowInsetsListener { view,insets ->
            val bars=insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            val ime=insets.getInsets(WindowInsets.Type.ime())
            view.setPadding(bars.left,bars.top,bars.right,maxOf(bars.bottom,ime.bottom))
            if(::search.isInitialized) search.maxWidth=if(ime.bottom>0) resources.getDimensionPixelSize(androidx.appcompat.R.dimen.sesl_search_view_preferred_width) else dp(280)
            insets
        }
        toolbar.findViewById<dev.oneuiproject.oneui.widget.RoundedFrameLayout>(dev.oneuiproject.oneui.design.R.id.tbl_main_content).apply { roundedCorners=0;fillHorizontalPadding=false }
        toolbar.findViewById<View>(dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners).visibility=View.GONE
        adapter=RootPermissionAdapter { group,allowed -> model.change(group,allowed) }
        list=findViewById<RecyclerView>(R.id.root_apps).apply {
            layoutManager=LinearLayoutManager(this@GuestRootActivity);adapter=this@GuestRootActivity.adapter
            (itemAnimator as? SimpleItemAnimator)?.supportsChangeAnimations=false
            seslSetFastScrollerEnabled(true);seslSetGoToTopEnabled(true)
            seslSetOnGoToTopClickListener { recycler -> recycler.smoothScrollToPosition(0);true }
        }
        search=findViewById<SearchView>(R.id.root_search).apply {
            isIconified=false;setQuery(this@GuestRootActivity.query,false);clearFocus()
            setOnQueryTextListener(object:SearchView.OnQueryTextListener {
                override fun onQueryTextSubmit(value:String?):Boolean { clearFocus();return true }
                override fun onQueryTextChange(value:String?):Boolean { this@GuestRootActivity.query=value.orEmpty();render();return true }
            })
        }
        search.setSearchableInfo(getSystemService(android.app.SearchManager::class.java).getSearchableInfo(componentName))
        search.findViewById<View>(androidx.appcompat.R.id.search_voice_btn).setOnClickListener {
            try {
                voiceSearch.launch(android.content.Intent(android.speech.RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(android.speech.RecognizerIntent.EXTRA_LANGUAGE_MODEL,android.speech.RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(android.speech.RecognizerIntent.EXTRA_MAX_RESULTS,1)
                })
            } catch(_:android.content.ActivityNotFoundException) { search.requestFocus() }
        }
        list.viewTreeObserver.addOnPreDrawListener {
            val listLocation=IntArray(2);val searchLocation=IntArray(2)
            list.getLocationInWindow(listLocation);search.getLocationInWindow(searchLocation)
            val overlap=(listLocation[1]+list.height-searchLocation[1]).coerceAtLeast(0)
            val clearance=overlap+dp(12)
            if(list.paddingBottom!=clearance)list.setPadding(0,0,0,clearance)
            list.seslSetGoToTopBottomPadding(overlap+dp(8))
            true
        }
        findViewById<View>(R.id.root_retry).setOnClickListener { model.refresh() }
        render()
    }
    override fun onCreateOptionsMenu(menu:Menu):Boolean {
        menu.add(Menu.NONE,R.id.root_filters_action,Menu.NONE,R.string.root_filters).apply {
            setIcon(R.drawable.ic_root_filter)
            setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS)
            setOnMenuItemClickListener {
                val toolbar=findViewById<ToolbarLayout>(R.id.root_toolbar).toolbar
                showFilters(toolbar.findViewById<View>(R.id.root_filters_action) ?: toolbar)
                true
            }
        }
        return true
    }
    private fun dp(value:Int)=(value*resources.displayMetrics.density+.5f).toInt()
    private fun showFilters(anchor:View) {
        PopupMenu(this,anchor).apply {
            val accessMenu=menu.addSubMenu(R.string.root_access_filter)
            resources.getStringArray(R.array.root_access_options).forEachIndexed { index,label ->
                accessMenu.add(1,100+index,index,label).isChecked=access.ordinal==index
            }
            accessMenu.setGroupCheckable(1,true,true)
            val kindMenu=menu.addSubMenu(R.string.root_kind_filter)
            resources.getStringArray(R.array.root_kind_options).forEachIndexed { index,label ->
                kindMenu.add(2,200+index,index,label).isChecked=kind.ordinal==index
            }
            kindMenu.setGroupCheckable(2,true,true)
            setOnMenuItemClickListener { item ->
                when(item.groupId) {
                    1 -> access=Permissions.Access.entries[item.itemId-100]
                    2 -> kind=Permissions.Kind.entries[item.itemId-200]
                    else -> return@setOnMenuItemClickListener false
                }
                render();true
            }
            show()
        }
    }
    override fun onStart() {
        super.onStart()
        model.observer={ state ->
            render()
            if(state.error!=null && state.groups.isNotEmpty()) {
                AlertDialog.Builder(this).setTitle(R.string.root_permissions_title).setMessage(state.error).setPositiveButton(android.R.string.ok,null).show()
                model.dismissError()
            }
        }
        render();model.refresh()
    }
    override fun onStop() { model.observer=null;super.onStop() }
    override fun onDestroy() { adapter.close();super.onDestroy() }
    override fun onSaveInstanceState(outState:Bundle) { outState.putString("query",query);outState.putInt("access",access.ordinal);outState.putInt("kind",kind.ordinal);super.onSaveInstanceState(outState) }
    private fun render() {
        if(!::adapter.isInitialized)return
        val state=model.state
        val visible=Permissions.filter(state.groups,query,access,kind)
        adapter.submitList(visible.mapIndexed { index,group -> RootPermissionAdapter.Row(group,state.pending[group.uid],state.loading,index==0,index==visible.lastIndex) })
        val empty=visible.isEmpty()
        findViewById<View>(R.id.root_empty).visibility=if(empty)View.VISIBLE else View.GONE
        list.visibility=if(empty)View.INVISIBLE else View.VISIBLE
        findViewById<TextView>(R.id.root_empty_text).text=when {
            state.loading -> getString(R.string.root_loading)
            state.error!=null && state.groups.isEmpty() -> state.error
            state.groups.isEmpty() -> getString(R.string.root_none)
            else -> getString(R.string.root_no_matches)
        }
        findViewById<View>(R.id.root_retry).visibility=if(empty && state.error!=null)View.VISIBLE else View.GONE
    }
}
