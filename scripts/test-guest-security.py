#!/usr/bin/env python3
"""Execute native IPC and patched injection policies without a phone or root.

Requires a C/C++ compiler and Cargo with the pinned anyhow/libc crates cached.
Rust/C++ policy sources are taken from the committed NeoZygisk patch itself.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


def function(source, name):
    start = source.index('static int '+name+'(')
    brace = source.index('{', start)
    depth = 1
    end = brace+1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


class GuestSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='oneos-security-')
        cls.base = Path(cls.temp.name)
        cls.neo = cls.base/'neo'
        cls.neo.mkdir()
        for path in ['zygiskd/src/guest_policy.rs', 'loader/src/ptracer/guest_target.hpp']:
            subprocess.run(['git', 'apply', '--unidiff-zero', '--include='+path,
                            str(ROOT/'third_party/guest-runtime/neozygisk.patch')], cwd=cls.neo, check=True)
        source = (ROOT/'switcher/native/guest_root.c').read_text()
        fd_source = cls.base/'fds.c'
        fd_source.write_text(r'''
#include <sys/socket.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
''' + function(source, 'take_stdio_fds') + r'''
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); return 1; } } while(0)
int main(int argc, char **argv) {
    CHECK(argc==2);int mode=atoi(argv[1]), base=open("/dev/null",O_RDONLY);CHECK(base>=0);
    int fds[3]={-1,-1,-1}, delivered[64], count=0;
    char control[CMSG_SPACE(64*sizeof(int))]={0}, byte='x';
    struct iovec iov={&byte,1};struct msghdr msg={0};
    msg.msg_control=control;msg.msg_controllen=sizeof(control);msg.msg_iov=&iov;msg.msg_iovlen=1;
    if(mode==4 || mode==5) {
        count=mode==4?4:5;
        for(int i=0;i<count;i++){delivered[i]=dup(base);CHECK(delivered[i]>=0);}
        struct cmsghdr *cm=(struct cmsghdr*)control;
        cm->cmsg_level=SOL_SOCKET;cm->cmsg_type=SCM_RIGHTS;
        int first=mode==4?4:3;cm->cmsg_len=CMSG_LEN(first*sizeof(int));
        memcpy(CMSG_DATA(cm),delivered,first*sizeof(int));
        msg.msg_controllen=CMSG_SPACE(first*sizeof(int));
        if(mode==5) {
            cm=(struct cmsghdr*)(control+msg.msg_controllen);
            cm->cmsg_level=SOL_SOCKET;cm->cmsg_type=SCM_RIGHTS;cm->cmsg_len=CMSG_LEN(2*sizeof(int));
            memcpy(CMSG_DATA(cm),delivered+3,2*sizeof(int));msg.msg_controllen+=CMSG_SPACE(2*sizeof(int));
        }
    } else {
        int sockets[2];CHECK(socketpair(AF_UNIX,SOCK_DGRAM,0,sockets)==0);
        int number=mode==32?32:mode;CHECK(number>=1&&number<=32);
        struct cmsghdr *cm=CMSG_FIRSTHDR(&msg);cm->cmsg_level=SOL_SOCKET;cm->cmsg_type=SCM_RIGHTS;
        cm->cmsg_len=CMSG_LEN(number*sizeof(int));msg.msg_controllen=CMSG_SPACE(number*sizeof(int));
        for(int i=0;i<number;i++)memcpy((char*)CMSG_DATA(cm)+i*sizeof(int),&base,sizeof(int));
        CHECK(sendmsg(sockets[0],&msg,0)==1);
        memset(control,0,sizeof(control));msg.msg_controllen=CMSG_SPACE(3*sizeof(int));
        CHECK(recvmsg(sockets[1],&msg,0)==1);
        for(cm=CMSG_FIRSTHDR(&msg);cm;cm=CMSG_NXTHDR(&msg,cm)) {
            if(cm->cmsg_type!=SCM_RIGHTS)continue;
            size_t available=(size_t)(control+msg.msg_controllen-(char*)cm);
            size_t length=cm->cmsg_len<available?cm->cmsg_len:available;
            int n=(length-CMSG_LEN(0))/sizeof(int);
            for(int i=0;i<n;i++)memcpy(&delivered[count++],(char*)CMSG_DATA(cm)+i*sizeof(int),sizeof(int));
        }
        close(sockets[0]);close(sockets[1]);
        if(mode==32)CHECK(msg.msg_flags&MSG_CTRUNC);
    }
    CHECK(take_stdio_fds(&msg,fds)==(mode==3));
    for(int i=0;i<count;i++) {
        if(i<3){CHECK(fds[i]==delivered[i]);CHECK(fcntl(delivered[i],F_GETFD)>=0);close(fds[i]);}
        else {errno=0;CHECK(fcntl(delivered[i],F_GETFD)==-1&&errno==EBADF);}
    }
    CHECK(fcntl(base,F_GETFD)>=0);close(base);return 0;
}
''')
        cls.fd_binary = cls.base/'fds'
        subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror',str(fd_source),'-o',str(cls.fd_binary)],check=True)
        target_source=cls.base/'target.cpp'
        target_source.write_text('''#include "guest_target.hpp"
#include <cstdlib>
int main(int n,char **v) {
 if(n!=5)return 2;
 return guest_trace_target_is_child(1000000000,atoi(v[2]),v[1],v[3]) == (atoi(v[4])!=0) ? 0 : 1;
}
''')
        cls.target_binary=cls.base/'target'
        subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(cls.neo/'loader/src/ptracer'),str(target_source),'-o',str(cls.target_binary)],check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_scm_rights_closes_all_surplus_descriptors(self):
        for mode in [1,2,3,4,5,32]:
            with self.subTest(mode=mode):
                subprocess.run([self.fd_binary,str(mode)],check=True)

    def test_injector_accepts_only_callers_child_in_guest_root(self):
        with tempfile.TemporaryDirectory(dir=self.base) as d:
            root=Path(d);guest=root/'guest';host=root/'host';proc=root/'proc';pid=proc/'1000000000'
            guest.mkdir();host.mkdir();pid.mkdir(parents=True)
            (pid/'root').symlink_to(guest)
            cases=[('PPid:\t24680\n',24680,True),('PPid:\t12345\n',24680,False),('PPid:\t1\n',1,False),('PPid:\tinvalid\n',24680,False)]
            for status,caller,expected in cases:
                (pid/'status').write_text(status)
                subprocess.run([self.target_binary,str(proc),str(caller),str(guest),str(int(expected))],check=True)
            (pid/'status').write_text('PPid:\t24680\n');(pid/'root').unlink();(pid/'root').symlink_to(host)
            subprocess.run([self.target_binary,str(proc),'24680',str(guest),'0'],check=True)
            (pid/'root').unlink();(pid/'root').symlink_to(guest);(pid/'status').unlink()
            subprocess.run([self.target_binary,str(proc),'24680',str(guest),'0'],check=True)

    def test_peer_namespace_and_package_grant_policies(self):
        crate=self.base/'rust';(crate/'src').mkdir(parents=True)
        packages=tomllib.loads((ROOT/'third_party/guest-runtime/Cargo.lock').read_text())['package']
        versions={p['name']:p['version'] for p in packages if p['name'] in ('anyhow','libc')}
        (crate/'Cargo.toml').write_text('[package]\nname="oneos-policy-tests"\nversion="0.1.0"\nedition="2024"\n[dependencies]\n'+''.join(f'{name}="={version}"\n' for name,version in versions.items()))
        (crate/'src/lib.rs').write_text(f'#[path="{self.neo}/zygiskd/src/guest_policy.rs"]\nmod guest_policy;\n')
        result=subprocess.run(['cargo','test','--offline','--manifest-path',str(crate/'Cargo.toml')],capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)
        self.assertIn('8 passed',result.stdout)
        print(result.stdout)


if __name__ == '__main__':
    unittest.main()
