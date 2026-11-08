package model

import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.root.RootScript
import com.fahadali.oneos.core.root.RootShell
import com.fahadali.oneos.session.RootVerbs
import java.io.ByteArrayOutputStream
import java.io.OutputStream
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.concurrent.TimeUnit
import kotlin.concurrent.thread

/** Explicit process/path harness. No real RootShell ProcessBuilder or lifetime is exercised. */
object SetupWorld {
    lateinit var repository:Path
    lateinit var case:Path
    lateinit var script:Path
    lateinit var prelude:Path
    lateinit var shell:Path
    var mode=""
    var assetOpens=0
    var assetCloses=0
    var shellRuns=0
    var containedRuns=0
    var cancelCalls=0
    var feedCallbacks=0
    var reentryRefused=0
    var capturedFeedBytes=0L
    fun nativeBytes()=ByteArray(128){((it*7+3)%251).toByte()}
    fun configure(args:Array<String>) {
        require(args.size==6)
        repository=Path.of(args[0]).toRealPath();case=Path.of(args[1]).toRealPath()
        require(case.startsWith(repository.resolve("out")))
        script=Path.of(args[2]).toRealPath();prelude=Path.of(args[3]).toRealPath();shell=Path.of(args[4]).toRealPath();mode=args[5]
        require(script.startsWith(case)&&prelude.startsWith(case))
    }
    private fun posix(path:Path):String {
        val value=path.toAbsolutePath().normalize().toString().replace('\\','/')
        return if(value.length>2&&value[1]==':')"/"+value[0].lowercase()+value.substring(2) else value
    }
    fun runActualShell(command:String,feed:RootShell.Feed?,onLine:(String)->Unit):RootShell.End {
        shellRuns++
        val line=command.lineSequence().single{it.startsWith("set -- ")}.removePrefix("set -- ")
        val words=line.split(' ');require(words.size==3&&words[0]=="install-closed-controller")
        val args=words.drop(1)
        require(command==RootScript.launcher(RootScript.Verb.INSTALL_CLOSED_CONTROLLER,args,
            BuildConfig.ROOT_SCRIPT_SHA256,BuildConfig.ROOT_SCRIPT_BYTES)){"actual PHONE command differs"}
        val captured=object:ByteArrayOutputStream(){
            override fun write(b:ByteArray,off:Int,len:Int){
                check(count+len<=3*1024*1024){"bounded model feed"}
                if(mode=="feed_error"&&count>=BuildConfig.ROOT_SCRIPT_BYTES)throw java.io.IOException("authored feed failure")
                super.write(b,off,len)
                if(feedCallbacks++==0){
                    RootVerbs.cancel() // During the actual source-owned install feed.
                    if(mode=="reenter"){
                        var refused=false
                        try{com.fahadali.oneos.session.RetainedControllerSetup.ensureInstalled(android.content.Context(),BuildConfig.RETAINED_CONTROLLER_SHA256,BuildConfig.RETAINED_CONTROLLER_BYTES)}
                        catch(expected:IllegalStateException){refused=true}
                        if(!refused)throw AssertionError("reentry admitted")
                        reentryRefused++
                    }
                }
            }
        }
        try{requireNotNull(feed).write(captured);captured.flush()}
        catch(failure:Throwable){capturedFeedBytes=captured.size().toLong();return RootShell.End(null,"",false,true,"authored feed unavailable",capturedFeedBytes)}
        capturedFeedBytes=captured.size().toLong()
        val bytes=captured.toByteArray();val prefix=Files.readAllBytes(script)
        require(bytes.size==prefix.size+nativeBytes().size&&bytes.copyOfRange(0,prefix.size).contentEquals(prefix))
        require(bytes.copyOfRange(prefix.size,bytes.size).contentEquals(nativeBytes())){"actual SCRIPT_DATA feed is prefix then native, without omission/duplication"}
        val fake=RootScript.Layout(posix(case.resolve("stage")),posix(case.resolve("legacy")),"/bin/sh",posix(case.resolve("proc")),"0","0:0")
        val text=RootScript.launcher(RootScript.Verb.INSTALL_CLOSED_CONTROLLER,args,BuildConfig.ROOT_SCRIPT_SHA256,BuildConfig.ROOT_SCRIPT_BYTES,fake)
        val launcher=case.resolve("app-launcher.sh");Files.writeString(launcher,Files.readString(prelude)+"\n"+text)
        val payload=case.resolve("app-payload.bin");Files.write(payload,bytes)
        val pb=ProcessBuilder(shell.toString(),"--noprofile","--norc",launcher.toString()).directory(case.toFile()).redirectInput(payload.toFile())
        listOf("BASH_ENV","ENV","SHELLOPTS","BASHOPTS","CDPATH","GLOBIGNORE").forEach{pb.environment().remove(it)}
        containedRuns++
        val out=ByteArrayOutputStream();val err=ByteArrayOutputStream()
        val errors=java.util.concurrent.ConcurrentLinkedQueue<Throwable>()
        val readers=mutableListOf<Thread>();val pipes=mutableListOf<java.io.InputStream>()
        var child:Process?=null;var exit:Int?=null;var primary:Throwable?=null
        fun remember(t:Throwable){if(primary==null)primary=t else if(primary!==t)primary!!.addSuppressed(t)}
        try {
            child=pb.start() // Retained before stream acquisition, Thread allocation or start.
            pipes.add(child.inputStream);pipes.add(child.errorStream)
            for((index,input) in pipes.withIndex()) {
                val target=if(index==0)out else err
                val reader=Thread({
                    try{input.use{val bytes=ByteArray(4096);while(true){val n=it.read(bytes);if(n<0)break;synchronized(target){check(target.size()+n<=256*1024);target.write(bytes,0,n)}}}}
                    catch(t:Throwable){errors.add(t)}
                },"authored-installer-reader-$index")
                readers.add(reader);reader.isDaemon=true;reader.start()
            }
            check(child.waitFor(40,TimeUnit.SECONDS)){"contained shell timeout"}
            exit=child.exitValue()
        } catch(t:Throwable){remember(t)}
        finally {
            val owned=child
            if(owned!=null){
                try{if(owned.isAlive)owned.destroyForcibly()}catch(t:Throwable){remember(t)}
                try{if(owned.waitFor(5,TimeUnit.SECONDS))exit=owned.exitValue() else remember(AssertionError("owned shell reap unconfirmed"))}catch(t:Throwable){remember(t)}
                for(reader in readers)try{if(reader.state!=Thread.State.NEW)reader.join(2000);if(reader.isAlive)remember(AssertionError("owned reader remains active"))}catch(t:Throwable){remember(t)}
                for((index,input) in pipes.withIndex())if(index>=readers.size||readers[index].state==Thread.State.NEW)try{input.close()}catch(t:Throwable){remember(t)}
            }
            for(t in errors)remember(t)
            try{
                Files.write(case.resolve("app-shell.stdout"),synchronized(out){out.toByteArray()})
                Files.write(case.resolve("app-shell.stderr"),synchronized(err){err.toByteArray()})
                Files.writeString(case.resolve("app-shell.result.json"),"{\"exitCode\":$exit,\"reaped\":${exit!=null},\"failed\":${primary!=null},\"readerIncomplete\":${readers.any{it.isAlive}},\"descendantCleanupClaimed\":false}")
            }catch(t:Throwable){remember(t)}
        }
        primary?.let{throw it}
        val stdout=out.toString("UTF-8");val stderr=err.toString("UTF-8")
        stdout.lineSequence().filter{it.isNotEmpty()}.filterNot{mode=="lost_ack"&&it.startsWith("@@OK")}.forEach(onLine)
        if(mode=="duplicate_ack"&&exit==0){
            val real=stdout.lineSequence().single{it=="@@OK closed-controller-installed"}
            onLine(real) // Explicit negative replay of an observed genuine ACK, never a fabricated success.
        }
        return RootShell.End(exit,stderr,false,false,null,capturedFeedBytes)
    }
}
