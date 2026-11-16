/*
 * OneOS (0.5.17): Nothing OS's Essential key on a Galaxy, from a double press of Volume Down.
 *
 * Nothing's PhoneWindowManager hands a key with scan code 250 to its Essential key service, but only for a key
 * that was not injected: interceptKeyBeforeQueueing resets its gesture detector and skips handleKeyGesture for any
 * event whose policy flags say "injected" (0x40000), so InputManager.injectInputEvent (the first try, the Java
 * OneOSEssentialKey) never reached it (owner's A36: Essential Space's "Double-Click to Continue" ignored it).
 * This makes a small virtual keyboard with uinput that can only send key 250, so the guest's input reader sees a
 * hardware key, and watches the volume keys (read-only, never grabbed: Volume Down still changes the volume):
 *  - a second Volume Down press within WINDOW_MS of the first, released within LONG_MS: an Essential double click
 *    (Essential Space);
 *  - the second press held: an Essential long press for as long as it is held (record).
 *
 * The key reaches Nothing's PhoneWindowManager as a hardware key (scanCode=250, owner's A36), but Nothing's Essential
 * key service only forwards it to Essential Space once it has connected at boot on a phone with Nothing's key, which a
 * Galaxy never has: so [action], when given, is run too (oneos_switch.sh: open Essential Space in the guest).
 *
 * Usage: oneos_essential_key <guest system_server pid> [action command]   (as root; ends when that process is gone)
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define KEY_ESSENTIAL 250
#define WINDOW_MS 600
#define LONG_MS 400
#define MAX_DEV 16

static long long now_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static int alive(const char *pid) {
    char p[64];
    struct stat st;
    snprintf(p, sizeof p, "/proc/%s", pid);
    return stat(p, &st) == 0;
}

static void emit(int fd, int type, int code, int value) {
    struct input_event e;
    memset(&e, 0, sizeof e);
    e.type = type;
    e.code = code;
    e.value = value;
    if (write(fd, &e, sizeof e) != (ssize_t)sizeof e) fprintf(stderr, "uinput write: %s\n", strerror(errno));
}

static void key(int fd, int value) {
    emit(fd, EV_KEY, KEY_ESSENTIAL, value);
    emit(fd, EV_SYN, SYN_REPORT, 0);
}

/* The action, detached: a slow am start must not hold the key watch. */
static void run_action(const char *cmd) {
    if (!cmd || !*cmd) return;
    pid_t p = fork();
    if (p == 0) {
        if (fork() == 0) { execl("/system/bin/sh", "sh", "-c", cmd, (char *)NULL); _exit(127); }
        _exit(0);
    }
    if (p > 0) waitpid(p, NULL, 0);
}

static int has_voldown(int fd) {
    unsigned char bits[KEY_MAX / 8 + 1];
    memset(bits, 0, sizeof bits);
    if (ioctl(fd, EVIOCGBIT(EV_KEY, sizeof bits), bits) < 0) return 0;
    return (bits[KEY_VOLUMEDOWN / 8] >> (KEY_VOLUMEDOWN % 8)) & 1;
}

static int make_uinput(void) {
    int fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) return -1;
    if (ioctl(fd, UI_SET_EVBIT, EV_KEY) < 0 || ioctl(fd, UI_SET_KEYBIT, KEY_ESSENTIAL) < 0) { close(fd); return -1; }
    struct uinput_setup s;
    memset(&s, 0, sizeof s);
    s.id.bustype = BUS_VIRTUAL;
    s.id.vendor = 0x4f4e;  /* "ON" */
    s.id.product = 0x4553; /* "ES" */
    s.id.version = 1;
    strncpy(s.name, "OneOS Essential Key", UINPUT_MAX_NAME_SIZE - 1);
    if (ioctl(fd, UI_DEV_SETUP, &s) < 0 || ioctl(fd, UI_DEV_CREATE) < 0) { close(fd); return -1; }
    return fd;
}

