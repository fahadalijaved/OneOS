import android.os.Looper;
import android.os.SystemClock;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.InputStreamReader;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Samsung's speaker and audio processing pipeline for the guest (0.4.58 -> 0.5.36).
 *
 * One UI's audioserver runs three Samsung effects together on the output mix, in order:
 *   1. Dolby DAX3 (type 46d279d9 -> DAX3_S_3.14.0.0_r1)
 *   2. Samsung SoundBoosterPlus (type ee8aeac0 -> asymmetric stereo speaker
 *      calibration, loudness and distortion limiter from /vendor/etc/SoundBoosterParam.txt)
 *   3. Samsung SoundAlive (type c4da1d1f -> 9-band EQ & volume control / libaudiosaplus_sec.so)
 *
 * Parameter IDs verified directly from S24 FE /vendor/lib64/soundfx/*.so:
 *   - libswdap.so (DlbEffectContext::setParam): param 19 = EFFECT_PARAM_ENABLE,
 *     param 0 = EFFECT_PARAM_PROFILE (0..5), param 21 = CONTENT_PROC_ENABLE.
 *     (Volume leveler stays at dax-default.xml profile tuning, matching One UI's -1 KVP;
 *     param 5 is EFFECT_PARAM_REVERT_SPECIFIC_PARAMS on DAX3_S; legacy CPDP param 5 is
 *     used only as a fallback when param 19 < 0.)
 *   - libaudiosaplus_sec.so (SA_setParameter): param 9 = SA_PARAM_PROPERTIES
 *     with 22-byte value (int16 curPreset=-1, int16 numBands=9, int16[9] in -12..12 dB),
 *     fallback param 2 = SA_PARAM_BAND_LEVEL.
 *   - libsamsungSoundbooster_plus.so: DEVICE_IND | VOLUME_IND | AUDIO_MODE_IND;
 *     enables automatically on speaker and auto-bypasses on headphones/BT/voice calls.
 *
 * Multi-output support:
 *   When the guest AudioFlinger patch (ONEOS_GUEST_SOUNDBOOSTER_PATCH) is active, passing
 *   priority = (0x51000000 | ioHandle) with sessionId = 0 attaches an independent session-0
 *   effect chain to every speaker MIXER output thread (PRIMARY, DEEP_BUFFER, FAST) so apps
 *   routing to PRIMARY/FAST (e.g. TikTok, games, short video players) get the exact same
 *   DAX3_S -> SoundBoosterPlus -> SoundAlive processing as DEEP_BUFFER apps (YouTube, YTM).
 *   Self-verifies via dumpsys media.audio_flinger and stays single-output on unpatched ROMs.
 */
public final class OneOSSoundFx {
 private static final String DOLBY_TYPE = "46d279d9-9be7-453d-9d7c-ef937f675587";
 private static final String SOUNDALIVE_TYPE = "c4da1d1f-7cdf-42e2-ba60-efc7eb3508a3";
 private static final String SOUNDBOOSTER_TYPE = "ee8aeac0-5d4b-11e5-a837-0800200c9a66";
 private static final String TYPE_NULL = "ec7178ec-e5e1-4432-a3f4-4657e6795210";

 // Magic priority prefix recognized by AudioFlinger::createEffect hook to target an explicit I/O handle on session 0.
 private static final int PRIORITY_IO_MAGIC = 0x51000000;
 private static final int DEVICE_OUT_EARPIECE = 0x1;

 // AudioOutputFlags masks for eligible speaker MIXER threads (PRIMARY | FAST | DEEP_BUFFER).
 private static final int FLAG_DIRECT = 0x1;
 private static final int FLAG_PRIMARY = 0x2;
 private static final int FLAG_FAST = 0x4;
 private static final int FLAG_DEEP_BUFFER = 0x8;
 private static final int FLAG_COMPRESS_OFFLOAD = 0x10;
 private static final int FLAG_MMAP_NOIRQ = 0x4000;
 private static final int FLAG_INCALL_MUSIC = 0x10000;
 private static final int ELIGIBLE_INCLUDE_MASK = FLAG_PRIMARY | FLAG_FAST | FLAG_DEEP_BUFFER;
 private static final int ELIGIBLE_EXCLUDE_MASK = FLAG_DIRECT | FLAG_COMPRESS_OFFLOAD | FLAG_MMAP_NOIRQ | FLAG_INCALL_MUSIC;

 // Samsung DAX3_S EffectContext::setParam IDs (4-byte LE int32 values).
 private static final int DAX_PARAM_PROFILE = 0;
 private static final int DAX_PARAM_ENABLE = 19;
 private static final int DAX_PARAM_CONTENT_PROC_ENABLE = 21;

 // Legacy CPDP fallback (non-DAX3_S vendor libs only).
 private static final int LEGACY_PARAM_CPDP_VALUES = 5;
 private static final int LEGACY_CPDP_ENABLE = 0;
 private static final int LEGACY_CPDP_PROFILE = 0x0A000000;

 // Samsung SoundAlive SA_setParameter IDs.
 private static final int SA_PARAM_BAND_LEVEL = 2;
 private static final int SA_PARAM_PROPERTIES = 9;
 private static final int SA_NUM_BANDS = 9;

 private static final String PRIMARY_CONFIG_PATH = "/data/user/0/com.fahadali.oneos.guest/files/oneos_sound.conf";
 private static final String LEGACY_CONFIG_PATH = "/data/oneos_dolby.conf";
 private static final String STATE_PATH = "/data/oneos_bootui/sound_state";

