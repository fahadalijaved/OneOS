#!/usr/bin/env python3
"""The guest restart's process scan (guest_softreboot.sh, written by guest_prepare.sh).

A Galaxy A34 needed 50 s for one pass over its processes (two spawned commands
per process), so the second pass ran the restart into the watcher's 120 s limit
and the watcher returned to One UI (report of 2026-11-12, 0.4.93). The scan now
takes one listing per pass and looks by itself only at the processes the listing
does not show outside the guest. These tests run the real loop from the script
over a made-up /proc tree and check both halves: the same processes are stopped
as before whatever the listing says, and far fewer of them are looked at.

Nothing here can signal a real process: the loop's `kill -9` is replaced by a
function that writes the pid to a file, a function named `kill` ends the test if
the loop reaches it all the same, and every made-up pid is above the kernel's
highest possible pid.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREPARE = (ROOT / 'switcher/assets/guest_prepare.sh').read_text()

FIRST = 'echo "$(date +%T) soft reboot ($1): stopping the guest\'s processes"\n'
LAST = '[ $pass -le 5 ] || { echo "soft reboot: guest processes still running after 5 passes:$left"; exit 1; }\n'

HOST_NS = 4026531841
GUEST_NS = 4026532999
OTHER_NS = 4026533555          # a One UI process in a mount namespace of its own
APP_NS = 4026534001            # a guest app: zygote gives each its own namespace
HOST_DEV = 64768
GUEST_DEV = 1802
BASE = 9000000                 # above pid_max's upper bound (4194304)

FUNCTIONS = r'''
kill() { echo "the loop reached the real kill: $*" >&2; exit 97; }
record_kill() {
    [ "$1" = -9 ] || { echo "record_kill: $*" >&2; exit 96; }
    case "$2" in ''|*[!0-9]*) echo "record_kill: $*" >&2; exit 96 ;; esac
    echo "$2" >> "$OUT/kills"
    case " $SURVIVORS " in *" $2 "*) ;; *) rm -rf "$FAKE/$2" ;; esac
    return 0
}
timeout() { shift; "$@"; }
readlink() { echo "$1" >> "$OUT/looks"; command readlink "$@"; }
# The listing's first half: `ls -l` over the namespace links. This machine's own
# ls prints the made-up links; the settings below then spoil what it printed.
ls() {
    [ "$1" = -l ] || { echo "ls: unexpected $*" >&2; exit 95; }
    shift
    echo x >> "$OUT/listings"
    case "$LISTING" in
        none) return 1 ;;
        garbage) echo "total 0"; echo; echo "x -> y"; echo "l 1 u g 0 d t /x/12/ns/mnt -> mnt:[oops]"; return 0 ;;
    esac
    command ls -l "$@" | while read -r l_line; do
        l_pid=${l_line% -> *}; l_pid=${l_pid##* }; l_pid=${l_pid#"$FAKE/"}; l_pid=${l_pid%%/*}
        case " $NOT_LISTED " in *" $l_pid "*) continue ;; esac
        case " $LISTED_AS_GUEST " in *" $l_pid "*) l_line="${l_line% -> *} -> mnt:[$GUEST_NS_ID]" ;; esac
        echo "$l_line"
    done
    # Cut off inside its last line, which names a process of the guest as One UI's.
    [ "$LISTING" = cut ] && printf '%s' "lrwxrwxrwx 1 u g 0 d t $FAKE/$CUT_PID/ns/mnt -> mnt:[$HOST_NS_ID"
    return 0
}
# The phone's stat over the made-up tree: `stat -L -c FORMAT path...`; a root's
# device is in the file `rootdev` next to it. A path without one is an error and
# the next path follows, as with the real command. With more than one path it
# is the listing's second half.
stat() {
    [ "$1" = -L ] && [ "$2" = -c ] || { echo "stat: unexpected $*" >&2; exit 95; }
    s_fmt=$3; shift 3; s_rc=0
    if [ $# -gt 1 ]; then
        [ "$s_fmt" = '%d %n' ] || { echo "stat: unexpected format $s_fmt" >&2; exit 95; }
        [ "$ROOTS" = none ] && return 1
        case "$LISTING" in
            none) return 1 ;;
            garbage) echo "stat: not the output this script expects"; echo "a /x/12/root"; echo "7"; return 0 ;;
        esac
    else
        [ "$s_fmt" = '%d' ] || { echo "stat: unexpected format $s_fmt" >&2; exit 95; }
    fi
    for s_f in "$@"; do
        s_d=${s_f%/}
        case "$s_d" in */root) s_d=${s_d%/root} ;; *) echo "stat: unexpected path $s_f" >&2; exit 95 ;; esac
        [ -f "$s_d/rootdev" ] || { s_rc=1; continue; }
        if [ $# -gt 1 ]; then
            case " $NOT_LISTED " in *" ${s_d##*/} "*) s_rc=1; continue ;; esac
            echo "$(cat "$s_d/rootdev") $s_f"
        else
            cat "$s_d/rootdev"
        fi
    done
    # Cut off inside its last line, which puts a guest app's root on One UI's device.
    [ $# -gt 1 ] && [ "$LISTING" = cut ] && printf '%s' "$HOST_DEV_ID $FAKE/$CUT_ROOT_PID"
    # A process that enters the guest right after the first listing.
    if [ $# -gt 1 ] && [ -n "$JOINS_AFTER_LISTING" ] && [ ! -e "$OUT/joined" ]; then
        : > "$OUT/joined"
        ln -sfn "mnt:[$GUEST_NS_ID]" "$FAKE/$JOINS_AFTER_LISTING/ns/mnt"
    fi
    return $s_rc
}
'''


def softreboot_script():
    body = PREPARE.split("<<'GUESTSOFTREBOOT'\n", 1)[1].split('\nGUESTSOFTREBOOT\n', 1)[0] + '\n'
    return body


def scan_loop():
    body = softreboot_script()
    loop = FIRST + body.split(FIRST, 1)[1].split(LAST, 1)[0] + LAST
    return loop


class Tree:
    """A made-up /proc: name -> pid, with each process's namespace, root device and name."""

    def __init__(self, d):
        self.proc = Path(d) / 'proc'
        self.out = Path(d) / 'out'
        self.proc.mkdir()
        self.out.mkdir()
        self.pids = {}
        bb = Path(d) / 'busybox'
        bb.write_text('#!/bin/sh\nif command -v busybox >/dev/null 2>&1; then exec busybox "$@"; fi\nexec "$@"\n')
        bb.chmod(0o755)
        self.bb = bb

    def add(self, name, ns, dev):
        pid = BASE + len(self.pids) + 1
        p = self.proc / str(pid)
        (p / 'ns').mkdir(parents=True)
        (p / 'comm').write_text(name + '\n')
        if ns is not None:
            os.symlink('mnt:[%d]' % ns, p / 'ns' / 'mnt')
        if dev is not None:
            (p / 'rootdev').write_text('%d\n' % dev)
            os.symlink('/', p / 'root')
        self.pids[name] = pid
        return pid

    def usual(self, hosts=40):
        for i in range(hosts):
            self.add('host%d' % i, HOST_NS, HOST_DEV)
        self.add('host-own-ns', OTHER_NS, HOST_DEV)
        self.add('zombie', None, None)
        for name in ('init', 'servicemanager', 'zygote64', 'system_server', 'surfaceflinger'):
            self.add('guest-' + name, GUEST_NS, GUEST_DEV)
        for i in range(6):
            self.add('guest-app%d' % i, APP_NS + i, GUEST_DEV)
        self.add('guest-entered-helper', GUEST_NS, HOST_DEV)          # in its namespace, One UI's root
        return self

    def guests(self, namespace_only=False):
        return sorted(pid for name, pid in self.pids.items()
                      if name.startswith('guest-') and not (namespace_only and 'app' in name))

    def run(self, guest_ns='mnt:[%d]' % GUEST_NS, guest_dev=str(GUEST_DEV), **env):
        loop = scan_loop()
        assert loop.count('kill -9 "$pid" 2>/dev/null') == 1, 'the loop no longer has its one kill line'
        loop = loop.replace('kill -9 "$pid"', 'record_kill -9 "$pid"').replace('/proc/', str(self.proc) + '/')
        code = '\n'.join(x for x in loop.splitlines() if not x.lstrip().startswith('#'))
        assert not re.search(r'(?<![_\w])kill\b', code.replace('record_kill', 'record')), 'a kill is left in the loop'
        assert '/proc' not in loop.replace(str(self.proc), ''), 'a /proc path is left in the loop'
        script = FUNCTIONS + 'GUEST_NS=%s\nGUEST_DEV=%s\n' % (shquote(guest_ns), shquote(guest_dev)) + loop + 'echo "scan done"\n'
        e = dict(os.environ, FAKE=str(self.proc), OUT=str(self.out), BB=str(self.bb),
                 GUEST_NS_ID=str(GUEST_NS), HOST_NS_ID=str(HOST_NS), HOST_DEV_ID=str(HOST_DEV))
        for k in ('LISTING', 'ROOTS', 'SURVIVORS', 'LISTED_AS_GUEST', 'NOT_LISTED', 'JOINS_AFTER_LISTING', 'CUT_PID', 'CUT_ROOT_PID'):
            e.pop(k, None)
        e.update({k: str(v) for k, v in env.items()})
        r = subprocess.run(['sh', '-c', script, 'softreboot-test', 'test'], env=e, capture_output=True, text=True, timeout=120)
        self.result = r
        return r

    def lines(self, name):
        f = self.out / name
        return f.read_text().split() if f.exists() else []

    def kills(self):
        return sorted(int(x) for x in self.lines('kills'))

    def looked_at(self):
        return [int(Path(x).parts[-3]) for x in self.lines('looks')]

    def first_pass(self):
        m = re.search(r'soft reboot: killed (\d+) guest processes \(looked at (\d+) of (\d+)\)', self.result.stdout)
        assert m, self.result.stdout + self.result.stderr
        return tuple(int(x) for x in m.groups())


