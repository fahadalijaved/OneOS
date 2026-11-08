/* OneOS experimental guest root. No host root-manager APIs or host permission DB.
 * GPL-3.0-or-later. Linux/Android, built static for each supported ABI.
 * This is a session runtime, not a security boundary against hostile root code.
 */
#define _GNU_SOURCE
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <sys/ptrace.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/ioctl.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <linux/audit.h>
#include <stddef.h>
#include <fcntl.h>
#include <signal.h>
#include <errno.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define BASE "/data/adb/oneos"
#define SOCK BASE "/run/su.sock"
#define GRANTS BASE "/grants"
#define PACKAGES "/data/system/packages.list"
#define MANAGER "com.fahadali.oneos.guest"
#define MAX_CMD 65536
struct request { uint32_t magic, op, length; };
enum { RUN=1, LIST=2, GRANT=3, REVOKE=4, INFO=5 };
static int write_all(int fd, const void *buf, size_t n) {
    const char *p=buf;
    while(n) { ssize_t k=write(fd,p,n); if(k<0&&errno==EINTR)continue; if(k<=0)return -1; p+=k;n-=(size_t)k; }
    return 0;
}
static void reap(int sig) { (void)sig;while(waitpid(-1,NULL,WNOHANG)>0){} }
static int safe_package(const char *s) {
    if (!*s || strlen(s)>255)return 0;
    for(;*s;s++)if(!((*s>='a'&&*s<='z')||(*s>='A'&&*s<='Z')||(*s>='0'&&*s<='9')||*s=='_'||*s=='.'))return 0;
    return 1;
}
static int package_uid(const char *package, unsigned *uid) {
    FILE *f=fopen(PACKAGES,"re"); if(!f)return 0;
    char line[8192],p[256];unsigned u;int found=0;
    while(fgets(line,sizeof(line),f))if(sscanf(line,"%255s %u",p,&u)==2&&!strcmp(p,package)){*uid=u;found=1;break;}
    fclose(f);return found;
}
static int granted(const char *package,unsigned uid) {
    FILE *f=fopen(GRANTS,"re"); if(!f)return 0;
    char p[256];unsigned u;int found=0;
    while(fscanf(f,"%255s %u\n",p,&u)==2)if(u==uid&&!strcmp(package,p)){found=1;break;}
    fclose(f);return found;
}
static int allowed(unsigned uid) {
    if(uid==0)return 1; /* already-root guest boot helpers */
    FILE *f=fopen(PACKAGES,"re");if(!f)return 0;
    char line[8192],p[256];unsigned u;int found=0;
    while(fgets(line,sizeof(line),f))if(sscanf(line,"%255s %u",p,&u)==2&&u==uid&&granted(p,u)){found=1;break;}
    fclose(f);return found;
}
static int same_root(pid_t pid) {
    char p[64];struct stat peer,own;
    snprintf(p,sizeof(p),"/proc/%d/root",pid);
    return !stat(p,&peer)&&!stat("/",&own)&&peer.st_dev==own.st_dev&&peer.st_ino==own.st_ino;
}
/* Read-only KernelSU live state. The two magic words request a driver fd;
 * they are not Linux's reboot magic. No root profiles/features are changed.
 * ABI follows KernelSU uapi/supercall.h (GPL-2.0), ioctl-first API. */
