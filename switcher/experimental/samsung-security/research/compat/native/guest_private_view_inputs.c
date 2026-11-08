/* Authored existing-stage custody. open_existing only adopts inputs read-only.
 * begin_view invokes the actual child namespace/mount owner. No staging/exec. */
#define _GNU_SOURCE 1
#include "guest_private_view_inputs.h"
#include "guest_private_view_mountinfo.h"
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <unistd.h>

#define STAGE "/data/local/tmp/oneos"
#define DATA_PATH STAGE "/data"
#define ID_CAP 1024U
enum { F_STAGE,F_IMAGE,F_ID,F_DATA,F_COUNT };
enum { I_OPENING=1,I_AVAILABLE,I_VIEW,I_REFUSED,I_CLOSED };
struct gvi_inputs {
    int state,fd[F_COUNT],close_error,begin_attempted,terminal;
    pid_t parent;
    struct stat initial[F_COUNT];
    struct gvo_owner *view;
    char id_bytes[ID_CAP+1];
    size_t id_length;
};
static struct gvi_inputs one;
static int used;

static void close_owned(struct gvi_inputs *p,int *cell) {
    int fd=*cell,saved=errno;
    *cell=-1;
    if (fd>=0 && close(fd)<0 && !p->close_error) p->close_error=errno;
    errno=saved;
}
static int one_thread(void) {
    DIR *d=opendir("/proc/self/task");
    struct dirent *e;
    size_t count=0;
    int saved=0;
    if (!d) return -1;
    for (;;) {
        errno=0;e=readdir(d);
        if (!e) { saved=errno;break; }
        if (e->d_name[0]=='.') continue;
        if (++count>1) { saved=EPERM;break; }
    }
    if (closedir(d)<0 && !saved) saved=errno;
    if (!saved && count!=1) saved=EPERM;
    if (saved) { errno=saved;return -1; }
    return 0;
}
static int valid(struct gvi_inputs *p) {
    if (!used || p!=&one || getpid()!=p->parent || one_thread()<0) { errno=EINVAL;return 0; }
    return 1;
}
static int walk(struct gvi_inputs *p,int base,const char *relative) {
    char path[256],*s,*next;
    int fd=fcntl(base,F_DUPFD_CLOEXEC,3),n=-1,saved;
    if (fd<0) return -1;
    if (!relative || !*relative || strlen(relative)>=sizeof(path)) { errno=EINVAL;goto fail; }
    strcpy(path,relative);s=path;
    for (;;) {
        next=strchr(s,'/');if (next) *next=0;
        if (!*s || !strcmp(s,".") || !strcmp(s,"..")) { errno=EINVAL;goto fail; }
        n=openat(fd,s,O_PATH|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        if (n<0) goto fail;
        close_owned(p,&fd);
        if (p->close_error) { errno=p->close_error;goto fail; }
        fd=n;n=-1;
        if (!next) return fd;
        s=next+1;
    }
fail:
    saved=errno;close_owned(p,&fd);close_owned(p,&n);errno=saved;return -1;
}
static int same_identity(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev && a->st_ino==b->st_ino &&
        a->st_mode==b->st_mode && a->st_uid==b->st_uid && a->st_gid==b->st_gid &&
        a->st_nlink==b->st_nlink && a->st_size==b->st_size &&
        a->st_mtim.tv_sec==b->st_mtim.tv_sec && a->st_mtim.tv_nsec==b->st_mtim.tv_nsec &&
        a->st_ctim.tv_sec==b->st_ctim.tv_sec && a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
static int root_object(int fd,int directory,struct stat *s) {
    if (fstat(fd,s)<0) return -1;
    if ((directory?!S_ISDIR(s->st_mode):!S_ISREG(s->st_mode)) || s->st_uid!=0 || (s->st_mode&0022)) { errno=EPERM;return -1; }
    return 0;
}
static int read_id(int fd,char bytes[ID_CAP+1],size_t *length) {
    size_t n=0;
    while (n<ID_CAP) {
        ssize_t got=pread(fd,bytes+n,ID_CAP-n,(off_t)n);
        if (got<0) return -1;
        if (!got) { bytes[n]=0;*length=n;return 0; }
        n+=(size_t)got;
    }
    errno=E2BIG;return -1;
}
static int decimal(const char *s,size_t n,uint64_t *value) {
    uint64_t v=0;size_t i;
    if (!n) return -1;
    for (i=0;i<n;i++) {
        unsigned d=(unsigned char)s[i]-'0';
        if (d>9 || v>(UINT64_MAX-d)/10U) return -1;
        v=v*10U+d;
    }
    *value=v;return 0;
}
/* Original three-field grammar, bounded canonical stat rendering. The digest
 * is syntax-checked cached staging text, never presented as a fresh hash. */
static int id_matches(const char *bytes,size_t length,const struct stat *image) {
    const char *tokens[3];size_t sizes[3],i=0,k;
    uint64_t size;
    char actual[160];int n;
    for (k=0;k<3;k++) {
        while (i<length && (bytes[i]==' ' || bytes[i]=='\t' || bytes[i]=='\r' || bytes[i]=='\n')) i++;
        tokens[k]=bytes+i;
        while (i<length && bytes[i]!=' ' && bytes[i]!='\t' && bytes[i]!='\r' && bytes[i]!='\n') {
            if (!bytes[i]) { errno=EPROTO;return -1; }i++;
        }
        sizes[k]=(size_t)(bytes+i-tokens[k]);
    }
    while (i<length && (bytes[i]==' ' || bytes[i]=='\t' || bytes[i]=='\r' || bytes[i]=='\n')) i++;
    if (i!=length || decimal(tokens[0],sizes[0],&size)<0 || sizes[1]!=64 || image->st_size<=0 || size!=(uint64_t)image->st_size || image->st_mtim.tv_sec<0) { errno=EPROTO;return -1; }
    for (k=0;k<64;k++) if (!((tokens[1][k]>='0' && tokens[1][k]<='9') || (tokens[1][k]>='a' && tokens[1][k]<='f'))) { errno=EPROTO;return -1; }
    n=snprintf(actual,sizeof(actual),"%llu:%llu:%llu:%llu",(unsigned long long)image->st_dev,(unsigned long long)image->st_ino,(unsigned long long)image->st_size,(unsigned long long)image->st_mtim.tv_sec);
    if (n<0 || (size_t)n>=sizeof(actual) || sizes[2]!=(size_t)n || memcmp(tokens[2],actual,(size_t)n)) { errno=ESTALE;return -1; }
    return 0;
}
static int bounded_text(struct gvi_inputs *p,const char *path,char *buffer,size_t cap,size_t *length) {
    int fd=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW),saved=0,result=-1;
    size_t used=0;
    if (fd<0) return -1;
    while (used<cap) {
        ssize_t n=read(fd,buffer+used,cap-used);
        if (n<0) { saved=errno;break; }
        if (!n) { buffer[used]=0;*length=used;result=0;break; }
        used+=(size_t)n;
    }
    if (used==cap) saved=E2BIG;
    close_owned(p,&fd);
    if (!saved && p->close_error) saved=p->close_error;
    if (saved) { errno=saved;return -1; }return result;
}
static int mnt_id(struct gvi_inputs *p,int fd,uint64_t *id) {
    char path[64],text[GPV_FDINFO_MAX_BYTES+1];size_t n;
    int k=snprintf(path,sizeof(path),"/proc/self/fdinfo/%d",fd);
    if (k<0 || (size_t)k>=sizeof(path)) { errno=EOVERFLOW;return -1; }
    if (bounded_text(p,path,text,sizeof(text)-1,&n)<0) return -1;
    if (gpv_parse_fdinfo_mnt_id(text,n,id)!=GPV_OK) { errno=EPROTO;return -1; }return 0;
}
static int topology(struct gvi_inputs *p) {
    char *text=NULL;struct gpv_mount_row *rows=NULL;
    size_t length,count=0,capacity=0,i;uint64_t data_id;
    const struct gpv_mount_row *data;int result=-1,saved;
    text=malloc(GPV_MOUNTINFO_MAX_BYTES+1U);if (!text) goto done;
    if (bounded_text(p,"/proc/self/mountinfo",text,GPV_MOUNTINFO_MAX_BYTES,&length)<0) goto done;
    for (i=0;i<length;i++) if (text[i]=='\n') capacity++;
    if (!capacity || capacity>GPV_MOUNTINFO_MAX_ROWS) { errno=E2BIG;goto done; }
    if (capacity<GPV_MOUNTINFO_MAX_ROWS) capacity++;
    if (capacity>SIZE_MAX/sizeof(*rows)) { errno=EOVERFLOW;goto done; }
    rows=calloc(capacity,sizeof(*rows));if (!rows) goto done;
    if (gpv_parse_mountinfo(text,length,rows,capacity,&count)!=GPV_OK) { errno=EPROTO;goto done; }
    free(text);text=NULL;
    if (mnt_id(p,p->fd[F_DATA],&data_id)<0 || !(data=gpv_mount_by_id(rows,count,data_id))) goto done;
    if (major(p->initial[F_DATA].st_dev)!=data->major || minor(p->initial[F_DATA].st_dev)!=data->minor) { errno=EXDEV;goto done; }
    for (i=0;i<count;i++) {
        size_t n=strlen(DATA_PATH);
        if (!strncmp(rows[i].point,DATA_PATH,n) && (!rows[i].point[n] || rows[i].point[n]=='/')) { errno=EXDEV;goto done; }
    }
    result=0;
done:
    saved=errno;free(text);free(rows);errno=saved;return result;
}
static int recheck(struct gvi_inputs *p) {
    struct stat now;char current_id[ID_CAP+1];size_t length,i;
    int slash=-1,stage=-1,data=-1,image=-1,id=-1,result=-1,saved;
    for (i=0;i<F_COUNT;i++) if (fstat(p->fd[i],&now)<0 || !same_identity(&now,&p->initial[i])) { errno=ESTALE;return -1; }
    if (read_id(p->fd[F_ID],current_id,&length)<0 || length!=p->id_length || memcmp(current_id,p->id_bytes,length) ||
        id_matches(current_id,length,&p->initial[F_IMAGE])<0) { errno=ESTALE;return -1; }
    slash=open("/",O_PATH|O_DIRECTORY|O_CLOEXEC);if (slash<0) goto done;
    stage=walk(p,slash,"data/local/tmp/oneos");if (stage<0) goto done;
    data=walk(p,stage,"data");image=openat(stage,"system.raw",O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    id=openat(stage,"system.raw.id",O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    { int fds[F_COUNT]={stage,image,id,data};
      for (i=0;i<F_COUNT;i++) if (fds[i]<0 || fstat(fds[i],&now)<0 || !same_identity(&now,&p->initial[i])) { errno=ESTALE;goto done; }
    }
    if (topology(p)<0) goto done;
    result=0;
done:
    saved=errno;close_owned(p,&slash);close_owned(p,&stage);close_owned(p,&data);close_owned(p,&image);close_owned(p,&id);
    if (!result && p->close_error) { result=-1;saved=p->close_error; }
    errno=saved;return result;
}
int gvi_open_existing(struct gvi_inputs **out) {
    struct gvi_inputs *p=&one;struct stat host;
    int slash=-1,host_data=-1,check=-1,saved;size_t i;
    if (used) { errno=EBUSY;return -1; }
    if (!out) { errno=EINVAL;return -1; }*out=NULL;
    if (one_thread()<0 || getuid()!=0 || geteuid()!=0) { errno=EPERM;return -1; }
    used=1;memset(p,0,sizeof(*p));p->parent=getpid();p->state=I_OPENING;
    for (i=0;i<F_COUNT;i++) p->fd[i]=-1;
    *out=p; /* retained even on any later refusal/uncertain local close */
    slash=open("/",O_PATH|O_DIRECTORY|O_CLOEXEC);if (slash<0) goto fail;
    p->fd[F_STAGE]=walk(p,slash,"data/local/tmp/oneos");if (p->fd[F_STAGE]<0) goto fail;
    p->fd[F_IMAGE]=openat(p->fd[F_STAGE],"system.raw",O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    p->fd[F_ID]=openat(p->fd[F_STAGE],"system.raw.id",O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    p->fd[F_DATA]=walk(p,p->fd[F_STAGE],"data");
    for (i=0;i<F_DATA;i++) if (p->fd[i]<0 || root_object(p->fd[i],i==F_STAGE,&p->initial[i])<0) goto fail;
    if (p->fd[F_DATA]<0 || fstat(p->fd[F_DATA],&p->initial[F_DATA])<0) goto fail;
    if (!S_ISDIR(p->initial[F_DATA].st_mode) || p->initial[F_DATA].st_uid!=1000 ||
        p->initial[F_DATA].st_gid!=1000 || (p->initial[F_DATA].st_mode&07777)!=0771) { errno=EPERM;goto fail; }
    if (p->initial[F_ID].st_size<=0 || p->initial[F_ID].st_size>=ID_CAP ||
        read_id(p->fd[F_ID],p->id_bytes,&p->id_length)<0 || id_matches(p->id_bytes,p->id_length,&p->initial[F_IMAGE])<0) goto fail;
    host_data=walk(p,slash,"data");if (host_data<0 || fstat(host_data,&host)<0) goto fail;
    if (host.st_dev==p->initial[F_DATA].st_dev && host.st_ino==p->initial[F_DATA].st_ino) { errno=EXDEV;goto fail; }
    check=walk(p,p->fd[F_DATA],"user/0");if (check<0) goto fail;close_owned(p,&check);
    check=walk(p,p->fd[F_DATA],"data");if (check<0) goto fail;close_owned(p,&check);
    if (p->close_error || topology(p)<0 || recheck(p)<0) goto fail;
    close_owned(p,&slash);close_owned(p,&host_data);
    if (p->close_error) { errno=p->close_error;goto fail; }
    p->state=I_AVAILABLE;return GVI_OK;
fail:
    saved=errno?errno:EIO;close_owned(p,&slash);close_owned(p,&host_data);close_owned(p,&check);p->state=I_REFUSED;
    errno=saved;return saved==ENOENT || saved==ENOTDIR || saved==ENXIO ? GVI_NEED_PREPARED_STAGE : -1;
}
int gvi_begin_view(struct gvi_inputs *p,struct gvi_observation *observation) {
    struct gvo_plan plan;struct gvo_observation actual;int result,saved;
    if (!valid(p) || !observation || p->state!=I_AVAILABLE || p->begin_attempted) { errno=EINVAL;return -1; }
    memset(observation,0,sizeof(*observation));
    if (recheck(p)<0) { p->state=I_REFUSED;return -1; }
    p->begin_attempted=1;
    plan.image_witness_fd=p->fd[F_IMAGE];plan.private_data_witness_fd=p->fd[F_DATA];
    /* gvo stores its actual owner into our private cell before after-fork
     * failure. No cleanup path releases provider objects before known gvo local terminal0 or3. */
    result=gvo_begin(&plan,&p->view);saved=errno;
    if (p->view) p->state=I_VIEW;else p->state=I_REFUSED;
    if (result<0) { errno=saved;return -1; }
    result=gvo_receive_partial(p->view,&actual);
    if (!result) {
        observation->namespace_inode=actual.namespace_inode;
        observation->data_group=actual.data_group;
        observation->mirror_group=actual.mirror_group;
    }
    return result;
}
int gvi_close(struct gvi_inputs *p) {
    size_t i;int result;
    if (!valid(p)) return -1;
    if (p->state==I_CLOSED) return p->terminal;
    if (p->close_error) { errno=p->close_error;return GVI_HOLD; }
    if (p->view) {
        result=gvo_close(p->view);
        if (result!=0 && result!=GVO_LOCAL_RELEASED_KERNEL_UNCONFIRMED) return GVI_HOLD;
        p->terminal=result==GVO_LOCAL_RELEASED_KERNEL_UNCONFIRMED?GVI_LOCAL_RELEASED_KERNEL_UNCONFIRMED:0;
        p->view=NULL; /* source owner keeps its process-lifetime metadata tombstone */
    }
    /* Only known terminal local closure/reap (0 refusal or explicit3) permits
     * release of provider-owned sources. Unknown commit never reaches here. */
    for (i=0;i<F_COUNT;i++) close_owned(p,&p->fd[i]);
    if (p->close_error) { errno=p->close_error;return GVI_HOLD; }
    p->state=I_CLOSED;return p->terminal;
}
