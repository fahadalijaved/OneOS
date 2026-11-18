"""Verify bounded app-prompt parcel/request/action source contracts.

No converter, runtime carrier, OEM class or Android Binder is executed.
Run --report to regenerate only bounded derived metadata from frozen source pins.
"""
import argparse,hashlib,json
from pathlib import Path
PROJECT=Path(__file__).resolve().parent.parent
PARENT=PROJECT.parent
SOURCES = [{'raw': 'firmware/prompt-wire-contract/20261105T201116240116Z-fd672930f990420690a9b67bd56f8e2a.jsonl',
  'rawSha256': '8fce044c82eb563fc51ff068f3593aced3be785b543c07a31571355d29e9eb4a',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201116240116Z-fd672930f990420690a9b67bd56f8e2a/receipt.json',
  'receiptSha256': '03a07fa24f41df6dd3e1ed7d9d121b3ed9cf9fa8280498aa5455c912634be7eb'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201117006256Z-d38808c13da44c3c9545a31538b741ae.jsonl',
  'rawSha256': 'e4f79f8f934547a11baee09628406ea42203bb9a063ce0e38435bbb29f3a32bd',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201117006256Z-d38808c13da44c3c9545a31538b741ae/receipt.json',
  'receiptSha256': '59b9ebd0186a59205bb91396141a3e5c6e216a2be9a18e0a5683cdd26e84f686'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201117755906Z-12bc7e44d1fd4752b064f2b896c3ac6b.jsonl',
  'rawSha256': '3e744420a07f6ffa4a43f7cd8be74fe07eca5e9d4ee0663bab62b7d0e1ec0a64',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201117755906Z-12bc7e44d1fd4752b064f2b896c3ac6b/receipt.json',
  'receiptSha256': 'ad82f5e6283c88c867f3c02304b87153a88d3a67e2db17f327ae06f73d5986ba'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201146766222Z-ec1be8a29207485b8701472fb7b93fce.jsonl',
  'rawSha256': '0cad4d2d3c970d85d98513126fd3ba9712baa97628fe53cb09f519bda77c57c4',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201146766222Z-ec1be8a29207485b8701472fb7b93fce/receipt.json',
  'receiptSha256': '3ef8ecbe100bc3d8634d38943177c01fffcae8fb8b7743a791ef76260ccace1d'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201147540846Z-1e9f75a1353c4c7dbc7b498a92a75430.jsonl',
  'rawSha256': '3a1df4708e4459dc47384605157c31ee6613f33fe29aac1e805ffbfbb181400e',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201147540846Z-1e9f75a1353c4c7dbc7b498a92a75430/receipt.json',
  'receiptSha256': '3897ba502fe785a007d5f9e0aa5c45dac7899a39dd2641c8078907d945a80997'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201148305963Z-dcd0e2dafb514c39a4ae6b21ba170703.jsonl',
  'rawSha256': 'c753d52b436dd03a478c1861b72c07c0b0f4ed969f75d25f93a26eb170b0da99',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201148305963Z-dcd0e2dafb514c39a4ae6b21ba170703/receipt.json',
  'receiptSha256': '070e440d03f9e28a937b8456ad97dea701a8245000cb253608e2775e621054ac'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201149066802Z-7da8908139e74128a1f8ac0b0a0aadaf.jsonl',
  'rawSha256': '43b2c9b88006640f5bfef84b8ab19b062deffd1d27c8256ae00623ef3c37f06c',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T201149066802Z-7da8908139e74128a1f8ac0b0a0aadaf/receipt.json',
  'receiptSha256': 'f5c5826155d72e4072490dfbf8857e38e2b0d3b2e999c9ed0a4ddba104763b71'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201149779914Z-8cb4d051b86a4ec4a17a86e9b3019230.jsonl',
  'rawSha256': 'bfb550c5b2ec508ebe4dfe030f74141bb658870623ea69addb636daecc8dd576',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T201149779914Z-8cb4d051b86a4ec4a17a86e9b3019230/receipt.json',
  'receiptSha256': 'f8603709f23d22cf974f1d4a093a388d905e82f3d8972062b3e428b74969e244'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201150517013Z-89f16700a594453a8e2383e5b5261e07.jsonl',
  'rawSha256': '95150db451b2736d29ba1ceb4d93429a5e4307cf11c1a03b7ae316c1a5a03dee',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T201150517013Z-89f16700a594453a8e2383e5b5261e07/receipt.json',
  'receiptSha256': '5ef24f46afd2bfdcd37d032a9ae9b7cb74958cb0a81c01c55d9529a332d01379'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201151263651Z-7f0969667c214bea8d3224e475ce95a4.jsonl',
  'rawSha256': 'c5da2c7e7fd51b7c3491ec41ce40463e2ba8f78d6e0863de288c1cafa9e519f8',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T201151263651Z-7f0969667c214bea8d3224e475ce95a4/receipt.json',
  'receiptSha256': '382233321f86cf3d966260733319cef35000f3ec2c0df55461582f1fb3547fe6'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201152014776Z-903582a09512436dad7ad36b655a5dd8.jsonl',
  'rawSha256': '7fccf6e71230c9a22d19587a8464d39e6977f20e3baf43fd0f958494a11ea790',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T201152014776Z-903582a09512436dad7ad36b655a5dd8/receipt.json',
  'receiptSha256': '4b5abf2dfe7bd116c0f84995f5db5dd2bc04f7a15372d0e129c1f2603ab023f6'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201152722687Z-df9bdcdc1ec242f69b020f421b1301ad.jsonl',
  'rawSha256': '1aa97aada7d2086b1d2ad64a72017c2438477fbd90a889c033c99a16e0d4042b',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T201152722687Z-df9bdcdc1ec242f69b020f421b1301ad/receipt.json',
  'receiptSha256': 'cb9e016a5f504375775e2a4cd7a07359310f4e3fb531fca0b43362a87fb50472'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201522632827Z-05973ccb14384544a84df16ed5220e32.jsonl',
  'rawSha256': '4a1e61b86f25520e96d01c8be11a531dad3924cbf43931e829d6c9b25dc0eef5',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201522632827Z-05973ccb14384544a84df16ed5220e32/receipt.json',
  'receiptSha256': 'aeef08980b8484930a46c3666cd09b761882ed810221e2035bd0a24cb7adead1'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201523382452Z-a042a03b039b4caa8568a11ed22b8c70.jsonl',
  'rawSha256': 'd3763c77ad01043b33c3d15fed62033277209f467e5c36550aeab0abfef22a41',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201523382452Z-a042a03b039b4caa8568a11ed22b8c70/receipt.json',
  'receiptSha256': '9d8d823f0496a51c356c4f36595259dd945e0ee0063d463c8679b88f9490c845'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201524114563Z-0fa5618a3c0f4ac0b2cc45696f3b2d97.jsonl',
  'rawSha256': '0a8dc43c9a78924a988c8c1b8fd4f4db97144e734f26eb785fc35bfe01cd7e7a',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201524114563Z-0fa5618a3c0f4ac0b2cc45696f3b2d97/receipt.json',
  'receiptSha256': 'd9652bf0bee6149773ffecdd4bc83fcda9a382721b3795892aa23238d4433453'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201524872512Z-5165406069b34e858bf41c46d5c1cc4e.jsonl',
  'rawSha256': 'ac7c2a09a9e50c4576c95f01b7823d901aebf58e43eaef832a1c64f3b98cefb8',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201524872512Z-5165406069b34e858bf41c46d5c1cc4e/receipt.json',
  'receiptSha256': '240daae2efce602528f2636486250d763799179336d0aab21c9024d03bbde558'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201525621159Z-da62754f7a7d4658bc24ae56e6a26e2d.jsonl',
  'rawSha256': '9bbb47b6e824e1810696a43fbeed3ecf68855ac7a3fcf54235b25c427393c913',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201525621159Z-da62754f7a7d4658bc24ae56e6a26e2d/receipt.json',
  'receiptSha256': 'e91c359d7b3c9e24415c9a3df94c0bc7070f7b725593c1de05acc3f404b72305'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201526361785Z-71aa26636e9349fe80632c9400fd8660.jsonl',
  'rawSha256': 'dbcc38aa6458f6f942a27c8a53656b47d58fdbf63d6dc63fa8cc1b192bb7e486',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201526361785Z-71aa26636e9349fe80632c9400fd8660/receipt.json',
  'receiptSha256': 'e7ba26536584ad4c1ee4ad16e5dcc29914c1ca8938a8e4864c6c49b404e99778'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201527103444Z-8d4160f66e9f43ae8b2180095227af95.jsonl',
  'rawSha256': '8ccfc4822b51ee904486127993521895e123fee7f2696850e910137a91c547b8',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201527103444Z-8d4160f66e9f43ae8b2180095227af95/receipt.json',
  'receiptSha256': 'e7bb66d7736faeec499fe834eacb831806a15e3b1fb9bceefb4722c462382ef0'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201527843069Z-fd7b51edb05349de9b0ebd591c872347.jsonl',
  'rawSha256': '2848ec708fe2877854c6065322e4ef8bf40a42f2a4feff7a1c742d71a7b2e212',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T201527843069Z-fd7b51edb05349de9b0ebd591c872347/receipt.json',
  'receiptSha256': '133ef67f2f44336ddd77b28245852e53bf90dcff01c1ab74660f7f46d6ad84cc'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201528560700Z-7238259d1f914ff9a700a2c28a505160.jsonl',
  'rawSha256': 'e5f6866971ff98d26a37b3f4b5764fc7e7dd5617a3182c0e0dde0275b630dfb1',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T201528560700Z-7238259d1f914ff9a700a2c28a505160/receipt.json',
  'receiptSha256': '11b9c970e3608cdfccc4c4eacfe2e4980218116bfb256a3291e84d12ec90e8b6'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201529307841Z-c8ca0152eca24f3383e2ea43cf1c9286.jsonl',
  'rawSha256': 'f1e12a93fa7fb301e7918ed8e80b0071a56504eec61a9c5c93d54726023f3784',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T201529307841Z-c8ca0152eca24f3383e2ea43cf1c9286/receipt.json',
  'receiptSha256': '9fd1c91cfce9c360f2b393931d54a5cb3830c2b75ff91a08aeb1d912e7ef9b68'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201530003973Z-2356503485d34a92b30bb99dd076a700.jsonl',
  'rawSha256': '7a7b871205e2a24293c5d04ece3ae9cd6b8914a004ebda74d9ea927fa2da111d',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T201530003973Z-2356503485d34a92b30bb99dd076a700/receipt.json',
  'receiptSha256': '2f1f6f3948fa4a0ebb8a83e2774af437bb8f1f689454cf9b6be87f1e6511a631'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201530699587Z-4c55c68315cc42beb097ef021e111c1b.jsonl',
  'rawSha256': '55a19e90f3ea21da0871e33a695bd3b1914aad76db9e78415b04bb5d1329a0d0',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T201530699587Z-4c55c68315cc42beb097ef021e111c1b/receipt.json',
  'receiptSha256': 'cef4f7335d70b03c29a924f0118dee7ba7e28694550eed2773f1c266072ea0ed'},
 {'raw': 'firmware/trust-policy/20261105T123607943247Z-b7f460a700da40b1b931695958e9994f.jsonl',
  'rawSha256': 'cdae3faaad5054ff987855da71ded84a3027385d3fadd6bc3cf2a56a09cf090c',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T123607943247Z-b7f460a700da40b1b931695958e9994f/receipt.json',
  'receiptSha256': '9f0ff24b66036b7caac159dbaae431a0f4e3c596ec1b11c299b2645061f7d3e2',
  'select': ['authenticate(Landroid/os/IBinder;JILandroid/hardware/biometrics/IBiometricServiceReceiver;Ljava/lang/String;Landroid/hardware/biometrics/PromptInfo;)J']},
 {'raw': 'firmware/prompt-wire-contract/20261105T201649172472Z-476ed5161f354dfa986cdb58b7b4f440.jsonl',
  'rawSha256': 'e858f2fec53f2a0384c8b14b56e3b468e14dc002cec6285fc88d017563deae91',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T201649172472Z-476ed5161f354dfa986cdb58b7b4f440/receipt.json',
  'receiptSha256': 'e3db19e5dd17c8eb50f9bae9dc7b99316ec73495f1c756037e83b1114f7bd5f9'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201649739074Z-39689d2e43874dafb15c6326d5b21a9e.jsonl',
  'rawSha256': '4674c358dacda9f4d3d4e2fb0ad35c1187692e1f7dfa1d21d437ba4766ae0ecd',
  'archive': 'firmware/donor/extracted/system/framework/services.jar',
  'archiveSha256': '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3',
  'receipt': 'out/tooling/20261105T201649739074Z-39689d2e43874dafb15c6326d5b21a9e/receipt.json',
  'receiptSha256': 'de978cc120a2106f452a8a7bdb88f40b1d7c6c9ed2c18ea5d9d2a4646723af98'},
 {'raw': 'firmware/prompt-wire-contract/20261105T201847393997Z-eacf33b20db74b76a3751e8ec32a71e3.jsonl',
  'rawSha256': 'f6323d6ef1012269e3b45db9ae83cd5733223cd8ae8b6ce8502a26e080d8c1af',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T201847393997Z-eacf33b20db74b76a3751e8ec32a71e3/receipt.json',
  'receiptSha256': 'ed1da5c1542be271f500c693fe1144dbb4504871327128bea420622cc01d43b6'},
 {'raw': 'firmware/prompt-wire-contract/20261105T202641737128Z-6852fdfd55514305b638dc61684aa8d7.jsonl',
  'rawSha256': '8484ecee2fe990ae534afd811e8b21be88cef941044166be55e5e415c2b043aa',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T202641737128Z-6852fdfd55514305b638dc61684aa8d7/receipt.json',
  'receiptSha256': '00a19b5461d325784b302165e1e15926c8dc9f2ce6daedcf201bfc1d4bbe55f7'},
 {'raw': 'firmware/prompt-wire-contract/20261105T202642550263Z-d686a150619e46e0a1d854a1cd40c223.jsonl',
  'rawSha256': 'b2746a41913604f1925dcc1d180001b6fa6f024f92848ae32be2d6845dce4a59',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T202642550263Z-d686a150619e46e0a1d854a1cd40c223/receipt.json',
  'receiptSha256': '06ab3a25345d437ba2a48ff957b4216c79bd356c1bfb6233d1c83bb0fa9a5357'},
 {'raw': 'firmware/prompt-wire-contract/20261105T202752164467Z-9e31ac969b66451db58e8733a4403436.jsonl',
  'rawSha256': 'a9fe1d93035d90aced6d327e9ebe141ff66346d014911b97f8484440dbf21372',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T202752164467Z-9e31ac969b66451db58e8733a4403436/receipt.json',
  'receiptSha256': 'ff52b7ddce7e2fa1b60a50ae97512e9fb9db8b88b930c4955b607aba7fbe4f50'},
 {'raw': 'firmware/prompt-wire-contract/20261105T202752926102Z-c540f925bed8450c8f9ddbd813ca560e.jsonl',
  'rawSha256': '8e025892422b12b7211504a4ee78c092a880e5595c8e7e55a88c2f6ef471fcb3',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T202752926102Z-c540f925bed8450c8f9ddbd813ca560e/receipt.json',
  'receiptSha256': '171148de8f1cf5f77991d1dcdae3c5dfed411b98a2cbb37e6cca5ba13f47d0fc'}]