int main(int argc, char **argv) {
    if (argc < 2 || argc > 3 || !argv[1][0] || strspn(argv[1], "0123456789") != strlen(argv[1])) {
        fprintf(stderr, "usage: %s <guest system_server pid>\n", argv[0]);
        return 2;
    }
    setvbuf(stdout, NULL, _IOLBF, 0);
    const char *guest = argv[1];

    struct pollfd pfd[MAX_DEV];
    int n = 0;
    DIR *d = opendir("/dev/input");
    if (!d) { printf("no /dev/input: %s\n", strerror(errno)); return 1; }
    struct dirent *de;
    while ((de = readdir(d)) && n < MAX_DEV) {
        if (strncmp(de->d_name, "event", 5)) continue;
        char p[300];
        snprintf(p, sizeof p, "/dev/input/%s", de->d_name);
        int fd = open(p, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0) continue;
        if (has_voldown(fd)) { pfd[n].fd = fd; pfd[n].events = POLLIN; n++; } else close(fd);
    }
    closedir(d);
    if (!n) { printf("no input device with Volume Down; exiting\n"); return 1; }

    int ui = make_uinput();
    if (ui < 0) { printf("could not create the uinput key: %s; exiting\n", strerror(errno)); return 1; }
    /* The guest has its own /dev: print this key's event node (major:minor) for oneos_switch.sh to make there. */
    char sys[64] = "";
    if (ioctl(ui, UI_GET_SYSNAME(sizeof sys), sys) >= 0) {
        char dp[200];
        snprintf(dp, sizeof dp, "/sys/devices/virtual/input/%s", sys);
        DIR *sd = opendir(dp);
        struct dirent *se;
        while (sd && (se = readdir(sd))) {
            if (strncmp(se->d_name, "event", 5)) continue;
            char np[400], mm[32] = "";
            snprintf(np, sizeof np, "%s/%s/dev", dp, se->d_name);
            FILE *f = fopen(np, "r");
            if (f) { if (fgets(mm, sizeof mm, f)) mm[strcspn(mm, "\n")] = 0; fclose(f); }
            if (mm[0]) printf("node %s %s\n", se->d_name, mm);
        }
        if (sd) closedir(sd);
    }
    printf("watching Volume Down on %d device(s) for the Essential key (uinput key 250, double press within %d ms), guest %s\n",
           n, WINDOW_MS, guest);

    long long last_down = 0, ess_down = 0;
    int presses = 0;
    while (alive(guest)) {
        int r = poll(pfd, n, 3000);
        if (r <= 0) continue;
        for (int i = 0; i < n; i++) {
            if (!(pfd[i].revents & POLLIN)) continue;
            struct input_event ev;
            while (read(pfd[i].fd, &ev, sizeof ev) == (ssize_t)sizeof ev) {
                if (ev.type != EV_KEY || ev.code != KEY_VOLUMEDOWN || ev.value == 2) continue;
                long long t = now_ms();
                if (ev.value == 1) {
                    if (last_down && t - last_down <= WINDOW_MS) {
                        ess_down = t;
                        last_down = 0;
                        key(ui, 1);
                    } else {
                        last_down = t;
                    }
                } else if (ev.value == 0 && ess_down) {
                    long long held = t - ess_down;
                    key(ui, 0);
                    if (held < LONG_MS) {
                        usleep(60000);
                        key(ui, 1);
                        usleep(60000);
                        key(ui, 0);
                    }
                    if (argc == 3) run_action(argv[2]);
                    if (presses++ < 20) printf("Essential key %s (%lld ms)%s\n", held < LONG_MS ? "double click" : "long press", held,
                                               argc == 3 ? ": Essential Space" : "");
                    ess_down = 0;
                }
            }
        }
    }
    if (ess_down) key(ui, 0);
    ioctl(ui, UI_DEV_DESTROY);
    printf("guest system_server %s gone; %d Essential key presses\n", guest, presses);
    return 0;
}
