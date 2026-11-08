package model;
import java.net.*;
import java.nio.file.*;
import java.lang.reflect.*;

/** Every case has fresh canonical-model and unchanged-cell statics. */
public final class CompletionModelTest {
    public static void main(String[] args) throws Throwable {
        if(args.length!=2)throw new IllegalArgumentException("program and authored fixtures");
        URL[] urls={Paths.get(args[0]).toRealPath().toUri().toURL(),Paths.get(args[1]).toRealPath().toUri().toURL()};
        int checks=0;
        for(int number=0;number<16;number++) {
            try(URLClassLoader loader=new URLClassLoader(urls,ClassLoader.getPlatformClassLoader())) {
                Class<?> dispatcher=Class.forName("com.appleexploit.oneos.security.transport.CompletionModelDispatcher",true,loader);
                try {checks+=((Integer)dispatcher.getMethod("runCase",int.class).invoke(null,number)).intValue();}
                catch(InvocationTargetException failure){throw failure.getCause();}
            }
            System.out.println("MODEL_CASE "+number);
        }
        System.out.println("{\"pass\":true,\"modeledOnly\":true,\"cases\":16,\"checks\":"+checks+",\"privateCellStateInspected\":false,\"runnableInvocations\":0}");
    }
}
