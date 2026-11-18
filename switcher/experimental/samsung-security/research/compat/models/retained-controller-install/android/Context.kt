package android.content
import android.content.res.AssetManager
import java.io.File
class Context(private val selectedPackage:String="com.fahadali.oneos") {
 val applicationContext:Context get()=this
 val packageName:String get()=selectedPackage
 val assets=AssetManager()
 val filesDir:File get()=model.SetupWorld.case.resolve("app-files").toFile()
}
