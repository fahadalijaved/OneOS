"""Derive an unselected child-birth getter for the staged file-backed provider."""

import json
from pathlib import Path

from build_tree_retained_controller import edit, require
from run_guest_tree_install_transport import load_io, pinned


BUILD = 'out/tree-retained-controller/r-b40000a8'
BUILD_RECEIPT = (BUILD + '/receipt.json', '22865cbd53a654d217e93db31eff650e0bacc1a94f8681ceee817e1c3ee05e2d')
CONTROLLER = 'out/tree-retained-controller-static-exec/r-20b2ea21'
CONTROLLER_RECEIPT = (CONTROLLER + '/readback-receipt.json',
                      '0b5fd9f057020f14309b4e10013f4ef6109ac737d634a040517025d1df68697a')
CONTROLLER_SHA256 = 'e9cbc1012b4d3afe734f0c050de6c4c1c43b17253e83bb6206e99f4c2d65f891'
SOURCES = {
    'guest_tree_stage_provider.c': (18588, '4a130abe0699e6786fcb9cfc9bf3d9d5192c79095f81813b94b4c7c996938dbd'),
    'guest_tree_stage_provider.h': (2069, '86c4836c8dddab1349da40a182fb0cf9d4c52818bdd66b532cf88297f438e762'),
}


_STOP = '''/* Cut off the same attempt; this only requests its actual child drain. */
int gtsp_request_stop(struct gtsp_owner *owner);
'''
_HEADER = '''#ifdef ONEOS_FILE_TREE_BACKING
/* Read the exact live Partial's child birth from the retained control owner.
 * Refusal clears the output and has no effect on the view or its cutoff. */
int gtsp_observed_child_birth(struct gtsp_owner *owner, struct gtc_child_birth *out);
#endif

'''
_STOP_BODY = '''int gtsp_request_stop(struct gtsp_owner *owner) {
    if (enter_owner(owner) < 0) return -1;
    int result = stop(owner);
    leave();
    return result;
}
'''
_FORWARD = '''#ifdef ONEOS_FILE_TREE_BACKING
int gtsp_observed_child_birth(struct gtsp_owner *owner, struct gtc_child_birth *out) {
    if (!out) return refuse(EINVAL);
    memset(out, 0, sizeof(*out));
    if (enter_owner(owner) < 0) return -1;
    int result;
    if (!owner->armed || owner->cutoff || owner->terminal || !owner->control
            || owner->close_error || owner->stop_error || owner->source_error) {
        result = refuse(EBUSY);
    } else {
        struct gtc_child_birth actual = {0};
        result = gtc_observed_child_birth(owner->control, &actual);
        if (result > 0 || (!result && (actual.pid <= 0 || !actual.start_ticks))) result = refuse(EPROTO);
        if (!result) *out = actual;
    }
    leave();
    return result == 0 ? 0 : -1;
}
#endif

'''
_EDITS = {
    'guest_tree_stage_provider.c': ((_STOP_BODY, _FORWARD + _STOP_BODY),),
    'guest_tree_stage_provider.h': ((_STOP, _HEADER + _STOP),),
}


def derive():
    """Return the exact two derived source buffers without publishing or selecting them."""
    io = load_io()
    build = json.loads(pinned(io, *BUILD_RECEIPT, 64 * 1024), object_pairs_hook=io['unique_object'])
    link = json.loads(pinned(io, *CONTROLLER_RECEIPT, 8192), object_pairs_hook=io['unique_object'])
    executable = link['executable']
    path = CONTROLLER + '/oneos_retained_tree_preparation'
    require(link['status'] == 'PASS_FILE_BACKED_PREPARE_STOP_STATIC_EXEC_LINK_ONLY'
            and link['selected'] is False and link['deviceEligible'] is False and link['targetExecuted'] is False
            and link['predecessorReceipt'] == {'path': BUILD_RECEIPT[0], 'sha256': BUILD_RECEIPT[1]}
            and link['relocatable'] == build['relocatable']
            and (executable['path'], executable['bytes'], executable['sha256']) == (path, 724152, CONTROLLER_SHA256),
            'Unexpected static controller lineage')
    require(len(pinned(io, path, CONTROLLER_SHA256, 724152)) == 724152, 'Incomplete static controller')
    command = build['commands']['guest_tree_stage_provider']
    argv = command['argv']
    require(build['status'] == 'PASS_FILE_BACKED_PREPARE_STOP_STATIC_LINK_ONLY'
            and command['exitCode'] == 0 and '-DONEOS_FILE_TREE_BACKING' in argv
            and Path(argv[-3]) == io['ROOT'] / BUILD / 'source/guest_tree_stage_provider.c',
            'Unexpected file-backed provider compilation')
    result = {}
    for name, (size, digest) in SOURCES.items():
        path = f'{BUILD}/source/{name}'
        require(build['inputs'][str(io['ROOT'] / path)] == digest, f'Unpinned compiled provider input: {name}')
        source = pinned(io, path, digest, size)
        require(len(source) == size, f'Incomplete compiled provider input: {name}')
        result[name] = edit(source, _EDITS[name])
    return result
