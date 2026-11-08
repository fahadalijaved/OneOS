package android.content;
public final class ComponentName {
 private final String pkg,cls;public ComponentName(String p,String c){pkg=p;cls=c;}
 public String getPackageName(){return pkg;}public String getClassName(){return cls;}
 public boolean equals(Object value){return value instanceof ComponentName&&pkg.equals(((ComponentName)value).pkg)&&cls.equals(((ComponentName)value).cls);}
 public int hashCode(){return pkg.hashCode()*31+cls.hashCode();}
}
