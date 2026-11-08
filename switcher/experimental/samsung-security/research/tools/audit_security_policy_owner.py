"""Verify exact original policy load/update/persistence frontiers.

Source/API research only. No provider, runtime wrapper or policy values are authored.
Run --report to check pinned archives/raw evidence and regenerate derived metadata.
"""
import argparse,hashlib,json
from pathlib import Path
PROJECT=Path(__file__).resolve().parent.parent
PARENT=PROJECT.parent
SOURCES = [{'raw': 'firmware/security-policy-owner/20261105T194910589452Z-25b359968399445f81de6db032d7fb5d.jsonl',
  'rawSha256': '86094232074da6b4b4af7d4fb29a67d42d1e28d562d473304b4f34ff6c9a725b',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T194910589452Z-25b359968399445f81de6db032d7fb5d/receipt.json',
  'receiptSha256': '00cb7ae77c56a4e52115269ad9472016f5dac5dfec13902c1c820f198df0dab6'},
 {'raw': 'firmware/security-policy-owner/20261105T194911183072Z-9e23f3bf95b24d2d9dd2467248f5bada.jsonl',
  'rawSha256': '6a7c7e3fbcbe63990b7a666761f0030dad43463c660c657c47c9f258f759cc36',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T194911183072Z-9e23f3bf95b24d2d9dd2467248f5bada/receipt.json',
  'receiptSha256': 'faf180a8cc7a25a17301a29ffd806aac69bfc242cfb1d8e4765d250ce4b47a2c'},
 {'raw': 'firmware/security-policy-owner/20261105T194911750649Z-e3268e9e3f42447c97359005b0785ccd.jsonl',
  'rawSha256': 'ae9435fba7538e12085b679b68780bd003ae4b03d94a492f0711d34fb6d46263',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T194911750649Z-e3268e9e3f42447c97359005b0785ccd/receipt.json',
  'receiptSha256': '7adeebb056aa069780da45e51858b5b0861ab736de0ef5e6c2da242c04291df8'},
 {'raw': 'firmware/security-policy-owner/20261105T194912343261Z-32d6841fd1d94ec48685564899ed571e.jsonl',
  'rawSha256': 'c95bc6bc54829eb51ca5315e31b5fffc089a4444699d1db119ce299345a17362',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T194912343261Z-32d6841fd1d94ec48685564899ed571e/receipt.json',
  'receiptSha256': '913576506e8d5bba0f43e0e974dfdc639266a69043d97581c6269730c533e3b8'},
 {'raw': 'firmware/security-policy-owner/20261105T194912955406Z-aa0e3c8a7fc7489abb31a47eeeef45de.jsonl',
  'rawSha256': '5040651a980daa2e0b42d5d7baa4f4c5541adbe5b25ccc8658f819f4239dd4f0',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T194912955406Z-aa0e3c8a7fc7489abb31a47eeeef45de/receipt.json',
  'receiptSha256': '4fc357b57c61636e18ff2b9a2e65c0a50d9c57503144c33c734a377759be3985'},
 {'raw': 'firmware/security-policy-owner/20261105T194913532021Z-8b20fe53eff24c9eaf6772b489997ffb.jsonl',
  'rawSha256': '522b3c07decb38add63e11ec7028444df1b05a0095135efc3e2bf5dfda7e886d',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T194913532021Z-8b20fe53eff24c9eaf6772b489997ffb/receipt.json',
  'receiptSha256': 'f2ceb3b9f6a26837059ebd627a88f05281fcc9858509a67c587852e4b1c5b117'},
 {'raw': 'firmware/security-policy-owner/20261105T195036693686Z-7074a217730c4094811aded85ce0f0ad.jsonl',
  'rawSha256': '0a66d640e81fc59cb4d57b587ed799b286a0d96727bc4e567e721c7b20fcfc31',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T195036693686Z-7074a217730c4094811aded85ce0f0ad/receipt.json',
  'receiptSha256': 'aeeb21c82304500555950343f675ddf88dba228ad798601b8362b0c19faf0c17'},
 {'raw': 'firmware/security-policy-owner/20261105T195037638853Z-d457fe20a2634e718e370078804595d2.jsonl',
  'rawSha256': '45697410de40eb66fdca9c7537b0ea64043f75c37f6335949a81d21de7af4ce3',
  'archive': 'firmware/donor/extracted/system/framework/framework.jar',
  'archiveSha256': 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
  'receipt': 'out/tooling/20261105T195037638853Z-d457fe20a2634e718e370078804595d2/receipt.json',
  'receiptSha256': '0169566ed6cc965421671291fe86ca5b803a159d91dcb35915f7ec785e12148b'},
 {'raw': 'firmware/security-policy-owner/20261105T195038677016Z-e912a17725564dfdb6253ef28683be6c.jsonl',
  'rawSha256': 'f43676b709251768fca8d38382e257b45149456b95c4d254a62916c9af420b09',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T195038677016Z-e912a17725564dfdb6253ef28683be6c/receipt.json',
  'receiptSha256': 'ab7370b407c6a529acf6b0aa6f2488726aacae9b4d183105c4b65f958a056102'},
 {'raw': 'firmware/security-policy-owner/20261105T195039444648Z-872cb51e7db942b59dfffb0e614ceacb.jsonl',
  'rawSha256': 'bb8feb9c626120524e2f0ac3cf98e0233fa4c2233b7b147a43ac801ee504c82c',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195039444648Z-872cb51e7db942b59dfffb0e614ceacb/receipt.json',
  'receiptSha256': 'e644d18c26b2e490bb9df670122114e742132988fa72e83a583752bc67fb0a5b'},
 {'raw': 'firmware/security-policy-owner/20261105T195040734346Z-459ce910b4f04a0bb5f2496c825a693e.jsonl',
  'rawSha256': '9df280dcfd7e56348429583adbfef3aa1d71290add24fe8c4118b16508b57855',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195040734346Z-459ce910b4f04a0bb5f2496c825a693e/receipt.json',
  'receiptSha256': '294f99b1d1942eedb3cf38c7581215ebcbe6650052f19364cf8ab77f3e0f071a'},
 {'raw': 'firmware/security-policy-owner/20261105T195042071058Z-e1a346f66cb64ae0a47902ab28be7058.jsonl',
  'rawSha256': 'ea7dea290e88d0e9de1afd4f33ee9526c788e58cc5f4971ca75a12ab911a0398',
  'archive': 'firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk',
  'archiveSha256': '0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77',
  'receipt': 'out/tooling/20261105T195042071058Z-e1a346f66cb64ae0a47902ab28be7058/receipt.json',
  'receiptSha256': '0dd015701a32915d900c0e89c7ebf7332e2bde9e436cb6caefad0953fac8df3a'},
 {'raw': 'firmware/security-policy-owner/20261105T195044319461Z-d24facbec29544218ab6bc27bb214d09.jsonl',
  'rawSha256': 'dd6bea107c7cbe1497774d50024d6e9653d117bbb6dca0ca93df2b8ae12cbfd9',
  'archive': 'firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk',
  'archiveSha256': '0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77',
  'receipt': 'out/tooling/20261105T195044319461Z-d24facbec29544218ab6bc27bb214d09/receipt.json',
  'receiptSha256': 'fe9f2cc036b12a25f0ef16a40c962510aae9a34a01349a34c962546b437ee114'},
 {'raw': 'firmware/security-policy-owner/20261105T195047106486Z-06953491fb8345b28bc7a4c6fcf1c458.jsonl',
  'rawSha256': '4a035d6e46d95a007931d4949f83e62cfada2be2998f4c56ef0119c3abb8d0b1',
  'archive': 'firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk',
  'archiveSha256': '33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b',
  'receipt': 'out/tooling/20261105T195047106486Z-06953491fb8345b28bc7a4c6fcf1c458/receipt.json',
  'receiptSha256': 'f8f9f597b8475c6767b57448193a1a9ac1017eb43569ac96e3a6723fc1aaaf2b'},
 {'raw': 'firmware/security-policy-owner/20261105T195049991503Z-7b58b8f6ad4645f08a27b1a3e8d3907b.jsonl',
  'rawSha256': '424be3c930d1095d8cc33285d6f3945c69fe0a20f099c1e7e0a77f8cf67135ae',
  'archive': 'firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk',
  'archiveSha256': '33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b',
  'receipt': 'out/tooling/20261105T195049991503Z-7b58b8f6ad4645f08a27b1a3e8d3907b/receipt.json',
  'receiptSha256': '27bbdef056484e7fb0226ed8afef9909647cab0521097966541af7f5984dc0cf'},
 {'raw': 'firmware/security-policy-owner/20261105T195247832940Z-083c58a104a24197bdfa0c95e2a2c832.jsonl',
  'rawSha256': '4f6f9cbfeb2fe7fc60513ef29ee3f3a0013b9db62e54a1e4db166005af3a3d09',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195247832940Z-083c58a104a24197bdfa0c95e2a2c832/receipt.json',
  'receiptSha256': '76f7f855684ab3449de6e673e9b6f3121a6655aac73504b8475ac685311b2a98'},
 {'raw': 'firmware/security-policy-owner/20261105T195248482541Z-959f79d45bad4b77a970ee052b025911.jsonl',
  'rawSha256': 'ee073a69755752adca22e1ee2f3e582dc1856b5c1358ba60013e5ad548bf566d',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195248482541Z-959f79d45bad4b77a970ee052b025911/receipt.json',
  'receiptSha256': '9ee19a826acbd87cc1c6f515fdfebadeab0dbc16e5c435d064656186d52241d9'},
 {'raw': 'firmware/security-policy-owner/20261105T195249206666Z-10825f6ed19d494bb2297e635ce18d6a.jsonl',
  'rawSha256': 'aa3e7f184e5c4c8954401df256f135d8beba70eb2865570101497f36b882484e',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195249206666Z-10825f6ed19d494bb2297e635ce18d6a/receipt.json',
  'receiptSha256': '0ae09a256c0c60d772b392ead2336b18ea54368ba4c136dadd0dda50ceb0123f'},
 {'raw': 'firmware/security-policy-owner/20261105T195249803276Z-67df37a32b2c498d991415ebb84bd02d.jsonl',
  'rawSha256': '80d4551ae15041d2be88c7b026c7aa097ae91da3c10628bf2541e64b31e2d116',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195249803276Z-67df37a32b2c498d991415ebb84bd02d/receipt.json',
  'receiptSha256': '42d275581f563b11382cf0e57d9c957a0fa8db2ee7fc057a16c85010ed7f1fe5'},
 {'raw': 'firmware/security-policy-owner/20261105T195250442388Z-c9c58cb8d46a4116991e614faaa25046.jsonl',
  'rawSha256': 'dcccee34cddb0d604e3e2cd09df1af229f5cb21fd35ef65862e5b27000bc9918',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195250442388Z-c9c58cb8d46a4116991e614faaa25046/receipt.json',
  'receiptSha256': 'f535e8d260f9764055502ae00487cc7a8c951a247fff06d5b9a302720acc212e'},
 {'raw': 'firmware/security-policy-owner/20261105T195252072660Z-19f53314e60f45dda1bd54fb5769f435.jsonl',
  'rawSha256': 'a5a148742f1301a8a9c229437440b551ac0410a0f70a21acedf8ceb21f6366d4',
  'archive': 'firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk',
  'archiveSha256': '0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77',
  'receipt': 'out/tooling/20261105T195252072660Z-19f53314e60f45dda1bd54fb5769f435/receipt.json',
  'receiptSha256': '47650f371c9ffe57e1f0d4e23cad6c64abc09299ad520280b99b7c258ef726dc'},
 {'raw': 'firmware/security-policy-owner/20261105T195253129371Z-36d5328685744ae5be5ccf92b5ddea52.jsonl',
  'rawSha256': '962d3efcdf8a49891176188970ce12de3521e58a106c6facc5d88158ac932b9a',
  'archive': 'firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk',
  'archiveSha256': '0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77',
  'receipt': 'out/tooling/20261105T195253129371Z-36d5328685744ae5be5ccf92b5ddea52/receipt.json',
  'receiptSha256': '4396450777cd23a548a4b116feaeaefdf4ed4f187adbddd814e5396637504e2e'},
 {'raw': 'firmware/security-policy-owner/20261105T195254206535Z-3dc4affaea634821921cb7b96db6e6d5.jsonl',
  'rawSha256': 'b17d34674f719f6b3dbdeae0d3e707988ead92e9719d8945b4c750c4cba9ec84',
  'archive': 'firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk',
  'archiveSha256': '0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77',
  'receipt': 'out/tooling/20261105T195254206535Z-3dc4affaea634821921cb7b96db6e6d5/receipt.json',
  'receiptSha256': 'eec9bcadf509adbf44026277af7c29a49aeec6683066e404a65e01dddc647e36'},
 {'raw': 'firmware/security-policy-owner/20261105T195255435264Z-43e2778c13cc4f5c966e8cf537ee2de4.jsonl',
  'rawSha256': '2943cefe8718bc2e50562cbc1943f5a7d594b9241113844e366e1a9932ed90af',
  'archive': 'firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk',
  'archiveSha256': '33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b',
  'receipt': 'out/tooling/20261105T195255435264Z-43e2778c13cc4f5c966e8cf537ee2de4/receipt.json',
  'receiptSha256': '825b2888c5d6900ad1adfffeee1c13322ec1bb59aa8671c67a7e49421abf00b3'},
 {'raw': 'firmware/security-policy-owner/20261105T195256797462Z-034cca85bdb54331bb60d5d83a030694.jsonl',
  'rawSha256': 'cb4805449e9049720903c0884799f9d66b8996a1717928be9262d6b3be4e37eb',
  'archive': 'firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk',
  'archiveSha256': '33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b',
  'receipt': 'out/tooling/20261105T195256797462Z-034cca85bdb54331bb60d5d83a030694/receipt.json',
  'receiptSha256': 'f32d87cabaeaac3cf52a2c9fe9c85d6292da13fddf3142f0eab1eff61b1dfbfa'},
 {'raw': 'firmware/security-policy-owner/20261105T195422076755Z-ff6452b1c8994860a22653fed18bc6b0.jsonl',
  'rawSha256': '664909963910ea04b84c0cf358210bd0c0dd3c18152c30e722ee9f4a935eca59',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195422076755Z-ff6452b1c8994860a22653fed18bc6b0/receipt.json',
  'receiptSha256': 'c073d6d18b5eea16e5454ef778a7dce8a9ebfc88858a90ed3248b0de828f14ce'},
 {'raw': 'firmware/security-policy-owner/20261105T195422646345Z-69e9146daf854fe486343aaca7f4cde3.jsonl',
  'rawSha256': '7c260b8020f885a00730858682adaafff399cbd3d5efad5d7484271d71a4cf72',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195422646345Z-69e9146daf854fe486343aaca7f4cde3/receipt.json',
  'receiptSha256': '6963d02047d895c6c622f4987a271d6d3cc51f65a4d33412d988e4e0e33cc13a'},
 {'raw': 'firmware/security-policy-owner/20261105T195423210441Z-5208a1a7d709447a9ba9adc1a784d1e2.jsonl',
  'rawSha256': '4ff678e322ccae4e39ea29e8d1aed0fe4118d66f491e7cddaeccd68d2b79ebe9',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195423210441Z-5208a1a7d709447a9ba9adc1a784d1e2/receipt.json',
  'receiptSha256': '0e05fcc85a73531d44c59550713861d37f31f11cbeee547165d25ec88e71ba43'},
 {'raw': 'firmware/security-policy-owner/20261105T195423782052Z-499d0488a245415aaa3ab3388e725f4a.jsonl',
  'rawSha256': '17b32360ccd3ff9d0f9c518689263766c2b2ea99631f5195fb6a8502731b32af',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195423782052Z-499d0488a245415aaa3ab3388e725f4a/receipt.json',
  'receiptSha256': 'a928524bcd360b2eb4a1960b386cca27c379f10590d714a3e5dd32d1ba6a1539'},
 {'raw': 'firmware/security-policy-owner/20261105T195614347261Z-02d97381379d4427b6dee493a5ef37f4.jsonl',
  'rawSha256': 'd2512b669d439542c88e8306bd98d797e57ac15f7e68eb01aa0e41ac082f116f',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195614347261Z-02d97381379d4427b6dee493a5ef37f4/receipt.json',
  'receiptSha256': '0b79e77610c62291d95b992395af26dbe38912c3b858f80471387fa5fe20af55'},
 {'raw': 'firmware/security-policy-owner/20261105T195655261546Z-c812eaf1cacb44009ea9377604ff0226.jsonl',
  'rawSha256': 'cd1b4b7e6957896669906c3334f0d9058b52a20769b4139de20d2750671dff12',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195655261546Z-c812eaf1cacb44009ea9377604ff0226/receipt.json',
  'receiptSha256': 'c6cc9a9ae50d25c968158ebd75fcc9fa0c1856486d814529666eeb1d52528c5c'},
 {'raw': 'firmware/security-policy-owner/20261105T195655893159Z-8887f673fabc494ab93deedbfe18225b.jsonl',
  'rawSha256': '31e0039123aa8741706190942bbcb27ef0f5651f63ad1ca0992ae12a752fa900',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195655893159Z-8887f673fabc494ab93deedbfe18225b/receipt.json',
  'receiptSha256': '0a7aa4a21f6c84fac2da90148fda6b74fa30b42992e66519f1ec4292dc71efc3'},
 {'raw': 'firmware/security-policy-owner/20261105T195943533491Z-f8891f997d264f1caf5e8f5712ef20c5.jsonl',
  'rawSha256': '1fdde257e1bd824b3670678b6d88e703ca3b79a5b001cb8f7cde7fbc59aea9d8',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195943533491Z-f8891f997d264f1caf5e8f5712ef20c5/receipt.json',
  'receiptSha256': 'edb97565ed18eeee8139e74df9cd03a7682300a719d3a9be54736f8599b94e59'},
 {'raw': 'firmware/security-policy-owner/20261105T195944116560Z-b65c05ededda49d1a730f3f6709ebcf7.jsonl',
  'rawSha256': '5a9e51b4169bf95cc3bc4966d54f9a5620e519c325fc349d0f708ea94877ef19',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195944116560Z-b65c05ededda49d1a730f3f6709ebcf7/receipt.json',
  'receiptSha256': '6c51601d135c84958296511a9dc2d249f89dfa1de358d78d4df7cfac450b8c88'},
 {'raw': 'firmware/security-policy-owner/20261105T195944682173Z-57b34b6b7a2a415396e2677dab889060.jsonl',
  'rawSha256': '86eb008d04b49a5bf1425f2db7d441e8fd3c2db30707cdc5b872c6d0c01cd092',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195944682173Z-57b34b6b7a2a415396e2677dab889060/receipt.json',
  'receiptSha256': '8cc87bb7a85b5c3c7ffcb09ea466fa71ae1e68eebff1455dceef54633ebfedc4'},
 {'raw': 'firmware/security-policy-owner/20261105T195945250261Z-fd99eeb54bf14763b6b2f9509a71eacf.jsonl',
  'rawSha256': 'e117ef36071b16106bc805be03bb99648a2ea69c540168d358e00f5881696042',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195945250261Z-fd99eeb54bf14763b6b2f9509a71eacf/receipt.json',
  'receiptSha256': '9816b7ef61c47c85c27fce088c5e5b0e2cb822579fb11cd4b685df92bcff6456'},
 {'raw': 'firmware/security-policy-owner/20261105T195945807318Z-704d6653e8fa4a249931c7fa82aadc9f.jsonl',
  'rawSha256': 'd10ed364b211189e98acc6dc62267ac7f9ada2fdbb093ab48a7aca56035c7bfd',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195945807318Z-704d6653e8fa4a249931c7fa82aadc9f/receipt.json',
  'receiptSha256': 'fcb206a85a299de79f595139b13b819d3ca27e1ef2975f8eac9e016c25534328'},
 {'raw': 'firmware/security-policy-owner/20261105T195946359904Z-163c20ea4dc444de9d9fe1c5fc6454ca.jsonl',
  'rawSha256': '28da5f5ce3899986052e3a459c34e2a019fcaa74f0441cfc225661e221b770a8',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T195946359904Z-163c20ea4dc444de9d9fe1c5fc6454ca/receipt.json',
  'receiptSha256': '20f7b6465008881b36be6e39ab239f158376eb34c1fcbcd5e285e1caf8b47183'},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184720581016Z-8456a07eeb35436c937d1bfc54e0bcd7.jsonl',
  'rawSha256': 'aa7f0ca10db1409d22ce1f9b2f52466b19f0430daeb038b70f5077c5f7ddf685',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T184720581016Z-8456a07eeb35436c937d1bfc54e0bcd7/receipt.json',
  'receiptSha256': '5f1f9905b61e53fe381bbb1b09938b3cb1e0ed2ad952f64fb9fc186dcae5e89f',
  'select': ['getInstance()Landroid/app/admin/DeviceStateCache;']},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184721338118Z-badeccd8f3524d218ce8c81c9ac4967e.jsonl',
  'rawSha256': '2c4f6b688ac1a946d9ffb28a7b7985ecba4884ffad6f3dbbd5f1072eac63259a',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184721338118Z-badeccd8f3524d218ce8c81c9ac4967e/receipt.json',
  'receiptSha256': 'af16ebb187aa6c83dd79370fe49e1f81275512f91dda7d9ebe3b435fa46a577b',
  'select': ['isDeviceProvisioned()Z', 'isUserOrganizationManaged(I)Z']},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184721915719Z-33ed76cd4a3745e3bc3eb3e24d8baa0e.jsonl',
  'rawSha256': '612b5e86939b5f9b7dba489783b3fccb26f0ee1bcb30589ea70dfe2293e03403',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184721915719Z-33ed76cd4a3745e3bc3eb3e24d8baa0e/receipt.json',
  'receiptSha256': 'e77d0c248d102fb6914ddb01d1571d37e7075317a86290ea6910fead77db94f7',
  'select': ['isSecureLockDeviceEnabled()Z', 'onBootCompleted()V']},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184723642251Z-a2f4d2df3f9345aba0144cc22c51913d.jsonl',
  'rawSha256': '6243b143a3f67027b806b48bcecf4d93a7e33861d7cb548bfc304d9686841d54',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184723642251Z-a2f4d2df3f9345aba0144cc22c51913d/receipt.json',
  'receiptSha256': '7649f64ce8cda3cde3d9d04e1d080b65caed9667ffa9560a0fbf80f2d29f8b31',
  'select': ['saveToFile(Landroid/util/AtomicFile;ZILcom/android/server/security/authenticationpolicy/settings/SecureLockDeviceSettingsManagerImpl;)V',
             'updateStateAndWriteToFile(IZ)V']},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184754304025Z-be11a0ebe3504e7c958804465d9aa3bc.jsonl',
  'rawSha256': '56a74f2378ee0f667258222d7d615114fa904ec88be4cfe5d9e269d40cad8e78',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184754304025Z-be11a0ebe3504e7c958804465d9aa3bc/receipt.json',
  'receiptSha256': 'a80dfcb45402df80324135c7f0e822c208f9d0fda608389d2214162bb1a22486',
  'select': ['<init>(Lcom/android/server/devicepolicy/Injector;Lcom/android/server/devicepolicy/PolicyPathProvider;)V',
             'getCurrentFailedPasswordAttempts(Ljava/lang/String;IZ)I',
             'getPasswordHistoryLength(Landroid/content/ComponentName;IZ)I']},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184828161578Z-b0db4455583247c7bff69702482223f4.jsonl',
  'rawSha256': '20d10f9ff95cd8e37e12a61b09c58250b4ddcfdcdc92e49d8abe2a9453e0514d',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184828161578Z-b0db4455583247c7bff69702482223f4/receipt.json',
  'receiptSha256': 'b25bfa9b31916a196ef112cc71cea6df1f34b7db631fecd3a9f2611d3189242c',
  'select': ['initializePolicyDataFromXml(ILcom/android/server/devicepolicy/DevicePolicyData;)V',
             'makeJournaledFile(ILjava/lang/String;)Lcom/android/internal/util/JournaledFile;',
             'updateUserSetupCompleteAndPaired()V']},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184828756174Z-93bddc0d62044b4298a9695a7fe2622d.jsonl',
  'rawSha256': 'a50cb6537e3b7eed6f97450eee6c61a61daa0bd27744b55230cb920fd5e07bf2',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184828756174Z-93bddc0d62044b4298a9695a7fe2622d/receipt.json',
  'receiptSha256': '2e032b92d85890ac584f0001a0e4dd6f9ac5172b999c070704e812089b0a2186',
  'select': ['load()V']},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184929076801Z-728968ca115240449e0b615d277c08ad.jsonl',
  'rawSha256': '2a9fb4ee0745c874fdb06b7db1119a573fffd2bc392f1209adab3fbffff85c8b',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184929076801Z-728968ca115240449e0b615d277c08ad/receipt.json',
  'receiptSha256': 'cbccccea68ff4f5581f1b1e13289b3a486bfb653433ea6fab2755f267840f7a3',
  'select': ['load(Lcom/android/server/devicepolicy/DevicePolicyData;Lcom/android/internal/util/JournaledFile;Ljava/util/function/Function;Landroid/content/ComponentName;)V']},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T184929646552Z-83ff1bda87b3428da16bdcfca7ad222b.jsonl',
  'rawSha256': 'f2104775106d3584dce67185e4b7e5d0fcce7a805013080c248352dee97ac5b1',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T184929646552Z-83ff1bda87b3428da16bdcfca7ad222b/receipt.json',
  'receiptSha256': 'c004c8f387a606e55f151583310eedd114f702d16b3d587764314f89ad14b6a6',
  'select': ['getUserData(I)Lcom/android/server/devicepolicy/DevicePolicyData;',
             'getUserDataUnchecked(I)Lcom/android/server/devicepolicy/DevicePolicyData;']},
 {'raw': 'firmware/security-user-binding/20261105T153354981341Z-b23ec7648928490f934a1690c6f7129d.jsonl',
  'rawSha256': '1e015c602dd0a3a735203df413c78051dfa2e2e1e918b68dfabe64871b36bf56',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'select': ['isEscrowTokenRequired(I)Z']},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185827096696Z-3987887bd94f410cbacabe3c83ba92c6.jsonl',
  'rawSha256': '6c905010ed7e2f2473ce3915824ad31383670f709842144bc272e0b133240739',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185827096696Z-3987887bd94f410cbacabe3c83ba92c6/receipt.json',
  'receiptSha256': 'dfc51d09829354b8d0fa64fe3a87ff1de936ace986dd72f9d0e01868620b1ed3',
  'select': ['-$$Nest$msyncStateWithDevicePolicyManager(Lcom/android/server/supervision/SupervisionService;I)V']},
 {'raw': 'firmware/authority-bootstrap-policy/20261105T185900858830Z-8d401802ab784cbd86647fab52e126eb.jsonl',
  'rawSha256': 'e07e2e78af629d5b2cf3034db09bb130672cbaf70bbb23ddc1c31be1be846491',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T185900858830Z-8d401802ab784cbd86647fab52e126eb/receipt.json',
  'receiptSha256': 'e81ee27cbfa68fa6aae0179c2372e92756202add5bbf85780f3ac5da95297c53',
  'select': ['setSupervisionEnabledForUserInternal(ILjava/lang/String;Z)V']},
 {'raw': 'firmware/tooling/20261105T123602189303Z-13cb9b7c9f294be296de6da0d63a43c0.jsonl',
  'rawSha256': 'cc88a0875c9f5ae89d16021e8de86748067b6f9b72391c70f35aed484144d5b5',
  'archive': 'firmware/samsung/runtime-20261104/services.jar',
  'archiveSha256': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
  'receipt': 'out/tooling/20261105T123602189303Z-13cb9b7c9f294be296de6da0d63a43c0/receipt.json',
  'receiptSha256': '0a30bd1f6ea91dc3b0ee62fe4942cc5acfe8f42ec45194f6f6cc75d795cdedbc',
  'select': ['getFailureCount(I)I',
             'notifyPasswordMetricsChanged(Lcom/android/internal/widget/LockscreenCredential;I)V',
             'onPostLockCredentialChanged(Lcom/android/internal/widget/LockscreenCredential;I)V']}]

