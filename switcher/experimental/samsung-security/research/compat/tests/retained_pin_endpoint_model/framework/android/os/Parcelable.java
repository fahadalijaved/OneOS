package android.os;
/** Authored codec interface, not platform serialization. */
public interface Parcelable {
    int PARCELABLE_WRITE_RETURN_VALUE = 1;
    void writeToParcel(Parcel parcel, int flags);
    int describeContents();
    interface Creator<T> {
        T createFromParcel(Parcel parcel);
        T[] newArray(int size);
    }
}
