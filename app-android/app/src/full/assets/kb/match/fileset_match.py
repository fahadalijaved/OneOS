#!/usr/bin/env python3
"""Pair functions and data of a stripped fileset kernel with a native kernel that has symbols."""
import argparse
from array import array
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
import hashlib
import json
import struct
from pathlib import Path

from kc_image import Image, scan
from fileset_shape import checked_shape

EXEC_SEGMENTS = ('__TEXT_EXEC', '__TEXT_BOOT_EXEC', '__KLD', '__LAST')
MATCHER_VERSION = 8


def matcher_signature():
    """Invalidate cached maps when analysis code or reviewed evidence changes."""
    root = Path(__file__).parent
    digest = hashlib.sha256()
    for path in [Path(__file__),root/'kc_image.py',root/'fileset_shape.py',*sorted((root/'fixtures').glob('fileset-*-symbols.json'))]:
        digest.update(path.name.encode()+b'\0'+path.read_bytes())
    return digest.hexdigest()


def vtable_slots(side, base):
    result = []
    for offset in range(16, 8192, 8):
        pointer = side.fixups.get(base + offset)
        if not pointer or pointer[1:3] != (1, 0) or not side.in_exec(pointer[0]):
            return result
        result.append(pointer)
    return []  # unterminated, so no proven table extent


class Side:
    """Functions, references and pointer fixups of one kernel."""

    def __init__(self, image, fixups, mapped):
        self.image = image
        self.fixups = fixups
        self.mapped = mapped
        execs = [s for s in image.segments if s['name'] in EXEC_SEGMENTS and s['size']]
        self.exec_ranges = [(s['va'], s['va'] + s['size']) for s in execs]
        backed = [(s['va'], s['va'] + s['filesize']) for s in execs if s['filesize']]
        starts = sorted(a for a in set(image.function_starts()) if self.in_exec(a))
        self.starts = starts
        self.checked_functions = {}
        self.functions, self.callees, self.callers = {}, defaultdict(set), defaultdict(set)
        for index, start in enumerate(starts):
            end = min([e for b, e in self.exec_ranges if b <= start < e] +
                      ([starts[index + 1]] if index + 1 < len(starts) else []))
            for b, e in backed:
                if b <= start < e:
                    end = min(end, e)
            if end - start < 4:
                continue
            calls, refs, shape = scan(image.read(start, end - start), start)
            strings = {}
            for site, address, _ in refs:
                if not self.in_exec(address):
                    text = image.cstring(address)
                    if text is not None and len(text) >= 4:
                        strings[site] = text
            self.functions[start] = {
                'end': end,
                'refs': [(site - start, address) for site, address, _ in refs],
                'length': len(shape),
                'digest': hashlib.md5(array('I', shape)).hexdigest(),
                'strings': strings,
                'calls': [(site - start, target) for site, target, _ in calls],
            }
            checked, positions, _, _ = checked_shape(image.read(start, end - start), start)
            self.checked_functions[start] = {
                'digest': hashlib.md5(array('I', checked)).hexdigest(), 'length': len(checked),
                'refs': [(positions[site-start], address) for site,address,_ in refs if site-start in positions],
                'calls': [(positions[site-start], target) for site,target,_ in calls if site-start in positions],
            }
            for _, target, _ in calls:
                if self.in_exec(target):
                    at = bisect_right(starts, target) - 1
                    if at >= 0:
                        self.callees[start].add(starts[at])
                        self.callers[starts[at]].add(start)
        self.symbol_names = image.symbols()
        self.symbol_addrs = sorted(self.symbol_names)
        names = defaultdict(set)
        for address, symbols in self.symbol_names.items():
            if address in self.functions:
                for name in symbols:
                    names[name].add(address)
        self.named_functions = {name: next(iter(addresses)) for name,addresses in names.items()
                                if len(addresses) == 1}
        self.string_owners = defaultdict(set)
        for start, fn in self.functions.items():
            for text in set(fn['strings'].values()):
                self.string_owners[text].add(start)
        self.diversity = defaultdict(set)
        for _, (target, auth, _, diversity, _) in fixups.items():
            if auth and diversity and self.in_mapped(target):
                self.diversity[diversity].add(target)

    def in_exec(self, address):
        return any(b <= address < e for b, e in self.exec_ranges)

    def in_mapped(self, address):
        return any(b <= address < e for b, e in self.mapped)

    def name_at(self, address):
        names, addend = self.symbol_names.get(address), 0
        if not names:
            index = bisect_right(self.symbol_addrs, address) - 1
            if index < 0:
                return None, 0
            base = self.symbol_addrs[index]
            addend = address - base
            if addend > 0x10000:
                return None, 0
            names = self.symbol_names[base]
        return min(names), addend

    def section_of(self, address):
        section = self.image.section(address)
        return f"{section['segment']},{section['name']}" if section else '?'


