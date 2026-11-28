/* First-party, admission-closed root controller. No guest or authority operation.
 * Default invocation is a no-op. This source has not been executed on Android. */
#define _GNU_SOURCE 1
#include "retained_root_session_protocol.h"
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <sys/random.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>

#ifndef SYS_pidfd_open
#error "The selected Linux/Android syscall headers must declare SYS_pidfd_open"
#endif

#define ORS_TIMEOUT_MS UINT64_C(30000)
#define ORS_RIGHTS_MAX 16U
#define ORS_NAME_BYTES 42U

struct owned_fd {
    int fd;
    unsigned char close_attempted;
    unsigned char close_uncertain;
};
struct controller {
    struct owned_fd image, input, output, listener, peer, self_pidfd;
    struct owned_fd unexpected[ORS_RIGHTS_MAX];
    DIR *tasks;
    unsigned char tasks_close_uncertain;
    unsigned char local_cutoff;
    unsigned char cleanup_failed;
};
static volatile sig_atomic_t stopping;

static void stop_requested(int number) { (void)number; stopping=1; }
static void fd_init(struct owned_fd *slot) {
    slot->fd=-1; slot->close_attempted=0; slot->close_uncertain=0;
}
static void controller_init(struct controller *c) {
    size_t i;
    memset(c,0,sizeof(*c));
    fd_init(&c->image); fd_init(&c->input); fd_init(&c->output); fd_init(&c->listener);
    fd_init(&c->peer); fd_init(&c->self_pidfd);
    for (i=0;i<ORS_RIGHTS_MAX;++i) fd_init(&c->unexpected[i]);
}
/* Consume before the actual close. An uncertain close is never retried, even
 * after EINTR: that integer may no longer refer to the owned open description.
 * The private slot retains its disposition until this process exits. */
static int close_owned(struct controller *c,struct owned_fd *slot) {
    if (slot->fd<0 || slot->close_attempted) return slot->close_uncertain?-1:0;
    slot->close_attempted=1;
    if (close(slot->fd)<0) {
        slot->close_uncertain=1; c->cleanup_failed=1; return -1;
    }
    return 0;
}
static int close_tasks(struct controller *c) {
    DIR *actual=c->tasks;
    if (!actual) return c->tasks_close_uncertain?-1:0;
    c->tasks=NULL; /* consumed before closedir; no retry on an uncertain result */
    if (closedir(actual)<0) {
        c->tasks_close_uncertain=1; c->cleanup_failed=1; return -1;
    }
    return 0;
}
static void cleanup(struct controller *c) {
    size_t i;
    c->local_cutoff=1;
    (void)close_tasks(c);
    for (i=0;i<ORS_RIGHTS_MAX;++i) (void)close_owned(c,&c->unexpected[i]);
    (void)close_owned(c,&c->self_pidfd);
    (void)close_owned(c,&c->listener);
    (void)close_owned(c,&c->peer);
    (void)close_owned(c,&c->input);
    (void)close_owned(c,&c->output);
    (void)close_owned(c,&c->image);
}
/* The fixed root command opens and verifies the image, then execs that SAME
 * open description through /proc/self/fd/3. This check is image custody only,
 * not host/source authority. Consume fd3 before acquiring any other descriptor. */
