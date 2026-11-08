package model

import com.fahadali.oneos.core.root.RootScript
import com.fahadali.oneos.core.root.RootReply
import java.nio.file.Files
import java.nio.file.Path

/** Calls actual first-party validator/launcher/parser; contains no installer implementation. */
object ControllerContract {
    private var checks = 0
    private fun yes(value: Boolean, detail: String) { checks++; check(value) { detail } }
    private val sum = "a".repeat(64)
    @JvmStatic fun main(args: Array<String>) {
        when (args.firstOrNull()) {
            "validate" -> {
                val verb = RootScript.Verb.INSTALL_CLOSED_CONTROLLER
                yes(verb.stdin == RootScript.Stdin.SCRIPT_DATA, "script-prefix plus native data is selected")
                for (size in listOf("1", "128", "2097152"))
                    yes(RootScript.problems(verb, listOf(size, sum)).isEmpty(), "canonical bounded native size")
                for (size in listOf("", "0", "01", "-1", "+1", "1.0", "2097153", "999999999999999999999999", "1;touch"))
                    yes(RootScript.problems(verb, listOf(size, sum)).isNotEmpty(), "invalid native size is rejected")
                for (hash in listOf("", "A".repeat(64), "a".repeat(63), "a".repeat(65), "g".repeat(64), "a".repeat(63)+";"))
                    yes(RootScript.problems(verb, listOf("128", hash)).isNotEmpty(), "strict native hash")
                yes(RootScript.problems(verb, listOf("128")).isNotEmpty(), "missing argument")
                yes(RootScript.problems(verb, listOf("128", sum, "arbitrary-target")).isNotEmpty(), "no target argument exists")
                val reply = RootReply()
                reply.accept("@@OK closed-controller-installed")
                yes(reply.ok == "closed-controller-installed", "actual reply parser preserves the install-only acknowledgement")
                println("{\"pass\":true,\"actualFirstPartyCode\":true,\"checks\":$checks,\"rootOrNativeExecuted\":false}")
            }
            "launcher" -> {
                require(args.size == 10)
                val repository = Path.of(args[1]).toRealPath()
                val output = Path.of(args[9]).toAbsolutePath().normalize()
                require(output.startsWith(repository.resolve("out")))
                require(output.parent.toRealPath().startsWith(repository.resolve("out")) && !Files.exists(output))
                val layout = RootScript.Layout(args[2], args[3], "/bin/sh", args[4], "0", "0:0")
                val text = RootScript.launcher(RootScript.Verb.INSTALL_CLOSED_CONTROLLER,
                    listOf(args[7], args[8]), args[6], Files.size(Path.of(args[5])), layout)
                Files.writeString(output, text)
                println("{\"generatedFromActualRootScript\":true}")
            }
            else -> error("Selected test mode required")
        }
    }
}
