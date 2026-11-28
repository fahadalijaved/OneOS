package android.content.pm;
public final class SigningInfo {public Signature[] current;public boolean multiple;public boolean hasMultipleSigners(){return multiple;}public Signature[] getApkContentsSigners(){return current;}public Signature[] getSigningCertificateHistory(){return current;}}
