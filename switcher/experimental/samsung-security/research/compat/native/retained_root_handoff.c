/* First-party direct-host closed-control v2. No guest or authority operation.
 * Default is a no-op. Source preparation only; no Android/native execution. */
#define _GNU_SOURCE 1
#include "retained_root_handoff.h"
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <linux/magic.h>
#include <stdint.h>
#include <string.h>
#include <sys/random.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/un.h>
#include <sys/vfs.h>
#include <time.h>
#include <unistd.h>

#ifndef SYS_pidfd_open
#error "The selected Linux/Android syscall headers must declare SYS_pidfd_open"
#endif

#define ORH_TIMEOUT_MS UINT64_C(30000)
#define ORH_RIGHTS_MAX 16U
#define ORH_NAME_BYTES 42U
#define ORH_CGROUP_FDS 7U
#define ORH_MOUNTINFO_BYTES (512U*1024U)

struct owned_fd {
    int fd;
    unsigned char close_attempted;
    unsigned char close_uncertain;
};
struct controller {
    struct owned_fd image, input, output, listener, peer, self_pidfd;
    struct owned_fd original_stdio[3];
    struct owned_fd cgroup[ORH_CGROUP_FDS];
    unsigned char cgroup_write_attempted, cgroup_write_returned, cgroup_write_uncertain;
    struct owned_fd unexpected[ORH_RIGHTS_MAX];
    DIR *tasks;
    unsigned char tasks_close_uncertain;
    unsigned char local_cutoff;
    unsigned char cleanup_failed;
};
static volatile sig_atomic_t stopping;
static volatile sig_atomic_t host_committed;

