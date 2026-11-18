package com.android.internal.widget;

/** Pure canonical typed response predicates, with explicitly authored fault hooks. */
public final class VerifyCredentialResponse implements android.os.Parcelable {
    private final int code;
    private final boolean timeout;
    public Runnable onMatched, onTimeout, onOther;
    public Error failMatched, failTimeout, failOther;
    public int matchedReads, timeoutReads, otherReads;
    private VerifyCredentialResponse(int code,boolean timeout) {this.code=code;this.timeout=timeout;}
    public static VerifyCredentialResponse modelCreate(int code,boolean timeout) {return new VerifyCredentialResponse(code,timeout);}
    public boolean isMatched() {
        matchedReads++;if(onMatched!=null)onMatched.run();if(failMatched!=null)throw failMatched;return code==0;
    }
    public boolean hasTimeout() {
        timeoutReads++;if(onTimeout!=null)onTimeout.run();if(failTimeout!=null)throw failTimeout;return timeout;
    }
    public boolean isOtherError() {
        otherReads++;if(onOther!=null)onOther.run();if(failOther!=null)throw failOther;return code==-1;
    }
    public void writeToParcel(android.os.Parcel parcel,int flags) {throw new AssertionError("no wire execution");}
    public int describeContents() {return 0;}
}
