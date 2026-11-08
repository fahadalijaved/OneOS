package com.fahadali.oneos.session

import com.fahadali.oneos.core.model.LaunchCommitGuard
import com.fahadali.oneos.session.ViewPreparationStatus.Cleanup
import com.fahadali.oneos.session.ViewPreparationStatus.CloseObservation as Close
import com.fahadali.oneos.session.ViewPreparationStatus.Message
import com.fahadali.oneos.session.ViewPreparationStatus.Preparation as Prep

private fun occurrence() = checkNotNull(ViewPreparationOccurrence.recordAtCommitCut(LaunchCommitGuard()))

private class Fixture {
    val occurrence = occurrence()
    val ui = ViewPreparationStatus(occurrence)
    val sent = mutableListOf<ViewPreparationOccurrence>()

    fun ask() = checkNotNull(ui.showStopConfirmation())
    fun confirm(prompt: ViewPreparationStatus.StopPrompt) {
        ui.confirmStop(prompt)?.let(sent::add)
    }
}

private fun case(name: String, test: Fixture.() -> Unit) {
    Fixture().test()
    println("PASS $name")
}

fun main() {
    case("keep going consumes only its dialog") {
        val first = ask()
        check(ask() === first && ui.snapshot.confirmationOpen && !ui.snapshot.stopEnabled)
        check(ui.keepGoing(first) && ui.snapshot.stopEnabled)
        val second = ask()
        check(second !== first && !ui.keepGoing(first))
        confirm(first)
        check(sent.isEmpty() && ui.snapshot.confirmationOpen)
        check(ui.keepGoing(second) && ui.snapshot.message == Message.PREPARING)
    }

    case("stop queues the same occurrence once and remains pending") {
        val prompt = ask()
        confirm(prompt)
        confirm(prompt)
        check(sent.single() === occurrence && ui.showStopConfirmation() == null)
        check(ui.snapshot.cleanup == Cleanup.PENDING && ui.snapshot.message == Message.STOPPING)
        check(!ui.observeClose(occurrence, Close.HOLD))
        check(ui.observeClose(occurrence, Close.LOCAL_TERMINAL))
        check(ui.snapshot.cleanup == Cleanup.LOCAL_TERMINAL && ui.snapshot.message == Message.STOPPING)
        check(!ui.observeClose(occurrence, Close.HOLD))
        check(ui.observeClose(occurrence, Close.STOP_CONFIRMED))
        check(ui.snapshot.cleanup == Cleanup.CONFIRMED && ui.snapshot.message == Message.CANCELLED)
        check(!ui.observePreparation(occurrence, Prep.PARTIAL))
        check(!ui.observeClose(occurrence, Close.UNCONFIRMED) && ui.showStopConfirmation() == null)
    }

    case("same-owner no-work stop can be confirmed without a terminal frame") {
        confirm(ask())
        check(ui.observeClose(occurrence, Close.STOP_CONFIRMED))
        check(ui.snapshot.message == Message.CANCELLED && ui.snapshot.cleanup == Cleanup.CONFIRMED)
    }

    case("local cleanup alone does not confirm user stop") {
        check(!ui.observeClose(occurrence, Close.STOP_CONFIRMED))
        confirm(ask())
        check(ui.observeClose(occurrence, Close.CLEANUP_CONFIRMED))
        check(ui.snapshot.message == Message.LOCALLY_CLOSED)
        check(!ui.observeClose(occurrence, Close.STOP_CONFIRMED))
    }

    case("foreign occurrence and foreign dialog callbacks leave the snapshot unchanged") {
        val other = Fixture()
        val own = ask()
        val before = ui.snapshot
        confirm(other.ask())
        check(!ui.keepGoing(other.ask()) && sent.isEmpty())
        check(!ui.observePreparation(other.occurrence, Prep.REFUSED))
        check(!ui.observeClose(other.occurrence, Close.CLEANUP_CONFIRMED))
        check(ui.snapshot == before && ui.keepGoing(own))
    }

    case("partial observation does not clear a pending close or permit a second result") {
        check(!ui.observePreparation(occurrence, Prep.PENDING))
        check(ui.observePreparation(occurrence, Prep.PARTIAL))
        check(ui.snapshot.message == Message.PARTIAL_OBSERVED && ui.snapshot.stopEnabled)
        confirm(ask())
        check(!ui.observePreparation(occurrence, Prep.PARTIAL))
        check(!ui.observePreparation(occurrence, Prep.REFUSED))
        check(ui.snapshot.preparation == Prep.PARTIAL && ui.snapshot.message == Message.STOPPING)
    }

    case("partial callback after stop preserves stopping") {
        confirm(ask())
        check(ui.observePreparation(occurrence, Prep.PARTIAL))
        check(ui.snapshot.preparation == Prep.PARTIAL && ui.snapshot.message == Message.STOPPING)
        check(!ui.snapshot.stopEnabled && sent.single() === occurrence)
    }

    case("stage refusal closes the dialog and retains independent cleanup") {
        val old = ask()
        check(ui.observePreparation(occurrence, Prep.NEED_STAGE))
        confirm(old)
        check(sent.isEmpty() && ui.snapshot.message == Message.NEED_STAGE)
        check(!ui.snapshot.confirmationOpen && ui.snapshot.cleanup == Cleanup.PENDING)
        check(ui.observeClose(occurrence, Close.UNCONFIRMED))
        check(ui.snapshot.message == Message.NEED_STAGE && ui.snapshot.cleanup == Cleanup.UNCONFIRMED)
        check(!ui.observeClose(occurrence, Close.CLEANUP_CONFIRMED))
    }

    case("refusal after the stop request is preserved through local cleanup") {
        confirm(ask())
        check(ui.observePreparation(occurrence, Prep.REFUSED))
        check(ui.snapshot.message == Message.REFUSED && ui.snapshot.cleanup == Cleanup.PENDING)
        check(!ui.observeClose(occurrence, Close.STOP_CONFIRMED))
        check(ui.observeClose(occurrence, Close.CLEANUP_CONFIRMED))
        check(ui.snapshot.message == Message.REFUSED && ui.snapshot.cleanup == Cleanup.CONFIRMED)
    }

    case("unavailable preparation rejects late success and repeat stop") {
        val old = ask()
        check(ui.observePreparation(occurrence, Prep.UNAVAILABLE))
        confirm(old)
        check(sent.isEmpty() && ui.showStopConfirmation() == null)
        check(ui.snapshot.message == Message.RESULT_UNAVAILABLE && ui.snapshot.cleanup == Cleanup.UNCONFIRMED)
        check(!ui.observePreparation(occurrence, Prep.PARTIAL))
        check(!ui.observeClose(occurrence, Close.CLEANUP_CONFIRMED))
    }

    case("source cutoff can begin without a user stop and never fabricates cancellation") {
        val old = ask()
        check(ui.observeClose(occurrence, Close.HOLD))
        confirm(old)
        check(sent.isEmpty() && ui.snapshot.message == Message.CLEANING_UP)
        check(ui.observeClose(occurrence, Close.LOCAL_TERMINAL))
        check(!ui.observeClose(occurrence, Close.STOP_CONFIRMED))
        check(ui.observeClose(occurrence, Close.UNCONFIRMED))
        check(ui.snapshot.message == Message.CLEANUP_UNCONFIRMED)
        check(!ui.observeClose(occurrence, Close.CLEANUP_CONFIRMED))
    }
}
