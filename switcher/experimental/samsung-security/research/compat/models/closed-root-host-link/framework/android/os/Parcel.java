package android.os;
import java.util.*;
import model.LinkModel;
/** Authored token stream, no native parcel layout/exception codec. */
public final class Parcel {
 private final List<Object> values=new ArrayList<Object>();private int pos;private final boolean borrowed;private boolean recycled;
 private Parcel(boolean borrowed){this.borrowed=borrowed;}
 public static Parcel obtain(){LinkModel.parcelObtains.incrementAndGet();return new Parcel(false);}public static Parcel obtain(IBinder ignored){return obtain();}
 private void live(){if(recycled)throw new AssertionError("Parcel after recycle");}
 private Object next(){live();if(pos==values.size())throw new IllegalArgumentException("truncated parcel");return values.get(pos++);}
 public void writeInterfaceToken(String value){writeString(value);}public void enforceInterface(String value){if(!value.equals(readString()))throw new SecurityException("descriptor");}
 public void enforceNoDataAvail(){live();if(pos!=values.size())throw new IllegalArgumentException("trailing data");}
 public void writeInt(int value){live();values.add(value);}public int readInt(){return(Integer)next();}
 public void writeLong(long value){live();values.add(value);}public long readLong(){return(Long)next();}
 public void writeString(String value){live();values.add(value);}public String readString(){return(String)next();}
 public void writeStrongBinder(IBinder value){live();values.add(value);}public IBinder readStrongBinder(){return(IBinder)next();}
 public void writeNoException(){writeInt(0);}public void readException(){if(readInt()!=0)throw new IllegalStateException("error frame");}
 public void writeException(Exception error){writeInt(1);}public void setDataPosition(int value){pos=value;}public int dataAvail(){return values.size()-pos;}
 public void recycle(){if(borrowed){LinkModel.borrowedRecycles.incrementAndGet();throw new AssertionError("borrowed recycle");}if(recycled)throw new AssertionError("double recycle");recycled=true;LinkModel.parcelRecycles.incrementAndGet();}
 Parcel borrow(){Parcel p=new Parcel(true);p.values.addAll(values);return p;}Parcel blankBorrow(){return new Parcel(true);}
 void receive(Parcel p){values.clear();values.addAll(p.values);pos=0;}
}
