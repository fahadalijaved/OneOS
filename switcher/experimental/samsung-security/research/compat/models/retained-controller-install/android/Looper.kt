package android.os
class Looper private constructor(val thread:Thread) {
 companion object {
  private var main=Looper(Thread("authored-main-not-started"))
  @JvmStatic fun getMainLooper():Looper=main
  @JvmStatic fun myLooper():Looper?=if(Thread.currentThread()===main.thread)main else null
  @JvmStatic fun modelMain(){main=Looper(Thread.currentThread())}
 }
}
