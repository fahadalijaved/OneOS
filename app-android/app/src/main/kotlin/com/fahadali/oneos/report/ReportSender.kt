package com.fahadali.oneos.report

import com.fahadali.oneos.BuildConfig
import android.os.Build
import com.fahadali.oneos.core.model.CustomRomRule
import com.fahadali.oneos.core.model.ReportRecord
import com.fahadali.oneos.core.model.ReportReply
import com.fahadali.oneos.core.model.Reports
import java.io.File
import java.io.IOException
import java.io.RandomAccessFile
import java.net.HttpURLConnection
import java.net.URL

/**
 * Send to the OneOS team (0.4.29): the report service (reports/worker.js).
 * The zip goes first, in parts of [Reports.PART_BYTES] (POST /v1/part), then
 * the record (POST /v1/report), which the service takes only once every part
 * is there; a part it reports missing is sent again once. Every request is
 * HTTPS with the build's upload-only key ([BuildConfig.REPORT_KEY]); nothing
 * is read back but the service's answer. Runs on the caller's thread.
 */
object ReportSender {
    /** This build knows the service (an APK built without its address shows no Send). */
    val available: Boolean
        get() = BuildConfig.REPORT_URL.startsWith("https://") && BuildConfig.REPORT_KEY.isNotEmpty()

    open class Failed(message: String) : IOException(message)

    /** 0.5.16 (owner): the service wants a Telegram sign-in (none, or the pass is no longer valid). */
    class NeedsSignIn(message: String) : Failed(message)

    /** 0.5.16 (owner): the signed-in account is not in the OneOS group (or is banned from it). */
    class NotMember(message: String) : Failed(message)

    /** The OneOS Telegram group. */
    const val GROUP_URL = "https://t.me/TheoneOS"

    /**
     * 0.5.24: reports are posted from the user's own Telegram into the private OneOSReports group (files only,
     * slow mode; reports/tgbot.py checks OneOS-group membership, files each report and replies). This link asks to
     * join; the bot lets members of the OneOS group in. The Telegram apps tried first, in this order, for Share.
     */
    const val REPORTS_INVITE = "https://t.me/+mKhV2d_lcJs4YjQ8"
    val TELEGRAM_PACKAGES = listOf("org.telegram.messenger", "org.telegram.messenger.web", "org.thunderdog.challegram", "com.fahadali.xgram")

    /** Sign-in (0.5.16): the code and the t.me link to open; the user taps Start there. */
    fun signin(): Pair<String, String> {
        check(available) { "this build has no report service" }
        val (code, text) = post("/v1/signin", "application/json", 0) {}
        if (code != 200) throw Failed(message(code, text))
        return ReportReply.signin(text) ?: throw Failed("The report service gave no sign-in link")
    }

    /** Asks whether the user pressed Start for [code]. */
    fun claim(code: String): ReportReply.Claim {
        check(available) { "this build has no report service" }
        val (status, text) = post("/v1/claim?code=" + java.net.URLEncoder.encode(code, "UTF-8"), "application/json", 0) {}
        return ReportReply.claim(status, text) ?: throw Failed(message(status, text))
    }

    /** The refusal as the exception the screen reacts to. */
    private fun failure(code: Int, text: String): Failed = when (ReportReply.refusal(code, text)) {
        ReportReply.Refusal.JOIN -> NotMember(message(code, text))
        ReportReply.Refusal.SIGN_IN -> NeedsSignIn(message(code, text))
        null -> Failed(message(code, text))
    }

    /**
     * 0.4.74 (owner): a custom ROM sends nothing, findings included ([CustomRomRule]); this is
     * why, for the screens that would show Send. Null on stock One UI and in the other systems.
     * Read from this phone's own properties (no getprop process, so safe on the main thread).
     */
    val refusal: String? by lazy {
        runCatching {
            val get = Class.forName("android.os.SystemProperties").getMethod("get", String::class.java)
            fun prop(k: String) = (get.invoke(null, k) as? String).orEmpty()
            CustomRomRule.check(
                CustomRomRule.Signals(
                    model = prop("ro.product.model").ifEmpty { Build.MODEL.orEmpty() },
                    bootloader = Build.BOOTLOADER.orEmpty().takeIf { it.isNotEmpty() && it != Build.UNKNOWN } ?: prop("ro.bootloader"),
                    vendorModel = prop("ro.product.vendor.model"),
                    oneUiRaw = prop("ro.build.version.oneui"),
                ),
            )?.detail
        }.getOrNull()
    }

