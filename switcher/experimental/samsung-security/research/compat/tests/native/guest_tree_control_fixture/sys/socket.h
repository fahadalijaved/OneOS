#ifndef ONEOS_GTC_TEST_SOCKET_H
#define ONEOS_GTC_TEST_SOCKET_H
#include <stddef.h>
#include <sys/types.h>
typedef unsigned socklen_t;
#define AF_UNIX 1
#define SOCK_SEQPACKET 5
#define SOCK_CLOEXEC 0x80000
#define SOCK_NONBLOCK 0x800
#define SOL_SOCKET 1
#define SO_PASSCRED 16
#define SCM_RIGHTS 1
#define SCM_CREDENTIALS 2
#define MSG_NOSIGNAL 0x4000
#define MSG_DONTWAIT 0x40
#define MSG_CMSG_CLOEXEC 0x40000000
#define MSG_TRUNC 0x20
#define MSG_CTRUNC 0x8
struct ucred { pid_t pid; uid_t uid; gid_t gid; };
struct iovec { void *iov_base; size_t iov_len; };
struct msghdr { struct iovec *msg_iov; size_t msg_iovlen; void *msg_control; size_t msg_controllen; int msg_flags; };
struct cmsghdr { size_t cmsg_len; int cmsg_level, cmsg_type; };
#define CMSG_ALIGN(n) (((n) + sizeof(size_t) - 1) & ~(sizeof(size_t) - 1))
#define CMSG_LEN(n) (CMSG_ALIGN(sizeof(struct cmsghdr)) + (n))
#define CMSG_SPACE(n) CMSG_ALIGN(CMSG_LEN(n))
#define CMSG_DATA(c) ((unsigned char *)(c) + CMSG_ALIGN(sizeof(struct cmsghdr)))
#define CMSG_FIRSTHDR(m) ((m)->msg_controllen >= sizeof(struct cmsghdr) ? (struct cmsghdr *)(m)->msg_control : NULL)
static inline struct cmsghdr *CMSG_NXTHDR(const struct msghdr *m, const struct cmsghdr *c) {
    size_t next = (size_t)((const unsigned char *)c - (const unsigned char *)m->msg_control) + CMSG_ALIGN(c->cmsg_len);
    return next + sizeof(*c) <= m->msg_controllen ? (struct cmsghdr *)((unsigned char *)m->msg_control + next) : NULL;
}
int socketpair(int domain, int type, int protocol, int out[2]);
int setsockopt(int fd, int level, int option, const void *value, socklen_t length);
ssize_t recvmsg(int fd, struct msghdr *message, int flags);
ssize_t sendmsg(int fd, const struct msghdr *message, int flags);
#endif
