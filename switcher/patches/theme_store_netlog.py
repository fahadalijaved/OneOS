"""Debug build of ColorOS's Theme Store (KeKeThemeSpace): log every OkHttp request and its reply.

The Theme Store opens on every Galaxy since 0.4.47/0.4.48 but shows "No Data": OPPO's server answers
nothing we can see. This adds Loneos/ts/NetLog; (an okhttp3.Interceptor) to every OkHttpClient the app
builds (OkHttpClient$Builder.build() calls NetLog.attach(builder), which adds it once) and logs to
logcat, tag OneOSTheme, in 3000-character pieces:
  >> METHOD URL | request headers (not Authorization or cookies)
  << CODE URL | response headers
  << body CONTENT-TYPE N bytes: the text (json, text, xml) or base64 of the first 16 KB, from
     peekBody(64 KB), so the app still reads the whole body
  !! URL exception, when the call fails (rethrown)
For a test-channel set only (owner, 2026-11-05: "build test apk for me ... I can log what you want");
the OneOS report's logcat carries it, with personal values removed by the report collector.

Usage: theme_store_netlog.py <smali root dir of the decoded APK>
Prints the smali_* directory it changed.
"""
import os
import re
import sys

BUILDER = os.path.join("okhttp3", "OkHttpClient$Builder.smali")
HOOK = "    invoke-static {p0}, Loneos/ts/NetLog;->attach(Lokhttp3/OkHttpClient$Builder;)V\n"

