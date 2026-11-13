/* Authored host-only diagnostic owner. No generic command or inherited env. */
#ifndef HOST_PROBE_CORE_TEST
#define _GNU_SOURCE 1
#endif
#include <stdint.h>
#include <stddef.h>

#ifdef HOST_PROBE_CORE_TEST
#define CORE_API __declspec(dllexport)
#else
#define CORE_API static
#endif

enum { OWN_WAIT_READY=0, OWN_WAIT_PERMIT=1, OWN_MAY_EXEC=2, OWN_STOPPING=3,
       OWN_HOLD=4, OWN_REAPED=5, OWN_LOST=6 };
struct owner {
    int32_t pid, phase, owned, permit_attempted, term_attempted, kill_attempted;
    int32_t cancelled, reserved;
    uint64_t deadline_ms, kill_at_ms;
};
CORE_API void core_init(struct owner *o, int32_t pid, uint64_t now) {
    o->pid=pid; o->phase=OWN_WAIT_READY; o->owned=pid>0; o->permit_attempted=0;
    o->term_attempted=0; o->kill_attempted=0; o->cancelled=0; o->reserved=0;
    o->deadline_ms=now+30000; o->kill_at_ms=0;
}
CORE_API int core_can_signal(const struct owner *o) {
    return o->owned && o->pid>0 && o->phase!=OWN_REAPED && o->phase!=OWN_LOST;
}
CORE_API int core_begin_permit(struct owner *o, int ready_published, int valid,
                               uint64_t now) {
    if (!core_can_signal(o) || o->phase!=OWN_WAIT_PERMIT || !ready_published ||
        !valid || o->cancelled || now>=o->deadline_ms) return 0;
    /* Commit MAY_EXEC before any byte of the internal permit is attempted. */
    o->permit_attempted=1; o->phase=OWN_MAY_EXEC; return 1;
}
CORE_API void core_cancel(struct owner *o) {
    o->cancelled=1;
    if (core_can_signal(o)) o->phase=OWN_STOPPING;
}
CORE_API int core_signal_action(struct owner *o, uint64_t now) {
    if (now>=o->deadline_ms) core_cancel(o);
    if (!core_can_signal(o) || !o->cancelled) return 0;
    if (!o->term_attempted) {
        o->term_attempted=1; o->kill_at_ms=now+2000; return 15;
    }
    if (!o->kill_attempted && now>=o->kill_at_ms) {
        o->kill_attempted=1; return 9;
    }
    return 0;
}
CORE_API int core_finish_wait(struct owner *o, int32_t returned_pid, int terminal) {
    if (o->phase==OWN_REAPED || o->phase==OWN_LOST) return 0;
    if (returned_pid!=o->pid || !o->owned) {
        o->owned=0; o->phase=OWN_LOST; o->cancelled=1; return 0;
    }
    if (!terminal) { o->phase=OWN_HOLD; o->cancelled=1; return 0; }
    o->owned=0; o->phase=OWN_REAPED; return 1;
}
CORE_API int core_control(const unsigned char *line, uint32_t length,
                           const unsigned char *nonce) {
    static const unsigned char cancel[7]={'C','A','N','C','E','L','\n'};
    static const unsigned char prefix[7]={'P','E','R','M','I','T',' '};
    uint32_t i;
    if (length==7) {
        for (i=0;i<7;i++) if (line[i]!=cancel[i]) break;
        if (i==7) return 2;
    }
    if (length!=40 || line[39]!='\n') return 0;
    for (i=0;i<7;i++) if (line[i]!=prefix[i]) return 0;
    for (i=0;i<32;i++) {
        unsigned char c=line[7+i];
        if (!((c>='0'&&c<='9')||(c>='a'&&c<='f')) || c!=nonce[i]) return 0;
    }
    return 1;
}
CORE_API int core_env_value(const unsigned char *s, uint32_t n) {
    uint32_t i;
    if (!n || n>8192) return 0;
    for (i=0;i<n;i++) {
        unsigned char c=s[i];
        if (!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||
              c=='_'||c=='.'||c=='/'||c==':'||c=='+'||c=='-')) return 0;
    }
    return 1;
}
CORE_API int core_status_four(const unsigned char *text,uint32_t length,
                              const unsigned char *key,uint32_t key_length,
                              uint32_t output[4]) {
    uint32_t start=0,found=0,values[4]={0,0,0,0};
    if (!length || length>4095 || !key_length || key_length>8) return 0;
    while (start<length) {
        uint32_t end=start,p,i;
        while (end<length && text[end]!='\n') ++end;
        if (end-start>key_length && text[start+key_length]==':') {
            for(i=0;i<key_length;i++)if(text[start+i]!=key[i])break;
            if(i==key_length) {
                if(found++)return 0;
                p=start+key_length+1;
                for(i=0;i<4;i++) {
                    uint64_t value=0;uint32_t digits=0;
                    while(p<end&&(text[p]==' '||text[p]=='\t'))++p;
                    while(p<end&&text[p]>='0'&&text[p]<='9') {
                        value=value*10+(uint64_t)(text[p++]-'0');
                        if(++digits>10||value>UINT32_MAX)return 0;
                    }
                    if(!digits)return 0;
                    values[i]=(uint32_t)value;
                }
                while(p<end&&(text[p]==' '||text[p]=='\t'))++p;
                if(p!=end)return 0;
            }
        }
        start=end+1;
    }
    if(found!=1)return 0;
    for(uint32_t i=0;i<4;i++)output[i]=values[i];
    return 1;
}
#ifdef HOST_PROBE_CORE_TEST
CORE_API uint32_t core_owner_size(void) { return (uint32_t)sizeof(struct owner); }
#endif

