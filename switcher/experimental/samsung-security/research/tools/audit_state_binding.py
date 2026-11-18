"""Bounded offline state-path evidence; never opens live credential state or a device."""
import argparse, hashlib, json, runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'out/construction-state'
ARCHIVES={
 'samsung-framework':('../firmware/samsung/framework.jar','8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'),
 'samsung-services':('../firmware/samsung/runtime-20261104/services.jar','def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'),
 'coloros-framework':('../firmware/donor/extracted/system/framework/framework.jar','d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
}
QUERIES=[
 ('samsung-framework','android.app.ContextImpl',('getDatabasePath','getDatabasesDir','getDataDir','createDeviceProtectedStorageContext','isDeviceProtectedStorage','isCredentialProtectedStorage')),
 ('coloros-framework','android.app.ContextImpl',('getDatabasePath','getDatabasesDir','getDataDir','createDeviceProtectedStorageContext','isDeviceProtectedStorage','isCredentialProtectedStorage')),
 ('samsung-framework','android.app.LoadedApk',('getDataDirFile','getDeviceProtectedDataDirFile','getCredentialProtectedDataDirFile')),
 ('samsung-framework','android.os.Environment',('<clinit>','getDirectory','getDataDirectory','getDataSystemDirectory','getDataSystemDeDirectory','getDataSystemCeDirectory','getUserSystemDirectory')),
 ('coloros-framework','android.os.Environment',('<clinit>','getDirectory','getDataDirectory','getDataSystemDirectory','getDataSystemDeDirectory','getDataSystemCeDirectory','getUserSystemDirectory')),
 ('samsung-framework','android.database.sqlite.SQLiteOpenHelper',('<init>','getDatabaseLocked')),
 ('samsung-services','com.android.server.biometrics.sensors.BiometricUserState',('<init>','scheduleWriteStateLocked','getFile','readStateSyncLocked','doWriteState')),
 ('samsung-services','com.android.server.biometrics.sensors.fingerprint.FingerprintUtils',('getInstance$1',)),
 ('samsung-services','com.android.server.StorageManagerService',('connectVold$1','resetIfBootedAndConnected','restoreSystemUnlockedUsers','lockCeStorage')),
 ('samsung-services','com.android.server.StorageManagerService$Lifecycle',('<init>','onStart','onBootPhase')),
 ('samsung-services','com.android.server.StorageManagerService$Callbacks',('handleMessage',)),
 ('samsung-services','com.android.server.biometrics.sensors.BiometricUserState$$ExternalSyntheticLambda0',('run',)),
 ('samsung-framework','android.os.Environment',('getDirectoryPath',)),
 ('samsung-services','com.android.server.locksettings.LockSettingsService',('migrateLockSettingsDB','migrateSpblob')),
 ('samsung-services','com.android.server.locksettings.LockSettingsStorage$DatabaseHelper',('onCreate','onUpgrade','onDowngrade')),
 ('samsung-framework','com.samsung.android.lock.SPBnRManager',('<clinit>','init','startWrite','finishWrite','setProtectorIdForBackup','getBackupDirectory','getOriginalDirectory')),
 ('samsung-framework','com.samsung.android.lock.SPBnRManager',('getBackupDirectoryForUser','getSyntheticPasswordDirectoryForUser','ensureSPBnRDirectoryForUser','resetMode','checkIntegrity','startBackup','startRestore')),
 ('samsung-services','com.android.server.locksettings.LockSettingsService',('setLong',)),
 ('samsung-framework','android.os.Environment',('getEnvPath','prep')),
 ('coloros-framework','android.os.Environment',('getDirectoryPath','getEnvPath','prep')),
 ('samsung-framework','android.util.AtomicFile',('<init>','finishWrite','rename')),
 ('samsung-services','com.android.server.biometrics.sensors.fingerprint.FingerprintUserState',('getLegacyFileName',)),
]
def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def assemble(results):
 """Export authored assertions and handles, never raw instruction text."""
 facts=[];bodies=[]
 for key,r in results.items():
  if sha(ROOT/r['raw'])!=r['rawSha256']:raise ValueError('Raw changed: '+key)
  for row in map(json.loads,(ROOT/r['raw']).read_text().splitlines()):
   if row['record']=='method':bodies.append((key,r,row))
 old=json.loads((ROOT/'out/storage-keys/java-receipts.json').read_text())
 for key,r in old.items():
  if key not in ('com.android.server.locksettings.LockSettingsStorage','com.android.server.locksettings.PasswordSlotManager','com.android.server.locksettings.SyntheticPasswordManager'):continue
  if sha(ROOT/r['raw'])!=r['rawSha256']:raise ValueError('Reused raw changed')
  for row in map(json.loads,(ROOT/r['raw']).read_text().splitlines()):
   if row['record']=='method':bodies.append(('reused:'+key,r,row))
 def check(fid,query,method,need):
  selected=[(r,row) for key,r,row in bodies if key==query and row['body']['signature']==method]
  if len(selected)!=1:raise ValueError('Exact method missing/ambiguous: '+fid)
  r,row=selected[0];code=row['body']['instructions'];pcs=[]
  for fragment in need:
   hits=[i['pc'] for i in code if fragment in i.get('reference','')]
   if not hits:raise ValueError('Source assertion failed: '+fid+' '+fragment)
   pcs.extend(hits)
  facts.append({'id':fid,'classification':'observed-source','owner':row['body']['owner'],'method':method,'normalizedBodySha256':row['normalizedBodySha256'],'evidencePcsDecimal':sorted(set(pcs)),'raw':r['raw'],'rawSha256':r['rawSha256'],'receipt':r['receipt']})
 for archive in ('samsung','coloros'):
  q=archive+'-framework:android.app.ContextImpl'
  check(archive+'-system-context-database-path',q,'getDatabasesDir()Ljava/io/File;',('string=android','string=/data/system','->ensurePrivateDirExists('))
  check(archive+'-relative-database-name',q,'getDatabasePath(Ljava/lang/String;)Ljava/io/File;',('->getDatabasesDir()','->makeFilename('))
  check(archive+'-context-data-selection',q,'getDataDir()Ljava/io/File;',('->isCredentialProtectedStorage()','->isDeviceProtectedStorage()','->getCredentialProtectedDataDirFile()','->getDeviceProtectedDataDirFile()','->getDataDirFile()'))
  q=archive+'-framework:android.os.Environment'
  check(archive+'-environment-data-root',q,'<clinit>()V',('string=ANDROID_DATA','string=/data','->getDirectoryPath('))
  check(archive+'-sp-base',q,'getDataSystemDeDirectory(I)Ljava/io/File;',('->getDataDirectory()','string=system_de'))
  check(archive+'-biometric-base',q,'getUserSystemDirectory(I)Ljava/io/File;',('->getDataSystemDirectory()','string=users'))
 check('sqlite-context-open','samsung-framework:android.database.sqlite.SQLiteOpenHelper','getDatabaseLocked(Z)Landroid/database/sqlite/SQLiteDatabase;',('->mContext:','->getDatabasePath(','->openDatabase(','->onCreate(','->onUpgrade('))
 q='samsung-services:com.android.server.biometrics.sensors.BiometricUserState'
 check('fingerprint-constructor-path-migration',q,'<init>(Landroid/content/Context;Ljava/lang/String;I)V',('->getUserSystemDirectory(','->getLegacyFileName()','->renameTo(','->readStateSyncLocked()'))
 check('fingerprint-parse-recovery',q,'readStateSyncLocked()V',('->delete()','AsyncTask;->execute(','->mIsInvalidBiometricState:'))
 check('fingerprint-sensor-filename','samsung-services:com.android.server.biometrics.sensors.fingerprint.FingerprintUtils','getInstance$1(I)Lcom/android/server/biometrics/sensors/fingerprint/FingerprintUtils;',('string=settings_fingerprint_','string=.xml'))
 check('fingerprint-asynchronous-file-write','samsung-services:com.android.server.biometrics.sensors.BiometricUserState$$ExternalSyntheticLambda0','run()V',('AtomicFile;->startWrite()','AtomicFile;->finishWrite(','AtomicFile;->failWrite('))
 q='samsung-services:com.android.server.StorageManagerService'
 check('vold-connect-active-listener',q,'connectVold$1()V',('string=vold','->linkToDeath(','IVold;->setListener(','IVold;->getUnlockedUsers()'))
 check('storage-reset-mutates-native-owner',q,'resetIfBootedAndConnected()V',('->mBootCompleted:','->mDaemonConnected:','->onReset(','IVold;->reset()','IVold;->onUserAdded(','->serialNumber:I','->restoreSystemUnlockedUsers('))
 check('storage-recover-unlocked-users',q,'restoreSystemUnlockedUsers(Landroid/os/UserManager;Ljava/util/List;[I)V',('->isUserRunning(','->isUserUnlockingOrUnlocked(','IVold;->onUserStarted(','->sendToTarget()'))
 check('storage-lifecycle-publishes-and-attaches','samsung-services:com.android.server.StorageManagerService$Lifecycle','onStart()V',('LocalServices;->addService(','->publishBinderService(','->connectVold$1()'))
 check('storage-handler-reset','samsung-services:com.android.server.StorageManagerService$Callbacks','handleMessage(Landroid/os/Message;)V',('->resetIfBootedAndConnected()',))
 q='samsung-services:com.android.server.locksettings.LockSettingsService'
 check('db-migration-decisions',q,'migrateLockSettingsDB()V',('string=PRAGMA integrity_check(1)','string=locksettings_db_backup','string=locksettings_db_restore','->setLong('))
 check('sp-migration-recovery',q,'migrateSpblob()V',('SPBnRManager;->init(','SPBnRManager;->resetMode()','SPBnRManager;->setProtectorIdForBackup(','SPBnRManager;->startBackup()','SPBnRManager;->checkIntegrity()'))
 check('migration-flags-route-to-storage','samsung-services:com.android.server.locksettings.LockSettingsService:setLong','setLong(Ljava/lang/String;JI)V',('->checkWritePermission()','LockSettingsStorage;->setString('))
 check('fresh-db-oncreate-policy','samsung-services:com.android.server.locksettings.LockSettingsStorage$DatabaseHelper','onCreate(Landroid/database/sqlite/SQLiteDatabase;)V',('->execSQL(','string=ro.lockscreen.disable.default','string=lockscreen.disabled','->writeKeyValue('))
 q='reused:com.android.server.locksettings.LockSettingsStorage'
 check('storage-backup-restore-dispatch',q,'setString(Ljava/lang/String;Ljava/lang/String;I)V',('->KEY_TO_DB_RESTORE:','->restoreLockSettingsDB()','->KEY_TO_DB_BACKUP:','->backupLockSettingsDB()'))
 check('db-original-literal-path',q,'getOriginDbName()Ljava/lang/String;',('string=/data/system/','->getDatabaseName()'))
 check('db-backup-literal-return-path',q,'getBackupDbName()Ljava/lang/String;',('string=/data/sec_backup_sys_de/locksetting/','string=/data/system/','string=.bak'))
 check('sp-file-local-write-boundary',q,'writeFile(Ljava/io/File;[BZ)V',('SPBnRManager;->startWrite(','AtomicFile;->finishWrite(','SPBnRManager;->finishWrite(','->fsyncDirectory('))
 check('sqlite-local-transaction-boundary',q,'writeKeyValue(Landroid/database/sqlite/SQLiteDatabase;Ljava/lang/String;Ljava/lang/String;I)V',('->beginTransaction()','->setTransactionSuccessful()','->endTransaction()'))
 q='samsung-framework:com.samsung.android.lock.SPBnRManager:getBackupDirectoryForUser,getSyntheticPasswordDirectoryForUser,ensureSPBnRDirectoryForUser,resetMode,checkIntegrity,startBackup,startRestore'
 check('sp-backup-directory',q,'getBackupDirectoryForUser(I)Ljava/io/File;',('string=/data/sec_backup_de/','string=spblob/'))
 check('sp-backup-original-directory',q,'getSyntheticPasswordDirectoryForUser(I)Ljava/io/File;',('->getDataSystemDeDirectory(','string=spblob/'))
 check('sp-backup-integrity-recovery',q,'checkIntegrity()Z',('->checkValidState(','->startBackuplist(','->startRestorelist('))
 check('sp-bnr-write-rename','samsung-framework:com.samsung.android.lock.SPBnRManager','startWrite(Ljava/io/File;)Ljava/io/File;',('->hasFsverity(','string=.bnr','->renameTo('))
 check('weaver-slot-map-path','reused:com.android.server.locksettings.PasswordSlotManager','getSlotMapDir()Ljava/lang/String;',('string=/metadata/password_slots',))
 check('weaver-init-refresh','reused:com.android.server.locksettings.SyntheticPasswordManager','getWeaverServiceLocked()Landroid/hardware/weaver/IWeaver;',('->getConfig()','->getUsedWeaverSlots()','->refreshActiveSlots('))
 check('atomicfile-replaces-base','samsung-framework:android.util.AtomicFile','finishWrite(Ljava/io/FileOutputStream;)V',('FileUtils;->sync(','->mNewName:','->mBaseName:','->rename(','string=Failed to sync file output stream'))
 check('atomicfile-rename-failure-logging','samsung-framework:android.util.AtomicFile','rename(Ljava/io/File;Ljava/io/File;)V',('->renameTo(','string=Failed to rename ',))
 check('fingerprint-legacy-filename','samsung-services:com.android.server.biometrics.sensors.fingerprint.FingerprintUserState','getLegacyFileName()Ljava/lang/String;',('string=settings_fingerprint.xml',))
 inputs=json.loads((ROOT/'inventory/inputs.json').read_text());sources=[]
 ranges={'guest_prepare.sh':[(19,24),(39,49),(2454,2466),(2505,2509),(3233,3259)],'guest_start.sh':[(12,18),(40,48),(610,616)],'oneos_switch.sh':[(337,344),(1406,1418)],'return_to_oneui.sh':[(341,360),(368,374)]}
 for name,spans in ranges.items():
  item=next(f for f in inputs['files'] if f['path'].endswith('/'+name));path=ROOT.parent/item['path']
  if sha(path)!=item['sha256']:raise ValueError('OneOS source changed: '+name)
  sources.append({'path':'../'+item['path'],'sha256':item['sha256'],'lineSpansInclusive':spans,'classification':'observed-source; installation unverified'})
 target=ROOT/'inventory/construction-state.json'
 data={'schema':'construction-state/v1','status':'STATIC_PATH_EDGES_RESOLVED_LIVE_BINDING_AND_TRANSFER_OPEN','goal':'GOAL.md','oneosCommit':inputs['oneosCommit'],'readerQueries':len(results),'selectedMethodBodies':sum(len(r['selectedMethodProofs']) for r in results.values()),'checkedSourceAssertions':facts,'oneosScriptAnchors':sources,'javaReceipts':'out/construction-state/java-receipts.json','javaReceiptsSha256':sha(WORK/'java-receipts.json'),'reusedStorageInventory':{'path':'inventory/storage-keys.json','sha256':sha(ROOT/'inventory/storage-keys.json')},'toolSha256':sha(Path(__file__)),'classification':{'runtimeVerified':False,'oemExecuted':False,'phoneActions':False,'privateStateReadOrCopied':False},'unresolved':['Actual installed bridges.sh, patched Java/native bytes, effective mount graph and ANDROID_DATA for every authority process','Original user IDs/profile ownership/serials and physical DB/SP/Weaver/fingerprint/recovery paths; no live identities acquired','Exact exclusive-writer acquisition and native/session/write drain acknowledgments across Java process death','Trusted reconciliation after uncertain hardware or key/storage commit; no cross-resource atomic rollback established','Scope-specific core key/recovery dependencies; optional OPPO RPMB/RoR/presentation DBs need not become authoritative','Device acceptance: reciprocal PIN/FP, fresh operation-bound keys, intended CE/data access and legitimate invalidations after return/reboot']}
 data['stateBindings']=[
  {'state':'users/profiles/serials','owner':'same Samsung logical authority and actual UserManager identity source','physicalPath':'not established by this bounded path selection','gate':'before recoverable cleanup, storage reset, provider or credential construction'},
  {'state':'locksettings DB','owner':'original credential authority','sourcePath':'android package Context: /data/system/locksettings.db; other Context: selected dataDir/databases/locksettings.db','livePhysicalBinding':'unknown','gate':'before SQLite helper opens or migration runs'},
  {'state':'synthetic-password files','owner':'same user/protector authority','sourcePath':'ANDROID_DATA(default /data)/system_de/<u>/spblob; Samsung virtual-user alternative system/users/<u>/spblob','livePhysicalBinding':'unknown','gate':'before protector inventory, unwrap, migration or Weaver attach'},
  {'state':'Weaver allocation map','owner':'same hardware slots plus original mode/current protector inventory','sourcePath':'/metadata/password_slots/slot_map','guestSourceConflict':'guest_start conditional tmpfs on /metadata','livePhysicalBinding':'unknown','gate':'before getWeaverServiceLocked/refreshActiveSlots'},
  {'state':'fingerprint metadata','owner':'same Samsung user/sensor/HAL enrollment authority','sourcePath':'ANDROID_DATA(default /data)/system/users/<u>/settings_fingerprint_<sensor>.xml; legacy settings_fingerprint.xml under same directory','livePhysicalBinding':'unknown','gate':'before first provider getBiometricsForUser/userstate constructor'},
  {'state':'core original recovery state','owner':'same authority and current trusted recovery policy','sourcePath':'DB backup actual return /data/system/locksettings.db.bak; SP backup /data/sec_backup_de/<u>/spblob; transient .bnr beside original SP files','livePhysicalBinding':'unknown','gate':'before systemReady migration/ordinary original writes; never export to PC or replay stale state'},
  {'state':'native key/FBE/hardware state','owner':'retained actual vold, keystore2, Gatekeeper, KeyMint/Weaver/fingerprint services and their hardware identities','sourcePath':'see storage-keys native ledger; excluded private-state roots were not acquired','livePhysicalBinding':'unknown','gate':'before native service attachment or cryptographic mutation'},
  {'state':'guest presentation metadata/app data','owner':'guest runtime','sourcePath':'staged guest data trees and current installed bridge set','gate':'keep separate unless an exact core security route proves a binding necessary; no whole-/data bind or optional OPPO DB preservation requirement'}]
 data['handoffConditions']={'classification':'required design conditions; no implemented lease or drain mechanism','acquire':['identify actual process/mount/native-service/user namespace and pinned runtime bytes','complete destructive guest preparation without any authoritative-state mount under stage','retain one authority generation/exclusive writer before eager constructors or native listener attachment','install narrow physical state bindings after final guest metadata mount and before authority startup'], 'quiesce':['stop new credential/enrollment/policy mutations and stale generation callbacks','account for in-flight verification reenroll, blob upgrade, async metadata writes and native operations','obtain real per-owner completion and durable-state acknowledgments; process death alone is insufficient'], 'transfer':['pending/uncertain mutation blocks competing startup and cache reuse','successor uses same current physical state; never snapshot/replay a credential DB or raw secret backup','reconcile through genuine original policy/recovery and current identities; no general hardware rollback asserted','publish enabled guest only after all construction, policy, key and data dependencies are owned; otherwise disabled and fail closed']}
 target.write_text(json.dumps(data,indent=2)+'\n')
 print('PASS '+str(len(facts))+' exact source assertions; '+str(len(sources))+' pinned OneOS source files')
def main():
 argparse.ArgumentParser(description=__doc__).parse_args()
 WORK.mkdir(parents=True,exist_ok=True)
 for path,pin in ARCHIVES.values():
  if sha(ROOT/path)!=pin:raise ValueError('Archive input drift')
 ledger=WORK/'java-receipts.json'
 results=json.loads(ledger.read_text()) if ledger.exists() else {}
 read=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive']
 used=set()
 for archive,owner,names in QUERIES:
  base=archive+':'+owner
  key=base if base not in used else base+':'+','.join(names)
  used.add(base)
  if key in results:
   r=results[key]
   if sha(ROOT/r['raw'])!=r['rawSha256']:raise ValueError('Frozen raw drift: '+key)
   declared=r['selectedClassDeclarations']
   if len(declared)!=1 or r['archiveSha256']!=ARCHIVES[archive][1]:raise ValueError('Cached query source differs')
   expected=[m['signature'] for m in declared[0]['methods'] if m['signature'].split('(')[0] in names]
   if expected!=r['query']['exactMethods']:raise ValueError('Cached selector differs; use a separate bounded query key')
   continue
  path,pin=ARCHIVES[archive]
  declaration=read(ROOT/path,pin,class_name=owner,stream='construction-state')
  classes=declaration['selectedClassDeclarations']
  if len(classes)!=1:raise ValueError('Class missing/ambiguous: '+key)
  methods=[m['signature'] for m in classes[0]['methods'] if m['signature'].split('(')[0] in names]
  absent=[n for n in names if not any(s.split('(')[0]==n for s in methods)]
  if not methods:raise ValueError('No selected methods: '+key)
  r=read(ROOT/path,pin,class_name=owner,methods=methods,stream='construction-state')
  r['declarationReceipt']=declaration['receipt'];r['requestedNamesAbsent']=absent
  results[key]=r;ledger.write_text(json.dumps(results,indent=2)+'\n')
  print(key+': '+str(len(r['selectedMethodProofs']))+' bodies; absent '+','.join(absent),flush=True)
 for method in ('backupLockSettingsDB()Z','restoreLockSettingsDB()Z'):
  key='directrefs:'+method
  if key in results:
   if sha(ROOT/results[key]['raw'])!=results[key]['rawSha256']:raise ValueError('Reference raw drift')
   continue
  path,pin=ARCHIVES['samsung-services']
  results[key]=read(ROOT/path,pin,reference='Lcom/android/server/locksettings/LockSettingsStorage;->'+method,stream='construction-state')
  ledger.write_text(json.dumps(results,indent=2)+'\n')
  print(key+': '+str(results[key]['referenceMatchCount'])+' directrefs',flush=True)
 assemble(results)
 for path,pin in ARCHIVES.values():
  if sha(ROOT/path)!=pin:raise ValueError('Archive input drift after audit')
 print('PASS '+str(len(results))+' bounded queries; no OEM/Android execution')
if __name__=='__main__':main()