NETLOG = r""".class public final Loneos/ts/NetLog;
.super Ljava/lang/Object;
.source "NetLog.smali"

# interfaces
.implements Lokhttp3/Interceptor;


.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static attach(Lokhttp3/OkHttpClient$Builder;)V
    .locals 4
    :try_start
    invoke-virtual {p0}, Lokhttp3/OkHttpClient$Builder;->interceptors()Ljava/util/List;
    move-result-object v0
    invoke-interface {v0}, Ljava/util/List;->iterator()Ljava/util/Iterator;
    move-result-object v1
    :loop
    invoke-interface {v1}, Ljava/util/Iterator;->hasNext()Z
    move-result v2
    if-eqz v2, :add
    invoke-interface {v1}, Ljava/util/Iterator;->next()Ljava/lang/Object;
    move-result-object v2
    instance-of v3, v2, Loneos/ts/NetLog;
    if-eqz v3, :loop
    return-void
    :add
    new-instance v2, Loneos/ts/NetLog;
    invoke-direct {v2}, Loneos/ts/NetLog;-><init>()V
    invoke-virtual {p0, v2}, Lokhttp3/OkHttpClient$Builder;->addInterceptor(Lokhttp3/Interceptor;)Lokhttp3/OkHttpClient$Builder;
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch
    return-void
    :catch
    move-exception v0
    return-void
.end method

.method public static log(Ljava/lang/String;)V
    .locals 5
    if-nez p0, :ok
    return-void
    :ok
    const-string v0, "OneOSTheme"
    invoke-virtual {p0}, Ljava/lang/String;->length()I
    move-result v1
    const/4 v2, 0x0
    :loop
    if-ge v2, v1, :done
    add-int/lit16 v3, v2, 0xbb8
    if-le v3, v1, :cut
    move v3, v1
    :cut
    invoke-virtual {p0, v2, v3}, Ljava/lang/String;->substring(II)Ljava/lang/String;
    move-result-object v4
    invoke-static {v0, v4}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    move v2, v3
    goto :loop
    :done
    return-void
.end method

.method public static headers(Lokhttp3/Headers;)Ljava/lang/String;
    .locals 6
    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    if-eqz p0, :out
    invoke-virtual {p0}, Lokhttp3/Headers;->size()I
    move-result v1
    const/4 v2, 0x0
    :loop
    if-ge v2, v1, :out
    invoke-virtual {p0, v2}, Lokhttp3/Headers;->name(I)Ljava/lang/String;
    move-result-object v3
    invoke-virtual {v3}, Ljava/lang/String;->toLowerCase()Ljava/lang/String;
    move-result-object v4
    const-string v5, "authorization"
    invoke-virtual {v4, v5}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v5
    if-nez v5, :skip
    const-string v5, "cookie"
    invoke-virtual {v4, v5}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v5
    if-nez v5, :skip
    invoke-virtual {v0, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v5, ": "
    invoke-virtual {v0, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {p0, v2}, Lokhttp3/Headers;->value(I)Ljava/lang/String;
    move-result-object v4
    invoke-virtual {v0, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v5, "; "
    invoke-virtual {v0, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    :skip
    add-int/lit8 v2, v2, 0x1
    goto :loop
    :out
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v1
    return-object v1
.end method

.method public intercept(Lokhttp3/Interceptor$Chain;)Lokhttp3/Response;
    .locals 8
    invoke-interface {p1}, Lokhttp3/Interceptor$Chain;->request()Lokhttp3/Request;
    move-result-object v0
    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    const-string v2, ">> "
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Lokhttp3/Request;->method()Ljava/lang/String;
    move-result-object v2
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v2, " "
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Lokhttp3/Request;->url()Lokhttp3/HttpUrl;
    move-result-object v2
    invoke-virtual {v2}, Ljava/lang/Object;->toString()Ljava/lang/String;
    move-result-object v7
    invoke-virtual {v1, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v2, " | "
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Lokhttp3/Request;->headers()Lokhttp3/Headers;
    move-result-object v2
    invoke-static {v2}, Loneos/ts/NetLog;->headers(Lokhttp3/Headers;)Ljava/lang/String;
    move-result-object v2
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v2
    invoke-static {v2}, Loneos/ts/NetLog;->log(Ljava/lang/String;)V
    :try_start_call
    invoke-interface {p1, v0}, Lokhttp3/Interceptor$Chain;->proceed(Lokhttp3/Request;)Lokhttp3/Response;
    move-result-object v3
    :try_end_call
    .catch Ljava/io/IOException; {:try_start_call .. :try_end_call} :catch_call
    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    const-string v2, "<< "
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v3}, Lokhttp3/Response;->code()I
    move-result v2
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;
    const-string v2, " "
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v2, " | "
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v3}, Lokhttp3/Response;->headers()Lokhttp3/Headers;
    move-result-object v2
    invoke-static {v2}, Loneos/ts/NetLog;->headers(Lokhttp3/Headers;)Ljava/lang/String;
    move-result-object v2
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v2
    invoke-static {v2}, Loneos/ts/NetLog;->log(Ljava/lang/String;)V
    :try_start_body
    const-wide/32 v4, 0x10000
    invoke-virtual {v3, v4, v5}, Lokhttp3/Response;->peekBody(J)Lokhttp3/ResponseBody;
    move-result-object v6
    invoke-virtual {v6}, Lokhttp3/ResponseBody;->contentType()Lokhttp3/MediaType;
    move-result-object v2
    const-string v0, ""
    if-eqz v2, :ct_done
    invoke-virtual {v2}, Ljava/lang/Object;->toString()Ljava/lang/String;
    move-result-object v0
    :ct_done
    invoke-virtual {v6}, Lokhttp3/ResponseBody;->bytes()[B
    move-result-object v2
    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    const-string v4, "<< body "
    invoke-virtual {v1, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v4, " "
    invoke-virtual {v1, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    array-length v4, v2
    invoke-virtual {v1, v4}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;
    const-string v4, " bytes: "
    invoke-virtual {v1, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v4, "json"
    invoke-virtual {v0, v4}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v4
    if-nez v4, :text
    const-string v4, "text"
    invoke-virtual {v0, v4}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v4
    if-nez v4, :text
    const-string v4, "xml"
    invoke-virtual {v0, v4}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v4
    if-nez v4, :text
    array-length v4, v2
    const/16 v5, 0x4000
    if-le v4, v5, :b64
    invoke-static {v2, v5}, Ljava/util/Arrays;->copyOf([BI)[B
    move-result-object v2
    :b64
    const/4 v4, 0x2
    invoke-static {v2, v4}, Landroid/util/Base64;->encodeToString([BI)Ljava/lang/String;
    move-result-object v4
    const-string v5, "base64 "
    invoke-virtual {v1, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    goto :emit
    :text
    new-instance v4, Ljava/lang/String;
    const-string v5, "UTF-8"
    invoke-direct {v4, v2, v5}, Ljava/lang/String;-><init>([BLjava/lang/String;)V
    invoke-virtual {v1, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    :emit
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v4
    invoke-static {v4}, Loneos/ts/NetLog;->log(Ljava/lang/String;)V
    :try_end_body
    .catch Ljava/lang/Throwable; {:try_start_body .. :try_end_body} :catch_body
    :ret
    return-object v3
    :catch_body
    move-exception v2
    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    const-string v4, "<< body not read: "
    invoke-virtual {v1, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2}, Ljava/lang/Object;->toString()Ljava/lang/String;
    move-result-object v4
    invoke-virtual {v1, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v4
    invoke-static {v4}, Loneos/ts/NetLog;->log(Ljava/lang/String;)V
    goto :ret
    :catch_call
    move-exception v2
    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    const-string v4, "!! "
    invoke-virtual {v1, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v4, " "
    invoke-virtual {v1, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2}, Ljava/lang/Object;->toString()Ljava/lang/String;
    move-result-object v4
    invoke-virtual {v1, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v4
    invoke-static {v4}, Loneos/ts/NetLog;->log(Ljava/lang/String;)V
    throw v2
.end method
"""


def main(root):
    hits = []
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d, BUILDER)
        if d.startswith("smali") and os.path.isfile(p):
            hits.append((d, p))
    if len(hits) != 1:
        sys.exit(f"expected one {BUILDER}, found {len(hits)}")
    smali_dir, path = hits[0]
    s = open(path).read()
    if "Loneos/ts/NetLog;" in s:
        sys.exit(f"{path}: already logs")
    m = re.search(r"\.method public final build\(\)Lokhttp3/OkHttpClient;\n(\s*\.locals \d+\n)"
                  r"((?:\s*\.annotation[^\n]*\n(?:[^\n]*\n)*?\s*\.end annotation\n)*)", s)
    if not m:
        sys.exit(f"{path}: build() not found as expected")
    s = s[:m.end()] + HOOK + s[m.end():]
    open(path, "w").write(s)
    out = os.path.join(root, smali_dir, "oneos", "ts")
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "NetLog.smali"), "w").write(NETLOG)
    print(smali_dir)
    print(f"{smali_dir}: OkHttpClient$Builder.build() attaches Loneos/ts/NetLog; (tag OneOSTheme)", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