#ifndef HOST_PROBE_CORE_TEST
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <sys/prctl.h>
#include <sys/random.h>
#include <unistd.h>
#include <fcntl.h>
#include <grp.h>
#include <signal.h>
#include <poll.h>
#include <time.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <dirent.h>
#include <limits.h>
#include "host_probe_profile.h"

#define LINE_MAXIMUM 8192
#define OUTPUT_MAXIMUM 65536
#define WIRE_MAXIMUM 262144
#define QUEUE_MAXIMUM 65536
#define CHILD_MAGIC 0x48505331u
enum { MSG_READY=1, MSG_SETUP_ERROR=2, MSG_EXEC_ATTEMPT=3, MSG_EXEC_ERROR=4 };
struct file_fact { int32_t fd; uint32_t mode; uint64_t dev,ino,size; };
struct ready_fact {
    int32_t pid,ppid; uint32_t uid[4],gid[4]; int32_t group,pdeathsig;
    char domain[128],ns[3][64]; struct file_fact files[6];
};
struct child_message { uint32_t magic,type; int32_t error,stage; struct ready_fact facts; };
static const char *const roles[6]={"framework","services","app_process","runtime","art","jar"};
static const char *const paths[6]={"/system/framework/framework.jar","/system/framework/services.jar",
    "/system/bin/app_process64","/system/lib64/libandroid_runtime.so",
    "/apex/com.android.art/lib64/libart.so",HOST_PROBE_JAR};
static volatile sig_atomic_t external_cancel;
static char queue_data[QUEUE_MAXIMUM];
static size_t queue_start,queue_end,wire_bytes;
static int output_failed,ready_published;
static size_t ready_end_position;
static uint64_t output_sequence;