static int host_audit(void) {
    if(getuid()!=0)return 1;
    int fd=-1;syscall(SYS_reboot,0xDEADBEEFUL,0xCAFEBABEUL,0,&fd);
    if(fd<0){fprintf(stderr,"OneOS: live root-provider audit unsupported\n");return 1;}
    unsigned manager=0;
    if(ioctl(fd,0x80004B0AUL,&manager)){close(fd);return 1;}
    printf("manager %u\n",manager);
    struct {uint16_t count,total;uint32_t uid[65535];} *list=calloc(1,sizeof(*list));
    if(!list){close(fd);return 1;}
    for(unsigned allow=0;allow<2;allow++){
        list->count=65535;
        unsigned long command=_IOC(_IOC_READ|_IOC_WRITE,'K',allow?6:7,4);
        if(ioctl(fd,command,list)){
            struct {uint32_t uid[128],count;uint8_t allow;} legacy={0};
            legacy.allow=(uint8_t)allow;
            if(ioctl(fd,allow?0xC0004B06UL:0xC0004B07UL,&legacy)||legacy.count>=128){free(list);close(fd);return 1;}
            list->count=(uint16_t)legacy.count;list->total=list->count;memcpy(list->uid,legacy.uid,list->count*sizeof(uint32_t));
        }
        if(list->count!=list->total){free(list);close(fd);return 1;}
        for(unsigned i=0;i<list->count;i++){
            struct {uint32_t uid;uint8_t value;} unmount={list->uid[i],0};
            if(ioctl(fd,0xC0004B09UL,&unmount)){free(list);close(fd);return 1;}
            printf("%s %u unmount=%u\n",allow?"allow":"deny",list->uid[i],unmount.value);
        }
    }
    free(list);close(fd);return 0;
}
static int edit_grant(const char *package,int add) {
    unsigned uid;if(!safe_package(package)||!package_uid(package,&uid))return -1;
    int fd=open(GRANTS ".new",O_CREAT|O_EXCL|O_WRONLY|O_CLOEXEC|O_NOFOLLOW,0600);if(fd<0)return -1;
    FILE *out=fdopen(fd,"w"),*in=fopen(GRANTS,"re");char p[256];unsigned u;
    if(!out){close(fd);unlink(GRANTS ".new");return -1;}
    if(in){while(fscanf(in,"%255s %u\n",p,&u)==2)if(strcmp(p,package))fprintf(out,"%s %u\n",p,u);fclose(in);}
    if(add)fprintf(out,"%s %u\n",package,uid);
    int ok=fflush(out)==0&&fsync(fd)==0; if(fclose(out))ok=0;
    if(!ok||rename(GRANTS ".new",GRANTS)){unlink(GRANTS ".new");return -1;}return 0;
}
static void list_apps(int out) {
    FILE *f=fopen(PACKAGES,"re");if(!f)return;
    char line[8192],p[256];unsigned u;
    while(fgets(line,sizeof(line),f))if(sscanf(line,"%255s %u",p,&u)==2&&u>=10000&&safe_package(p)&&strcmp(p,MANAGER))
        dprintf(out,"%s %u %d\n",p,u,granted(p,u));
    fclose(f);
}
/* Take exactly three stdio descriptors; close every delivered surplus fd,
 * including padding-sized fourth descriptors and subsequent SCM_RIGHTS headers.
 * The caller closes the retained descriptors even when this returns false. */
