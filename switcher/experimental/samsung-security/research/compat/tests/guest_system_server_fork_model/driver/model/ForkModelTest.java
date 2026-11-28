package model;

import java.net.*;
import java.nio.file.*;
import java.lang.reflect.*;
import java.util.*;

/** JDK-only driver. Every case gets new actual helper and fixture static state. */
public final class ForkModelTest {
    public static void main(String[] args) throws Throwable {
        if(args.length!=4)throw new IllegalArgumentException("program, fixtures, own data, repo");
        Path program=Paths.get(args[0]).toRealPath(), fixtures=Paths.get(args[1]).toRealPath();
        Path data=Paths.get(args[2]).toRealPath(), repo=Paths.get(args[3]).toRealPath();
        if(!data.startsWith(repo.resolve("out")) || !program.startsWith(repo.resolve("out")) || !fixtures.startsWith(repo.resolve("out")))
            throw new IllegalArgumentException("repo-owned inputs and data required");
        if(!Files.isRegularFile(repo.resolve("tools/test_guest_system_server_fork.py")))
            throw new IllegalArgumentException("normal repository runner marker required before fixture writes");
        int checks=0;
        for(int number=0;number<16;number++) {
            Path own=data.resolve("case-"+number);Files.createDirectory(own);
            Throwable primary=null;
            try(URLClassLoader loader=new URLClassLoader(new URL[]{program.toUri().toURL(),fixtures.toUri().toURL()},ClassLoader.getPlatformClassLoader())) {
                Class<?> dispatcher=Class.forName("com.android.internal.os.ForkModelDispatcher",true,loader);
                try {checks+=((Integer)dispatcher.getMethod("runCase",int.class,String.class,String.class).invoke(null,number,repo.toString(),own.toString())).intValue();}
                catch(InvocationTargetException failure) {throw failure.getCause();}
            } catch(Throwable failure) {primary=failure;throw failure;}
            finally {
                try {
                    List<Path> paths=new ArrayList<Path>();
                    try(java.util.stream.Stream<Path> stream=Files.walk(own)){stream.forEach(paths::add);}
                    Collections.sort(paths,Comparator.reverseOrder());
                    for(Path path:paths) {
                        if(!path.toRealPath().startsWith(own))throw new IllegalStateException("cleanup escaped fixture");
                        Files.delete(path);
                    }
                } catch(Throwable cleanup) {if(primary!=null)primary.addSuppressed(cleanup);else throw cleanup;}
            }
            System.out.println("MODEL_CASE "+number);
        }
        try(java.util.stream.Stream<Path> stream=Files.list(data)) {
            if(stream.findAny().isPresent())throw new AssertionError("fixture data remained");
        }
        System.out.println("{\"pass\":true,\"modeledOnly\":true,\"cases\":16,\"checks\":"+checks+",\"privateHelperStateInspected\":false,\"runnableInvocations\":0}");
    }
}