static int consume_image(struct controller *c) {
    struct stat opened,executing;
    c->image.fd=3;
    if (fstat(c->image.fd,&opened)<0 || stat("/proc/self/exe",&executing)<0 ||
        !S_ISREG(opened.st_mode) || !S_ISREG(executing.st_mode) ||
        opened.st_dev!=executing.st_dev || opened.st_ino!=executing.st_ino) return -1;
    return close_owned(c,&c->image);
}
static int install_signals(void) {
    struct sigaction action;
    sigset_t empty;
    memset(&action,0,sizeof(action));
    if (sigemptyset(&action.sa_mask)<0) return -1;
    action.sa_handler=SIG_IGN;
    if (sigaction(SIGPIPE,&action,NULL)<0) return -1;
    action.sa_handler=stop_requested;
    if (sigaction(SIGINT,&action,NULL)<0 ||
        sigaction(SIGTERM,&action,NULL)<0 ||
        sigaction(SIGHUP,&action,NULL)<0) return -1;
    if (sigemptyset(&empty)<0 || sigprocmask(SIG_SETMASK,&empty,NULL)<0) return -1;
    return 0;
}
static int one_thread(struct controller *c) {
    struct dirent *entry;
    unsigned count=0;
    c->tasks=opendir("/proc/self/task"); /* retain before readdir or checks */
    if (!c->tasks) return -1;
    for (;;) {
        const unsigned char *p;
        errno=0; entry=readdir(c->tasks);
        if (!entry) {
            int failed=errno!=0;
            if (close_tasks(c)<0 || failed || count!=1U) return -1;
            return 0;
        }
        if (!strcmp(entry->d_name,".") || !strcmp(entry->d_name,"..")) continue;
        p=(const unsigned char *)entry->d_name;
        if (!*p) return -1;
        for (;*p;++p) if (*p<'0' || *p>'9') return -1;
        if (++count>1U) return -1;
    }
}
static int now_ms(uint64_t *value) {
    struct timespec t;
    if (clock_gettime(CLOCK_BOOTTIME,&t)<0 || t.tv_sec<0 ||
        t.tv_nsec<0 || t.tv_nsec>=1000000000L ||
        (uint64_t)t.tv_sec>(UINT64_MAX-999U)/1000U) return -1;
    *value=(uint64_t)t.tv_sec*1000U+(uint64_t)t.tv_nsec/1000000U;
    return 0;
}
static int new_deadline(uint64_t *deadline) {
    uint64_t now;
    if (stopping || now_ms(&now)<0 || now>UINT64_MAX-ORS_TIMEOUT_MS) return -1;
    *deadline=now+ORS_TIMEOUT_MS; return 0;
}
/* One absolute deadline per whole handshake/frame, not per byte or retry. */
static int wait_fd(int fd,short events,uint64_t deadline) {
    struct pollfd p;
    for (;;) {
        uint64_t now,remaining;
        int result,delay;
        if (stopping || now_ms(&now)<0 || now>=deadline) return -1;
        remaining=deadline-now;
        delay=(int)(remaining>250U?250U:remaining);
        p.fd=fd; p.events=events; p.revents=0;
        result=poll(&p,1,delay);
        if (result<0) { if (errno==EINTR) continue; return -1; }
        if (!result) continue;
        if (p.revents&POLLNVAL) return -1;
        /* Read any queued data even with HUP; exact-frame read still refuses
         * premature EOF. A write to a closed pipe/socket fails in the syscall. */
        if (p.revents&events) return 0;
        if (p.revents&(POLLERR|POLLHUP)) return -1;
    }
}
/* A captured CLOSED-ADMISSION session may remain idle without a heartbeat.
 * No GVI/guest/host operation exists here. Only once input becomes readable
 * does the caller start its bounded complete-frame/reply deadline. Actual peer
 * EOF/HUP or a termination signal cuts off this local controller. */
static int wait_request(int fd) {
    struct pollfd p;
    while (!stopping) {
        int result;
        p.fd=fd; p.events=POLLIN; p.revents=0;
        result=poll(&p,1,250);
        if (result<0) { if (errno==EINTR) continue; return -1; }
        if (!result) continue;
        if (p.revents&POLLNVAL) return -1;
        if (p.revents&POLLIN) return 0;
        if (p.revents&(POLLERR|POLLHUP)) return -1;
    }
    return -1;
}
static int nonblocking(int fd) {
    int flags=fcntl(fd,F_GETFL);
    return flags<0?-1:fcntl(fd,F_SETFL,flags|O_NONBLOCK);
}
static uint16_t read16(const unsigned char *p) {
    return (uint16_t)(((uint16_t)p[0]<<8)|p[1]);
}
static uint32_t read32(const unsigned char *p) {
    return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|
           ((uint32_t)p[2]<<8)|p[3];
}
static void write16(unsigned char *p,uint16_t value) {
    p[0]=(unsigned char)(value>>8); p[1]=(unsigned char)value;
}
static void write32(unsigned char *p,uint32_t value) {
    p[0]=(unsigned char)(value>>24); p[1]=(unsigned char)(value>>16);
    p[2]=(unsigned char)(value>>8); p[3]=(unsigned char)value;
}
static int zero_bytes(const unsigned char *p,size_t count) {
    size_t i;
    for (i=0;i<count;++i) if (p[i]) return 0;
    return 1;
}
static void make_frame(unsigned char *frame,uint16_t kind,
        uint32_t sequence,uint32_t status) {
    memset(frame,0,ORS_FRAME_BYTES);
    frame[0]=ORS_MAGIC_0; frame[1]=ORS_MAGIC_1;
    frame[2]=ORS_MAGIC_2; frame[3]=ORS_MAGIC_3;
    write16(frame+4,ORS_VERSION); write16(frame+6,kind);
    write32(frame+8,sequence); write32(frame+12,status);
}
static int header_is(const unsigned char *frame,uint16_t kind,
        uint32_t sequence,uint32_t status) {
    return frame[0]==ORS_MAGIC_0 && frame[1]==ORS_MAGIC_1 &&
        frame[2]==ORS_MAGIC_2 && frame[3]==ORS_MAGIC_3 &&
        read16(frame+4)==ORS_VERSION && read16(frame+6)==kind &&
        read32(frame+8)==sequence && read32(frame+12)==status;
}
static int pipe_read_frame(int fd,unsigned char *frame,uint64_t deadline) {
    size_t offset=0;
    while (offset<ORS_FRAME_BYTES) {
        ssize_t count;
        if (wait_fd(fd,POLLIN,deadline)<0) return -1;
        count=read(fd,frame+offset,ORS_FRAME_BYTES-offset);
        if (count<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK)) continue;
        if (count<=0) return -1;
        offset+=(size_t)count;
    }
    return 0;
}
static int write_frame(int fd,const unsigned char *frame,uint64_t deadline,int socket_fd) {
    size_t offset=0;
    while (offset<ORS_FRAME_BYTES) {
        ssize_t count;
        if (wait_fd(fd,POLLOUT,deadline)<0) return -1;
        count=socket_fd?send(fd,frame+offset,ORS_FRAME_BYTES-offset,MSG_NOSIGNAL|MSG_DONTWAIT):
            write(fd,frame+offset,ORS_FRAME_BYTES-offset);
        if (count<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK)) continue;
        if (count<=0) return -1;
        offset+=(size_t)count;
    }
    return 0;
}
/* Kernel-created SCM_RIGHTS integers are acquired resources. Store every
 * delivered one before refusing any ancillary-bearing command. MSG_CTRUNC
 * also refuses; Linux closes rights not delivered in the supplied buffer. */
