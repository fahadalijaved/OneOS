package model;
import java.net.*;
import java.nio.file.*;
import java.lang.reflect.*;
import java.util.*;

/** Fresh public-API/Spawn model loader per case; no private production reflection. */
public final class RootSessionModelTest {
    public static void main(String[] args)throws Throwable {
        if(args.length!=4)throw new IllegalArgumentException("program, fixtures, own data, repo");
        Path program=Paths.get(args[0]).toRealPath(),framework=Paths.get(args[1]).toRealPath();
        Path data=Paths.get(args[2]).toRealPath(),repo=Paths.get(args[3]).toRealPath();
        if(!data.startsWith(repo.resolve("out")) || !Files.isRegularFile(repo.resolve("tools/test_retained_root_session.py")))
            throw new IllegalArgumentException("repo-owned fixture data and runner required");
        int checks=0;
        for(int number=0;number<25;number++) {
            Path own=data.resolve("case-"+number);Files.createDirectory(own);Throwable primary=null;
            try(URLClassLoader loader=new URLClassLoader(new URL[]{framework.toUri().toURL(),program.toUri().toURL()},ClassLoader.getPlatformClassLoader())) {
                Class<?> dispatcher=Class.forName("com.fahadali.oneos.core.root.RootSessionModelDispatcher",true,loader);
                try{checks+=((Integer)dispatcher.getMethod("runCase",int.class,String.class,String.class).invoke(null,number,repo.toString(),own.toString())).intValue();}
                catch(InvocationTargetException failure){throw failure.getCause();}
            }catch(Throwable failure){primary=failure;throw failure;}
            finally {
                try {
                    List<Path> files=new ArrayList<Path>();try(java.util.stream.Stream<Path> stream=Files.walk(own)){stream.forEach(files::add);}
                    Collections.sort(files,Comparator.reverseOrder());
                    for(Path path:files){if(!path.toRealPath().startsWith(own))throw new IllegalStateException("cleanup escaped model directory");Files.delete(path);}
                }catch(Throwable cleanup){if(primary!=null)primary.addSuppressed(cleanup);else throw cleanup;}
            }
            System.out.println("MODEL_CASE "+number);
        }
        System.out.println("{\"pass\":true,\"modeledOnly\":true,\"cases\":25,\"checks\":"+checks+",\"privateControllerStateInspected\":false,\"nativeOrSuExecuted\":false}");
    }
}
