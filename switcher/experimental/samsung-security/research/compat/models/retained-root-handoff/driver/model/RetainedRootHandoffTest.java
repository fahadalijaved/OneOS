package model;
import java.lang.reflect.InvocationTargetException;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Path;
import java.nio.file.Paths;

/** Loads unchanged app SDK bytes with an authored F/Spawn cohort per scenario. */
public final class RetainedRootHandoffTest {
    private static Object invoke(ClassLoader loader,String type,String method,Class<?>[] signature,Object... args)throws Throwable {
        try{return Class.forName(type,true,loader).getMethod(method,signature).invoke(null,args);}
        catch(InvocationTargetException problem){throw problem.getCause();}
    }
    public static void main(String[] args)throws Throwable {
        if(args.length!=7)throw new IllegalArgumentException("host,app,integration-F,C,app-F,own-case-root,repository required");
        Path program=Paths.get(args[1]).toRealPath(),framework=Paths.get(args[4]).toRealPath();
        ClassLoader platform=ClassLoader.getPlatformClassLoader();
        int checks=0,cases=0;
        for(int scenario=0;scenario<16;scenario++){
            try(URLClassLoader world=new URLClassLoader(new URL[]{framework.toUri().toURL(),program.toUri().toURL()},platform)){
                if(scenario==0)checks+=(Integer)invoke(world,"model.HandoffProtocolAssertions","run",new Class<?>[0]);
                checks+=(Integer)invoke(world,"com.fahadali.oneos.core.root.OfferRelayAssertions","run",new Class<?>[]{int.class},scenario);
            }
            cases++;System.out.println("MODEL_CASE "+scenario);
        }
        checks+=HostHandoffAssertions.run(args);cases+=16;
        System.out.println("{\"pass\":true,\"modeledOnly\":true,\"cases\":"+cases+",\"checks\":"+checks+",\"nativeExecuted\":false,\"actualHostIssuerExercised\":true}");
    }
}
