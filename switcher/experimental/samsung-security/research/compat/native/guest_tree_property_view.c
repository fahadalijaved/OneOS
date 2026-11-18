#include "guest_tree_property_view.h"

#include <string.h>

enum {
    AREA_HEADER = 128,
    ROOT_AND_DIRTY_BACKUP = 112,
    TRIE_HEADER = 20,
    PROPERTY_NAME = 96,
    MAX_SEGMENT = 255,
    MAX_VISITED_SPANS = 128
};

struct interval {
    uint32_t offset;
    uint32_t end;
    uint32_t incoming_edge;
};

struct lookup {
    const unsigned char *data;
    uint32_t used;
    size_t seen_count;
    struct interval seen[MAX_VISITED_SPANS];
};

struct segment {
    const unsigned char *name;
    size_t length;
};

struct short_value {
    const unsigned char *bytes;
    size_t length;
};

static uint32_t le32(const unsigned char *bytes)
{
    return (uint32_t)bytes[0] | (uint32_t)bytes[1] << 8 |
           (uint32_t)bytes[2] << 16 | (uint32_t)bytes[3] << 24;
}

static int span_in_data(const struct lookup *walk, uint32_t offset, size_t bytes)
{
    return offset >= ROOT_AND_DIRTY_BACKUP && (offset & 3u) == 0 &&
           offset <= walk->used && bytes <= walk->used - offset;
}

static int record_span(struct lookup *walk, uint32_t offset, size_t bytes,
                       uint32_t incoming_edge)
{
    const size_t aligned = (bytes + 3u) & ~(size_t)3u;
    if (!span_in_data(walk, offset, aligned)) return 0;
    const uint32_t end = offset + (uint32_t)aligned;
    for (size_t i = 0; i < walk->seen_count; ++i) {
        const struct interval *seen = &walk->seen[i];
        if (end <= seen->offset || offset >= seen->end) continue;
        return offset == seen->offset && end == seen->end &&
               incoming_edge == seen->incoming_edge;
    }
    if (walk->seen_count == MAX_VISITED_SPANS) return 0;
    walk->seen[walk->seen_count++] = (struct interval){offset, end, incoming_edge};
    return 1;
}

static int name_char(unsigned char byte)
{
    return (byte >= 'a' && byte <= 'z') || (byte >= 'A' && byte <= 'Z') ||
           (byte >= '0' && byte <= '9') || byte == '_' || byte == '-' ||
           byte == '@' || byte == ':';
}

/* bionic compares segment length before the bytes. */
static int segment_order(struct segment left, struct segment right)
{
    if (left.length != right.length) return left.length < right.length ? -1 : 1;
    return memcmp(left.name, right.name, left.length);
}

static enum guest_tree_prop_result find_segment(struct lookup *walk, uint32_t *edge,
                                                struct segment wanted)
{
    struct segment lower = {0};
    struct segment upper = {0};
    for (unsigned probes = 0; probes < MAX_VISITED_SPANS; ++probes) {
        const uint32_t offset = le32(walk->data + *edge);
        if (!offset) return GUEST_TREE_PROP_MISSING;
        if (!span_in_data(walk, offset, TRIE_HEADER + 1)) return GUEST_TREE_PROP_INVALID;
        const unsigned char *node = walk->data + offset;
        const struct segment current = {node + TRIE_HEADER, le32(node)};
        if (!current.length || current.length > MAX_SEGMENT ||
            !record_span(walk, offset, TRIE_HEADER + current.length + 1, *edge) ||
            current.name[current.length] != 0) return GUEST_TREE_PROP_INVALID;
        for (size_t i = 0; i < current.length; ++i) {
            if (!name_char(current.name[i])) return GUEST_TREE_PROP_INVALID;
        }
        if ((lower.name && segment_order(lower, current) >= 0) ||
            (upper.name && segment_order(current, upper) >= 0)) return GUEST_TREE_PROP_INVALID;

        const int order = segment_order(wanted, current);
        if (!order) {
            *edge = offset;
            return GUEST_TREE_PROP_STORED_RELEASE; /* Internal lookup found a node. */
        }
        if (order < 0) {
            upper = current;
            *edge = offset + 8;
        } else {
            lower = current;
            *edge = offset + 12;
        }
    }
    return GUEST_TREE_PROP_INVALID;
}

static enum guest_tree_prop_result read_short(struct lookup *walk, const char *key,
                                               struct short_value *value)
{
    uint32_t node = 0;
    const char *part = key;
    for (;;) {
        const char *dot = strchr(part, '.');
        const struct segment wanted = {
            (const unsigned char *)part, dot ? (size_t)(dot - part) : strlen(part)
        };
        node += 16; /* children offset, including the root at data offset 0 */
        const enum guest_tree_prop_result found = find_segment(walk, &node, wanted);
        if (found != GUEST_TREE_PROP_STORED_RELEASE) return found;
        if (!dot) break;
        part = dot + 1;
    }
    const uint32_t offset = le32(walk->data + node + 4);
    const size_t key_bytes = strlen(key) + 1;
    if (!offset) return GUEST_TREE_PROP_MISSING;
    if (!record_span(walk, offset, PROPERTY_NAME + key_bytes, node + 4)) return GUEST_TREE_PROP_INVALID;
    const unsigned char *record = walk->data + offset;
    const uint32_t serial = le32(record);
    const size_t length = serial >> 24;
    if (memcmp(record + PROPERTY_NAME, key, key_bytes) || (serial & 1u)) return GUEST_TREE_PROP_INVALID;
    if (serial & UINT32_C(0x10000)) return GUEST_TREE_PROP_UNSUPPORTED;
    if (length >= GUEST_TREE_PROP_SHORT_VALUE_BYTES || record[4 + length] != 0 ||
        memchr(record + 4, 0, length)) return GUEST_TREE_PROP_INVALID;
    *value = (struct short_value){record + 4, length};
    return GUEST_TREE_PROP_STORED_RELEASE;
}

