#ifndef ONEOS_GUEST_TREE_PROPERTY_VIEW_H
#define ONEOS_GUEST_TREE_PROPERTY_VIEW_H

#include <stddef.h>
#include <stdint.h>

#define GUEST_TREE_BUILD_PROP_AREA "u:object_r:build_prop:s0"
#define GUEST_TREE_VNDK_PROP_AREA "u:object_r:vndk_prop:s0"
#define GUEST_TREE_DEBUG_PROP_AREA "u:object_r:userdebug_or_eng_prop:s0"
#define GUEST_TREE_PROP_AREA_BYTES 262144u
#define GUEST_TREE_PROP_SHORT_VALUE_BYTES 92u

enum guest_tree_prop_result {
    GUEST_TREE_PROP_INVALID = 0,
    GUEST_TREE_PROP_MISSING,
    GUEST_TREE_PROP_UNSUPPORTED,
    GUEST_TREE_PROP_STORED_RELEASE,
    GUEST_TREE_PROP_STORED_LINKERCONFIG
};

/*
 * Read the two fixed classpath property names from an immutable byte
 * snapshot of the donor bionic build_prop context area. The supported
 * data profile is a canonical positive decimal SDK and codename REL.
 * area and sdk must be disjoint. sdk is cleared unless STORED_RELEASE.
 *
 * This validates only the reachable lookup paths for those two keys.
 * A successful result describes stored bytes. Establishing the source
 * producer, private /dev mount, property_info mapping, consumer read
 * access and absence of inherited host access requires a separate owner.
 */
enum guest_tree_prop_result guest_tree_property_read_release(
        const void *area, size_t bytes, uint32_t *sdk);

enum guest_tree_linker_property_key {
    GUEST_TREE_LINKER_VNDK_LITE,
    GUEST_TREE_LINKER_VNDK_VERSION,
    GUEST_TREE_LINKER_PRODUCT_VNDK_VERSION,
    GUEST_TREE_LINKER_DEBUGGABLE,
    GUEST_TREE_LINKER_PROPERTY_COUNT
};

struct guest_tree_linker_property_value {
    uint8_t present, length;
    char bytes[GUEST_TREE_PROP_SHORT_VALUE_BYTES];
};

struct guest_tree_linker_property_sample {
    struct guest_tree_linker_property_value values[GUEST_TREE_LINKER_PROPERTY_COUNT];
};

/* Read the four fixed linkerconfig keys from disjoint immutable snapshots
 * of the donor vndk_prop and userdebug_or_eng_prop contexts. Preserve raw
 * short values, including stored empty strings, and record missing lookup
 * paths separately. The output is disjoint from both inputs and is published
 * only after all four lookups succeed or are missing. The owner must prove
 * both context mappings, custody in the same guest view, and effective
 * consumer access. A missing area is not a missing key, and this reader
 * applies no consumer defaults. */
enum guest_tree_prop_result guest_tree_property_read_linkerconfig(
        const void *vndk_area, size_t vndk_bytes, const void *debug_area,
        size_t debug_bytes, struct guest_tree_linker_property_sample *out);

#endif
