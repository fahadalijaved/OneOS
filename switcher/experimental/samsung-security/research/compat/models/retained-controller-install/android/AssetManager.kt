package android.content.res
import java.io.ByteArrayInputStream
import java.io.InputStream
import java.io.IOException
import java.nio.file.Files
import model.SetupWorld
/** Only two retained, repo-owned model assets; never actual app/OEM assets. */
class AssetManager {
 fun list(path:String):Array<String> = emptyArray()
 fun open(name:String):InputStream {
  SetupWorld.assetOpens++
  val original=when(name){
   "root/oneos_root.sh" -> Files.readAllBytes(SetupWorld.script)
   "root/oneos_retained_root_session" -> SetupWorld.nativeBytes()
   else -> error("unknown model asset")
  }
  val bytes=when {
   name.endsWith("root.sh") && SetupWorld.mode=="bad_script" -> original.clone().also{it[0]=(it[0].toInt() xor 1).toByte()}
   name.endsWith("session") && SetupWorld.mode=="short" -> original.copyOf(original.size-1)
   name.endsWith("session") && SetupWorld.mode=="long" -> original+byteArrayOf(9)
   name.endsWith("session") && SetupWorld.mode=="corrupt" -> original.clone().also{it[0]=(it[0].toInt() xor 1).toByte()}
   else -> original
  }
  return object:ByteArrayInputStream(bytes){override fun close(){SetupWorld.assetCloses++;super.close();if(name.endsWith("session")&&SetupWorld.mode=="asset_close")throw IOException("model asset close uncertain")}}
 }
}
