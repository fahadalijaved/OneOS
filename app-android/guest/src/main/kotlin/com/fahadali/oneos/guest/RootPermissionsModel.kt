package com.fahadali.oneos.guest

import android.app.Application
import android.content.pm.ApplicationInfo
import android.os.Handler
import android.os.Looper
import androidx.lifecycle.AndroidViewModel
import com.fahadali.oneos.core.model.GuestRootPermissions as Permissions
import java.util.concurrent.Executors

class RootPermissionsModel(application: Application) : AndroidViewModel(application) {
    data class State(val groups: List<Permissions.Group> = emptyList(), val loading: Boolean = false,
        val pending: Map<Int,Boolean> = emptyMap(), val error: String? = null, val loaded: Boolean = false)
    private val io=Executors.newSingleThreadExecutor()
    private val main=Handler(Looper.getMainLooper())
    private val metadata=hashMapOf<String,Pair<String,Boolean>>()
    var state=State();private set
    var observer: ((State)->Unit)?=null
    private fun publish(next:State) { state=next;observer?.invoke(next) }
    private fun identity() {
        check(java.io.File("/data/adb/oneos/run/su.sock").exists()) { "Guest root runtime is inactive" }
        val result=GuestRuntime.command("--oneos-info")
        check(result.first==0 && result.second.trim()=="OneOS guest root API 1 manager=${getApplication<Application>().packageName}") { "Guest root runtime needs an update" }
    }
    private fun grants():List<Permissions.Grant> {
        val result=GuestRuntime.command("--oneos-list")
        check(result.first==0) { result.second.ifBlank { "Could not read guest root permissions" } }
        return Permissions.parse(result.second)
    }
    private fun load():List<Permissions.Group> {
        val pm=getApplication<Application>().packageManager
        return Permissions.groups(grants().map { grant ->
            val meta=metadata.getOrPut(grant.packageName) {
                runCatching {
                    val app=pm.getApplicationInfo(grant.packageName,0)
                    pm.getApplicationLabel(app).toString().ifBlank { grant.packageName } to ((app.flags and (ApplicationInfo.FLAG_SYSTEM or ApplicationInfo.FLAG_UPDATED_SYSTEM_APP))!=0)
                }.getOrDefault(grant.packageName to true)
            }
            Permissions.App(grant.packageName,grant.uid,grant.allowed,meta.first,meta.second)
        })
    }
    fun refresh() {
        if(state.loading || state.pending.isNotEmpty())return
        publish(state.copy(loading=true,error=null))
        io.execute {
            val result=runCatching { identity();metadata.clear();load() }
            main.post {
                result.onSuccess { publish(state.copy(groups=it,loading=false,loaded=true,error=null)) }
                    .onFailure { publish(state.copy(loading=false,loaded=true,error=it.message ?: "Could not read root permissions")) }
            }
        }
    }
    fun change(group:Permissions.Group,allow:Boolean) {
        if(state.loading || group.uid in state.pending)return
        publish(state.copy(pending=state.pending+(group.uid to allow),error=null))
        io.execute {
            val result=runCatching {
                identity()
                val current=grants().filter { it.uid==group.uid }
                check(current.any { it.packageName==group.primary.packageName }) { "This app changed or was removed. Refresh and try again." }
                // A single grant permits the shared UID; revoke every grant for that UID.
                val targets=if(allow) listOf(current.first { it.packageName==group.primary.packageName }) else current.filter { it.allowed }
                targets.forEach { app ->
                    val response=GuestRuntime.command(if(allow) "--oneos-grant" else "--oneos-revoke",app.packageName)
                    check(response.first==0) { response.second.ifBlank { "Could not save root access" } }
                }
                load()
            }
            val recovered=if(result.isFailure)runCatching { load() }.getOrNull() else null
            main.post {
                publish(state.copy(groups=result.getOrNull() ?: recovered ?: state.groups,pending=state.pending-group.uid,
                    error=result.exceptionOrNull()?.message,loaded=true))
            }
        }
    }
    fun dismissError() { publish(state.copy(error=null)) }
    override fun onCleared() { observer=null;io.shutdown();super.onCleared() }
}
