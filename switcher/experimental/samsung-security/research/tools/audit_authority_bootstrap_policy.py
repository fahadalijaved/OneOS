"""Verify bounded original policy/bootstrap evidence; never executes OEM code.

--report verifies pinned input/raw/reader receipts and writes derived metadata.
No service adaptation or runtime policy object is implemented by this tool.
"""
import argparse, hashlib, json
from pathlib import Path
PROJECT=Path(__file__).resolve().parent.parent
PARENT=PROJECT.parent
SOURCES = [{'raw': 'firmware/authority-bootstrap-policy/20261105T184719803405Z-f85abd4459814000a27ff7c04e84fd8e.jsonl',
  'rawSha256': '1ccb3efb1d060539961706e9be0112a68e2e6437cc5b027aa6783e873f6ac726',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T184719803405Z-f85abd4459814000a27ff7c04e84fd8e/receipt.json',
  'receiptSha256': '40ebf65366f6712a6c83f0cc2a6b6ac1ffce92c63f282f8a4e878b583303c04a'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184720581016Z-8456a07eeb35436c937d1bfc54e0bcd7.jsonl',
  'rawSha256': 'aa7f0ca10db1409d22ce1f9b2f52466b19f0430daeb038b70f5077c5f7ddf685',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T184720581016Z-8456a07eeb35436c937d1bfc54e0bcd7/receipt.json',
  'receiptSha256': '5f1f9905b61e53fe381bbb1b09938b3cb1e0ed2ad952f64fb9fc186dcae5e89f'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184721338118Z-badeccd8f3524d218ce8c81c9ac4967e.jsonl',
  'rawSha256': '2c4f6b688ac1a946d9ffb28a7b7985ecba4884ffad6f3dbbd5f1072eac63259a',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184721338118Z-badeccd8f3524d218ce8c81c9ac4967e/receipt.json',
  'receiptSha256': 'af16ebb187aa6c83dd79370fe49e1f81275512f91dda7d9ebe3b435fa46a577b'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184721915719Z-33ed76cd4a3745e3bc3eb3e24d8baa0e.jsonl',
  'rawSha256': '612b5e86939b5f9b7dba489783b3fccb26f0ee1bcb30589ea70dfe2293e03403',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184721915719Z-33ed76cd4a3745e3bc3eb3e24d8baa0e/receipt.json',
  'receiptSha256': 'e77d0c248d102fb6914ddb01d1571d37e7075317a86290ea6910fead77db94f7'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184722486822Z-0459f7d18f5344f393b75bb96cfb35d2.jsonl',
  'rawSha256': '09a9165b221c771eb8b1c9b0455e7383488aa7bce487c9e68af00227e50ab193',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184722486822Z-0459f7d18f5344f393b75bb96cfb35d2/receipt.json',
  'receiptSha256': 'cff84fbbca4f835a8849b02acc212b3efadf5dc644aaf4ad5d7d50f2f7e92c67'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184723069167Z-ae77a6ab676941c08c03e54f0bdad5b4.jsonl',
  'rawSha256': '0a1f5cd9b4a2801c4f0fff1d2c0d19e1c09cb4786319763426ff4088f73d7bc6',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184723069167Z-ae77a6ab676941c08c03e54f0bdad5b4/receipt.json',
  'receiptSha256': 'fece3f944428f2227f57cec0cd287d37f025b8ac2dce0ba4b4c39d528269ddd0'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184723642251Z-a2f4d2df3f9345aba0144cc22c51913d.jsonl',
  'rawSha256': '6243b143a3f67027b806b48bcecf4d93a7e33861d7cb548bfc304d9686841d54',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184723642251Z-a2f4d2df3f9345aba0144cc22c51913d/receipt.json',
  'receiptSha256': '7649f64ce8cda3cde3d9d04e1d080b65caed9667ffa9560a0fbf80f2d29f8b31'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184724229345Z-dabe1d48fd5c4068ab1d6ad4819cdae9.jsonl',
  'rawSha256': '4b574efb29752692401450fa13858c0b2152e8aa339cdba85ed5d8bc3abaa3c2',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184724229345Z-dabe1d48fd5c4068ab1d6ad4819cdae9/receipt.json',
  'receiptSha256': '11126f628682db6808475d2fe343718cee3393ae5decbfe20f3d1f280e14b410'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184752833278Z-640a9efae3f543798d2bc36326fd65a1.jsonl',
  'rawSha256': 'b516203cf74f1bbfa2faa8a9a331b0f5f6d19b6ba659a748f1b5be6372de00c8',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184752833278Z-640a9efae3f543798d2bc36326fd65a1/receipt.json',
  'receiptSha256': '562c7f8d9cd8d0f5f4624782f726da9b27fa326ca1d7fa1ba6ff0c00599e1f7e'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184754304025Z-be11a0ebe3504e7c958804465d9aa3bc.jsonl',
  'rawSha256': '56a74f2378ee0f667258222d7d615114fa904ec88be4cfe5d9e269d40cad8e78',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184754304025Z-be11a0ebe3504e7c958804465d9aa3bc/receipt.json',
  'receiptSha256': 'a80dfcb45402df80324135c7f0e822c208f9d0fda608389d2214162bb1a22486'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184754901224Z-2eca8327f2984eebb6c5ea878a4e6ead.jsonl',
  'rawSha256': '56df17a84a9441a2c6ff1e33e04b1e854f183aa73b68fdb016ede2bc69ef8d8c',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184754901224Z-2eca8327f2984eebb6c5ea878a4e6ead/receipt.json',
  'receiptSha256': '7adea5185c50002051bbe80ee1d45514ffea16a961194336aeac929c65e49c50'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184827591979Z-01b873138a6e4b4f8a2d2096e13ec839.jsonl',
  'rawSha256': '16da8e748fb8dd2f9616e8ac475af0f147805df1477a6bd0157fc31eb0e314b7',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184827591979Z-01b873138a6e4b4f8a2d2096e13ec839/receipt.json',
  'receiptSha256': 'f073a504a43765e5e2b4e5e30cbef351020275c9a4a7fc40367ce4763acceecf'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184828161578Z-b0db4455583247c7bff69702482223f4.jsonl',
  'rawSha256': '20d10f9ff95cd8e37e12a61b09c58250b4ddcfdcdc92e49d8abe2a9453e0514d',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184828161578Z-b0db4455583247c7bff69702482223f4/receipt.json',
  'receiptSha256': 'b25bfa9b31916a196ef112cc71cea6df1f34b7db631fecd3a9f2611d3189242c'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184828756174Z-93bddc0d62044b4298a9695a7fe2622d.jsonl',
  'rawSha256': 'a50cb6537e3b7eed6f97450eee6c61a61daa0bd27744b55230cb920fd5e07bf2',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184828756174Z-93bddc0d62044b4298a9695a7fe2622d/receipt.json',
  'receiptSha256': '2e032b92d85890ac584f0001a0e4dd6f9ac5172b999c070704e812089b0a2186'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184829335776Z-8588e362b9a4424da3b3b373785474cb.jsonl',
  'rawSha256': '573fa8c923fc8522f44f1b309b860ee8e7c575c9845bfa7d1cb94c2e7588602d',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184829335776Z-8588e362b9a4424da3b3b373785474cb/receipt.json',
  'receiptSha256': 'fa3a2385dc558e73f613c87bcbc8e5c0a3dc8562d34c48188128042bee8c7e4c'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184829991419Z-9b8ed81b870445b3b4c9046e0a11a0b2.jsonl',
  'rawSha256': '00ee952c465d2fe2d3f45d859504d40b019254d1095b6c6c9b4de71e9c234b94',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184829991419Z-9b8ed81b870445b3b4c9046e0a11a0b2/receipt.json',
  'receiptSha256': '651d275fead8381a0662e233f5f041b68419bcfea996357d5a7180a14192eee6'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184830511998Z-5fbd16fc180348b5915bdb60a9dc37a2.jsonl',
  'rawSha256': 'a0c7956f73129823c8dc88c0557c87d4c1b2a9167d4960da247ba25bf1a8d5c7',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184830511998Z-5fbd16fc180348b5915bdb60a9dc37a2/receipt.json',
  'receiptSha256': 'a0b86f8835ab0208c6bf1937e6e3f3eaf098babb1795009ef47f34d208fbc25c'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184928517714Z-b28de24571e947478139bfabc399bd13.jsonl',
  'rawSha256': 'a21979d03a4586d4160466a438d4eebcb69d42757d62678361cba73451a50357',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184928517714Z-b28de24571e947478139bfabc399bd13/receipt.json',
  'receiptSha256': 'cd6f45a220c43b1f4bcc82eb5928edba7e04bb5903b4adf0fb01b09bfcfe3ebd'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184929076801Z-728968ca115240449e0b615d277c08ad.jsonl',
  'rawSha256': '2a9fb4ee0745c874fdb06b7db1119a573fffd2bc392f1209adab3fbffff85c8b',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184929076801Z-728968ca115240449e0b615d277c08ad/receipt.json',
  'receiptSha256': 'cbccccea68ff4f5581f1b1e13289b3a486bfb653433ea6fab2755f267840f7a3'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184929646552Z-83ff1bda87b3428da16bdcfca7ad222b.jsonl',
  'rawSha256': 'f2104775106d3584dce67185e4b7e5d0fcce7a805013080c248352dee97ac5b1',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184929646552Z-83ff1bda87b3428da16bdcfca7ad222b/receipt.json',
  'receiptSha256': 'c004c8f387a606e55f151583310eedd114f702d16b3d587764314f89ad14b6a6'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184930236725Z-ca4fd38975fb436da71d2825f1544fd4.jsonl',
  'rawSha256': 'b5f8e0c81046b6dec62aef34aa7ef5bf91006790ec04704c1721b3139a1b737c',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T184930236725Z-ca4fd38975fb436da71d2825f1544fd4/receipt.json',
  'receiptSha256': 'e071e6fc7ced8c944c755ab6025680c66deaf83357eb54c244e1e9e6c53c8223'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184930985373Z-e67e3b9fbe40484895eb76334dbf4f35.jsonl',
  'rawSha256': '31607f6f5f533309e9d83261dac020fd2f483fb99c399bf9d0dbec0ff0e74495',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T184930985373Z-e67e3b9fbe40484895eb76334dbf4f35/receipt.json',
  'receiptSha256': 'eb81e98f72bd649fbb825b5e61d3399f85ed813ff6b14fe7fedf7dbe986ba4be'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184931758134Z-f750399f7dd04a80bd3059713f0cc14f.jsonl',
  'rawSha256': 'd916970be6b194d5fa28113efa041ba53216d468c13f3a8534d3d17ef3caed18',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T184931758134Z-f750399f7dd04a80bd3059713f0cc14f/receipt.json',
  'receiptSha256': '7819d0e3110ef51eb384921a7ed7f655977fe5b0ab4e1986cd01b7774a15a81e'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184932496282Z-d3b1c310af5e4defb7667e2a81450e7f.jsonl',
  'rawSha256': 'b3f15f72ff66599b9d37dd7406c224f294d8f9e2d64a86f34cc16d995aeeec23',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T184932496282Z-d3b1c310af5e4defb7667e2a81450e7f/receipt.json',
  'receiptSha256': 'b8603fbb3a061d45675b91532268085f0d8d46775324ae5361fee1b3bbba35b6'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184933264521Z-0fab21db1556462c9984262b900287d9.jsonl',
  'rawSha256': '9ffa03cf438beac94c92703054aa0ae9617553ccb5e44634982870409c132598',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T184933264521Z-0fab21db1556462c9984262b900287d9/receipt.json',
  'receiptSha256': '1fb5ac8b45abb9131b35a9f11737dfad6aff4e801a5c62c54d05e4452dfb8cf3'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184934000149Z-dc43c4ad86dd415c9231474a55cd1782.jsonl',
  'rawSha256': '58765a8dfa058c2c26500bfad5c3aa08b3a5e64e93c54de64f5073ab5e276801',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T184934000149Z-dc43c4ad86dd415c9231474a55cd1782/receipt.json',
  'receiptSha256': '474f470e6a551bb24b6e5d431d6be1edf1c45c148dbbcc096fe056b58e2d9b17'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184934761265Z-a3f46e1027cf40c6b11f5da6dbd5d8d3.jsonl',
  'rawSha256': '326d91c384c867fe0be2d7856ab123a7fbe97649c344ff9cbb9e5e78a12e9739',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T184934761265Z-a3f46e1027cf40c6b11f5da6dbd5d8d3/receipt.json',
  'receiptSha256': '15a61134bed03634089ca592350172e8f250f0859579367d8ed4f93cd182ab2a'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185118045330Z-f43dcca68391492883bde5684ce0b110.jsonl',
  'rawSha256': '280435ea0ebc81fa601a41e7b695ee6865e6fc25dfafa783c3f437feb75059ff',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185118045330Z-f43dcca68391492883bde5684ce0b110/receipt.json',
  'receiptSha256': '5b072c3f3e12af279876b0c624c81162007e555b4689cc502f7abbeaea5353ab'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185118613930Z-daed22273d834781a50d8d89bbce3ade.jsonl',
  'rawSha256': '65e92fac9958b193e9582a04827293cd05467358bf1fe42d773150df7276975a',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185118613930Z-daed22273d834781a50d8d89bbce3ade/receipt.json',
  'receiptSha256': '286e5426e4e9aed9dab2a5ed11fa4ebe95ac0abc0c5a670617d3ced2e6f3c83c'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185119185046Z-07cf88a771fe4cedb164f946c6d0c7cc.jsonl',
  'rawSha256': '7817f9ad07b4fd7d7ee1d4cbaf1324accee3b863ffb7ce6083039f22424452bd',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185119185046Z-07cf88a771fe4cedb164f946c6d0c7cc/receipt.json',
  'receiptSha256': 'd69cea865d8da1b1f9c7a73af56aae0b01f1e729c04d1f0fa2c774d5fd068f17'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185119758156Z-4c30b40178c54c609909901ac3384cf5.jsonl',
  'rawSha256': '62113933462b1a25cf291c12e95f3155be6cbdd053065557966bd0321c9e7356',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185119758156Z-4c30b40178c54c609909901ac3384cf5/receipt.json',
  'receiptSha256': 'd86115265a6cae3855d4215030ea90f3e67adccb8cfd42ce54c0ba0bda3487ed'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185120351259Z-b8bbda1faf0e4ce99f7c8e617be97ca2.jsonl',
  'rawSha256': '4bb91f7f71e79c9b64a05a5dcfd915b3be8fbbd92aecfe1a5f9a08edcc916769',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T185120351259Z-b8bbda1faf0e4ce99f7c8e617be97ca2/receipt.json',
  'receiptSha256': '1315ef16121537c74b58b4ef8495972c876e28956a44957eb8b4b36c58086c3d'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185121109894Z-383afde7d91e4c829552807373b2fb92.jsonl',
  'rawSha256': '437f0c540ecd8dbfd1f9b8c5899dbdf1d85b7bb5afc439dfdc0f0bb56a226465',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T185121109894Z-383afde7d91e4c829552807373b2fb92/receipt.json',
  'receiptSha256': '6645947bc877521922496af8278680f01a06eb85bb50a99d0eef3e7b7a6fb2ce'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185121882023Z-f7810185aa8d430cbedf4c20aca2e4dd.jsonl',
  'rawSha256': '519b0789c0817ae8dd1eba91a0b0a7c0798f564a303c0ebc656e0c895a040ffc',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T185121882023Z-f7810185aa8d430cbedf4c20aca2e4dd/receipt.json',
  'receiptSha256': '0e064f151fa9ad690702c2837899a2e0b9b7eeba1de2d604f110c6da5fade56c'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185217152452Z-75da4a1d061e4ceab3f29f3239d95d3d.jsonl',
  'rawSha256': '241eaccb58469eb1089b1657ba1f049de9ba5b83a6ac12431640ec22397639aa',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T185217152452Z-75da4a1d061e4ceab3f29f3239d95d3d/receipt.json',
  'receiptSha256': '22ab071f4831031ba601abf77d08e5895a27a06a262f4f2536f1ba818ee32bdf'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185218874723Z-2b7a8181ad18465fa9a759544f7b4d00.jsonl',
  'rawSha256': 'e716a70fbac541eee13aeea4ebab61a7103e35efba634e8032618ad60405a360',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185218874723Z-2b7a8181ad18465fa9a759544f7b4d00/receipt.json',
  'receiptSha256': '32086eef76017b42ab132e7fe330cdb2fd50f217ebbaa43eba7fcc293258a658'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185247032859Z-3bb1ca012ad547e28660b9990befca19.jsonl',
  'rawSha256': 'a831de077c2746e08ec9154dd0c3e93e8d410a17f27ec3fc48d5b99a6455cfaa',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T185247032859Z-3bb1ca012ad547e28660b9990befca19/receipt.json',
  'receiptSha256': 'fe23b9e09132a12613808d8b6b45c986b67d5588822461062a97b48eef14130e'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185247797994Z-b731dd7f03e04466a57de3d385750c3e.jsonl',
  'rawSha256': '1922a74e6cf07bb8df0fa44e78c5041dde03ac17cbd29e637ab0d1e8fb401f15',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T185247797994Z-b731dd7f03e04466a57de3d385750c3e/receipt.json',
  'receiptSha256': '8cc5fdb935d500f5bb27658ac6e247978feafab8a2e4bc2357b79fb60a40bab8'},
 {'raw': 'firmware/tooling/20261105T123602189303Z-13cb9b7c9f294be296de6da0d63a43c0.jsonl',
  'rawSha256': 'cc88a0875c9f5ae89d16021e8de86748067b6f9b72391c70f35aed484144d5b5',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T123602189303Z-13cb9b7c9f294be296de6da0d63a43c0/receipt.json',
  'receiptSha256': '0a30bd1f6ea91dc3b0ee62fe4942cc5acfe8f42ec45194f6f6cc75d795cdedbc',
  'select': ['<init>(Lcom/android/server/locksettings/LockSettingsService$Injector;)V',
             'systemReady()V',
             'disableEscrowTokenOnNonManagedDevicesIfNeeded(I)V',
             'onCredentialVerified(Lcom/android/server/locksettings/SyntheticPasswordManager$SyntheticPassword;Landroid/app/admin/PasswordMetrics;I)V',
             'unlockUser(I)V',
             'onPostLockCredentialChanged(Lcom/android/internal/widget/LockscreenCredential;I)V',
             'maybeShowEncryptionNotificationForUser(ILjava/lang/String;)V']},
 {'raw': 'firmware/credentials/20261105T123452923820Z-aac9ea4ce220401eac1f56291b0de70b.jsonl',
  'rawSha256': '1cc9cc837fe39ea8a24616c622eaf638222fb58fd6a4f74b969ddd0ed26a9d79',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T123452923820Z-aac9ea4ce220401eac1f56291b0de70b/receipt.json',
  'receiptSha256': 'ea4226fef602e87818346742d4feac9667f252f2a2a3d82b0151dc444d14bb2a',
  'select': ['getDevicePolicyManager()Landroid/app/admin/DevicePolicyManager;']},
 {'raw': 'firmware/authority-bootstrap-users/20261105T185029827311Z-55fd8bbc34b842faa4b6735d135105fc.jsonl',
  'rawSha256': 'a79d0099f2e677bc0bf36149df9b19623104fe56d13f03ba641f24c8ca569425',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185029827311Z-55fd8bbc34b842faa4b6735d135105fc/receipt.json',
  'receiptSha256': '87685f9adc582daf439d58f3585050a8f3fef09fd2dc082b6d438f2721351d52'},
 {'raw': 'firmware/authority-bootstrap-users/20261105T185030942027Z-71a496d846b04f458dc628aaf2396d34.jsonl',
  'rawSha256': '203c860498e198ec0498aac333103be03aca6b5b70902101e5e3801060289637',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185030942027Z-71a496d846b04f458dc628aaf2396d34/receipt.json',
  'receiptSha256': '53d9e3e458c49544e207734915c1f6b025367241c9580e71527af68019e13419'},
 {'raw': 'firmware/authority-bootstrap-users/20261105T185311769971Z-1fb9159ebe3d45879468bc20292da59e.jsonl',
  'rawSha256': '8895f0a68b76aa9422c532c29f4e15ff07b0fd94f0a9e22ed370b5e4624840f0',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185311769971Z-1fb9159ebe3d45879468bc20292da59e/receipt.json',
  'receiptSha256': '8462bd111fe593f6c96429af98df0975e4dd0ea2c47d49e99f1308592a7bfeff'},
 {'raw': 'firmware/security-user-binding/20261105T153354981341Z-b23ec7648928490f934a1690c6f7129d.jsonl',
  'rawSha256': '1e015c602dd0a3a735203df413c78051dfa2e2e1e918b68dfabe64871b36bf56',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'},
 {'raw': 'firmware/security-user-binding/20261105T153509278546Z-1ab536a393f941e6a2a3c12b57b917a6.jsonl',
  'rawSha256': 'a3f354a23585f1f9ec98b975f4b58751f80ba78e5384569897fd1d642d93a47d',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185757378595Z-65c80551d00944ac8d03a6a87c608878.jsonl',
  'rawSha256': '8136f57cf83d8da985f5784a97cbe69a381cb88f9021fc22920238b165c43ddd',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185757378595Z-65c80551d00944ac8d03a6a87c608878/receipt.json',
  'receiptSha256': '2e13b01512d8b2cc165c4a6de005c8f4dee39ec79bb0357801e09bfd0ad18fd1'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185808503261Z-434c980ae4e347f79c1ab8c85fc3ae43.jsonl',
  'rawSha256': 'c6584cf3cb6c3fb4fcdd9a42ad80d6b5b2e16b74b23e9def80854bf696650f8d',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185808503261Z-434c980ae4e347f79c1ab8c85fc3ae43/receipt.json',
  'receiptSha256': 'dd6a3b47233864f8b65963017b0c9dd546187ffd42e56adffb8a1398a093abfc'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185827096696Z-3987887bd94f410cbacabe3c83ba92c6.jsonl',
  'rawSha256': '6c905010ed7e2f2473ce3915824ad31383670f709842144bc272e0b133240739',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185827096696Z-3987887bd94f410cbacabe3c83ba92c6/receipt.json',
  'receiptSha256': 'dfc51d09829354b8d0fa64fe3a87ff1de936ace986dd72f9d0e01868620b1ed3'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185900858830Z-8d401802ab784cbd86647fab52e126eb.jsonl',
  'rawSha256': 'e07e2e78af629d5b2cf3034db09bb130672cbaf70bbb23ddc1c31be1be846491',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185900858830Z-8d401802ab784cbd86647fab52e126eb/receipt.json',
  'receiptSha256': 'e81ee27cbfa68fa6aae0179c2372e92756202add5bbf85780f3ac5da95297c53'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T190312927722Z-85c4ac6620a24c328c0f8a46f44bb3f9.jsonl',
  'rawSha256': '35aac6849ce4cfdeaac2c7cd21e4e46d9db4c845b4dc0a8d7ff2a6299d0116ea',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T190312927722Z-85c4ac6620a24c328c0f8a46f44bb3f9/receipt.json',
  'receiptSha256': 'd10831e8e8254fdc5eb0b8f0c125f533516d80413c5c75de4decbd56ca5681b1'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T190313515810Z-ba88f2d92d754398bbf850f5495dd43c.jsonl',
  'rawSha256': 'bf97cd1352fd9d23c718dd2c70529e2c793c6031cfcbabb2d6494b8ab8d8dcb1',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T190313515810Z-ba88f2d92d754398bbf850f5495dd43c/receipt.json',
  'receiptSha256': '2bfa106438a1f30695e82b4354b023d53e9cc5e9d2a22bb477e267f2b8cc66fa'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T190314075399Z-2d371803509f458c80a9995df7c26ab4.jsonl',
  'rawSha256': '1710b9400f98dde83d570ecae045be3080f87f4a149ee227752f30c9af64dc01',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T190314075399Z-2d371803509f458c80a9995df7c26ab4/receipt.json',
  'receiptSha256': '1cb3bc09b099c00211488b68184508ccbe69e88fc788bff939028d359ffce212'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T190430240122Z-c4d0b7a7afd046728b5afe3372f9fe8d.jsonl',
  'rawSha256': 'e6d10c698c00bdb81bcfe0cf9c5b6c05001fb9ed9d761d70a52ddd489c1243d6',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T190430240122Z-c4d0b7a7afd046728b5afe3372f9fe8d/receipt.json',
  'receiptSha256': '96977190bab1935eecb882c0cee8d1d799c0679251512ba0c75177b6346823e2'}]

SS='def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'
SF='8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
CF='d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'
LSS='Lcom/android/server/locksettings/LockSettingsService;'
DPMS='Lcom/android/server/devicepolicy/DevicePolicyManagerService;'
DPM='Landroid/app/admin/DevicePolicyManager;'
DS='Landroid/app/admin/DeviceStateCache;'
DSI='Lcom/android/server/devicepolicy/DeviceStateCacheImpl;'
SLD='Lcom/android/server/security/authenticationpolicy/SecureLockDeviceService;'
LC='Lcom/android/server/security/authenticationpolicy/SecureLockDeviceService$Lifecycle;'
FS='Lcom/android/server/security/authenticationpolicy/settings/SecureLockDeviceSettingsFileStore;'
PM='Landroid/app/ApplicationPackageManager;'

def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def report():
    methods={}; refs=[]; rawpins=[]; archives={}; lss_frontier=[]; lss_method_count=0
    for source in SOURCES:
        archive=PARENT/source['archive']
        if source['archive'] not in archives:
            assert digest(archive)==source['archiveSha256'], 'Archive pin drift: '+str(archive)
            archives[source['archive']]=source['archiveSha256']
        raw=PROJECT/source['raw']
        assert digest(raw)==source['rawSha256'], 'Raw pin drift: '+str(raw)
        if source.get('receipt'):
            assert digest(PROJECT/source['receipt'])==source['receiptSha256'], 'Receipt pin drift'
            receipt=json.loads((PROJECT/source['receipt']).read_text())
            assert receipt['readerExitCode']==0 and receipt['archiveAndToolPinsVerifiedBeforeAndAfter']
            assert not receipt['oemCodeExecuted'] and not receipt['androidExecuted']
            assert receipt['rawSha256']==source['rawSha256']
        rawpins.append(source)
        for line in raw.open(encoding='utf-8'):
            row=json.loads(line)
            if row['record']=='method':
                b=row['body']
                if b['owner']==LSS and source['archiveSha256']==SS:
                    lss_method_count+=1
                    for i in b['instructions']:
                        ref=i.get('reference','')
                        if any(ref.startswith(prefix) for prefix in ['Landroid/app/IActivityManager;->','Landroid/app/admin/DevicePolicyManager;->','Landroid/app/admin/DeviceStateCache;->','Landroid/app/supervision/SupervisionManagerInternal;->','Lcom/android/server/security/authenticationpolicy/SecureLockDeviceService;->','Landroid/content/pm/PackageManager;->hasSystemFeature']):
                            lss_frontier.append({'owner':b['owner'],'signature':b['signature'],'pc':i['pc'],'reference':ref,'bodySha256':row['normalizedBodySha256'],'raw':source['raw']})
                if source.get('select') is not None and b['signature'] not in source['select']: continue
                key=(source['archiveSha256'],b['owner'],b['signature'])
                value={**row,'raw':source['raw'],'rawSha256':source['rawSha256']}
                if key in methods: assert methods[key]['normalizedBodySha256']==row['normalizedBodySha256']
                methods[key]=value
            elif row['record']=='reference': refs.append({**row,'archiveSha256':source['archiveSha256'],'raw':source['raw']})
    assert lss_method_count==199,lss_method_count
    assert sum(x['reference'].startswith('Landroid/app/IActivityManager;->') for x in lss_frontier)==1
    def method(side,owner,sig): return methods[(side,owner,sig)]
    def anchor(side,owner,sig,*checks):
        row=method(side,owner,sig); b=row['body']; evidence=[]
        for pc,kind,wanted in checks:
            hits=[i for i in b['instructions'] if i['pc']==pc]
            assert len(hits)==1, (owner,sig,pc)
            value=hits[0].get(kind)
            assert (wanted in value if isinstance(wanted,str) else wanted==value), (owner,sig,pc,kind,value,wanted)
            evidence.append({'pc':pc,kind:value})
        return {'archiveSha256':side,'owner':owner,'signature':sig,'bodySha256':row['normalizedBodySha256'],'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],'raw':row['raw'],'checks':evidence}
    def a(side,owner,sig,*checks): return anchor(side,owner,sig,*[(pc,'reference',ref) for pc,ref in checks])
    facts=[]
    def fact(identity,claim,*anchors): facts.append({'id':identity,'classification':'observed-source','claim':claim,'anchors':list(anchors)})
    ctor='<init>(Lcom/android/server/locksettings/LockSettingsService$Injector;)V'
    fact('F01','LSS captures genuine AM/Notification/Supervision owners; DPM is obtained from Context.',
         a(SS,LSS,ctor,(440,'ActivityManager;->getService'),(610,'mNotificationManager'),(661,'mSupervisionManagerInternal')),
         a(SS,'Lcom/android/server/locksettings/LockSettingsService$Injector;','getDevicePolicyManager()Landroid/app/admin/DevicePolicyManager;'))
    fact('F02','systemReady reads real failed-attempt state before active migration; post-change policy reads password history.',
         a(SS,LSS,'systemReady()V',(35,'getDevicePolicyManager'),(40,'getCurrentFailedPasswordAttempts'),(47,'migrateLockSettingsDB'),(522,'isSecureLockDeviceEnabled')),
         a(SF,DPM,'getCurrentFailedPasswordAttempts(I)I',(12,'IDevicePolicyManager;->getCurrentFailedPasswordAttempts')),
         a(SF,DPM,'getPasswordHistoryLength(Landroid/content/ComponentName;I)I',(6,'IDevicePolicyManager;->getPasswordHistoryLength')))
    fact('F03','The Samsung DPM failed-attempt request enforces caller/user authorization and returns loaded credential-owner policy data.',
         a(SS,DPMS,'getCurrentFailedPasswordAttempts(Ljava/lang/String;IZ)I',(16,'getCallerIdentity'),(20,'hasFullCrossUsersPermission'),(24,'checkCallAuthorization'),(64,'getCredentialOwner'),(68,'getUserDataUnchecked'),(72,'mFailedPasswordAttempts')))
    fact('F04','DeviceStateCache is provided by a process-local DevicePolicyManagerInternal, with an empty-cache fallback when absent.',
         a(SF,DS,'getInstance()Landroid/app/admin/DeviceStateCache;',(0,'DevicePolicyManagerInternal;'),(2,'LocalServices;->getService'),(10,'getDeviceStateCache'),(15,'EmptyDeviceStateCache;')),
         a(SS,'Lcom/android/server/devicepolicy/DevicePolicyManagerService$LocalService;','getDeviceStateCache()Landroid/app/admin/DeviceStateCache;'),
         anchor(SF,'Landroid/app/admin/DeviceStateCache$EmptyDeviceStateCache;','isDeviceProvisioned()Z',(0,'literal',0)),
         anchor(SF,'Landroid/app/admin/DeviceStateCache$EmptyDeviceStateCache;','isUserOrganizationManaged(I)Z',(0,'literal',0)))
    escrow='disableEscrowTokenOnNonManagedDevicesIfNeeded(I)V'
    fact('F05','Escrow retention reads organization/provisioning and supervision policy before conditional destruction of both SP escrow states.',
         a(SS,LSS,escrow,(47,'DeviceStateCache;->getInstance'),(51,'isUserOrganizationManaged'),(110,'isEscrowTokenRequired'),(151,'isDeviceProvisioned'),(173,'hasSystemFeature'),(238,'SyntheticPasswordManager;->destroyState'),(241,'SyntheticPasswordManager;->destroyState')),
         a(SS,DSI,'isUserOrganizationManaged(I)Z',(0,'mHasProfileOwner'),(22,'mDeviceOwnerType')),
         a(SS,DSI,'isDeviceProvisioned()Z',(0,'mIsDeviceProvisioned')))
    fact('F06','Owners.load populates the cache from original owner data and broadcasts ownership to existing local managers.',
         a(SS,'Lcom/android/server/devicepolicy/Owners;','load()V',(28,'OwnersData;->load'),(62,'mDeviceOwnerType'),(89,'setHasProfileOwner'),(119,'notifyChangeLocked'),(122,'pushDeviceOwnerUidToActivityTaskManagerLocked')),
         a(SS,'Lcom/android/server/devicepolicy/OwnersData;','load([I)V',(5,'readFromFileLocked'),(19,'readFromFileLocked')))
    fact('F07','Original owner filenames and XML parsing are selected; this tool does not read private policy files.',
         a(SS,'Lcom/android/server/devicepolicy/OwnersData;','getDeviceOwnerFile()Ljava/io/File;',(7,'getDataSystemDirectory'),(11,'device_owner_2.xml')),
         a(SS,'Lcom/android/server/devicepolicy/OwnersData;','getProfileOwnerFile(I)Ljava/io/File;',(7,'getUserSystemDirectory'),(11,'profile_owner.xml')),
         a(SS,'Lcom/android/server/devicepolicy/OwnersData$FileReadWriter;','readFromFileLocked()V',(65,'openRead'),(69,'resolvePullParser'),(135,'readInner')))
    parse='load(Lcom/android/server/devicepolicy/DevicePolicyData;Lcom/android/internal/util/JournaledFile;Ljava/util/function/Function;Landroid/content/ComponentName;)V'
    fact('F08','Per-user policy XML supplies setup-complete and failed-password-attempts; setup updates also come from real Settings.Secure.',
         a(SS,'Lcom/android/server/devicepolicy/DevicePolicyData;',parse,(63,'setup-complete'),(80,'mUserSetupComplete'),(385,'failed-password-attempts'),(401,'mFailedPasswordAttempts')),
         a(SS,DPMS,'initializePolicyDataFromXml(ILcom/android/server/devicepolicy/DevicePolicyData;)V',(33,'DevicePolicyData;->load'),(58,'mIsDeviceProvisioned')),
         a(SS,DPMS,'updateUserSetupCompleteAndPaired()V',(24,'user_setup_complete'),(33,'getIntForUser'),(59,'mIsDeviceProvisioned')))
    dc='<init>(Lcom/android/server/devicepolicy/Injector;Lcom/android/server/devicepolicy/PolicyPathProvider;)V'
    fact('F09','Constructing full original DPMS starts observers and conditionally upgrades policy files before publishing its full internal service.',
         a(SS,DPMS,dc,(2041,'registerReceiverAsUser'),(2304,'LocalServices;->addService'),(2979,'DevicePolicyData;->store'),(2994,'writeDeviceOwner'),(3075,'JournaledFile;->commit'),(3338,'Owners;->load'),(3550,'DevicePolicyManagerInternal;'),(3554,'LocalServices;->addService'),(3607,'DevicePolicyEngine;->load')))
    fact('F10','SecureLockDevice enabled state is a concrete private store/file-lock field read, not a Binder boolean.',
         a(SS,SLD,'isSecureLockDeviceEnabled()Z',(0,'mStore'),(2,'mFileStore'),(4,'mFileLock'),(7,'mIsEnabled')))
    sc='<init>(Landroid/content/Context;)V'
    fact('F11','SecureLockDevice lifecycle constructs the original private owner and synchronously loads enabled/client-id/original-settings from its authoritative file; source error paths reset defaults.',
         a(SS,LC,sc,(240,'SecureLockDeviceService;'),(376,'getDataSystemDirectory'),(382,'secure_lock_device_state.xml'),(469,'openRead'),(473,'resolvePullParser'),(582,'loadOriginalSettingsFromXml'),(598,'mClientUserId'),(609,'mIsEnabled'),(679,'mIsEnabled'),(692,'mIsEnabled')))
    fact('F12','SecureLockDevice original startup registers receiver/biometric/StrongAuth listeners and later applies actual restrictions; construction alone is not policy-ready.',
         a(SS,LC,sc,(717,'registerReceiver'),(727,'registerEnabledOnKeyguardCallback')),
         a(SS,LC,'onStart()V',(18,'LocalServices;->addService')),
         a(SS,SLD,'onLockSettingsReady()V',(27,'LocalServices;->getService'),(69,'registerStrongAuthTracker')),
         a(SS,SLD,'onBootCompleted()V',(26,'registerBiometricStateListener'),(45,'registerBiometricStateListener'),(164,'applySecureLockDeviceSettings'),(176,'storeSecureLockDeviceEnabled')))
    fact('F13','Supervision service source initializes loaded settings and owned callbacks; the exact user/local policy stream owns its full gate.',
         a(SS,'Lcom/android/server/supervision/SupervisionService;','<init>(Lcom/android/server/supervision/SupervisionService$Injector;)V',(81,'ServiceThread;->start'),(113,'addUserLifecycleListener'),(153,'addOnRoleHoldersChangedListenerAsUser')),
         a(SS,'Lcom/android/server/supervision/SupervisionService$Lifecycle;','onStart()V',(6,'publishLocalService'),(12,'publishBinderService'),(15,'registerProfileOwnerListener')))
    fact('F14','A genuine system ActivityThread with no global feature cache has a source-supported PM fallback; cache absence is not by itself an impossible bootstrap.',
         a(SF,PM,'<init>(Landroid/app/ContextImpl;Landroid/content/pm/IPackageManager;)V',(51,'isSystemFeaturesCacheAvailable'),(55,'mUseSystemFeaturesCache')),
         a(SF,PM,'isSystemFeaturesCacheAvailable()Z',(0,'ActivityThread;->isSystem'),(6,'SystemFeaturesCache;->hasInstance')),
         a(SF,PM,'hasSystemFeature(Ljava/lang/String;I)Z',(11,'RoSystemFeatures;->maybeHasFeature'),(22,'mUseSystemFeaturesCache'),(26,'SystemFeaturesCache;->getInstance'),(41,'mHasSystemFeatureCache'),(49,'PropertyInvalidatedCache;->query')))
    fact('F15','The original package service answers non-maintenance features from its actual feature map; guest map equivalence is not established.',
         a(SS,'Lcom/android/server/pm/PackageManagerService;','hasSystemFeature(Ljava/lang/String;I)Z',(61,'mAvailableFeatures')))
    fact('F16','LSS requests real user unlock using an IProgressListener; Samsung and guest transport codes differ.',
         a(SS,LSS,'unlockUser(I)V',(42,'IActivityManager;->unlockUser2')))
    fact('F17','Encrypted-user notifications are real package/user resource operations; the Samsung wrapper includes extra edge/overflow and delayed-work paths before enqueue.',
         a(SS,LSS,'maybeShowEncryptionNotificationForUser(ILjava/lang/String;)V',(252,'DevicePolicyResourcesManager;->getString'),(655,'NotificationManager;->notifyAsUser'),(733,'NotificationManager;->notifyAsUser')),
         a(SF,'Landroid/app/NotificationManager;','notifyAsUser(Ljava/lang/String;ILandroid/app/Notification;Landroid/os/UserHandle;)V',(42,'postEdgeNotification'),(143,'getBlockInfoOfNotificationsForOverflow'),(338,'Handler;->postDelayed'),(454,'enqueueNotificationWithTag')))
    fact('F18','DPM notification strings query genuine resource policy with an original fallback supplier; they are not authentication results.',
         a(SF,'Landroid/app/admin/DevicePolicyResourcesManager;','getString(Ljava/lang/String;Ljava/util/function/Supplier;)Ljava/lang/String;',(36,'IDevicePolicyManager;->getString'),(49,'ParcelableResource;->getString')))
    fact('F19','Profile-owner broadcast synchronization uses the sending user, real DPMInternal owner, original resources and persistent supervision state; it is not a presentation-only observer.',
         a(SS,'Lcom/android/server/supervision/SupervisionService$Lifecycle;','registerProfileOwnerListener()V',(5,'PROFILE_OWNER_CHANGED'),(26,'registerReceiverForAllUsers')),
         a(SS,'Lcom/android/server/supervision/SupervisionService$Lifecycle$ProfileOwnerBroadcastReceiver;','onReceive(Landroid/content/Context;Landroid/content/Intent;)V',(4,'getSendingUserId'),(8,'syncStateWithDevicePolicyManager')),
         a(SS,'Lcom/android/server/supervision/SupervisionService;','-$$Nest$msyncStateWithDevicePolicyManager(Lcom/android/server/supervision/SupervisionService;I)V',(2,'getDpmInternal'),(8,'getProfileOwnerAsUser'),(54,'setSupervisionEnabledForUserInternal'),(89,'setSupervisionEnabledForUserInternal')),
         a(SS,'Lcom/android/server/supervision/SupervisionService;','setSupervisionEnabledForUserInternal(ILjava/lang/String;Z)V',(5,'getUserData'),(19,'saveUserData'),(38,'withCleanCallingIdentity'),(55,'withCleanCallingIdentity')))
    fact('F20','Concrete original owner subparsers populate device-owner types and profile-owner records; supervision caches the genuine canonical DPMInternal lookup.',
         a(SS,'Lcom/android/server/devicepolicy/OwnersData$DeviceOwnerReadWriter;','readInner(ILcom/android/modules/utils/TypedXmlPullParser;Ljava/lang/String;)Z',(73,'device-owner-type'),(243,'mDeviceOwnerTypes'),(443,'OwnerInfo;->readFromXml'),(447,'mDeviceOwner')),
         a(SS,'Lcom/android/server/devicepolicy/OwnersData$ProfileOwnerReadWriter;','readInner(ILcom/android/modules/utils/TypedXmlPullParser;Ljava/lang/String;)Z',(8,'profile-owner'),(33,'mProfileOwners'),(41,'OwnerInfo;->readFromXml')),
         a(SS,'Lcom/android/server/supervision/SupervisionService$Injector;','getDpmInternal()Landroid/app/admin/DevicePolicyManagerInternal;',(4,'DevicePolicyManagerInternal;'),(6,'LocalServices;->getService'),(12,'mDpmInternal')))
    scan_counts={
        'DeviceStateCacheImpl':sum(x['instruction'].get('reference','').startswith(DSI) for x in refs),
        'SystemFeaturesCache':sum(x['instruction'].get('reference','').startswith('Landroid/content/pm/SystemFeaturesCache;') for x in refs),
        'IActivityManager.unlockUser2Services':sum(x['instruction'].get('reference','')=='Landroid/app/IActivityManager;->unlockUser2(ILandroid/os/IProgressListener;)Z' for x in refs),
        'IPackageManager.hasSystemFeatureFramework':sum(x['instruction'].get('reference','')=='Landroid/content/pm/IPackageManager;->hasSystemFeature(Ljava/lang/String;I)Z' for x in refs)}
    assert list(scan_counts.values())==[51,18,2,5],scan_counts
    reused_pins={'inventory/authority-bootstrap-users.json':'3be21cf44efd85ccd56ba75d4ec7cfe95070f34cdfba00dc5bc0efa8dd5f8b91','docs/authority-bootstrap-users.md':'9ffcda68bb306ecb199695059f91b7ae355b1da4ac4d35a006175b4284d9033d'}
    for rel,expected_pin in reused_pins.items():assert digest(PROJECT/rel)==expected_pin,rel
    wire=[]
    for owner,sig in [
        ('Landroid/app/admin/IDevicePolicyManager$Stub$Proxy;','getCurrentFailedPasswordAttempts(Ljava/lang/String;IZ)I'),
        ('Landroid/app/admin/IDevicePolicyManager$Stub$Proxy;','getPasswordHistoryLength(Landroid/content/ComponentName;IZ)I'),
        ('Landroid/app/IActivityManager$Stub$Proxy;','unlockUser2(ILandroid/os/IProgressListener;)Z'),
        ('Landroid/app/INotificationManager$Stub$Proxy;','enqueueNotificationWithTag(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;ILandroid/app/Notification;I)V')]:
        pair=[]
        for side in (SF,CF):
            row=method(side,owner,sig); ins=row['body']['instructions']
            calls=[(n,i) for n,i in enumerate(ins) if '->transact(' in i.get('reference','')];assert len(calls)==1
            n,call=calls[0];reg=call['registers'][1]
            assignment=next(i for i in reversed(ins[:n]) if i.get('registers',[None])[0]==reg and i['opcode'].startswith('CONST'))
            assert 'literal' in assignment
            writes=[i['reference'].split('->')[1] for i in ins if i.get('reference','').startswith('Landroid/os/Parcel;->write')]
            pair.append({'archiveSha256':side,'transaction':assignment['literal'],'transactionPc':assignment['pc'],'dataWrites':writes,'bodySha256':row['normalizedBodySha256'],'raw':row['raw']})
        wire.append({'owner':owner,'signature':sig,'samsung':pair[0],'coloros':pair[1],'sameTransactionAndWriteSignatures':pair[0]['transaction']==pair[1]['transaction'] and pair[0]['dataWrites']==pair[1]['dataWrites'],'provesParcelableLayoutOrAuthority':False})
    expected=[(31,31),(19,19),(208,205),(7,7)]
    assert [(w['samsung']['transaction'],w['coloros']['transaction']) for w in wire]==expected
    proof=[]
    for (side,owner,sig),row in sorted(methods.items()):
        b=row['body'];proof.append({'archiveSha256':side,'owner':owner,'signature':sig,'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],'bodySha256':row['normalizedBodySha256'],'hasCode':b['hasCode'],'instructionCount':len(b['instructions']),'tryHandlerCount':len(b['catches']),'raw':row['raw']})
    result={'schema':'authority-bootstrap-policy/v1','status':'finite-source-gate-open-no-runtime-binding','gate':'F','selected':False,'oemExecuted':False,'phoneActions':False,'privatePolicyFilesRead':False,'sourceAssertions':facts,'wireCases':wire,'lssAuxiliaryFrontier':lss_frontier,'reusedLssMethodsInspected':lss_method_count,'selectedMethods':proof,'selectedMethodCount':len(proof),'selectedCodeBodyCount':sum(x['hasCode'] for x in proof),'sources':rawpins,'archivePins':archives,'referenceScanCounts':scan_counts,'reusedGateCPins':reused_pins,'reusedReports':['construction-credentials','security-user-binding','strong-auth-gating','authority-bootstrap-users'],'requiredOwners':['Original initialized policy/user state before escrow reconciliation','Real DPM caller/user/credential-owner policy plus DeviceStateCache producer','Original Supervision settings/lifecycle/user-role update owner','SecureLockDevice file/settings/factor/StrongAuth/biometric producer and phase owners','Genuine feature/resource/package/caller ownership','Typed guest ActivityManager unlockUser2 and exact real progress callback','Owned notification publication/delayed-work/resource identity'],'unresolvedBindings':['No admitted live authoritative policy files or loaded owner objects','No selected replacement for global LocalServices policy reads','No complete DPMS constructor/upgrade/observer dependency assembly','No complete SecureLockDevice settings-controller/native/Binder assembly or shutdown protocol','No accepted PM feature-map/resource equivalence or cache invalidation transport','Matching DPM/notification wire codes do not prove complete Parcelable/server/caller semantics','No implemented guest AM typed adapter/progress-to-storage/lifecycle completion fence','No runtime handoff, uncertain-progress recovery or additional-factor readiness proof'],'candidateAdaptation':'Source proposal only: preserve genuine original local policy owners or explicitly retarget reached operations to the same admitted authoritative policy producer through reviewed typed APIs; use genuine guest AM/notification clients where proven, preserving subject/callback/resource semantics. Never substitute absent/empty caches, policy false, fake readiness or success.','wholeSystemServerConclusion':'No proof that the entire Samsung system_server is mandatory; full original DPMS construction is concretely broader and mutating. A smaller policy owner remains unimplemented and requires exact producer/state/update/caller closure.','limits':['Static pinned archives only; installed guest/runtime/native policy unknown','No OEM implementations or full method dumps emitted into normal files','Only selected requests compared; matching selected codes are not general Binder compatibility','Supervision closure is shared with gate C; UserManager and Context bootstrap remain separately owned','No optional OPPO removal or required policy suppression selected by this audit']}
    out=PROJECT/'inventory/authority-bootstrap-policy.json';out.write_text(json.dumps(result,indent=2)+'\n')
    generated=PROJECT/'out/authority-bootstrap-policy';generated.mkdir(exist_ok=True,parents=True)
    (generated/'verification.json').write_text(json.dumps({'inventorySha256':digest(out),'toolSha256':digest(Path(__file__)),'sourceAssertionsVerified':len(facts),'wireCasesVerified':len(wire),'selectedMethods':len(proof),'selectedCodeBodies':sum(x['hasCode'] for x in proof),'archivePinsVerified':len(archives),'rawPinsVerified':len(rawpins),'oemExecuted':False},indent=2)+'\n')
    print(json.dumps({'inventory':str(out),'sha256':digest(out),'assertions':len(facts),'wireCases':len(wire),'selectedMethods':len(proof)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',action='store_true',required=True);parser.parse_args();report()