class Matcher:
    """Bind original functions to native functions; every bind must survive its checks."""

    def __init__(self, original, native):
        self.original, self.native = original, native
        self.pairs, self.reverse, self.how = {}, {}, {}
        self.conflicts = []

    def bind(self, orig, native, how):
        if self.pairs.get(orig) == native:
            return False
        if any('.cold.' in name for name in self.native.symbol_names.get(native, ())):
            left, right = self.original.functions.get(orig), self.native.functions.get(native)
            if left and right and left['digest'] != right['digest']:
                return False
        if orig in self.pairs or native in self.reverse and how not in ('vtable', 'reviewed', 'metaclass-getter'):
            self.conflicts.append({'kind': 'double-bind', 'orig': f'{orig:#x}',
                                   'native': f'{native:#x}', 'via': how})
            return False
        self.pairs[orig], self.how[orig] = native, how
        self.reverse.setdefault(native, orig)
        return True

    PURE_LEAF_SKIP = {0xd503245f, 0xd503241f, 0xd503249f, 0xd50324df}  # BTI variants
    PURE_LEAF_RET = {0xd65f03c0, 0xd65f0bff, 0xd65f0fff}               # RET, RETAA, RETAB

    @classmethod
    def pure_leaf(cls, side, start):
        """The instructions of a function that only computes registers and returns, else None.

        Such a body has no memory access, call or branch, so any function with the same
        instructions behaves the same; its identity does not matter.
        """
        fn = side.functions.get(start)
        if fn is None:
            return None
        count = (fn['end'] - start) // 4
        words = [w for w in struct.unpack(f'<{count}I', side.image.read(start, count * 4))
                 if w not in cls.PURE_LEAF_SKIP]
        for index, word in enumerate(words[:8]):
            if word in cls.PURE_LEAF_RET:
                return tuple(words[:index + 1])
            if (word >> 25) & 0xf not in (0b1000, 0b1001, 0b0101, 0b1101):
                return None  # not data processing on registers
        return None

    def pair_pure_leaves(self, targets):
        """Bind each unpaired kext-facing pure leaf to an unused native function with the same instructions."""
        pool = defaultdict(list)
        for start in sorted(self.native.functions):
            body = self.pure_leaf(self.native, start)
            if body is not None and start not in self.reverse:
                pool[body].append(start)
        bound = 0
        for orig in sorted(targets):
            if orig in self.pairs or orig not in self.original.functions:
                continue
            body = self.pure_leaf(self.original, orig)
            if body is not None and pool.get(body):
                bound += self.bind(orig, pool[body].pop(0), 'pure-leaf')
        return bound

    def canon(self, native_start):
        # Local symbols and LLVM outlined names can repeat across object files.
        # Two such names are not one call-graph node.
        return native_start

    def anchor_reference(self, reference, pairing):
        """Transfer identities from unique code matches through unique symbols.

        The additional image is only a naming reference. Final addresses always
        come from the actual native kernel; graph/string guesses do not transfer.
        """
        accepted = {'shape', 'pac-checked-shape', 'reference-shape', 'reviewed'}
        bound = 0
        for key, value in pairing['functions'].items():
            if value['how'] not in accepted:
                continue
            orig, ref = int(key,16), int(value['native'],16)
            names = [name for name in reference.symbol_names.get(ref, ())
                     if reference.named_functions.get(name) == ref and
                     not any(part in name for part in ('.cold.', 'OUTLINED_FUNCTION', '.llvm.'))]
            targets = {self.native.named_functions[name] for name in names
                       if name in self.native.named_functions}
            if len(targets) == 1:
                bound += self.bind(orig, next(iter(targets)), 'reference-symbol')
        return bound

    def anchor_reference_order(self, reference, pairing, rounds=4):
        """Fill gaps between ordered reference pairs, then transfer names like anchor_reference.

        The release reference keeps the original's function order (one object
        file after another), so unpaired functions between two consecutive
        pairs line up in order when their lengths agree.
        """
        pairs = {int(k, 16): int(v['native'], 16) for k, v in pairing['functions'].items()}
        for _ in range(rounds):
            reverse = {v: k for k, v in pairs.items()}
            anchors = sorted(pairs)
            added = {}
            for left, right in zip(anchors, anchors[1:]):
                if pairs[right] <= pairs[left]:
                    continue
                a, b = bisect_right(self.original.starts, left), bisect_left(self.original.starts, right)
                gap = [o for o in self.original.starts[a:b] if o not in pairs and o in self.original.functions]
                a, b = bisect_right(reference.starts, pairs[left]), bisect_left(reference.starts, pairs[right])
                fill = [n for n in reference.starts[a:b] if n not in reverse and n in reference.functions]
                if not gap or not fill or len(gap) * len(fill) > 40000:
                    continue
                lengths = [self.original.functions[o]['length'] for o in gap], [reference.functions[n]['length'] for n in fill]
                close = lambda i, j: abs(lengths[0][i] - lengths[1][j]) <= max(2, max(lengths[0][i], lengths[1][j]) // 10)
                if len(gap) == len(fill):
                    added.update((gap[i], (fill[i], True)) for i in range(len(gap)) if close(i, i))
                    continue
                table = [[0] * (len(fill) + 1) for _ in range(len(gap) + 1)]
                for i in range(len(gap) - 1, -1, -1):
                    for j in range(len(fill) - 1, -1, -1):
                        table[i][j] = table[i + 1][j + 1] + 1 if close(i, j) else max(table[i + 1][j], table[i][j + 1])
                i = j = 0
                while i < len(gap) and j < len(fill):
                    if close(i, j) and table[i][j] == table[i + 1][j + 1] + 1:
                        added[gap[i]] = (fill[j], False)
                        i += 1
                        j += 1
                    elif table[i + 1][j] >= table[i][j + 1]:
                        i += 1
                    else:
                        j += 1
            # Order alone is not proof: calls into paired functions must agree with the reference,
            # and a function without such calls needs a near-identical length.
            # In a gap of unequal counts, a length match alone is not enough.
            checked = {}
            for orig, (ref, equal) in added.items():
                agree = sum(1 for t in self.original.callees[orig] if t in pairs and pairs[t] in reference.callees[ref])
                miss = sum(1 for t in self.original.callees[orig] if t in pairs and pairs[t] not in reference.callees[ref])
                exact = abs(self.original.functions[orig]['length'] - reference.functions[ref]['length']) <= 2
                texts = set(self.original.functions[orig]['strings'].values()), set(reference.functions[ref]['strings'].values())
                if texts[0] and texts[1] and texts[0] != texts[1]:
                    continue
                if (agree and miss * 4 <= agree) or (equal and not agree and not miss and exact) or \
                        (texts[0] and texts[0] == texts[1] and not miss):
                    checked[orig] = ref
            if not checked:
                break
            pairs.update(checked)
        # A pair is kept when it sits in order between its neighbors; out-of-order pairs are the
        # ones layout or a wrong match moved.
        anchors = sorted(pairs)
        monotone = {anchors[i] for i in range(1, len(anchors) - 1)
                    if pairs[anchors[i - 1]] < pairs[anchors[i]] < pairs[anchors[i + 1]]}
        bound = 0
        for orig, ref in pairs.items():
            if orig in self.pairs or orig not in monotone:
                continue
            names = [name for name in reference.symbol_names.get(ref, ())
                     if reference.named_functions.get(name) == ref and
                     not any(part in name for part in ('.cold.', 'OUTLINED_FUNCTION', '.llvm.'))]
            targets = {self.native.named_functions[name] for name in names if name in self.native.named_functions}
            if len(targets) == 1:
                bound += self.bind(orig, next(iter(targets)), 'reference-order')
        return bound

    def reference_data(self, reference, pairing, targets, known):
        """Name data targets through the reference: paired data, or a fixed offset from the
        nearest paired object of the same section that lands on a reference symbol."""
        pairs = {int(k, 16): int(v['native'], 16) for k, v in pairing['data'].items()}
        anchors = sorted(pairs)
        natives = defaultdict(set)
        for address, names in self.native.symbol_names.items():
            if not self.native.in_exec(address):
                for name in names:
                    natives[name].add(address)
        added = 0
        for target in sorted(targets):
            if target in known or self.original.in_exec(target):
                continue
            ref = pairs.get(target)
            if ref is None:
                index = bisect_right(anchors, target) - 1
                if index < 0 or target - anchors[index] > 0x10000:
                    continue
                low = anchors[index]
                if self.original.section_of(low) != self.original.section_of(target):
                    continue
                ref = pairs[low] + target - low
                if index + 1 < len(anchors) and anchors[index + 1] - target < 0x10000 and \
                        pairs[anchors[index + 1]] - ref != anchors[index + 1] - target:
                    continue
            if reference.section_of(ref).split(',')[1] != self.original.section_of(target).split(',')[1]:
                continue
            name, addend = reference.name_at(ref)
            if name is None or addend not in (0, 16) or (addend and not name.startswith('__ZTV')):
                continue
            if reference.symbol_names.get(ref - addend, ()) and len(natives.get(name, ())) == 1:
                known[target] = (next(iter(natives[name])) + addend, 'reference-data')
                added += 1
        return added

    def reviewed_records(self, inputs):
        """Reviewed identities are pinned to the original kernelcache; the native side is named by symbol,
        so a rebuilt native kernel keeps them."""
        for path in sorted((Path(__file__).parent / 'fixtures').glob('fileset-*-symbols.json')):
            record = json.loads(path.read_text())
            pinned = record['inputs']
            if (pinned['kernelcache_sha256'], pinned['entry']) == (inputs['kernelcache_sha256'], inputs['entry']):
                yield record

    def pair_data_slots(self, targets, known):
        """A constant pointer slot (Class::metaClass, kOSBooleanTrue) is named by the object it points to."""
        pointed = defaultdict(set)
        for site, (target, *_rest) in self.native.fixups.items():
            if not self.native.in_exec(site) and self.native.symbol_names.get(site):
                pointed[target].add(site)
        objects = {address: native for address, (native, _) in known.items()}
        added = 0
        for target in sorted(targets):
            if target in known or self.original.in_exec(target):
                continue
            fix = self.original.fixups.get(target)
            if not fix:
                continue
            native_object = self.pairs.get(fix[0]) if self.original.in_exec(fix[0]) else objects.get(fix[0])
            slots = pointed.get(native_object, set())
            if len(slots) == 1:
                known[target] = (next(iter(slots)), 'slot')
                added += 1
        return added

    def pair_sysctl_variables(self, targets, known):
        """A sysctl OID names its variable: oid_name (+0x30) is a string, oid_arg1 (+0x20) the variable."""
        def variables(side):
            found = defaultdict(set)
            image = side.image
            for site, (target, *_rest) in side.fixups.items():
                arg = side.fixups.get(site - 0x10)
                if not arg or side.in_exec(arg[0]) or not side.in_mapped(site):
                    continue
                try:
                    raw = image.read(target, 64)
                except ValueError:
                    continue
                name = raw.split(b'\0', 1)[0]
                if 3 <= len(name) < 64 and b'\0' in raw and all(48 <= b < 123 or b == 95 for b in name):
                    found[name].add(arg[0])
            return found
        original, native = variables(self.original), variables(self.native)
        added = 0
        # SYSCTL_NODE anchors "__anchor__(_parent_name)" hang off their node's children list (oid_parent, +0).
        symbols = {name: address for address, names in self.native.symbol_names.items() for name in names}
        for site, (target, *_rest) in self.original.fixups.items():
            parent = self.original.fixups.get(site - 0x28)
            if not parent or parent[0] not in targets or parent[0] in known:
                continue
            try:
                name = self.original.image.read(target, 80).split(b'\0', 1)[0]
            except ValueError:
                continue
            if name.startswith(b'__anchor__(') and name.endswith(b')'):
                children = symbols.get(f'_sysctl_{name[11:-1].decode()}_children')
                if children is not None:
                    known[parent[0]] = (children, 'sysctl')
                    added += 1
        for name, addresses in original.items():
            if len(addresses) != 1 or len(native.get(name, ())) != 1:
                continue
            address = next(iter(addresses))
            if address in targets and address not in known:
                known[address] = (next(iter(native[name])), 'sysctl')
                added += 1
        return added

    def pair_data_fields(self, targets, known):
        """Paired constant objects have equal layouts: pointers at equal offsets name each other."""
        votes = defaultdict(Counter)
        for orig, (native, _) in list(known.items()):
            for offset in range(0, 0x100, 8):
                left, right = self.original.fixups.get(orig + offset), self.native.fixups.get(native + offset)
                if left and right and left[0] in targets and left[0] not in known and \
                        not self.original.in_exec(left[0]) and not self.native.in_exec(right[0]):
                    votes[left[0]][right[0]] += 1
        added = 0
        for target, counter in votes.items():
            (best, count), = counter.most_common(1)
            if count >= 2 and count * 4 >= sum(counter.values()) * 3:
                known[target] = (best, 'fields')
                added += 1
        return added

    def pair_data_by_users(self, targets, known):
        """Every paired function that references a data target references its native counterpart."""
        users = defaultdict(set)
        for orig, fn in self.original.functions.items():
            if orig in self.pairs:
                for _, address in fn['refs']:
                    users[address].add(orig)
        added = 0
        for target in sorted(targets):
            if target in known or self.original.in_exec(target) or not users.get(target):
                continue
            section = self.original.section_of(target).split(',')[-1]
            candidates = None
            for orig in users[target]:
                refs = {address for _, address in self.native.functions[self.pairs[orig]]['refs']
                        if not self.native.in_exec(address) and self.native.section_of(address).split(',')[-1] == section}
                candidates = refs if candidates is None else candidates & refs
            if candidates and len(candidates) == 1 and len(users[target]) >= 2:
                known[target] = (next(iter(candidates)), 'users')
                added += 1
        return added

    def anchor_reviewed(self, inputs):
        """Load individually reviewed ABI identities for the exactly pinned original image."""
        added = 0
        for record in self.reviewed_records(inputs):
            for entry in record['functions']:
                if not entry.get('evidence'):
                    raise ValueError('Reviewed function requires recorded evidence')
                orig = int(entry['original'],16)
                if orig not in self.original.functions:
                    raise ValueError(f'Reviewed function is absent: {entry["original"]}')
                fn = self.original.functions[orig]
                if hashlib.sha256(self.original.image.read(orig, fn['end'] - orig)).hexdigest() != entry['original_sha256']:
                    raise ValueError(f'Reviewed function bytes changed: {entry["original"]}')
                native = self.native.named_functions.get(entry['native_symbol'])
                if native is not None:
                    added += self.bind(orig, native, 'reviewed')
        return added

    def reviewed_data(self, inputs, known):
        """Reviewed data identities: original address -> native symbol plus addend."""
        names = defaultdict(set)
        for address, symbols in self.native.symbol_names.items():
            for name in symbols:
                names[name].add(address)
        added = 0
        for record in self.reviewed_records(inputs):
            for entry in record.get('data', []):
                if not entry.get('evidence'):
                    raise ValueError('Reviewed data requires recorded evidence')
                found = names.get(entry['native_symbol'], ())
                if len(found) == 1:
                    known[int(entry['original'], 16)] = (next(iter(found)) + entry.get('addend', 0), 'reviewed')
                    added += 1
        return added

    def anchor_strings(self):
        """Unique string references anchor the first pairs."""
        votes = defaultdict(Counter)
        for text, owners in self.original.string_owners.items():
            targets = self.native.string_owners.get(text)
            if targets and len(owners) == 1 and len(targets) == 1:
                orig, target = next(iter(owners)), next(iter(targets))
                # LLVM may outline the panic path into foo.cold.N in only one
                # build. A string in that path identifies foo, not an ABI-callable
                # replacement for foo. Equal-shaped outlined functions can still
                # match directly; otherwise require the named parent to call it.
                left, right = self.original.functions[orig], self.native.functions[target]
                if left['digest'] != right['digest']:
                    parents = {self.native.named_functions.get(name.split('.cold.')[0])
                               for name in self.native.symbol_names.get(target, ()) if '.cold.' in name}
                    parents.discard(None)
                    if parents:
                        if len(parents) != 1:
                            continue
                        parent = next(iter(parents))
                        if target not in self.native.callees[parent]:
                            continue
                        target = parent
                votes[orig][target] += 1
        claimed = Counter(n for counter in votes.values() for n in counter)
        bound = 0
        for orig, counter in votes.items():
            if len(counter) == 1:
                native = next(iter(counter))
                if claimed[native] == 1:
                    bound += self.bind(orig, native, 'string')
        return bound

    def anchor_shapes(self):
        """A relocation-masked instruction sequence owned by exactly one function per side."""
        groups = defaultdict(lambda: ([], []))
        for orig, fn in self.original.functions.items():
            groups[(fn['digest'], fn['length'])][0].append(orig)
        for native, fn in self.native.functions.items():
            groups[(fn['digest'], fn['length'])][1].append(native)
        bound = 0
        for originals, natives in groups.values():
            if len(originals) == 1 and len(natives) == 1:
                bound += self.bind(originals[0], natives[0], 'shape')
        return bound

    def anchor_checked_shapes(self):
        """Match unique bodies while accounting for explicit compiler PAC checks."""
        groups = defaultdict(lambda: ([], []))
        for index, side in enumerate((self.original, self.native)):
            for address, fn in side.checked_functions.items():
                groups[fn['digest'], fn['length']][index].append(address)
        return sum(self.bind(a[0], b[0], 'pac-checked-shape')
                   for a,b in groups.values() if len(a) == len(b) == 1)

    def comparable_functions(self, orig, native):
        left, right = self.original.functions[orig], self.native.functions[native]
        if left['digest'] != right['digest']:
            left = getattr(self.original, 'checked_functions', {}).get(orig, left)
            right = getattr(self.native, 'checked_functions', {}).get(native, right)
        return left, right


    def propagate(self):
        """Match unmatched functions by their set of already matched neighbor names."""
        index = defaultdict(list)
        for native in self.native.functions:
            if native not in self.reverse:
                out = frozenset(self.canon(n) for n in self.native.callees[native] if n in self.reverse)
                incoming = frozenset(self.canon(n) for n in self.native.callers[native] if n in self.reverse)
                index[out,incoming].append(native)
        proposals, claimed = [], Counter()
        for orig in self.original.functions:
            if orig in self.pairs:
                continue
            out = frozenset(self.canon(self.pairs[t]) for t in self.original.callees[orig] if t in self.pairs)
            incoming = frozenset(self.canon(self.pairs[t]) for t in self.original.callers[orig] if t in self.pairs)
            if len(out | incoming) < 2:
                continue
            candidates = index.get((out,incoming), [])
            if len(candidates) > 1:
                digest = self.original.functions[orig]['digest']
                candidates = [n for n in candidates if self.native.functions[n]['digest'] == digest]
            if len(candidates) == 1:
                proposals.append((orig, candidates[0]))
                claimed[candidates[0]] += 1
        bound = 0
        for orig, native in proposals:
            if claimed[native] == 1:
                bound += self.bind(orig, native, 'calls')
        return bound

    def validate_calls(self):
        """Inlining differs between builds; unbind only when many matched edges disagree."""
        bad = []
        for orig, native in self.pairs.items():
            out_missing = sum(1 for t in self.original.callees[orig]
                              if t in self.pairs and self.pairs[t] not in self.native.callees[native])
            in_missing = sum(1 for n in self.native.callees[native]
                             if n in self.reverse and self.reverse[n] not in self.original.callees[orig])
            agree = sum(1 for t in self.original.callees[orig]
                        if t in self.pairs and self.pairs[t] in self.native.callees[native])
            if out_missing + in_missing > max(2, (agree + out_missing + in_missing) // 4):
                bad.append(orig)
        for orig in bad:
            self.conflicts.append({'kind': 'call-edge', 'orig': f'{orig:#x}',
                                   'native': f'{self.pairs[orig]:#x}', 'via': self.how[orig]})
            del self.reverse[self.pairs.pop(orig)]
            del self.how[orig]
        return len(bad)

    def align_orders(self):
        """Between matched anchors, equal shapes in the same order bind non-unique functions."""
        bound = sorted(self.pairs)
        added = 0
        for left, right in zip(bound, bound[1:]):
            if self.pairs[right] <= self.pairs[left]:
                continue
            a, b = bisect_right(self.original.starts, left), bisect_left(self.original.starts, right)
            gap = [o for o in self.original.starts[a:b] if o not in self.pairs]
            a = bisect_right(self.native.starts, self.pairs[left])
            b = bisect_left(self.native.starts, self.pairs[right])
            fill = [n for n in self.native.starts[a:b] if n not in self.reverse]
            if not gap or not fill:
                continue
            original = self.original.functions
            native = self.native.functions
            # Longest common subsequence over relocation-masked shapes.
            table = [[0] * (len(fill) + 1) for _ in range(len(gap) + 1)]
            for i in range(len(gap) - 1, -1, -1):
                for j in range(len(fill) - 1, -1, -1):
                    if original[gap[i]]['digest'] == native[fill[j]]['digest']:
                        table[i][j] = table[i + 1][j + 1] + 1
                    else:
                        table[i][j] = max(table[i + 1][j], table[i][j + 1])
            i = j = 0
            while i < len(gap) and j < len(fill):
                if original[gap[i]]['digest'] == native[fill[j]]['digest']:
                    added += self.bind(gap[i], fill[j], 'order')
                    i += 1
                    j += 1
                elif table[i + 1][j] >= table[i][j + 1]:
                    i += 1
                else:
                    j += 1
        return added

    def validate_diversity(self):
        """A pointer diversity is a name hash: a bound pair must not contradict it."""
        bad = []
        for diversity, originals in self.original.diversity.items():
            natives = self.native.diversity.get(diversity)
            if not natives:
                continue
            for orig in originals:
                native = self.pairs.get(orig)
                if native is not None and native not in natives:
                    bad.append(orig)
        for orig in sorted(set(bad)):
            if orig not in self.pairs:
                continue
            self.conflicts.append({'kind': 'diversity', 'orig': f'{orig:#x}',
                                   'native': f'{self.pairs[orig]:#x}', 'via': self.how[orig]})
            del self.reverse[self.pairs.pop(orig)]
            del self.how[orig]
        return len(bad)

    def pair_data(self, known):
        """Identical functions reference their data at identical instruction offsets."""
        votes = defaultdict(Counter)
        for orig, native in self.pairs.items():
            left, right = self.comparable_functions(orig, native)
            if left['digest'] != right['digest'] or len(left['refs']) != len(right['refs']):
                continue
            for (offset, address), (native_offset, native_address) in zip(left['refs'], right['refs']):
                if offset != native_offset:
                    break
                if not self.original.in_exec(address) and not self.native.in_exec(native_address) and \
                        self.original.in_mapped(address) and self.native.in_mapped(native_address):
                    votes[address][native_address] += 1
        split = 0
        for address, counter in votes.items():
            if address in known:
                continue
            if len(counter) == 1:
                known[address] = (next(iter(counter)), 'refs')
            else:
                split += 1
        return split

    def pair_calls(self):
        """Use corresponding call sites in already paired, equal-shaped functions."""
        votes = defaultdict(set)
        for orig, native in self.pairs.items():
            left, right = self.comparable_functions(orig, native)
            if not left or not right or left['digest'] != right['digest'] or left['length'] != right['length']:
                continue
            if len(left['calls']) != len(right['calls']):
                continue
            for (offset, target), (native_offset, native_target) in zip(left['calls'], right['calls']):
                if offset != native_offset:
                    break
                if target in self.original.functions and native_target in self.native.functions:
                    votes[target].add(native_target)
        return sum(self.bind(orig, next(iter(targets)), 'call-sites')
                   for orig, targets in votes.items() if len(targets) == 1)

    def pair_data_users(self, known):
        """Two identified data objects jointly identify their unique function user.

        Include already-bound functions in the candidate index: removing them
        first would turn an ambiguous data signature into a false unique match.
        """
        users = defaultdict(set)
        for native, fn in self.native.functions.items():
            for _, address in fn['refs']:
                users[address].add(native)
        proposals, claimed = [], Counter()
        for orig, fn in self.original.functions.items():
            if orig in self.pairs:
                continue
            anchors = {known[address][0] for _, address in fn['refs'] if address in known}
            if len(anchors) < 2:
                continue
            candidates = set.intersection(*(users[address] for address in anchors))
            calls = {self.pairs[target] for target in self.original.callees[orig]
                     if target in self.pairs and target != orig}
            if len(candidates) > 1 and calls:
                candidates = {n for n in candidates if calls <= self.native.callees[n]}
            if len(candidates) == 1:
                native = next(iter(candidates))
                proposals.append((orig, native))
                claimed[native] += 1
        return sum(self.bind(orig, native, 'data-users') for orig, native in proposals if claimed[native] == 1)

    def pair_reference_shapes(self, known):
        """Disambiguate equal-shaped methods by every data operand and call site."""
        shapes = defaultdict(list)
        for n, fn in self.native.functions.items():
            shapes[fn['digest'],fn['length']].append(n)
        proposals, claimed = [], Counter()
        for o,left in self.original.functions.items():
            if o in self.pairs or not any(a in known for _,a in left['refs']):
                continue
            candidates = []
            for n in shapes[left['digest'],left['length']]:
                right = self.native.functions[n]
                if len(left['refs']) != len(right['refs']) or len(left['calls']) != len(right['calls']):
                    continue
                valid = True
                for (site,address),(other,target) in zip(left['refs'],right['refs']):
                    if site != other:
                        valid = False; break
                    if address in known:
                        if known[address][0] != target:
                            valid = False; break
                    else:
                        string = self.original.image.cstring(address)
                        if string is None or string != self.native.image.cstring(target):
                            valid = False; break
                if not valid:
                    continue
                for (site,address),(other,target) in zip(left['calls'],right['calls']):
                    if site != other:
                        valid = False; break
                    if o <= address < left['end']:
                        if target-n != address-o:
                            valid = False; break
                    elif self.pairs.get(address) != target:
                        valid = False; break
                if valid:
                    candidates.append(n)
            if len(candidates) == 1:
                proposals.append((o,candidates[0]));claimed[candidates[0]] += 1
        return sum(self.bind(o,n,'reference-shape') for o,n in proposals if claimed[n] == 1)

    def diversity_data(self, known):
        """A diversity held by one target per side names that target; binds functions and data."""
        collisions = 0
        for diversity, originals in self.original.diversity.items():
            natives = self.native.diversity.get(diversity)
            if not natives:
                continue
            if len(originals) != 1 or len(natives) != 1:
                collisions += 1
                continue
            orig, native = next(iter(originals)), next(iter(natives))
            if self.original.in_exec(orig) and self.native.in_exec(native):
                self.bind(orig, native, 'diversity')
            elif orig not in known and not self.original.in_exec(orig) and not self.native.in_exec(native):
                known[orig] = (native, 'diversity')
        return collisions

    def anchor_vtables(self, known):
        """Match slots only within an identified table with the same complete PAC layout.

        A discriminator alone identifies a virtual slot, not its implementation.
        Table identity comes from paired data references; native symbols delimit
        the table start. Stop at the first non-function pointer, before padding
        and the following object. Never extend to the next symbol through a gap.
        """
        votes = defaultdict(set)
        identified = set()
        for orig, (native, how) in known.items():
            if how not in ('refs', 'vtable-layout', 'vtable-user', 'metaclass-vtable') or not any(name.startswith('__ZTV')
                                       for name in self.native.symbol_names.get(native, ())):
                continue
            if self.original.image.read(orig, 16) != bytes(16) or self.native.image.read(native, 16) != bytes(16):
                continue
            left, right = vtable_slots(self.original, orig), vtable_slots(self.native, native)
            if len(left) < 2 or len(left) != len(right) or any(a[1:] != b[1:] for a, b in zip(left, right)):
                continue
            for a, b in zip(left, right):
                votes[a[0]].add(b[0])
                if how in ('metaclass-vtable','vtable-user'):
                    identified.add(a[0])
        added = 0
        for orig, targets in votes.items():
            if len(targets) == 1:
                native = next(iter(targets))
                if orig in identified and self.pairs.get(orig) not in (None,native):
                    if self.how[orig] == 'reviewed':
                        raise ValueError(f'Class vtable contradicts reviewed identity at {orig:#x}')
                    old = self.pairs.pop(orig)
                    self.conflicts.append({'kind':'vtable-correction','orig':hex(orig),
                                           'previous':hex(old),'native':hex(native),'via':self.how.pop(orig)})
                    if self.reverse.get(old) == orig:
                        self.reverse.pop(old)
                        other = next((o for o,n in self.pairs.items() if n == old),None)
                        if other is not None:
                            self.reverse[old] = other
                added += self.bind(orig, native, 'vtable')
        return added

    def pair_vtables(self, known):
        """Find a table using at least two distinct bound methods and all PAC slots."""
        uses = defaultdict(set)
        for site, pointer in self.original.fixups.items():
            if pointer[1:3] == (1, 0) and self.original.in_mapped(site):
                uses[pointer[0]].add(site)
        claimed = {native for native, _ in known.values()}
        added = 0
        for native, names in self.native.symbol_names.items():
            if native in claimed or not any(name.startswith('__ZTV') for name in names):
                continue
            right = vtable_slots(self.native, native)
            anchors = [(index * 8 + 16, self.reverse[pointer[0]]) for index, pointer in enumerate(right)
                       if pointer[0] in self.reverse and
                       self.how[self.reverse[pointer[0]]] not in ('identical-leaf', 'thunk')]
            if len({orig for _, orig in anchors}) < 2:
                continue
            candidates = None
            for offset, orig in sorted(anchors, key=lambda row: len(uses[row[1]])):
                locations = {site - offset for site in uses[orig]}
                candidates = locations if candidates is None else candidates & locations
                if not candidates:
                    break
            qualified = []
            for orig in candidates or ():
                if orig in known or not self.original.in_mapped(orig):
                    continue
                try:
                    if self.original.image.read(orig, 16) != bytes(16):
                        continue
                except ValueError:
                    continue
                left = vtable_slots(self.original, orig)
                if len(left) != len(right) or any(a[1:] != b[1:] for a, b in zip(left, right)):
                    continue
                def disagrees(a, b):
                    target = self.pairs.get(a[0])
                    if target is None or target == b[0]:
                        return False
                    if self.how[a[0]] == 'identical-leaf':
                        first, second = self.native.functions.get(target), self.native.functions.get(b[0])
                        if first and second:
                            return self.native.image.read(target, first['end']-target) != \
                                self.native.image.read(b[0], second['end']-b[0])
                    return True
                if any(disagrees(a, b) for a, b in zip(left, right)):
                    continue
                qualified.append(orig)
            if len(qualified) == 1:
                known[qualified[0]] = (native, 'vtable-layout')
                added += 1
        return added

    def pair_vtable_users(self, known):
        """An identified class method can identify its own complete vtable.

        This covers MetaClass::alloc and initialize routines whose bodies differ
        because of inlining. Require the class name in the native method symbol,
        one matching table in each function, and equal complete PAC layouts.
        """
        votes = defaultdict(set)
        for orig,native in self.pairs.items():
            if self.how[orig] not in ('string','vtable','reviewed','reference-shape'):
                continue
            left,right = self.original.functions.get(orig),self.native.functions.get(native)
            if not left or not right:
                continue
            native_tables = {}
            for _,address in right['refs']:
                names = [n for n in self.native.symbol_names.get(address,()) if n.startswith('__ZTV')]
                if not names:
                    continue
                if not any(name[5:] in method for name in names
                           for method in self.native.symbol_names.get(native,())):
                    continue
                slots = vtable_slots(self.native,address)
                if len(slots) >= 2:
                    native_tables[address] = tuple(p[1:] for p in slots)
            original_tables = {}
            for _,address in left['refs']:
                if not self.original.in_mapped(address):
                    continue
                try:
                    if self.original.image.read(address,16) != bytes(16):
                        continue
                except ValueError:
                    continue
                slots = vtable_slots(self.original,address)
                if len(slots) >= 2:
                    original_tables[address] = tuple(p[1:] for p in slots)
            for address,signature in native_tables.items():
                candidates = [a for a,s in original_tables.items() if s == signature]
                if len(candidates) == 1 and sum(s == signature for s in native_tables.values()) == 1:
                    votes[candidates[0]].add(address)
        added = 0
        for orig,targets in votes.items():
            if orig not in known and len(targets) == 1:
                known[orig] = (next(iter(targets)),'vtable-user')
                added += 1
        return added

    def pair_metaclass_vtables(self, known):
        """The class-specific getMetaClass pointer identifies a complete table."""
        uses = defaultdict(set)
        for site,pointer in self.original.fixups.items():
            if pointer[1:3] == (1,0) and self.original.in_mapped(site):
                uses[pointer[0]].add(site)
        added = 0
        for native,names in self.native.symbol_names.items():
            table_names = [name[5:] for name in names if name.startswith('__ZTV')]
            if not table_names:
                continue
            right = vtable_slots(self.native,native)
            for index,pointer in enumerate(right):
                method = pointer[0]
                if not any('12getMetaClassEv' in name and any(cls in name for cls in table_names)
                           for name in self.native.symbol_names.get(method,())):
                    continue
                originals = [o for o,n in self.pairs.items() if n == method and
                             self.how[o] in ('reference-shape','shape','vtable','reviewed','metaclass-getter')]
                for orig_method in originals:
                    left_fn,right_fn = self.original.functions[orig_method],self.native.functions[method]
                    if left_fn['digest'] != right_fn['digest'] or len(left_fn['refs']) != 1 or len(right_fn['refs']) != 1:
                        continue
                    original_meta,native_meta = left_fn['refs'][0][1],right_fn['refs'][0][1]
                    if known.get(original_meta,(None,))[0] != native_meta:
                        continue
                    if not any('10gMetaClassE' in name and any(cls in name for cls in table_names)
                               for name in self.native.symbol_names.get(native_meta,())):
                        continue
                    for site in uses[orig_method]:
                        orig = site-16-index*8
                        if orig in known:
                            continue
                        try:
                            if self.original.image.read(orig,16) != bytes(16):
                                continue
                        except ValueError:
                            continue
                        left = vtable_slots(self.original,orig)
                        if len(left) == len(right) and all(a[1:] == b[1:] for a,b in zip(left,right)):
                            known[orig] = (native,'metaclass-vtable');added += 1
        return added

    def pair_metaclass_getters(self, known):
        """Identify getMetaClass by its sole known metaobject and exact code shape."""
        getters = defaultdict(set)
        for n,fn in self.native.functions.items():
            if fn['calls'] or len(fn['refs']) != 1:
                continue
            names = [name for name in self.native.symbol_names.get(n,()) if name.endswith('12getMetaClassEv')]
            address = fn['refs'][0][1]
            if not names or not any(name.endswith('10gMetaClassE') for name in self.native.symbol_names.get(address,())):
                continue
            getters[address,fn['digest'],fn['length']].add(n)
        added = 0
        for o,fn in self.original.functions.items():
            if o in self.pairs or fn['calls'] or len(fn['refs']) != 1:
                continue
            target = known.get(fn['refs'][0][1],(None,))[0]
            candidates = getters.get((target,fn['digest'],fn['length']),())
            if len(candidates) == 1:
                added += self.bind(o,next(iter(candidates)),'metaclass-getter')
        return added

    def report(self, data):
        functions = {}
        for orig in sorted(self.pairs):
            native = self.pairs[orig]
            name, addend = self.native.name_at(native)
            functions[f'{orig:#x}'] = {'native': f'{native:#x}', 'name': name, 'addend': addend,
                                       'how': self.how[orig]}
        payload = {
            'matcher_version': MATCHER_VERSION,
            'matcher_signature': matcher_signature(),
            'functions': functions,
            'data': {f'{orig:#x}': {'native': f'{native:#x}', 'name': self.native.name_at(native)[0],
                                    'how': how, 'sections': [self.original.section_of(orig),
                                                             self.native.section_of(native)]}
                     for orig, (native, how) in sorted(data.items())},
            'stats': {
                'functions_original': len(self.original.functions),
                'functions_native': len(self.native.functions),
                'functions_matched': len(self.pairs),
                'functions_by_method': dict(Counter(self.how.values())),
                'data_matched': len(data),
                'data_by_method': dict(Counter(how for _, how in data.values())),
                'conflicts': dict(Counter(c['kind'] for c in self.conflicts)),
            },
            'conflicts': self.conflicts[:100],
        }
        return payload


def match_images(raw, native_data, entry_name='com.apple.kernel', max_rounds=40, reference_data=None, pure_leaves=True):
    """Build a map bound to the exact two input images."""
    cache = Image(raw)
    if entry_name not in cache.entries:
        raise ValueError(f'No fileset entry {entry_name!r}')
    _, at = cache.entries[entry_name]
    entry = Image(raw, at)
    fixups = cache.fixups()
    original = Side(entry, fixups, entry.mapped())
    print(f'original: {len(original.functions)} functions, {len(original.diversity)} diversities')
    native_image = Image(native_data)
    native = Side(native_image, native_image.fixups(), native_image.mapped())
    print(f'native:   {len(native.functions)} functions, {len(native.diversity)} diversities')

    matcher = Matcher(original, native)
    inputs = {'kernelcache_sha256': hashlib.sha256(raw).hexdigest(),
              'native_sha256': hashlib.sha256(native_data).hexdigest(), 'entry': entry_name}
    print(f'reviewed anchors: {matcher.anchor_reviewed(inputs)}')
    if reference_data is not None:
        # Pure-leaf binds carry behaviour, not identity, so the naming reference must not use them.
        reference_pairing = match_images(raw, reference_data, entry_name, max_rounds, pure_leaves=False)
        reference_image = Image(reference_data)
        reference = Side(reference_image, reference_image.fixups(), reference_image.mapped())
        print(f'reference symbol anchors: {matcher.anchor_reference(reference, reference_pairing)}')
        print(f'reference order anchors: {matcher.anchor_reference_order(reference, reference_pairing)}')
    print(f'string anchors: {matcher.anchor_strings()}')
    print(f'PAC checked shape anchors: {matcher.anchor_checked_shapes()}')
    data = {}
    split = 0
    kernel = entry.mapped()
    inside = lambda address: any(b <= address < e for b, e in kernel)
    targets = {fix[0] for site, fix in fixups.items() if inside(fix[0]) and not inside(site)}
    print(f'reviewed data: {matcher.reviewed_data(inputs, data)}')
    if reference_data is not None:
        print(f'reference data names: {matcher.reference_data(reference, reference_pairing, targets, data)}')
    for _ in range(max_rounds):
        bound = matcher.anchor_shapes() + matcher.propagate()
        split = matcher.pair_data(data)
        bound += matcher.pair_metaclass_getters(data) + matcher.pair_metaclass_vtables(data) + matcher.pair_vtable_users(data)
        bound += matcher.pair_vtables(data) + matcher.anchor_vtables(data)
        bound += matcher.pair_calls() + matcher.pair_data_users(data)
        bound += matcher.pair_reference_shapes(data)
        if not bound:
            break
    if pure_leaves:
        print(f'pure leaves: {matcher.pair_pure_leaves(targets)}')
    print(f'data slots: {matcher.pair_data_slots(targets, data)}, data by users: {matcher.pair_data_by_users(targets, data)}, '
          f'sysctl: {matcher.pair_sysctl_variables(targets, data)}, fields: {matcher.pair_data_fields(targets, data)}')
    payload = matcher.report(data)
    payload['inputs'] = inputs
    if reference_data is not None:
        payload['reference_sha256'] = hashlib.sha256(reference_data).hexdigest()

    named = sum(1 for t in targets if t in matcher.pairs or (t in data and data[t] and
                                                             matcher.native.name_at(data[t][0])[0]))
    payload['stats'].update({'kext_targets': len(targets), 'kext_targets_named': named,
                             'data_votes_split': split})
    stats = payload['stats']
    print(f"functions: {stats['functions_matched']}/{stats['functions_original']} "
          f"({', '.join(f'{v} {k}' for k, v in sorted(stats['functions_by_method'].items()))})")
    print(f"data: {stats['data_matched']} ({', '.join(f'{v} {k}' for k, v in sorted(stats['data_by_method'].items())) or 'none'})")
    print(f"kext-facing targets named: {named}/{len(targets)}")
    print(f"conflicts: {stats['conflicts'] or 'none'}")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kernelcache', help='decompressed MH_FILESET kernelcache')
    parser.add_argument('native', help='native arm64e kernel with symbols')
    parser.add_argument('--entry', default='com.apple.kernel', help='fileset entry to pair')
    parser.add_argument('--out', help='write the pairing as JSON to this path')
    parser.add_argument('--max-rounds', type=int, default=40, help='call graph propagation rounds')
    parser.add_argument('--reference-kernel', type=Path, help='additional symbol-bearing kernel for unique code matches')
    args = parser.parse_args()
    payload = match_images(Path(args.kernelcache).read_bytes(), Path(args.native).read_bytes(),
                           args.entry, args.max_rounds,
                           args.reference_kernel.read_bytes() if args.reference_kernel else None)
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=1))
        print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