static int adopt_unexpected(struct controller *c,struct msghdr *message) {
    struct cmsghdr *header;
    size_t used=0;
    int invalid=(message->msg_flags&(MSG_CTRUNC|MSG_TRUNC))!=0;
    for (header=CMSG_FIRSTHDR(message);header;header=CMSG_NXTHDR(message,header)) {
        size_t bytes,count,i;
        if (header->cmsg_len<CMSG_LEN(0)) { invalid=1; break; }
        if (header->cmsg_level!=SOL_SOCKET || header->cmsg_type!=SCM_RIGHTS) {
            invalid=1; continue;
        }
        bytes=header->cmsg_len-CMSG_LEN(0); count=bytes/sizeof(int);
        for (i=0;i<count;++i) {
            int acquired;
            memcpy(&acquired,(unsigned char *)CMSG_DATA(header)+i*sizeof(int),sizeof(int));
            /* The control buffer holds at most ORS_RIGHTS_MAX integers.
             * Kernel framing supplies valid descriptors, not peer integers. */
            if (used>=ORS_RIGHTS_MAX) { invalid=1; break; }
            c->unexpected[used++].fd=acquired;
        }
        invalid=1; /* no incoming ancillary of any kind is part of the protocol */
    }
    return invalid || used || message->msg_controllen ? -1:0;
}
static int socket_read_frame(struct controller *c,unsigned char *frame,uint64_t deadline) {
    size_t offset=0;
    while (offset<ORS_FRAME_BYTES) {
        union {
            struct cmsghdr alignment;
            unsigned char bytes[CMSG_SPACE(ORS_RIGHTS_MAX*sizeof(int))];
        } control;
        struct iovec vector;
        struct msghdr message;
        ssize_t count;
        if (wait_fd(c->peer.fd,POLLIN,deadline)<0) return -1;
        memset(&message,0,sizeof(message)); memset(&control,0,sizeof(control));
        vector.iov_base=frame+offset; vector.iov_len=ORS_FRAME_BYTES-offset;
        message.msg_iov=&vector; message.msg_iovlen=1;
        message.msg_control=control.bytes; message.msg_controllen=sizeof(control.bytes);
        count=recvmsg(c->peer.fd,&message,MSG_CMSG_CLOEXEC|MSG_DONTWAIT);
        if (count<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK)) continue;
        if (count<0) return -1;
        if (adopt_unexpected(c,&message)<0 || count==0) return -1;
        offset+=(size_t)count;
    }
    return 0;
}
static int random_name(char *name,uint64_t deadline) {
    static const char hex[]="0123456789abcdef";
    unsigned char random_bytes[16];
    size_t offset=0,i;
    while (offset<sizeof(random_bytes)) {
        uint64_t now;
        ssize_t count;
        if (stopping || now_ms(&now)<0 || now>=deadline) return -1;
        count=getrandom(random_bytes+offset,sizeof(random_bytes)-offset,GRND_NONBLOCK);
        if (count<0 && errno==EINTR) continue;
        if (count<=0) return -1; /* no weak entropy/time/PID fallback */
        offset+=(size_t)count;
    }
    memcpy(name,"oneos.ors.",10U);
    for (i=0;i<sizeof(random_bytes);++i) {
        name[10U+2U*i]=hex[random_bytes[i]>>4];
        name[11U+2U*i]=hex[random_bytes[i]&15U];
    }
    name[ORS_NAME_BYTES]='\0'; return 0;
}
static int make_listener(struct controller *c,char *name,uint64_t deadline) {
    struct sockaddr_un address;
    socklen_t size;
    if (random_name(name,deadline)<0) return -1;
    c->listener.fd=socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC|SOCK_NONBLOCK,0);
    if (c->listener.fd<0) return -1;
    memset(&address,0,sizeof(address)); address.sun_family=AF_UNIX;
    /* sockaddr contains its abstract leading NUL; OFFER contains the printable
     * name only. It is not a pathname and creates no filesystem socket inode. */
    memcpy(address.sun_path+1,name,ORS_NAME_BYTES);
    size=(socklen_t)(offsetof(struct sockaddr_un,sun_path)+1U+ORS_NAME_BYTES);
    if (bind(c->listener.fd,(struct sockaddr *)&address,size)<0 ||
        listen(c->listener.fd,1)<0) return -1;
    return 0;
}
static int accept_peer(struct controller *c,uint32_t pid,uint32_t uid,uint64_t deadline) {
    struct ucred credentials;
    socklen_t count=sizeof(credentials);
    for (;;) {
        if (wait_fd(c->listener.fd,POLLIN,deadline)<0) return -1;
        c->peer.fd=accept4(c->listener.fd,NULL,NULL,SOCK_CLOEXEC|SOCK_NONBLOCK);
        if (c->peer.fd<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK)) continue;
        if (c->peer.fd<0) return -1;
        break;
    }
    memset(&credentials,0,sizeof(credentials));
    if (getsockopt(c->peer.fd,SOL_SOCKET,SO_PEERCRED,&credentials,&count)<0 ||
        count!=sizeof(credentials) || credentials.pid<=0 ||
        (uint32_t)credentials.pid!=pid || (uint32_t)credentials.uid!=uid) return -1;
    /* This compares real kernel peer credentials with the untrusted INIT
     * association. Neither the comparison nor this socket grants host authority. */
    return 0;
}
static int send_identity(struct controller *c,uint32_t self,uint64_t deadline) {
    unsigned char frame[ORS_FRAME_BYTES];
    union {
        struct cmsghdr alignment;
        unsigned char bytes[CMSG_SPACE(sizeof(int))];
    } control;
    struct cmsghdr *header;
    struct iovec vector;
    struct msghdr message;
    ssize_t count;
    size_t offset;
    int descriptor_flags;
    long acquired=syscall(SYS_pidfd_open,getpid(),0U);
    if (acquired<0) return -1;
    c->self_pidfd.fd=(int)acquired; /* acquire before CLOEXEC/other checks */
    descriptor_flags=fcntl(c->self_pidfd.fd,F_GETFD);
    if (acquired>INT_MAX || descriptor_flags<0 || !(descriptor_flags&FD_CLOEXEC)) return -1;
    make_frame(frame,ORS_IDENTITY,0,ORS_ADMISSION_CLOSED);
    write32(frame+ORS_PAYLOAD_OFFSET,self);
    memset(&message,0,sizeof(message)); memset(&control,0,sizeof(control));
    vector.iov_base=frame; vector.iov_len=sizeof(frame);
    message.msg_iov=&vector; message.msg_iovlen=1;
    message.msg_control=control.bytes; message.msg_controllen=sizeof(control.bytes);
    header=CMSG_FIRSTHDR(&message); header->cmsg_level=SOL_SOCKET;
    header->cmsg_type=SCM_RIGHTS; header->cmsg_len=CMSG_LEN(sizeof(int));
    memcpy(CMSG_DATA(header),&c->self_pidfd.fd,sizeof(int));
    for (;;) {
        if (wait_fd(c->peer.fd,POLLOUT,deadline)<0) return -1;
        count=sendmsg(c->peer.fd,&message,MSG_NOSIGNAL|MSG_DONTWAIT);
        if (count<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK)) continue;
        if (count<=0) return -1;
        break;
    }
    /* A positive partial send has already sent the ancillary. Never resend it. */
    offset=(size_t)count;
    while (offset<sizeof(frame)) {
        if (wait_fd(c->peer.fd,POLLOUT,deadline)<0) return -1;
        count=send(c->peer.fd,frame+offset,sizeof(frame)-offset,MSG_NOSIGNAL|MSG_DONTWAIT);
        if (count<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK)) continue;
        if (count<=0) return -1;
        offset+=(size_t)count;
    }
    return 0;
}
static int serve(struct controller *c) {
    unsigned char frame[ORS_FRAME_BYTES];
    uint32_t next=1;
    for (;;) {
        uint64_t deadline;
        uint16_t kind;
        if (wait_request(c->peer.fd)<0 || new_deadline(&deadline)<0 ||
            socket_read_frame(c,frame,deadline)<0) return -1;
        kind=read16(frame+6);
        if ((kind!=ORS_PING && kind!=ORS_CLOSE) ||
            !header_is(frame,kind,next,ORS_REQUEST) ||
            !zero_bytes(frame+ORS_PAYLOAD_OFFSET,ORS_FRAME_BYTES-ORS_PAYLOAD_OFFSET)) return -1;
        if (kind==ORS_CLOSE) {
            c->local_cutoff=1;
            /* No guest/host operation ever existed. Retire the local listener
             * and self copy first. The actual control peer still exists while
             * writing ACK; ACK does NOT promise FD cleanup or native exit. */
            if (close_owned(c,&c->listener)<0 || close_owned(c,&c->self_pidfd)<0) return -1;
            make_frame(frame,ORS_CLOSED,next,ORS_LOCAL_CLOSED);
            return write_frame(c->peer.fd,frame,deadline,1);
        }
        if (next==UINT32_MAX || c->local_cutoff) return -1;
        make_frame(frame,ORS_PONG,next,ORS_ADMISSION_CLOSED);
        if (write_frame(c->peer.fd,frame,deadline,1)<0) return -1;
        ++next;
    }
}
int main(int argc,char **argv) {
    struct controller owner;
    unsigned char frame[ORS_FRAME_BYTES];
    char name[ORS_NAME_BYTES+1U];
    uint64_t deadline;
    uint32_t caller_pid,caller_uid,self;
    int result=2;
    if (argc==1) return 0; /* no signals, descriptors, output or root effects */
    if (argc!=2 || strcmp(argv[1],"--closed-session-v1")) return 2;
    controller_init(&owner);
    if (getuid()!=0 || geteuid()!=0 || consume_image(&owner)<0 || one_thread(&owner)<0 ||
        install_signals()<0 || new_deadline(&deadline)<0) goto done;
    owner.input.fd=fcntl(STDIN_FILENO,F_DUPFD_CLOEXEC,3);
    if (owner.input.fd<0) goto done;
    owner.output.fd=fcntl(STDOUT_FILENO,F_DUPFD_CLOEXEC,3);
    if (owner.output.fd<0 || nonblocking(owner.input.fd)<0 ||
        nonblocking(owner.output.fd)<0) goto done;
    if (pipe_read_frame(owner.input.fd,frame,deadline)<0 ||
        !header_is(frame,ORS_INIT,0,ORS_REQUEST) ||
        !zero_bytes(frame+ORS_PAYLOAD_OFFSET+8U,ORS_FRAME_BYTES-ORS_PAYLOAD_OFFSET-8U)) goto done;
    caller_pid=read32(frame+ORS_PAYLOAD_OFFSET);
    caller_uid=read32(frame+ORS_PAYLOAD_OFFSET+4U);
    if (!caller_pid || caller_pid>(uint32_t)INT_MAX) goto done;
    self=(uint32_t)getpid();
    if (!self || self>(uint32_t)INT_MAX || make_listener(&owner,name,deadline)<0) goto done;
    make_frame(frame,ORS_OFFER,0,ORS_ADMISSION_CLOSED);
    write32(frame+ORS_PAYLOAD_OFFSET,self);
    memcpy(frame+ORS_PAYLOAD_OFFSET+4U,name,ORS_NAME_BYTES);
    if (write_frame(owner.output.fd,frame,deadline,0)<0 ||
        accept_peer(&owner,caller_pid,caller_uid,deadline)<0 ||
        send_identity(&owner,self,deadline)<0 || serve(&owner)<0) goto done;
    result=0;
done:
    cleanup(&owner);
    if (owner.cleanup_failed) result=3;
    return result;
}