static void stop_requested(int number) {
    if (number==SIGHUP && host_committed) return;
    stopping=1;
}
static void fd_init(struct owned_fd *slot) {
    slot->fd=-1; slot->close_attempted=0; slot->close_uncertain=0;
}
static void controller_init(struct controller *c) {
    size_t i;
    memset(c,0,sizeof(*c));
    fd_init(&c->image); fd_init(&c->input); fd_init(&c->output); fd_init(&c->listener);
    fd_init(&c->peer); fd_init(&c->self_pidfd);
    for (i=0;i<3U;++i) fd_init(&c->original_stdio[i]);
    for (i=0;i<ORH_CGROUP_FDS;++i) fd_init(&c->cgroup[i]);
    for (i=0;i<ORH_RIGHTS_MAX;++i) fd_init(&c->unexpected[i]);
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
    for (i=0;i<ORH_CGROUP_FDS;++i) (void)close_owned(c,&c->cgroup[i]);
    for (i=0;i<ORH_RIGHTS_MAX;++i) (void)close_owned(c,&c->unexpected[i]);
    (void)close_owned(c,&c->self_pidfd);
    (void)close_owned(c,&c->listener);
    (void)close_owned(c,&c->peer);
    (void)close_owned(c,&c->input);
    (void)close_owned(c,&c->output);
    for (i=0;i<3U;++i) (void)close_owned(c,&c->original_stdio[i]);
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
static int adopt_stdio(struct controller *c) {
    int i;
    for (i=0;i<3;++i) {
        if (fcntl(i,F_GETFD)<0) return -1;
        c->original_stdio[i].fd=i;
    }
    return 0;
}
static int establish_session(void) {
    pid_t self=getpid();
    if (self<=0) return -1;
    if (getsid(0)!=self || getpgrp()!=self) {
        if (setsid()!=self) return -1; /* no fork or shell-detach fallback */
    }
    return getsid(0)==self && getpgrp()==self?0:-1;
}
static int clear_parent_death(void) {
    int actual=-1;
    if (prctl(PR_SET_PDEATHSIG,0,0,0,0)<0 ||
        prctl(PR_GET_PDEATHSIG,&actual,0,0,0)<0 || actual!=0) return -1;
    return 0;
}
static int now_ms(uint64_t *value);
static int before_deadline(uint64_t deadline) {
    uint64_t now;
    return !stopping && now_ms(&now)==0 && now<deadline?0:-1;
}
/* One exact self-only cgroup2 profile. Namespace-relative '/' alone is not
 * accepted: self/init cgroup namespace objects and the opened mount root are
 * bound first. No arbitrary PID/path, process-tree migration or restore exists. */
static int cgroup_read(struct controller *c,size_t slot,const char *path,
        char *buffer,size_t capacity,size_t *used,uint64_t deadline) {
    size_t count=0;
    c->cgroup[slot].fd=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);
    if (c->cgroup[slot].fd<0) return -1;
    while (count<capacity) {
        ssize_t amount;
        if (before_deadline(deadline)<0) return -1;
        amount=read(c->cgroup[slot].fd,buffer+count,capacity-count);
        if (amount<0 && (errno==EINTR || errno==EAGAIN)) continue;
        if (amount<0) return -1;
        if (!amount) {
            if (memchr(buffer,'\0',count)) return -1;
            buffer[count]='\0';*used=count;return 0;
        }
        count+=(size_t)amount;
    }
    return -1; /* a full buffer does not establish EOF */
}
static int decimal_span(const char *start,const char *end,uint64_t *value) {
    uint64_t n=0;
    if (start==end) return -1;
    for (;start<end;++start) {
        unsigned digit;
        if (*start<'0' || *start>'9') return -1;
        digit=(unsigned)(*start-'0');
        if (n>(UINT64_MAX-digit)/10U) return -1;
        n=n*10U+digit;
    }
    *value=n;return 0;
}
static int cgroup_mount_id(struct controller *c,uint64_t *id,uint64_t deadline) {
    char path[64],buffer[2049];
    char *line,*next;
    size_t count;
    unsigned matches=0;
    int length=snprintf(path,sizeof(path),"/proc/self/fdinfo/%d",c->cgroup[2].fd);
    if (length<=0 || (size_t)length>=sizeof(path) ||
        cgroup_read(c,4U,path,buffer,sizeof(buffer)-1U,&count,deadline)<0) return -1;
    for (line=buffer;*line;line=next) {
        char *end=strchr(line,'\n');
        if (!end) return -1;
        next=end+1;
        if ((size_t)(end-line)>=7U && !memcmp(line,"mnt_id:",7U)) {
            char *first=line+7;
            while (first<end && (*first==' ' || *first=='\t')) ++first;
            if (++matches!=1U || decimal_span(first,end,id)<0 || !*id) return -1;
        }
    }
    return matches==1U?0:-1;
}
static int cgroup_mount_root(struct controller *c,uint64_t id,uint64_t deadline) {
    static char buffer[ORH_MOUNTINFO_BYTES+1U];
    char *line,*next;
    size_t count;
    unsigned matched=0;
    if (cgroup_read(c,5U,"/proc/self/mountinfo",buffer,
            ORH_MOUNTINFO_BYTES,&count,deadline)<0) return -1;
    for (line=buffer;*line;line=next) {
        char *end=strchr(line,'\n'),*space,*token,*state=NULL;
        uint64_t actual;
        unsigned field;
        if (!end) return -1;
        next=end+1;space=memchr(line,' ',(size_t)(end-line));
        if (!space || decimal_span(line,space,&actual)<0) return -1;
        if (actual!=id) continue;
        if (++matched!=1U) return -1;
        *end='\0';token=strtok_r(line," ",&state);
        for (field=0;field<6U;++field) {
            if (!token || (field==3U && strcmp(token,"/")) ||
                (field==4U && strcmp(token,"/sys/fs/cgroup"))) return -1;
            token=strtok_r(NULL," ",&state);
        }
        while (token && strcmp(token,"-")) token=strtok_r(NULL," ",&state);
        if (!token || !(token=strtok_r(NULL," ",&state)) || strcmp(token,"cgroup2")) return -1;
    }
    return matched==1U?0:-1;
}
static int same_node(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev && a->st_ino==b->st_ino;
}
static int place_self_root_cgroup(struct controller *c,uint64_t deadline) {
    struct stat self_ns,init_ns,live,root,procs;
    struct statfs filesystem;
    char membership[65];
    uint64_t mount_id;
    size_t count,i;
    ssize_t wrote;
    int failed=0;
    /* Proc namespace links are intentionally followed to actual namespace FDs. */
    c->cgroup[0].fd=open("/proc/self/ns/cgroup",O_RDONLY|O_CLOEXEC);
    if (c->cgroup[0].fd<0) return -1;
    c->cgroup[1].fd=open("/proc/1/ns/cgroup",O_RDONLY|O_CLOEXEC);
    if (c->cgroup[1].fd<0 || fstat(c->cgroup[0].fd,&self_ns)<0 ||
        fstat(c->cgroup[1].fd,&init_ns)<0 || !same_node(&self_ns,&init_ns)) return -1;
    c->cgroup[2].fd=open("/sys/fs/cgroup",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (c->cgroup[2].fd<0 || fstat(c->cgroup[2].fd,&root)<0 || !S_ISDIR(root.st_mode) ||
        fstatfs(c->cgroup[2].fd,&filesystem)<0 ||
        (unsigned long)filesystem.f_type!=(unsigned long)CGROUP2_SUPER_MAGIC ||
        cgroup_mount_id(c,&mount_id,deadline)<0 || cgroup_mount_root(c,mount_id,deadline)<0) return -1;
    c->cgroup[3].fd=openat(c->cgroup[2].fd,"cgroup.procs",O_WRONLY|O_NOFOLLOW|O_CLOEXEC);
    if (c->cgroup[3].fd<0 || fstat(c->cgroup[3].fd,&procs)<0 || !S_ISREG(procs.st_mode) ||
        procs.st_dev!=root.st_dev || fstatfs(c->cgroup[3].fd,&filesystem)<0 ||
        (unsigned long)filesystem.f_type!=(unsigned long)CGROUP2_SUPER_MAGIC ||
        before_deadline(deadline)<0) return -1;
    c->cgroup_write_attempted=1; /* a failed/short write may already have moved self */
    wrote=write(c->cgroup[3].fd,"0\n",2U);
    if (wrote!=2) { c->cgroup_write_uncertain=1;return -1; }
    c->cgroup_write_returned=1;
    if (cgroup_read(c,6U,"/proc/self/cgroup",membership,sizeof(membership)-1U,
            &count,deadline)<0 || count!=5U || memcmp(membership,"0::/\n",5U) ||
        stat("/proc/self/ns/cgroup",&live)<0 || !same_node(&self_ns,&live) ||
        stat("/proc/1/ns/cgroup",&live)<0 || !same_node(&init_ns,&live) ||
        fstat(c->cgroup[2].fd,&live)<0 || !same_node(&root,&live) ||
        before_deadline(deadline)<0) return -1;
    for (i=0;i<ORH_CGROUP_FDS;++i) if (close_owned(c,&c->cgroup[i])<0) failed=1;
    /* No OFFER follows a placement/readback/close uncertainty. No rollback or
     * kernel/root-manager/process-kill immunity is inferred from this profile. */
    return failed?-1:0;
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
    if (stopping || now_ms(&now)<0 || now>UINT64_MAX-ORH_TIMEOUT_MS) return -1;
    *deadline=now+ORH_TIMEOUT_MS; return 0;
}
/* One absolute deadline per whole handshake/frame, not per byte or retry. */
static int app_alive(struct controller *c) {
    struct pollfd p;
    int result;
    p.fd=c->input.fd; p.events=POLLIN; p.revents=0;
    do { result=poll(&p,1,0); } while (result<0 && errno==EINTR && !stopping);
    /* No app data follows INIT. Readability, EOF or any error cuts precommit off. */
    return result==0 && !stopping?0:-1;
}
static int wait_fd(struct controller *c,int fd,short events,uint64_t deadline,int watch_app) {
    struct pollfd p[2];
    for (;;) {
        uint64_t now,remaining;
        int result,delay;
        nfds_t count=watch_app && !host_committed?2U:1U;
        if (stopping || now_ms(&now)<0 || now>=deadline) return -1;
        remaining=deadline-now; delay=(int)(remaining>250U?250U:remaining);
        memset(p,0,sizeof(p)); p[0].fd=fd; p[0].events=events;
        if (count==2U) { p[1].fd=c->input.fd; p[1].events=POLLIN; }
        result=poll(p,count,delay);
        if (result<0) { if (errno==EINTR) continue; return -1; }
        if (!result) continue;
        if (count==2U && p[1].revents) return -1;
        if (p[0].revents&POLLNVAL) return -1;
        if (p[0].revents&events) return 0;
        if (p[0].revents&(POLLERR|POLLHUP)) return -1;
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
    memset(frame,0,ORH_FRAME_BYTES);
    frame[0]=ORH_MAGIC_0; frame[1]=ORH_MAGIC_1;
    frame[2]=ORH_MAGIC_2; frame[3]=ORH_MAGIC_3;
    write16(frame+4,ORH_VERSION); write16(frame+6,kind);
    write32(frame+8,sequence); write32(frame+12,status);
}
static int header_is(const unsigned char *frame,uint16_t kind,
        uint32_t sequence,uint32_t status) {
    return frame[0]==ORH_MAGIC_0 && frame[1]==ORH_MAGIC_1 &&
        frame[2]==ORH_MAGIC_2 && frame[3]==ORH_MAGIC_3 &&
        read16(frame+4)==ORH_VERSION && read16(frame+6)==kind &&
        read32(frame+8)==sequence && read32(frame+12)==status;
}
static int pipe_read_frame(struct controller *c,int fd,unsigned char *frame,uint64_t deadline) {
    size_t offset=0;
    while (offset<ORH_FRAME_BYTES) {
        ssize_t count;
        if (wait_fd(c,fd,POLLIN,deadline,0)<0) return -1;
        count=read(fd,frame+offset,ORH_FRAME_BYTES-offset);
        if (count<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK)) continue;
        if (count<=0) return -1;
        offset+=(size_t)count;
    }
    return 0;
}
static int write_frame(struct controller *c,int fd,const unsigned char *frame,uint64_t deadline,int socket_fd) {
    size_t offset=0;
    while (offset<ORH_FRAME_BYTES) {
        ssize_t count;
        if (wait_fd(c,fd,POLLOUT,deadline,1)<0) return -1;
        count=socket_fd?send(fd,frame+offset,ORH_FRAME_BYTES-offset,MSG_NOSIGNAL|MSG_DONTWAIT):
            write(fd,frame+offset,ORH_FRAME_BYTES-offset);
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
            /* The control buffer holds at most ORH_RIGHTS_MAX integers.
             * Kernel framing supplies valid descriptors, not peer integers. */
            if (used>=ORH_RIGHTS_MAX) { invalid=1; break; }
            c->unexpected[used++].fd=acquired;
        }
        invalid=1; /* no incoming ancillary of any kind is part of the protocol */
    }
    return invalid || used || message->msg_controllen ? -1:0;
}
static int socket_read_frame(struct controller *c,unsigned char *frame,uint64_t deadline) {
    size_t offset=0;
    while (offset<ORH_FRAME_BYTES) {
        union {
            struct cmsghdr alignment;
            unsigned char bytes[CMSG_SPACE(ORH_RIGHTS_MAX*sizeof(int))];
        } control;
        struct iovec vector;
        struct msghdr message;
        ssize_t count;
        if (wait_fd(c,c->peer.fd,POLLIN,deadline,1)<0) return -1;
        memset(&message,0,sizeof(message)); memset(&control,0,sizeof(control));
        vector.iov_base=frame+offset; vector.iov_len=ORH_FRAME_BYTES-offset;
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
    memcpy(name,"oneos.orh.",10U);
    for (i=0;i<sizeof(random_bytes);++i) {
        name[10U+2U*i]=hex[random_bytes[i]>>4];
        name[11U+2U*i]=hex[random_bytes[i]&15U];
    }
    name[ORH_NAME_BYTES]='\0'; return 0;
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
    memcpy(address.sun_path+1,name,ORH_NAME_BYTES);
    size=(socklen_t)(offsetof(struct sockaddr_un,sun_path)+1U+ORH_NAME_BYTES);
    if (bind(c->listener.fd,(struct sockaddr *)&address,size)<0 ||
        listen(c->listener.fd,1)<0) return -1;
    return 0;
}
static int accept_peer(struct controller *c,uint32_t pid,uint32_t uid,uint64_t deadline) {
    struct ucred credentials;
    socklen_t count=sizeof(credentials);
    for (;;) {
        if (wait_fd(c,c->listener.fd,POLLIN,deadline,1)<0) return -1;
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
    unsigned char frame[ORH_FRAME_BYTES];
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
    make_frame(frame,ORH_IDENTITY,0,ORH_ADMISSION_CLOSED);
    write32(frame+ORH_PAYLOAD_OFFSET,self);
    memset(&message,0,sizeof(message)); memset(&control,0,sizeof(control));
    vector.iov_base=frame; vector.iov_len=sizeof(frame);
    message.msg_iov=&vector; message.msg_iovlen=1;
    message.msg_control=control.bytes; message.msg_controllen=sizeof(control.bytes);
    header=CMSG_FIRSTHDR(&message); header->cmsg_level=SOL_SOCKET;
    header->cmsg_type=SCM_RIGHTS; header->cmsg_len=CMSG_LEN(sizeof(int));
    memcpy(CMSG_DATA(header),&c->self_pidfd.fd,sizeof(int));
    for (;;) {
        if (wait_fd(c,c->peer.fd,POLLOUT,deadline,1)<0) return -1;
        count=sendmsg(c->peer.fd,&message,MSG_NOSIGNAL|MSG_DONTWAIT);
        if (count<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK)) continue;
        if (count<=0) return -1;
        break;
    }
    /* A positive partial send has already sent the ancillary. Never resend it. */
    offset=(size_t)count;
    while (offset<sizeof(frame)) {
        if (wait_fd(c,c->peer.fd,POLLOUT,deadline,1)<0) return -1;
        count=send(c->peer.fd,frame+offset,sizeof(frame)-offset,MSG_NOSIGNAL|MSG_DONTWAIT);
        if (count<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK)) continue;
        if (count<=0) return -1;
        offset+=(size_t)count;
    }
    return 0;
}
static int retire_app_stdio(struct controller *c) {
    size_t i;
    int failed=0;
    if (close_owned(c,&c->input)<0) failed=1;
    if (close_owned(c,&c->output)<0) failed=1;
    for (i=0;i<3U;++i) if (close_owned(c,&c->original_stdio[i])<0) failed=1;
    return failed?-1:0;
}
static int commit_host(struct controller *c,uint64_t deadline) {
    sigset_t block,old,pending;
    uint64_t now;
    int admitted=0;
    if (sigemptyset(&block)<0 || sigaddset(&block,SIGHUP)<0 ||
        sigaddset(&block,SIGINT)<0 || sigaddset(&block,SIGTERM)<0 ||
        sigprocmask(SIG_BLOCK,&block,&old)<0) return -1;
    if (!stopping && now_ms(&now)==0 && now<deadline && app_alive(c)==0 &&
        sigpending(&pending)==0 && !sigismember(&pending,SIGHUP) &&
        !sigismember(&pending,SIGINT) && !sigismember(&pending,SIGTERM)) {
        /* This userspace latch follows the last observed app/signal check.
         * It is not an atomic global observation of process/channel death. */
        host_committed=1; admitted=1;
    }
    if (sigprocmask(SIG_SETMASK,&old,NULL)<0) { c->cleanup_failed=1;return -1; }
    if (!admitted || stopping) return -1;
    /* Never revoke commitment or regain app command authority after this point.
     * No acknowledgement precedes actual inherited/duplicated stdio retirement. */
    return retire_app_stdio(c);
}
static int associate_host(struct controller *c,uint32_t pid,uint32_t uid,uint32_t self,uint64_t deadline) {
    unsigned char frame[ORH_FRAME_BYTES];
    if (accept_peer(c,pid,uid,deadline)<0 || close_owned(c,&c->listener)<0 ||
        send_identity(c,self,deadline)<0 || socket_read_frame(c,frame,deadline)<0 ||
        !header_is(frame,ORH_COMMIT,1,ORH_REQUEST) ||
        !zero_bytes(frame+ORH_PAYLOAD_OFFSET,ORH_FRAME_BYTES-ORH_PAYLOAD_OFFSET) ||
        commit_host(c,deadline)<0) return -1;
    make_frame(frame,ORH_COMMITTED,1,ORH_ADMISSION_CLOSED);
    return write_frame(c,c->peer.fd,frame,deadline,1);
}
static int serve(struct controller *c) {
    unsigned char frame[ORH_FRAME_BYTES];
    uint32_t next=2;
    for (;;) {
        uint64_t deadline;
        uint16_t kind;
        if (wait_request(c->peer.fd)<0 || new_deadline(&deadline)<0 ||
            socket_read_frame(c,frame,deadline)<0) return -1;
        kind=read16(frame+6);
        if ((kind!=ORH_PING && kind!=ORH_CLOSE) ||
            !header_is(frame,kind,next,ORH_REQUEST) ||
            !zero_bytes(frame+ORH_PAYLOAD_OFFSET,ORH_FRAME_BYTES-ORH_PAYLOAD_OFFSET)) return -1;
        if (kind==ORH_CLOSE) {
            c->local_cutoff=1;
            /* No guest/host operation ever existed. Retire the local listener
             * and self copy first. The actual control peer still exists while
             * writing ACK; ACK does NOT promise FD cleanup or native exit. */
            if (close_owned(c,&c->listener)<0 || close_owned(c,&c->self_pidfd)<0) return -1;
            make_frame(frame,ORH_CLOSED,next,ORH_LOCAL_CLOSED);
            return write_frame(c,c->peer.fd,frame,deadline,1);
        }
        if (next==UINT32_MAX || c->local_cutoff) return -1;
        make_frame(frame,ORH_PONG,next,ORH_ADMISSION_CLOSED);
        if (write_frame(c,c->peer.fd,frame,deadline,1)<0) return -1;
        ++next;
    }
}
int main(int argc,char **argv) {
    struct controller owner;
    unsigned char frame[ORH_FRAME_BYTES];
    char name[ORH_NAME_BYTES+1U];
    uint64_t deadline;
    uint32_t caller_pid,caller_uid,self;
    int result=2;
    if (argc==1) return 0; /* no signals, descriptors, output or root effects */
    if (argc!=2 || strcmp(argv[1],"--host-control-v2")) return 2;
    controller_init(&owner);
    if (getuid()!=0 || geteuid()!=0 || adopt_stdio(&owner)<0 ||
        consume_image(&owner)<0 || one_thread(&owner)<0 || install_signals()<0 ||
        establish_session()<0 || clear_parent_death()<0 || new_deadline(&deadline)<0 ||
        place_self_root_cgroup(&owner,deadline)<0) goto done;
    owner.input.fd=fcntl(STDIN_FILENO,F_DUPFD_CLOEXEC,3);
    if (owner.input.fd<0) goto done;
    owner.output.fd=fcntl(STDOUT_FILENO,F_DUPFD_CLOEXEC,3);
    if (owner.output.fd<0 || nonblocking(owner.input.fd)<0 ||
        nonblocking(owner.output.fd)<0) goto done;
    if (pipe_read_frame(&owner,owner.input.fd,frame,deadline)<0 ||
        !header_is(frame,ORH_INIT,0,ORH_REQUEST) ||
        !zero_bytes(frame+ORH_PAYLOAD_OFFSET+8U,ORH_FRAME_BYTES-ORH_PAYLOAD_OFFSET-8U)) goto done;
    caller_pid=read32(frame+ORH_PAYLOAD_OFFSET);
    caller_uid=read32(frame+ORH_PAYLOAD_OFFSET+4U);
    if (!caller_pid || caller_pid>(uint32_t)INT_MAX || caller_uid!=1000U) goto done;
    self=(uint32_t)getpid();
    if (!self || self>(uint32_t)INT_MAX || make_listener(&owner,name,deadline)<0) goto done;
    make_frame(frame,ORH_OFFER,0,ORH_ADMISSION_CLOSED);
    write32(frame+ORH_PAYLOAD_OFFSET,self);
    memcpy(frame+ORH_PAYLOAD_OFFSET+4U,name,ORH_NAME_BYTES);
    if (write_frame(&owner,owner.output.fd,frame,deadline,0)<0 ||
        associate_host(&owner,caller_pid,caller_uid,self,deadline)<0 || serve(&owner)<0) goto done;
    result=0;
done:
    cleanup(&owner);
    if (owner.cleanup_failed) result=3;
    return result;
}