SS='def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'
SF='8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
CF='d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'
UI='0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77'
ST='33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b'
D='Lcom/android/server/devicepolicy/DevicePolicyManagerService;'
L='Lcom/android/server/locksettings/LockSettingsService;'
U='Lcom/android/internal/widget/LockPatternUtils;'
S='Lcom/android/server/security/authenticationpolicy/SecureLockDeviceService;'
FS='Lcom/android/server/security/authenticationpolicy/settings/SecureLockDeviceSettingsFileStore;'
SUP='Lcom/android/server/supervision/SupervisionService;'
FROZEN_F='df78da9e85e05dd1528d69f6a7a51742be94e6fdc886cbe0d717c12c3baff640'

def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def report():
    assert digest(PROJECT/'inventory/authority-bootstrap-policy.json')==FROZEN_F
    methods={};refs=[];archives={}
    for src in SOURCES:
        path=PARENT/src['archive']
        if src['archive'] not in archives:
            assert digest(path)==src['archiveSha256'],str(path)
            archives[src['archive']]=src['archiveSha256']
        assert digest(PROJECT/src['raw'])==src['rawSha256'],src['raw']
        if src.get('receipt'):
            assert digest(PROJECT/src['receipt'])==src['receiptSha256']
            r=json.loads((PROJECT/src['receipt']).read_text())
            assert r['readerExitCode']==0 and r['archiveAndToolPinsVerifiedBeforeAndAfter'] and not r['oemCodeExecuted']
        for line in (PROJECT/src['raw']).open(encoding='utf-8'):
            row=json.loads(line)
            if row['record']=='method':
                b=row['body']
                if src.get('select') is not None and b['signature'] not in src['select']:continue
                key=(src['archiveSha256'],b['owner'],b['signature'])
                if key in methods:assert row['normalizedBodySha256']==methods[key]['normalizedBodySha256']
                methods[key]={**row,'raw':src['raw'],'rawSha256':src['rawSha256']}
            elif row['record']=='reference':refs.append({**row,'archiveSha256':src['archiveSha256'],'raw':src['raw']})
    def method(side,owner,sig):return methods[(side,owner,sig)]
    def a(side,owner,sig,*checks):
        row=method(side,owner,sig);e=[]
        for pc,wanted in checks:
            i=next(i for i in row['body']['instructions'] if i['pc']==pc)
            assert wanted in i.get('reference',''),(owner,sig,pc,wanted,i)
            e.append({'pc':pc,'reference':i['reference']})
        return {'archiveSha256':side,'owner':owner,'signature':sig,'bodySha256':row['normalizedBodySha256'],'raw':row['raw'],'checks':e}
    facts=[]
    def f(identity,claim,*anchors):facts.append({'id':identity,'classification':'observed-source','claim':claim,'anchors':list(anchors)})
    f('P01','Original DeviceAdmins owns one loaded per-user data set and retains the real DPMS delegate; lazy loading invokes active original policy initialization.',
      a(SS,'Lcom/android/server/devicepolicy/DeviceAdmins;','<init>(Lcom/android/server/devicepolicy/Lock;Lcom/android/server/devicepolicy/Injector;Lcom/android/server/devicepolicy/Owners;Lcom/android/server/devicepolicy/DevicePolicyManagerService;)V',(10,'mLock'),(12,'mInjector'),(14,'mOwners'),(24,'mDelegate')),
      a(SS,'Lcom/android/server/devicepolicy/DeviceAdmins;','getUserData(I)Lcom/android/server/devicepolicy/DevicePolicyData;',(29,'initializePolicyDataFromXml')),
      a(SS,D,'initializePolicyDataFromXml(ILcom/android/server/devicepolicy/DevicePolicyData;)V',(33,'DevicePolicyData;->load'),(39,'updateMaximumTimeToLockLocked'),(46,'setStatusBarDisabledInternal')))
    f('P02','Device-admin data loading resolves original package receiver metadata and constructs original DeviceAdminInfo, preserving its required permission check.',
      a(SS,D,'findAdmin(ILandroid/content/ComponentName;Z)Landroid/app/admin/DeviceAdminInfo;',(29,'BIND_DEVICE_ADMIN'),(83,'DeviceAdminInfo;-><init>')),
      a(SS,'Lcom/android/server/devicepolicy/DevicePolicyManagerService$$ExternalSyntheticLambda64;','getOrThrow()Ljava/lang/Object;',(245,'IPackageManager;->getReceiverInfo')))
    f('P03','Password-history length is the original profile/admin strictest-policy aggregation, not a cached integer.',
      a(SS,D,'getPasswordHistoryLength(Landroid/content/ComponentName;IZ)I',(22,'getStrictestPasswordRequirement')),
      a(SS,D,'getStrictestPasswordRequirement(Landroid/content/ComponentName;IZLjava/util/function/Function;I)I',(15,'hasFullCrossUsersPermission'),(33,'getActiveAdminUnchecked'),(58,'getActiveAdminsForLockscreenPoliciesLocked'),(88,'DeviceAdminInfo;->usesPolicy')),
      a(SS,'Lcom/android/server/devicepolicy/DevicePolicyManagerService$$ExternalSyntheticLambda16;','apply(Ljava/lang/Object;)Ljava/lang/Object;',(136,'passwordHistoryLength')))
    f('P04','Credential-owner and profile aggregation depend on actual UserManager profile/challenge state; unrelated R8 cases must not enlarge the required path.',
      a(SS,D,'getCredentialOwner(IZ)I',(20,'withCleanCallingIdentity')),
      a(SS,'Lcom/android/server/devicepolicy/DevicePolicyManagerService$$ExternalSyntheticLambda8;','getOrThrow()Ljava/lang/Object;',(137,'getProfileParent'),(147,'getCredentialOwnerProfile')),
      a(SS,'Lcom/android/server/devicepolicy/DevicePolicyManagerService$$ExternalSyntheticLambda202;','runOrThrow()V',(19,'getProfiles'),(43,'getUserDataUnchecked'),(84,'getParentActiveAdmin')))
    f('P05','Owner updates change the actual DeviceStateCache and notify other local owners; they are not standalone independent boolean writes.',
      a(SS,'Lcom/android/server/devicepolicy/Owners;','setProfileOwner(ILandroid/content/ComponentName;)V',(24,'setHasProfileOwner'),(27,'notifyChangeLocked')),
      a(SS,'Lcom/android/server/devicepolicy/Owners;','removeProfileOwner(I)V',(17,'setHasProfileOwner'),(20,'notifyChangeLocked')),
      a(SS,'Lcom/android/server/devicepolicy/Owners;','setDeviceOwner(ILandroid/content/ComponentName;)V',(51,'mDeviceOwnerType'),(56,'notifyChangeLocked')))
    f('P06','Original setup updates require real Settings observer registration and current user setup data, followed by original persistence.',
      a(SS,D,'onLockSettingsReady()V',(211,'registerContentObserver'),(226,'registerContentObserver'),(245,'registerContentObserver'),(260,'registerContentObserver'),(263,'updateUserSetupCompleteAndPaired')),
      a(SS,'Lcom/android/server/devicepolicy/DevicePolicyManagerService$SetupContentObserver;','onChange(ZLandroid/net/Uri;I)V',(118,'updateUserSetupCompleteAndPaired')),
      a(SS,D,'updateUserSetupCompleteAndPaired()V',(33,'getIntForUser'),(59,'mIsDeviceProvisioned'),(73,'saveSettingsLocked')))
    fail='reportFailedPasswordAttempt(IZ)V'
    f('P07','Failed-report processing authorizes caller/user/profile, consumes real count synchronization, persists, notifies admins and conditionally executes wipe policy.',
      a(SS,D,fail,(13,'hasFullCrossUsersPermission'),(23,'hasCallingOrSelfPermission'),(87,'mFailedPasswordAttempts'),(90,'mFailedPasswordAttemptsFromGateKeeper'),(99,'mFailedPasswordAttempts'),(102,'saveSettingsLocked'),(109,'getAdminWithMinimumFailedPasswordsForWipeLocked'),(131,'sendAdminCommandForLockscreenPoliciesLocked'),(239,'wipeDataNoLock')),
      a(SS,D,'reportFailedPasswordAttemptWithFailureCount(IIZ)V',(62,'getUserData'),(66,'mFailedPasswordAttemptsFromGateKeeper'),(69,'reportFailedPasswordAttempt')))
    f('P08','Samsung LPU synchronizes the actual LSS failure count; guest LPU plain failure reporting omits this Samsung operation.',
      a(SF,U,'reportFailedPasswordAttempt(I)V',(40,'ILockSettings;->getFailureCount'),(77,'reportFailedPasswordAttemptWithFailureCount'),(90,'TrustManager;->reportUnlockAttempt')),
      a(CF,U,'reportFailedPasswordAttempt(I)V',(14,'DevicePolicyManager;->reportFailedPasswordAttempt'),(28,'TrustManager;->reportUnlockAttempt')),
      a(SS,L,'getFailureCount(I)I',(11,'getHermesService'),(19,'SyntheticPasswordManager;->getFailureCount'),(26,'getGateKeeperService'),(34,'SyntheticPasswordManager;->getFailureCount')))
    f('P09','Real success-report processing conditionally resets policy state through original synchronous clean-identity work and saves/admin notification.',
      a(SS,D,'reportSuccessfulPasswordAttempt(I)V',(85,'withCleanCallingIdentity')),
      a(SS,'Lcom/android/server/devicepolicy/DevicePolicyManagerService$$ExternalSyntheticLambda27;','runOrThrow()V',(61,'mFailedPasswordAttempts'),(63,'mFailedPasswordAttemptsFromGateKeeper'),(92,'mPasswordOwner'),(94,'saveSettingsLocked'),(105,'sendAdminCommandForLockscreenPoliciesLocked')))
    f('P10','Credential-change policy updates include expiration, validity, CA approval and admin work plus per-user persistence.',
      a(SS,D,'reportPasswordChanged(Landroid/app/admin/PasswordMetrics;I)V',(19,'isSystemUid'),(74,'mFailedPasswordAttempts'),(114,'updatePasswordValidityCheckpointLocked'),(121,'updatePasswordExpirationsLocked'),(130,'setExpirationAlarmCheckLocked'),(136,'sendAdminCommandForLockscreenPoliciesLocked'),(139,'removeCaApprovalsIfNeeded'),(166,'saveSettingsLocked')),
      a(SS,D,'setPasswordHistoryLength(Landroid/content/ComponentName;IZ)V',(61,'passwordHistoryLength'),(63,'updatePasswordValidityCheckpointLocked'),(66,'saveSettingsLocked')))
    f('P11','Original saveSettingsLocked checks the real store result, syncs the original file and notifies/invalidate caches; its void return is not a durable-success attestation.',
      a(SS,D,'saveSettingsLocked(IZZZ)V',(13,'DevicePolicyData;->store'),(43,'DevicePolicyData;->sync'),(54,'sendChangedNotification'),(61,'invalidateBinderCaches')))
    f('P12','Native Settings history uses actual LSS history/salt and genuine DPM history length; the original setter updates the same history key.',
      a(CF,U,'checkPasswordHistory([B[BI)Z',(7,'lockscreen.passwordhistory'),(20,'getRequestedPasswordHistoryLength'),(27,'getSalt'),(35,'passwordToHistoryHash')),
      a(CF,U,'getRequestedPasswordHistoryLength(I)I',(5,'DevicePolicyManager;->getPasswordHistoryLength')),
      a(SS,L,'onPostLockCredentialChanged(Lcom/android/internal/widget/LockscreenCredential;I)V',(47,'lockscreen.passwordhistory'),(82,'getPasswordHistoryLength'),(189,'setString')))
    f('P13','Original LSS credential-metrics callbacks asynchronously invoke real DPM reportPasswordChanged; they are part of the same authority transaction tail.',
      a(SS,L,'notifyPasswordMetricsChanged(Lcom/android/internal/widget/LockscreenCredential;I)V'),
      a(SS,'Lcom/android/server/locksettings/LockSettingsService$$ExternalSyntheticLambda3;','run()V',(17,'DevicePolicyManager;->reportPasswordChanged'),(33,'DevicePolicyManager;->reportPasswordChanged')))
    f('P14','Supervision actual setter changes persisted state before its clean-identity policy work; original file-write errors have a failure path.',
      a(SS,SUP,'setSupervisionEnabledForUserInternal(ILjava/lang/String;Z)V',(19,'saveUserData'),(38,'withCleanCallingIdentity'),(55,'withCleanCallingIdentity')),
      a(SS,'Lcom/android/server/supervision/SupervisionSettings;','saveUserData()V',(27,'AtomicFile;->startWrite'),(252,'AtomicFile;->finishWrite'),(259,'AtomicFile;->failWrite')))
    f('P15','SecureLockDevice enable/disable are genuine policy operations with StrongAuth, restrictions, user and biometric completion ownership.',
      a(SS,S,'enableSecureLockDevice(Landroid/os/UserHandle;)I',(27,'switchUserToForeground'),(81,'requireStrongAuth'),(166,'applySecureLockDeviceSettings'),(171,'storeSecureLockDeviceEnabled'),(209,'WindowManagerInternal;->lockNow')),
      a(SS,S,'disableSecureLockDevice(Landroid/os/UserHandle;)I',(114,'isUserUnlocked'),(162,'LockSettingsInternal;->disableSecureLockDevice'),(222,'updateStateAndWriteToFile'),(225,'notifyAllSecureLockDeviceListenersEnabledStatusUpdated')))
    f('P16','SecureLockDevice writes update memory before a queued original file write; callback/operation return does not acknowledge disk completion.',
      a(SS,FS,'updateStateAndWriteToFile(IZ)V',(16,'mIsEnabled'),(18,'mClientUserId'),(33,'Handler;->post')),
      a(SS,'Lcom/android/server/security/authenticationpolicy/settings/SecureLockDeviceSettingsFileStore$$ExternalSyntheticLambda0;','run()V',(7,'mIsEnabled'),(9,'mClientUserId'),(13,'saveToFile')))
    f('P17','Full original DPMS bootstrap is a broader active alternative, with real migration/reapplication and other conditional management effects.',
      a(SS,D,'systemReady(I)V',(137,'FactoryResetter;->factoryReset'),(242,'reapplyAllPoliciesOnBootLocked'),(299,'migratePoliciesToPolicyEngineLocked'),(414,'onLockSettingsReady')),
      a(SS,D,'<init>(Lcom/android/server/devicepolicy/Injector;Lcom/android/server/devicepolicy/PolicyPathProvider;)V',(2979,'DevicePolicyData;->store'),(2994,'writeDeviceOwner'),(3338,'Owners;->load'),(3554,'LocalServices;->addService')))
    r8=[]
    for caller,sig,cls,callback in [
       (D,'getCredentialOwner(IZ)I',8,'getOrThrow()Ljava/lang/Object;'),
       (D,'getPasswordHistoryLength(Landroid/content/ComponentName;IZ)I',16,'apply(Ljava/lang/Object;)Ljava/lang/Object;'),
       (D,'reportSuccessfulPasswordAttempt(I)V',27,'runOrThrow()V'),
       (D,'getActiveAdminsForUserAndItsManagedProfilesLocked(ILjava/util/function/Predicate;)Ljava/util/List;',202,'runOrThrow()V'),
       (D,'findAdmin(ILandroid/content/ComponentName;Z)Landroid/app/admin/DeviceAdminInfo;',64,'getOrThrow()Ljava/lang/Object;')]:
        owner='Lcom/android/server/devicepolicy/DevicePolicyManagerService$$ExternalSyntheticLambda'+str(cls)+';'
        ctor=method(SS,owner,'<init>(I)V')['body']
        assert ctor['registerCount']==2
        assert any(i['opcode']=='IPUT' and i.get('registers')==[1,0] and '->$r8$classId:I' in i.get('reference','') for i in ctor['instructions'])
        ins=method(SS,caller,sig)['body']['instructions']
        n,call=next((n,i) for n,i in enumerate(ins) if i.get('reference')==owner+'-><init>(I)V')
        reg=call['registers'][1];assignment=next(i for i in reversed(ins[:n]) if i.get('registers',[None])[0]==reg and i['opcode'].startswith('CONST'))
        key=assignment['literal'];body=method(SS,owner,callback)['body'];sw=next(i for i in body['instructions'] if i['opcode'] in ('PACKED_SWITCH','SPARSE_SWITCH'))
        payload=next(i for i in body['instructions'] if i['pc']==sw['targetPc']);chosen=next((x for x in payload['switchElements'] if x['key']==key),None)
        target=sw['pc']+chosen['offsetFromReferringSwitchPc'] if chosen else sw['pc']+sw['codeUnits']
        r8.append({'caller':caller+'->'+sig,'constructor':owner+'-><init>(I)V','constructorPc':call['pc'],'classId':key,'callback':owner+'->'+callback,'switchPc':sw['pc'],'entryPc':target,'callbackBodySha256':method(SS,owner,callback)['normalizedBodySha256']})
    assert [(x['classId'],x['entryPc']) for x in r8[:4]]==[(0,127),(9,132),(0,50),(2,5)]
    # Prove exact existing LPU user/count argument order rather than naming two ints from memory.
    ins=method(SF,U,'reportFailedPasswordAttempt(I)V')['body']['instructions']
    get=next(i for i in ins if i['pc']==40);report=next(i for i in ins if i['pc']==77)
    assert get['registers']==[1,6] and report['registers']==[0,6,1]
    # The selected service method's first int indexes user data; second int is stored as count.
    ins=method(SS,D,'reportFailedPasswordAttemptWithFailureCount(IIZ)V')['body']['instructions']
    assert next(i for i in ins if i['pc']==62)['registers']==[1,4]
    assert next(i for i in ins if i['pc']==66)['registers']==[5,1]
    proof=[];edges=[]
    for (side,owner,sig),row in sorted(methods.items()):
        b=row['body'];proof.append({'archiveSha256':side,'owner':owner,'signature':sig,'bodySha256':row['normalizedBodySha256'],'hasCode':b['hasCode'],'instructionCount':len(b['instructions']),'tryHandlerCount':len(b['catches']),'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],'raw':row['raw']})
        for i in b['instructions']:
            ref=i.get('reference','')
            if i['opcode'].startswith('INVOKE') and any(t in ref for t in ['reportFailedPassword','reportSuccessfulPassword','reportPasswordChanged','checkPasswordHistory','getPasswordHistoryLength','getFailureCount','saveUserData','updateStateAndWriteToFile','registerContentObserver']):edges.append({'archiveSha256':side,'caller':owner+'->'+sig,'pc':i['pc'],'callee':ref,'raw':row['raw']})
    counts={}
    for src in SOURCES:
        if src.get('receipt'):
            receipt=json.loads((PROJECT/src['receipt']).read_text());ref=receipt['query'].get('reference')
            if ref:counts[src['archiveSha256'][:8]+':'+ref]=receipt['referenceMatchCount']
    result={'schema':'security-policy-owner/v1','status':'source-owner-frontier-frozen-no-policy-provider','selected':False,'policyProviderImplemented':False,'runtimeWrapperImplemented':False,'oemExecuted':False,'phoneActions':False,'privatePolicyFilesRead':False,'frozenFInventorySha256':FROZEN_F,'sourceAssertions':facts,'selectedMethods':proof,'selectedMethodCount':len(proof),'selectedCodeBodyCount':sum(x['hasCode'] for x in proof),'originalR8SelectedCases':r8,'actualOperationCallsites':edges,'directReferenceScanCounts':counts,'sources':SOURCES,'archivePins':archives,'actualFailedReportArgumentOrder':['userId','realFailureCount','parentInstance'],'minimumObservedOwners':['Original DPMS/DeviceAdmins/Owners/DevicePolicyData lock and delegate, genuine admin package metadata and profile/challenge state','Original DeviceStateCache producer plus live owner and setup updates','Authoritative LSS/SPM failure-count backend and history/salt/hash-factor state','Original Supervision loaded settings, user/role/profile-owner updates and persistence','Original SecureLockDevice store/controllers/StrongAuth/biometric/user owner and queued-write completion','One actual DPM report/change sender, original admin effects and lifecycle/handoff drain'],'genuineBlockers':['Private authoritative management/user/policy values remain unknown, never no-admin/default-off','Original data loading invokes active DPMS initialization; DeviceAdmins retains actual DPMS delegate','Plain guest failure reporting omits Samsung actual failure-count synchronization','History needs both same-owner DPM requirements and authoritative LSS history/salt/hash-factor; a redirected length getter alone is insufficient','Original failed/change/success operations include persistence, admin/profile/wipe/expiration effects','Full original DPMS constructor/bootstrap dependencies and policy migration/effects are not assembled','SecureLockDevice memory update, status publication and queued persistence are distinct progress points','No accepted cross-authority operation/result/update/persistence or shutdown protocol exists'],'sourceApiDisposition':'Retain the identified genuine original producers and existing typed operations, or close exact source extraction of their real state/effects/update owners before proposing implementation. No new policy values, provider/interface or readiness booleans are supplied as closure.','limits':['Bounded static archives and exact direct callers only; not installed code, reflection, runtime policy or acceptance','R8 branches are matched to actual constructor discriminators; unrelated cases are not automatic dependencies','No attempt to execute conditional admin wipe, factory reset, policy writes, credential or factor actions','Local LockSettings listener and user-registry closure remains assigned to peer streams; no duplicate Trust reporting is authored']}
    out=PROJECT/'inventory/security-policy-owner.json';out.write_text(json.dumps(result,indent=2)+'\n')
    generated=PROJECT/'out/security-policy-owner';generated.mkdir(exist_ok=True,parents=True)
    (generated/'verification.json').write_text(json.dumps({'inventorySha256':digest(out),'toolSha256':digest(Path(__file__)),'assertionGroups':len(facts),'r8CasesVerified':len(r8),'selectedMethods':len(proof),'codeBodies':sum(x['hasCode'] for x in proof),'rawPins':len(SOURCES),'oemExecuted':False},indent=2)+'\n')
    print(json.dumps({'inventorySha256':digest(out),'assertions':len(facts),'r8Cases':len(r8),'methods':len(proof),'codeBodies':sum(x['hasCode'] for x in proof)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',action='store_true',required=True);p.parse_args();report()
