#include "guest_loop_detach_sample.h"

enum { MAX_U32_DECIMAL = 10, MAX_U64_DECIMAL = 20 };

static int decimal(const char *bytes, size_t length, uint64_t max, uint64_t *out) {
    uint64_t value = 0;

    if (length == 0 || (length > 1 && bytes[0] == '0')) return 0;
    for (size_t i = 0; i < length; ++i) {
        unsigned digit = (unsigned char)bytes[i] - (unsigned)'0';
        if (digit > 9 || value > (max - digit) / 10) return 0;
        value = value * 10 + digit;
    }
    *out = value;
    return 1;
}

static int decimal_line(struct guest_loop_sysfs_line line, uint64_t *out) {
    return line.bytes && line.length >= 2 && line.length <= MAX_U64_DECIMAL + 1
            && line.bytes[line.length - 1] == '\n'
            && decimal(line.bytes, line.length - 1, UINT64_MAX, out);
}

static int same_dev(struct guest_loop_sysfs_line line, uint32_t major, uint32_t minor) {
    size_t separator = 0;
    uint64_t observed_major, observed_minor;

    if (!line.bytes || line.length < 4 || line.length > 2 * MAX_U32_DECIMAL + 2
            || line.bytes[line.length - 1] != '\n') return 0;
    while (separator < line.length - 1 && line.bytes[separator] != ':') ++separator;
    if (separator == line.length - 1) return 0;
    return decimal(line.bytes, separator, UINT32_MAX, &observed_major)
            && decimal(line.bytes + separator + 1, line.length - separator - 2,
                       UINT32_MAX, &observed_minor)
            && observed_major == major && observed_minor == minor;
}

static int read_bracket(const struct guest_loop_sysfs_sample *sample,
        uint32_t major, uint32_t minor, uint64_t *sequence, uint64_t *size) {
    uint64_t end;
    return decimal_line(sample->diskseq_before, sequence)
            && same_dev(sample->dev, major, minor)
            && decimal_line(sample->size, size)
            && decimal_line(sample->diskseq_after, &end)
            && *sequence == end;
}

enum guest_loop_detach_result guest_loop_detach_sample_check(
        uint32_t held_major, uint32_t held_minor, uint64_t held_diskseq,
        const struct guest_loop_sysfs_sample *original,
        const struct guest_loop_sysfs_sample *later) {
    uint64_t old_sequence, old_size, new_sequence, new_size;

    if (!original || !later || held_diskseq == 0
            || original->loop_group != GUEST_LOOP_GROUP_PRESENT
            || later->loop_group != GUEST_LOOP_GROUP_ABSENT
            || !read_bracket(original, held_major, held_minor, &old_sequence, &old_size)
            || !read_bracket(later, held_major, held_minor, &new_sequence, &new_size)
            || old_sequence != held_diskseq || old_size == 0
            || new_sequence <= old_sequence || new_size != 0) {
        return GUEST_LOOP_DETACH_UNKNOWN;
    }
    return GUEST_LOOP_OLD_ATTACHMENT_DETACHED_SAMPLE;
}
