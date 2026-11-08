"""Add the optional child-birth record to one matched native Prepare reply."""

from build_tree_retained_controller import edit
from run_guest_tree_install_transport import load_io, pinned


NAME = 'retained_root_handoff.c'
SOURCE = ('out/tree-retained-controller/r-b40000a8/source/' + NAME,
          '21d6a95c35ac48487840a04297580d95810391fc094d58de86d4305c85bfdb60')

REPLY = """static int reply_view(struct controller *c,uint32_t sequence,uint64_t deadline) {
    unsigned char frame[ORH_FRAME_BYTES];
    make_frame(frame,ORH_VIEW_STATE,sequence,ORH_ADMISSION_CLOSED);
    write32(frame+16,c->view_state);write32(frame+20,c->view_observed);
    if (c->view_observed) {
        write64(frame+24,c->view_observation.namespace_inode);
        write64(frame+32,c->view_observation.data_group);
        write64(frame+40,c->view_observation.mirror_group);
    }
    return write_frame(c,c->peer.fd,frame,deadline,1);
}"""

SUCCESSOR = """static int reply_view_frame(struct controller *c,uint32_t sequence,uint64_t deadline,int prepare_reply) {
    _Static_assert(ORH_FRAME_BYTES==64U,"stop-role trailer frame size");
    unsigned char frame[ORH_FRAME_BYTES];
    make_frame(frame,ORH_VIEW_STATE,sequence,ORH_ADMISSION_CLOSED);
    write32(frame+16,c->view_state);write32(frame+20,c->view_observed);
    if (c->view_observed) {
        write64(frame+24,c->view_observation.namespace_inode);
        write64(frame+32,c->view_observation.data_group);
        write64(frame+40,c->view_observation.mirror_group);
    }
    if (prepare_reply && c->view_state==ORH_VIEW_PARTIAL_OBSERVED && c->view_observed
            && c->view_observation.namespace_inode && c->view && !c->local_cutoff) {
        struct gtc_child_birth child={0};
        int saved=errno;
        if (gtsp_observed_child_birth(c->view,&child)==0 && child.pid>0 && child.pid!=getpid()
                && child.start_ticks>0 && child.start_ticks<=INT64_MAX) {
            write32(frame+48,UINT32_C(0x50535231)); /* PSR1 */
            write32(frame+52,(uint32_t)child.pid);
            write64(frame+56,child.start_ticks);
        }
        errno=saved;
    }
    return write_frame(c,c->peer.fd,frame,deadline,1);
}
static int reply_view(struct controller *c,uint32_t sequence,uint64_t deadline) {
    return reply_view_frame(c,sequence,deadline,0);
}"""

CALL = """                prepared=prepare_view(c,deadline);
            }
            if (reply_view(c,next,deadline)<0) return -1;
            c->next_sequence=++next;"""

ROLE_CALL = """                prepared=prepare_view(c,deadline);
            }
            if (reply_view_frame(c,next,deadline,kind==ORH_VIEW_PREPARE && prepared==0)<0) return -1;
            c->next_sequence=++next;"""


def derive():
    raw = pinned(load_io(), *SOURCE, 64 * 1024)
    return {NAME: edit(raw, ((REPLY, SUCCESSOR), (CALL, ROLE_CALL)))}
