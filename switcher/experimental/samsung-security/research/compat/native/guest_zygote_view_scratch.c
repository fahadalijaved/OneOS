#include "guest_zygote_view_scratch.h"

#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

enum { FIRST_RETAINED = 5, PROTECTED_COUNT = 1 + GTR_WITNESSES + GTR_VIEW_RIGHTS };

static int refuse(int error) {
    errno = error;
    return -1;
}

static int distinct_retained_fds(const int *fds, size_t count) {
    for (size_t i = 0; i < count; ++i) {
        if (fds[i] < FIRST_RETAINED) return refuse(EINVAL);
        for (size_t j = 0; j < i; ++j) {
            if (fds[i] == fds[j]) return refuse(EINVAL);
        }
    }
    return 0;
}

int guest_zygote_view_scratch_close(int scratch[GUEST_ZYGOTE_VIEW_SCRATCH_COUNT],
        const struct gtc_child_inputs *input, const struct gtc_child_view *view,
        const struct guest_zygote_view_context *context) {
    if (!scratch || !input || !input->witnesses || !view || !context) return refuse(EINVAL);

    int preserved[PROTECTED_COUNT] = {context->control_fd};
    memcpy(preserved + 1, input->witnesses, GTR_WITNESSES * sizeof(int));
    memcpy(preserved + 1 + GTR_WITNESSES, view->rights, sizeof(view->rights));
    if (distinct_retained_fds(preserved, PROTECTED_COUNT) < 0
            || distinct_retained_fds(scratch, GUEST_ZYGOTE_VIEW_SCRATCH_COUNT) < 0) return -1;

    for (size_t i = 0; i < GUEST_ZYGOTE_VIEW_SCRATCH_COUNT; ++i) {
        for (size_t j = 0; j < PROTECTED_COUNT; ++j) {
            if (scratch[i] == preserved[j]) return refuse(EINVAL);
        }
        int flags = fcntl(scratch[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) return refuse(EPERM);
    }
    for (size_t i = GUEST_ZYGOTE_VIEW_SCRATCH_COUNT; i > 0; --i) {
        int fd = scratch[i - 1];
        scratch[i - 1] = -1;
        if (close(fd) < 0) return -1;
    }
    return 0;
}
