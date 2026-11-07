package com.fahadali.oneos.guest

import android.graphics.drawable.Drawable
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.SectionIndexer
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.fahadali.oneos.core.model.GuestRootPermissions as Permissions
import dev.oneuiproject.oneui.widget.RoundedLinearLayout
import dev.oneuiproject.oneui.widget.SwitchItemView
import java.util.concurrent.Executors
import java.util.concurrent.Future

class RootPermissionAdapter(private val change:(Permissions.Group,Boolean)->Unit) :
    ListAdapter<RootPermissionAdapter.Row,RootPermissionAdapter.Holder>(DIFF),SectionIndexer {
    data class Row(val group:Permissions.Group,val pending:Boolean?,val loading:Boolean,val first:Boolean,val last:Boolean)
    private val icons=android.util.LruCache<String,Drawable.ConstantState>(80)
    private val io=Executors.newFixedThreadPool(2)
    private var closed=false
    init { setHasStableIds(true);stateRestorationPolicy=RecyclerView.Adapter.StateRestorationPolicy.PREVENT_WHEN_EMPTY }
    override fun getItemId(position:Int)=getItem(position).group.uid.toLong()
    override fun onCreateViewHolder(parent:ViewGroup,viewType:Int):Holder {
        val ctx=parent.context
        val frame=LinearLayout(ctx).apply {
            layoutParams=RecyclerView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT)
            orientation=LinearLayout.VERTICAL
        }
        val card=RoundedLinearLayout(ctx).apply {
            orientation=LinearLayout.VERTICAL;setBackgroundColor(ctx.getColor(R.color.preboot_card))
            roundedCorners=androidx.appcompat.util.SeslRoundedCorner.ROUNDED_CORNER_ALL
            val value=android.util.TypedValue();ctx.theme.resolveAttribute(androidx.appcompat.R.attr.roundedCornerColor,value,true)
            roundedCornersColor=value.data;fillHorizontalPadding=false
        }
        val row=SwitchItemView(ctx).apply { showTopDivider=false;showBottomDivider=false;separateSwitch=false;iconSize=frame.dp(40) }
        card.addView(row,LinearLayout.LayoutParams(-1,-2));frame.addView(card,LinearLayout.LayoutParams(-1,-2))
        return Holder(frame,row,card)
    }
    override fun onBindViewHolder(holder:Holder,position:Int)=holder.bind(getItem(position))
    override fun onViewRecycled(holder:Holder) { holder.iconTask?.cancel(true);holder.key=null;holder.row.onCheckedChangedListener=null;super.onViewRecycled(holder) }
    inner class Holder(view:View,val row:SwitchItemView,val card:RoundedLinearLayout):RecyclerView.ViewHolder(view) {
        var key:String?=null;var iconTask:Future<*>?=null
        fun bind(item:Row) {
            val ctx=row.context;val group=item.group;val primary=group.primary
            row.onCheckedChangedListener=null
            row.title=primary.label
            card.roundedCorners=(if(item.first) 3 else 0) or (if(item.last) 12 else 0)
            row.showBottomDivider=!item.last
            val summary=buildString {
                append(primary.packageName)
                if(item.pending!=null)append(" · ").append(ctx.getString(R.string.root_saving))
                if(group.apps.size>1)append("\n").append(ctx.getString(R.string.root_shared,group.apps.size))
            }
            row.summaryOn=summary;row.summaryOff=summary
            row.isChecked=item.pending ?: group.allowed
            row.isEnabled=!item.loading && item.pending==null
            row.findViewById<TextView>(dev.oneuiproject.oneui.design.R.id.switch_card_title).textSize=20f
            row.findViewById<TextView>(dev.oneuiproject.oneui.design.R.id.switch_card_summary)?.apply { textSize=14f;maxLines=Int.MAX_VALUE;ellipsize=null }
            row.findViewById<View>(dev.oneuiproject.oneui.design.R.id.switch_widget).contentDescription=ctx.getString(R.string.root_toggle,primary.label)
            row.onCheckedChangedListener={ _,allowed -> change(group,allowed) }
            row.findViewById<View>(dev.oneuiproject.oneui.design.R.id.content_frame).setOnLongClickListener {
                AlertDialog.Builder(ctx).setTitle(primary.label).setMessage(buildString {
                    if(group.apps.size>1)append(ctx.getString(R.string.root_shared_details,group.uid)).append("\n\n")
                    else append("UID: ${group.uid}\n\n")
                    append(ctx.getString(if(group.allowed)R.string.root_allowed else R.string.root_denied)).append("\n\n")
                    append(group.apps.joinToString("\n\n") { "${it.label}\n${it.packageName}" })
                }).setPositiveButton(android.R.string.ok,null).show();true
            }
            if(key!=primary.packageName) {
                key=primary.packageName;iconTask?.cancel(true)
                val cached=icons.get(primary.packageName)
                row.icon=cached?.newDrawable(ctx.resources) ?: ctx.packageManager.defaultActivityIcon
                if(cached==null && !closed)iconTask=io.submit {
                    val icon=runCatching { ctx.packageManager.getApplicationIcon(primary.packageName) }.getOrNull()
                    icon?.constantState?.let { icons.put(primary.packageName,it) }
                    row.post { if(!closed && key==primary.packageName && icon!=null)row.icon=icon }
                }
            }
        }
    }
    private fun checkpoints():List<Pair<String,Int>> {
        val result=mutableListOf<Pair<String,Int>>()
        currentList.forEachIndexed { index,row ->
            val letter=row.group.primary.label.firstOrNull()?.takeIf { it.isLetterOrDigit() }?.uppercaseChar()?.toString() ?: "#"
            if(result.lastOrNull()?.first!=letter)result.add(letter to index)
        }
        return result
    }
    override fun getSections():Array<String> = checkpoints().map { it.first }.toTypedArray()
    override fun getPositionForSection(sectionIndex:Int):Int { val points=checkpoints();return if(points.isEmpty())0 else points[sectionIndex.coerceIn(points.indices)].second }
    override fun getSectionForPosition(position:Int)=checkpoints().indexOfLast { it.second<=position }.coerceAtLeast(0)
    fun close() { closed=true;io.shutdownNow() }
    private fun View.dp(value:Int)=(value*resources.displayMetrics.density+.5f).toInt()
    companion object {
        private val DIFF=object:DiffUtil.ItemCallback<Row>() {
            override fun areItemsTheSame(old:Row,new:Row)=old.group.uid==new.group.uid
            override fun areContentsTheSame(old:Row,new:Row)=old==new
        }
    }
}