 private static Method sSetParamBytes;
 private static Method sSetParamByteParam;
 private static Method sSetEnabled;
 private static Method sGetEnabled;
 private static Method sHasControl;
 private static Method sGetId;
 private static Method sGetDescriptor;
 private static Method sRelease;

 private static final class SoundConfig {
  int enable = 1;
  int profile = 0;
  int soundBooster = 1;
  final int[] eqBands = new int[SA_NUM_BANDS];

  boolean sameAs(SoundConfig o) {
   return o != null && enable == o.enable && profile == o.profile
       && soundBooster == o.soundBooster && Arrays.equals(eqBands, o.eqBands);
  }
 }

 private static final class Chain {
  final int ioHandle; // 0 = default (getOutputForEffect), >0 = explicit I/O handle
  Object dolby;
  Object soundBooster;
  Object soundAlive;

  Chain(int ioHandle) {
   this.ioHandle = ioHandle;
  }

  void releaseAll() {
   releaseOne(soundAlive); soundAlive = null;
   releaseOne(soundBooster); soundBooster = null;
   releaseOne(dolby); dolby = null;
  }

  int anyEffectId() {
   if (dolby != null) return effectId(dolby);
   if (soundBooster != null) return effectId(soundBooster);
   if (soundAlive != null) return effectId(soundAlive);
   return -1;
  }

  void collectIds(Set<Integer> out) {
   int id;
   if ((id = effectId(dolby)) >= 0) out.add(id);
   if ((id = effectId(soundBooster)) >= 0) out.add(id);
   if ((id = effectId(soundAlive)) >= 0) out.add(id);
  }
 }

 private static final class AfSnapshot {
  final List<Integer> eligibleIos = new ArrayList<>();
  final Map<Integer, Integer> effectToIo = new HashMap<>();
  final Set<Integer> activeIos = new HashSet<>();
 }

