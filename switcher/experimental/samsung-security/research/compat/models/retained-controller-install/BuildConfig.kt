package com.fahadali.oneos
/** Model configuration only; actual app source bodies compile unchanged against these pins. */
object BuildConfig {
 @JvmField val APPLICATION_ID="com.fahadali.oneos"
 @JvmField val ROOT_SCRIPT_SHA256=System.getProperty("model.script.sha")
 @JvmField val ROOT_SCRIPT_BYTES=System.getProperty("model.script.bytes").toLong()
 @JvmField val RETAINED_CONTROLLER_SHA256=System.getProperty("model.native.sha")
 @JvmField val RETAINED_CONTROLLER_BYTES=System.getProperty("model.native.bytes").toLong()
 @JvmField val SCRIPTS_SHA256="0".repeat(64)
}
