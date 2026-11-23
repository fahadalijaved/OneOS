package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.OneiosFix
import com.fahadali.oneos.core.model.OneiosKind
import com.fahadali.oneos.core.model.OneiosMessage
import com.fahadali.oneos.core.model.OneiosPart
import com.fahadali.oneos.core.model.OneiosPlain
import com.fahadali.oneos.core.model.OneiosStaged
import com.fahadali.oneos.core.model.Units

/**
 * The iOS 27 (OneiOS) flow as its screens show it (docs/oneios.md, "In the app"), in the steps and
 * marks of the Android guests' Setting up: check this phone, get the runtime, import the image set,
 * iOS's data, the last check before the switch. Read from what root's `status` printed
 * ([OneiosStatus]: what is staged, the session, and `ready` with the preflight's one refusal), the job
 * that runs or ran last, and what the app checked when it staged each package ([OneiosStaged]).
 * Nothing here asks root anything, and nothing changes what root checks: the switch is still root's
 * `switch` verb with its own preflight.
 */
object OneiosFlow {
    enum class Step { PHONE, RUNTIME, IMAGE, DATA, READY }

    /** [NEXT]: waiting for the user (the step's action is the screen's button); [RUNNING]: a job runs it now. */
    enum class Mark { PENDING, NEXT, RUNNING, DONE, FAILED }

    /**
     * A package's check now, by root's status: every file is there, root's, and the one root hashed at staging
     * (its device, inode, size and time; status hashes nothing, so it answers at once). The switch's own preflight
     * hashes them again before it changes anything. [NOT_CHECKED]: the preflight stopped before it got there (or
     * has not run).
     */
    enum class Check { NOT_STAGED, PASSED, FAILED, NOT_CHECKED }

    /** The one thing to do now: the screen's main button. */
    enum class Next {
        WAIT, NOT_THIS_PHONE, CHECK_AGAIN, GET_RUNTIME, DOWNLOAD_RUNTIME, IMPORT_RUNTIME, IMPORT_IMAGE,
        BACK_TO_ONE_UI, REMOVE, SESSION_LOGS, SWITCH;

        companion object {
            fun of(fix: OneiosFix): Next = when (fix) {
                OneiosFix.NONE, OneiosFix.CHECK_AGAIN -> CHECK_AGAIN
                OneiosFix.GET_RUNTIME -> GET_RUNTIME
                OneiosFix.DOWNLOAD_RUNTIME -> DOWNLOAD_RUNTIME
                OneiosFix.IMPORT_RUNTIME -> IMPORT_RUNTIME
                OneiosFix.IMPORT_IMAGE -> IMPORT_IMAGE
                OneiosFix.BACK_TO_ONE_UI -> BACK_TO_ONE_UI
                OneiosFix.REMOVE -> REMOVE
                OneiosFix.SESSION_LOGS -> SESSION_LOGS
            }
        }
    }

    /** What the app runs for the iOS system (one at a time). */
    enum class Job(val kind: OneiosKind? = null) {
        CHECK, DOWNLOAD_RUNTIME(OneiosKind.RUNTIME), IMPORT_RUNTIME(OneiosKind.RUNTIME), IMPORT_IMAGE(OneiosKind.IMAGE), SWITCH, RETURN, REMOVE,

        /** The prelink inputs into the stage: the app's kb/ assets and the Apple kernelcache the user hands over. */
        STAGE_KB,

        /** The phone-built kernel.kc in place (root's `finish kernel`), with its hashes, lists and receipt. */
        FINISH_KERNEL,

        /** Back to the kept kernel set (root's `restore kernel`). */
        RESTORE_KERNEL;

        val copies: Boolean get() = kind != null
    }

    data class Input(
        /** Root's last `status`; null until it answered once. */
        val status: OneiosStatus?,
        /** This phone takes the system; null until read. */
        val offered: Boolean?,
        /** The job that runs now; null when none. */
        val running: Job? = null,
        /** The job that ran last, and its failure (null: it worked, or none ran). */
        val last: Job? = null,
        val failure: String? = null,
        val runtimeRecord: OneiosStaged? = null,
        val imageRecord: OneiosStaged? = null,
        /**
         * The phone row's name for a phone that takes the system but is not the one it is mainly tested on (the
         * Galaxy A56: "Galaxy A56, iOS 16.5, untested there"); null: the Galaxy S24 Ultra's row, as before.
         */
        val phone: String? = null,
    )

    data class Row(val step: Step, val mark: Mark, val line: String?)

    data class View(
        val rows: List<Row>,
        val runtime: Check,
        val image: Check,
        /** What stops the next step, in plain words (the last job's failure first, then the preflight's); null when nothing does. */
        val problem: OneiosMessage?,
        val next: Next,
        /** Root's last preflight passed and nothing else stops the switch: Switch to iOS 27 is the next step. */
        val ready: Boolean,
        /** The step to do now (the first not done), and the one after it; null when every step is done. */
        val current: Step?,
        val then: Step?,
        /** "Runtime 0.1.6 · 21 files, 12 MB · checked" and the image set's, data's, for the screens' state. */
        val runtimeLine: String?,
        val imageLine: String?,
        val dataLine: String?,
    ) {
        fun row(step: Step): Row = rows.first { it.step == step }
        fun mark(step: Step): Mark = row(step).mark
    }