 public static void main(String[] args) throws Exception {
  final int guest = Integer.parseInt(args[0]);
  final UUID singleType = args.length > 1 ? UUID.fromString(args[1]) : null;
  final UUID implNull = UUID.fromString(TYPE_NULL);

  Looper.prepareMainLooper();
  Class<?> c = Class.forName("android.media.audiofx.AudioEffect");
  Constructor<?> ctor = c.getDeclaredConstructor(UUID.class, UUID.class, int.class, int.class);
  ctor.setAccessible(true);
  sSetParamBytes = findMethod(c, "setParameter", int.class, byte[].class);
  sSetParamByteParam = findMethod(c, "setParameter", byte[].class, byte[].class);
  sSetEnabled = findMethod(c, "setEnabled", boolean.class);
  sGetEnabled = findMethod(c, "getEnabled");
  sHasControl = findMethod(c, "hasControl");
  sGetId = findMethod(c, "getId");
  sGetDescriptor = findMethod(c, "getDescriptor");
  sRelease = findMethod(c, "release");

  String lastStamp = "";
  SoundConfig cfg = readConfig();
  Chain primary = new Chain(0);
  List<Chain> extraChains = new ArrayList<>();
  boolean missingSaLogged = false;
  boolean missingSbLogged = false;

  // The guest's audioserver registers late (guest_start.sh): retry up to ~60 s.
  for (int i = 0; i < 30 && alive(guest); i++) {
   cfg = readConfig();
   String why = (i == 0 || i == 29) ? ("try " + (i + 1)) : null;
   if (singleType != null) {
    primary.dolby = createSingle(ctor, singleType, implNull, 0, cfg, why, true);
    if (primary.dolby != null) break;
   } else {
    if (primary.dolby == null) primary.dolby = createDolby(ctor, implNull, 0, cfg, why, true);
    if (primary.soundBooster == null) primary.soundBooster = createSoundBooster(ctor, implNull, 0, cfg, why);
    if (primary.soundAlive == null) primary.soundAlive = createSoundAlive(ctor, implNull, 0, cfg, why);
    if (primary.dolby != null || primary.soundBooster != null || primary.soundAlive != null) break;
   }
   Thread.sleep(2000);
  }

  if (primary.dolby == null && primary.soundBooster == null && primary.soundAlive == null) {
   log("no Samsung/Dolby audio effects on the output mix; exiting");
   writeState(false, false, false);
   return;
  }

  // Give SoundBooster & SoundAlive one short follow-up chance if audioserver only partially registered on try 1.
  if (singleType == null) {
   if (primary.soundBooster == null && alive(guest)) {
    primary.soundBooster = createSoundBooster(ctor, implNull, 0, cfg, "follow-up");
    if (primary.soundBooster == null) missingSbLogged = true;
   }
   if (primary.soundAlive == null && alive(guest)) {
    primary.soundAlive = createSoundAlive(ctor, implNull, 0, cfg, "follow-up");
    if (primary.soundAlive == null) missingSaLogged = true;
   }
   if (primary.soundAlive == null && !missingSaLogged) {
    log("SoundAlive (" + SOUNDALIVE_TYPE + ") not present in vendor effect HAL");
    missingSaLogged = true;
   }
   if (primary.soundBooster == null && !missingSbLogged) {
    log("SoundBoosterPlus (" + SOUNDBOOSTER_TYPE + ") not present in vendor effect HAL");
    missingSbLogged = true;
   }
  }

  final boolean expectDolby = (primary.dolby != null);
  final boolean expectSb = (primary.soundBooster != null);
  final boolean expectSa = (primary.soundAlive != null);

  // Attach matching session-0 chains to all other speaker MIXER outputs (PRIMARY/FAST/DEEP_BUFFER)
  // when the AudioFlinger multi-output hook is active; self-verifies via dumpsys.
  boolean multiOutputSupported = attachExtraOutputs(
      ctor, singleType, implNull, cfg, primary, extraChains, expectDolby, expectSb, expectSa);

  lastStamp = configStamp();
  writeState(isActive(primary.dolby, cfg.enable != 0),
      isActive(primary.soundAlive, true),
      isActive(primary.soundBooster, cfg.soundBooster != 0));

  boolean wasMusic = false;
  boolean verifiedOnPlayback = false;
  int moves = 0;
  int recoveryTicks = 0;
  int atDevice = musicDevice();
  while (alive(guest)) {
   Thread.sleep(400);
   if (!alive(guest)) break;

   String stamp = configStamp();
   if (!stamp.equals(lastStamp)) {
    lastStamp = stamp;
    SoundConfig next = readConfig();
    if (!next.sameAs(cfg)) {
     applyConfigToChain(primary, singleType, cfg, next, "config changed", true);
     for (int i = 0; i < extraChains.size(); i++) {
      applyConfigToChain(extraChains.get(i), singleType, cfg, next, null, false);
     }
     cfg = next;
     writeState(isActive(primary.dolby, cfg.enable != 0),
         isActive(primary.soundAlive, true),
         isActive(primary.soundBooster, cfg.soundBooster != 0));
    }
   }

   boolean nowMusic = musicActive();
   int curDevice = musicDevice();
   if (atDevice == 0 && curDevice != 0) atDevice = curDevice;
   boolean deviceChanged = curDevice != 0 && atDevice != 0 && curDevice != atDevice;
   if (deviceChanged) {
    verifiedOnPlayback = false;
    if (!nowMusic) atDevice = curDevice;
   }
   boolean liveMove = nowMusic && wasMusic && deviceChanged && curDevice != DEVICE_OUT_EARPIECE;
   boolean primaryHealthy = chainHealthy(primary, singleType, expectDolby, expectSb, expectSa);
   boolean extrasHealthy = allExtrasHealthy(extraChains, singleType, expectDolby, expectSb, expectSa);
   if ((nowMusic && !wasMusic) || liveMove) {
    boolean needRecreate = !primaryHealthy;
    if (!needRecreate && multiOutputSupported && extraChains.size() < 2) {
     // Pick up any speaker MIXER output that opened after initial boot attach.
     multiOutputSupported = attachExtraOutputs(
         ctor, singleType, implNull, cfg, primary, extraChains, expectDolby, expectSb, expectSa);
    }
    if (!needRecreate && !verifiedOnPlayback) {
     // First music start or output device switch (e.g. speaker <-> Bluetooth A2DP):
     // wait briefly for AudioPolicyManager to activate the target output thread,
     // then check whether any of our chains is already on that active thread.
     Thread.sleep(liveMove ? 1500 : 250);
     if (!alive(guest)) break;
     int settledDev = musicDevice();
     if (settledDev != 0) atDevice = settledDev;
     Set<Integer> ids = new HashSet<>();
     primary.collectIds(ids);
     for (int i = 0; i < extraChains.size(); i++) extraChains.get(i).collectIds(ids);
     int checkRes = checkAnyEffectOnActiveThread(ids);
     if (checkRes > 0) {
      verifiedOnPlayback = true;
      log("effects already on active playback thread (chains=" + (1 + extraChains.size()) + "); no recreate needed");
     } else if (checkRes < 0) {
      needRecreate = true;
     }
    }
    if (needRecreate) {
     releaseAllExtras(extraChains);
     primary.releaseAll();

     cfg = readConfig();
     lastStamp = configStamp();
     String why = !primaryHealthy ? "music started (recover)"
         : (liveMove ? ("music moved to output device " + atDevice) : "music started (move to active output)");
     populateChain(ctor, singleType, implNull, primary, cfg, why, expectDolby, expectSb, expectSa, true);
     if (singleType == null && expectDolby && primary.dolby == null) {
      Thread.sleep(800);
      if (alive(guest)) {
       cfg = readConfig();
       populateChain(ctor, null, implNull, primary, cfg, why + " (retry)", expectDolby, expectSb, expectSa, true);
      }
     }
     if (multiOutputSupported && chainHealthy(primary, singleType, expectDolby, expectSb, expectSa)) {
      multiOutputSupported = attachExtraOutputs(
          ctor, singleType, implNull, cfg, primary, extraChains, expectDolby, expectSb, expectSa);
     }
     writeState(isActive(primary.dolby, cfg.enable != 0),
         isActive(primary.soundAlive, true),
         isActive(primary.soundBooster, cfg.soundBooster != 0));
     verifiedOnPlayback = chainHealthy(primary, singleType, expectDolby, expectSb, expectSa);
     int postDev = musicDevice();
     if (postDev != 0) atDevice = postDev;
     moves++;
    } else if (deviceChanged && curDevice != DEVICE_OUT_EARPIECE) {
     int postDev = musicDevice();
     if (postDev != 0) atDevice = postDev;
    }
    recoveryTicks = 0;
   } else if (!primaryHealthy || !extrasHealthy) {
    // Recover cleanly if audioserver restarted or another client took control.
    if (++recoveryTicks >= 5) {
     recoveryTicks = 0;
     if (!primaryHealthy) {
      verifiedOnPlayback = false;
      releaseAllExtras(extraChains);
      primary.releaseAll();
      cfg = readConfig();
      lastStamp = configStamp();
      populateChain(ctor, singleType, implNull, primary, cfg, "recover", expectDolby, expectSb, expectSa, true);
      if (chainHealthy(primary, singleType, expectDolby, expectSb, expectSa)) {
       multiOutputSupported = attachExtraOutputs(
           ctor, singleType, implNull, cfg, primary, extraChains, expectDolby, expectSb, expectSa);
      }
      writeState(isActive(primary.dolby, cfg.enable != 0),
          isActive(primary.soundAlive, true),
          isActive(primary.soundBooster, cfg.soundBooster != 0));
     } else if (multiOutputSupported) {
      // Only an extra output chain went stale (e.g. thread reopened); refresh extra chains without interrupting primary.
      releaseAllExtras(extraChains);
      multiOutputSupported = attachExtraOutputs(
          ctor, singleType, implNull, cfg, primary, extraChains, expectDolby, expectSb, expectSa);
     }
    }
   } else {
    recoveryTicks = 0;
   }
   wasMusic = nowMusic;
  }

  releaseAllExtras(extraChains);
  primary.releaseAll();
  writeState(false, false, false);
  log("guest system_server " + guest + " gone; released (" + moves + " re-attachments)");
 }