    /** Send is offered: this build has the service and the phone is not a custom ROM. */
    val offered: Boolean get() = available && refusal == null

    /** [progress]: bytes sent so far of the zip's size. */
    fun send(record: ReportRecord, zip: File?, pass: String? = null, progress: (sent: Long, total: Long) -> Unit = { _, _ -> }) {
        check(available) { "this build has no report service" }
        refusal?.let { throw Failed(it) }
        val total = zip?.length() ?: 0L
        val parts = Reports.parts(total)
        check(record.logs == null || record.logs!!.parts == parts) { "the record names ${record.logs?.parts} parts, the zip has $parts" }
        var sent = 0L
        for (i in 0 until parts) {
            sendPart(record.reportId, zip!!, i, parts, pass) { n -> progress(sent + n, total) }
            sent += partLength(total, i)
        }
        val body = record.toJson().toByteArray(Charsets.UTF_8)
        var (code, text) = post("/v1/report", "application/json", body.size.toLong(), pass) { it.write(body) }
        if (code == 409 && zip != null) {
            // The service did not see a part yet: send the ones it names, then the record again.
            Regex("\\d+").findAll(text.substringAfter("missing")).map { it.value.toInt() }.filter { it in 0 until parts }.forEach { i ->
                sendPart(record.reportId, zip, i, parts, pass) {}
            }
            post("/v1/report", "application/json", body.size.toLong(), pass) { it.write(body) }.let { (c, t) -> code = c; text = t }
        }
        if (code != 200) throw failure(code, text)
        progress(total, total)
    }

    private fun partLength(total: Long, i: Int): Long = minOf(Reports.PART_BYTES.toLong(), total - i.toLong() * Reports.PART_BYTES)

    private fun sendPart(id: String, zip: File, i: Int, n: Int, pass: String?, progress: (Long) -> Unit) {
        val length = partLength(zip.length(), i)
        var last: Exception? = null
        repeat(3) { attempt ->
            try {
                val (code, text) = post("/v1/part?id=$id&i=$i&n=$n", "application/octet-stream", length, pass) { out ->
                    RandomAccessFile(zip, "r").use { f ->
                        f.seek(i.toLong() * Reports.PART_BYTES)
                        val buf = ByteArray(64 * 1024)
                        var left = length
                        var done = 0L
                        while (left > 0) {
                            val r = f.read(buf, 0, minOf(buf.size.toLong(), left).toInt())
                            if (r < 0) throw IOException("the zip ended early")
                            out.write(buf, 0, r)
                            left -= r
                            done += r
                            progress(done)
                        }
                    }
                }
                if (code == 200) return
                // A refusal (a bad key, a bad request) does not get better by retrying.
                if (code in 400..499 && code != 429) throw failure(code, text)
                last = Failed(message(code, text))
            } catch (e: Failed) {
                throw e
            } catch (e: IOException) {
                last = e
            }
            Thread.sleep(2_000L * (attempt + 1))
        }
        throw last ?: Failed("part ${i + 1} of $n was not sent")
    }

    internal fun post(path: String, type: String, length: Long, pass: String? = null, body: (java.io.OutputStream) -> Unit): Pair<Int, String> {
        val c = URL(BuildConfig.REPORT_URL + path).openConnection() as HttpURLConnection
        try {
            c.requestMethod = "POST"
            c.doOutput = true
            c.connectTimeout = 20_000
            c.readTimeout = 120_000
            c.setFixedLengthStreamingMode(length)
            c.setRequestProperty("Content-Type", type)
            c.setRequestProperty("X-OneOS-Key", BuildConfig.REPORT_KEY)
            if (!pass.isNullOrEmpty()) c.setRequestProperty("X-OneOS-Pass", pass)
            c.outputStream.use(body)
            val code = c.responseCode
            val text = (if (code < 400) c.inputStream else c.errorStream)?.use { it.readBytes().decodeToString().take(2_000) }.orEmpty()
            return code to text
        } finally {
            c.disconnect()
        }
    }

    private fun message(code: Int, text: String): String {
        val reason = Regex("\"error\"\\s*:\\s*\"([^\"]{1,200})\"").find(text)?.groupValues?.get(1)
        return when (code) {
            403 -> reason ?: "The report service refused this report"
            503 -> "Telegram could not be checked right now: try again in a minute"
            429 -> "Too many reports from this network right now: try again in a minute"
            else -> "The report service answered $code${reason?.let { " ($it)" } ?: ""}"
        }
    }
}
