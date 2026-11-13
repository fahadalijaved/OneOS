/* Authored fixed-stage caller only. Default no-op. Never executed in PC prep.
 * open_existing is read-only adoption; begin_view effects child mounts via gvo. */
#define _GNU_SOURCE 1
#include "guest_private_view_inputs.h"
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t stopping;

static void request_stop(int signal_number) {
    (void)signal_number;
    stopping=1; /* no async close, waiter, logging or opaque-owner access */
}
static int elapsed_ms(uint64_t *value) {
    struct timespec t;
    if (clock_gettime(CLOCK_BOOTTIME,&t)<0) return -1;
    if (t.tv_sec<0 || t.tv_nsec<0 || t.tv_nsec>=1000000000L ||
        (uint64_t)t.tv_sec>(UINT64_MAX-999U)/1000U) {
        errno=EOVERFLOW;return -1;
    }
    *value=(uint64_t)t.tv_sec*1000U+(uint64_t)t.tv_nsec/1000000U;
    return 0;
}
/* No output queue or blocking retry. All possible frames are authored and
 * bounded; partial/error writes cancel activity and never prove delivery. */
static int frame(const char *bytes,size_t count) {
    ssize_t written;
    int flags;
    if (!count || count>384U) { errno=E2BIG;return -1; }
    flags=fcntl(STDOUT_FILENO,F_GETFL);
    if (flags<0 || fcntl(STDOUT_FILENO,F_SETFL,flags|O_NONBLOCK)<0) return -1;
    written=write(STDOUT_FILENO,bytes,count);
    if (written!=(ssize_t)count) { if (written>=0) errno=EIO;return -1; }
    return 0;
}
static int fixed_frame(const char *bytes) { return frame(bytes,strlen(bytes)); }
static int observe(const struct gvi_observation *o) {
    char text[384];
    int n=snprintf(text,sizeof(text),
        "{\"event\":\"PARTIAL_FILESYSTEM_HELD\",\"namespace_inode\":%llu,"
        "\"data_group\":%llu,\"mirror_group\":%llu}\n",
        (unsigned long long)o->namespace_inode,(unsigned long long)o->data_group,
        (unsigned long long)o->mirror_group);
    if (n<0 || (size_t)n>=sizeof(text)) { errno=EOVERFLOW;return -1; }
    return frame(text,(size_t)n);
}
/* Any available input, HUP, EOF or invalid descriptor requests shutdown.
 * There is no command parser, permit, heartbeat or second-operation grammar. */
static int control_stop(int timeout_ms) {
    struct pollfd p={STDIN_FILENO,POLLIN,0};
    int result=poll(&p,1,timeout_ms);
    if (result<0) return errno==EINTR ? (stopping?1:0) : 1;
    return result && p.revents ? 1 : 0;
}
static int install_signals(void) {
    struct sigaction sa;
    sigset_t empty;
    memset(&sa,0,sizeof(sa));sigemptyset(&sa.sa_mask);
    /* No other waiter/threads/auto-reaper are created by this standalone main.
     * gvi/gvo additionally enforce their dedicated single-thread profile. */
    sa.sa_handler=SIG_DFL;
    if (sigaction(SIGCHLD,&sa,NULL)<0) return -1;
    sa.sa_handler=SIG_IGN;
    if (sigaction(SIGPIPE,&sa,NULL)<0) return -1;
    sa.sa_handler=request_stop;
    if (sigaction(SIGINT,&sa,NULL)<0 || sigaction(SIGTERM,&sa,NULL)<0 ||
        sigaction(SIGHUP,&sa,NULL)<0) return -1;
    sigemptyset(&empty);
    return sigprocmask(SIG_SETMASK,&empty,NULL);
}
int main(int argc,char **argv) {
    struct gvi_inputs *inputs=NULL;
    struct gvi_observation observation;
    uint64_t now,deadline;
    int result,output_failed=0,hold_reported=0;
    if (argc==1) {
        /* No provider, signal setup or process/view creation on default path. */
        (void)fixed_frame("{\"event\":\"NO_OPERATION\"}\n");
        return 0;
    }
    if (argc!=2 || strcmp(argv[1],"--prepare-fs-view")) return 2;
    if (install_signals()<0 || elapsed_ms(&now)<0 || now>UINT64_MAX-30000U) return 2;
    deadline=now+30000U; /* elapsed-device decision budget, not guaranteed death */
    if (stopping || control_stop(0)) return 2;
    result=gvi_open_existing(&inputs); /* read-only input adoption only */
    if (result!=GVI_OK) {
        output_failed=fixed_frame(result==GVI_NEED_PREPARED_STAGE ?
            "{\"event\":\"NEED_PREPARED_STAGE\"}\n" :
            "{\"event\":\"INPUT_REFUSED\"}\n")<0;
        goto close_owner;
    }
    if (stopping || control_stop(0) || elapsed_ms(&now)<0 || now>=deadline) goto close_owner;
    /* Effectful synchronous call: actual gvo fork/unshare/mount preparation.
     * Signal handling only sets a flag; cleanup cannot reenter this call.
     * Its original gvo receive budget remains unchanged (up to 30s plus kernel
     * scheduling/blocking). Stdin is observed immediately after it returns. */
    result=gvi_begin_view(inputs,&observation);
    if (result!=GVI_OK) {
        output_failed=fixed_frame("{\"event\":\"VIEW_REFUSED\"}\n")<0;
        goto close_owner;
    }
    if (stopping || control_stop(0) || elapsed_ms(&now)<0 || now>=deadline) goto close_owner;
    if (observe(&observation)<0) { output_failed=1;goto close_owner; }
    while (!stopping) {
        int delay;
        if (elapsed_ms(&now)<0 || now>=deadline) break;
        delay=(int)(deadline-now>100U?100U:deadline-now);
        if (control_stop(delay)) break;
    }
close_owner:
    /* inputs can be nonnull even when open or begin failed. Never drop it on
     * an error path. Only known local terminal0 or partial3 authorizes process exit here. */
    if (!inputs) return 2;
    for (;;) {
        result=gvi_close(inputs);
        if (result==GVI_LOCAL_RELEASED_KERNEL_UNCONFIRMED) {
            (void)fixed_frame("{\"event\":\"LOCAL_RELEASED_KERNEL_UNCONFIRMED\"}\n");
            return 3; /* explicit partial terminal, never full cleanup/return0 */
        }
        if (result==GVI_OK) {
            if (fixed_frame("{\"event\":\"REFUSED_NO_OWN_CONFIGURATION_CLOSED\"}\n")<0) output_failed=1;
            return output_failed ? 4 : 2;
        }
        if (!hold_reported) {
            hold_reported=1;
            if (fixed_frame("{\"event\":\"HOLD_UNRESOLVED_OWNER\"}\n")<0) output_failed=1;
        }
        /* Includes permanent close uncertainty. The sole owner stays alive;
         * gvi never retries consumed numeric descriptors. No launch/retry or
         * timeout exit is permitted. A future controller must report HOLD. */
        (void)poll(NULL,0,200);
    }
}
