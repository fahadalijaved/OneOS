#!/usr/bin/env python3
"""Run the real boot event parser with inert local Android command stand-ins."""
from pathlib import Path
import subprocess,tempfile,os,time
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
