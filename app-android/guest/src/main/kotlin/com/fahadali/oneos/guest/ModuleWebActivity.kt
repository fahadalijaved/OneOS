package com.fahadali.oneos.guest

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.MimeTypeMap
import android.widget.LinearLayout
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AlertDialog
import com.fahadali.oneos.shared.NativeCards
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.util.concurrent.Executors

/** Local module assets only; the root bridge always uses this guest's authenticated broker. */
class ModuleWebActivity : AppCompatActivity() {
    private lateinit var web: WebView
    private lateinit var module: String
    private val io = Executors.newCachedThreadPool()
    private val jobs = java.util.concurrent.ConcurrentHashMap.newKeySet<Process>()
    private lateinit var origin: String
    private val callback = Regex("[A-Za-z_$][A-Za-z0-9_$]*")
    private var info = "{}"
    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        module = intent.getStringExtra("module").orEmpty()
        if (!module.matches(Regex("[A-Za-z][A-Za-z0-9._-]{1,63}"))) { finish(); return }
        origin = java.security.MessageDigest.getInstance("SHA-256").digest(module.toByteArray()).take(12).joinToString("") { "%02x".format(it) } + ".oneos-module.local"
        val content=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL; fitsSystemWindows=true }
        setContentView(content)
        val bar=NativeCards.section(content,null,getColor(R.color.preboot_card))
        NativeCards.row(bar,"Module WebUI", "Back to guest modules") { finish() }
        web=WebView(this); content.addView(web,LinearLayout.LayoutParams(-1,0,1f))
        web.settings.apply {
            javaScriptEnabled=true; domStorageEnabled=true; allowFileAccess=false; allowContentAccess=false
            mixedContentMode=android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
            setSupportMultipleWindows(false)
        }
        web.addJavascriptInterface(Bridge(),"ksu")
        web.webViewClient=object:WebViewClient() {
            override fun shouldOverrideUrlLoading(view:WebView,request:WebResourceRequest):Boolean = !local(request.url)
            override fun shouldInterceptRequest(view:WebView,request:WebResourceRequest):WebResourceResponse {
                if (!local(request.url)) return failure()
                return runCatching {
                    val path=request.url.path.orEmpty().removePrefix("/")
                    require(path.isNotEmpty() && path.split('/').none { it == ".." || it == "." || it.isEmpty() })
                    val script="/system/bin/sh /data/oneos_runtime.sh control asset ${GuestRuntime.quote(module)} ${GuestRuntime.quote(path)}"
                    val p=process(script); val bytes=try { val data=p.inputStream.use { input ->
                        val out=java.io.ByteArrayOutputStream();val b=ByteArray(65536)
                        while(true){val n=input.read(b);if(n<0)break;require(out.size()+n<=16*1024*1024);out.write(b,0,n)};out.toByteArray()
                    }
                        check(p.waitFor()==0);data
                    } finally { jobs.remove(p);p.destroy() }
                    val mime=when(path.substringAfterLast('.').lowercase()){ "js","mjs"->"application/javascript";"css"->"text/css";"html"->"text/html";"json"->"application/json";"svg"->"image/svg+xml";else->MimeTypeMap.getSingleton().getMimeTypeFromExtension(path.substringAfterLast('.')) ?: "application/octet-stream" }
                    WebResourceResponse(mime,"UTF-8",200,"OK",mapOf("Access-Control-Allow-Origin" to "https://$origin", "X-Content-Type-Options" to "nosniff", "Content-Security-Policy" to "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; style-src 'self' 'unsafe-inline'; frame-src 'none'; object-src 'none'"),ByteArrayInputStream(bytes))
                }.getOrElse { failure() }
            }
        }
        GuestRuntime.work({
            val state=GuestRuntime.read(applicationContext)
            val m=state.modules.first { it.id==module && !it.pending && !it.removing }
            check(state.root && "webui" in m.capabilities)
            info=JSONObject().put("id",m.id).put("name",m.name).put("version",m.version).put("versionCode",m.versionCode)
                .put("author",m.author).put("description",m.description).put("moduleDir","/data/adb/modules/$module").toString()
            state
        }) { state ->
            if(isDestroyed)return@work
            if(state.error!=null){ AlertDialog.Builder(this).setTitle("Module WebUI").setMessage(state.error).setPositiveButton(android.R.string.ok){_,_->finish()}.show() }
            else web.loadUrl("https://$origin/index.html")
        }
    }
    private fun local(uri:android.net.Uri)=uri.scheme=="https" && uri.host==origin && uri.port in listOf(-1,443)
    private fun failure()=WebResourceResponse("text/plain","UTF-8",403,"Forbidden",emptyMap(),ByteArrayInputStream("Module resource unavailable".toByteArray()))
    private fun process(script:String):Process {
        check(java.io.File("/data/adb/oneos/run/su.sock").exists()) { "Guest runtime unavailable" }
        return ProcessBuilder("/system/xbin/su","-c",script).start().also { jobs.add(it) }
    }
    private fun script(cmd:String,options:String?):String {
        val opts=if(options.isNullOrBlank())JSONObject()else JSONObject(options)
        val cwd=opts.optString("cwd").ifBlank { "/data/adb/modules/$module" }
        val env=opts.optJSONObject("env")
        val exports=StringBuilder("export ASH_STANDALONE=1 PATH=/system/bin:/system/xbin:/data/adb/ksu/bin; ")
        env?.keys()?.forEach { key -> require(key.matches(Regex("[A-Za-z_][A-Za-z0-9_]*")));exports.append("export $key=${GuestRuntime.quote(env.getString(key))}; ") }
        return "cd ${GuestRuntime.quote(cwd)} || exit 1; $exports /data/oneos_bin/busybox timeout 120 /data/oneos_bin/busybox sh -c ${GuestRuntime.quote(cmd)}"
    }
    private fun js(code:String) { web.post { if(!isDestroyed)web.evaluateJavascript(code,null) } }
    inner class Bridge {
        @JavascriptInterface fun exec(cmd:String):String {
            val p=process(script(cmd,null)); val err=io.submit<String> { GuestRuntime.boundedOutput(p.errorStream) }
            val output=GuestRuntime.boundedOutput(p.inputStream);p.waitFor();err.get();jobs.remove(p);return output
        }
        @JavascriptInterface fun exec(cmd:String,cb:String)=exec(cmd,null,cb)
        @JavascriptInterface fun exec(cmd:String,options:String?,cb:String) {
            require(callback.matches(cb))
            io.execute {
                runCatching {
                    val p=process(script(cmd,options))
                    val err=io.submit<String>{GuestRuntime.boundedOutput(p.errorStream)}
                    val out=GuestRuntime.boundedOutput(p.inputStream);val status=p.waitFor();val stderr=err.get();jobs.remove(p)
                    js("window[${JSONObject.quote(cb)}]($status,${JSONObject.quote(out)},${JSONObject.quote(stderr)})")
                }.onFailure { js("window[${JSONObject.quote(cb)}](1,'',${JSONObject.quote(it.message ?: "Command failed")})") }
            }
        }
        @JavascriptInterface fun spawn(command:String,args:String,options:String?,cb:String) {
            require(callback.matches(cb))
            io.execute {
                runCatching {
                    val a=JSONArray(args);val cmd=GuestRuntime.quote(command)+(0 until a.length()).joinToString(""){" "+GuestRuntime.quote(a.getString(it))}
                    val p=process(script(cmd,options))
                    fun stream(name:String,input:java.io.InputStream) {
                        input.reader().use { reader ->
                            val buffer=CharArray(4096);var sent=0
                            while(true){val n=reader.read(buffer);if(n<0)break;if(sent<1048576){val data=String(buffer,0,minOf(n,1048576-sent));sent+=data.length;js("window[${JSONObject.quote(cb)}].$name.emit('data',${JSONObject.quote(data)})")}}
                        }
                    }
                    val err=io.submit { stream("stderr",p.errorStream) };stream("stdout",p.inputStream);val code=p.waitFor();err.get();jobs.remove(p)
                    if(code!=0)js("window[${JSONObject.quote(cb)}].emit('error',Object.assign(new Error('Command failed'),{exitCode:$code}))")
                    js("window[${JSONObject.quote(cb)}].emit('exit',$code)")
                }.onFailure { js("window[${JSONObject.quote(cb)}].emit('error',new Error(${JSONObject.quote(it.message ?: "Command failed")}))") }
            }
        }
        @JavascriptInterface fun moduleInfo()=info
        @JavascriptInterface fun toast(message:String) { runOnUiThread { Toast.makeText(this@ModuleWebActivity,message,Toast.LENGTH_SHORT).show() } }
        @JavascriptInterface fun fullScreen(enabled:Boolean) { runOnUiThread { if(enabled) window.insetsController?.hide(android.view.WindowInsets.Type.systemBars()) else window.insetsController?.show(android.view.WindowInsets.Type.systemBars()) } }
        @JavascriptInterface fun enableEdgeToEdge(enabled:Boolean) { runOnUiThread { window.setDecorFitsSystemWindows(!enabled) } }
    }
    override fun onDestroy() { jobs.forEach { it.destroyForcibly() };io.shutdownNow();if(::web.isInitialized){web.removeJavascriptInterface("ksu");web.destroy()};super.onDestroy() }
}
