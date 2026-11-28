package android.os;
/** Authored hierarchy declaration only, no Android parcel implementation. */
public interface Parcelable {
    void writeToParcel(Parcel parcel,int flags);
    int describeContents();
}