 private static void populateChain(Constructor<?> ctor, UUID singleType, UUID implNull,
     Chain ch, SoundConfig cfg, String why, boolean expectDolby, boolean expectSb, boolean expectSa,
     boolean sendHalParams) {
  if (singleType != null) {
   if (ch.dolby == null) ch.dolby = createSingle(ctor, singleType, implNull, ch.ioHandle, cfg, why, sendHalParams);
  } else {
   if (expectDolby && ch.dolby == null) {
    ch.dolby = createDolby(ctor, implNull, ch.ioHandle, cfg, why, sendHalParams);
   }
   if (expectSb && ch.soundBooster == null) {
    ch.soundBooster = createSoundBooster(ctor, implNull, ch.ioHandle, cfg, why);
   }
   if (expectSa && ch.soundAlive == null) {
    ch.soundAlive = createSoundAlive(ctor, implNull, ch.ioHandle, cfg, why);
   }
  }
 }

 private static void applyConfigToChain(Chain ch, UUID singleType, SoundConfig prev, SoundConfig next,
     String why, boolean sendHalParams) {
  if (singleType != null) {
   applySingle(ch.dolby, singleType, next, why, sendHalParams);
  } else {
   if (ch.dolby != null && (next.enable != prev.enable || next.profile != prev.profile)) {
    applyDax(ch.dolby, next, why, sendHalParams);
   }
   if (ch.soundBooster != null && next.soundBooster != prev.soundBooster) {
    applySoundBooster(ch.soundBooster, next, why);
   }
   if (ch.soundAlive != null && !Arrays.equals(next.eqBands, prev.eqBands)) {
    applySoundAlive(ch.soundAlive, next, why);
   }
  }
 }

 /**
  * Probes and attaches session-0 chains to all eligible speaker MIXER outputs other than the
  * output hosting {@code primary}. Returns true if the AudioFlinger io-override hook is active
  * (or no extra outputs were present yet), false if the host AudioFlinger ignored the override.
  */
 private static boolean attachExtraOutputs(Constructor<?> ctor, UUID singleType, UUID implNull,
     SoundConfig cfg, Chain primary, List<Chain> extraChains,
     boolean expectDolby, boolean expectSb, boolean expectSa) {
  int primaryId = primary.anyEffectId();
  if (primaryId < 0) return false;
  AfSnapshot snap = queryAudioFlinger();
  if (snap == null) {
   log("attachExtraOutputs: dumpsys media.audio_flinger returned null");
   return true;
  }
  if (snap.eligibleIos.isEmpty()) return true;

  Integer primaryIoObj = snap.effectToIo.get(primaryId);
  int primaryIo = primaryIoObj != null ? primaryIoObj : -1;

  Set<Integer> attachedIos = new HashSet<>();
  if (primaryIo > 0) attachedIos.add(primaryIo);
  for (int i = 0; i < extraChains.size(); i++) {
   attachedIos.add(extraChains.get(i).ioHandle);
  }

  for (int i = 0; i < snap.eligibleIos.size(); i++) {
   int io = snap.eligibleIos.get(i);
   if (io <= 0 || io > 0xFFFF || attachedIos.contains(io)) continue;

   Chain ch = new Chain(io);
   Object probe = null;
   int probeKind = 0; // 1=dolby, 2=sb, 3=sa, 4=single
   if (singleType != null) {
    probe = createSingle(ctor, singleType, implNull, io, cfg, null, false);
    ch.dolby = probe;
    probeKind = 4;
   } else if (expectDolby) {
    probe = createDolby(ctor, implNull, io, cfg, null, false);
    ch.dolby = probe;
    probeKind = 1;
   } else if (expectSb) {
    probe = createSoundBooster(ctor, implNull, io, cfg, null);
    ch.soundBooster = probe;
    probeKind = 2;
   } else if (expectSa) {
    probe = createSoundAlive(ctor, implNull, io, cfg, null);
    ch.soundAlive = probe;
    probeKind = 3;
   }
   int probeId = effectId(probe);
   if (probe == null || probeId < 0) {
    ch.releaseAll();
    continue;
   }

   AfSnapshot verify = queryAudioFlinger();
   Integer actualIoObj = verify != null ? verify.effectToIo.get(probeId) : null;
   int actualIo = actualIoObj != null ? actualIoObj : -1;
   if (actualIo != io) {
    ch.releaseAll();
    log("multi-output io override inactive (probe io=" + io + " landed on io=" + actualIo + "); single-output mode");
    return false;
   }

   if (probeKind != 4) {
    if (expectSb && ch.soundBooster == null) {
     ch.soundBooster = createSoundBooster(ctor, implNull, io, cfg, null);
    }
    if (expectSa && ch.soundAlive == null) {
     ch.soundAlive = createSoundAlive(ctor, implNull, io, cfg, null);
    }
   }
   extraChains.add(ch);
   attachedIos.add(io);
   log("attached multi-output chain to io=" + io
       + " (dax=" + effectId(ch.dolby)
       + ", sb=" + effectId(ch.soundBooster)
       + ", sa=" + effectId(ch.soundAlive) + ")");
  }
  return true;
 }

