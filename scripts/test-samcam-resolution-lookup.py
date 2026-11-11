#!/usr/bin/env python3
"""The Samsung Camera size-lookup patcher (samsung-camera/fix_a_series_resolution_lookup.py) and its
helper (samsung-camera/helpers/src/oneos/camera/OneOSResolution.java).

The patcher runs on a made-up decoded tree whose size table has the camera's shape; the helper's
choices run on this machine's Java when it has one.
"""
from pathlib import Path
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
CAM = ROOT / 'scripts/samsung-camera'
FIX = CAM / 'fix_a_series_resolution_lookup.py'
JAVA = CAM / 'helpers/src/oneos/camera/OneOSResolution.java'
SMALI = CAM / 'helpers/smali/OneOSResolution.smali'
MARKER = '@oneos-callers-that-catch@'
MSG = '"getResolution : argument is invalid - "'
APPLY = 'Ljava/util/function/BiFunction;->apply(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;'
T = 'Lt/Sizes;'
NAMES = (['RESOLUTION_3264X2448', 'RESOLUTION_4000X3000', 'RESOLUTION_4000X2252', 'RESOLUTION_8160X6120',
          'RESOLUTION_1920X1080', 'RESOLUTION_1920X1080_60FPS', 'RESOLUTION_3840X2160_120FPS', 'RESOLUTION_12000X9000']
         + ['RESOLUTION_%dX%d' % (1000 + 16 * i, 750 + 12 * i) for i in range(14)])

BY_ID = f'''.method public static find(I){T}
    .locals 2

    .line 1
    sget-object v0, {T}->mIdMap:Ljava/util/Map;

    .line 2
    .line 3
    invoke-static {{p0}}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;

    move-result-object v1

    invoke-interface {{v0, v1}}, Ljava/util/Map;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v0

    check-cast v0, {T}

    if-eqz v0, :cond_0

    return-object v0

    .line 16
    :cond_0
    new-instance v0, Ljava/lang/IllegalArgumentException;

    .line 17
    .line 18
    const-string v1, {MSG}

    invoke-static {{p0, v1}}, Lq/a;->k(ILjava/lang/String;)Ljava/lang/String;

    move-result-object p0

    invoke-direct {{v0, p0}}, Ljava/lang/IllegalArgumentException;-><init>(Ljava/lang/String;)V

    throw v0
.end method
'''
# The exception in v3 and its message in v4: the registers come from the throw, not from this script.
BY_TEXT = f'''.method public static named(Ljava/lang/String;){T}
    .locals 5

    invoke-static {{}}, {T}->values()[{T}

    move-result-object v0

    array-length v1, v0

    const/4 v2, 0x0

    :goto_0
    if-ge v2, v1, :cond_1

    aget-object v3, v0, v2

    invoke-virtual {{v3}}, {T}->text()Ljava/lang/String;

    move-result-object v4

    invoke-virtual {{v4, p0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v4

    if-eqz v4, :cond_0

    return-object v3

    :cond_0
    add-int/lit8 v2, v2, 0x1

    goto :goto_0

    .line 25
    :cond_1
    new-instance v3, Ljava/lang/IllegalArgumentException;

    const-string v4, {MSG}

    invoke-static {{v4, p0}}, Lq/b;->C(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object p0

    invoke-direct {{v3, p0}}, Ljava/lang/IllegalArgumentException;-><init>(Ljava/lang/String;)V

    throw v3
.end method
'''


