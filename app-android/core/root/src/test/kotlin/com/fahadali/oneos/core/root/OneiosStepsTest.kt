package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.OneiosFix
import com.fahadali.oneos.core.model.OneiosMessage
import com.fahadali.oneos.core.model.OneiosPart
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * iOS 27's one checklist (docs/oneios.md, "UI (2026-11-25)"): each step's state on the way from a fresh phone to a
 * session and back, the next step (the page's primary button), a running step's progress from the job's bytes and
 * from oneios-tool's own event lines, a failure's reason and where Show log goes; and the step names are the docs'.
 */
class OneiosStepsTest {
    private fun status(vararg lines: String) = OneiosStatus.parse(lines.toList())

    private val runtime = "runtime 0.1.31 1 bin/xnuhost 1 0"
    private val image = "image 1 27.0.1 24A446 17900000000"
    private val bid = "xnu-12377.121.6-ios-27.0.1-24A446-abcdef012345"
    private val old = "xnu-12377.100.1-ios-27.0.1-24A446-000000000000"

    private fun steps(
        st: OneiosStatus?,
        job: OneiosSteps.Job = OneiosSteps.Job(),
        tool: OneiosSteps.Tool = OneiosSteps.Tool(),
        expected: String? = st?.runtimeKernel?.buildId,
    ): OneiosSteps.View {
        val flow = OneiosFlow.of(OneiosFlow.Input(st, true, job.running, job.last, job.failure))
        return OneiosSteps.of(OneiosSteps.Input(flow, st, job, tool, expected))
    }

    private fun states(v: OneiosSteps.View) = v.steps.map { it.state }

    private fun fold(vararg lines: String): OneiosToolFlow = lines.fold(OneiosToolFlow()) { f, l -> f.with(OneiosTool.parse(l)!!) }

    private val S = OneiosSteps.State.entries.associateBy { it.name.first() }

    @Test
    fun theStepNamesAreTheDocs() {
        assertEquals(
            listOf("Get the runtime", "Make iOS image", "Update the kernel"),
            OneiosSteps.Id.entries.map { it.title },
        )
        // docs/oneios.md (the fork's) names each of them in its UI section, as the screens do.
        val doc = File(Shipped.appSources, "../../../docs/oneios.md").readText()
        val ui = doc.substringAfter("## UI (2026-11-25)").substringBefore("\n## ")
        for (id in OneiosSteps.Id.entries) assertTrue("docs/oneios.md's UI section lacks the step ${id.title}", ui.contains("| ${id.title} |"))
        for (id in OneiosSteps.Id.entries) assertTrue(id.about, id.about.length in 20..120 && id.about.endsWith("."))
    }

    @Test
    fun aFreshPhoneStartsAtGetTheRuntime() {
        val v = steps(status("stage none"))
        assertEquals(OneiosSteps.State.TODO, v.step(OneiosSteps.Id.RUNTIME).state)
        assertEquals(OneiosSteps.State.WAITING, v.step(OneiosSteps.Id.IMAGE).state)
        assertEquals("After Get the runtime", v.step(OneiosSteps.Id.IMAGE).line)
        assertTrue(v.steps.drop(1).all { it.state == OneiosSteps.State.WAITING })
        assertEquals(OneiosSteps.Id.RUNTIME, v.next)
        // Before root answered once: no step to press, the page's button is Check again.
        assertNull(steps(null).next)
    }

    @Test
    fun aDownloadShowsItsBytesAndCanBeCancelled() {
        val job = OneiosSteps.Job(OneiosFlow.Job.DOWNLOAD_RUNTIME, "Downloading the runtime…", 25, 100, null, "25 B of 100 B (25%)")
        val v = steps(status("stage none"), job)
        val r = v.step(OneiosSteps.Id.RUNTIME)
        assertEquals(OneiosSteps.State.RUNNING, r.state)
        assertEquals(0.25f, r.progress!!.fraction)
        assertEquals(25, r.progress!!.percent)
        assertEquals("Downloading the runtime…", r.progress!!.phase)
        assertEquals("25 B of 100 B (25%)", r.progress!!.amount)
        assertEquals(OneiosSteps.Cancel.JOB, r.cancel)
        assertNull(v.next)
        // It failed: the plain words, and root's whole answer behind Show log.
        val failed = steps(status("stage none"), OneiosSteps.Job(last = OneiosFlow.Job.DOWNLOAD_RUNTIME, failure = "the download stopped: connection reset"))
        val f = failed.step(OneiosSteps.Id.RUNTIME)
        assertEquals(OneiosSteps.State.FAILED, f.state)
        assertTrue(f.reason!!.isNotBlank())
        assertEquals(OneiosSteps.Log.ROOT, f.log)
        assertEquals(OneiosSteps.Id.RUNTIME, failed.next)
    }

    @Test
    fun makeIosImageShowsTheToolsOwnProgress() {
        val st = status("stage present", runtime, "kernel runtime $bid xnu-12377.121.6", "image none", "session none never", "outcome none",
            "ready 0 no iOS image set is staged: import the one you built")
        assertEquals(OneiosSteps.Id.IMAGE, steps(st).next)
        assertEquals(OneiosSteps.State.TODO, steps(st).step(OneiosSteps.Id.IMAGE).state)
        // The tool's lines as it sends them on serve: its plan, a step, that step's progress.
        val view = fold(
            """{"ev":"start","id":"1","cmd":"make-image","steps":[{"step":"check","text":"Checking the room"},{"step":"download","text":"Downloading iOS from Apple"},{"step":"decrypt","text":"Decrypting"},{"step":"place","text":"Placing"}]}""",
            """{"ev":"step","id":"1","step":"download","n":2,"of":4,"text":"Downloading iOS from Apple"}""",
            """{"ev":"progress","id":"1","step":"download","done":3221225472,"total":11382548957,"unit":"bytes","percent":28.3,"rate":41943040,"eta":290}""",
        )
        val tool = OneiosSteps.Tool(running = OneiosSteps.ToolFlow.MAKE_IMAGE, last = OneiosSteps.ToolFlow.MAKE_IMAGE, view = view, phase = "Making the iOS image on this phone")
        val v = steps(st, tool = tool)
        val s = v.step(OneiosSteps.Id.IMAGE)
        assertEquals(OneiosSteps.State.RUNNING, s.state)
        assertEquals(0.283f, s.progress!!.fraction!!, 0.0001f)
        assertEquals("Making the iOS image on this phone · Step 2 of 4 · Downloading iOS from Apple", s.progress!!.phase)
        assertTrue(s.progress!!.amount!!, s.progress!!.amount!!.contains("(28%)") && s.progress!!.amount!!.contains("left"))
        assertEquals(OneiosSteps.Cancel.TOOL, s.cancel)
        assertNull(v.next)
        // A step with no numbers: the bar is the share of the plan done (2 of 4 steps before it).
        val decrypt = fold(
            """{"ev":"start","id":"1","cmd":"make-image","steps":[{"step":"check"},{"step":"download"},{"step":"decrypt","text":"Decrypting"},{"step":"place"}]}""",
            """{"ev":"step","id":"1","step":"decrypt","n":3,"of":4,"text":"Decrypting"}""",
        )
        val p = OneiosSteps.toolProgress(decrypt, held = "Paused: the case is at 44 C")
        assertEquals(0.5f, p.fraction)
        assertEquals("Step 3 of 4 · Decrypting", p.phase)
        assertEquals("Paused: the case is at 44 C", p.amount)
        // Before the plan: a moving bar.
        assertNull(OneiosSteps.toolProgress(OneiosToolFlow(), starting = true).fraction)
        assertEquals("Starting oneios-tool…", OneiosSteps.toolProgress(OneiosToolFlow(), starting = true).phase)
        // It stopped: the plain words, and the tool's details behind Show log.
        val why = OneiosMessage("Not enough room", "It needs 37.1 GB free, this phone has 12.0 GB", OneiosFix.NONE, OneiosPart.IMAGE)
        val failed = steps(st, tool = OneiosSteps.Tool(last = OneiosSteps.ToolFlow.MAKE_IMAGE, view = view, failure = why))
        val f = failed.step(OneiosSteps.Id.IMAGE)
        assertEquals(OneiosSteps.State.FAILED, f.state)
        assertEquals("Not enough room", f.line)
        assertEquals("It needs 37.1 GB free, this phone has 12.0 GB", f.reason)
        assertEquals(OneiosSteps.Log.TOOL, f.log)
        assertEquals(OneiosSteps.Id.IMAGE, failed.next)
        // A later run that failed with a set staged: the failure shows, the switch is still next.
        val staged = status("stage present", runtime, "kernel runtime $bid xnu-12377.121.6", image, "kernel image $bid ${"a".repeat(64)} 0",
            "session none never", "outcome none", "ready 1")
        val again = steps(staged, tool = OneiosSteps.Tool(last = OneiosSteps.ToolFlow.MAKE_IMAGE, view = view, failure = why))
        assertEquals(OneiosSteps.State.FAILED, again.step(OneiosSteps.Id.IMAGE).state)
        // No step left for the user: the page's button is the flow's Switch to iOS 27.
        assertNull(again.next)
        assertEquals(OneiosFlow.Next.SWITCH, OneiosFlow.of(OneiosFlow.Input(staged, true)).next)
    }

    private val ready = status("stage present", runtime, "kernel runtime $bid xnu-12377.121.6", image, "kernel image $bid ${"a".repeat(64)} 0",
        "session none never", "outcome none", "ready 1")

    /** The other runtime's kernel in the image, as after a runtime update: Update the kernel is due. */
    private val stale = status("stage present", runtime, "kernel runtime $bid xnu-12377.121.6", image, "kernel image $old ${"a".repeat(64)} 1",
        "session none never", "outcome none", "ready 1")

    @Test
    fun readyToSwitchHasEveryStepDoneAndTheSwitchIsTheButton() {
        // The switch is a button, no step (the owner, 2026-11-25): three steps, all done, and the flow's next is Switch.
        val v = steps(ready)
        assertEquals(listOf(S['D'], S['D'], S['D']), states(v))
        assertNull(v.next)
        assertEquals(0, v.todo)
        assertEquals(OneiosFlow.Next.SWITCH, OneiosFlow.of(OneiosFlow.Input(ready, true)).next)
        // A refused preflight is no step either: On this phone shows it with its fix (the flow's problem), the button is the fix.
        val refused = status("stage present", runtime, "kernel runtime $bid xnu-12377.121.6", image, "kernel image $bid ${"a".repeat(64)} 0",
            "session none never", "outcome none", "ready 0 battery at 12% and not charging")
        assertNull(steps(refused).next)
        assertTrue(OneiosFlow.of(OneiosFlow.Input(refused, true)).problem!!.line.contains("12%"))
    }

    @Test
    fun updateTheKernelBuildsThenPutsItInAsOneStep() {
        val v = steps(stale)
        assertEquals(OneiosSteps.State.TODO, v.step(OneiosSteps.Id.KERNEL).state)
        // Building: the tool's progress and Cancel.
        val building = steps(stale, tool = OneiosSteps.Tool(running = OneiosSteps.ToolFlow.KERNEL, last = OneiosSteps.ToolFlow.KERNEL, phase = "Building the kernel"))
        assertEquals(OneiosSteps.State.RUNNING, building.step(OneiosSteps.Id.KERNEL).state)
        assertEquals(OneiosSteps.Cancel.TOOL, building.step(OneiosSteps.Id.KERNEL).cancel)
        // Built: still to do (it is put in next), then root's finish kernel runs as the same step, with no Cancel.
        val built = OneiosSteps.Tool(last = OneiosSteps.ToolFlow.KERNEL, builtKc = "b".repeat(64))
        assertEquals(OneiosSteps.State.TODO, steps(stale, tool = built).step(OneiosSteps.Id.KERNEL).state)
        val putting = steps(stale, OneiosSteps.Job(OneiosFlow.Job.FINISH_KERNEL, "Activating the phone-built kernel…"), built)
        assertEquals(OneiosSteps.State.RUNNING, putting.step(OneiosSteps.Id.KERNEL).state)
        assertEquals("Activating the phone-built kernel…", putting.step(OneiosSteps.Id.KERNEL).progress!!.phase)
        assertNull(putting.step(OneiosSteps.Id.KERNEL).cancel)
        // A kernel staged before kernel tracking is to do; a runtime without a kernel has nothing to build.
        val unknown = status("stage present", runtime, "kernel runtime $bid xnu-12377.121.6", image, "session none never", "outcome none", "ready 1")
        assertEquals(OneiosSteps.State.TODO, steps(unknown).step(OneiosSteps.Id.KERNEL).state)
        val noKernel = status("stage present", runtime, image, "session none never", "outcome none", "ready 1")
        assertEquals(OneiosSteps.State.WAITING, steps(noKernel).step(OneiosSteps.Id.KERNEL).state)
    }

    /**
     * The phone's report (2026-11-25): Update the kernel, then Activate, and the page showed Update the kernel again.
     * Activate cleared the built kernel before root ran; a refused activation, or one that did not start because another
     * job ran, lost it. Now the built kernel stays until root's finish kernel put it in: refused, the step is failed with
     * root's reason and Show log, and the build is still there to put in; done, the step is done.
     */
    @Test
    fun aRefusedActivationKeepsTheBuiltKernelAndADoneOneIsDone() {
        val built = OneiosSteps.Tool(last = OneiosSteps.ToolFlow.KERNEL, builtKc = "b".repeat(64))
        val refused = steps(stale, OneiosSteps.Job(last = OneiosFlow.Job.FINISH_KERNEL, failure = "the built kernel.kc is not ${"b".repeat(64)}: run the kernel build again"), built)
        val k = refused.step(OneiosSteps.Id.KERNEL)
        assertEquals(OneiosSteps.State.FAILED, k.state)
        assertTrue(k.reason!!.isNotBlank())
        assertEquals(OneiosSteps.Log.ROOT, k.log)
        // Root put it in: the status names the runtime's kernel, the built one is gone (OneiosToolJob.kernelActivated).
        val after = status("stage present", runtime, "kernel runtime $bid xnu-12377.121.6", image, "kernel image $bid ${"b".repeat(64)} 1",
            "session none never", "outcome none", "ready 1")
        val done = steps(after, OneiosSteps.Job(last = OneiosFlow.Job.FINISH_KERNEL), OneiosSteps.Tool(last = OneiosSteps.ToolFlow.KERNEL))
        assertEquals(OneiosSteps.State.DONE, done.step(OneiosSteps.Id.KERNEL).state)
        assertEquals(OneiosFlow.Next.SWITCH, OneiosFlow.of(OneiosFlow.Input(after, true)).next)
    }

    private fun auto(st: OneiosStatus, latest: String? = null, due: Boolean = false, tried: Set<String> = emptySet(), idle: Boolean = true,
        tool: OneiosSteps.Tool = OneiosSteps.Tool(), job: OneiosSteps.Job = OneiosSteps.Job()): OneiosSteps.Auto {
        val flow = OneiosFlow.of(OneiosFlow.Input(st, true, job.running, job.last, job.failure))
        val input = OneiosSteps.Input(flow, st, job, tool, st.runtimeKernel?.buildId)
        return OneiosSteps.auto(OneiosSteps.AutoInput(input, idle, latest, due, tried))
    }

    /** Updates by themselves (the owner, 2026-11-25): runtime and kernel, once each, never during a session or a job. */
    @Test
    fun theRuntimeAndTheKernelUpdateByThemselves() {
        // A newer release: its runtime is staged; the same or an older one: nothing; a look every 6 h.
        assertEquals(OneiosSteps.Auto.UPDATE_RUNTIME, auto(ready, latest = "0.1.33"))
        assertEquals(OneiosSteps.Auto.NONE, auto(ready, latest = "0.1.31"))
        assertEquals(OneiosSteps.Auto.NONE, auto(ready, latest = "0.1.30"))
        assertEquals(OneiosSteps.Auto.CHECK_RUNTIME, auto(ready, latest = "0.1.31", due = true))
        // The image's kernel is another runtime's: Update the kernel; then the built kernel is put in.
        assertEquals(OneiosSteps.Auto.UPDATE_KERNEL, auto(stale))
        val built = OneiosSteps.Tool(last = OneiosSteps.ToolFlow.KERNEL, builtKc = "b".repeat(64))
        assertEquals(OneiosSteps.Auto.ACTIVATE, auto(stale, tool = built))
        // Each once: a failure stays on its step (the user's tap tries again).
        val flow = OneiosFlow.of(OneiosFlow.Input(stale, true))
        val key = OneiosSteps.autoKey(OneiosSteps.Auto.UPDATE_KERNEL, OneiosSteps.Input(flow, stale, expectedKernel = bid), null)
        assertEquals(OneiosSteps.Auto.NONE, auto(stale, tried = setOf(key)))
        assertEquals(OneiosSteps.Auto.NONE, auto(stale, tool = built, tried = setOf("activate ${"b".repeat(64)}")))
        assertEquals(OneiosSteps.Auto.NONE, auto(ready, latest = "0.1.33", tried = setOf("runtime 0.1.33")))
        // Never while something runs, during a session, before root answered, or before the user staged a runtime.
        assertEquals(OneiosSteps.Auto.NONE, auto(stale, idle = false))
        val open = status("stage present", runtime, "kernel runtime $bid xnu-12377.121.6", image, "kernel image $old ${"a".repeat(64)} 1",
            "session open running", "outcome none", "ready 0 an iOS session is running")
        assertEquals(OneiosSteps.Auto.NONE, auto(open, latest = "0.1.33", due = true))
        assertEquals(OneiosSteps.Auto.NONE, auto(status("stage none"), latest = "0.1.33", due = true))
        // A current kernel and the newest runtime: nothing.
        assertEquals(OneiosSteps.Auto.NONE, auto(ready, latest = "0.1.31"))
    }

    @Test
    fun anOpenSessionHasNoStepsLeftAndBackToOneUiIsTheFlowsButton() {
        // Back to One UI and the logs are no steps (the owner, 2026-11-25): the page's button is the flow's own next.
        val st = status("stage present", runtime, image, "session open running", "outcome none", "ready 0 an iOS session is running")
        val v = steps(st)
        assertNull(v.next)
        assertEquals(OneiosFlow.Next.BACK_TO_ONE_UI, OneiosFlow.of(OneiosFlow.Input(st, true)).next)
        // While root returns, no step runs either: the button spins with the job's words.
        assertNull(steps(st, OneiosSteps.Job(OneiosFlow.Job.RETURN, "Returning to One UI…")).running)
    }
}