 private static Object newEffect(Constructor<?> ctor, UUID type, UUID implUuid, int ioHandle) throws Exception {
  int prio = (ioHandle > 0 && ioHandle <= 0xFFFF) ? (PRIORITY_IO_MAGIC | ioHandle) : 0;
  return ctor.newInstance(type, implUuid, prio, 0);
 }

 private static Object createSingle(Constructor<?> ctor, UUID type, UUID implUuid, int ioHandle,
     SoundConfig cfg, String why, boolean sendHalParams) {
  String ts = type.toString();
  if (DOLBY_TYPE.equals(ts)) return createDolby(ctor, implUuid, ioHandle, cfg, why, sendHalParams);
  if (SOUNDBOOSTER_TYPE.equals(ts)) return createSoundBooster(ctor, implUuid, ioHandle, cfg, why);
  if (SOUNDALIVE_TYPE.equals(ts)) return createSoundAlive(ctor, implUuid, ioHandle, cfg, why);
  try {
   Object fx = newEffect(ctor, type, implUuid, ioHandle);
   applySingle(fx, type, cfg, why, sendHalParams);
   return fx;
  } catch (Throwable t) {
   if (why != null || ioHandle > 0) {
    log("create " + type + " failed (" + failTag(why, ioHandle) + "): " + rootCause(t));
   }
   return null;
  }
 }

 private static void applySingle(Object fx, UUID type, SoundConfig cfg, String why, boolean sendHalParams) {
  if (fx == null) return;
  String ts = type.toString();
  if (DOLBY_TYPE.equals(ts)) applyDax(fx, cfg, why, sendHalParams);
  else if (SOUNDBOOSTER_TYPE.equals(ts)) applySoundBooster(fx, cfg, why);
  else if (SOUNDALIVE_TYPE.equals(ts)) applySoundAlive(fx, cfg, why);
  else {
   int r = invokeSetEnabled(fx, cfg.enable != 0);
   if (why != null) logCreated(fx, why, "setEnabled=" + r);
  }
 }

 private static Object createDolby(Constructor<?> ctor, UUID implUuid, int ioHandle,
     SoundConfig cfg, String why, boolean sendHalParams) {
  try {
   Object fx = newEffect(ctor, UUID.fromString(DOLBY_TYPE), implUuid, ioHandle);
   applyDax(fx, cfg, why, sendHalParams);
   return fx;
  } catch (Throwable t) {
   if (why != null || ioHandle > 0) {
    log("create Dolby (" + DOLBY_TYPE + ") failed (" + failTag(why, ioHandle) + "): " + rootCause(t));
   }
   return null;
  }
 }

 private static Object createSoundAlive(Constructor<?> ctor, UUID implUuid, int ioHandle,
     SoundConfig cfg, String why) {
  try {
   Object fx = newEffect(ctor, UUID.fromString(SOUNDALIVE_TYPE), implUuid, ioHandle);
   applySoundAlive(fx, cfg, why);
   return fx;
  } catch (Throwable t) {
   if (why != null || ioHandle > 0) {
    log("create SoundAlive (" + SOUNDALIVE_TYPE + ") failed (" + failTag(why, ioHandle) + "): " + rootCause(t));
   }
   return null;
  }
 }

 private static Object createSoundBooster(Constructor<?> ctor, UUID implUuid, int ioHandle,
     SoundConfig cfg, String why) {
  try {
   Object fx = newEffect(ctor, UUID.fromString(SOUNDBOOSTER_TYPE), implUuid, ioHandle);
   applySoundBooster(fx, cfg, why);
   return fx;
  } catch (Throwable t) {
   if (why != null || ioHandle > 0) {
    log("create SoundBoosterPlus (" + SOUNDBOOSTER_TYPE + ") failed (" + failTag(why, ioHandle) + "): " + rootCause(t));
   }
   return null;
  }
 }

 private static String failTag(String why, int ioHandle) {
  return why != null ? why : ("io=" + ioHandle);
 }

 private static void applyDax(Object fx, SoundConfig cfg, String why, boolean sendHalParams) {
  try {
   int en = cfg.enable != 0 ? 1 : 0;
   int prof = en != 0 ? cfg.profile : 5;

   // Send Samsung DAX3_S native DlbEffectContext::setParam IDs (4-byte LE int32).
   // Leave volume leveler at dax-default.xml tuning (dvla=0), matching One UI's -1 KVP.
   int rEn = setInt32Param(fx, DAX_PARAM_ENABLE, en);
   int rCp = setInt32Param(fx, DAX_PARAM_CONTENT_PROC_ENABLE, en);
   int rPr = setInt32Param(fx, DAX_PARAM_PROFILE, prof);

   String modeNote;
   if (rEn >= 0) {
    modeNote = "dax3s en=" + en + "(" + rEn + ") prof=" + prof + "(" + rPr + ") cp=" + en + "(" + rCp + ")";
   } else {
    // Fallback only if vendor HAL uses non-Samsung DAX3.6 CPDP arrays.
    int reCpdp = setCpdpIntParam(fx, LEGACY_CPDP_ENABLE, en);
    int rpCpdp = setCpdpIntParam(fx, LEGACY_CPDP_PROFILE, prof);
    modeNote = "cpdp fallback en=" + en + "(" + reCpdp + ") prof=" + prof + "(" + rpCpdp + ")";
   }

   if (sendHalParams) setDolbyAudioParams(en, prof, -1);
   int r = invokeSetEnabled(fx, en != 0);
   if (why != null) logCreated(fx, why, modeNote + "; setEnabled(" + (en != 0) + ")=" + r);
  } catch (Throwable t) {
   if (why != null) log("applyDax failed (" + why + "): " + rootCause(t));
  }
 }

