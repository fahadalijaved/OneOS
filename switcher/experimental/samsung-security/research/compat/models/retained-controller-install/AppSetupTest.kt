package model

import android.content.Context
import android.os.Looper
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.session.RetainedControllerSetup
import java.nio.file.Files

/** Public actual setup calls and observable authored process/asset counters only. */
object AppSetupTest {
 @JvmStatic fun main(args:Array<String>) {
  SetupWorld.configure(args)
  val mode=SetupWorld.mode
  if(mode=="main")Looper.modelMain()
  val context=Context(if(mode=="wrong_context")"foreign.app" else "com.fahadali.oneos")
  val hash=if(mode=="bad_expected_pin")"b".repeat(64) else BuildConfig.RETAINED_CONTROLLER_SHA256
  var failure:Throwable?=null
  try{RetainedControllerSetup.ensureInstalled(context,hash,BuildConfig.RETAINED_CONTROLLER_BYTES)}catch(t:Throwable){failure=t}
  val success=mode in listOf("good","reenter")
  check((failure==null)==success){"actual setup outcome differs for $mode: ${failure?.javaClass?.name}"}
  if(success||mode in listOf("lost_ack","duplicate_ack")) {
   check(SetupWorld.shellRuns==1&&SetupWorld.containedRuns==1)
   check(Files.readAllBytes(SetupWorld.case.resolve("stage/bin/oneos_retained_root_session")).contentEquals(SetupWorld.nativeBytes()))
   check(SetupWorld.capturedFeedBytes==BuildConfig.ROOT_SCRIPT_BYTES+BuildConfig.RETAINED_CONTROLLER_BYTES)
   check(SetupWorld.feedCallbacks>0&&SetupWorld.cancelCalls==0){"actual RootVerbs retains install instead of cancelling its source"}
  } else if(mode=="feed_error") {
   check(SetupWorld.shellRuns==1&&SetupWorld.containedRuns==0)
   check(!Files.exists(SetupWorld.case.resolve("stage/bin/oneos_retained_root_session")))
  } else check(SetupWorld.shellRuns==0&&SetupWorld.containedRuns==0){"invalid input/asset must not reach the process boundary"}
  if(mode=="reenter")check(SetupWorld.reentryRefused==1)
  val priorRuns=SetupWorld.shellRuns
  var retryRefused=false
  try{RetainedControllerSetup.ensureInstalled(context,BuildConfig.RETAINED_CONTROLLER_SHA256,BuildConfig.RETAINED_CONTROLLER_BYTES)}catch(t:IllegalStateException){retryRefused=true}
  check(retryRefused&&SetupWorld.shellRuns==priorRuns){"actual setup attempt may not rearm after success or uncertainty"}
  check(SetupWorld.assetOpens==SetupWorld.assetCloses){"all acquired modeled asset streams closed"}
  println("{\"pass\":true,\"actualSetupSource\":true,\"mode\":\"$mode\",\"sourceReturnedNormally\":$success,\"shellCalls\":${SetupWorld.shellRuns},\"containedRuns\":${SetupWorld.containedRuns},\"nativeOrRootExecuted\":false}")
 }
}