def shquote(s):
    return "'" + s.replace("'", "'\\''") + "'"


class ScanTest(unittest.TestCase):
    def tree(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return Tree(d.name)

    def ok(self, t, r):
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual('', r.stderr)
        self.assertIn('scan done', r.stdout)

    def test_the_guests_processes_are_stopped_and_only_those_are_looked_at(self):
        t = self.tree().usual()
        r = t.run()
        self.ok(t, r)
        self.assertEqual(t.guests(), t.kills())
        killed, looked, total = t.first_pass()
        self.assertEqual((12, 13, 54), (killed, looked, total))           # the 12 of the guest and the zombie
        self.assertEqual(sorted(t.guests() + [t.pids['zombie']]), sorted(t.looked_at()))
        self.assertEqual(2, len(t.lines('listings')))                       # pass 2 found nothing left

    def test_a_guest_on_the_hosts_device_is_told_by_its_namespace_alone(self):
        # guest_softreboot.sh empties GUEST_DEV when the guest's root is on One UI's device.
        t = self.tree().usual()
        t.add('host-on-that-device', OTHER_NS + 1, GUEST_DEV)
        r = t.run(guest_dev='')
        self.ok(t, r)
        self.assertEqual(t.guests(namespace_only=True), t.kills())
        self.assertEqual((6, 7, 55), t.first_pass())

    def test_without_a_listing_every_process_is_looked_at_once(self):
        for listing in ('none', 'garbage'):
            with self.subTest(listing=listing):
                t = self.tree().usual()
                r = t.run(LISTING=listing)
                self.ok(t, r)
                self.assertEqual(t.guests(), t.kills())
                self.assertEqual((12, 54, 54), t.first_pass())
                # Pass 2: the stopped ones are gone, the others are remembered.
                self.assertEqual(sorted(t.pids.values()), sorted(t.looked_at()))

    def test_a_namespace_the_listing_cannot_read_is_left_to_the_look(self):
        t = self.tree()
        t.add('host', HOST_NS, HOST_DEV)
        odd = t.add('guest-odd', None, GUEST_DEV + 1)
        os.symlink('mnt:[odd]', t.proc / str(odd) / 'ns' / 'mnt')
        r = t.run(guest_ns='mnt:[odd]')
        self.ok(t, r)
        self.assertEqual([odd], t.kills())
        self.assertEqual((1, 1, 2), t.first_pass())

    def test_a_listing_that_stops_halfway_leaves_the_rest_to_the_look(self):
        # Both halves end inside a line that would pass a process of the guest over if it were
        # taken: the namespace half names guest-init as One UI's, the root half puts guest-app0 on
        # One UI's device. In the second case the root half prints nothing, so the cut namespace
        # line is the listing's last. Looked at besides the guest's own and the zombie: the
        # processes the listing left out and, in the first case, the one whose root line the cut
        # namespace line ran into.
        for guest_dev, roots, counts in ((str(GUEST_DEV), '', (12, 16, 54)), ('', 'none', (6, 10, 54))):
            with self.subTest(guest_dev=guest_dev):
                t = self.tree().usual()
                missing = [t.pids['host3'], t.pids['host-own-ns'], t.pids['guest-zygote64'], t.pids['guest-app2']]
                r = t.run(guest_dev=guest_dev, LISTING='cut', ROOTS=roots, CUT_PID=t.pids['guest-init'],
                          CUT_ROOT_PID=t.pids['guest-app0'], NOT_LISTED=' '.join(str(p) for p in missing))
                self.ok(t, r)
                self.assertEqual(t.guests(namespace_only=not guest_dev), t.kills())
                self.assertEqual(counts, t.first_pass())

    def test_the_listing_alone_never_stops_a_process(self):
        t = self.tree().usual()
        wrong = [t.pids['host0'], t.pids['host-own-ns']]
        r = t.run(LISTED_AS_GUEST=' '.join(str(p) for p in wrong))
        self.ok(t, r)
        self.assertEqual(t.guests(), t.kills())
        for pid in wrong:
            self.assertIn(pid, t.looked_at())
            self.assertTrue((t.proc / str(pid)).is_dir())
        # Found to be One UI's once: not looked at again in pass 2, whatever its listing says.
        self.assertEqual(1, t.looked_at().count(wrong[0]))

    def test_a_process_that_joins_the_guest_after_the_listing_goes_in_the_next_pass(self):
        t = self.tree().usual()
        late = t.add('late-helper', HOST_NS, HOST_DEV)
        r = t.run(JOINS_AFTER_LISTING=late)
        self.ok(t, r)
        self.assertEqual(sorted(t.guests() + [late]), t.kills())
        self.assertEqual(3, len(t.lines('listings')))                       # pass 3 found nothing left

    def test_a_process_that_does_not_die_fails_the_restart(self):
        t = self.tree().usual(hosts=5)
        stuck = t.pids['guest-system_server']
        r = t.run(SURVIVORS=stuck)
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn('guest processes still running after 5 passes: %d:guest-system_server\n' % stuck, r.stdout)
        self.assertNotIn('scan done', r.stdout)
        self.assertEqual(5, t.kills().count(stuck))
        self.assertEqual(sorted(set(t.guests())), sorted(set(t.kills())))

    def test_one_ui_alone_means_one_pass_and_no_look(self):
        t = self.tree()
        for i in range(30):
            t.add('host%d' % i, HOST_NS, HOST_DEV)
        r = t.run()
        self.ok(t, r)
        self.assertEqual([], t.kills())
        self.assertEqual((0, 0, 30), t.first_pass())
        self.assertEqual(1, len(t.lines('listings')))


class RealStatTest(unittest.TestCase):
    """The listing's filter against this machine's own ls and stat output (no loop, no kill)."""

    def test_the_filter_reads_what_stat_prints(self):
        loop = scan_loop()
        program = "not_guest_awk='" + loop.split("not_guest_awk='", 1)[1].split("'\n", 1)[0] + "'\n"
        self.assertNotIn('kill', program)
        me = os.getpid()
        listing = ("{ ls -l /proc/%d/ns/mnt /proc/%d/nothing; stat -L -c '%%d %%n' /proc/%d/root /proc/%d/nothing; } 2>/dev/null"
                   % (me, me, me, me))
        probe = subprocess.run(['sh', '-c', listing], capture_output=True, text=True)
        rows = [x.split() for x in probe.stdout.splitlines()]
        if len(rows) != 2:
            self.skipTest('this machine does not show its own namespace link')
        ns, dev = rows[0][-1], rows[1][0]
        self.assertEqual(ns, os.readlink('/proc/%d/ns/mnt' % me))
        awk = 'busybox awk' if shutil.which('busybox') else 'awk'       # the phone's is busybox's

        def filtered(guest_ns, guest_dev):
            r = subprocess.run(['sh', '-c', program + listing + ' | ' + awk + ' -v ns="$1" -v dev="$2" "$not_guest_awk"',
                                'filter-test', guest_ns, guest_dev], capture_output=True, text=True)
            self.assertEqual('', r.stderr)
            return r.stdout.split()

        self.assertEqual([str(me)], filtered('mnt:[1]', '1'))               # another namespace, another device
        self.assertEqual([], filtered(ns, '1'))                       # in the guest's namespace
        self.assertEqual([], filtered('mnt:[1]', dev))                      # on the guest's root
        self.assertEqual([str(me)], filtered('mnt:[1]', ''))                # no device to tell by
        self.assertEqual([], filtered(ns, ''))


if __name__ == '__main__':
    unittest.main()