 private static void applySoundAlive(Object fx, SoundConfig cfg, String why) {
  try {
   byte[] props = new byte[22];
   putInt16LE(-1, props, 0);          // curPreset = -1 (custom 9-band)
   putInt16LE(SA_NUM_BANDS, props, 2); // numBands = 9
   for (int i = 0; i < SA_NUM_BANDS; i++) {
    putInt16LE(clamp(cfg.eqBands[i], -12, 12), props, 4 + i * 2);
   }

   int rProp = invokeSetParam(sSetParamBytes, fx, SA_PARAM_PROPERTIES, props);
   String eqDetail = "sa props(" + SA_NUM_BANDS + ")=" + rProp;
   if (rProp < 0 && sSetParamByteParam != null) {
    int ok = 0;
    for (int i = 0; i < SA_NUM_BANDS; i++) {
     byte[] p = new byte[8];
     byte[] v = new byte[2];
     putInt32LE(SA_PARAM_BAND_LEVEL, p, 0);
     putInt32LE(i, p, 4);
     putInt16LE(clamp(cfg.eqBands[i], -12, 12), v, 0);
     if (invokeSetParam(sSetParamByteParam, fx, p, v) >= 0) ok++;
    }
    eqDetail += " fallback bands=" + ok + "/" + SA_NUM_BANDS;
   }
   int r = invokeSetEnabled(fx, true);
   if (why != null) logCreated(fx, why, eqDetail + "; setEnabled(true)=" + r);
  } catch (Throwable t) {
   if (why != null) log("applySoundAlive failed (" + why + "): " + rootCause(t));
  }
 }

 private static void applySoundBooster(Object fx, SoundConfig cfg, String why) {
  try {
   boolean on = cfg.soundBooster != 0;
   int r = invokeSetEnabled(fx, on);
   if (why != null) logCreated(fx, why, "setEnabled(" + on + ")=" + r);
  } catch (Throwable t) {
   if (why != null) log("applySoundBooster failed (" + why + "): " + rootCause(t));
  }
 }

 private static void logCreated(Object fx, String why, String extra) {
  try {
   Object d = sGetDescriptor != null ? sGetDescriptor.invoke(fx) : null;
   Object en = sGetEnabled != null ? sGetEnabled.invoke(fx) : "?";
   Object ctrl = sHasControl != null ? sHasControl.invoke(fx) : "?";
   log("created " + field(d, "name") + " " + field(d, "uuid") + " (" + field(d, "implementor")
       + ") on the output mix (" + why + "); " + extra + ", enabled=" + en + ", hasControl=" + ctrl);
  } catch (Throwable t) {
   log("created effect (" + why + "): " + extra + " (inspect failed: " + rootCause(t) + ")");
  }
 }

 private static int setInt32Param(Object fx, int param, int value) {
  byte[] buf = new byte[4];
  putInt32LE(value, buf, 0);
  return invokeSetParam(sSetParamBytes, fx, param, buf);
 }

 private static int setCpdpIntParam(Object fx, int param, int value) {
  byte[] buf = new byte[12];
  putInt32LE(param, buf, 0);
  putInt32LE(1, buf, 4);
  putInt32LE(value, buf, 8);
  return invokeSetParam(sSetParamBytes, fx, LEGACY_PARAM_CPDP_VALUES, buf);
 }

 private static int invokeSetParam(Method m, Object fx, Object p, Object v) {
  if (m == null || fx == null) return -998;
  try {
   return (Integer) m.invoke(fx, p, v);
  } catch (Throwable t) {
   return -999;
  }
 }

 private static int invokeSetEnabled(Object fx, boolean enable) {
  if (sSetEnabled == null || fx == null) return -998;
  try {
   return (Integer) sSetEnabled.invoke(fx, enable);
  } catch (Throwable t) {
   return -999;
  }
 }

 private static boolean isActive(Object fx, boolean expectedEnabled) {
  if (fx == null) return false;
  if (!expectedEnabled) return false;
  try {
   return Boolean.TRUE.equals(sGetEnabled.invoke(fx));
  } catch (Throwable ignored) {
   return true;
  }
 }

 private static File activeConfigFile() {
  File p = new File(PRIMARY_CONFIG_PATH);
  if (p.isFile()) return p;
  File l = new File(LEGACY_CONFIG_PATH);
  return l.isFile() ? l : null;
 }

 private static String configStamp() {
  File p = new File(PRIMARY_CONFIG_PATH);
  File l = new File(LEGACY_CONFIG_PATH);
  return (p.isFile() ? ("P:" + p.lastModified() + ":" + p.length()) : "P:-")
      + "|" + (l.isFile() ? ("L:" + l.lastModified() + ":" + l.length()) : "L:-");
 }