static uint64_t now_ms(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_BOOTTIME,&t)!=0 || t.tv_sec<0) return UINT64_MAX;
    return (uint64_t)t.tv_sec*1000u+(uint64_t)t.tv_nsec/1000000u;
}
static void cancel_handler(int sig) { (void)sig; external_cancel=1; }
static int nonblock(int fd) {
    int f=fcntl(fd,F_GETFL); return f<0?-1:fcntl(fd,F_SETFL,f|O_NONBLOCK);
}
static void close_fd(int *fd) { if (*fd>=0) { close(*fd); *fd=-1; } }
static int event(const char *fmt,...) {
    char line[LINE_MAXIMUM]; va_list ap; int n;
    va_start(ap,fmt); n=vsnprintf(line,sizeof(line),fmt,ap); va_end(ap);
    if (n<0 || (size_t)n+1>=sizeof(line) || wire_bytes+(size_t)n+1>WIRE_MAXIMUM) {
        output_failed=1; return -1;
    }
    if (queue_start && queue_end+(size_t)n+1>sizeof(queue_data)) {
        size_t old=queue_start;
        memmove(queue_data,queue_data+queue_start,queue_end-queue_start);
        queue_end-=old; queue_start=0;
        if (ready_end_position) ready_end_position=ready_end_position>old?ready_end_position-old:0;
    }
    if (queue_end+(size_t)n+1>sizeof(queue_data)) { output_failed=1; return -1; }
    memcpy(queue_data+queue_end,line,(size_t)n); queue_end+=(size_t)n;
    queue_data[queue_end++]='\n'; wire_bytes+=(size_t)n+1; return 0;
}
static void flush_output(void) {
    if(output_failed)return;
    while (queue_start<queue_end) {
        ssize_t n=write(STDOUT_FILENO,queue_data+queue_start,queue_end-queue_start);
        if (n>0) {
            queue_start+=(size_t)n;
            if (ready_end_position && queue_start>=ready_end_position) ready_published=1;
        } else if (n<0 && errno==EINTR) break;
        else if (n<0 && (errno==EAGAIN||errno==EWOULDBLOCK)) break;
        else { output_failed=1; break; }
    }
    if (queue_start==queue_end) { queue_start=queue_end=0; ready_end_position=0; }
}
static int send_child(int fd,struct child_message *m) {
    size_t p=0; m->magic=CHILD_MAGIC;
    while (p<sizeof(*m)) {
        ssize_t n=write(fd,(const unsigned char *)m+p,sizeof(*m)-p);
        if (n>0) p+=(size_t)n;
        else if (n<0 && errno==EINTR) continue;
        else return -1;
    }
    return 0;
}
static void child_fail(int fd,int stage) {
    struct child_message m; int saved=errno;
    memset(&m,0,sizeof(m)); m.type=MSG_SETUP_ERROR; m.stage=stage; m.error=saved;
    (void)send_child(fd,&m); _exit(70);
}
static int exact_status_four(const char *text,const char *key,uint32_t out[4]) {
    return core_status_four((const unsigned char *)text,(uint32_t)strlen(text),
                            (const unsigned char *)key,(uint32_t)strlen(key),out)?0:-1;
}
static int read_bounded(const char *path,char *out,size_t cap) {
    int fd=open(path,O_RDONLY|O_CLOEXEC); size_t p=0;
    if (fd<0) return -1;
    while (p<cap-1) {
        ssize_t n=read(fd,out+p,cap-1-p);
        if (n>0) p+=(size_t)n;
        else if (!n) { out[p]=0;close(fd);return 0; }
        else if (errno!=EINTR) { close(fd);return -1; }
    }
    close(fd);errno=EOVERFLOW;return -1;
}
static int safe_label(char *s,int namespace_label) {
    size_t n=strlen(s);
    if (n && s[n-1]=='\n') s[--n]=0;
    if (!n) return -1;
    for (size_t i=0;i<n;i++) {
        unsigned char c=(unsigned char)s[i];
        if (!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||
              c=='_'||c==':'||c=='-'||c=='.'||c==','||(namespace_label&&(c=='['||c==']')))) return -1;
    }
    return 0;
}
static void child_main(pid_t supervisor,int gate,int status,int out,int err) {
    struct child_message m; gid_t group=1000; uid_t ur,ue,us; gid_t gr,ge,gs;
    char proc_status[4096]; int nullfd=-1; sigset_t mask;
    memset(&m,0,sizeof(m));
    signal(SIGPIPE,SIG_DFL);signal(SIGTERM,SIG_DFL);signal(SIGINT,SIG_DFL);
    signal(SIGHUP,SIG_DFL);signal(SIGCHLD,SIG_DFL);sigemptyset(&mask);
    if (sigprocmask(SIG_SETMASK,&mask,NULL)!=0) child_fail(status,1);
    if (prctl(PR_SET_PDEATHSIG,SIGKILL)!=0 || getppid()!=supervisor) child_fail(status,2);
    if (setgroups(1,&group)!=0 || setresgid(1000,1000,1000)!=0 || setresuid(1000,1000,1000)!=0) child_fail(status,3);
    /* Credential transitions clear PDEATHSIG; arm before final parent check. */
    if (prctl(PR_SET_PDEATHSIG,SIGKILL)!=0 || getppid()!=supervisor) child_fail(status,4);
    if (getresuid(&ur,&ue,&us)!=0 || getresgid(&gr,&ge,&gs)!=0 || ur!=1000||ue!=1000||us!=1000||gr!=1000||ge!=1000||gs!=1000) child_fail(status,5);
    if (getgroups(1,&group)!=1 || group!=1000) child_fail(status,6);
    if (read_bounded("/proc/self/status",proc_status,sizeof(proc_status))!=0 ||
        exact_status_four(proc_status,"Uid",m.facts.uid)!=0 || exact_status_four(proc_status,"Gid",m.facts.gid)!=0) child_fail(status,7);
    for (int i=0;i<4;i++) if (m.facts.uid[i]!=1000||m.facts.gid[i]!=1000) { errno=EPERM;child_fail(status,8); }
    if (read_bounded("/proc/self/attr/current",m.facts.domain,sizeof(m.facts.domain))!=0 || safe_label(m.facts.domain,0)!=0) child_fail(status,9);
    const char *const ns_paths[3]={"/proc/self/ns/mnt","/proc/self/ns/pid","/proc/self/ns/user"};
    for (int i=0;i<3;i++) {
        ssize_t n=readlink(ns_paths[i],m.facts.ns[i],sizeof(m.facts.ns[i])-1);
        if (n<1||(size_t)n>=sizeof(m.facts.ns[i])-1) child_fail(status,10);
        m.facts.ns[i][n]=0;if(safe_label(m.facts.ns[i],1)!=0) child_fail(status,11);
    }
    for (int i=0;i<6;i++) {
        struct stat st; int fd=open(paths[i],O_RDONLY|O_CLOEXEC);
        int file_flags=fd<0?-1:fcntl(fd,F_GETFL),fd_flags=fd<0?-1:fcntl(fd,F_GETFD);
        if (fd<0||file_flags<0||fd_flags<0||fstat(fd,&st)!=0||!S_ISREG(st.st_mode)||st.st_size<0||
            (file_flags&O_ACCMODE)!=O_RDONLY||(fd_flags&FD_CLOEXEC)!=FD_CLOEXEC) child_fail(status,12);
        m.facts.files[i].fd=fd;m.facts.files[i].mode=(uint32_t)st.st_mode;
        m.facts.files[i].dev=(uint64_t)st.st_dev;m.facts.files[i].ino=(uint64_t)st.st_ino;m.facts.files[i].size=(uint64_t)st.st_size;
    }
    nullfd=open("/dev/null",O_RDONLY|O_CLOEXEC);
    if (nullfd<0||dup2(nullfd,0)<0||dup2(out,1)<0||dup2(err,2)<0) child_fail(status,13);
    close(nullfd);close(out);close(err);
    m.facts.pid=getpid();m.facts.ppid=getppid();m.facts.group=1000;
    if (prctl(PR_GET_PDEATHSIG,&m.facts.pdeathsig)!=0||m.facts.pdeathsig!=SIGKILL||m.facts.ppid!=supervisor) child_fail(status,14);
    m.type=MSG_READY;if(send_child(status,&m)!=0)_exit(70);
    unsigned char permit=0;ssize_t n;
    do {n=read(gate,&permit,1);}while(n<0&&errno==EINTR);
    close(gate);
    if(n!=1||permit!=0xa5||getppid()!=supervisor)_exit(70);
    m.type=MSG_EXEC_ATTEMPT;if(send_child(status,&m)!=0)_exit(70);
    /* Kept descriptors are O_CLOEXEC. Exec/domain transitions may clear PDEATHSIG
       or revalidate FDs; no postexec parent-death/FD-survival guarantee is made. */
    execve("/system/bin/app_process64",host_probe_argv,host_probe_env);
    m.type=MSG_EXEC_ERROR;m.error=errno;(void)send_child(status,&m);_exit(71);
}
static int ready_event(const struct ready_fact *r,const char *nonce,struct owner *o) {
    char fds[2048];size_t p=0;uint64_t now=now_ms();
    if(r->pid!=o->pid||r->ppid!=getpid()||r->group!=1000||r->pdeathsig!=9||now>=o->deadline_ms)return -1;
    for(int i=0;i<4;i++)if(r->uid[i]!=1000||r->gid[i]!=1000)return -1;
    for(int i=0;i<6;i++) {
        int n=snprintf(fds+p,sizeof(fds)-p,"%s{\"role\":\"%s\",\"fd\":%d,\"dev\":\"%llu\",\"ino\":\"%llu\",\"size\":\"%llu\",\"mode\":%u}",i?",":"",roles[i],r->files[i].fd,(unsigned long long)r->files[i].dev,(unsigned long long)r->files[i].ino,(unsigned long long)r->files[i].size,r->files[i].mode);
        if(n<0||(size_t)n>=sizeof(fds)-p)return -1;p+=(size_t)n;
    }
    int rc=event("{\"v\":1,\"event\":\"READY\",\"nonce\":\"%s\",\"pid\":%d,\"ppid\":%d,\"uid\":[1000,1000,1000,1000],\"gid\":[1000,1000,1000,1000],\"groups\":[1000],\"pdeathsig\":9,\"domain\":\"%s\",\"ns\":{\"mnt\":\"%s\",\"pid\":\"%s\",\"user\":\"%s\"},\"profile_sha256\":\"%s\",\"deadline_boottime_ms\":%llu,\"remaining_ms\":%llu,\"fds\":[%s]}",nonce,r->pid,r->ppid,r->domain,r->ns[0],r->ns[1],r->ns[2],HOST_PROBE_PROFILE_SHA,(unsigned long long)o->deadline_ms,(unsigned long long)(o->deadline_ms-now),fds);
    if(!rc)ready_end_position=queue_end;return rc;
}
static void output_chunk(int *fd,const char *stream,size_t *total,int *complete,struct owner *o) {
    unsigned char bytes[256];char hex[513];ssize_t n;
    for(;;) {
        n=read(*fd,bytes,sizeof(bytes));
        if(n>0) {
            if(*total+(size_t)n>OUTPUT_MAXIMUM){core_cancel(o);close_fd(fd);return;}
            *total+=(size_t)n;
            for(ssize_t i=0;i<n;i++){static const char digits[]="0123456789abcdef";hex[2*i]=digits[bytes[i]>>4];hex[2*i+1]=digits[bytes[i]&15];}hex[2*n]=0;
            if(event("{\"v\":1,\"event\":\"OUTPUT\",\"stream\":\"%s\",\"seq\":%llu,\"hex\":\"%s\"}",stream,(unsigned long long)++output_sequence,hex)!=0){core_cancel(o);close_fd(fd);return;}
            flush_output();
        }else if(!n){*complete=1;close_fd(fd);return;}
        else if(errno==EINTR)return;
        else if(errno==EAGAIN||errno==EWOULDBLOCK)return;
        else{core_cancel(o);close_fd(fd);return;}
    }
}
static int validate_profile(void) {
    static const char *const keys[10]={"PATH=","ANDROID_ROOT=","ANDROID_DATA=","ANDROID_I18N_ROOT=","ANDROID_TZDATA_ROOT=","BOOTCLASSPATH=","DEX2OATBOOTCLASSPATH=","SYSTEMSERVERCLASSPATH=","STANDALONE_SYSTEMSERVER_JARS=","CLASSPATH="};
    for(int i=0;i<10;i++) {
        size_t n=strlen(keys[i]);if(!host_probe_env[i]||strncmp(host_probe_env[i],keys[i],n)||!core_env_value((const unsigned char *)host_probe_env[i]+n,(uint32_t)strlen(host_probe_env[i]+n)))return -1;
    }
    if(host_probe_env[10]!=NULL||strcmp(host_probe_env[9],"CLASSPATH=" HOST_PROBE_JAR))return -1;
    static const char *const expected[4]={"/system/bin/app_process64","/system/bin","com.appleexploit.oneos.security.probe.SamsungContextProbe","--host-context-probe"};
    for(int i=0;i<4;i++)if(!host_probe_argv[i]||strcmp(host_probe_argv[i],expected[i]))return -1;
    return host_probe_argv[4]==NULL?0:-1;
}
static int close_inherited(void) {
    DIR *dir=opendir("/proc/self/fd");struct dirent *entry;int count=0;
    if(!dir)return -1;
    int keep=dirfd(dir);
    for(;;) {
        errno=0;entry=readdir(dir);
        if(!entry){int error=errno;closedir(dir);errno=error;return error?-1:0;}
        if(entry->d_name[0]=='.')continue;
        char *end=NULL;errno=0;long fd=strtol(entry->d_name,&end,10);
        if(errno||!end||*end||fd<0||fd>INT_MAX||++count>256){closedir(dir);errno=EOVERFLOW;return -1;}
        if(fd>2&&fd!=keep&&close((int)fd)!=0){int error=errno;closedir(dir);errno=error;return -1;}
    }
}
static int early_fail(const char *reason,int error,int code) {
    (void)nonblock(1);(void)event("{\"v\":1,\"event\":\"FAIL\",\"reason\":\"%s\",\"errno\":%d}",reason,error);flush_output();return code;
}
int main(int argc,char **argv) {
    int gate[2]={-1,-1},status[2]={-1,-1},out[2]={-1,-1},err[2]={-1,-1};
    struct sigaction sa;sigset_t mask;struct owner own;uid_t a,b,c;uint64_t start;
    if(argc!=2||strcmp(argv[1],"--host-context-supervisor-v1"))return early_fail("ARGUMENTS",0,64);
    if(getresuid(&a,&b,&c)!=0||a||b||c||validate_profile()!=0)return early_fail("ROOT_OR_PROFILE",errno,77);
    start=now_ms();if(start==UINT64_MAX||start>UINT64_MAX-32000)return early_fail("CLOCK",errno,70);
    memset(&sa,0,sizeof(sa));sigemptyset(&sa.sa_mask);sa.sa_handler=SIG_DFL;
    if(sigaction(SIGCHLD,&sa,NULL)!=0)return early_fail("SIGNALS",errno,70); /* no SIG_IGN/SA_NOCLDWAIT */
    sa.sa_handler=SIG_IGN;if(sigaction(SIGPIPE,&sa,NULL)!=0)return early_fail("SIGNALS",errno,70);
    sa.sa_handler=cancel_handler;
    if(sigaction(SIGTERM,&sa,NULL)||sigaction(SIGINT,&sa,NULL)||sigaction(SIGHUP,&sa,NULL))return early_fail("SIGNALS",errno,70);
    sigemptyset(&mask);if(sigprocmask(SIG_SETMASK,&mask,NULL)!=0)return early_fail("SIGNALS",errno,70);
    if(fcntl(2,F_GETFD)<0||close_inherited()!=0||nonblock(0)||nonblock(1)||pipe2(gate,O_CLOEXEC)||pipe2(status,O_CLOEXEC)||pipe2(out,O_CLOEXEC)||pipe2(err,O_CLOEXEC))return early_fail("DESCRIPTORS",errno,70);
    pid_t supervisor=getpid(),pid=fork();
    if(pid<0)return early_fail("FORK",errno,70);
    if(pid==0){close(gate[1]);close(status[0]);close(out[0]);close(err[0]);child_main(supervisor,gate[0],status[1],out[1],err[1]);_exit(70);}
    close_fd(&gate[0]);close_fd(&status[1]);close_fd(&out[1]);close_fd(&err[1]);
    core_init(&own,pid,start);
    if(nonblock(gate[1])||nonblock(status[0])||nonblock(out[0])||nonblock(err[0]))core_cancel(&own);
    unsigned char control[80],packet[sizeof(struct child_message)];size_t control_used=0,packet_used=0,total_child=0;
    char nonce[33]={0};int ready_seen=0,exec_seen=0,status_eof=0,out_complete=0,err_complete=0,hold_sent=0,reaped=0,wait_status=0,terminal_sent=0,clock_lost=0,input_fd=0;
    uint64_t reaped_at=0;
    for(;;) {
        uint64_t now=now_ms();
        if(now==UINT64_MAX){if(!clock_lost)event("{\"v\":1,\"event\":\"FAIL\",\"reason\":\"CLOCK_LOST\",\"errno\":%d}",errno);clock_lost=1;core_cancel(&own);}
        if(external_cancel||output_failed)core_cancel(&own);
        if(own.owned) {
            siginfo_t info;memset(&info,0,sizeof(info));
            if(waitid(P_PID,(id_t)pid,&info,WEXITED|WNOHANG|WNOWAIT)<0) {
                if(errno!=EINTR){own.owned=0;own.phase=OWN_LOST;own.cancelled=1;event("{\"v\":1,\"event\":\"HOLD\",\"pid\":%d,\"reason\":\"OWNERSHIP_LOST\",\"owned_unreaped\":false}",pid);hold_sent=1;}
            }else if(info.si_pid) {
                if(info.si_pid!=pid){own.owned=0;own.phase=OWN_LOST;own.cancelled=1;}
                else if(info.si_code!=CLD_EXITED&&info.si_code!=CLD_KILLED&&info.si_code!=CLD_DUMPED){core_cancel(&own);own.phase=OWN_HOLD;}
                else {
                    pid_t got=waitpid(pid,&wait_status,WNOHANG);
                    if(got==pid&&core_finish_wait(&own,got,WIFEXITED(wait_status)||WIFSIGNALED(wait_status))){reaped=1;reaped_at=now;close_fd(&gate[1]);}
                    else if(got<0&&errno!=EINTR){own.owned=0;own.phase=OWN_LOST;own.cancelled=1;}
                }
            }
        }
        if(own.cancelled)close_fd(&gate[1]);
        if(own.phase==OWN_LOST&&!hold_sent){event("{\"v\":1,\"event\":\"HOLD\",\"pid\":%d,\"reason\":\"OWNERSHIP_LOST\",\"owned_unreaped\":false}",pid);hold_sent=1;}
        if(own.phase==OWN_HOLD&&!own.kill_attempted&&!hold_sent){event("{\"v\":1,\"event\":\"HOLD\",\"pid\":%d,\"reason\":\"NONTERMINAL_WAIT\",\"owned_unreaped\":true}",pid);hold_sent=1;}
        if(!reaped && own.phase!=OWN_LOST) {
            int action=0;
            if(clock_lost){if(core_can_signal(&own)&&!own.kill_attempted){own.kill_attempted=1;action=9;}}
            else action=core_signal_action(&own,now);
            if(action) {
                close_fd(&gate[1]);int rc=kill(pid,action),saved=rc<0?errno:0;
                event("{\"v\":1,\"event\":\"SIGNAL\",\"pid\":%d,\"signal\":%d,\"rc\":%d,\"errno\":%d}",pid,action,rc,saved);
            }
            if(own.kill_attempted&&!hold_sent){own.phase=OWN_HOLD;event("{\"v\":1,\"event\":\"HOLD\",\"pid\":%d,\"reason\":\"%s\",\"owned_unreaped\":true}",pid,clock_lost?"UNREAPED_CLOCK_LOST":"UNREAPED");hold_sent=1;}
        }
        if(status[0]>=0)for(;;) {
            ssize_t n=read(status[0],packet+packet_used,sizeof(packet)-packet_used);
            if(n>0) {
                packet_used+=(size_t)n;if(packet_used<sizeof(packet))continue;
                struct child_message msg;memcpy(&msg,packet,sizeof(msg));packet_used=0;
                if(msg.magic!=CHILD_MAGIC){core_cancel(&own);break;}
                if(msg.type==MSG_READY && !ready_seen && own.phase==OWN_WAIT_READY) {
                    unsigned char random[16];size_t used=0;
                    while(used<sizeof(random)&&!external_cancel&&now_ms()<own.deadline_ms){ssize_t count=getrandom(random+used,sizeof(random)-used,GRND_NONBLOCK);if(count>0)used+=(size_t)count;else if(count<0&&errno==EINTR)continue;else break;}
                    if(used!=sizeof(random)){event("{\"v\":1,\"event\":\"FAIL\",\"reason\":\"NONCE_UNAVAILABLE\",\"errno\":%d}",errno);core_cancel(&own);continue;}
                    for(size_t i=0;i<16;i++){static const char digits[]="0123456789abcdef";nonce[2*i]=digits[random[i]>>4];nonce[2*i+1]=digits[random[i]&15];}
                    if(ready_event(&msg.facts,nonce,&own)!=0){core_cancel(&own);continue;}
                    own.phase=OWN_WAIT_PERMIT;ready_seen=1;
                }else if(msg.type==MSG_SETUP_ERROR){event("{\"v\":1,\"event\":\"FAIL\",\"reason\":\"CHILD_SETUP\",\"errno\":%d}",msg.error);core_cancel(&own);}
                else if(msg.type==MSG_EXEC_ATTEMPT&&own.permit_attempted&&!exec_seen){exec_seen=1;event("{\"v\":1,\"event\":\"EXEC_ATTEMPTED\",\"pid\":%d}",pid);}
                else if(msg.type==MSG_EXEC_ERROR&&exec_seen){event("{\"v\":1,\"event\":\"EXEC_ERROR\",\"pid\":%d,\"errno\":%d}",pid,msg.error);core_cancel(&own);}
                else core_cancel(&own);
            }else if(!n){if(packet_used)core_cancel(&own);status_eof=1;close_fd(&status[0]);event("{\"v\":1,\"event\":\"EXEC_PIPE_CLOSED\",\"pid\":%d,\"ambiguous\":true}",pid);break;}
            else if(errno==EINTR)break;
            else if(errno==EAGAIN||errno==EWOULDBLOCK)break;
            else{core_cancel(&own);close_fd(&status[0]);break;}
        }
        if(out[0]>=0)output_chunk(&out[0],"stdout",&total_child,&out_complete,&own);
        if(err[0]>=0)output_chunk(&err[0],"stderr",&total_child,&err_complete,&own);
        if(!reaped&&input_fd>=0) {
            unsigned char input[80];ssize_t n=read(input_fd,input,sizeof(input));
            if(n>0)for(ssize_t i=0;i<n;i++) {
                if(control_used==sizeof(control)){core_cancel(&own);break;}
                control[control_used++]=input[i];if(input[i]!='\n')continue;
                int command=core_control(control,(uint32_t)control_used,(const unsigned char *)nonce);control_used=0;
                if(command==2)core_cancel(&own);
                else if(command==1&&!external_cancel&&!output_failed&&core_begin_permit(&own,ready_published,1,now_ms())) {
                    if(event("{\"v\":1,\"event\":\"PERMIT_ATTEMPTED\",\"pid\":%d}",pid)!=0||output_failed||external_cancel||now_ms()>=own.deadline_ms){core_cancel(&own);close_fd(&gate[1]);}
                    else{unsigned char permit=0xa5;ssize_t sent=write(gate[1],&permit,1);close_fd(&gate[1]);if(sent!=1)core_cancel(&own);}
                }else core_cancel(&own);
            }
            else if(!n){core_cancel(&own);close_fd(&input_fd);}
            else if(errno!=EINTR&&errno!=EAGAIN&&errno!=EWOULDBLOCK){core_cancel(&own);close_fd(&input_fd);}
        }
        flush_output();
        if(reaped) {
            if(!terminal_sent && ((out_complete&&err_complete&&status_eof)||clock_lost||now-reaped_at>=2000)) {
                event("{\"v\":1,\"event\":\"REAPED\",\"pid\":%d,\"kind\":\"%s\",\"status\":%d,\"permit_attempted\":%s,\"exec_attempt_observed\":%s,\"stdout_complete\":%s,\"stderr_complete\":%s,\"cancelled\":%s}",pid,WIFEXITED(wait_status)?"exit":"signal",WIFEXITED(wait_status)?WEXITSTATUS(wait_status):WTERMSIG(wait_status),own.permit_attempted?"true":"false",exec_seen?"true":"false",out_complete?"true":"false",err_complete?"true":"false",own.cancelled?"true":"false");terminal_sent=1;
            }
            flush_output();
            if(terminal_sent && (queue_start==queue_end||clock_lost||now-reaped_at>=2000))return(!own.cancelled&&!output_failed&&out_complete&&err_complete&&status_eof&&queue_start==queue_end&&WIFEXITED(wait_status)&&WEXITSTATUS(wait_status)==0)?0:1;
        }
        struct pollfd pf[5]={{input_fd,POLLIN,0},{status[0],POLLIN,0},{out[0],POLLIN,0},{err[0],POLLIN,0},{output_failed?-1:1,queue_start<queue_end?POLLOUT:0,0}};
        (void)poll(pf,5,20); /* Absolute BOOTTIME is checked again, including EINTR. */
    }
}
#endif