static int init_lookup(struct lookup *walk, const void *area, size_t bytes)
{
    if (!area || bytes != GUEST_TREE_PROP_AREA_BYTES) return 0;
    const unsigned char *header = area;
    walk->data = header + AREA_HEADER;
    walk->used = le32(header);
    walk->seen_count = 0;
    if (le32(header + 8) != UINT32_C(0x504f5250) ||
        le32(header + 12) != UINT32_C(0xfc6ed0ab) ||
        walk->used < ROOT_AND_DIRTY_BACKUP || walk->used > bytes - AREA_HEADER ||
        (walk->used & 3u)) return 0;
    for (size_t i = 16; i < AREA_HEADER; ++i) {
        if (header[i]) return 0;
    }
    /* The first four words of the root are name length, property and siblings. */
    return !le32(walk->data) && !le32(walk->data + 4) && !le32(walk->data + 8) && !le32(walk->data + 12);
}

enum guest_tree_prop_result guest_tree_property_read_release(
        const void *area, size_t bytes, uint32_t *sdk)
{
    if (!sdk) return GUEST_TREE_PROP_INVALID;
    *sdk = 0;
    struct lookup walk;
    if (!init_lookup(&walk, area, bytes)) return GUEST_TREE_PROP_INVALID;
    struct short_value sdk_value, codename;
    enum guest_tree_prop_result result = read_short(&walk, "ro.build.version.sdk", &sdk_value);
    if (result != GUEST_TREE_PROP_STORED_RELEASE) return result;
    result = read_short(&walk, "ro.build.version.codename", &codename);
    if (result != GUEST_TREE_PROP_STORED_RELEASE) return result;
    if (codename.length != 3 || memcmp(codename.bytes, "REL", 3) ||
        !sdk_value.length || sdk_value.bytes[0] == '0') return GUEST_TREE_PROP_UNSUPPORTED;
    uint32_t parsed = 0;
    for (size_t i = 0; i < sdk_value.length; ++i) {
        const uint32_t digit = (uint32_t)sdk_value.bytes[i] - '0';
        if (digit > 9 || parsed > ((uint32_t)INT32_MAX - digit) / 10) return GUEST_TREE_PROP_UNSUPPORTED;
        parsed = parsed * 10 + digit;
    }
    *sdk = parsed;
    return GUEST_TREE_PROP_STORED_RELEASE;
}

static int ranges_overlap(const void *left, size_t left_bytes, const void *right, size_t right_bytes)
{
    const uintptr_t a = (uintptr_t)left, b = (uintptr_t)right;
    return a <= b ? b - a < left_bytes : a - b < right_bytes;
}

enum guest_tree_prop_result guest_tree_property_read_linkerconfig(
        const void *vndk_area, size_t vndk_bytes, const void *debug_area,
        size_t debug_bytes, struct guest_tree_linker_property_sample *out)
{
    static const char *const keys[GUEST_TREE_LINKER_PROPERTY_COUNT] = {
        [GUEST_TREE_LINKER_VNDK_LITE] = "ro.vndk.lite",
        [GUEST_TREE_LINKER_VNDK_VERSION] = "ro.vndk.version",
        [GUEST_TREE_LINKER_PRODUCT_VNDK_VERSION] = "ro.product.vndk.version",
        [GUEST_TREE_LINKER_DEBUGGABLE] = "ro.debuggable",
    };
    struct lookup walk;
    if (!out || !vndk_area || !debug_area || vndk_bytes != GUEST_TREE_PROP_AREA_BYTES ||
        debug_bytes != GUEST_TREE_PROP_AREA_BYTES ||
        ranges_overlap(vndk_area, vndk_bytes, debug_area, debug_bytes) ||
        ranges_overlap(vndk_area, vndk_bytes, out, sizeof(*out)) ||
        ranges_overlap(debug_area, debug_bytes, out, sizeof(*out)) ||
        !init_lookup(&walk, vndk_area, vndk_bytes))
        return GUEST_TREE_PROP_INVALID;

    struct guest_tree_linker_property_sample sample = {0};
    for (size_t i = 0; i < GUEST_TREE_LINKER_PROPERTY_COUNT; ++i) {
        if (i == GUEST_TREE_LINKER_DEBUGGABLE && !init_lookup(&walk, debug_area, debug_bytes))
            return GUEST_TREE_PROP_INVALID;
        struct short_value value;
        enum guest_tree_prop_result found = read_short(&walk, keys[i], &value);
        if (found == GUEST_TREE_PROP_MISSING) continue;
        if (found != GUEST_TREE_PROP_STORED_RELEASE) return found;
        struct guest_tree_linker_property_value *stored = &sample.values[i];
        stored->present = 1;
        stored->length = (uint8_t)value.length;
        memcpy(stored->bytes, value.bytes, value.length);
    }
    *out = sample;
    return GUEST_TREE_PROP_STORED_LINKERCONFIG;
}