 private static SoundConfig readConfig() {
  SoundConfig cfg = new SoundConfig();
  File f = activeConfigFile();
  if (f == null) return cfg;
  try (BufferedReader br = new BufferedReader(new FileReader(f))) {
   String line;
   while ((line = br.readLine()) != null) {
    line = line.trim();
    if (line.isEmpty() || line.startsWith("#")) continue;
    int eq = line.indexOf('=');
    if (eq <= 0) continue;
    String k = line.substring(0, eq).trim();
    String v = line.substring(eq + 1).trim();
    if ("enable".equals(k) || "dolby_enable".equals(k)) {
     if ("0".equals(v) || "false".equalsIgnoreCase(v)) cfg.enable = 0;
     else if ("1".equals(v) || "true".equalsIgnoreCase(v)) cfg.enable = 1;
    } else if ("profile".equals(k) || "dolby_profile".equals(k)) {
     try {
      int p = Integer.parseInt(v);
      if (p >= 0 && p <= 5) cfg.profile = p;
     } catch (NumberFormatException ignored) { }
    } else if ("soundbooster".equals(k) || "soundbooster_enable".equals(k)) {
     if ("0".equals(v) || "false".equalsIgnoreCase(v)) cfg.soundBooster = 0;
     else if ("1".equals(v) || "true".equalsIgnoreCase(v)) cfg.soundBooster = 1;
    } else if ("eq_bands".equals(k)) {
     String[] parts = v.split(",");
     for (int i = 0; i < SA_NUM_BANDS && i < parts.length; i++) {
      try {
       cfg.eqBands[i] = clamp(Integer.parseInt(parts[i].trim()), -12, 12);
      } catch (NumberFormatException ignored) { }
     }
    }
   }
  } catch (Throwable ignored) { }
  return cfg;
 }

 private static String sLastState = "";

 private static void writeState(boolean dolbyOn, boolean soundAliveOn, boolean soundBoosterOn) {
  String text = "dolby=" + (dolbyOn ? 1 : 0)
      + "\nsoundalive=" + (soundAliveOn ? 1 : 0)
      + "\nsoundbooster=" + (soundBoosterOn ? 1 : 0) + "\n";
  if (text.equals(sLastState)) return;
  File out = new File(STATE_PATH);
  File dir = out.getParentFile();
  if (dir == null || !dir.isDirectory()) return;
  File tmp = new File(dir, "sound_state.tmp");
  try {
   try (FileOutputStream fos = new FileOutputStream(tmp)) {
    fos.write(text.getBytes(StandardCharsets.US_ASCII));
    fos.getFD().sync();
   }
   tmp.setReadable(true, false);
   if (tmp.renameTo(out)) {
    out.setReadable(true, false);
    sLastState = text;
   } else {
    tmp.delete();
   }
  } catch (Throwable ignored) {
   tmp.delete();
  }
 }

 private static void setDolbyAudioParams(int enable, int profile, int leveler) {
  try {
   Class<?> s = Class.forName("android.media.AudioSystem");
   s.getMethod("setParameters", String.class).invoke(null,
       "g_effect_dolby_enable=" + enable
       + ";g_effect_dolby_profile=" + profile
       + ";g_effect_dolby_volume_leveler=" + leveler);
  } catch (Throwable ignored) { }
 }

 private static Method findMethod(Class<?> c, String name, Class<?>... params) {
  try { return c.getMethod(name, params); } catch (Throwable ignored) { }
  try {
   Method m = c.getDeclaredMethod(name, params);
   m.setAccessible(true);
   return m;
  } catch (Throwable t) {
   log("AudioEffect." + name + " not found: " + t);
   return null;
  }
 }

 private static void putInt32LE(int v, byte[] dst, int off) {
  dst[off] = (byte) (v & 0xff);
  dst[off + 1] = (byte) ((v >>> 8) & 0xff);
  dst[off + 2] = (byte) ((v >>> 16) & 0xff);
  dst[off + 3] = (byte) ((v >>> 24) & 0xff);
 }

 private static void putInt16LE(int v, byte[] dst, int off) {
  dst[off] = (byte) (v & 0xff);
  dst[off + 1] = (byte) ((v >>> 8) & 0xff);
 }

 private static int clamp(int v, int lo, int hi) {
  return Math.max(lo, Math.min(hi, v));
 }

 private static void releaseOne(Object fx) {
  if (fx == null || sRelease == null) return;
  try { sRelease.invoke(fx); } catch (Throwable ignored) { }
 }

 private static void releaseAllExtras(List<Chain> extraChains) {
  for (int i = 0; i < extraChains.size(); i++) {
   extraChains.get(i).releaseAll();
  }
  extraChains.clear();
 }

 private static int effectId(Object fx) {
  if (fx == null || sGetId == null) return -1;
  try {
   return (Integer) sGetId.invoke(fx);
  } catch (Throwable ignored) {
   return -1;
  }
 }

 private static boolean effectHealthy(Object fx) {
  if (fx == null) return false;
  if (sHasControl == null) return true;
  try {
   return Boolean.TRUE.equals(sHasControl.invoke(fx));
  } catch (Throwable ignored) {
   return false;
  }
 }

 private static boolean chainHealthy(Chain ch, UUID singleType,
     boolean expectDolby, boolean expectSb, boolean expectSa) {
  if (singleType != null) return effectHealthy(ch.dolby);
  if (!expectDolby && !expectSb && !expectSa) return false;
  if (expectDolby && !effectHealthy(ch.dolby)) return false;
  if (expectSb && !effectHealthy(ch.soundBooster)) return false;
  if (expectSa && !effectHealthy(ch.soundAlive)) return false;
  return true;
 }

 private static boolean allExtrasHealthy(List<Chain> extraChains, UUID singleType,
     boolean expectDolby, boolean expectSb, boolean expectSa) {
  for (int i = 0; i < extraChains.size(); i++) {
   if (!chainHealthy(extraChains.get(i), singleType, expectDolby, expectSb, expectSa)) return false;
  }
  return true;
 }