    fun of(i: Input): View {
        val st = i.status
        val failure = i.failure?.takeIf { it.isNotBlank() }?.let { OneiosPlain.refused(it, i.last?.kind) }
        // No stage at all: the launcher answers `stage none` and no `ready` line; that is the first step, not a fault.
        val refusal = when {
            // Root has said what is staged; its preflight still runs (OneiosStatus.partial): no answer yet.
            st == null || st.ready || st.checking -> null
            st?.staged == false -> OneiosPlain.refused("OneiOS is not set up on this phone yet")
            else -> OneiosPlain.refused(st?.notReady.orEmpty())
        }
        val runtimeCheck = check(st, st?.runtime != null, refusal, OneiosPart.RUNTIME)
        val imageCheck = check(st, st?.image != null, refusal, OneiosPart.IMAGE)
        val runtimeRecord = i.runtimeRecord?.takeIf { r -> st?.runtime?.let { r.kind == OneiosKind.RUNTIME && r.matches(it.version) } == true }
        val imageRecord = i.imageRecord?.takeIf { r -> st?.image?.let { r.kind == OneiosKind.IMAGE && r.matches(it.version, it.build) } == true }
        fun failedBy(vararg jobs: Job) = failure?.takeIf { i.last in jobs }

        val phone = when {
            st == null && i.running == Job.CHECK -> Row(Step.PHONE, Mark.RUNNING, "Asking root what is on this phone…")
            i.offered == false -> Row(Step.PHONE, Mark.DONE, "warned: OneiOS is mainly tested and working on the Galaxy S24 Ultra; on this phone it may be unstable")
            // A check whose own `status` failed: what is shown of the stage is the last answer, not this one.
            failedBy(Job.CHECK) != null || (st == null && failure != null) -> Row(Step.PHONE, Mark.FAILED, failure!!.line)
            st == null -> Row(Step.PHONE, Mark.PENDING, null)
            refusal?.part == OneiosPart.PHONE -> Row(Step.PHONE, Mark.FAILED, refusal.line)
            else -> Row(Step.PHONE, Mark.DONE, "${i.phone ?: "Galaxy S24 Ultra"} · root allowed")
        }
        val phoneDone = phone.mark == Mark.DONE

        fun packageRow(step: Step, staged: Boolean, check: Check, jobs: Array<Job>, line: String?, before: Boolean): Row = when {
            i.running in jobs -> Row(step, Mark.RUNNING, null)
            failedBy(*jobs) != null -> Row(step, Mark.FAILED, failure!!.line)
            !phoneDone -> Row(step, if (staged) Mark.DONE else Mark.PENDING, line)
            check == Check.FAILED -> Row(step, Mark.FAILED, refusal?.line)
            staged -> Row(step, Mark.DONE, line)
            before -> Row(step, Mark.NEXT, null)
            else -> Row(step, Mark.PENDING, null)
        }
        val runtimeLine = st?.runtime?.let { runtimeLine(it, runtimeCheck, runtimeRecord) }
        val imageLine = st?.image?.let { imageLine(it, imageCheck, imageRecord) }
        val runtime = packageRow(Step.RUNTIME, st?.runtime != null, runtimeCheck, arrayOf(Job.DOWNLOAD_RUNTIME, Job.IMPORT_RUNTIME), runtimeLine, true)
        val image = packageRow(
            Step.IMAGE, st?.image != null, imageCheck, arrayOf(Job.IMPORT_IMAGE), imageLine,
            runtime.mark == Mark.DONE,
        )
        val filesDone = runtime.mark == Mark.DONE && image.mark == Mark.DONE
        val dataLine = st?.let { dataLine(it) }
        val data = Row(Step.DATA, if (filesDone) Mark.DONE else Mark.PENDING, if (filesDone) dataLine else null)
        val lastCheck = when {
            i.running == Job.SWITCH -> Row(Step.READY, Mark.RUNNING, "Checking every file and the phone once more…")
            i.running == Job.CHECK && filesDone -> Row(Step.READY, Mark.RUNNING, "Root checks the staged files and the phone…")
            failedBy(Job.SWITCH) != null && filesDone -> Row(Step.READY, Mark.FAILED, failure!!.line)
            !filesDone -> Row(Step.READY, Mark.PENDING, null)
            st?.ready == true -> Row(Step.READY, Mark.DONE, "Ready to switch")
            refusal != null && refusal.part != OneiosPart.PHONE -> Row(Step.READY, Mark.FAILED, refusal.line)
            else -> Row(Step.READY, Mark.NEXT, null)
        }
        val rows = listOf(phone, runtime, image, data, lastCheck)

        // The problem to show: the job just run first (what the user did), else the preflight's,
        // unless it only says what the next step is and that step is already on the screen.
        val problem = failure?.takeIf { i.running == null } ?: refusal
        val next = when {
            i.running != null -> Next.WAIT
            st?.sessionOpen == true -> Next.BACK_TO_ONE_UI
            st == null -> Next.CHECK_AGAIN
            phone.mark == Mark.FAILED -> Next.of(problem?.fix ?: OneiosFix.CHECK_AGAIN)
            runtime.mark != Mark.DONE -> nextFor(problem, OneiosPart.RUNTIME, Next.GET_RUNTIME)
            image.mark != Mark.DONE -> nextFor(problem, OneiosPart.IMAGE, Next.IMPORT_IMAGE)
            st?.ready == true && lastCheck.mark == Mark.DONE -> Next.SWITCH
            else -> Next.of(problem?.fix ?: OneiosFix.CHECK_AGAIN)
        }
        val open = rows.filter { it.mark != Mark.DONE }
        return View(
            rows = rows,
            runtime = runtimeCheck,
            image = imageCheck,
            problem = problem,
            next = next,
            ready = next == Next.SWITCH,
            current = open.firstOrNull()?.step,
            then = open.getOrNull(1)?.step,
            runtimeLine = runtimeLine,
            imageLine = imageLine,
            dataLine = dataLine,
        )
    }