def table(names=NAMES, by_id=BY_ID, by_text=BY_TEXT):
    fields = ''.join(f'.field public static final enum {n}:{T}\n\n' for n in names)
    init = ''.join(f'    new-instance v0, {T}\n\n    const-string v1, "{n}"\n\n    const/4 v2, 0x0\n\n'
                   f'    invoke-direct {{v0, v1, v2}}, {T}-><init>(Ljava/lang/String;I)V\n\n'
                   f'    sput-object v0, {T}->{n}:{T}\n\n' for n in names)
    return f'''.class public final enum {T}
.super Ljava/lang/Enum;
.source "x"


# static fields
.field private static final synthetic $VALUES:[{T}

{fields}.field private static final mIdMap:Ljava/util/Map;


# direct methods
.method static constructor <clinit>()V
    .locals 3

{init}    return-void
.end method

{by_id}
{by_text}
.method public static values()[{T}
    .locals 1

    sget-object v0, {T}->$VALUES:[{T}

    invoke-virtual {{v0}}, [{T}->clone()Ljava/lang/Object;

    move-result-object v0

    check-cast v0, [{T}

    return-object v0
.end method
'''


def cls(name, *methods):
    return f'.class public final L{name};\n.super Ljava/lang/Object;\n.source "x"\n\n\n# direct methods\n' + '\n'.join(methods)


ID_CALL = f'invoke-static {{p0}}, {T}->find(I){T}'
TEXT_CALL = f'invoke-static {{p0}}, {T}->named(Ljava/lang/String;){T}'
USES = cls('t/Uses', f'''.method public static plain(I){T}
    .locals 1

    {ID_CALL}

    move-result-object v0

    return-object v0
.end method
''', f'''.method public static fn(Ljava/util/function/BiFunction;)Ljava/lang/Object;
    .locals 1

    const/4 v0, 0x0

    invoke-interface {{p0, v0, v0}}, {APPLY}

    move-result-object v0

    return-object v0
.end method
''')
# Asks whether an id exists: the exception is its answer.
PROBE = cls('t/Probe', f'''.method public static ask(I){T}
    .locals 1

    :try_start_0
    {ID_CALL}

    move-result-object v0
    :try_end_0
    .catch Ljava/lang/IllegalArgumentException; {{:try_start_0 .. :try_end_0}} :catch_0

    return-object v0

    :catch_0
    const/4 v0, 0x0

    return-object v0
.end method
''', f'''.method public static other(I){T}
    .locals 1

    {ID_CALL}

    move-result-object v0

    return-object v0
.end method
''', f'''.method public static after(I){T}
    .locals 1

    :try_start_0
    invoke-static {{}}, Lq/a;->work()V
    :try_end_0
    .catch Ljava/lang/IllegalArgumentException; {{:try_start_0 .. :try_end_0}} :catch_0

    :catch_0
    {ID_CALL}

    move-result-object v0

    return-object v0
.end method
''')
# A synchronized block: its handler releases the lock and throws on.
LOCKED = cls('u/Locked', f'''.method public static list(Ljava/lang/String;){T}
    .locals 2

    sget-object v0, Lu/Locked;->lock:Ljava/lang/Object;

    monitor-enter v0

    :try_start_0
    {TEXT_CALL}

    move-result-object p0

    monitor-exit v0

    return-object p0

    :catchall_0
    move-exception v1

    goto :goto_0

    :goto_0
    monitor-exit v0
    :try_end_0
    .catchall {{:try_start_0 .. :try_end_0}} :catchall_0

    throw v1
.end method
''')
SWALLOW = cls('u/Swallow', f'''.method public static any(Ljava/lang/String;){T}
    .locals 1

    :try_start_0
    {TEXT_CALL}

    move-result-object p0
    :try_end_0
    .catchall {{:try_start_0 .. :try_end_0}} :catchall_0

    return-object p0

    :catchall_0
    move-exception v0

    const/4 p0, 0x0

    return-object p0
.end method
''')
IO = cls('u/Io', f'''.method public static read(I){T}
    .locals 1

    :try_start_0
    {ID_CALL}

    move-result-object v0
    :try_end_0
    .catch Ljava/io/IOException; {{:try_start_0 .. :try_end_0}} :catch_0

    return-object v0

    :catch_0
    const/4 v0, 0x0

    return-object v0
.end method
''', f'''.method public constructor <init>(I)V
    .locals 1

    invoke-direct {{p0}}, Ljava/lang/Object;-><init>()V

    :try_start_0
    invoke-static {{p1}}, {T}->find(I){T}
    :try_end_0
    .catch Ljava/lang/Exception; {{:try_start_0 .. :try_end_0}} :catch_0

    :catch_0
    return-void
.end method
''')
CATCHERS = 't.Probe.ask u.Io.<init> u.Swallow.any'
FILES = {'smali/q/a.smali': cls('q/a'), 'smali_classes2/t/Sizes.smali': table(), 'smali_classes2/t/Uses.smali': USES,
         'smali_classes2/t/Probe.smali': PROBE, 'smali_classes3/u/Locked.smali': LOCKED,
         'smali_classes3/u/Swallow.smali': SWALLOW, 'smali_classes3/u/Io.smali': IO}


