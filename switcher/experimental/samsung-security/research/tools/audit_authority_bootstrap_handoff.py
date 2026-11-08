"""Static OneOS0.4.57 authority handoff plan; never executes downloaded source.

Verifies the pinned fourteen-source baseline plus one immutable return script.
No phone, /proc, service, mount, shell-script, credential or native operation.
"""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'out/authority-bootstrap-handoff'
COMMIT='1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe'
RETURN=ROOT/('firmware/authority-bootstrap-handoff/'+COMMIT+'/switcher/assets/return_to_oneui.sh')
RETURN_SHA='04eec2a0b855ddbb89035b6c2d7daeb086e7a094a31be274c3213f79a89b0a03'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,obj):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf8')
def main():
 ledger=ROOT/'inventory/method-review-upstream.json';j=json.loads(ledger.read_text());assert j['commit']==COMMIT and j['release']=='v0.4.57'
 files={};pins=[]
 for item in j['sourceFiles']+j['supplementalFiles']:
  rel=item.get('sourceRelativePath',item['path']);p=ROOT/item['path']if 'sourceRelativePath'in item else ROOT/j['sourceRoot']/rel
  if sha(p)!=item['sha256']:raise ValueError('Immutable input drift '+str(p))
  files[rel]=p.read_text(encoding='utf8').splitlines();pins.append({'sourceRelativePath':rel,'path':p.relative_to(ROOT).as_posix(),'sha256':item['sha256'],'bytes':p.stat().st_size})
 assert len(pins)==14
 if sha(RETURN)!=RETURN_SHA:raise ValueError('Immutable return source drift')
 ret='switcher/assets/return_to_oneui.sh';files[ret]=RETURN.read_text().splitlines()
 pins.append({'sourceRelativePath':ret,'path':RETURN.relative_to(ROOT).as_posix(),'sha256':RETURN_SHA,'bytes':RETURN.stat().st_size,'url':'https://raw.githubusercontent.com/fahadalijaved/OneOS/'+COMMIT+'/'+ret,'scope':'One specifically missing immutable source file; fetched/read only, never executed'})
 facts=[]
 def fact(id,file,a,b,text,need=()):
  lines=files[file];part='\n'.join(lines[a-1:b])
  for token in need:
   if token not in part:raise ValueError('Source anchor missing '+id+' '+token)
  facts.append({'id':id,'sourceRelativePath':file,'firstLine':a,'lastLine':b,'lineSliceSha256':hashlib.sha256(part.encode()).hexdigest(),'classification':'observed source ordering/branch only','fact':text})
 sw='switcher/assets/oneos_switch.sh';prep='switcher/assets/guest_prepare.sh';start='switcher/assets/guest_start.sh'
 fact('init-mount-ns',sw,70,81,'Switch re-execs into init mount namespace when needed; authority view is not separately retained.', ['nsenter','-t 1 -m'])
 fact('stock-baseline',sw,542,545,'Existing return baseline is captured while stock framework is still running; not a credential-operation drain.', ['return_to_oneui.sh','baseline'])
 fact('stop-stock-java',sw,971,999,'Stops stock zygotes, then sends SIGKILL by name to app_process64 and system_server; no quiescence acknowledgement here.', ['ctl.stop zygote','pidof app_process64','pidof system_server'])
 fact('stock-keeper',sw,1000,1012,'Polling keeper repeatedly stops stock zygotes/display/audio classes; polling is not proof of zero producer-restart overlap.', ['while true','ctl.stop zygote','sleep 0.2'])
 fact('prepare-call',sw,1086,1115,'guest_prepare runs after Java kill; its failure and prepare-only mode invoke return. Proposed launch/view hook is immediately before line1087.', ['"$STAGE/guest_prepare.sh"','return_to_oneui.sh'])
 fact('guest-props',sw,1148,1149,'Guest property add occurs after preparation and before takeover; processes share the property service.', ['guest_props.sh',' add '])
 fact('guest-start',sw,1417,1429,'Guest takeover unshares mount namespace and records namespace/root device; no authority process or generation ticket is launched.', ['unshare -m','TAKEOVER_PID=$!','guest_mntns','guest_rootdev'])
 fact('stage-state-removal',prep,2462,2473,'Legacy Weaver-marked staged state is removed from stage; authoritative state must never be bound into preparation scratch.', ['*.weaver','rm -f','locksettings.db'])
 fact('host-data-bridges',prep,3240,3268,'Preparation binds staged app/user/media/cache trees over host paths and mounts staged data into guest root; not a Samsung authority data view.', ['for pair in $BRIDGES','mount --bind','"/data/$h"','"$ROOTFS/data"'])
 fact('guest-root',start,9,48,'Guest makes mounts private, pivots root and detaches old host root; launching authority here uses the guest view.', ['mount --make-rprivate /','pivot_root','/postinstall'])
 fact('guest-classpath',start,106,125,'Guest replaces inherited host classpath variables with derive_classpath output; authority must retain/admit Samsung runtime independently.', ['BOOTCLASSPATH','SYSTEMSERVERCLASSPATH','derive_classpath'])
 fact('guest-metadata',start,608,638,'Guest conditionally mounts fresh tmpfs over metadata for aconfig; this is not the original Samsung password-slot view.', ['tmpfs /metadata','/metadata/aconfig'])
 fact('guest-vold-selection',prep,1249,1281,'Guarded gvld build pair keeps original vold name; fallback guest vold takes canonical vold and does not support in-place return.', ['vold_patched','service.incremental','echo gvld','no return without a reboot'])
 fact('guest-vold-check',start,679,709,'gvld branch verifies original vold PID/name and required patched consumers/rescue configuration; source does not prove live branch/profile.', ['VOLD_NAME=gvld','HOST_VOLD=','host_vold_lost','gvld'])
 fact('guest-vold-start',start,738,744,'Guest starts its own native vold; this must stay isolated from the preserved Samsung vold authority.', ['/system/bin/vold','VOLD_PID=$!'])
 fact('return-native-baseline',ret,70,98,'Baseline records boot ID, properties, APEX/linker views and selected native service PIDs; no Java authority generation or FP/Weaver/KeyMint session drain.', ['HOST_NAMES=','android.system.keystore2.IKeystoreService/default','android.service.gatekeeper.IGateKeeperService','svcpid'])
 fact('return-force-kills',ret,193,229,'Return stops recorder/keepers and force-kills commands matching system_server plus guest zygote; no new authority drain channel.', ['oneos_rec_stop','pkill -9 -f "system_server"','pkill -9 -f "ctl.stop zygote"'])
 fact('return-namespace-kills',ret,256,285,'Return repeatedly SIGKILLs processes sharing guest namespace or root device; a guest-root authority would be included.', ['GUEST_NS=','GUEST_DEV=','kill -9 "$pid"'])
 fact('return-host-data',ret,343,363,'Restores original host data trees before stock start and forces reboot branch if bridges remain.', ['umnt "/data/$d"','ONEOS_RETURN_MODE=reboot'])
 fact('return-state-log-only',ret,368,386,'Protected-state comparison logs changes only; it neither reconciles uncertain commits nor restores old credential state.', ['Logged only','host_state.after','host state changed'])
 fact('return-unmount-stage',ret,389,416,'Detaches stage mount propagation and unmounts deepest stage mounts; borrowed authority code/state views need prior lifetime handling.', ['mount --make-rprivate','umnt -l'])
 fact('return-default-mode',ret,418,474,'Default mode is reboot; inplace requires same-boot baseline/no stage mounts, otherwise reboot or shutdown actions follow.', ['MODE=${ONEOS_RETURN_MODE:-reboot}','MODE=reboot','sys.powerctl reboot,oneos-return'])
 fact('return-failsafe',ret,498,517,'In-place failure path restores properties then requests reboot, with further forced reboot fallbacks; not a no-reboot recovery acknowledgement.', ['restore-persist','reboot,oneos-inplace-failsafe','reboot -f'])
 fact('return-native-owner-gate',ret,689,709,'Before stock start, compares surviving native endpoint PIDs to baseline and refuses early stock Java start; PID equality is not new authority retirement.', ['now=$(svc_pid','One UI\'s vold restarted','! pidof system_server'])
 fact('return-property-policy',ret,710,753,'Restores selected properties and baseline SELinux before stock processes; newly added authority needs separate policy/source lifecycle.', ['restore-persist','setenforce 1'])
 fact('return-native-up',ret,859,874,'Existing GateB requires no guest-root process and selected native/services up before stock Java restart.', ['wait_found','vold keystore2 servicemanager hwservicemanager logd lmkd installd','Gate B'])
 fact('return-stock-reconstruct',ret,876,907,'In-place restarts native zygote-next/netd, then starts stock zygote(s), reconstructing original system_server services.', ['ctl.restart zygote_next','ctl.restart netd','ctl.start zygote'])
 fact('return-stock-postcheck',ret,910,942,'Postcheck watches one system_server PID and user0 unlock/launcher with failure reboot; no cross-OS credential or FP acceptance.', ['One UI\'s system_server did not start','RUNNING_UNLOCKED','up + 30'])
 # Ordering checks address actual integration hooks, not executable readiness.
 assert 999<1011<1087<1149<1418
 assert 193<225<278<351<422<689<740<874<897<920
 phases=[
  {'id':'stock-before-switch','sourceHook':'oneos_switch baseline545, before stop971','requiredCut':'Real stock authority stops admitting new credential/FP writes and drains callbacks/native sessions or reconciles every uncertain commit; capture actual service/source/user/native generation. Existing baseline is insufficient.'},
  {'id':'stock-retired','sourceHook':'after kill999 and keeper1011, before prepare1087','requiredCut':'Confirm original writer retirement and inhibit restart/duplicate publication; SIGKILL or a polling keeper alone does not acknowledge native operation completion.'},
  {'id':'candidate-host-view-launch','sourceHook':'proposed insertion immediately before oneos_switch1087','requiredCut':'Owned unique process launched only after kill window; preserve actual Samsung app_process/bootclasspath/resources/linker/native and physical state/user view before host-data bridges/global guest properties. Controlled legitimate CE/vold propagation and real Context/local owners are required; nothing launched here.'},
  {'id':'guest-admission','sourceHook':'before guest_prepare/guest_start can construct original guest security producers','requiredCut':'Install reviewed guest producer suppression and canonical/alias endpoint plan from scopeB. Admit new generation only after genuine Samsung service/native/state readiness and applied policy, never a shell ready flag.'},
  {'id':'return-quiesce','sourceHook':'new coordinator before return force teardown193-229','requiredCut':'Close new ingress, retain endpoints for owned completion/cancel, drain real credential/FP/hardware/storage work, reconcile uncertainty, then retire exact authority PID/handles/source views. Kill-by-name is not cleanup.'},
  {'id':'stock-handoff','sourceHook':'before return native/stock restart gates689-907','requiredCut':'Dedicated writer and endpoint generation retired; current authoritative state retained, native owners/current mounts valid. Then stock reconstructs and owns next generation; never restore credential snapshots or overlap original LSS with a live dedicated writer.'}]
 report={'schema':'authority-bootstrap-handoff-plan/v1','status':'STATIC_CANDIDATE_ONLY; exclusive writer/process/native/mount handoff unassembled','oneosCommit':COMMIT,'release':'v0.4.57','upstreamLedger':'inventory/method-review-upstream.json','upstreamLedgerSha256':sha(ledger),'inputs':pins,'sourceFacts':facts,'proposedHandoffPhases':phases,'endpointAssumption':'ScopeB proposal only: canonical Samsung-protocol lock_settings and separate guest alias oneos_coloros_lock_settings, both hosted in same dedicated authority process; lifecycle/local channels remain unimplemented','materializedAuthorityProcess':None,'currentEndpointOwners':None,'currentNativeOwners':None,'liveMountView':None,'runtimePhoneAvailable':False,'sourceExecuted':False,'oemExecuted':False,'phoneActions':0,'runtimeAccepted':False,'toolSha256':sha(__file__),'remainingGoNoGo':['Actual Context/user/local-policy/native startup graph under scopeA','Complete guest lookup/producer/lifecycle replacement under scopeB','Old and new writer/native session quiescence and uncertain-write reconciliation','Admitted Samsung process/source/mount/property view before preparation, including controlled CE changes','Exact native endpoint generation including fingerprint/Weaver/KeyMint beyond current HOST_NAMES baseline','Owned return retirement before stock reconstruction, and actual no-reboot acceptance; default/failsafe remains reboot','Live installed profile, PID/native/mount identity and all cross-OS security acceptance']}
 save(ROOT/'inventory/authority-bootstrap-handoff.json',report);print('verified',len(pins),'immutable sources;',len(facts),'bounded ordering facts; static plan only')
if __name__=='__main__':main()
