package com.fahadali.oneos.core.root
import java.io.OutputStream
import model.SetupWorld
/** ONLY the public process API is replaced. No real RootShell process/drain claim. */
class RootShell(private val command:String,private val retainInvocation:Boolean=false) {
 fun interface Feed {fun write(out:OutputStream)}
 data class End(val exitCode:Int?,val stderr:String,val cancelled:Boolean,val killed:Boolean,val error:String?,val written:Long)
 fun cancel(){SetupWorld.cancelCalls++}
 fun run(feed:Feed?,onLine:(String)->Unit,silenceLimitMs:()->Long,totalLimitMs:Long):End {
  check(retainInvocation){"source must retain controller invocation"}
  return SetupWorld.runActualShell(command,feed,onLine)
 }
}
