#include "guest_loop_detach_sample.h"

#include <stdio.h>
#include <stdlib.h>

#define LINE(s) { (s), sizeof(s) - 1 }
#define SPAN(s) (struct guest_loop_sysfs_line) LINE(s)

static const struct guest_loop_sysfs_sample original = {
    LINE("17\n"), LINE("7:12\n"), LINE("2048\n"), GUEST_LOOP_GROUP_PRESENT, LINE("17\n")
};
static const struct guest_loop_sysfs_sample later = {
    LINE("19\n"), LINE("7:12\n"), LINE("0\n"), GUEST_LOOP_GROUP_ABSENT, LINE("19\n")
};
static unsigned checks;

static void expect(uint32_t major, uint32_t minor, uint64_t sequence,
        const struct guest_loop_sysfs_sample *before,
        const struct guest_loop_sysfs_sample *after,
        enum guest_loop_detach_result expected, int line) {
    enum guest_loop_detach_result result =
        guest_loop_detach_sample_check(major, minor, sequence, before, after);
    ++checks;
    if (result != expected) {
        fprintf(stderr, "line %d, check %u: expected %d, saw %d\n", line, checks, expected, result);
        exit(1);
    }
}

#define UNKNOWN(before, after) \
    expect(7, 12, 17, (before), (after), GUEST_LOOP_DETACH_UNKNOWN, __LINE__)

int main(void) {
    const struct guest_loop_sysfs_line bad_number[] = {
        LINE(""), LINE("\n"), LINE("1"), LINE("1\r\n"), LINE(" 1\n"),
        LINE("1 \n"), LINE("1\n\n"), LINE("1\n2\n"), LINE("01\n"),
        LINE("+1\n"), LINE("-1\n"), LINE("1x\n"), LINE("1\0\n"),
        LINE("1\n\0"), LINE("\xff\n"), LINE("18446744073709551616\n"),
        LINE("184467440737095516150\n"), { NULL, 2 }, { "x", SIZE_MAX },
    };
    const struct guest_loop_sysfs_line bad_dev[] = {
        LINE(""), LINE("7:12"), LINE("7:12\r\n"), LINE(":12\n"),
        LINE("7:\n"), LINE("7:12:1\n"), LINE("07:12\n"), LINE("7:012\n"),
        LINE("+7:12\n"), LINE("7:-12\n"), LINE("7: 12\n"), LINE("7:12\n0\n"),
        LINE("7:1\0\n"), LINE("4294967296:12\n"), LINE("7:4294967296\n"),
        LINE("4294967296:4294967296\n"), LINE("8:12\n"), LINE("7:13\n"),
        { NULL, 5 }, { "x", SIZE_MAX },
    };
    struct guest_loop_sysfs_sample a = original, b = later;

    expect(7, 12, 17, &a, &b, GUEST_LOOP_OLD_ATTACHMENT_DETACHED_SAMPLE, __LINE__);
    UNKNOWN(NULL, &b);
    UNKNOWN(&a, NULL);
    UNKNOWN(&a, &a);
    expect(8, 12, 17, &a, &b, GUEST_LOOP_DETACH_UNKNOWN, __LINE__);
    expect(7, 13, 17, &a, &b, GUEST_LOOP_DETACH_UNKNOWN, __LINE__);
    expect(7, 12, 16, &a, &b, GUEST_LOOP_DETACH_UNKNOWN, __LINE__);

    for (size_t i = 0; i < sizeof(bad_number) / sizeof(bad_number[0]); ++i) {
        a = original;
        b = later;
        a.diskseq_before = bad_number[i];
        UNKNOWN(&a, &b);
        a = original;
        a.diskseq_after = bad_number[i];
        UNKNOWN(&a, &b);
        a = original;
        a.size = bad_number[i];
        UNKNOWN(&a, &b);
        a = original;
        b.diskseq_before = bad_number[i];
        UNKNOWN(&a, &b);
        b = later;
        b.diskseq_after = bad_number[i];
        UNKNOWN(&a, &b);
        b = later;
        b.size = bad_number[i];
        UNKNOWN(&a, &b);
    }

    for (size_t i = 0; i < sizeof(bad_dev) / sizeof(bad_dev[0]); ++i) {
        a = original;
        b = later;
        a.dev = bad_dev[i];
        UNKNOWN(&a, &b);
        a = original;
        b.dev = bad_dev[i];
        UNKNOWN(&a, &b);
    }

    a = original;
    b = later;
    a.diskseq_after = SPAN("18\n");
    UNKNOWN(&a, &b);
    a = original;
    b.diskseq_before = SPAN("18\n");
    UNKNOWN(&a, &b);
    b.diskseq_after = b.diskseq_before = a.diskseq_before;
    UNKNOWN(&a, &b);
    b.diskseq_after = b.diskseq_before = SPAN("16\n");
    UNKNOWN(&a, &b);
    b = later;
    a.diskseq_after = a.diskseq_before = SPAN("0\n");
    expect(7, 12, 0, &a, &b, GUEST_LOOP_DETACH_UNKNOWN, __LINE__);
    a = original;
    a.size = SPAN("0\n");
    UNKNOWN(&a, &b);
    a = original;
    b.size = SPAN("1\n");
    UNKNOWN(&a, &b);

    for (int group = GUEST_LOOP_GROUP_UNOBSERVED; group <= GUEST_LOOP_GROUP_IO_ERROR + 1; ++group) {
        if (group != GUEST_LOOP_GROUP_PRESENT) {
            a = original;
            a.loop_group = (enum guest_loop_group_observation)group;
            UNKNOWN(&a, &later);
        }
        if (group != GUEST_LOOP_GROUP_ABSENT) {
            b = later;
            b.loop_group = (enum guest_loop_group_observation)group;
            UNKNOWN(&original, &b);
        }
    }

    a = original;
    b = later;
    a.dev = b.dev = SPAN("4294967295:4294967295\n");
    a.diskseq_before = a.diskseq_after = SPAN("18446744073709551614\n");
    b.diskseq_before = b.diskseq_after = SPAN("18446744073709551615\n");
    a.size = b.diskseq_before;
    expect(UINT32_MAX, UINT32_MAX, UINT64_MAX - 1, &a, &b,
           GUEST_LOOP_OLD_ATTACHMENT_DETACHED_SAMPLE, __LINE__);

    /* Readable counted bytes need no C string terminator. */
    const char sequence[] = { '1', '9', '\n' };
    const char dev[] = { '7', ':', '1', '2', '\n' };
    const char size[] = { '0', '\n' };
    b = later;
    b.diskseq_before = (struct guest_loop_sysfs_line){ sequence, sizeof(sequence) };
    b.dev = (struct guest_loop_sysfs_line){ dev, sizeof(dev) };
    b.size = (struct guest_loop_sysfs_line){ size, sizeof(size) };
    expect(7, 12, 17, &original, &b, GUEST_LOOP_OLD_ATTACHMENT_DETACHED_SAMPLE, __LINE__);
    printf("PASS %u loop detach byte fixtures\n", checks);
    return 0;
}
