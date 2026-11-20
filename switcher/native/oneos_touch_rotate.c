/*
 * OneOS: a Flip's cover touchscreen, rotated with the cover display.
 *
 * HyperOS rotates a Flip's cover display to user rotation 1 (748x720) so the
 * guest UI is upright, but its InputReader keeps mapping the panel's raw touch
 * axes as 720x748: a touch lands 90 degrees clockwise from the finger.  The
 * panel itself is installed at 90 degrees (One UI's installOrientation 1), so
 * the guest needs the raw touch axes turned one quarter before its own input
 * mapper sees them.
 *
 * This grabs the cover touchscreen (read-only otherwise: every event is passed
 * through) and makes a virtual touchscreen with the same name, so the guest's
 * input-port-associations.xml still maps it to the cover display.  X/Y are
 * turned in the raw 0..4095 space; every other event (multitouch slots,
 * tracking ids, pressure, ...) is copied unchanged.  The direction is read
 * from a file on every SYN_REPORT, so it can be changed without a restart:
 *   echo ccw > <dir file>   (the first guess: 90 degrees counter-clockwise)
 *   echo cw  > <dir file>
 *
 * Usage: oneos_touch_rotate <input device> <guest system_server pid>
 *                            [direction file]   (as root; ends with that process)
 */
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef UI_ABS_SETUP
struct uinput_abs_setup {
    __u16 code;
    struct input_absinfo absinfo;
};
#define UI_ABS_SETUP _IOW(UINPUT_IOCTL_BASE, 4, struct uinput_abs_setup)
#endif
#ifndef UI_SET_PROPBIT
#define UI_SET_PROPBIT _IOW(UINPUT_IOCTL_BASE, 110, int)
#endif

#define MAX_SLOTS 64
#define DEFAULT_DIR "/data/local/tmp/oneos/data/oneos_touch_rotate_dir"
#define DEFAULT_CAL "/data/local/tmp/oneos/data/oneos_touch_rotate_cal"

/* The panel's touch IC may report a slightly inset active area (bezel and
 * rounded corners); DEFAULT_CAL can stretch it over the whole display with
 * four numbers (xmin xmax ymin ymax).  Left at the full range by default: the
 * inset is a UI/layout question on the panels seen so far. */
static int xmin = 0, xmax = 4095, ymin = 0, ymax = 4095;

static volatile sig_atomic_t stopping;

static void stop(int sig) {
    (void)sig;
    stopping = 1;
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
    if (write(fd, &e, sizeof e) != (ssize_t)sizeof e)
        fprintf(stderr, "uinput write: %s\n", strerror(errno));
}

static int read_direction(const char *path, int old) {
    char b[16];
    FILE *f = fopen(path, "r");
    if (!f) return old;
    if (!fgets(b, sizeof b, f)) b[0] = 0;
    fclose(f);
    if (!strncmp(b, "ccw", 3)) return 0;
    if (!strncmp(b, "cw", 2)) return 1;
    return old;
}

static void read_calibration(const char *path) {
    int a, b, c, d;
    FILE *f = fopen(path, "r");
    if (!f) return;
    if (fscanf(f, "%d %d %d %d", &a, &b, &c, &d) == 4 && b > a && d > c) {
        xmin = a; xmax = b; ymin = c; ymax = d;
    }
    fclose(f);
}

static int cal(int v, int lo, int hi) {
    if (v <= lo) return 0;
    if (v >= hi) return 4095;
    return (int)((long long)(v - lo) * 4095 / (hi - lo));
}

static int make_uinput(int real, const char *name, const char *phys) {
    int fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) return -1;

    unsigned char evbits[EV_MAX / 8 + 1] = {0};
    unsigned char keybits[KEY_MAX / 8 + 1] = {0};
    unsigned char absbits[ABS_MAX / 8 + 1] = {0};
    unsigned char props[INPUT_PROP_MAX / 8 + 1] = {0};
    if (ioctl(real, EVIOCGBIT(0, sizeof evbits), evbits) < 0 ||
        ioctl(real, EVIOCGBIT(EV_KEY, sizeof keybits), keybits) < 0 ||
        ioctl(real, EVIOCGBIT(EV_ABS, sizeof absbits), absbits) < 0)
        goto fail;

    for (int c = 0; c <= EV_MAX; c++)
        if (evbits[c / 8] & (1 << (c % 8)) && ioctl(fd, UI_SET_EVBIT, c) < 0) goto fail;
    for (int c = 0; c <= KEY_MAX; c++)
        if (keybits[c / 8] & (1 << (c % 8)) && ioctl(fd, UI_SET_KEYBIT, c) < 0) goto fail;
    for (int c = 0; c <= ABS_MAX; c++) {
        if (!(absbits[c / 8] & (1 << (c % 8)))) continue;
        if (ioctl(fd, UI_SET_ABSBIT, c) < 0) goto fail;
        struct input_absinfo ai;
        memset(&ai, 0, sizeof ai);
        if (ioctl(real, EVIOCGABS(c), &ai) < 0) goto fail;
        struct uinput_abs_setup as;
        memset(&as, 0, sizeof as);
        as.code = c;
        as.absinfo = ai;
        if (ioctl(fd, UI_ABS_SETUP, &as) < 0) goto fail;
    }
    if (ioctl(real, EVIOCGPROP(sizeof props), props) >= 0)
        for (int p = 0; p <= INPUT_PROP_MAX; p++)
            if (props[p / 8] & (1 << (p % 8)) && ioctl(fd, UI_SET_PROPBIT, p) < 0) goto fail;

    struct uinput_setup s;
    memset(&s, 0, sizeof s);
    s.id.bustype = BUS_VIRTUAL;
    /* A different id from the real panel keeps the two devices distinct in the
     * guest's InputReader while the name still selects the cover's display. */
    s.id.vendor = 0x4f4e;   /* "ON" */
    s.id.product = 0x5452;  /* "TR" */
    s.id.version = 1;
    snprintf(s.name, sizeof s.name, "%s", name);
    if (ioctl(fd, UI_DEV_SETUP, &s) < 0) goto fail;
    if (phys && *phys && ioctl(fd, UI_SET_PHYS, phys) < 0) goto fail;
    if (ioctl(fd, UI_DEV_CREATE) < 0) goto fail;
    return fd;

