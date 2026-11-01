#!/usr/bin/env python3
"""Run the real boot event parser with inert local Android command stand-ins."""
from pathlib import Path
import subprocess,tempfile,os,time,signal
script=(Path(__file__).resolve().parents[1]/'switcher/assets/boot_status.sh').read_text()
with tempfile.TemporaryDirectory(prefix='oneos-status-test-') as t:
 d=Path(t); (d/'generation').write_text('test1\n'); (d/'verbose').write_text('1\n')
 # Use the shipped parser and supervisor, with inert filesystem-local stand-ins.
 source=d/'boot_status.sh'; source.write_text(script.replace('/data/local/tmp/oneos/OneOSBootStatus.dex',str(d/'status.dex')).replace('/sys/fs/cgroup/cgroup.procs',str(d/'cgroup.procs')).replace('/proc/$$/oom_score_adj',str(d/'oom_score_adj')))
 for name, body in {
 'logcat': '''#!/bin/sh
cat <<'EOF'
I/boot_progress_system_run(10): 100
I/boot_progress_pms_start(10): 101
I/am_proc_start(10): [0,101,1000,com.example.guest,service,start]
I/am_proc_died(10): [0,101,com.example.guest,900,0]
I/boot_progress_enable_screen(10): 102
EOF
''',
 'app_process': '#!/bin/sh\nwhile [ ! -f "$ONEOS_BOOT_DIR/stop" ]; do sleep .05; done\n',
 'pidof': '#!/bin/sh\necho 12345\n',
 'getprop': '#!/bin/sh\necho 1\n',
 }.items():
  p=d/name;p.write_text(body);p.chmod(0o755)
 env=os.environ|{'ONEOS_BOOT_DIR':str(d),'PATH':str(d)+':'+os.environ['PATH']}
 p=subprocess.run(['/bin/sh',str(source),'supervise','test1'],env=env,timeout=8,capture_output=True,text=True)
 assert p.returncode==0,(p.stdout,p.stderr)
 events=(d/'events.log').read_text()
 for text in ['Starting system_server','Loading package manager','Starting com.example.guest','Stopped com.example.guest','Display ready']: assert text in events,events
 assert not list(d.glob('*.pipe'))
 assert (d/'stop').exists()
 print('PASS: real event formats, display-ready termination and monitor cleanup')
 (d/'verbose').write_text('0\n'); before=events
 subprocess.run(['/bin/sh','-c','. "$1"; oneos_boot_event "should not appear"','sh',str(source)],env=env,check=True)
 assert (d/'events.log').read_text()==before
 print('PASS: verbose off suppresses process events')

 (d/'stop').unlink()
 (d/'generation').write_text('new-session\n')
 subprocess.run(['/bin/sh',str(source),'supervise','old-session'],env=env,check=True,timeout=5,capture_output=True)
 assert not (d/'stop').exists(), 'old supervisor stopped the new session'
 assert not list(d.glob('*.pipe'))
 print('PASS: an old generation cannot stop a new handoff')

 # The outgoing boot animation finishing must not dismiss a return splash.
 (d/'generation').write_text('test-return\n')
 (d/'framework').unlink(missing_ok=True)
 (d/'logcat').write_text('#!/bin/sh\nexec sleep 20\n')
 (d/'getprop').write_text('#!/bin/sh\nif [ -f "$ONEOS_BOOT_DIR/animation-ended" ]; then echo 1; else echo 0; fi\n')
 supervisor=subprocess.Popen(['/bin/sh',str(source),'supervise','test-return'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 time.sleep(.5)
 (d/'animation-ended').touch()
 time.sleep(.6)
 assert supervisor.poll() is None and not (d/'stop').exists(), 'outgoing animation dismissed the return layer'
 (d/'framework').write_text('test-return\n')
 supervisor.communicate(timeout=4)
 assert (d/'stop').exists()
 print('PASS: outgoing animation cannot dismiss the splash before the new framework starts')

 # Run the independent thaw guard against a harmless stopped local process.
 # This verifies timeout recovery without stopping any phone service.
 thaw=d/'thaw-test.sh'
 thaw.write_text(source.read_text().replace('remaining=180','remaining=1'))
 sleeper=subprocess.Popen(['sleep','20'])
 try:
  identity='fixture-process'
  # Linux /proc is unavailable on macOS; keep the real guard and signals, only
  # replace its process identity lookup with the fixture's known identity.
  thaw.write_text(thaw.read_text().replace('cat "/proc/$1/stat" 2>/dev/null | sed \'s/.*) //\' | awk \'{print $20}\'', 'echo fixture-process'))
  (d/'held_composer').write_text(f'{sleeper.pid} {identity} return-test\n')
  os.kill(sleeper.pid,signal.SIGSTOP)
  subprocess.run(['/bin/sh',str(thaw),'thaw',str(sleeper.pid),identity,'return-test'],env=env,check=True,timeout=4,capture_output=True)
  # A running sleeper must respond to TERM. A stopped one needs CONT first.
  sleeper.terminate(); sleeper.wait(timeout=2)
  print('PASS: independent bounded guard thaws the held display if return stalls')
 finally:
  if sleeper.poll() is None:
   os.kill(sleeper.pid,signal.SIGCONT); sleeper.kill(); sleeper.wait()

 sleeper=subprocess.Popen(['sleep','20'])
 try:
  (d/'held_composer').write_text(f'{sleeper.pid} fixture-process normal-return\n')
  os.kill(sleeper.pid,signal.SIGSTOP)
  subprocess.run(['/bin/sh','-c','. "$1"; oneos_boot_release_display','sh',str(thaw)],env=env,check=True,timeout=2)
  assert not (d/'held_composer').exists()
  sleeper.terminate(); sleeper.wait(timeout=2)
  print('PASS: normal compositor restart releases the exact held process before continuing')
 finally:
  if sleeper.poll() is None:
   os.kill(sleeper.pid,signal.SIGCONT); sleeper.kill(); sleeper.wait()

 # Restore the inert commands used by the remaining entry tests.
 (d/'stop').unlink(missing_ok=True)

 # Exercise the actual compositor decision with a delayed first frame.
 switch=(Path(__file__).resolve().parents[1]/'switcher/assets/oneos_switch.sh').read_text()
 decision=switch[switch.index('SF_FROZEN=""'):switch.index('setprop ctl.stop zygote',switch.index('SF_FROZEN=""'))]
 (d/'data').mkdir()
 (d/'gap.log').write_text('Status: ok\nsettled now\n')
 fixture=d/'freeze-test.sh'
 fixture.write_text('. "$1"\n'
  'STAGE=$ONEOS_BOOT_DIR\nGAP_SPLASH_LOG=$STAGE/gap.log\nONEOS_VERBOSE_BOOT=1\n'
  'oneos_boot_ready() { [ -f "$ONEOS_BOOT_DIR/first-frame" ]; }\n'
  'pidof() { echo 12345; }\n'
  'kill() { echo "$*" >> "$ONEOS_BOOT_DIR/signals"; }\n'+decision)
 producer=subprocess.Popen(['/bin/sh','-c','sleep .4; touch "$ONEOS_BOOT_DIR/first-frame"'],env=env)
 result=subprocess.run(['/bin/sh',str(fixture),str(source)],env=env,timeout=8,capture_output=True,text=True)
 producer.wait(timeout=2)
 assert result.returncode==0,(result.stdout,result.stderr)
 assert 'kept live for status updates' in result.stdout,result.stdout
 assert not (d/'signals').exists(), 'compositor frozen before the delayed renderer could post its frame'
 print('PASS: delayed renderer handshake keeps the compositor live')
 (d/'first-frame').unlink()
 fixture.write_text(fixture.read_text().replace('oneos_boot_wait_ready 5','oneos_boot_wait_ready 0'))
 result=subprocess.run(['/bin/sh',str(fixture),str(source)],env=env,timeout=2,capture_output=True,text=True)
 assert '-STOP 12345' in (d/'signals').read_text(), (result.stdout,result.stderr)
 print('PASS: unavailable renderer retains the bounded static fallback')

 writers=[subprocess.Popen(['/bin/sh','-c','. "$1"; for n in 1 2 3 4 5; do oneos_boot_write status "$2:$n"; done','sh',str(source),str(i)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for i in range(3)]
 for writer in writers:
  stdout,stderr=writer.communicate(timeout=5)
  assert writer.returncode==0 and not stderr,(stdout,stderr)
 assert (d/'status').read_text().strip() in {f'{i}:5' for i in range(3)}
 print('PASS: concurrent status writers publish complete lines without temporary-file collisions')

 # Run the real return-start and framework-stop blocks. The outgoing framework
 # can blank its display on death: the return frame must already be held then.
 returning=(Path(__file__).resolve().parents[1]/'switcher/assets/return_to_oneui.sh').read_text()
 begin=returning[returning.index('echo oneos_return > /sys/power/wake_lock'):returning.index('# The call keepers')]
 begin=begin.replace('/sys/power/wake_lock',str(d/'wake_lock'))
 stop=returning[returning.index('oneos_boot_event "Stopping guest system_server"'):returning.index('# The heat cap')]
 mock=d/'return-fixture'; mock.mkdir()
 (mock/'boot_status.sh').write_text('''
oneos_boot_begin() { echo return-frame > "$S/frame"; }
oneos_boot_wait_ready() { return 0; }
oneos_boot_hold_display() { cp "$S/frame" "$S/held"; }
oneos_boot_event() { :; }
''')
 fixture=d/'return-order.sh'
 fixture.write_text('S="$1"\n'+begin+'''
pkill() { [ ! -f "$S/held" ] && echo blank > "$S/frame"; return 0; }
pidof() { echo 123; }
kill() { [ ! -f "$S/held" ] && echo blank > "$S/frame"; return 0; }
'''+stop)
 subprocess.run(['/bin/sh',str(fixture),str(mock)],check=True,timeout=3)
 assert (mock/'held').read_text().strip()=='return-frame'
 assert (mock/'frame').read_text().strip()=='return-frame'
 assert (d/'wake_lock').read_text().strip()=='oneos_return'
 print('PASS: return splash and wake lock precede outgoing framework teardown')