def code(text, start, end):
    """The instructions from the line `start` to the line `end`, without blank, comment and .line lines."""
    lines = [x.strip() for x in text.split('\n')]
    a = lines.index(start)
    b = lines.index(end, a)
    return [x for x in lines[a:b + 1] if x and not x.startswith('#') and not x.startswith('.line')]


class Patcher(unittest.TestCase):
    def tree(self, files=None, **changed):
        t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t)
        for name, text in dict(FILES if files is None else files, **changed).items():
            if text is not None:
                (t / name).parent.mkdir(parents=True, exist_ok=True)
                (t / name).write_text(text)
        return t

    def state(self, t):
        return {str(p.relative_to(t)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(t.rglob('*')) if p.is_file()}

    def fix(self, t, script=FIX):
        return subprocess.run([sys.executable, '-I', str(script), str(t)], capture_output=True, text=True, timeout=120)

    def refused(self, why, files=None, **changed):
        t = self.tree(files, **changed)
        before = self.state(t)
        out = self.fix(t)
        self.assertNotEqual(0, out.returncode, out.stderr)
        self.assertIn(why, out.stderr)
        self.assertEqual('', out.stdout)
        self.assertEqual(before, self.state(t), 'a refused tree was written to')

    def test_both_lookups_ask_the_helper_before_their_throw(self):
        t = self.tree()
        before = self.state(t)
        out = self.fix(t)
        self.assertEqual((0, ['smali_classes2', 'smali_classes4']), (out.returncode, out.stdout.split()), out.stderr)
        self.assertIn('by id (find) and by text (named) in smali_classes2/t/Sizes.smali ask OneOSResolution (smali_classes4)', out.stderr)
        self.assertIn(f'22 entries; 3 callers catch a miss themselves and keep it: {CATCHERS}\n', out.stderr)
        got = (t / 'smali_classes2/t/Sizes.smali').read_text()
        self.assertEqual([
            ':cond_0',
            'invoke-static {p0}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;', 'move-result-object v0',
            f'invoke-static {{}}, {T}->values()[{T}', 'move-result-object v1',
            'sget-object v2, Loneos/camera/OneOSResolution;->LOOKUP:Ljava/util/function/BiFunction;',
            'invoke-interface {v2, v0, v1}, ' + APPLY, 'move-result-object v0',
            f'instance-of v1, v0, {T}', 'if-eqz v1, :oneos_resolution_lookup_id', f'check-cast v0, {T}', 'return-object v0',
            ':oneos_resolution_lookup_id',
            'new-instance v0, Ljava/lang/IllegalArgumentException;', 'const-string v1, ' + MSG,
            'invoke-static {p0, v1}, Lq/a;->k(ILjava/lang/String;)Ljava/lang/String;', 'move-result-object p0',
            'invoke-direct {v0, p0}, Ljava/lang/IllegalArgumentException;-><init>(Ljava/lang/String;)V', 'throw v0',
        ], code(got, ':cond_0', 'throw v0'))
        self.assertEqual([
            ':cond_1',
            f'invoke-static {{}}, {T}->values()[{T}', 'move-result-object v4',
            'sget-object v5, Loneos/camera/OneOSResolution;->LOOKUP:Ljava/util/function/BiFunction;',
            'invoke-interface {v5, p0, v4}, ' + APPLY, 'move-result-object v3',
            f'instance-of v4, v3, {T}', 'if-eqz v4, :oneos_resolution_lookup_text', f'check-cast v3, {T}', 'return-object v3',
            ':oneos_resolution_lookup_text',
            'new-instance v3, Ljava/lang/IllegalArgumentException;', 'const-string v4, ' + MSG,
            'invoke-static {v4, p0}, Lq/b;->C(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;', 'move-result-object p0',
            'invoke-direct {v3, p0}, Ljava/lang/IllegalArgumentException;-><init>(Ljava/lang/String;)V', 'throw v3',
        ], code(got, ':cond_1', 'throw v3'))
        # One more local register each, nothing else in the class.
        self.assertEqual(['.locals 3', '.locals 3', '.locals 6', '.locals 1'], re.findall(r'\.locals \d+', got))
        plain = '\n'.join(x for x in got.split('\n') if x.strip())
        for was in (BY_ID, BY_TEXT):
            head, tail = was.split('    new-instance v', 1)
            tail = '\n'.join(x for x in ('    new-instance v' + tail).split('\n') if x.strip())
            self.assertIn(tail, plain)
        self.assertEqual(table().count('\n') + 25 + 21, got.count('\n'))
        # The helper in a dex file of its own, with the callers that keep the throw.
        helper = (t / 'smali_classes4/oneos/camera/OneOSResolution.smali').read_text()
        self.assertEqual(SMALI.read_text().replace(MARKER, CATCHERS), helper)
        self.assertIn(f'const-string v0, " {CATCHERS} "', helper)
        after = self.state(t)
        self.assertEqual({'smali_classes2/t/Sizes.smali', 'smali_classes4/oneos/camera/OneOSResolution.smali'},
                         {k for k in after if after[k] != before.get(k)})
        # A second run changes nothing.
        out = self.fix(t)
        self.assertNotEqual(0, out.returncode)
        self.assertIn('already patched', out.stderr)
        self.assertEqual(after, self.state(t))

    def test_the_helper_goes_where_an_earlier_one_is(self):
        t = self.tree(**{'smali_classes3/oneos/camera/OneOSResolution.smali': '# an earlier build\n'})
        out = self.fix(t)
        self.assertEqual((0, ['smali_classes2', 'smali_classes3']), (out.returncode, out.stdout.split()), out.stderr)
        self.assertIn(f'" {CATCHERS} "', (t / 'smali_classes3/oneos/camera/OneOSResolution.smali').read_text())
        self.assertFalse((t / 'smali_classes4').exists())

    def test_no_caller_that_catches(self):
        t = self.tree(**{'smali_classes2/t/Probe.smali': None, 'smali_classes3/u/Swallow.smali': None, 'smali_classes3/u/Io.smali': None})
        out = self.fix(t)
        self.assertEqual(0, out.returncode, out.stderr)
        self.assertIn('0 callers catch a miss themselves and keep it: -\n', out.stderr)
        self.assertIn('const-string v0, "  "', (t / 'smali_classes4/oneos/camera/OneOSResolution.smali').read_text())

    def test_a_dex_file_that_would_need_a_new_method_reference(self):
        # classes2.dex of the camera has 65535 of 65536: the call must be one the dex file already makes.
        self.refused('smali_classes2 does not call BiFunction.apply yet',
                     **{'smali_classes2/t/Uses.smali': None, 'smali_classes3/t/Uses.smali': USES})
        self.refused('by id: the method does not box its id',
                     **{'smali_classes2/t/Sizes.smali': table(by_id=BY_ID.replace(
                         '    invoke-static {p0}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;\n\n    move-result-object v1\n\n', ''))})

    def test_a_table_of_another_shape_is_left_alone(self):
        sizes = 'smali_classes2/t/Sizes.smali'
        throw = BY_TEXT.split('    .line 25\n', 1)[1].split('.end method', 1)[0]
        for why, text in (
                ('found in 0 classes', table().replace('argument is invalid', 'argument is wrong')),
                ('is not an enum', table().replace(' enum Lt/Sizes;\n.super', ' Lt/Sizes;\n.super', 1)),
                ('has no values()', table().replace('.method public static values()', '.method public static all()')),
                ('are not named RESOLUTION_<W>X<H> (22 entries, 8 read as sizes)',
                 table(names=NAMES[:8] + ['MODE_%d' % i for i in range(14)])),
                ('are not named RESOLUTION_<W>X<H> (19 entries', table(names=NAMES[:19])),
                ('are not named RESOLUTION_<W>X<H> (21 entries', table(names=[n for n in NAMES if n != 'RESOLUTION_4000X3000'])),
                ('0 by id, 1 by text', table(by_id=BY_ID.replace(MSG, '"no such id "'))),
                ('1 by id, 0 by text', table(by_text=BY_TEXT.replace('named(Ljava/lang/String;)', 'named(Ljava/lang/Object;)'))),
                ('by text: the throw with the message found 2 times', table(by_text=BY_TEXT.replace('.end method', throw + '.end method'))),
                ('by id: one register for the exception and its message', table(by_id=BY_ID.replace('const-string v1, ' + MSG, 'const-string v0, ' + MSG))),
                ('by id: the argument is overwritten before the throw', table(by_id=BY_ID.replace('    check-cast v0', '    const/4 p0, 0x0\n\n    check-cast v0'))),
                ('by text: no label right before the throw', table(by_text=BY_TEXT.replace('    :cond_1\n    new-instance', '    :cond_1\n    nop\n\n    new-instance'))),
                ('by text: no usable .locals', table(by_text=BY_TEXT.replace('.locals 5', '.locals 13'))),
                ('by id: no usable .locals', table(by_id=BY_ID.replace('.locals 2', '.locals 1')))):
            with self.subTest(why):
                self.refused(why, **{sizes: text})
        self.refused('found in 2 classes', **{'smali_classes3/u/Twin.smali': cls('u/Twin', f'.method public static x()V\n    const-string v0, {MSG}\n.end method\n')})
        self.refused('a catch line this does not read',
                     **{'smali_classes3/u/Swallow.smali': SWALLOW.replace('.catchall {:try_start_0 .. :try_end_0} :catchall_0', '.catchall {:try_start_0 ..}')})
        out = subprocess.run([sys.executable, '-I', str(FIX), str(self.tree() / 'none')], capture_output=True, text=True)
        self.assertEqual((1, ''), (out.returncode, out.stdout))

    def test_a_helper_without_the_place_for_the_callers(self):
        here = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, here)
        (here / 'helpers/smali').mkdir(parents=True)
        shutil.copy(FIX, here / FIX.name)
        (here / 'helpers/smali/OneOSResolution.smali').write_text(SMALI.read_text().replace(MARKER, ''))
        t = self.tree()
        before = self.state(t)
        out = self.fix(t, here / FIX.name)
        self.assertNotEqual(0, out.returncode)
        self.assertIn('has no place for the callers that catch', out.stderr)
        self.assertEqual(before, self.state(t))


