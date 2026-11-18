"""Exercise the legacy Stop reviewer with in-memory saved records."""

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import file_stage_stop_carrier as native
import review_file_stage_observation as ui
import review_integrated_file_stage_stop as review


def namespace(inode):
    return dict(deviceMajor=0, deviceMinor=1, inode=inode)


def birth(pid):
    return dict(pid=pid, startTicks=pid * 2, pidNamespace=namespace(10))


class IntegratedStopV1Tests(unittest.TestCase):
    def add(self, record):
        locator = f'record:r{len(self.raw)}'
        self.raw[locator] = record
        return dict(savedRelativePath='out/test/raw.json', sha256='e' * 64, recordLocator=locator)

    def read(self, ref):
        return self.raw[ref['recordLocator']]

    def setUp(self):
        self.raw = {}
        attempt = 'a' * 64
        self.cohort = dict(status='MATCHED_LOCAL_COHORT_VERIFIED', pairReceiptSha256='b' * 64,
                           profileSha256='c' * 64, controllerSha256='d' * 64, packages={})

        def event(kind, elapsed, **details):
            return dict(event=kind, elapsedMs=elapsed, attempt=attempt, component=ui.COMPONENT, **details)

        events = [event('prepare_confirmed', 10, dialog=ui.PREPARE),
                  event('status', 20, lines=[ui.PARTIAL, ui.PREPARE_ACK]),
                  event('stop_confirmed', 40, dialog=ui.STOP),
                  event('status', 50, lines=[ui.LOCAL_CLEANUP, ui.PARTIAL, ui.PREPARE_ACK, ui.STOP_ACK])]
        transcript = dict(schema=ui.SCHEMA, cohort=ui.expected_cohort(self.cohort), observations=events)

        mount_view = dict(mountId=2, deviceMajor=0, deviceMinor=1, rootInode=20, filesystemType='proc',
                          pidNamespace=namespace(10), hidePid=0, bypassGid=None)
        self.visibility_ref = self.add(dict(hidePid=0, bypassGid=None))
        proc = mount_view | dict(mountRawRef=self.add(mount_view.copy()), visibilityRawRef=self.visibility_ref)
        context = dict(bootId='01234567-89ab-cdef-0123-456789abcdef', buildFingerprint=review.FINGERPRINT,
                       hostMountNamespace=namespace(11), appBirth=birth(11), systemServerBirth=birth(12),
                       procView=proc, reader=dict(birth=birth(13), uid=0, euid=0, fsuid=0, gid=0, egid=0, fsgid=0,
                                                 groups=[], selinuxContext='u:r:test:s0'))
        baseline = dict(elapsedMs=30, context=context, rawRef=self.add(dict(elapsedMs=30)))
        for role, pid in [('controller', 14), ('child', 15)]:
            process_birth = birth(pid)
            baseline[role] = dict(birth=process_birth,
                                  rawRef=self.add(review.process_birth_line('PID_NAMESPACE', process_birth)))

        def boundary(elapsed, first_probe):
            probes = {}
            for index, role in enumerate(('controller', 'child')):
                pid = baseline[role]['birth']['pid']
                probes[role] = dict(pid=pid, priorBirthRef=baseline[role]['rawRef'],
                                    sampleElapsedMs=first_probe + index, lookup='proc_pid_nofollow', errno=2,
                                    rawRef=self.add(f'ONEOS_STOP_PROC_V1 PID_NAMESPACE DIRECT_ENOENT {pid}'))
            return dict(elapsedMs=elapsed, context=context, probes=probes, rawRef=self.add(dict(elapsedMs=elapsed)))

        processes = dict(attempt=attempt, preStop=baseline, postStart=boundary(60, 61), postEnd=boundary(90, 85))
        mount = dict(mountId=3, deviceMajor=253, deviceMinor=1)

        def node(inode, mode):
            return mount | dict(inode=inode, typeAndMode=mode, uid=0, gid=0)

        carrier_node = dict(node=node(101, 0o100600), links=1, sizeBytes=native._CARRIER_BYTES,
                            mtimeSec=0, mtimeNsec=0, ctimeSec=0, ctimeNsec=0)
        self.publication = mount | dict(inode=101, bytes=carrier_node['sizeBytes'],
                                        mtimeSec=0, mtimeNs=0, ctimeSec=0, ctimeNs=0)

        def samples(path, fd, sequence, item):
            return dict(path=path, fd=fd, openSequence=sequence, statusFlags=0,
                        namedBefore=item, heldBefore=item, namedAfter=item, heldAfter=item)

        def window(elapsed):
            measurement = dict(operation='FS_IOC_MEASURE_VERITY', fd=4, openSequence=2, elapsedMs=elapsed + 1,
                               status=0, algorithm=1, digestBytes=32, digestHex=native._VERITY_DIGEST)
            measurement['rawRef'] = self.add(measurement.copy())
            result = dict(bootId=context['bootId'], hostMountNamespace=context['hostMountNamespace'],
                          ownerBirth=context['reader']['birth'], startElapsedMs=elapsed, endElapsedMs=elapsed + 2,
                          dataMount=mount | dict(mountPoint='/data', filesystemType='f2fs'),
                          stage=samples(native.STAGE, 3, 1, node(100, 0o40700)),
                          carrier=samples(native.STAGE + '/guest.erofs', 4, 2, carrier_node), measurement=measurement)
            result['rawRef'] = self.add(result.copy())
            return result

        continuity = dict(ownerBirth=context['reader']['birth'], throughElapsedMs=82,
                          events=[dict(operation='open', role='stage', fd=3, sequence=1, elapsedMs=22),
                                  dict(operation='open', role='carrier', fd=4, sequence=2, elapsedMs=23)])
        continuity['rawRef'] = self.add(continuity.copy())
        terminal = dict(elapsedUpperMs=51, rawRef=self.add(dict(elapsedUpperMs=51, attempt=attempt,
                                                              lines=events[-1]['lines'])))
        self.doc = dict(schema=review.SCHEMA, transcriptRef=self.add(transcript), terminal=terminal, processes=processes,
                        carrier=dict(attempt=attempt, publication=self.publication, before=window(25), after=window(70),
                                     continuity=continuity))

    def assert_unbound(self):
        self.assertEqual(review.verify_record(self.doc, self.cohort, self.publication, self.read),
                         {'status': 'RECORDED_STOP_EVIDENCE_HELD', 'reason': 'V1_PROCESS_TIMING_AND_VISIBILITY_UNBOUND',
                          'mayExecute': False, 'deviceAcceptance': False})

    def test_matching_normalized_record_lacks_a_bound_raw_schema(self):
        self.assert_unbound()

    def test_raw_visibility_contradicts_normalized_view(self):
        self.read(self.visibility_ref)['hidePid'] = 2
        self.assert_unbound()

    def test_raw_boundary_contradicts_normalized_timing(self):
        post_start = self.doc['processes']['postStart']
        self.read(post_start['rawRef'])['elapsedMs'] = 49
        self.assert_unbound()

    def test_known_probe_mismatch_still_fails(self):
        probe = self.doc['processes']['postStart']['probes']['controller']
        self.raw[probe['rawRef']['recordLocator']] = 'ONEOS_STOP_PROC_V1 PID_NAMESPACE DIRECT_ENOENT 15'
        with self.assertRaisesRegex(ValueError, 'Raw process lookup differs'):
            review.verify_record(self.doc, self.cohort, self.publication, self.read)

    def test_cli_exit_is_held(self):
        output = io.StringIO()
        with (patch.object(review, 'load_io', return_value={'checked_input': lambda *a, **kw: io.StringIO(json.dumps(self.doc)),
                                                          'unique_object': dict}),
              patch.object(review, 'read_completed_stage', return_value=(None, self.publication)),
              patch.object(review, 'integrated_cohort', return_value=self.cohort),
              patch.object(review, 'raw_reader', return_value=self.read), redirect_stdout(output)):
            self.assertEqual(review.main([str(review.CAPTURES / 'r-00000000' / 'observation.json')]), 2)
        self.assertEqual(json.loads(output.getvalue())['reason'], 'V1_PROCESS_TIMING_AND_VISIBILITY_UNBOUND')


if __name__ == '__main__':
    unittest.main()
