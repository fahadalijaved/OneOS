/* Authored filesystem-resource preparation only. Compile/run separately gated.
 * No OEM/script exec, parent setns/chroot, image authentication, or READY.
 * V3 owns child-only RO image mounts and an empty private dev/socket skeleton. */
#define _GNU_SOURCE 1
#include "guest_private_view_owner.h"
#include "guest_private_view_mountinfo.h"
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/magic.h>
#include <linux/major.h>
#include <linux/loop.h>
#include <linux/fs.h>
#include <linux/nsfs.h>
#include <poll.h>
#include <sched.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define GVO_PATH 1024
#define GVO_MOUNTS 4096
#define GVO_TEXT (2U*1024U*1024U)
#define GVO_RIGHTS 7
#define GVO_MAGIC UINT32_C(0x47564f33)
#define GVO_ROOT "/mnt/gvi/root"
#define GVO_DATA "/data/local/tmp/oneos/data"
enum { W_PARTIAL=1, W_ERROR=2, W_CANCEL=3,W_CONFIG_OK=4,W_CONFIG_ACK=5,
       W_CONFIG_BUSY=6,W_PRECONFIG_ERROR=7,W_CONFIG_UNKNOWN=8 };
enum { L_NONE=0,L_CANDIDATE,L_PENDING,L_PRE_REFUSED,L_BUSY,L_CONFIRMED,L_UNKNOWN };
enum { S_INPUT=1,S_PRIVATE,S_REOPEN,S_CONFIG,S_IMAGE,S_DATA,S_ALIAS,S_MIRROR,
       S_DEV,S_SOCKET,S_READBACK,S_IPC };
enum { R_NAMESPACE=0,R_INHERITED_ROOT,R_GUEST_ROOT,R_DATA,R_MIRROR,R_DEV,R_SOCKET };
enum { O_UNUSED=0,O_STARTING,O_HELD,O_STOPPING,O_HOLD,O_LOST,O_REAPED,O_CLOSED };

struct wire {
    uint32_t magic,version,kind,stage;
    int32_t error,pid;
    uint32_t uid,gid;
    uint64_t namespace_inode,namespace_dev;
    uint64_t mounts[GVO_RIGHTS];
    uint64_t data_group,mirror_group,alias_native,alias_guest;
    uint64_t guest_data_mount,guest_mirror_mount;
    uint64_t image_dev,image_inode,loop_device;
    uint32_t loop_number,loop_flags;
    uint64_t reserved[2];
};
struct gvo_owner {
    int state,ctl,witness[2],held[GVO_RIGHTS],parent_ns,loop_fd,loop_state,partial_terminal;
    struct stat image_stat,loop_stat;
    pid_t child,parent;
    uid_t uid;
    gid_t gid;
    uint64_t parent_ns_inode,parent_ns_dev,deadline,kill_at;
    uint64_t forbidden[GVO_MOUNTS*3];
    size_t forbidden_count;
    int term_sent,kill_sent,reaped,wait_status,close_error;
    char root_path[GVO_PATH],data_path[GVO_PATH];
    struct gvo_observation observation;
};
static struct gvo_owner only_owner;
static int used_owner;
/* Bounded, process-private scratch. Dedicated one-thread profile only. */
static struct gpv_mount_row *mount_rows;
static size_t mount_count;

