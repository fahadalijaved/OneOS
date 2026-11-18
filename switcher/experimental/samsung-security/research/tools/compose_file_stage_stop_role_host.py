"""Derive the unselected host's exact Prepare-only Stop role decoder."""

import re

from build_tree_retained_controller import edit
from run_guest_tree_install_transport import load_io, pinned


CONTROL = 'RetainedHostNativeControlV2.java'
BINDING = 'PreparedRetainedHostNativeBindingV2.java'
SOURCES = {
    CONTROL: ('out/file-stage-early-exit-source/r-3050eec6/' + CONTROL,
              'bfd3d0c7a738cde5cf7ab091bac44c52eab9a87155d8786941f16af23d4cdeb8'),
    BINDING: ('out/file-stage-readiness-build/r-98658bf067/host/src/' + BINDING,
              'd13313a265195b0414c5a7f2afa5900dd0f1ddfa95cc5ddc38728cf55e91f469'),
}


def derive(controller_sha256, controller_bytes):
    """Return both sources for one caller-selected, reviewed successor pin."""
    if (type(controller_sha256) is not str or re.fullmatch(r'[0-9a-f]{64}', controller_sha256) is None
            or type(controller_bytes) is not int or not 1 <= controller_bytes <= 2 * 1024 * 1024):
        raise ValueError('Invalid Stop role controller digest or extent')
    io = load_io()
    control = pinned(io, *SOURCES[CONTROL], 32 * 1024)
    binding = pinned(io, *SOURCES[BINDING], 64 * 1024)
    return {
        CONTROL: edit(control, (
            ('    private final String offeredName;\n',
             '    private final String offeredName;\n'
             '    private final boolean stopRoleProfile;\n'),
            ('            int pidFromItsActualCallback, String nameFromItsActualCallback) {\n'
             '        owner = actualOwner;\n'
             '        offeredPid = pidFromItsActualCallback;\n'
             '        offeredName = nameFromItsActualCallback;\n',
             '            int pidFromItsActualCallback, String nameFromItsActualCallback,\n'
             '            HostRootLinkProfileV2 loadedProfile) {\n'
             '        owner = actualOwner;\n'
             '        offeredPid = pidFromItsActualCallback;\n'
             '        offeredName = nameFromItsActualCallback;\n'
             f'        stopRoleProfile = "{controller_sha256}".equals(loadedProfile.nativeSha256())\n'
             f'                && loadedProfile.nativeBytes() == {controller_bytes}L;\n'),
            ('                ViewState observed = readViewState(response, next);\n',
             '                RetainedStopRolePayload payload = RetainedStopRolePayload.decode(\n'
             '                        response, next, kind, offeredPid, stopRoleProfile);\n'
             '                PrepareRole role = payload == null ? null : new PrepareRole(next, payload);\n'
             '                ViewState observed = readViewState(response);\n'),
            ('                synchronized (lock) {\n'
             '                    retainViewState(observed);\n'
             '                    if (view != null) {\n'
             '                        require(viewCommand == view, "Private view command owner changed");\n'
             '                        view.response = observed;\n',
             '                synchronized (lock) {\n'
             '                    if (role != null) {\n'
             '                        require(view != null && view == viewPreparation && view == viewCommand\n'
             '                                && view.stopRole == null, "Stop role preparation owner changed");\n'
             '                    }\n'
             '                    retainViewState(observed);\n'
             '                    if (view != null) {\n'
             '                        require(viewCommand == view, "Private view command owner changed");\n'
             '                        view.response = observed;\n'
             '                        if (role != null) view.stopRole = role;\n'),
            ('''    private ViewState readViewState(byte[] response, long sequence) throws Throwable {
        RetainedHostControlProtocol.check(response, RetainedHostControlProtocol.VIEW_STATE, sequence,
                RetainedHostControlProtocol.ADMISSION_CLOSED);
        long state = RetainedHostControlProtocol.readU32(response, 16);
        long observed = RetainedHostControlProtocol.readU32(response, 20);
        require(state <= 6 && observed <= 1, "Private view metadata differs");
        long namespace = readU64(response, 24), data = readU64(response, 32), mirror = readU64(response, 40);
        require(observed != 0 || (namespace == 0 && data == 0 && mirror == 0), "Unobserved private view carries values");
        RetainedHostControlProtocol.zeroTail(response, 48);
        return new ViewState((int) state, observed == 1, namespace, data, mirror);
    }
''',
             '''    // Called only after the exact response header and tail are validated.
    private ViewState readViewState(byte[] response) {
        long state = RetainedHostControlProtocol.readU32(response, 16);
        long observed = RetainedHostControlProtocol.readU32(response, 20);
        require(state <= 6 && observed <= 1, "Private view metadata differs");
        long namespace = readU64(response, 24), data = readU64(response, 32), mirror = readU64(response, 40);
        require(observed != 0 || (namespace == 0 && data == 0 && mirror == 0), "Unobserved private view carries values");
        return new ViewState((int) state, observed == 1, namespace, data, mirror);
    }
'''),
            ('    private static final class ViewCommand {\n'
             '        final boolean prepare;\n'
             '        boolean sent, done;\n'
             '        ViewState response;\n',
             '    private static final class PrepareRole {\n'
             '        final long sequence;\n'
             '        final RetainedStopRolePayload child;\n'
             '        PrepareRole(long sequence, RetainedStopRolePayload child) {\n'
             '            this.sequence = sequence;\n'
             '            this.child = child;\n'
             '        }\n'
             '    }\n'
             '    private static final class ViewCommand {\n'
             '        final boolean prepare;\n'
             '        boolean sent, done;\n'
             '        ViewState response;\n'
             '        PrepareRole stopRole;\n'),
        )),
        BINDING: edit(binding, (
            ('        RetainedHostNativeControlV2 created = new RetainedHostNativeControlV2(this, actualOffer.pid, actualOffer.name);\n',
             '        RetainedHostNativeControlV2 created = new RetainedHostNativeControlV2(\n'
             '                this, actualOffer.pid, actualOffer.name, profile);\n'),
        )),
    }