fail:
    close(fd);
    return -1;
}

int main(int argc, char **argv) {
    if (argc < 3 || argc > 4 || !argv[1][0] || !argv[2][0]) {
        fprintf(stderr, "usage: %s <input device> <guest system_server pid> [direction file]\n", argv[0]);
        return 2;
    }
    setvbuf(stdout, NULL, _IOLBF, 0);
    const char *dev = argv[1];
    const char *guest = argv[2];
    const char *dirfile = argc == 4 ? argv[3] : DEFAULT_DIR;

    int real = open(dev, O_RDWR | O_NONBLOCK | O_CLOEXEC);
    if (real < 0) { printf("open %s: %s\n", dev, strerror(errno)); return 1; }

    char name[UINPUT_MAX_NAME_SIZE] = "";
    char phys[256] = "";
    if (ioctl(real, EVIOCGNAME(sizeof name - 1), name) < 0) snprintf(name, sizeof name, "oneos_touch");
    ioctl(real, EVIOCGPHYS(sizeof phys - 1), phys);

    int ui = make_uinput(real, name, phys);
    if (ui < 0) { printf("could not create the uinput touchscreen: %s\n", strerror(errno)); close(real); return 1; }

    char sys[64] = "";
    if (ioctl(ui, UI_GET_SYSNAME(sizeof sys), sys) >= 0) {
        char dp[200];
        snprintf(dp, sizeof dp, "/sys/devices/virtual/input/%s", sys);
        for (int i = 0; i < 32; i++) {
            char ev[32], np[400];
            snprintf(ev, sizeof ev, "event%d", i);
            snprintf(np, sizeof np, "%s/%s/dev", dp, ev);
            FILE *f = fopen(np, "r");
            if (!f) continue;
            char mm[32] = "";
            if (fgets(mm, sizeof mm, f)) { mm[strcspn(mm, "\r\n")] = 0; printf("node %s %s\n", ev, mm); }
            fclose(f);
        }
    }

    if (ioctl(real, EVIOCGRAB, 1) < 0) {
        printf("could not grab %s: %s\n", dev, strerror(errno));
        ioctl(ui, UI_DEV_DESTROY);
        close(ui); close(real);
        return 1;
    }

    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = stop;
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);

    int max_x = 4095, max_y = 4095;
    struct input_absinfo ai;
    if (ioctl(real, EVIOCGABS(ABS_MT_POSITION_X), &ai) >= 0 && ai.maximum > 0) max_x = ai.maximum;
    if (ioctl(real, EVIOCGABS(ABS_MT_POSITION_Y), &ai) >= 0 && ai.maximum > 0) max_y = ai.maximum;

    int raw_x[MAX_SLOTS] = {0}, raw_y[MAX_SLOTS] = {0};
    int slot = 0, direction = read_direction(dirfile, 0);
    read_calibration(DEFAULT_CAL);
    printf("rotating %s (%s, %dx%d) as %s, direction %s, active %d..%d x %d..%d\n", dev, name, max_x, max_y,
           phys[0] ? phys : "-", direction ? "cw" : "ccw", xmin, xmax, ymin, ymax);

    struct pollfd pfd = { real, POLLIN, 0 };
    while (!stopping && alive(guest)) {
        int r = poll(&pfd, 1, 1000);
        if (r < 0 && errno != EINTR) break;
        if (r <= 0) continue;
        struct input_event ev;
        while (read(real, &ev, sizeof ev) == (ssize_t)sizeof ev) {
            if (ev.type == EV_ABS) {
                if (ev.code == ABS_MT_SLOT) {
                    slot = ev.value;
                    if (slot < 0 || slot >= MAX_SLOTS) slot = 0;
                    emit(ui, ev.type, ev.code, ev.value);
                    continue;
                }
                if (ev.code == ABS_MT_TRACKING_ID) {
                    if (ev.value >= 0) {
                        raw_x[slot] = max_x / 2;
                        raw_y[slot] = max_y / 2;
                    }
                    emit(ui, ev.type, ev.code, ev.value);
                    continue;
                }
                if (ev.code == ABS_MT_POSITION_X || ev.code == ABS_X) {
                    raw_x[slot] = ev.value;
                    int cy = cal(raw_y[slot], ymin, ymax);
                    int v = direction ? max_y - cy : cy;
                    emit(ui, ev.type, ev.code, v);
                    continue;
                }
                if (ev.code == ABS_MT_POSITION_Y || ev.code == ABS_Y) {
                    raw_y[slot] = ev.value;
                    int cx = cal(raw_x[slot], xmin, xmax);
                    int v = direction ? cx : max_x - cx;
                    emit(ui, ev.type, ev.code, v);
                    continue;
                }
            } else if (ev.type == EV_SYN && ev.code == SYN_REPORT) {
                direction = read_direction(dirfile, direction);
                read_calibration(DEFAULT_CAL);
            }
            emit(ui, ev.type, ev.code, ev.value);
        }
    }

    ioctl(real, EVIOCGRAB, 0);
    ioctl(ui, UI_DEV_DESTROY);
    close(ui);
    close(real);
    printf("guest system_server %s gone or stopped; touch released\n", guest);
    return 0;
}