class HelperSmali(unittest.TestCase):
    def test_it_is_what_the_patcher_and_the_camera_need(self):
        text = SMALI.read_text()
        self.assertIn('.class public final Loneos/camera/OneOSResolution;', text)
        self.assertIn('.implements Ljava/util/function/BiFunction;', text)
        self.assertIn('.field public static final LOOKUP:Ljava/util/function/BiFunction;', text)
        self.assertIn('.method public apply(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;', text)
        self.assertEqual((1, 1), (text.count(MARKER), text.count(f'const-string v0, " {MARKER} "')))
        # No Android class (it runs on the build server too) and nothing a dex file of min-api 30 cannot hold.
        self.assertEqual([], re.findall(r'invoke-custom|Landroid/|Lj\$/', text))

    def test_it_was_built_from_the_source(self):
        # helpers/build.sh after a change of the source: every text of the source is in the smali.
        source = '\n'.join(x for x in JAVA.read_text().split('\n') if not x.strip().startswith(('*', '/*', '//')))
        texts = set(re.findall(r'"((?:[^"\\]|\\.)*)"', source))
        self.assertGreater(len(texts), 8)
        smali = SMALI.read_text()
        for text in sorted(texts):
            if text:
                self.assertIn('"%s"' % text.replace("'", "\\'"), smali)
        self.assertIn('getStackTrace', smali)