static int close_cell(int *cell) {
    int fd=*cell;
    *cell=-1; /* consume before close; never retry a potentially reused number */
    return fd<0 ? 0 : close(fd);
}
static void tracked_close_cell(int *first_error,int *cell) {
    int saved=errno;
    if (close_cell(cell)<0 && first_error && !*first_error) *first_error=errno;
    errno=saved; /* cleanup uncertainty is independent of the primary refusal */
}
static void owner_close_cell(struct gvo_owner *o,int *cell) {
    tracked_close_cell(&o->close_error,cell);
}
static int now_ms(uint64_t *value) {
    struct timespec t;
    if (clock_gettime(CLOCK_BOOTTIME,&t)<0 || t.tv_sec<0) return -1;
    *value=(uint64_t)t.tv_sec*1000U+(uint64_t)t.tv_nsec/1000000U;
    return 0;
}
static int read_text(const char *path,char *buffer,size_t capacity) {
    int fd=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    size_t used=0;
    int result=-1,saved=0;
    if (fd<0) return -1;
    while (used<capacity) {
        ssize_t n=read(fd,buffer+used,capacity-used);
        if (n<0) { saved=errno; goto done; }
        if (!n) { buffer[used]=0; result=(int)used; goto done; }
        used+=(size_t)n;
    }
    saved=E2BIG;
done:
    if (close_cell(&fd)<0 && !saved) { saved=errno; result=-1; }
    if (saved) errno=saved;
    return result;
}
static int u64(const char *s,uint64_t *out) {
    uint64_t n=0;
    if (!s || !*s) { errno=EPROTO; return -1; }
    for (;*s;s++) {
        unsigned digit=(unsigned char)*s-'0';
        if (digit>9 || n>(UINT64_MAX-digit)/10U) { errno=EPROTO; return -1; }
        n=n*10U+digit;
    }
    *out=n; return 0;
}
static void mounts_clear(void) {
    free(mount_rows);mount_rows=NULL;mount_count=0;
}
static int mounts_read(const char *path) {
    char *text;
    size_t i,lines=0,capacity;
    int n,result,saved;
    mounts_clear();
    text=(char *)malloc(GVO_TEXT+1U);
    if (!text) return -1;
    n=read_text(path,text,GVO_TEXT);
    if (n<0) { saved=errno;free(text);errno=saved;return -1; }
    for (i=0;i<(size_t)n;i++) if (text[i]=='\n') lines++;
    if (!lines || lines>GVO_MOUNTS) { free(text);errno=E2BIG;return -1; }
    capacity=lines<GVO_MOUNTS?lines+1U:lines;
    if (capacity>SIZE_MAX/sizeof(*mount_rows)) { free(text);errno=EOVERFLOW;return -1; }
    mount_rows=(struct gpv_mount_row *)calloc(capacity,sizeof(*mount_rows));
    if (!mount_rows) { saved=errno;free(text);errno=saved;return -1; }
    result=gpv_parse_mountinfo(text,(size_t)n,mount_rows,capacity,&mount_count);
    free(text); /* parser copies fields; no borrowed input spans survive */
    if (result!=GPV_OK) { mounts_clear();errno=result==GPV_LIMIT?E2BIG:EPROTO;return -1; }
    return 0;
}
static const struct gpv_mount_row *mount_find(uint64_t id) {
    const struct gpv_mount_row *row=gpv_mount_by_id(mount_rows,mount_count,id);
    if (!row) errno=EXDEV;
    return row;
}
static int fd_mount_id(int fd,uint64_t *id) {
    char path[64],text[GPV_FDINFO_MAX_BYTES+1];
    int n,result;
    n=snprintf(path,sizeof(path),"/proc/self/fdinfo/%d",fd);
    if (n<0 || (size_t)n>=sizeof(path)) { errno=EOVERFLOW;return -1; }
    n=read_text(path,text,sizeof(text)-1);
    if (n<0) return -1;
    result=gpv_parse_fdinfo_mnt_id(text,(size_t)n,id);
    if (result!=GPV_OK) { errno=result==GPV_LIMIT?E2BIG:EPROTO;return -1; }
    return 0;
}
static int fd_directory(int fd,struct stat *s) {
    if (fstat(fd,s)<0) return -1;
    if (!S_ISDIR(s->st_mode)) { errno=ENOTDIR; return -1; }
    return 0;
}
static int same_object(int a,int b) {
    struct stat x,y;
    if (fd_directory(a,&x)<0 || fd_directory(b,&y)<0) return -1;
    if (x.st_dev!=y.st_dev || x.st_ino!=y.st_ino) { errno=EXDEV; return -1; }
    return 0;
}
static int fd_member(int fd,uint64_t *id) {
    struct stat s;
    const struct gpv_mount_row *r;
    if (fd_directory(fd,&s)<0 || fd_mount_id(fd,id)<0 || !(r=mount_find(*id))) return -1;
    if ((unsigned)major(s.st_dev)!=r->major || (unsigned)minor(s.st_dev)!=r->minor) { errno=EXDEV; return -1; }
    return 0;
}
static int below(const char *path,const char *parent) {
    size_t n=strlen(parent);
    if (n==1 && parent[0]=='/') return path[0]=='/';
    return !strncmp(path,parent,n) && (path[n]=='/' || path[n]==0);
}
static int walk_at(int root,const char *relative) {
    char copy[GVO_PATH],*p,*part;
    int current=fcntl(root,F_DUPFD_CLOEXEC,3),saved;
    if (current<0) return -1;
    if (strlen(relative)>=sizeof(copy)) { saved=ENAMETOOLONG; goto fail; }
    strcpy(copy,relative);p=copy;
    while ((part=strsep(&p,"/"))!=NULL) {
        int next;
        if (!*part || !strcmp(part,".") || !strcmp(part,"..")) { saved=EINVAL; goto fail; }
        next=openat(current,part,O_PATH|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        if (next<0) { saved=errno; goto fail; }
        if (close_cell(&current)<0) { saved=errno; close_cell(&next); goto fail; }
        current=next;
    }
    return current;
fail:
    close_cell(&current);errno=saved;return -1;
}
static int open_absolute(const char *path) {
    int root=open("/",O_PATH|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC),out,saved;
    if (root<0) return -1;
    if (!strcmp(path,"/")) return root;
    out=walk_at(root,path+1);saved=errno;
    if (close_cell(&root)<0 && out>=0) { saved=errno;close_cell(&out); }
    errno=saved;return out;
}
static int fd_path(int fd,char path[64]) {
    int n=snprintf(path,64,"/proc/self/fd/%d",fd);
    if (n<0 || n>=64) { errno=EOVERFLOW;return -1; }
    return 0;
}
static int bind_fds(int source,int target) {
    char a[64],b[64];
    if (fd_path(source,a)<0 || fd_path(target,b)<0) return -1;
    return mount(a,b,NULL,MS_BIND,NULL);
}
static int shared_fd(int fd) {
    char p[64];
    if (fd_path(fd,p)<0) return -1;
    return mount(NULL,p,NULL,MS_SHARED,NULL);
}
static int forbidden_group(const struct gvo_owner *o,uint64_t group) {
    size_t i;
    if (!group) return 0;
    for (i=0;i<o->forbidden_count;i++) if (o->forbidden[i]==group) return 1;
    return 0;
}
static int private_table(void) {
    size_t i;
    for (i=0;i<mount_count;i++) if (mount_rows[i].shared || mount_rows[i].master || mount_rows[i].propagate) { errno=EXDEV;return -1; }
    return 0;
}
static int pair_check(const struct gvo_owner *o,int a,int b,uint64_t *group) {
    uint64_t x,y;
    const struct gpv_mount_row *ra,*rb;
    if (same_object(a,b)<0 || fd_member(a,&x)<0 || fd_member(b,&y)<0 || x==y) { errno=EXDEV;return -1; }
    ra=mount_find(x);rb=mount_find(y);
    if (!ra || !rb || !ra->shared || ra->shared!=rb->shared || ra->master || rb->master || ra->propagate || rb->propagate || strcmp(ra->root,rb->root) || forbidden_group(o,ra->shared)) { errno=EXDEV;return -1; }
    *group=ra->shared;return 0;
}

static int send_wire(int socket_fd,const struct wire *packet,const int *fds,size_t count) {
    struct iovec iov={(void *)packet,sizeof(*packet)};
    union { struct cmsghdr alignment; unsigned char bytes[CMSG_SPACE(sizeof(int)*GVO_RIGHTS)]; } control;
    struct msghdr msg;
    ssize_t n;
    if (count!=0 && count!=GVO_RIGHTS) { errno=EINVAL;return -1; }
    memset(&msg,0,sizeof(msg));memset(&control,0,sizeof(control));msg.msg_iov=&iov;msg.msg_iovlen=1;
    if (count) {
        struct cmsghdr *c;
        msg.msg_control=control.bytes;msg.msg_controllen=CMSG_SPACE(sizeof(int)*count);
        c=CMSG_FIRSTHDR(&msg);c->cmsg_level=SOL_SOCKET;c->cmsg_type=SCM_RIGHTS;c->cmsg_len=CMSG_LEN(sizeof(int)*count);
        memcpy(CMSG_DATA(c),fds,sizeof(int)*count);
    }
    n=sendmsg(socket_fd,&msg,MSG_NOSIGNAL|MSG_DONTWAIT);
    if (n!=(ssize_t)sizeof(*packet)) { if (n>=0) errno=EPROTO;return -1; }
    return 0;
}
/* Own every returned rights cell before judging the packet. Even a rejected or
 * control-truncated message must close all rights actually delivered to us. */
static int receive_wire(int socket_fd,struct wire *packet,int received[32],size_t *count,
                        pid_t expected_pid,uid_t expected_uid,gid_t expected_gid,int *close_error) {
    union { struct cmsghdr alignment; unsigned char bytes[CMSG_SPACE(sizeof(int)*32)+CMSG_SPACE(sizeof(struct ucred))]; } control;
    struct iovec iov={packet,sizeof(*packet)};
    struct msghdr msg;
    struct cmsghdr *c;
    struct ucred credential;
    int bad=0,rights_messages=0,credential_messages=0;
    ssize_t n;
    size_t i;
    *count=0;memset(packet,0,sizeof(*packet));memset(&msg,0,sizeof(msg));memset(&control,0,sizeof(control));memset(&credential,0,sizeof(credential));
    for (i=0;i<32;i++) received[i]=-1;
    msg.msg_iov=&iov;msg.msg_iovlen=1;msg.msg_control=control.bytes;msg.msg_controllen=sizeof(control.bytes);
    n=recvmsg(socket_fd,&msg,MSG_CMSG_CLOEXEC|MSG_DONTWAIT);
    if (n<0) return -1;
    if (n!=(ssize_t)sizeof(*packet) || (msg.msg_flags&(MSG_TRUNC|MSG_CTRUNC))) bad=1;
    for (c=CMSG_FIRSTHDR(&msg);c;c=CMSG_NXTHDR(&msg,c)) {
        size_t offset=(size_t)((unsigned char *)c-control.bytes),bytes;
        if (offset>msg.msg_controllen || c->cmsg_len<CMSG_LEN(0) || c->cmsg_len>msg.msg_controllen-offset) { bad=1;break; }
        bytes=c->cmsg_len-CMSG_LEN(0);
        if (c->cmsg_level==SOL_SOCKET && c->cmsg_type==SCM_RIGHTS) {
            size_t k;
            rights_messages++;
            if (bytes%sizeof(int)) bad=1;
            for (k=0;k+sizeof(int)<=bytes;k+=sizeof(int)) {
                int fd;
                memcpy(&fd,(unsigned char *)CMSG_DATA(c)+k,sizeof(fd));
                if (*count<32) received[(*count)++]=fd;
                else { tracked_close_cell(close_error,&fd);bad=1; }
            }
        } else if (c->cmsg_level==SOL_SOCKET && c->cmsg_type==SCM_CREDENTIALS) {
            credential_messages++;
            if (bytes!=sizeof(credential)) bad=1;
            else memcpy(&credential,CMSG_DATA(c),sizeof(credential));
        } else bad=1;
    }
    if (credential_messages!=1 || rights_messages>1 || credential.pid!=expected_pid || credential.uid!=expected_uid || credential.gid!=expected_gid) bad=1;
    if (packet->magic!=GVO_MAGIC || packet->version!=3 || packet->pid!=expected_pid || packet->uid!=(uint32_t)expected_uid || packet->gid!=(uint32_t)expected_gid || packet->reserved[0] || packet->reserved[1]) bad=1;
    for (i=0;i<*count;i++) {
        int flags=received[i]<0?-1:fcntl(received[i],F_GETFD);
        if (flags<0 || (flags&FD_CLOEXEC)!=FD_CLOEXEC) bad=1;
    }
    if (bad) {
        for (i=0;i<*count;i++) tracked_close_cell(close_error,&received[i]);
        *count=0;errno=EPROTO;return -1;
    }
    return 0;
}
static void wire_init(struct wire *w,uint32_t kind,uint32_t stage) {
    memset(w,0,sizeof(*w));w->magic=GVO_MAGIC;w->version=3;w->kind=kind;w->stage=stage;
    w->pid=(int32_t)getpid();w->uid=(uint32_t)geteuid();w->gid=(uint32_t)getegid();
}
static int wire_has_no_resources(const struct wire *w) {
    size_t i;
    if (w->namespace_inode || w->namespace_dev || w->data_group || w->mirror_group || w->alias_native || w->alias_guest || w->guest_data_mount || w->guest_mirror_mount) return 0;
    for (i=0;i<GVO_RIGHTS;i++) if (w->mounts[i]) return 0;
    return 1;
}
static int namespace_stat(int fd,struct stat *s) {
    struct statfs fs;
    int type;
    if (fstat(fd,s)<0 || fstatfs(fd,&fs)<0) return -1;
    if ((unsigned long)fs.f_type!=(unsigned long)NSFS_MAGIC) { errno=EXDEV;return -1; }
    type=ioctl(fd,NS_GET_NSTYPE);
    if (type<0) return -1;
    if (type!=CLONE_NEWNS) { errno=EXDEV;return -1; }
    return 0;
}
static int child_still_parented(const struct gvo_owner *o) {
    if (getppid()!=o->parent || geteuid()!=o->uid || getegid()!=o->gid) { errno=ECHILD;return -1; }
    return 0;
}
static int close_unlisted(int keep1,int keep2,int keep3,int keep4) {
    DIR *d=opendir("/proc/self/fd");
    struct dirent *e;
    int directory,saved=0;
    if (!d) return -1;
    directory=dirfd(d);
    if (directory<0) saved=errno;
    while (!saved) {
        uint64_t value;
        errno=0;e=readdir(d);
        if (!e) { saved=errno;break; }
        if (e->d_name[0]=='.') continue;
        if (u64(e->d_name,&value)<0 || value>INT_MAX) { saved=EPROTO;break; }
        /* Includes 0..2: closed stdio may have been reused by owned internals. */
        if ((int)value!=directory && (int)value!=keep1 && (int)value!=keep2 && (int)value!=keep3 && (int)value!=keep4) {
            int fd=(int)value;
            if (close_cell(&fd)<0) { saved=errno;break; }
        }
    }
    if (closedir(d)<0 && !saved) saved=errno;
    if (saved) { errno=saved;return -1; }
    return 0;
}
static int source_has_submounts(const char *path) {
    size_t i;
    for (i=0;i<mount_count;i++) if (strcmp(mount_rows[i].point,path) && below(mount_rows[i].point,path)) { errno=EXDEV;return -1; }
    return 0;
}
static int mount_option(const char *options,const char *wanted) {
    size_t n=strlen(wanted);const char *p=options;
    while (*p) {
        const char *end=strchr(p,',');size_t length=end?(size_t)(end-p):strlen(p);
        if (length==n && !memcmp(p,wanted,n)) return 1;
        if (!end) break;
        p=end+1;
    }
    return 0;
}
static int private_root_mount(int fd,const char *locator) {
    uint64_t id;
    const struct gpv_mount_row *r;
    if (fd_member(fd,&id)<0 || !(r=mount_find(id))) return -1;
    if (strcmp(r->point,locator) || strcmp(r->root,"/") || r->shared || r->master || r->propagate) { errno=EXDEV;return -1; }
    return 0;
}
static int same_mount(int a,int b) {
    uint64_t x,y;
    if (fd_mount_id(a,&x)<0 || fd_mount_id(b,&y)<0) return -1;
    if (x!=y) { errno=EXDEV;return -1; }
    return 0;
}

static int dev_directory_profile(int fd,struct stat *s) {
    if (fd_directory(fd,s)<0) return -1;
    if (s->st_uid!=0 || s->st_gid!=0 || (s->st_mode&07777)!=0755) {
        errno=EPERM;return -1;
    }
    return 0;
}
/* Fixed directory shapes only: an empty source/socket or new dev with socket.
 * Open a distinct readable descriptor; fdopendir owns it only after success.
 * Every read/close failure refuses, and parent-side close uncertainty latches. */
static int dev_directory_shape(struct gvo_owner *o,int fd,int with_socket) {
    int readable=-1,saved=0;
    unsigned seen=0,count=0,expected=with_socket?7U:3U;
    DIR *directory=NULL;
    struct dirent *entry;
    readable=openat(fd,".",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (readable<0) return -1;
    if (same_object(readable,fd)<0 || same_mount(readable,fd)<0) {
        saved=errno?errno:EXDEV;goto done;
    }
    directory=fdopendir(readable);
    if (!directory) { saved=errno;goto done; }
    readable=-1;
    for (;;) {
        unsigned bit;
        errno=0;entry=readdir(directory);
        if (!entry) { saved=errno;break; }
        if (++count>(with_socket?3U:2U)) { saved=ENOTEMPTY;break; }
        if (!strcmp(entry->d_name,".")) bit=1U;
        else if (!strcmp(entry->d_name,"..")) bit=2U;
        else if (with_socket && !strcmp(entry->d_name,"socket")) bit=4U;
        else { saved=ENOTEMPTY;break; }
        if (seen&bit) { saved=EPROTO;break; }
        seen|=bit;
    }
    if (!saved && seen!=expected) saved=EPROTO;
done:
    if (directory) {
        if (closedir(directory)<0) {
            int close_errno=errno;
            if (!o->close_error) o->close_error=close_errno;
            if (!saved) saved=close_errno;
        }
    }
    owner_close_cell(o,&readable);
    if (!saved && o->close_error) saved=o->close_error;
    if (saved) { errno=saved;return -1; }
    return 0;
}
/* Uses the caller's actual child mount table (parent reads /proc/owned/mountinfo).
 * Dev root and socket are TWO objects on ONE newly owned private filesystem. */
static int dev_socket_check(struct gvo_owner *o,int guest_root,int data,int mirror,
                            int dev,int socket_dir) {
    struct stat root_stat,data_stat,mirror_stat,dev_stat,socket_stat;
    struct statfs fs;
    const struct gpv_mount_row *root,*row;
    uint64_t root_id,data_id,mirror_id,dev_id,socket_id;
    char expected[GVO_PATH];
    int actual_dev=-1,actual_socket=-1,length,result=-1,saved;
    if (fd_directory(guest_root,&root_stat)<0 || fd_directory(data,&data_stat)<0 ||
        fd_directory(mirror,&mirror_stat)<0 || dev_directory_profile(dev,&dev_stat)<0 ||
        dev_directory_profile(socket_dir,&socket_stat)<0 || fstatfs(dev,&fs)<0 ||
        fd_member(guest_root,&root_id)<0 || fd_member(data,&data_id)<0 ||
        fd_member(mirror,&mirror_id)<0 || fd_member(dev,&dev_id)<0 ||
        fd_member(socket_dir,&socket_id)<0) goto done;
    if ((unsigned long)fs.f_type!=(unsigned long)TMPFS_MAGIC || dev_id!=socket_id ||
        dev_id==root_id || dev_id==data_id || dev_id==mirror_id ||
        dev_stat.st_dev!=socket_stat.st_dev || dev_stat.st_ino==socket_stat.st_ino ||
        dev_stat.st_dev==root_stat.st_dev || dev_stat.st_dev==data_stat.st_dev ||
        dev_stat.st_dev==mirror_stat.st_dev) { errno=EXDEV;goto done; }
    root=mount_find(root_id);row=mount_find(dev_id);
    if (!root || !row) goto done;
    length=snprintf(expected,sizeof(expected),"%s/dev",root->point);
    if (length<0 || (size_t)length>=sizeof(expected)) { errno=EOVERFLOW;goto done; }
    if (strcmp(row->point,expected) || strcmp(row->root,"/") || strcmp(row->type,"tmpfs") ||
        row->shared || row->master || row->propagate ||
        !mount_option(row->options,"rw") || !mount_option(row->super_options,"rw") ||
        !mount_option(row->options,"nosuid") || !mount_option(row->options,"nodev") ||
        !mount_option(row->options,"noexec")) { errno=EXDEV;goto done; }
    /* Single-component no-follow opens avoid borrowing a caller path or opening
     * a replacement root. Compare actual objects/mounts, not packet names. */
    actual_dev=openat(guest_root,"dev",O_PATH|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    actual_socket=openat(dev,"socket",O_PATH|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (actual_dev<0 || actual_socket<0 || same_object(actual_dev,dev)<0 ||
        same_mount(actual_dev,dev)<0 || same_object(actual_socket,socket_dir)<0 ||
        same_mount(actual_socket,socket_dir)<0 || dev_directory_shape(o,dev,1)<0 ||
        dev_directory_shape(o,socket_dir,0)<0) goto done;
    result=0;
done:
    saved=errno;
    owner_close_cell(o,&actual_dev);owner_close_cell(o,&actual_socket);
    if (o->close_error) { errno=o->close_error;return -1; }
    errno=saved;return result;
}

static int no_config_fields(const struct wire *w) {
    return !w->image_dev && !w->image_inode && !w->loop_device && !w->loop_number && !w->loop_flags;
}
static int loop_readback(const struct gvo_owner *o,struct loop_info64 *info) {
    int ro=0;struct stat block;
    memset(info,0,sizeof(*info));
    if (fstat(o->loop_fd,&block)<0 || ioctl(o->loop_fd,LOOP_GET_STATUS64,info)<0 || ioctl(o->loop_fd,BLKROGET,&ro)<0) return -1;
    if (block.st_dev!=o->loop_stat.st_dev || block.st_ino!=o->loop_stat.st_ino ||
        block.st_rdev!=o->loop_stat.st_rdev || !S_ISBLK(block.st_mode) || ro!=1 ||
        (info->lo_flags&(LO_FLAGS_READ_ONLY|LO_FLAGS_AUTOCLEAR))!=(LO_FLAGS_READ_ONLY|LO_FLAGS_AUTOCLEAR) ||
        (info->lo_flags&~(LO_FLAGS_READ_ONLY|LO_FLAGS_AUTOCLEAR|LO_FLAGS_PARTSCAN)) ||
        info->lo_device!=(uint64_t)o->image_stat.st_dev || info->lo_inode!=(uint64_t)o->image_stat.st_ino ||
        info->lo_number!=minor(block.st_rdev) || info->lo_offset || info->lo_sizelimit || info->lo_encrypt_type) { errno=EXDEV;return -1; }
    return 0;
}
static int child_send(const struct gvo_owner *o,int ctl,const struct wire *w) {
    for (;;) {
        uint64_t now;
        if (child_still_parented(o)<0 || now_ms(&now)<0 || now>=o->deadline) { errno=ETIMEDOUT;return -1; }
        if (send_wire(ctl,w,NULL,0)==0) return 0;
        if (errno!=EAGAIN && errno!=EINTR) return -1;
        { struct pollfd p={ctl,POLLOUT,0};(void)poll(&p,1,50); }
    }
}
static int child_configure(const struct gvo_owner *o,int ctl,int image,int *attempted,int *noticed) {
    struct loop_config config;struct loop_info64 info;struct wire packet;
    int result,saved;uint64_t now;
    memset(&config,0,sizeof(config));config.fd=(uint32_t)image;
    config.info.lo_flags=LO_FLAGS_READ_ONLY|LO_FLAGS_AUTOCLEAR;
    *attempted=1;result=ioctl(o->loop_fd,LOOP_CONFIGURE,&config);saved=errno;
    if (result<0) {
        wire_init(&packet,saved==EBUSY?W_CONFIG_BUSY:W_CONFIG_UNKNOWN,S_CONFIG);packet.error=saved?saved:EIO;
        if (child_send(o,ctl,&packet)==0) *noticed=2;
        errno=saved;return -1;
    }
    if (loop_readback(o,&info)<0) return -1; /* committed but not confirmed: UNKNOWN */
    wire_init(&packet,W_CONFIG_OK,S_CONFIG);
    packet.image_dev=info.lo_device;packet.image_inode=info.lo_inode;packet.loop_device=(uint64_t)o->loop_stat.st_rdev;
    packet.loop_number=info.lo_number;packet.loop_flags=info.lo_flags;
    if (child_send(o,ctl,&packet)<0) return -1;
    *noticed=1;
    for (;;) {
        int received[32];size_t count=0,i;struct pollfd p={ctl,POLLIN,0};
        if (child_still_parented(o)<0 || now_ms(&now)<0 || now>=o->deadline) { errno=ETIMEDOUT;return -1; }
        result=poll(&p,1,50);
        if (result<0 && errno==EINTR) continue;
        if (result<0) return -1;
        if (result && (p.revents&POLLIN)) {
            if (receive_wire(ctl,&packet,received,&count,o->parent,o->uid,o->gid,NULL)<0) {
                if (errno==EAGAIN || errno==EINTR) continue;
                return -1;
            }
            for (i=0;i<count;i++) close_cell(&received[i]);
            if (!count && packet.kind==W_CONFIG_ACK && packet.stage==S_CONFIG && !packet.error &&
                wire_has_no_resources(&packet) && no_config_fields(&packet)) return 0;
            errno=EPROTO;return -1;
        }
        if (result && (p.revents&(POLLHUP|POLLERR|POLLNVAL))) { errno=ECANCELED;return -1; }
    }
}
static int child_image_mount(struct gvo_owner *o) {
    int old=-1,tmp=-1,write_dir=-1,result=-1,saved;
    struct statfs fs;uint64_t old_id,new_id;const struct gpv_mount_row *r;
    char target[64],source[64];
    old=open_absolute("/mnt");if (old<0 || fd_mount_id(old,&old_id)<0 || fd_path(old,target)<0) goto done;
    if (mount("gvo-v2-scaffold",target,"tmpfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,"mode=0700,size=1048576,nr_inodes=64")<0) goto done;
    tmp=open_absolute("/mnt");
    if (tmp<0 || mounts_read("/proc/self/mountinfo")<0 || fd_member(tmp,&new_id)<0 || fstatfs(tmp,&fs)<0) goto done;
    r=mount_find(new_id);
    if (!r || old_id==new_id || strcmp(r->point,"/mnt") || strcmp(r->root,"/") || strcmp(r->type,"tmpfs") ||
        (unsigned long)fs.f_type!=(unsigned long)TMPFS_MAGIC || r->shared || r->master || r->propagate) { errno=EXDEV;goto done; }
    mounts_clear();
    write_dir=open("/mnt",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (write_dir<0 || same_object(write_dir,tmp)<0 || same_mount(write_dir,tmp)<0 ||
        mkdirat(write_dir,"gvi",0700)<0) goto done;
    { int gvi=walk_at(write_dir,"gvi");
      if (gvi<0) goto done;
      result=mkdirat(gvi,"root",0700);saved=errno;
      if (close_cell(&gvi)<0 && result==0) { result=-1;saved=errno; }
      errno=saved;if (result<0) goto done;
    }
    if (fd_path(o->loop_fd,source)<0 || mount(source,GVO_ROOT,"ext4",MS_RDONLY|MS_NOSUID|MS_NODEV,NULL)<0) { result=-1;goto done; }
    result=0;
done:
    saved=errno;mounts_clear();
    if (close_cell(&old)<0 && !result) { saved=errno;result=-1; }
    if (close_cell(&tmp)<0 && !result) { saved=errno;result=-1; }
    if (close_cell(&write_dir)<0 && !result) { saved=errno;result=-1; }
    errno=saved;return result;
}
static _Noreturn void child_prepare(struct gvo_owner *o,int ctl) {
    /* Preserve old f[0..4] roles and f[5..15] temporary meanings. V3's two
     * new owning cells are packed explicitly; rights[] never owns aliases. */
    int f[16],stage=S_PRIVATE,saved=0,image=-1,attempted=0,noticed=0;
    int dev_target=-1,dev_root=-1,dev_write=-1,socket_root=-1,socket_write=-1;
    int inherited_dev=-1,inherited_dev_after=-1,rights[GVO_RIGHTS];
    size_t i;
    struct stat ns,source_data,host_data,source_root,host_root;
    struct wire packet;
    uint64_t id,root_id,alias_a,alias_b;
    const struct gpv_mount_row *row;
    struct sigaction sa;
    sigset_t mask;
    for (i=0;i<16;i++) f[i]=-1;
    for (i=0;i<GVO_RIGHTS;i++) rights[i]=-1;
    memset(&sa,0,sizeof(sa));sa.sa_handler=SIG_DFL;sigemptyset(&sa.sa_mask);
    if (sigaction(SIGTERM,&sa,NULL)<0 || sigaction(SIGINT,&sa,NULL)<0 || sigaction(SIGHUP,&sa,NULL)<0) goto fail;
    sigemptyset(&mask);if (sigprocmask(SIG_SETMASK,&mask,NULL)<0) goto fail;
    if (prctl(PR_SET_PDEATHSIG,SIGKILL)<0 || child_still_parented(o)<0) goto fail;
    if (close_unlisted(ctl,o->witness[0],o->witness[1],o->loop_fd)<0) goto fail;
    if (unshare(CLONE_NEWNS)<0 || mount(NULL,"/",NULL,MS_REC|MS_PRIVATE,NULL)<0) goto fail;
    f[0]=open("/proc/self/ns/mnt",O_RDONLY|O_CLOEXEC);
    if (f[0]<0 || namespace_stat(f[0],&ns)<0) goto fail;
    if (ns.st_ino==o->parent_ns_inode && ns.st_dev==o->parent_ns_dev) { errno=EXDEV;goto fail; }
    if (mounts_read("/proc/self/mountinfo")<0 || private_table()<0 || child_still_parented(o)<0) goto fail;
    stage=S_REOPEN;
    { int stage_dir=open_absolute("/data/local/tmp/oneos"),saved_open;
      if (stage_dir<0) goto fail;
      image=openat(stage_dir,"system.raw",O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK);saved_open=errno;
      if (close_cell(&stage_dir)<0) goto fail;
      errno=saved_open;if (image<0) goto fail;
    }
    { struct stat st;
      if (fstat(image,&st)<0) goto fail;
      if (!S_ISREG(st.st_mode) || st.st_dev!=o->image_stat.st_dev || st.st_ino!=o->image_stat.st_ino ||
          st.st_size!=o->image_stat.st_size || st.st_uid!=o->image_stat.st_uid || st.st_gid!=o->image_stat.st_gid ||
          st.st_mode!=o->image_stat.st_mode || st.st_mtim.tv_sec!=o->image_stat.st_mtim.tv_sec ||
          st.st_mtim.tv_nsec!=o->image_stat.st_mtim.tv_nsec || st.st_ctim.tv_sec!=o->image_stat.st_ctim.tv_sec ||
          st.st_ctim.tv_nsec!=o->image_stat.st_ctim.tv_nsec) { errno=ESTALE;goto fail; }
    }
    f[1]=open_absolute("/");f[5]=open_absolute(o->data_path);f[6]=open_absolute("/data");f[7]=open_absolute("/data_mirror");
    if (f[1]<0 || f[5]<0 || f[6]<0 || f[7]<0 || same_object(f[5],o->witness[1])<0 || source_has_submounts(o->data_path)<0) goto fail;
    if (fd_directory(f[5],&source_data)<0 || fd_directory(f[6],&host_data)<0 ||
        source_data.st_uid!=1000 || source_data.st_gid!=1000 || (source_data.st_mode&07777)!=0771) { errno=EPERM;goto fail; }
    if (source_data.st_dev==host_data.st_dev && source_data.st_ino==host_data.st_ino) { errno=EXDEV;goto fail; }
    mounts_clear();stage=S_CONFIG;
    if (child_configure(o,ctl,image,&attempted,&noticed)<0) goto fail;
    stage=S_IMAGE;if (child_image_mount(o)<0) goto fail;
    f[2]=open_absolute(o->root_path);
    if (f[2]<0 || mounts_read("/proc/self/mountinfo")<0 || private_root_mount(f[2],o->root_path)<0 ||
        fd_directory(f[2],&source_root)<0 || fd_directory(f[1],&host_root)<0) goto fail;
    if (fd_mount_id(f[2],&root_id)<0 || !(row=mount_find(root_id)) || strcmp(row->type,"ext4") || !mount_option(row->options,"ro") || !mount_option(row->super_options,"ro") ||
        source_root.st_dev!=o->loop_stat.st_rdev || (source_root.st_dev==host_root.st_dev && source_root.st_ino==host_root.st_ino)) { errno=EXDEV;goto fail; }
    for (i=1;i<=7;i++) if (f[i]>=0 && fd_member(f[i],&id)<0) goto fail;
    f[8]=walk_at(f[2],"data");f[9]=walk_at(f[2],"data_mirror");
    if (f[8]<0 || f[9]<0 || same_mount(f[2],f[8])<0 || same_mount(f[2],f[9])<0) goto fail;
    if (close_cell(&o->witness[0])<0 || close_cell(&o->witness[1])<0) goto fail;
    mounts_clear();
    stage=S_DATA;
    if (child_still_parented(o)<0 || bind_fds(f[5],f[6])<0) goto fail;
    f[3]=open_absolute("/data");
    if (f[3]<0 || same_object(f[3],f[5])<0 || shared_fd(f[3])<0 || bind_fds(f[3],f[8])<0) goto fail;
    f[10]=walk_at(f[2],"data"); /* AFTER bind: old f[8] pins the covered object. */
    if (f[10]<0 || mounts_read("/proc/self/mountinfo")<0 || pair_check(o,f[3],f[10],&packet.data_group)<0) goto fail;
    /* Both peers exist before this alias. Plain bind cannot copy earlier private
     * child mounts; create the event now and prove the receiver afterward. */
    stage=S_ALIAS;
    f[11]=walk_at(f[3],"user/0");f[12]=walk_at(f[3],"data");
    if (f[11]<0 || f[12]<0 || same_mount(f[3],f[12])<0 || bind_fds(f[11],f[12])<0) goto fail;
    if (close_cell(&f[12])<0) goto fail;
    f[12]=walk_at(f[3],"data");f[13]=walk_at(f[2],"data/data");
    if (f[12]<0 || f[13]<0 || same_object(f[11],f[12])<0 || same_object(f[11],f[13])<0) goto fail;
    if (mounts_read("/proc/self/mountinfo")<0 || fd_member(f[12],&alias_a)<0 || fd_member(f[13],&alias_b)<0 || alias_a==alias_b) goto fail;
    if (fd_mount_id(f[3],&id)<0 || alias_a==id || fd_mount_id(f[10],&id)<0 || alias_b==id) { errno=EXDEV;goto fail; }
    stage=S_MIRROR;
    {
        char target[64];
        if (fd_path(f[7],target)<0 || mount("gvo-owned-mirror",target,"tmpfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,"mode=0700,size=1048576,nr_inodes=64")<0) goto fail;
    }
    f[4]=open_absolute("/data_mirror");
    if (f[4]<0) goto fail;
    {
        uint64_t old_id,new_id;
        struct statfs fs;
        if (mounts_read("/proc/self/mountinfo")<0 || fd_mount_id(f[7],&old_id)<0 || fd_member(f[4],&new_id)<0 || fstatfs(f[4],&fs)<0) goto fail;
        row=mount_find(new_id);
        if (!row || new_id==old_id || strcmp(row->type,"tmpfs") || strcmp(row->root,"/") || strcmp(row->point,"/data_mirror") || (unsigned long)fs.f_type!=(unsigned long)TMPFS_MAGIC || row->shared || row->master || row->propagate) { errno=EXDEV;goto fail; }
        mounts_clear();
    }
    f[15]=open("/data_mirror",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    /* Only this newly owned tmpfs gets backing-directory writes. No volume/user
     * defaults: null UUID, CE/FBE and populated mirror aliases stay external. */
    if (f[15]<0 || same_object(f[4],f[15])<0 || same_mount(f[4],f[15])<0 || mkdirat(f[15],"data_ce",0700)<0 || mkdirat(f[15],"data_de",0700)<0) goto fail;
    if (shared_fd(f[4])<0 || bind_fds(f[4],f[9])<0) goto fail;
    f[14]=walk_at(f[2],"data_mirror");
    if (f[14]<0) goto fail;
    stage=S_DEV;
    {
        char dev_path[GVO_PATH],target[64];
        int length;
        struct stat target_stat;
        inherited_dev=walk_at(f[1],"dev");
        dev_target=walk_at(f[2],"dev");
        if (inherited_dev<0 || dev_target<0 || dev_directory_profile(dev_target,&target_stat)<0 ||
            same_mount(f[2],dev_target)<0 || dev_directory_shape(o,dev_target,0)<0) goto fail;
        length=snprintf(dev_path,sizeof(dev_path),"%s/dev",o->root_path);
        if (length<0 || (size_t)length>=sizeof(dev_path)) { errno=EOVERFLOW;goto fail; }
        if (mounts_read("/proc/self/mountinfo")<0 || source_has_submounts(dev_path)<0 ||
            child_still_parented(o)<0 || fd_path(dev_target,target)<0) goto fail;
        /* Only this fresh private filesystem is writable. The covered image
         * directory and the inherited/native /dev are never written or bound. */
        if (mount("gvo-v3-owned-dev",target,"tmpfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,
                  "mode=0755,uid=0,gid=0,size=1048576,nr_inodes=64")<0) goto fail;
        dev_root=walk_at(f[2],"dev");
        if (dev_root<0 || mounts_read("/proc/self/mountinfo")<0) goto fail;
        {
            struct statfs fs;
            uint64_t old_id,new_id;
            if (fd_mount_id(dev_target,&old_id)<0 || fd_member(dev_root,&new_id)<0 ||
                fstatfs(dev_root,&fs)<0 || dev_directory_profile(dev_root,&target_stat)<0) goto fail;
            row=mount_find(new_id);
            if (!row || old_id==new_id || strcmp(row->point,dev_path) || strcmp(row->root,"/") ||
                strcmp(row->type,"tmpfs") || (unsigned long)fs.f_type!=(unsigned long)TMPFS_MAGIC ||
                row->shared || row->master || row->propagate ||
                !mount_option(row->options,"rw") || !mount_option(row->super_options,"rw") ||
                !mount_option(row->options,"nosuid") || !mount_option(row->options,"nodev") ||
                !mount_option(row->options,"noexec")) { errno=EXDEV;goto fail; }
        }
        if (dev_directory_shape(o,dev_root,0)<0) goto fail;
    }
    stage=S_SOCKET;
    dev_write=openat(dev_root,".",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (dev_write<0 || same_object(dev_write,dev_root)<0 || same_mount(dev_write,dev_root)<0 ||
        mkdirat(dev_write,"socket",0755)<0) goto fail;
    socket_write=openat(dev_write,"socket",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (socket_write<0 || same_mount(socket_write,dev_root)<0 ||
        fchown(socket_write,0,0)<0 || fchmod(socket_write,0755)<0) goto fail;
    socket_root=openat(dev_root,"socket",O_PATH|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    inherited_dev_after=walk_at(f[1],"dev");
    if (socket_root<0 || inherited_dev_after<0 || same_object(socket_root,socket_write)<0 ||
        same_object(inherited_dev_after,inherited_dev)<0 ||
        same_mount(inherited_dev_after,inherited_dev)<0) goto fail;
    if (close_cell(&dev_write)<0 || close_cell(&socket_write)<0) goto fail;
    stage=S_READBACK;
    wire_init(&packet,W_PARTIAL,(uint32_t)stage);
    if (mounts_read("/proc/self/mountinfo")<0 || pair_check(o,f[3],f[10],&packet.data_group)<0 || pair_check(o,f[4],f[14],&packet.mirror_group)<0 || packet.data_group==packet.mirror_group) goto fail;
    if (fd_member(f[4],&id)<0 || !(row=mount_find(id)) || strcmp(row->type,"tmpfs") || strcmp(row->root,"/")) { errno=EXDEV;goto fail; }
    if (fd_member(f[2],&root_id)<0 || !(row=mount_find(root_id)) || row->shared || row->master || row->propagate) { errno=EXDEV;goto fail; }
    if (same_object(f[11],f[12])<0 || same_object(f[11],f[13])<0 || fd_member(f[12],&packet.alias_native)<0 || fd_member(f[13],&packet.alias_guest)<0) goto fail;
    if (fd_member(f[10],&packet.guest_data_mount)<0 || fd_member(f[14],&packet.guest_mirror_mount)<0) goto fail;
    if (dev_socket_check(o,f[2],f[3],f[4],dev_root,socket_root)<0) goto fail;
    for (i=0;i<R_DEV;i++) rights[i]=f[i];
    rights[R_DEV]=dev_root;rights[R_SOCKET]=socket_root;
    for (i=1;i<GVO_RIGHTS;i++) if (fd_member(rights[i],&packet.mounts[i])<0) goto fail;
    packet.namespace_inode=(uint64_t)ns.st_ino;packet.namespace_dev=(uint64_t)ns.st_dev;
    mounts_clear();
    if (child_still_parented(o)<0) goto fail;
    stage=S_IPC;
    if (send_wire(ctl,&packet,rights,GVO_RIGHTS)<0) goto fail;
    for (;;) {
        struct pollfd p={ctl,POLLIN,0};
        int received[32];size_t count=0;
        int n=poll(&p,1,1000);
        if (n<0 && errno==EINTR) continue;
        if (n<0 || child_still_parented(o)<0) break;
        if (!n) continue;
        if (p.revents&POLLIN) {
            if (receive_wire(ctl,&packet,received,&count,o->parent,o->uid,o->gid,NULL)<0) break;
            for (i=0;i<count;i++) close_cell(&received[i]);
            if (count || packet.kind!=W_CANCEL || packet.stage || packet.error || !wire_has_no_resources(&packet) || !no_config_fields(&packet)) break;
            break;
        }
        if (p.revents&(POLLHUP|POLLERR|POLLNVAL)) break;
    }
    for (i=0;i<16;i++) close_cell(&f[i]);
    close_cell(&dev_target);close_cell(&dev_root);close_cell(&dev_write);
    close_cell(&socket_root);close_cell(&socket_write);
    close_cell(&inherited_dev);close_cell(&inherited_dev_after);
    close_cell(&image);close_cell(&o->loop_fd);close_cell(&ctl);_exit(0);
fail:
    saved=errno?errno:EIO;mounts_clear();
    if (!noticed) {
        wire_init(&packet,attempted?W_CONFIG_UNKNOWN:W_PRECONFIG_ERROR,(uint32_t)stage);packet.error=saved;
        (void)child_send(o,ctl,&packet);
    } else if (noticed==1 && attempted) {
        wire_init(&packet,W_ERROR,(uint32_t)stage);packet.error=saved;(void)child_send(o,ctl,&packet);
    }
    for (i=0;i<16;i++) close_cell(&f[i]);
    close_cell(&dev_target);close_cell(&dev_root);close_cell(&dev_write);
    close_cell(&socket_root);close_cell(&socket_write);
    close_cell(&inherited_dev);close_cell(&inherited_dev_after);
    close_cell(&image);close_cell(&o->loop_fd);close_cell(&o->witness[0]);close_cell(&o->witness[1]);close_cell(&ctl);_exit(1);
}

static int single_thread(void) {
    DIR *d=opendir("/proc/self/task");
    struct dirent *entry;
    unsigned count=0;int matched=0,saved=0;
    if (!d) return -1;
    errno=0;
    while ((entry=readdir(d))!=NULL) {
        uint64_t tid;
        if (entry->d_name[0]=='.') continue;
        if (u64(entry->d_name,&tid)<0 || ++count>1) { saved=EPERM;break; }
        if (tid==(uint64_t)getpid()) matched=1;
    }
    if (!saved && errno) saved=errno;
    if (closedir(d)<0 && !saved) saved=errno;
    if (!saved && (count!=1 || !matched)) saved=EPERM;
    if (saved) { errno=saved;return -1; }
    return 0;
}
static int valid_owner(struct gvo_owner *o) {
    if (o!=&only_owner || !used_owner || getpid()!=o->parent || single_thread()<0) { errno=EINVAL;return 0; }
    return 1;
}
static int wait_owned(struct gvo_owner *o) {
    int status;
    pid_t result;
    if (o->reaped) return 1;
    if (o->state==O_LOST) { errno=ECHILD;return -1; }
    result=waitpid(o->child,&status,WNOHANG);
    if (!result) return 0;
    if (result<0) {
        if (errno==EINTR) return 0;
        o->state=O_LOST;owner_close_cell(o,&o->ctl);return -1;
    }
    if (result!=o->child || (!WIFEXITED(status) && !WIFSIGNALED(status))) {
        /* A traced-child stop is not terminal consumption. Keep the exact child
         * owned; cancellation may still signal it while it is unreaped. */
        o->state=O_HOLD;errno=EPROTO;return 0;
    }
    o->reaped=1;o->wait_status=status;o->state=O_REAPED;
    return 1; /* no later signal path may pass reaped */
}
static int signal_owned(struct gvo_owner *o,int signal_number) {
    int result=wait_owned(o);
    if (result!=0 || o->reaped || o->state==O_LOST) return result<0?-1:0;
    if (kill(o->child,signal_number)<0) {
        /* ESRCH, including a race with exit, does not consume terminal status. */
        if (errno!=ESRCH && !o->close_error) o->close_error=errno;
        return -1;
    }
    return 0;
}
static void close_resources(struct gvo_owner *o) {
    size_t i;
    for (i=0;i<GVO_RIGHTS;i++) owner_close_cell(o,&o->held[i]);
    owner_close_cell(o,&o->witness[0]);owner_close_cell(o,&o->witness[1]);
    owner_close_cell(o,&o->parent_ns);
}

static int candidate_open(struct gvo_owner *o) {
    int base=-1,dev=-1,control=-1,dir=-1,number,saved,length;char name[64];struct stat st;
    base=open("/",O_PATH|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if (base<0) goto fail;
    dev=openat(base,"dev",O_PATH|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if (dev<0) goto fail;
    control=openat(dev,"loop-control",O_RDWR|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);
    if (control<0 || fstat(control,&st)<0) goto fail;
    /* Fixed loop-control endpoint: Linux v6.12 miscdevice.h LOOP_CTRL_MINOR237;
     * MISC_MAJOR comes from the selected NDK UAPI header. Not just a namesake. */
    if (!S_ISCHR(st.st_mode) || major(st.st_rdev)!=MISC_MAJOR || minor(st.st_rdev)!=237U) { errno=ENODEV;goto fail; }
    /* GET_FREE may create a global kernel pool object. It is NOT reservation. */
    number=ioctl(control,LOOP_CTL_GET_FREE);if (number<0) goto fail;
    dir=openat(dev,"block",O_PATH|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if (dir<0) goto fail;
    length=snprintf(name,sizeof(name),"loop%d",number);
    if (length<0 || (size_t)length>=sizeof(name)) { errno=EOVERFLOW;goto fail; }
    o->loop_fd=openat(dir,name,O_RDWR|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);
    if (o->loop_fd<0 || fstat(o->loop_fd,&o->loop_stat)<0) goto fail;
    if (!S_ISBLK(o->loop_stat.st_mode) || major(o->loop_stat.st_rdev)!=7U ||
        minor(o->loop_stat.st_rdev)!=(unsigned)number) { errno=EXDEV;goto fail; }
    owner_close_cell(o,&control);owner_close_cell(o,&dir);owner_close_cell(o,&dev);owner_close_cell(o,&base);
    if (o->close_error) { errno=o->close_error;return -1; }
    o->loop_state=L_CANDIDATE;return 0;
fail:
    saved=errno?errno:EIO;owner_close_cell(o,&control);owner_close_cell(o,&dir);
    owner_close_cell(o,&dev);owner_close_cell(o,&base);errno=saved;return -1;
}
int gvo_begin(const struct gvo_plan *plan,struct gvo_owner **out) {
    struct gvo_owner *o=&only_owner;struct sigaction disposition;
    struct stat ns,witness;uid_t r,e,u;gid_t gr,ge,gs;
    int sockets[2]={-1,-1},one=1,saved,flags;size_t i;uint64_t now;
    if (used_owner) { errno=EBUSY;return -1; }
    if (!out || !plan) { errno=EINVAL;return -1; }*out=NULL;
    if (single_thread()<0 || sigaction(SIGCHLD,NULL,&disposition)<0) return -1;
    if (disposition.sa_handler!=SIG_DFL || (disposition.sa_flags&SA_NOCLDWAIT)) { errno=EPERM;return -1; }
    if (getresuid(&r,&e,&u)<0 || getresgid(&gr,&ge,&gs)<0) return -1;
    if (r!=e || r!=u || gr!=ge || gr!=gs) { errno=EPERM;return -1; }
    used_owner=1;memset(o,0,sizeof(*o));o->state=O_STARTING;o->ctl=o->parent_ns=o->loop_fd=-1;
    o->witness[0]=o->witness[1]=-1;o->reaped=1; /* no child exists yet */
    for (i=0;i<GVO_RIGHTS;i++) o->held[i]=-1;
    o->parent=getpid();o->uid=r;o->gid=gr;*out=o;
    strcpy(o->root_path,GVO_ROOT);strcpy(o->data_path,GVO_DATA);
    o->witness[0]=fcntl(plan->image_witness_fd,F_DUPFD_CLOEXEC,3);
    o->witness[1]=fcntl(plan->private_data_witness_fd,F_DUPFD_CLOEXEC,3);
    if (o->witness[0]<0 || o->witness[1]<0 || fstat(o->witness[0],&o->image_stat)<0 || fd_directory(o->witness[1],&witness)<0) goto fail;
    flags=fcntl(o->witness[0],F_GETFL);
    if (flags<0 || (flags&O_ACCMODE)!=O_RDONLY || !S_ISREG(o->image_stat.st_mode) ||
        o->image_stat.st_uid!=0 || (o->image_stat.st_mode&0022) || o->image_stat.st_size<=0 ||
        witness.st_uid!=1000 || witness.st_gid!=1000 || (witness.st_mode&07777)!=0771) { errno=EPERM;goto fail; }
    o->parent_ns=open("/proc/self/ns/mnt",O_RDONLY|O_CLOEXEC);
    if (o->parent_ns<0 || namespace_stat(o->parent_ns,&ns)<0 || mounts_read("/proc/self/mountinfo")<0) goto fail;
    o->parent_ns_inode=(uint64_t)ns.st_ino;o->parent_ns_dev=(uint64_t)ns.st_dev;
    for (i=0;i<mount_count;i++) {
        if (mount_rows[i].shared) o->forbidden[o->forbidden_count++]=mount_rows[i].shared;
        if (mount_rows[i].master) o->forbidden[o->forbidden_count++]=mount_rows[i].master;
        if (mount_rows[i].propagate) o->forbidden[o->forbidden_count++]=mount_rows[i].propagate;
    }
    mounts_clear();
    if (candidate_open(o)<0 || socketpair(AF_UNIX,SOCK_SEQPACKET|SOCK_CLOEXEC|SOCK_NONBLOCK,0,sockets)<0 ||
        setsockopt(sockets[0],SOL_SOCKET,SO_PASSCRED,&one,sizeof(one))<0 ||
        setsockopt(sockets[1],SOL_SOCKET,SO_PASSCRED,&one,sizeof(one))<0 || now_ms(&now)<0) goto fail;
    if (now>UINT64_MAX-30000U) { errno=EOVERFLOW;goto fail; }o->deadline=now+30000U;
    o->loop_state=L_PENDING; /* a fork child may commit before our next instruction */
    o->child=fork();
    if (o->child<0) { o->loop_state=L_CANDIDATE;goto fail; }
    if (!o->child) child_prepare(o,sockets[1]);
    o->reaped=0;o->ctl=sockets[0];sockets[0]=-1;
    owner_close_cell(o,&sockets[1]);
    if (o->close_error) { errno=o->close_error;(void)gvo_cancel(o);return -1; }
    return 0;
fail:
    saved=errno?errno:EIO;mounts_clear();owner_close_cell(o,&sockets[0]);owner_close_cell(o,&sockets[1]);
    close_resources(o);owner_close_cell(o,&o->loop_fd);o->state=O_CLOSED;errno=saved;return -1;
}

static int validate_partial_checks(struct gvo_owner *o,const struct wire *packet,int received[32]) {
    struct stat ns,live;
    char path[64];
    int live_ns=-1,saved;
    size_t i;
    if (o->loop_state!=L_CONFIRMED || !no_config_fields(packet) || packet->kind!=W_PARTIAL || packet->stage!=S_READBACK || packet->error || packet->mounts[0] || !packet->data_group || !packet->mirror_group || packet->data_group==packet->mirror_group || !packet->alias_native || !packet->alias_guest || packet->alias_native==packet->alias_guest || !packet->guest_data_mount || !packet->guest_mirror_mount) { errno=EPROTO;return -1; }
    if (namespace_stat(received[0],&ns)<0 || (uint64_t)ns.st_ino!=packet->namespace_inode || (uint64_t)ns.st_dev!=packet->namespace_dev || ((uint64_t)ns.st_ino==o->parent_ns_inode && (uint64_t)ns.st_dev==o->parent_ns_dev)) { errno=EXDEV;return -1; }
    if (snprintf(path,sizeof(path),"/proc/%ld/ns/mnt",(long)o->child)<0) return -1;
    live_ns=open(path,O_RDONLY|O_CLOEXEC);
    if (live_ns<0) return -1;
    if (namespace_stat(live_ns,&live)<0 || live.st_dev!=ns.st_dev || live.st_ino!=ns.st_ino) { saved=errno?errno:EXDEV;owner_close_cell(o,&live_ns);errno=saved;return -1; }
    owner_close_cell(o,&live_ns);
    if (o->close_error) { errno=o->close_error;return -1; }
    if (snprintf(path,sizeof(path),"/proc/%ld/mountinfo",(long)o->child)<0 || mounts_read(path)<0) return -1;
    for (i=1;i<GVO_RIGHTS;i++) {
        uint64_t id;
        if (fd_member(received[i],&id)<0 || id!=packet->mounts[i]) { errno=EXDEV;return -1; }
    }
    for (i=1;i<=2;i++) {
        const struct gpv_mount_row *r=mount_find(packet->mounts[i]);
        if (!r || r->shared || r->master || r->propagate) { errno=EXDEV;return -1; }
        if (i==2 && (strcmp(r->type,"ext4") || !mount_option(r->options,"ro") || !mount_option(r->super_options,"ro") ||
            r->major!=major(o->loop_stat.st_rdev) || r->minor!=minor(o->loop_stat.st_rdev))) { errno=EXDEV;return -1; }
    }
    for (i=3;i<=4;i++) {
        const struct gpv_mount_row *r=mount_find(packet->mounts[i]);
        const struct gpv_mount_row *guest=mount_find(i==3?packet->guest_data_mount:packet->guest_mirror_mount);
        const struct gpv_mount_row *root=mount_find(packet->mounts[2]);
        uint64_t expected=i==3?packet->data_group:packet->mirror_group;
        char expected_point[GVO_PATH];int length;
        if (!r || r->shared!=expected || r->master || r->propagate || forbidden_group(o,expected)) { errno=EXDEV;return -1; }
        if (!guest || !root || guest->id==r->id || guest->shared!=expected || guest->master || guest->propagate || strcmp(guest->root,r->root) || guest->major!=r->major || guest->minor!=r->minor) { errno=EXDEV;return -1; }
        length=snprintf(expected_point,sizeof(expected_point),"%s/%s",root->point,i==3?"data":"data_mirror");
        if (length<0 || (size_t)length>=sizeof(expected_point) || strcmp(guest->point,expected_point) || strcmp(r->point,i==3?"/data":"/data_mirror")) { errno=EXDEV;return -1; }
    }
    {
        const struct gpv_mount_row *a=mount_find(packet->alias_native),*b=mount_find(packet->alias_guest);
        const struct gpv_mount_row *root=mount_find(packet->mounts[2]);
        char expected_point[GVO_PATH];int length;
        if (!a || !b || a->major!=b->major || a->minor!=b->minor || strcmp(a->root,b->root) || a->master || b->master || a->propagate || b->propagate || forbidden_group(o,a->shared) || forbidden_group(o,b->shared)) { errno=EXDEV;return -1; }
        if (!root) return -1;
        length=snprintf(expected_point,sizeof(expected_point),"%s/data/data",root->point);
        if (length<0 || (size_t)length>=sizeof(expected_point) || strcmp(a->point,"/data/data") || strcmp(b->point,expected_point)) { errno=EXDEV;return -1; }
    }
    if (dev_socket_check(o,received[R_GUEST_ROOT],received[R_DATA],received[R_MIRROR],
                         received[R_DEV],received[R_SOCKET])<0) return -1;
    return 0;
}

static int validate_partial(struct gvo_owner *o,const struct wire *packet,int received[32]) {
    int result=validate_partial_checks(o,packet,received),saved=errno;
    mounts_clear();errno=saved;return result;
}

int gvo_receive_partial(struct gvo_owner *o,struct gvo_observation *out) {
    if (!out || !valid_owner(o) || o->state!=O_STARTING) { errno=EINVAL;return -1; }
    memset(out,0,sizeof(*out));
    for (;;) {
        uint64_t now;
        struct pollfd p;
        int result,received[32],saved;
        size_t count=0,i;
        struct wire packet;
        if (now_ms(&now)<0) { saved=errno;(void)gvo_cancel(o);errno=saved;return -1; }
        if (now>=o->deadline) { (void)gvo_cancel(o);errno=ETIMEDOUT;return -1; }
        p.fd=o->ctl;p.events=POLLIN;p.revents=0;
        result=poll(&p,1,(int)((o->deadline-now)>100U?100U:o->deadline-now));
        if (result<0 && errno==EINTR) continue;
        if (result<0) { saved=errno;(void)gvo_cancel(o);errno=saved;return -1; }
        if (result && (p.revents&POLLIN)) {
            if (receive_wire(o->ctl,&packet,received,&count,o->child,o->uid,o->gid,&o->close_error)<0) {
                if (errno==EAGAIN || errno==EINTR) continue;
                saved=errno;(void)gvo_cancel(o);errno=saved;return -1;
            }
            if (o->loop_state==L_PENDING && count==0) {
                if (packet.kind==W_CONFIG_OK && packet.stage==S_CONFIG && !packet.error && wire_has_no_resources(&packet)) {
                    struct loop_info64 actual;struct wire ack;
                    if (loop_readback(o,&actual)<0 || packet.image_dev!=actual.lo_device || packet.image_inode!=actual.lo_inode ||
                        packet.loop_device!=(uint64_t)o->loop_stat.st_rdev || packet.loop_number!=actual.lo_number || packet.loop_flags!=actual.lo_flags) {
                        o->loop_state=L_UNKNOWN;saved=errno?errno:EPROTO;(void)gvo_cancel(o);errno=saved;return -1;
                    }
                    o->loop_state=L_CONFIRMED;
                    wire_init(&ack,W_CONFIG_ACK,S_CONFIG);
                    if (send_wire(o->ctl,&ack,NULL,0)<0) { saved=errno;(void)gvo_cancel(o);errno=saved;return -1; }
                    continue;
                }
                if (packet.kind==W_PRECONFIG_ERROR && packet.stage>=S_PRIVATE && packet.stage<=S_CONFIG &&
                    packet.error>0 && packet.error<4096 && wire_has_no_resources(&packet) && no_config_fields(&packet)) {
                    o->loop_state=L_PRE_REFUSED;saved=packet.error;(void)gvo_cancel(o);errno=saved;return -1;
                }
                if (packet.kind==W_CONFIG_BUSY && packet.stage==S_CONFIG && packet.error==EBUSY &&
                    wire_has_no_resources(&packet) && no_config_fields(&packet)) {
                    o->loop_state=L_BUSY;saved=EBUSY;(void)gvo_cancel(o);errno=saved;return -1;
                }
                /* Failed/unknown configure, malformed stage, lost result or
                 * wrong cardinality never establishes no-commit from a tuple. */
                o->loop_state=L_UNKNOWN;
            }
            if (packet.kind==W_ERROR && o->loop_state==L_CONFIRMED && count==0 && packet.error>0 && packet.error<4096 && packet.stage>=S_CONFIG && packet.stage<=S_IPC && wire_has_no_resources(&packet) && no_config_fields(&packet)) {
                saved=packet.error;(void)gvo_cancel(o);errno=saved;return -1;
            }
            if (count!=GVO_RIGHTS || validate_partial(o,&packet,received)<0) {
                saved=errno?errno:EPROTO;for (i=0;i<count;i++) owner_close_cell(o,&received[i]);(void)gvo_cancel(o);errno=saved;return -1;
            }
            if (now_ms(&now)<0 || now>=o->deadline) {
                saved=errno?errno:ETIMEDOUT;
                if (now>=o->deadline) saved=ETIMEDOUT;
                for (i=0;i<count;i++) owner_close_cell(o,&received[i]);
                (void)gvo_cancel(o);errno=saved;return -1;
            }
            if (wait_owned(o)!=0 || o->state!=O_STARTING) {
                for (i=0;i<count;i++) owner_close_cell(o,&received[i]);(void)gvo_cancel(o);errno=ECHILD;return -1;
            }
            for (i=0;i<GVO_RIGHTS;i++) { o->held[i]=received[i];received[i]=-1; }
            o->observation.namespace_inode=packet.namespace_inode;
            o->observation.data_group=packet.data_group;o->observation.mirror_group=packet.mirror_group;
            o->state=O_HELD;*out=o->observation;return 0;
        }
        if (wait_owned(o)!=0 || o->state!=O_STARTING || (result && (p.revents&(POLLHUP|POLLERR|POLLNVAL)))) {
            (void)gvo_cancel(o);errno=ECHILD;return -1;
        }
    }
}

int gvo_cancel(struct gvo_owner *o) {
    struct wire packet;
    uint64_t now;
    if (!valid_owner(o)) return -1;
    if (o->state==O_CLOSED) return 0;
    /* Keep every resource through actual reap; unknown commit keeps loop and
     * witness/view custody indefinitely. Control closure requests child stop. */
    if (o->loop_state==L_PENDING) o->loop_state=L_UNKNOWN;
    if (o->ctl>=0) {
        wire_init(&packet,W_CANCEL,0);(void)send_wire(o->ctl,&packet,NULL,0);
        owner_close_cell(o,&o->ctl); /* drops queued SCM rights even before receipt */
    }
    if (o->reaped) return 0;
    if (o->state==O_LOST) { errno=ECHILD;return -1; }
    o->state=O_STOPPING;
    if (!o->term_sent) {
        o->term_sent=1;
        if (now_ms(&now)<0) {
            /* No synthetic clock/grace: immediate exact-owned-child KILL policy. */
            o->kill_sent=1;(void)signal_owned(o,SIGKILL);
            if (o->reaped) o->state=O_REAPED;
            else if (o->state!=O_LOST) o->state=O_HOLD;
            return -1;
        }
        o->kill_at=now+2000U;(void)signal_owned(o,SIGTERM);
    }
    return 0; /* request only; never proof of child exit or teardown */
}

static int finish_local_close(struct gvo_owner *o) {
    if (!o->reaped || o->state==O_LOST || o->loop_state==L_PENDING || o->loop_state==L_UNKNOWN) {
        if (o->state!=O_LOST) o->state=O_HOLD;
        errno=EINPROGRESS;return GVO_HOLD;
    }
    close_resources(o);
    if (o->close_error) { o->state=O_HOLD;errno=o->close_error;return GVO_HOLD; }
    /* No CLR_FD, unbound query or numeric reopening. Actual AUTOCLEAR is only
     * a deferred kernel mechanism; consuming our final local opener proves no
     * global unbound state. Child process-table references are gone after reap. */
    owner_close_cell(o,&o->loop_fd);
    if (o->close_error) { o->state=O_HOLD;errno=o->close_error;return GVO_HOLD; }
    o->partial_terminal=o->loop_state==L_CONFIRMED?GVO_LOCAL_RELEASED_KERNEL_UNCONFIRMED:0;
    o->state=O_CLOSED;return o->partial_terminal;
}
int gvo_close(struct gvo_owner *o) {
    uint64_t now;int result,saved;
    if (!valid_owner(o)) return -1;
    if (o->state==O_CLOSED) {
        if (o->close_error) { errno=o->close_error;return GVO_HOLD; }
        return o->partial_terminal;
    }
    (void)gvo_cancel(o);result=wait_owned(o);
    if (result==1) return finish_local_close(o);
    if (result<0 || o->state==O_LOST) { errno=ECHILD;return GVO_HOLD; }
    if (!o->kill_sent) {
        result=now_ms(&now);saved=errno;
        if (result<0 || now>=o->kill_at) {
            o->kill_sent=1;(void)signal_owned(o,SIGKILL);
            if (result<0 && !o->close_error) o->close_error=saved;
        }
    }
    if (wait_owned(o)==1) return finish_local_close(o);
    if (o->state!=O_LOST) o->state=O_HOLD;
    errno=EINPROGRESS;return GVO_HOLD;
}