 /**
  * Parses {@code dumpsys media.audio_flinger} live Output threads:
  * discovers eligible speaker MIXER I/O handles (PRIMARY / FAST / DEEP_BUFFER),
  * maps every attached Effect ID to its thread's I/O handle, and records active outputs.
  */
 private static AfSnapshot queryAudioFlinger() {
  AfSnapshot snap = new AfSnapshot();
  Process p = null;
  BufferedReader br = null;
  boolean inOutput = false;
  boolean isMixer = false;
  int curIo = -1;
  try {
   p = new ProcessBuilder("/system/bin/dumpsys", "media.audio_flinger")
       .redirectErrorStream(true)
       .start();
   br = new BufferedReader(new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8));
   String line;
   while ((line = br.readLine()) != null) {
    String tr = line.trim();
    if (tr.startsWith("Historical Thread") || tr.startsWith("## BEGIN setParameters")
        || tr.startsWith("## BEGIN misc af")) {
     break;
    }
    if (tr.startsWith("Output thread ")) {
     inOutput = true;
     isMixer = tr.contains("type 0 (MIXER)");
     curIo = -1;
    } else if (tr.startsWith("Input thread ") || tr.startsWith("- Input thread ")
        || tr.startsWith("Global session")) {
     inOutput = false;
     isMixer = false;
     curIo = -1;
    } else if (inOutput && tr.startsWith("I/O handle:")) {
     curIo = parseFirstInt(tr.substring("I/O handle:".length()));
    } else if (inOutput && "Standby: no".equals(tr) && curIo > 0) {
     snap.activeIos.add(curIo);
    } else if (inOutput && isMixer && curIo > 0 && tr.startsWith("AudioStreamOut:")) {
     int fi = tr.indexOf("flags ");
     if (fi >= 0) {
      int flags = parseIntAuto(tr.substring(fi + 6));
      if ((flags & ELIGIBLE_INCLUDE_MASK) != 0 && (flags & ELIGIBLE_EXCLUDE_MASK) == 0) {
       if (!snap.eligibleIos.contains(curIo)) snap.eligibleIos.add(curIo);
      }
     }
    } else if (inOutput && curIo > 0 && tr.startsWith("Effect ID ") && tr.endsWith(":")) {
     int eid = parseFirstInt(tr.substring("Effect ID ".length(), tr.length() - 1));
     if (eid >= 0) snap.effectToIo.put(eid, curIo);
    }
   }
   return snap;
  } catch (Throwable ignored) {
   return null;
  } finally {
   if (br != null) {
    try { br.close(); } catch (Throwable ignored) { }
   }
   if (p != null) {
    try { p.destroy(); } catch (Throwable ignored) { }
   }
  }
 }

 /**
  * Returns 1 if any effect in {@code ids} is attached to an active (non-standby) Output thread
  * (or if dumpsys cannot be queried), -1 if an active Output thread exists without any of them,
  * or 0 if no Output thread is currently active.
  */
 private static int checkAnyEffectOnActiveThread(Set<Integer> ids) {
  if (ids.isEmpty()) return -1;
  AfSnapshot snap = queryAudioFlinger();
  if (snap == null) return 1;
  if (snap.activeIos.isEmpty()) return 0;
  for (Integer eid : ids) {
   Integer io = snap.effectToIo.get(eid);
   if (io != null && snap.activeIos.contains(io)) return 1;
  }
  return -1;
 }

 private static int parseFirstInt(String s) {
  if (s == null) return -1;
  int i = 0, n = s.length();
  while (i < n && !Character.isDigit(s.charAt(i))) i++;
  if (i >= n) return -1;
  int j = i;
  while (j < n && Character.isDigit(s.charAt(j))) j++;
  try {
   return Integer.parseInt(s.substring(i, j));
  } catch (NumberFormatException e) {
   return -1;
  }
 }

 private static int parseIntAuto(String s) {
  if (s == null) return 0;
  String t = s.trim();
  int end = 0;
  while (end < t.length() && !Character.isWhitespace(t.charAt(end)) && t.charAt(end) != '(') end++;
  t = t.substring(0, end);
  try {
   if (t.startsWith("0x") || t.startsWith("0X")) return (int) Long.parseLong(t.substring(2), 16);
   return Integer.parseInt(t);
  } catch (NumberFormatException e) {
   return 0;
  }
 }

 /** STREAM_MUSIC (3) active now (AudioSystem.isStreamActive, hidden); false when it cannot be asked. */
 private static boolean musicActive() {
  try {
   Class<?> s = Class.forName("android.media.AudioSystem");
   return (Boolean) s.getMethod("isStreamActive", int.class, int.class).invoke(null, 3, 0);
  } catch (Throwable t) {
   return false;
  }
 }

 /** Output device bit mask for STREAM_MUSIC (3) via AudioSystem.getDevicesForStream; 0 on failure. */
 private static int musicDevice() {
  try {
   Class<?> s = Class.forName("android.media.AudioSystem");
   return (Integer) s.getMethod("getDevicesForStream", int.class).invoke(null, 3);
  } catch (Throwable t) {
   return 0;
  }
 }

 private static boolean alive(int pid) { return new File("/proc/" + pid).exists(); }

 private static Throwable rootCause(Throwable t) { return t.getCause() != null ? t.getCause() : t; }

 private static Object field(Object o, String n) {
  if (o == null) return "?";
  try { return o.getClass().getField(n).get(o); } catch (Throwable t) { return "?"; }
 }

 private static void log(String s) {
  System.out.println(SystemClock.elapsedRealtime() + " " + s);
  System.out.flush();
 }
}