SIZES_JAVA = '''package t;
import oneos.camera.OneOSResolution;
public enum Sizes {
    RESOLUTION_3264X2448, RESOLUTION_4000X3000, RESOLUTION_4000X2252, RESOLUTION_8160X6120, RESOLUTION_8160X4592,
    RESOLUTION_1920X1080, RESOLUTION_1920X1080_60FPS, RESOLUTION_3024X3024, RESOLUTION_12000X9000, RESOLUTION_BROKEN,
    RESOLUTION_0X0, RESOLUTION_123456X1, OTHER_640X480;
    public static Object find(Object key) { return OneOSResolution.LOOKUP.apply(key, values()); }
    public static Object in(Object key, Object table) { return OneOSResolution.LOOKUP.apply(key, table); }
}
'''
BARE_JAVA = '''package t;
import oneos.camera.OneOSResolution;
public enum Bare {
    A, RESOLUTION_, RESOLUTION_X;
    public static Object find(Object key) { return OneOSResolution.LOOKUP.apply(key, values()); }
}
'''
PROBE_JAVA = '''package t;
public class Probe {
    public static Object ask(Object key) { return Sizes.find(key); }
    public static Object other(Object key) { return Sizes.find(key); }
}
'''
MAIN_JAVA = '''package t;
import java.lang.reflect.Field;
import oneos.camera.OneOSResolution;
public class Main {
    static Object plain(Object key) { return Sizes.find(key); }
    static void show(String what, Object got) { System.out.println(what + " -> " + got); }
    public static void main(String[] args) throws Exception {
        for (String s : new String[] {"8000x6000", "8000X6000", "8000x4500", "4080x2296", "1920x1080", "2000x2000", "100x37",
                "8000x6000", "abc", "0x0", "8000x", "x6000", "123456x1", "8000x6000x1", "-8000x6000", ""}) {
            show("plain " + s, plain(s));
        }
        show("plain id -1", plain(-1));
        show("plain id 99999", plain(99999));
        show("plain null", plain(null));
        show("plain a long", plain(7L));
        show("bare table id -1", Bare.find(-1));
        show("bare table 8000x6000", Bare.find("8000x6000"));
        show("not a table", Sizes.in("8000x6000", new String[] {"RESOLUTION_4000X3000"}));
        show("not from the table", OneOSResolution.LOOKUP.apply("8000x6000", Sizes.values()));
        Field f = OneOSResolution.class.getDeclaredField("CATCHERS");
        f.setAccessible(true);
        show("the list as built", "[" + f.get(null) + "]");
        show("probe before the list 640x360", Probe.ask("640x360"));
        f.set(null, " u.Else.x t.Probe.ask ");
        show("probe 8000x6000", Probe.ask("8000x6000"));
        show("probe id -1", Probe.ask(-1));
        show("probe's other method 8000x6000", Probe.other("8000x6000"));
        show("plain after the list 8000x6000", plain("8000x6000"));
        show("probe again", Probe.ask("8000x6000"));
    }
}
'''
WANT_OUT = '''plain 8000x6000 -> RESOLUTION_8160X6120
plain 8000X6000 -> RESOLUTION_8160X6120
plain 8000x4500 -> RESOLUTION_8160X4592
plain 4080x2296 -> RESOLUTION_4000X2252
plain 1920x1080 -> RESOLUTION_1920X1080
plain 2000x2000 -> RESOLUTION_3024X3024
plain 100x37 -> RESOLUTION_1920X1080
plain 8000x6000 -> RESOLUTION_8160X6120
plain abc -> null
plain 0x0 -> null
plain 8000x -> null
plain x6000 -> null
plain 123456x1 -> null
plain 8000x6000x1 -> null
plain -8000x6000 -> null
plain  -> null
plain id -1 -> RESOLUTION_4000X3000
plain id 99999 -> RESOLUTION_4000X3000
plain null -> null
plain a long -> null
bare table id -1 -> null
bare table 8000x6000 -> null
not a table -> null
not from the table -> null
the list as built -> [ @oneos-callers-that-catch@ ]
probe before the list 640x360 -> RESOLUTION_1920X1080
probe 8000x6000 -> null
probe id -1 -> null
probe's other method 8000x6000 -> RESOLUTION_8160X6120
plain after the list 8000x6000 -> RESOLUTION_8160X6120
probe again -> null
'''
SAID = "OneOSCamera: no entry for %s in this camera's size table: %s"
WANT_ERR = [SAID % x for x in (
    ('size 8000x6000', 'using RESOLUTION_8160X6120'), ('size 8000X6000', 'using RESOLUTION_8160X6120'),
    ('size 8000x4500', 'using RESOLUTION_8160X4592'), ('size 4080x2296', 'using RESOLUTION_4000X2252'),
    ('size 1920x1080', 'using RESOLUTION_1920X1080'), ('size 2000x2000', 'using RESOLUTION_3024X3024'),
    ('size 100x37', 'using RESOLUTION_1920X1080'))] + [SAID % ('size ' + s, "nothing to offer, the camera's own error follows")
                                                        for s in ('abc', '0x0', '8000x', 'x6000', '123456x1', '8000x6000x1', '-8000x6000', '')] + [
    SAID % x for x in (
        ('id -1', 'using RESOLUTION_4000X3000'), ('id 99999', 'using RESOLUTION_4000X3000'),
        ('id -1', "nothing to offer, the camera's own error follows"), ('size 8000x6000', "nothing to offer, the camera's own error follows"),
        ('size 640x360', 'using RESOLUTION_1920X1080'), ('size 8000x6000', 't.Probe.ask deals with that itself'),
        ('id -1', 't.Probe.ask deals with that itself'))]


@unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no Java on this machine')
class HelperChoices(unittest.TestCase):
    def test_what_a_miss_gets(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / 'src/t').mkdir(parents=True)
            for name, text in (('Sizes', SIZES_JAVA), ('Bare', BARE_JAVA), ('Probe', PROBE_JAVA), ('Main', MAIN_JAVA)):
                (t / f'src/t/{name}.java').write_text(text)
            built = subprocess.run(['javac', '-Xlint:all', '-Werror', '-d', str(t / 'out'), str(JAVA)]
                                   + [str(p) for p in sorted((t / 'src/t').glob('*.java'))], capture_output=True, text=True, timeout=300)
            self.assertEqual((0, ''), (built.returncode, built.stdout + built.stderr))
            ran = subprocess.run(['java', '-cp', str(t / 'out'), 't.Main'], capture_output=True, text=True, timeout=120)
            self.assertEqual(0, ran.returncode, ran.stderr[-600:])
            self.assertEqual(WANT_OUT, ran.stdout)
            # One line per different miss, however often it comes.
            self.assertEqual(WANT_ERR, ran.stderr.splitlines())


if __name__ == '__main__':
    unittest.main()
