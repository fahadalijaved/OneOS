package model;
/** Authored fault/counter controls only. No actual Module/Binding private state is touched. */
public final class BootstrapProbe {
 public static java.io.File dataRoot;
 private static java.nio.file.Path repositoryAnchor,dataAnchor;
 public static synchronized void configureFixtureData(java.io.File repository,java.io.File data)throws java.io.IOException {
  if(repositoryAnchor!=null||dataAnchor!=null)throw new java.io.IOException("fixture root already configured");
  java.nio.file.Path repo=repository.toPath().toRealPath(),root=data.toPath().toRealPath();
  if(!root.startsWith(repo.resolve("out")))throw new java.io.IOException("fixture data must be inside actual repository out");
  repositoryAnchor=repo;dataAnchor=root;dataRoot=root.toFile();
 }
 public static java.nio.file.Path fixturePath(String name)throws java.io.IOException {
  java.nio.file.Path repo=repositoryAnchor,root=dataAnchor;
  if(repo==null||root==null)throw new java.io.IOException("fixture roots not configured");
  java.nio.file.Path path=java.nio.file.Paths.get(name).toAbsolutePath().normalize();
  if(!path.startsWith(root))throw new java.io.IOException("outside own configured fixture data root");
  if(java.nio.file.Files.isSymbolicLink(path)||!path.toRealPath().startsWith(root)||!path.toRealPath().startsWith(repo.resolve("out")))throw new java.io.IOException("fixture path alias refused");
  return path;
 }
 public static int uid=1000,apiVersion=102,statUid=0,fileOperations;
 public static boolean closeFault;
 public static volatile Throwable originalFailure,observerFailure;
 public static volatile Runnable originalWork,lookupWork;
 public static volatile String faultStage;
 public static final java.util.concurrent.atomic.AtomicInteger originals=new java.util.concurrent.atomic.AtomicInteger();
 public static int faultFired;
 public static void lookup(){
  if(lookupWork!=null){Runnable work=lookupWork;lookupWork=null;work.run();}
  String stage=faultStage;if(stage==null)return;
  String type="com.appleexploit.oneos.security.authority."+stage;
  for(StackTraceElement element:Thread.currentThread().getStackTrace())if(element.getClassName().equals(type)&&
       (element.getMethodName().equals("captureExisting")||element.getMethodName().equals("prepare"))){
   faultStage=null;faultFired++;raise(observerFailure);return;
  }
 }
 public static void original(){originals.incrementAndGet();}
 public static void afterPhase(){if(originalWork!=null)originalWork.run();raise(originalFailure);}
 private static <T extends Throwable>void sneaky(Throwable failure)throws T{throw(T)failure;}
 public static void raise(Throwable failure){if(failure!=null)BootstrapProbe.<RuntimeException>sneaky(failure);}
}
