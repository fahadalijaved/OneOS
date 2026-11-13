package com.android.internal.os;
import model.ForkControl;
public final class ZygoteInit {
    public static Runnable zygoteInit(int sdk,long[] disabled,long[] enabled,String[] argv,ClassLoader loader) {
        ForkControl.inits++;ForkControl.sdk=sdk;ForkControl.disabled=disabled;ForkControl.enabled=enabled;ForkControl.argv=argv;ForkControl.loader=loader;
        if(ForkControl.duringInit!=null)ForkControl.duringInit.run();
        if(ForkControl.initError!=null)throw ForkControl.initError;return ForkControl.result;
    }
}
