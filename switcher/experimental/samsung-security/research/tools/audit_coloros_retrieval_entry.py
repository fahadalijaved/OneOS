"""Bounded source proposal for unsupported old-mode entry rejection. No patching."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'out/retrieval-entry-adaptation'
SETTINGS='33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b'
FRAMEWORK='d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'
P='Lcom/oplus/settings/feature/password/ConfirmLockPasswordFragment;'
T='Lcom/oplus/settings/feature/password/ConfirmLockPatternFragment;'

def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    archives={'settings':('../firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk',SETTINGS),'framework':('../firmware/donor/extracted/system/framework/framework.jar',FRAMEWORK)}
    for path,pin in archives.values():
        if digest(ROOT/path)!=pin:raise ValueError('Source archive drift')
    new=json.loads((OUT/'new-receipts.json').read_text(encoding='utf-8'))
    prior=ROOT/'out/retrieval-capability-leaf/source-lock.json'
    if digest(prior)!='69769c3e09027807455199ccaec768af2d8456cf59504f6fdfeb7a9a4a283ac1':raise ValueError('Frozen prior source lock drift')
    previous=json.loads(prior.read_text(encoding='utf-8'))
    rows=new+previous['receipts'][:2];bodies={};proofs={};receipts={};references=[]
    for q in rows:
        rp=ROOT/q['receipt'];r=json.loads(rp.read_text(encoding='utf-8'))
        if r['archiveSha256'] not in (SETTINGS,FRAMEWORK) or r['readerExitCode'] or not r['archiveAndToolPinsVerifiedBeforeAndAfter'] or digest(ROOT/r['raw'])!=r['rawSha256']:raise ValueError('Reader/raw identity drift')
        receipts[q['receipt']]={'sha256':digest(rp),'raw':r['raw'],'rawSha256':r['rawSha256'],'archiveSha256':r['archiveSha256']}
        for line in (ROOT/r['raw']).read_text(encoding='utf-8').splitlines():
            v=json.loads(line)
            if v['record']=='method':
                key=v['body']['owner']+'->'+v['body']['signature'];bodies[key]=v['body']
                proofs[key]={'bodySha256':v['normalizedBodySha256'],'physicalDex':v['physicalDex'],'logicalHeaderOffset':v['logicalHeaderOffset'],'receipt':q['receipt']}
            if v['record']=='reference':references.append(v)
    facts={}
    def fact(name,key,checks,meaning):
        ins={i['pc']:i for i in bodies[key]['instructions']};out=[]
        for pc,field,value in checks:
            if ins[pc].get(field)!=value:raise ValueError('Exact edge drift '+name+'@'+str(pc))
            out.append({'pc':pc,field:value})
        facts[name]={'classification':'observed-source','method':key,'checked':out,'meaning':meaning}
    view='onCreateView(Landroid/view/LayoutInflater;Landroid/view/ViewGroup;Landroid/os/Bundle;)Landroid/view/View;'
    fact('passwordOldFlag',P+'->'+view,[(12,'reference','string=is_verify_old_password'),(15,'reference','Lcom/oplus/settings/utils/IntentUtils;->getBooleanExtra(Landroid/content/Intent;Ljava/lang/String;Z)Z'),(19,'reference',P+'->mIsVerifyOldPwd:Z')],'Old-mode Intent is parsed before the password fragment view/tracker construction')
    fact('patternOldFlag',T+'->'+view,[(51,'reference','string=is_verify_old_password'),(53,'reference','Lcom/oplus/settings/utils/IntentUtils;->getBooleanExtra(Landroid/content/Intent;Ljava/lang/String;Z)Z'),(57,'reference',T+'->mIsVerifyOldPassword:Z')],'Pattern fragment parses the same old-mode flag, after its layout inflation')
    fact('patternSavedState',T+'->onCreate(Landroid/os/Bundle;)V',[(0,'opcode','INVOKE_SUPER'),(6,'reference','string=extra_chosen_pattern'),(8,'reference','Landroid/os/Bundle;->getByteArray(Ljava/lang/String;)[B'),(12,'reference','Lcom/oplus/settings/utils/LockScreenUtils;->byteArrayToPattern([B)Ljava/util/List;'),(16,'reference',T+'->mChosenPattern:Ljava/util/List;')],'Pattern state restore precedes onCreateView; the payload is not exclusively old-recovery state')
    fact('remotePatternStatePurpose',T[:-1]+'$4;->onPatternDetected(Ljava/util/List;)V',[(71,'targetPc',79),(81,'reference',T+'->access$100('+T+')Z'),(85,'targetPc',125),(89,'reference',T+'->E('+T+'Ljava/util/List;)V'),(94,'reference',T+'->access$200('+T+'Lcom/android/internal/widget/LockscreenCredential;)V')],'The chosen-pattern writer is in the non-old-mode remote-validation path')
    fact('remoteValidationFlag',T+'->access$100('+T+')Z',[(0,'reference','Lcom/android/settings/password/ConfirmDeviceCredentialBaseFragment;->mRemoteValidation:Z')],'Saved chosen pattern must not be rejected/cleared merely by key presence')
    fact('remoteValidateGuess',T+'->access$200('+T+'Lcom/android/internal/widget/LockscreenCredential;)V',[(0,'reference','Lcom/android/settings/password/ConfirmDeviceCredentialBaseFragment;->validateGuess(Lcom/android/internal/widget/LockscreenCredential;)V')],'The preserved pattern state supports genuine remote validation')
    for owner,label in ((P,'password'),(T,'pattern')):
        key=owner+'->onActivityResult(IILandroid/content/Intent;)V'
        if bodies[key]['registerCount']!=6:raise ValueError('Activity result parameter layout changed')
        fact(label+'ResultRouting',key,[(0,'registers',[2,3,4,5]),(42,'literal',4),(42,'registers',[3]),(43,'registers',[4,3]),(43,'targetPc',117),(107,'registers',[3,4]),(117,'literal',-1),(118,'registers',[4,3])],'r3 is requestCode initially, overwritten by constants; the tests compare RESULT code r4, not requestCode')
        fact(label+'DestructiveNonCancel',owner+'->deleteOldPasswordOnVerifyFailed()V',[(4,'literal',4),(5,'reference','Landroid/app/Activity;->setResult(I)V'),(13,'reference','Lcom/oplus/settings/utils/ThreadPoolUtils;->postOnBackgroundThread(Ljava/lang/Runnable;)Ljava/util/concurrent/Future;')],'Custom old-failure result 4 plus background deletion is not a cancellation helper')
        fact(label+'ResetSuccessNotCancel',owner+'->goToResetPassword(Lcom/android/internal/widget/LockscreenCredential;Lcom/android/internal/widget/LockscreenCredential;)V',[(63,'reference','Landroidx/fragment/app/Fragment;->startActivity(Landroid/content/Intent;)V'),(70,'literal',-1),(71,'reference','Landroid/app/Activity;->setResult(I)V')],'Reset navigation reports RESULT_OK; it is not an unavailable/cancel path')
    fact('typedResultStorage','Landroid/app/Activity;->setResult(ILandroid/content/Intent;)V',[(1,'reference','Landroid/app/Activity;->mResultCode:I'),(3,'reference','Landroid/app/Activity;->mResultData:Landroid/content/Intent;')],'Explicit proposed cancelled outcome is code0 with null data; source API stores both fields')
    fact('actualFinishSubmission','Landroid/app/Activity;->finish(I)V',[(54,'reference','Landroid/app/ActivityClient;->finishActivity(Landroid/os/IBinder;ILandroid/content/Intent;I)Z'),(61,'reference','Landroid/app/Activity;->mFinished:Z')],'Finish submits the stored result; no pending authentication/HAL/job drain is acknowledged')
    for suffix,method in (('Password','finishConfirmPassword'),('Pattern','finishConfirmLockPattern')):
        feature='Lcom/oplus/settings/feature/password/ScreenLockFeature;->'+method+'(Lcom/android/settings/password/ConfirmLock'+suffix+';)V'
        fact(suffix+'FeatureFinish',feature,[(11,'reference','Landroid/os/AsyncTask;->setDefaultExecutor(Ljava/util/concurrent/Executor;)V'),(18,'reference','Lcom/oplus/settings/utils/LockScreenUtils;->activityWithPopDownAnim(Landroid/app/Activity;Landroid/content/Intent;)V')],'Enabled native finish resets a process-wide executor and runs transition work; this is not cancellation/join')
    fact('originalEarlyFinishTemplate','Lcom/android/settings/SettingsActivity;->onCreate(Landroid/os/Bundle;)V',[(29,'reference','Lcom/android/settings/SettingsActivity;->finish()V'),(32,'opcode','INVOKE_SUPER'),(35,'opcode','RETURN_VOID'),(36,'opcode','INVOKE_SUPER'),(48,'reference','Lcom/android/settings/SettingsActivity;->createUiFromIntent(Landroid/os/Bundle;Landroid/content/Intent;)V')],'An original finish-plus-super-plus-return template exists; the ordinary UI factory follows super initialization')
    result={'schema':'coloros-retrieval-entry-adaptation/v1','status':'SOURCE_PROPOSAL_ONLY_ROOT_CUT_REVIEW_REQUIRED','patchApproved':False,'patchBuilt':False,'oemCodeExecuted':False,'phoneActions':False,
        'inputs':{k:{'path':v[0],'sha256':v[1]} for k,v in archives.items()},'readerReceipts':receipts,'methodProofs':proofs,'sourceFacts':facts,
        'typedOutcomeProposal':{'unsupported':'Activity.setResult(0,null); request actual finish; no auth success or credential/hardware mutation; finish is not drain','ordinaryCurrentAndRemote':'Preserve original methods and genuine authority/user/challenge/policy; do not reinterpret saved remote-validation pattern as optional old recovery','lateOldResult':'Reject UI admission only when its original optional operation/purpose/user/generation is known; a cancellation result does not roll back committed credentials'},
        'candidateCuts':[
            {'target':'SettingsActivity.onCreate(Bundle) PC48 createUiFromIntent(Bundle,Intent)','proposal':'Typed guarded UI-factory call restricted to the two actual native confirmation activities; unsupported old mode cancels before original fragment creation, ordinary calls delegate unchanged','bounds':['PC36 superclass call already precedes this site: actual restored-fragment ordering must close before using it for saved-state rejection','Concrete/base activity continuations after the common method returns remain; actual finish/adaptor/lifecycle handling must be preserved']},
            {'target':'PasswordFragment.onCreateView entry; PatternFragment.onCreate PC3 and onCreateView entry','proposal':'Reject explicit unsupported is_verify_old_password before optional view/input/tracker work; typed View result would be null only on the rejected path','bounds':['Bare finish+null-view return is not approved: later onResume/onPause use tracker/listener owners','Do not skip required superclass callbacks or pretend pending owners were drained','Do not reject/erase extra_chosen_pattern by presence; it supports remote validation']},
            {'target':'Both fragments.onActivityResult PC3, after original super callback','proposal':'Purpose-bound interception before logging/legacy result forwarding; only known unsupported old-operation completion returns cancelled0/null','bounds':['The original branch tests RESULTCODE4, not requestCode4','Unknown result purpose/generation requires fail-closed admission; never globally cancel requestCode4 or all RESULT_OK results','Actual already-completed credential changes stay authoritative']}],
        'remainingBindings':['Root must choose the exact guard boundary and preserve native Activity/Fragment superclass and adaptor continuations before any byte producer','Close framework restored-fragment ordering and genuine current/remote result tracker purpose/generation','Keep cold admission before optional inputs/jobs; active CountDownTimer.cancel/AsyncTask.cancel and listener-null writes are not stop/join acknowledgements','Keep dedicated Samsung previous-credential recovery separate and reject old PINs at ordinary unlock; no reset/delete/success helper reuse'],
        'limits':['Exact selected original Settings/framework bodies and explicit reference proofs only; no installed, reflection/dynamic or runtime closure','No caller identity, actual UI inflation, queued callback drain, native endpoint or cryptographic result was exercised'],
        'producerSha256':digest(Path(__file__))}
    p=ROOT/'inventory/coloros-retrieval-entry-adaptation.json';p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'facts':len(facts),'methodProofs':len(proofs),'sha256':digest(p),'patchBuilt':False}))

if __name__=='__main__':main()