SF='8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
CF='d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'
SS='def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'
CS='66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'
PI='Landroid/hardware/biometrics/PromptInfo;'
BP='Landroid/hardware/biometrics/BiometricPrompt;'
BU='Landroid/hardware/biometrics/BiometricPrompt$Builder;'
AUTH='Landroid/hardware/biometrics/IAuthService'
RECV='Landroid/hardware/biometrics/IBiometricSysuiReceiver'
AS='Lcom/android/server/biometrics/AuthService$AuthServiceImpl;'
AUTH_SIG='authenticate(Landroid/os/IBinder;JILandroid/hardware/biometrics/IBiometricServiceReceiver;Ljava/lang/String;Landroid/hardware/biometrics/PromptInfo;)J'
CANCEL_SIG='cancelAuthentication(Landroid/os/IBinder;Ljava/lang/String;J)V'
INTERNAL='authenticateInternal(JLandroid/os/CancellationSignal;Ljava/util/concurrent/Executor;Landroid/hardware/biometrics/BiometricPrompt$AuthenticationCallback;I)J'


def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def report():
    methods={};declarations={};archives={}
    for src in SOURCES:
        if src['archive'] not in archives:
            assert digest(PARENT/src['archive'])==src['archiveSha256'],src['archive']
            archives[src['archive']]=src['archiveSha256']
        assert digest(PROJECT/src['raw'])==src['rawSha256'],src['raw']
        assert digest(PROJECT/src['receipt'])==src['receiptSha256']
        rec=json.loads((PROJECT/src['receipt']).read_text())
        assert rec['readerExitCode']==0 and rec['archiveAndToolPinsVerifiedBeforeAndAfter'] and not rec['oemCodeExecuted']
        for line in (PROJECT/src['raw']).open(encoding='utf-8'):
            row=json.loads(line)
            if row['record']=='class':declarations[(src['archiveSha256'],row['descriptor'])]=row
            elif row['record']=='method':
                b=row['body']
                if src.get('select') is not None and b['signature'] not in src['select']:continue
                key=(src['archiveSha256'],b['owner'],b['signature'])
                if key in methods:assert row['normalizedBodySha256']==methods[key]['normalizedBodySha256']
                methods[key]={**row,'raw':src['raw']}
    def row(side,owner,sig):return methods[(side,owner,sig)]
    def body(side,owner,sig):return row(side,owner,sig)['body']
    def at(side,owner,sig,pc):return next(i for i in body(side,owner,sig)['instructions'] if i['pc']==pc)
    def anchor(side,owner,sig,*checks):
        r=row(side,owner,sig);out=[]
        for pc,kind,wanted in checks:
            i=at(side,owner,sig,pc);value=i.get(kind)
            assert (wanted in value if isinstance(wanted,str) else value==wanted),(owner,sig,pc,value,wanted)
            out.append({'pc':pc,kind:value})
        return {'archiveSha256':side,'owner':owner,'signature':sig,'bodySha256':r['normalizedBodySha256'],'raw':r['raw'],'checks':out}
    def a(side,owner,sig,*checks):return anchor(side,owner,sig,*[(pc,'reference',ref) for pc,ref in checks])
    def fields(side,owner):return [x for x in declarations[(side,owner)]['fields'] if not x['accessFlags']&8]
    def schema(side,owner,limit=None):
        w=body(side,owner,'writeToParcel(Landroid/os/Parcel;I)V')['instructions'];r=body(side,owner,'<init>(Landroid/os/Parcel;)V')['instructions']
        reads=[];pending=None
        for i in r:
            ref=i.get('reference','')
            if ref.startswith('Landroid/os/Parcel;->read'):pending={'readPc':i['pc'],'parcelRead':ref.split('->')[1]}
            elif i['opcode'].startswith('IPUT') and ref.startswith(owner+'->') and pending:
                reads.append({'field':ref.split('->')[1],**pending,'fieldWritePc':i['pc']});pending=None
                if limit and len(reads)==limit:break
        writes=[];pending=None
        for i in w:
            ref=i.get('reference','')
            if i['opcode'].startswith('IGET') and ref.startswith(owner+'->'):pending={'field':ref.split('->')[1],'fieldReadPc':i['pc']}
            elif ref.startswith('Landroid/os/Parcel;->write') and pending:
                writes.append({**pending,'writePc':i['pc'],'parcelWrite':ref.split('->')[1]});pending=None
                if limit and len(writes)==limit:break
        assert len(reads)==len(writes),(side,owner,len(reads),len(writes))
        assert [x['field'] for x in reads]==[x['field'] for x in writes],owner
        return [{**w,**{k:v for k,v in r.items() if k!='field'}} for w,r in zip(writes,reads)]
    common_s=schema(SF,PI,31);common_c=schema(CF,PI,31)
    def semantic(s):return [{k:x[k] for k in ['field','parcelWrite','parcelRead']} for x in s]
    assert semantic(common_s)==semantic(common_c)
    f_s=fields(SF,PI);f_c=fields(CF,PI)
    assert len(f_s)==36 and len(f_c)==31
    extra=[x for x in f_s if x['name'] not in {y['name'] for y in f_c}]
    assert {x['name'] for x in extra}=={'mSemDisplayId','mSemTaskId','mSemBiometricType','mSemPrivilegedFlag','mSemChallengeData'}
    nested=[]
    for owner in ['Landroid/hardware/biometrics/IdentityCheckInfo;','Landroid/hardware/biometrics/FallbackOption;','Landroid/hardware/biometrics/PromptContentViewWithMoreOptionsButton;','Landroid/hardware/biometrics/PromptVerticalListContentView;']:
        s=schema(SF,owner);c=schema(CF,owner);assert semantic(s)==semantic(c)
        hashes={sig:row(SF,owner,sig)['normalizedBodySha256']==row(CF,owner,sig)['normalizedBodySha256'] for sig in ['<init>(Landroid/os/Parcel;)V','writeToParcel(Landroid/os/Parcel;I)V']}
        nested.append({'owner':owner,'instanceFieldsSamsung':fields(SF,owner),'instanceFieldsColoros':fields(CF,owner),'samsung':s,'coloros':c,'sameSelectedReadWriteSchema':True,'identicalNormalizedBodies':hashes})
    # Source-linear field lists above do not imply unconditional nested byte layouts.
    identity_owner='Landroid/hardware/biometrics/IdentityCheckInfo;'
    flag_owner='Lcom/android/internal/hidden_from_bootclasspath/android/hardware/biometrics/Flags;'
    def validate_guard(ins,call_pc,branch_pc,target_pc,flag):
        call=next(i for i in ins if i['pc']==call_pc)
        result=next(i for i in ins if i['pc']==call_pc+3)
        branch=next(i for i in ins if i['pc']==branch_pc)
        assert call['opcode']=='INVOKE_STATIC' and call['reference']==flag_owner+'->'+flag+'()Z'
        assert result['opcode']=='MOVE_RESULT'
        assert branch['opcode']=='IF_EQZ' and branch['targetPc']==target_pc
        assert branch['registers']==result['registers']
    identity_guards=[]
    for field,flag,wcall,wbranch,wskip,wvalue,rcall,rbranch,rskip,rvalue in [
       ('mClearIdentityCheckFallbackOption','clearFallbackOption',10,14,21,18,24,28,36,30),
       ('mDeviceCredentialAndIdentityCheck','doubleAuth',21,25,32,29,36,40,48,42)]:
        sides=[]
        for side in (SF,CF):
            writer=body(side,identity_owner,'writeToParcel(Landroid/os/Parcel;I)V')['instructions']
            reader=body(side,identity_owner,'<init>(Landroid/os/Parcel;)V')['instructions']
            validate_guard(writer,wcall,wbranch,wskip,flag);validate_guard(reader,rcall,rbranch,rskip,flag)
            assert '->writeBoolean(Z)V' in next(i for i in writer if i['pc']==wvalue)['reference']
            assert '->readBoolean()Z' in next(i for i in reader if i['pc']==rvalue)['reference']
            sides.append({'archiveSha256':side,'writer':{'flagCallPc':wcall,'branchPc':wbranch,'skipTargetPc':wskip,'writeBooleanPc':wvalue},'reader':{'flagCallPc':rcall,'branchPc':rbranch,'skipTargetPc':rskip,'readBooleanPc':rvalue}})
        identity_guards.append({'field':field,'flagMethod':flag_owner+'->'+flag+'()Z','presence':'Read and write only when the respective runtime flag call returns true','sides':sides})
    for item in nested:
        item.pop('sameSelectedReadWriteSchema')
        item['sameSelectedSourceReadWriteShape']=True
        item['effectiveCrossRuntimeLayoutAdmitted']=False
        item['conditionalFields']=identity_guards if item['owner']==identity_owner else []
        item['effectiveFlagProfileKnown']=False if item['owner']==identity_owner else None
        for side_name in ('samsung','coloros'):
            for field_entry in item[side_name]:
                condition=next((g['flagMethod'] for g in item['conditionalFields'] if field_entry['field'].startswith(g['field']+':')),None)
                field_entry['presenceCondition']=condition or 'unconditional in selected method'
    sensitivity=[]
    original=body(SF,identity_owner,'writeToParcel(Landroid/os/Parcel;I)V')['instructions']
    for label,pc,patch in [('missing_clear_fallback_flag_call',10,{'reference':flag_owner+'->doubleAuth()Z'}),('clear_fallback_branch_does_not_skip_value',14,{'targetPc':18})]:
        mutant=[{**i,**patch} if i['pc']==pc else i for i in original]
        try:validate_guard(mutant,10,14,21,'clearFallbackOption')
        except AssertionError:sensitivity.append({'case':label,'rejected':True,'scope':'in-memory source-check sensitivity; no OEM execution'})
        else:raise AssertionError('Conditional source guard mutant accepted: '+label)
    wire=[]
    request_specs=[(AUTH,AUTH_SIG),(AUTH,CANCEL_SIG)]+[(RECV,sig) for sig in ['onDialogDismissed(I[B)V','onTryAgainPressed()V','onDeviceCredentialPressed()V','onSystemEvent(I)V','onDialogAnimatedIn(Z)V','onStartFingerprintNow()V','onPauseAuthentication()V','onResumeAuthentication()V']]
    for owner,sig in request_specs:
        pair=[]
        for side in (SF,CF):
            proxy=owner+'$Stub$Proxy;';stub=owner+'$Stub;';ins=body(side,proxy,sig)['instructions']
            n,call=next((n,i) for n,i in enumerate(ins) if '->transact(' in i.get('reference',''))
            def constant(reg):
                return next(i['literal'] for i in reversed(ins[:n]) if i.get('registers',[None])[0]==reg and i['opcode'].startswith('CONST') and 'literal' in i)
            code,flags=constant(call['registers'][1]),constant(call['registers'][-1])
            writes=[{'pc':i['pc'],'method':i['reference'].split('->')[1]} for i in ins if i.get('reference','').startswith('Landroid/os/Parcel;->write')]
            replies=[{'pc':i['pc'],'method':i['reference'].split('->')[1]} for i in ins if i.get('reference','').startswith('Landroid/os/Parcel;->read')]
            sb=body(side,stub,'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z')['instructions']
            target=next(i for i in sb if i.get('reference','').endswith('->'+sig))
            entries=[]
            for sw in sb:
                if sw['opcode'] not in ('PACKED_SWITCH','SPARSE_SWITCH'):continue
                payload=next(i for i in sb if i['pc']==sw['targetPc'])
                for x in payload['switchElements']:entries.append((x['key'],sw['pc']+x['offsetFromReferringSwitchPc']))
            entry=next(pc for key,pc in entries if key==code and pc<=target['pc'] and not any(pc<other<=target['pc'] for _,other in entries))
            block=[i for i in sb if entry<=i['pc']<=target['pc']]
            assert any('->enforceNoDataAvail()V' in i.get('reference','') for i in block) or not any('->read' in i.get('reference','') for i in block)
            pair.append({'archiveSha256':side,'transaction':code,'flags':flags,'transactPc':call['pc'],'dataWrites':writes,'replyReads':replies,'stubCasePc':entry,'stubInvokePc':target['pc'],'stubReads':[{'pc':i['pc'],'method':i['reference'].split('->')[1]} for i in block if i.get('reference','').startswith('Landroid/os/Parcel;->read')],'enforcesNoDataAvailInCase':any('->enforceNoDataAvail()V' in i.get('reference','') for i in block),'proxyBodySha256':row(side,proxy,sig)['normalizedBodySha256'],'stubBodySha256':row(side,stub,'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z')['normalizedBodySha256']})
        def wire_sem(x):return (x['transaction'],x['flags'],[i['method'] for i in x['dataWrites']],[i['method'] for i in x['replyReads']],[i['method'] for i in x['stubReads']])
        assert wire_sem(pair[0])==wire_sem(pair[1]),sig
        wire.append({'interface':owner+';','signature':sig,'samsung':pair[0],'coloros':pair[1],'sameSelectedOuterWire':True,'provesNestedPayloadOrActionSemantics':False})
    assert [x['samsung']['transaction'] for x in wire]==[5,6,1,2,3,4,5,6,7,8]
    assert [x['samsung']['flags'] for x in wire]==[0,0,1,1,1,1,1,1,1,1]
    for side in (SF,CF):
        actual={x['signature'] for x in declarations[(side,RECV+'$Stub$Proxy;')]['methods'] if x['signature'].startswith('on')}
        selected={sig for owner,sig in request_specs if owner==RECV}
        assert actual==selected,(actual,selected)
    facts=[]
    def f(identity,claim,*evidence):facts.append({'id':identity,'classification':'observed-source','claim':claim,'evidence':list(evidence)})
    f('W01','Selected IAuth outer authenticate/cancel requests and all eight SysuiReceiver action wires match, but PromptInfo nested layout differs.',a(SF,PI,'writeToParcel(Landroid/os/Parcel;I)V',(158,'writeInt'),(163,'writeInt'),(168,'writeInt'),(173,'writeInt'),(189,'writeByteArray')))
    f('W02','Samsung challenge tail emits only a zero marker for null/empty; positive data uses length plus original byte-array write.',
      anchor(SF,PI,'writeToParcel(Landroid/os/Parcel;I)V',(178,'opcode','IF_EQZ'),(181,'opcode','IF_LEZ'),(184,'reference','writeInt'),(189,'reference','writeByteArray'),(193,'reference','writeInt')),
      a(SF,PI,'<init>(Landroid/os/Parcel;)V',(303,'readInt'),(313,'readByteArray')))
    ctor=body(SF,PI,'<init>()V')
    assert not any('->mSem' in i.get('reference','') for i in ctor['instructions'])
    f('W03','A genuinely fresh ordinary Samsung Builder allocates PromptInfo through its actual constructor; absent Sem mutations have VM-initialized primitive/reference defaults, not fabricated privileges.',
      a(SF,BU,'<init>(Landroid/content/Context;)V',(13,'PromptInfo;-><init>()V'),(16,'mPromptInfo'),(20,'Context;->getDisplayId'),(24,'setDisplayId')),
      a(SF,PI,'<init>()V'),a(SF,BU,'build()Landroid/hardware/biometrics/BiometricPrompt;',(34,'ServiceManager;->getService'),(59,'BiometricPrompt;-><init>')))
    f('W04','The exact outgoing Samsung prompt receives genuine Context display and Activity task metadata; the source has its own display exception fallback.',
      a(SF,BP,'semSetExtraInfo(Landroid/hardware/biometrics/PromptInfo;)V',(6,'Context;->getDisplayId'),(32,'semSetDisplayId'),(37,'Activity;'),(43,'Activity;->getTaskId'),(47,'semSetTaskId')),
      a(SF,BP,INTERNAL,(89,'PromptInfo;-><init>'),(107,'semSetExtraInfo'),(125,'IAuthService;->authenticate')))
    f('W05','Samsung privilege/type setters require the actual Samsung privileged permission; ordinary guest Builder has no matching Sem API.',
      a(SF,BU,'semSetBiometricType(I)Landroid/hardware/biometrics/BiometricPrompt$Builder;',(2,'BIOMETRICS_PRIVILEGED'),(4,'checkSelfPermission'),(13,'semSetBiometricType')),
      a(SF,BU,'semSetPrivilegedFlag(I)Landroid/hardware/biometrics/BiometricPrompt$Builder;',(2,'BIOMETRICS_PRIVILEGED'),(4,'checkSelfPermission'),(13,'semSetPrivilegedFlag')))
    assert not any(x['signature'].startswith('sem') for x in declarations[(CF,BU)]['methods'])
    f('W06','BiometricPrompt preserves real operation ID, caller package, token/receiver/user and returned request ID; cancellation retains token/package/request identity.',
      a(SF,BP,INTERNAL,(8,'CryptoObject;->getOpId'),(118,'Context;->getPackageName'),(125,'IAuthService;->authenticate'),(131,'OnAuthenticationCancelListener;-><init>')),
      a(CF,BP,INTERNAL,(12,'CryptoObject;->getOpId'),(121,'Context;->getPackageName'),(129,'IAuthService;->authenticate')),
      a(SF,BP,'cancelAuthentication(J)V',(12,'IAuthService;->cancelAuthentication')),
      a(CF,BP,'cancelAuthentication(J)V',(14,'IAuthService;->cancelAuthentication')))
    f('W07','Actual Samsung ingress evaluates Binder caller/user, AppOps and feature/privilege permissions before clearing identity and entering BiometricService.',
      a(SS,AS,AUTH_SIG,(62,'getCallingUserId'),(66,'getCallingUid'),(70,'getCallingPid'),(113,'AppOpsManager;->noteOp'),(151,'requiresTestOrInternalPermission'),(177,'requiresInternalPermission'),(188,'requiresAdvancedPermission'),(209,'semGetPrivilegedFlag'),(215,'semGetBiometricType'),(236,'clearCallingIdentity'),(259,'IBiometricService;->authenticate')))
    f('W08','Actual guest ingress also checks Binder identity/AppOps/permissions; a transport hop must not replace those checks with fields supplied by a client.',
      a(CS,AS,AUTH_SIG,(8,'getCallingUserId'),(12,'getCallingUid'),(16,'getCallingPid'),(71,'checkAppOps'),(194,'clearCallingIdentity'),(231,'IBiometricService;->authenticate')))
    f('W09','Selected cancellation is permission checked and forwarded through the actual BiometricService; Binder return is not operation/callback drain.',
      a(SS,AS,CANCEL_SIG,(37,'checkPermission'),(45,'clearCallingIdentity')),
      a(CS,AS,CANCEL_SIG,(2,'checkPermission'),(10,'clearCallingIdentity')))
    f('W10','More-options parcel carries its description only, leaving original client button/listener owners outside this payload; vertical list keeps typed item frontier explicit.',
      a(SF,'Landroid/hardware/biometrics/PromptContentViewWithMoreOptionsButton;','writeToParcel(Landroid/os/Parcel;I)V',(0,'mDescription'),(2,'writeString')),
      a(SF,'Landroid/hardware/biometrics/PromptVerticalListContentView;','<init>(Landroid/os/Parcel;)V',(3,'PromptContentItemParcelable;'),(11,'readArrayList')))
    f('W11','IdentityCheckInfo has two unconditional fields followed by two separately flag-conditional fields in both runtimes; equal source shape does not establish effective flag-profile/layout equivalence.',
      anchor(SF,identity_owner,'writeToParcel(Landroid/os/Parcel;I)V',(10,'reference','Flags;->clearFallbackOption()Z'),(14,'targetPc',21),(21,'reference','Flags;->doubleAuth()Z'),(25,'targetPc',32)),
      anchor(SF,identity_owner,'<init>(Landroid/os/Parcel;)V',(24,'reference','Flags;->clearFallbackOption()Z'),(28,'targetPc',36),(36,'reference','Flags;->doubleAuth()Z'),(40,'targetPc',48)),
      anchor(CF,identity_owner,'writeToParcel(Landroid/os/Parcel;I)V',(10,'reference','Flags;->clearFallbackOption()Z'),(14,'targetPc',21),(21,'reference','Flags;->doubleAuth()Z'),(25,'targetPc',32)),
      anchor(CF,identity_owner,'<init>(Landroid/os/Parcel;)V',(24,'reference','Flags;->clearFallbackOption()Z'),(28,'targetPc',36),(36,'reference','Flags;->doubleAuth()Z'),(40,'targetPc',48)))
    proof=[{'archiveSha256':side,'owner':owner,'signature':sig,'bodySha256':r['normalizedBodySha256'],'hasCode':r['body']['hasCode'],'physicalDex':r['physicalDex'],'logicalHeaderOffset':r['logicalHeaderOffset'],'instructionCount':len(r['body']['instructions']),'tryHandlerCount':len(r['body']['catches']),'raw':r['raw']} for (side,owner,sig),r in sorted(methods.items())]
    result={'schema':'prompt-wire-contract/v1','status':'finite-source-contract-no-runtime-converter','selected':False,'runtimeConverterImplemented':False,'oemExecuted':False,'phoneActions':False,'sources':SOURCES,'archivePins':archives,'selectedMethodProofs':proof,'selectedMethodCount':len(proof),'sourceAssertions':facts,'promptInfo':{'samsungInstanceFields':f_s,'colorosInstanceFields':f_c,'sharedOrderedFieldCount':31,'samsungOrderedCommonPrefix':common_s,'colorosOrderedCommonPrefix':common_c,'samsungOnlyFields':extra,'wholeParcelableInterchangeable':False,'samsungChallengeWire':'null or empty -> zero marker; positive length -> length marker then writeByteArray; original reader owns matching allocation/read semantics'},'nestedSchemas':nested,'conditionalSchemaGuardSensitivity':sensitivity,'historicalCorrection':{'initialFreezeSha256':'cbe2a34178d02e3defea35267adae6f2c0480a408c3840dd8be63790f9366ff0','preservedSnapshot':'out/prompt-wire-contract/history/initial-freeze-cbe2a341','reason':'Initial nested IdentityCheckInfo summary omitted source flag guards; replaced fixed-layout implication with matching conditional source shape and unknown effective flag profile','rawSourcesChanged':False},'requestActionWires':wire,'freshOrdinarySamsungSourceProfile':{'preconditions':['Genuine fresh original Builder and PromptInfo','No Sem mutator, semAuthenticate or previous reused state','Real caller Context and actual original permission/AppOps/user checks'],'constructorAbsenceDefaults':{'mSemBiometricType':0,'mSemPrivilegedFlag':0,'mSemChallengeData':None},'defaultBasis':'Actual constructor has no Sem-field writes; genuine fresh instance primitive/reference initialization. This is not permission to overwrite fields on an existing Sem request.','displayTaskProducer':'Outgoing prompt uses original semSetExtraInfo; actual Context display, source exception handling and Activity task branch. Server Context is not a replacement for app Context.','blanketRejectOrdinaryGenericRequest':False},'typedConverterReviewObligations':['Construct a real target-side PromptInfo with all31 actual common values and target-owned nested payloads; never pass the foreign object or raw whole parcel','For an admitted ordinary non-Sem guest request, use genuine source-supported absent Sem type/privilege/challenge semantics, while supplying authenticated caller display/task metadata under original producer rules','Do not expose or synthesize Samsung privileged type/flag/challenge behavior through the guest ordinary API; retain genuine explicit Sem requests and required policy at their actual owner','Preserve operation/challenge/token/request/receiver identity, caller UID/PID/package/user/profile, authenticators and confirmation/device-credential/identity-check policy','Retain original client button/fallback callback ownership and exact ordered fallback semantics','Bind each canonical receiver Binder carrier to the issued real session/request and original source action target; oneway return is not application completion or drain'],'unclosedNestedSchemas':['IdentityCheckInfo clearFallbackOption/doubleAuth producer and effective flag-profile admission','Bitmap/native graphics parcel and CharSequence span contents','ComponentName resource/package/identity semantics across runtimes','Concrete PromptContentItemParcelable subtypes and arbitrary/custom content subclasses','App IBiometricServiceReceiver full callback wire and client executor/button action lifecycle','Samsung Sem wrapper Bundle construction/contents beyond PromptInfo source fields'],'separateFrontiers':['IStatusBarService/IStatusBar/CommandQueue request wire belongs to UI followup','No keyguard/enrollment route audited or accepted','No effective AuthSession B1 boolean policy derived from raw deviceCredentialAllowed alone','Real receiver publication/admission/queue/factor/auth-token/cancellation/drain semantics remain unimplemented'],'limits':['Exact pinned source request pairs only, not universal Binder/Parcelable compatibility','No schemas or defaults inferred from method names, declaration counts or a callback returning normally','No OEM execution, actual parcel roundtrip, Android Binder test, crypto acceptance or device candidate']}
    out=PROJECT/'inventory/prompt-wire-contract.json';out.write_text(json.dumps(result,indent=2)+'\n')
    work=PROJECT/'out/prompt-wire-contract';(work/'verification.json').write_text(json.dumps({'inventorySha256':digest(out),'toolSha256':digest(Path(__file__)),'assertionGroups':len(facts),'wirePairs':len(wire),'commonFields':31,'nestedPairs':len(nested),'conditionalGuardSensitivityCases':len(sensitivity),'effectiveIdentityFlagProfileAdmitted':False,'methods':len(proof),'rawPins':len(SOURCES),'oemExecuted':False},indent=2)+'\n')
    print(json.dumps({'inventorySha256':digest(out),'assertions':len(facts),'wirePairs':len(wire),'commonFields':31,'nestedPairs':len(nested),'methods':len(proof)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',required=True,action='store_true');parser.parse_args();report()