static int take_stdio_fds(struct msghdr *msg, int fds[3]) {
    size_t count=0;
    int malformed=0;
    for(struct cmsghdr *cm=CMSG_FIRSTHDR(msg);cm;cm=CMSG_NXTHDR(msg,cm)) {
        size_t remaining=(size_t)((char*)msg->msg_control+msg->msg_controllen-(char*)cm);
        if(cm->cmsg_len<CMSG_LEN(0)){malformed=1;break;}
        size_t length=cm->cmsg_len;
        if(length>remaining){length=remaining;malformed=1;}
        if(cm->cmsg_level!=SOL_SOCKET||cm->cmsg_type!=SCM_RIGHTS)continue;
        size_t bytes=length-CMSG_LEN(0);
        if(bytes%sizeof(int))malformed=1;
        for(size_t i=0;i<bytes/sizeof(int);i++) {
            int fd;memcpy(&fd,(char*)CMSG_DATA(cm)+i*sizeof(int),sizeof(fd));
            if(count<3)fds[count]=fd;else close(fd);
            count++;
        }
    }
    return count==3&&!malformed&&!(msg->msg_flags&(MSG_TRUNC|MSG_CTRUNC));
}
static void serve(int server) {
    /* Serialize management, fork only command jobs. Bound malformed clients. */
    for(;;){
        int c=accept4(server,NULL,NULL,SOCK_CLOEXEC);if(c<0){if(errno==EINTR)continue;exit(1);}
        struct timeval timeout={5,0};setsockopt(c,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
        struct ucred cred;socklen_t cl=sizeof(cred);
        char payload[sizeof(struct request)+MAX_CMD],control[CMSG_SPACE(3*sizeof(int))]={0};
        struct iovec iov={payload,sizeof(payload)};struct msghdr msg={0};
        msg.msg_iov=&iov;msg.msg_iovlen=1;msg.msg_control=control;msg.msg_controllen=sizeof(control);
        ssize_t n=recvmsg(c,&msg,MSG_CMSG_CLOEXEC);int fds[3]={-1,-1,-1};int status=126;
        int stdio_valid=n>=0&&take_stdio_fds(&msg,fds);
        struct request r={0};if(n>=(ssize_t)sizeof(r))memcpy(&r,payload,sizeof(r));
        int valid=n>=(ssize_t)sizeof(r)&&r.magic==0x4f535255&&r.length<MAX_CMD&&n==(ssize_t)(sizeof(r)+r.length)&&
            stdio_valid&&fds[0]>=0&&fds[1]>=0&&fds[2]>=0&&
            !getsockopt(c,SOL_SOCKET,SO_PEERCRED,&cred,&cl)&&same_root(cred.pid);
        if(valid){
            char *arg=payload+sizeof(r);arg[r.length]=0;unsigned manager=0;
            int admin=cred.uid==0||(package_uid(MANAGER,&manager)&&cred.uid==manager);
            if(r.op==INFO&&admin){dprintf(fds[1],"OneOS guest root API 1 manager=%s\n",MANAGER);status=0;}
            else if(r.op==LIST&&admin){list_apps(fds[1]);status=0;}
            else if((r.op==GRANT||r.op==REVOKE)&&admin)status=edit_grant(arg,r.op==GRANT)?1:0;
            else if(r.op==RUN&&(admin||allowed(cred.uid))){
                pid_t handler=fork();
                if(handler>0){for(int j=0;j<3;j++)close(fds[j]);close(c);continue;}
                if(handler<0){for(int j=0;j<3;j++)close(fds[j]);close(c);continue;}
                signal(SIGCHLD,SIG_DFL);
                pid_t job=fork();
                if(job==0){
                    close(server);close(c);setsid();
                    for(int j=0;j<3;j++)dup2(fds[j],j);
                    for(int j=0;j<3;j++)if(fds[j]>2)close(fds[j]);
                    clearenv();setenv("PATH","/system/bin:/system/xbin:/data/adb/ksu/bin",1);
                    setenv("HOME","/",1);setenv("USER","root",1);setenv("LOGNAME","root",1);
                    setenv("ANDROID_ROOT","/system",1);setenv("ANDROID_DATA","/data",1);
                    setenv("ANDROID_ART_ROOT","/apex/com.android.art",1);
                    setenv("ANDROID_I18N_ROOT","/apex/com.android.i18n",1);
                    setenv("ANDROID_TZDATA_ROOT","/apex/com.android.tzdata",1);
                    chdir("/");
                    if(!access("/data/oneos_genv.sh",R_OK)){
                        if(r.length)execl("/system/bin/sh","sh","/data/oneos_genv.sh","/system/bin/sh","-c",arg,NULL);
                        else execl("/system/bin/sh","sh","/data/oneos_genv.sh","/system/bin/sh",NULL);
                    }
                    if(r.length)execl("/system/bin/sh","sh","-c",arg,NULL);
                    else execl("/system/bin/sh","sh",NULL);
                    _exit(127);
                }
                close(server);
                if(job>0){int w=0;pid_t got;do{got=waitpid(job,&w,0);}while(got<0&&errno==EINTR);
                    status=got==job?(WIFEXITED(w)?WEXITSTATUS(w):128+WTERMSIG(w)):1;}
                (void)write_all(c,&status,sizeof(status));_exit(0);
            }else dprintf(fds[2],"OneOS: root permission denied; open Guest root in the OneOS guest app.\n");
        }
        (void)write_all(c,&status,sizeof(status));
        for(int j=0;j<3;j++)if(fds[j]>=0)close(fds[j]);close(c);
    }
}
/* Extract only plain files from OneOS's normalized stream. No ZIP installers run
 * as host root. openat(O_NOFOLLOW) checks every directory component. */
static int unpack(const char *dest) {
    int root=open(dest,O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if(root<0)return 1;
    char header[128],path[1024],buf[16384];unsigned count=0;uint64_t total=0;
    if(!fgets(header,sizeof(header),stdin)||strcmp(header,"ONEOS1\n")){close(root);return 1;}
    for(;;){
        unsigned len,mode;unsigned long long size;
        char extra;
        if(!fgets(header,sizeof(header),stdin)||!strchr(header,'\n')||sscanf(header,"%u %llu %o %c",&len,&size,&mode,&extra)!=3)break;
        if(!len){int extra=fgetc(stdin);close(root);return size==0&&mode==0&&extra==EOF?0:1;}
        if(len>=sizeof(path)||++count>50000||size>536870912ULL||(total+=size)>1073741824ULL)break;
        if(fread(path,1,len,stdin)!=len)break;path[len]=0;
        if(path[0]=='/'||memchr(path,0,len)||path[len-1]=='/')break;
        int dir=dup(root),bad=0;char *part=path,*next;
        while((next=strchr(part,'/'))){*next=0;
            if(!*part||!strcmp(part,".")||!strcmp(part,"..")){bad=1;break;}
            if(mkdirat(dir,part,0755)&&errno!=EEXIST){bad=1;break;}
            int child=openat(dir,part,O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);close(dir);dir=child;
            if(dir<0){bad=1;break;}part=next+1;
        }
        if(bad||!strcmp(part,".")||!strcmp(part,"..")){if(dir>=0)close(dir);break;}
        int out=openat(dir,part,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,(mode&0111)?0755:0644);close(dir);if(out<0)break;
        uint64_t left=size;while(left){size_t take=left>sizeof(buf)?sizeof(buf):(size_t)left;
            if(fread(buf,1,take,stdin)!=take||write_all(out,buf,take)){bad=1;break;}left-=take;}
        close(out);if(bad)break;
    }
    close(root);return 1;
}
static int client(int op,const char *arg) {
    int c=socket(AF_UNIX,SOCK_SEQPACKET|SOCK_CLOEXEC,0);if(c<0)return 1;
    struct sockaddr_un addr={.sun_family=AF_UNIX};strcpy(addr.sun_path,SOCK);
    if(connect(c,(struct sockaddr*)&addr,sizeof(addr))){perror("OneOS guest root");close(c);return 1;}
    size_t len=strlen(arg);if(len>=MAX_CMD){close(c);return 1;}
    struct request r={0x4f535255,(uint32_t)op,(uint32_t)len};struct iovec io[2]={{&r,sizeof(r)},{(void*)arg,len}};
    char control[CMSG_SPACE(3*sizeof(int))]={0};struct msghdr msg={0};
    msg.msg_iov=io;msg.msg_iovlen=2;msg.msg_control=control;msg.msg_controllen=sizeof(control);
    struct cmsghdr *cm=CMSG_FIRSTHDR(&msg);cm->cmsg_level=SOL_SOCKET;cm->cmsg_type=SCM_RIGHTS;cm->cmsg_len=CMSG_LEN(3*sizeof(int));
    int fds[3]={0,1,2};memcpy(CMSG_DATA(cm),fds,sizeof(fds));
    if(sendmsg(c,&msg,MSG_NOSIGNAL)<0){perror("sendmsg");close(c);return 1;}
    int status=1;if(recv(c,&status,sizeof(status),MSG_WAITALL)!=(ssize_t)sizeof(status))status=1;close(c);return status;
}
/* Prevent Vector's dex2oat helper from entering host init's mount namespace.
 * This filter is inherited across fork/exec; failure is fatal. */
static int guard_exec(char **argv) {
    struct sock_filter code[]={
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,arch)),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,AUDIT_ARCH_AARCH64,1,0),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,nr)),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,__NR_setns,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW)};
    struct sock_fprog filter={sizeof(code)/sizeof(code[0]),code};
    if(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0)||prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&filter)){perror("guest namespace guard");return 1;}
    execv(argv[0],argv);perror("exec");return 1;
}
/* Catch only our child's app_process exec, never seize host init or scan PIDs. */
static int launch(void) {
    pid_t pid=fork();if(pid<0)return 1;
    if(!pid){if(ptrace(PTRACE_TRACEME,0,0,0))_exit(126);execl("/data/zygote_exec","zygote_exec",NULL);_exit(127);}
    int w;char path[64],exe[512];snprintf(path,sizeof(path),"/proc/%d/exe",pid);
    for(int i=0;i<8;i++){
        if(waitpid(pid,&w,0)!=pid||!WIFSTOPPED(w))return 1;
        ssize_t n=readlink(path,exe,sizeof(exe)-1);if(n<0)return 1;exe[n]=0;
        if(strstr(exe,"/app_process64")){
            /* At an exec-event stop, DETACH's signal argument need not be
             * delivered. Queue a real SIGSTOP, detach without injecting a
             * signal, and confirm a group-stop before the tracer handoff. */
            if(kill(pid,SIGSTOP)||ptrace(PTRACE_DETACH,pid,0,0))return 1;
            pid_t stopped;
            do { stopped=waitpid(pid,&w,WUNTRACED); } while(stopped<0&&errno==EINTR);
            if(stopped!=pid||!WIFSTOPPED(w)||WSTOPSIG(w)!=SIGSTOP){kill(pid,SIGKILL);waitpid(pid,NULL,0);return 1;}
            char number[24];snprintf(number,sizeof(number),"%d",pid);
            pid_t injector=fork();if(!injector){execl(BASE "/bin/zygisk-ptrace64","zygisk-ptrace64","trace",number,"--spawn",NULL);_exit(127);}
            if(injector<0)return 1;int result;while(waitpid(injector,&result,0)<0&&errno==EINTR){}
            if(!WIFEXITED(result)||WEXITSTATUS(result)){kill(pid,SIGKILL);waitpid(pid,NULL,0);fprintf(stderr,"OneOS: guest injection failed; boot aborted\n");return 1;}
            FILE *proof=fopen(BASE "/run/injection.pid","we");
            if(proof){fprintf(proof,"%d\n",pid);fclose(proof);}
            kill(pid,SIGCONT);while(waitpid(pid,&w,0)<0&&errno==EINTR){}
            unlink(BASE "/run/injection.pid");return WIFEXITED(w)?WEXITSTATUS(w):1;
        }
        if(ptrace(PTRACE_SETOPTIONS,pid,0,(void*)(long)PTRACE_O_TRACEEXEC)||ptrace(PTRACE_CONT,pid,0,0))return 1;
    }
    kill(pid,SIGKILL);waitpid(pid,NULL,0);return 1;
}
int main(int argc,char **argv) {
    signal(SIGPIPE,SIG_IGN);
    if(argc==2&&!strcmp(argv[1],"--daemon")){
        if(getuid()!=0)return 1;umask(077);unlink(SOCK);
        int s=socket(AF_UNIX,SOCK_SEQPACKET|SOCK_CLOEXEC,0);struct sockaddr_un a={.sun_family=AF_UNIX};strcpy(a.sun_path,SOCK);
        if(s<0||bind(s,(struct sockaddr*)&a,sizeof(a))||chmod(SOCK,0666)||listen(s,16)){perror("guest root daemon");return 1;}
        signal(SIGCHLD,reap);serve(s);return 0;
    }
    if(argc==3&&!strcmp(argv[1],"--unpack"))return unpack(argv[2]);
    if(argc==2&&!strcmp(argv[1],"--host-audit"))return host_audit();
    if(argc>=3&&!strcmp(argv[1],"--guard-exec"))return getuid()?1:guard_exec(argv+2);
    if(argc==2&&!strcmp(argv[1],"--launch"))return getuid()?1:launch();
    if(argc==2&&!strcmp(argv[1],"--oneos-info"))return client(INFO,"");
    if(argc==2&&!strcmp(argv[1],"--oneos-list"))return client(LIST,"");
    if(argc==3&&!strcmp(argv[1],"--oneos-grant"))return client(GRANT,argv[2]);
    if(argc==3&&!strcmp(argv[1],"--oneos-revoke"))return client(REVOKE,argv[2]);
    if(argc==2&&(!strcmp(argv[1],"-v")||!strcmp(argv[1],"--version"))){puts("OneOS guest root prototype 1");return 0;}
    if(argc==2&&!strcmp(argv[1],"-V")){puts("1");return 0;}
    if(argc>=2&&(!strcmp(argv[1],"-mm")||!strcmp(argv[1],"-M")||!strcmp(argv[1],"--mount-master"))){argc--;argv++;}
    if(argc==1)return client(RUN,"");
    if(argc==3&&!strcmp(argv[1],"-c"))return client(RUN,argv[2]);
    if(argc==4&&(!strcmp(argv[1],"0")||!strcmp(argv[1],"root"))&&!strcmp(argv[2],"-c"))return client(RUN,argv[3]);
    fprintf(stderr,"Usage: su [-c command] | --oneos-list | --oneos-grant package | --oneos-revoke package\n");return 2;
}
