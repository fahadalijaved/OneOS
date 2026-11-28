"""Stage one-use posting and callback custody for the held guest PIN request."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from compose_guest_pin_source_occurrence import COMPLETION, OCCURRENCE, PACKAGE, REQUEST
from run_guest_tree_install_transport import ROOT, load_io, pinned


BASE = ('out/guest-pin-source-occurrence-source/r-3337934a/receipt.json',
        'c8f88b3a7bdfe3ba01d72a96fee58b2b3cc2886fcc2d28c1762a9068e9f07318')
OUT = ROOT / 'out/guest-pin-progress-queue-source'

POST = b'''    enum PostState { READY, POSTING, ACCEPTED, REFUSED, UNCERTAIN, NOT_POSTED }

    enum EntryState { WAITING, ENTERED, ADMITTED, SKIPPED, RETURNED, THREW }

    /** One exact delivery. Queue observations and main callback observations are independent. */
    static final class ProgressPost {
        private final GuestPinCheckRequest request;
        private final Handler handler;
        private final Runnable ticket;
        private PostState state = PostState.READY;
        private EntryState entry = EntryState.WAITING;

        private ProgressPost(GuestPinCheckRequest request, Handler handler, Runnable ticket) {
            this.request = request;
            this.handler = handler;
            this.ticket = ticket;
        }

        /** Calls the original Handler once. A thrown post leaves enqueue status uncertain. */
        PostState post() throws Throwable {
            synchronized (request.slot.lock) {
                if (state != PostState.READY) return state;
                synchronized (request.occurrence.publicationLock()) {
                    if (!request.currentLocked() || !request.originalMatchLocked()) {
                        state = PostState.NOT_POSTED;
                        return state;
                    }
                    state = PostState.POSTING;
                }
            }

            final boolean accepted;
            try {
                accepted = handler.post(ticket);
            } catch (Throwable failure) {
                synchronized (request.slot.lock) {
                    state = PostState.UNCERTAIN;
                }
                throw failure;
            }
            synchronized (request.slot.lock) {
                state = accepted ? PostState.ACCEPTED : PostState.REFUSED;
                return state;
            }
        }

        PostState state() {
            synchronized (request.slot.lock) {
                return state;
            }
        }

        EntryState entryState() {
            synchronized (request.slot.lock) {
                return entry;
            }
        }
    }

    /** One exact Runnable arrival, including an arrival whose original body is refused. */
    static final class ProgressEntry {
        private final ProgressPost post;

        private ProgressEntry(ProgressPost post) {
            this.post = post;
        }

        boolean finish(Throwable failure) {
            GuestPinCheckRequest request = post.request;
            if (Looper.myLooper() != request.slot.main) return false;
            synchronized (request.slot.lock) {
                if (request.checkingProgress || (post.entry != EntryState.ENTERED
                        && post.entry != EntryState.ADMITTED)) return false;
                if (failure != null) {
                    post.entry = EntryState.THREW;
                } else {
                    post.entry = post.entry == EntryState.ADMITTED ? EntryState.RETURNED : EntryState.SKIPPED;
                }
                return true;
            }
        }
    }

'''

OLD_ENTRY = b'''        return currentLocked() && pendingOriginalTicket == originalTicket && actualReceiver == receiver
                && actualHandler == handler && completion.finalKind() == PinCheckCompletion.FinalKind.ORIGINAL_MATCH;
    }
'''
NEW_ENTRY = b'''        return currentLocked() && sameProgressLocked(actualReceiver, actualHandler, originalTicket)
                && progressPost.entry == EntryState.ENTERED
                && (progressPost.state == PostState.POSTING || progressPost.state == PostState.ACCEPTED)
                && originalMatchLocked();
    }

    /** Records actual arrival before evaluating currentness or invoking original work. */
    ProgressEntry beginOriginalProgressDelivery(IInterface actualReceiver, Handler actualHandler,
            Runnable originalTicket) {
        if (Looper.myLooper() != slot.main) return null;
        synchronized (slot.lock) {
            if (!sameProgressLocked(actualReceiver, actualHandler, originalTicket)
                    || progressPost.entry != EntryState.WAITING || progressPost.state == PostState.READY
                    || progressPost.state == PostState.NOT_POSTED) return null;
            ProgressEntry entry = new ProgressEntry(progressPost);
            progressPost.entry = EntryState.ENTERED;
            return entry;
        }
    }

    private boolean sameProgressLocked(IInterface actualReceiver, Handler actualHandler, Runnable originalTicket) {
        return progressPost != null && actualReceiver == receiver && actualHandler == progressPost.handler
                && originalTicket == progressPost.ticket;
    }
'''

OLD_RETAIN = b'''    private void retainTicketLocked(Runnable ticket) {
        if (completion.finalKind() != PinCheckCompletion.FinalKind.ORIGINAL_MATCH) {
            pendingOriginalTicket = null;
        } else if (ticket != null) {
            // The future source/policy delivery owner must claim this exact ticket.
            pendingOriginalTicket = ticket;
        }
    }
'''
NEW_RETAIN = b'''    private ProgressPost preparePostLocked(Runnable ticket) {
        synchronized (occurrence.publicationLock()) {
            if (!currentLocked() || !originalMatchLocked()) {
                retireUnpostedProgressLocked();
                return null;
            }
            if (ticket == null || progressPost != null) return null;
            progressPost = new ProgressPost(this, handler, ticket);
            return progressPost;
        }
    }

    private boolean originalMatchLocked() {
        return completion.finalKind() == PinCheckCompletion.FinalKind.ORIGINAL_MATCH;
    }

    private void retireUnpostedProgressLocked() {
        if (progressPost != null && progressPost.state == PostState.READY) {
            progressPost.state = PostState.NOT_POSTED;
        }
    }
'''


def bind_queue(source):
    slot = b'    /** One slot on the original checker, independent of mCheckCredentialTask. */\n'
    failure = b'            completion.recordFailure(task, receiver, failure);\n'
    uncertain = b'            completion.recordTransportUncertain(task, receiver);\n'
    pending_clear = b'            pendingOriginalTicket = null;\n'
    retire_unposted = b'            retireUnpostedProgressLocked();\n'
    replacements = (
        (slot, POST + slot),
        (b'    private Runnable pendingOriginalTicket;\n', b'    private ProgressPost progressPost;\n'),
        (b'    void observeOriginalTicket(', b'    ProgressPost observeOriginalTicket('),
        (b'                    || actualHandler != handler) return;\n'
         b'            retainTicketLocked(completion.recordProgress(task, receiver, originalTicket));',
         b'                    || actualHandler != handler) return null;\n'
         b'            return preparePostLocked(completion.recordProgress(task, receiver, originalTicket));'),
        (b'    void observeOriginalFinal(', b'    ProgressPost observeOriginalFinal('),
        (b'            if (!workerCurrentLocked(actualTask)) return;\n            active = completion;',
         b'            if (!workerCurrentLocked(actualTask)) return null;\n            active = completion;'),
        (b'            if (workerCurrentLocked(actualTask)) retainTicketLocked(ticket);',
         b'            return workerCurrentLocked(actualTask) ? preparePostLocked(ticket) : null;'),
        (failure + pending_clear, failure + retire_unposted),
        (uncertain + pending_clear, uncertain + retire_unposted),
        (b'                pendingOriginalTicket = null;\n                return true;',
         b'                progressPost.entry = EntryState.ADMITTED;\n                return true;'),
        (OLD_ENTRY, NEW_ENTRY),
        (OLD_RETAIN, NEW_RETAIN),
        (b'        retired = true;\n        pendingOriginalTicket = null;',
         b'        retired = true;\n        retireUnpostedProgressLocked();'),
    )
    if b'\r\n' in source:
        replacements = tuple((old.replace(b'\n', b'\r\n'), new.replace(b'\n', b'\r\n'))
                             for old, new in replacements)
    updated = source
    for old, new in replacements:
        if updated.count(old) != 1 or new in updated:
            raise ValueError('Exact held request queue anchor changed')
        updated = updated.replace(old, new, 1)
    inverse = updated
    for old, new in reversed(replacements):
        if inverse.count(new) != 1:
            raise ValueError('Staged queue lacks the exact inverse')
        inverse = inverse.replace(new, old, 1)
    if inverse != source:
        raise ValueError('Staged queue lacks the whole-source inverse')
    return updated


def compose():
    io = load_io()
    base = json.loads(pinned(io, *BASE, 16384), object_pairs_hook=io['unique_object'])
    if (base['status'] != 'STAGED_DONOR_PIN_SOURCE_OCCURRENCE_SOURCE_ONLY'
            or base['selected'] is not False or base['deviceEligible'] is not False
            or base['targetExecuted'] is not False or base['wholeSourceInversePassed'] is not True
            or base['package'] != PACKAGE or set(base['outputs']) != {REQUEST, COMPLETION, OCCURRENCE}):
        raise ValueError('Expected the held occurrence source cohort')
    sources = {name: pinned(io, row['path'], row['sha256'], 16384)
               for name, row in base['outputs'].items()}
    sources[REQUEST] = bind_queue(sources[REQUEST])
    if OUT.resolve() != OUT:
        raise ValueError('Expected a repository-local source output')
    OUT.mkdir(exist_ok=True)
    run = OUT / ('r-' + uuid4().hex[:8])
    target = run / Path(*PACKAGE.split('.'))
    run.mkdir()
    target.mkdir(parents=True)
    outputs = {}
    for name, raw in sources.items():
        path = target / name
        with path.open('xb') as stream:
            stream.write(raw)
        outputs[name] = {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
                         'sha256': hashlib.sha256(raw).hexdigest()}
    result = {
        'schema': 'oneos-guest-pin-progress-queue-source/v1',
        'status': 'STAGED_DONOR_PIN_PROGRESS_QUEUE_SOURCE_ONLY',
        'selected': False, 'deviceEligible': False, 'targetExecuted': False,
        'package': PACKAGE, 'outputs': outputs, 'wholeSourceInversePassed': True,
        'baseReceipt': {'path': BASE[0], 'sha256': BASE[1]},
    }
    with (run / 'receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(compose(), indent=2))
