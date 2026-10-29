package com.fahadali.oneos.report

import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.model.ReportRecord
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

    class Failed(message: String) : IOException(message)

    /** [progress]: bytes sent so far of the zip's size. */
    fun send(record: ReportRecord, zip: File?, progress: (sent: Long, total: Long) -> Unit = { _, _ -> }) {
        check(available) { "this build has no report service" }
        val total = zip?.length() ?: 0L
        val parts = Reports.parts(total)
        check(record.logs == null || record.logs!!.parts == parts) { "the record names ${record.logs?.parts} parts, the zip has $parts" }
        var sent = 0L
        for (i in 0 until parts) {
            sendPart(record.reportId, zip!!, i, parts) { n -> progress(sent + n, total) }
            sent += partLength(total, i)
        }
        val body = record.toJson().toByteArray(Charsets.UTF_8)
        var (code, text) = post("/v1/report", "application/json", body.size.toLong()) { it.write(body) }
        if (code == 409 && zip != null) {
            // The service did not see a part yet: send the ones it names, then the record again.
            Regex("\\d+").findAll(text.substringAfter("missing")).map { it.value.toInt() }.filter { it in 0 until parts }.forEach { i ->
                sendPart(record.reportId, zip, i, parts) {}
            }
            post("/v1/report", "application/json", body.size.toLong()) { it.write(body) }.let { (c, t) -> code = c; text = t }
        }
        if (code != 200) throw Failed(message(code, text))
        progress(total, total)
    }

    private fun partLength(total: Long, i: Int): Long = minOf(Reports.PART_BYTES.toLong(), total - i.toLong() * Reports.PART_BYTES)

    private fun sendPart(id: String, zip: File, i: Int, n: Int, progress: (Long) -> Unit) {
        val length = partLength(zip.length(), i)
        var last: Exception? = null
        repeat(3) { attempt ->
            try {
                val (code, text) = post("/v1/part?id=$id&i=$i&n=$n", "application/octet-stream", length) { out ->
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
                if (code in 400..499 && code != 429) throw Failed(message(code, text))
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

    private fun post(path: String, type: String, length: Long, body: (java.io.OutputStream) -> Unit): Pair<Int, String> {
        val c = URL(BuildConfig.REPORT_URL + path).openConnection() as HttpURLConnection
        try {
            c.requestMethod = "POST"
            c.doOutput = true
            c.connectTimeout = 20_000
            c.readTimeout = 120_000
            c.setFixedLengthStreamingMode(length)
            c.setRequestProperty("Content-Type", type)
            c.setRequestProperty("X-OneOS-Key", BuildConfig.REPORT_KEY)
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
            429 -> "Too many reports from this network right now: try again in a minute"
            else -> "The report service answered $code${reason?.let { " ($it)" } ?: ""}"
        }
    }
}