    /** The fix a problem of [part] offers, else the step's own action. */
    private fun nextFor(problem: OneiosMessage?, part: OneiosPart, otherwise: Next): Next =
        problem?.takeIf { it.part == part && it.fix != OneiosFix.NONE && it.fix != OneiosFix.CHECK_AGAIN }?.let { Next.of(it.fix) } ?: otherwise

    /**
     * What root's preflight says of a package: it checks this phone and root, then the runtime, then
     * the image set, then the rest, and stops at the first refusal; so a refusal of a later part
     * means this one passed.
     */
    fun check(status: OneiosStatus?, staged: Boolean, refusal: OneiosMessage?, part: OneiosPart): Check = when {
        status == null -> Check.NOT_CHECKED
        !staged -> Check.NOT_STAGED
        status.ready -> Check.PASSED
        refusal == null -> Check.NOT_CHECKED
        refusal.part == part -> Check.FAILED
        refusal.part != OneiosPart.OTHER && refusal.part.ordinal > part.ordinal -> Check.PASSED
        else -> Check.NOT_CHECKED
    }

    fun checkWords(check: Check, kind: OneiosKind): String = when (check) {
        Check.PASSED -> "every file as staged"
        Check.FAILED -> "check failed"
        Check.NOT_CHECKED -> "not checked yet"
        Check.NOT_STAGED -> "not on this phone"
    }

    /** "0.1.6 · 21 files, 12 MB · every file as staged" (the size only from the app's own record of this version). */
    fun runtimeLine(r: OneiosStatus.Runtime, check: Check, record: OneiosStaged?): String = listOfNotNull(
        "Version ${r.version}",
        record?.let { "${it.files} files, ${Units.bytes(it.bytes)}" },
        if (r.placeholder) "placeholder, can't start iOS" else checkWords(check, OneiosKind.RUNTIME),
    ).joinToString(" · ")

    /** "iOS 27.0.1 (24A446) · 17.9 GB · every file as staged". */
    fun imageLine(m: OneiosStatus.Image, check: Check, record: OneiosStaged?): String = listOfNotNull(
        "iOS ${m.version}" + m.build.takeIf { it.isNotBlank() && it != "unknown" }?.let { " ($it)" }.orEmpty(),
        (m.bytes ?: record?.bytes)?.let(Units::bytes),
        checkWords(check, OneiosKind.IMAGE),
    ).joinToString(" · ")

    /**
     * iOS's own data (the stage's `data/`): the switch makes it, with `control/state`, at the first
     * switch, and a new runtime or image set keeps it. `status` does not name it, so this goes by
     * the session state root reports: `never` (no state file) is a stage that never switched.
     */
    fun dataLine(s: OneiosStatus): String =
        if (s.sessionState == null || s.sessionState == "never") "New: made at the first switch"
        else "Kept from earlier sessions"

    /** The data step's short value: "New" or "Kept". */
    fun dataNew(s: OneiosStatus?): Boolean = s?.sessionState.let { it == null || it == "never" }

    /** How the last session came back to One UI, in plain words; null when none has. */
    fun lastReturn(s: OneiosStatus?): OneiosMessage? = when (s?.lastReturn) {
        "inplace" -> OneiosMessage("Back in One UI without a restart", "The last iOS session returned in place.", OneiosFix.SESSION_LOGS, OneiosPart.OTHER, Level.OK)
        "reboot" -> OneiosMessage("Back in One UI by a restart", "The last iOS session returned by restarting the phone.", OneiosFix.SESSION_LOGS, OneiosPart.OTHER, Level.INFO)
        "failsafe" -> OneiosMessage(
            "Back in One UI by the failsafe",
            "A check of the return failed, so the phone restarted" + s?.lastReturnDetail?.takeIf { it.isNotBlank() }?.let { ": ${it.take(80)}" }.orEmpty(),
            OneiosFix.SESSION_LOGS, OneiosPart.OTHER, Level.WARN,
        )
        else -> null
    }
}
