#include "guest_tree_property_view.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

enum { HEADER = 128 };
static unsigned char area[GUEST_TREE_PROP_AREA_BYTES];
static unsigned checks;

static void put32(unsigned char *dst, uint32_t value)
{
    for (unsigned i = 0; i < 4; ++i) dst[i] = (unsigned char)(value >> (8 * i));
}

static void store(uint32_t offset, uint32_t value)
{
    put32(area + HEADER + offset, value);
}

static uint32_t take(uint32_t *next, size_t count)
{
    const uint32_t result = *next;
    *next += (uint32_t)((count + 3) & ~(size_t)3);
    assert(*next < sizeof(area) - HEADER);
    put32(area, *next);
    return result;
}

static uint32_t node(uint32_t *next, const char *name)
{
    const size_t len = strlen(name);
    const uint32_t at = take(next, 20 + len + 1);
    store(at, (uint32_t)len);
    memcpy(area + HEADER + at + 20, name, len + 1);
    return at;
}

static uint32_t prop(uint32_t *next, const char *name, const char *value)
{
    const uint32_t at = take(next, 96 + strlen(name) + 1);
    store(at, (uint32_t)strlen(value) << 24);
    memcpy(area + HEADER + at + 4, value, strlen(value) + 1);
    memcpy(area + HEADER + at + 96, name, strlen(name) + 1);
    return at;
}

struct fixture {
    uint32_t ro;
    uint32_t version;
    uint32_t sdk;
    uint32_t codename;
    uint32_t sdk_prop;
    uint32_t codename_prop;
};

static struct fixture build(const char *sdk_value, const char *codename_value)
{
    memset(area, 0, sizeof(area));
    put32(area + 8, UINT32_C(0x504f5250));
    put32(area + 12, UINT32_C(0xfc6ed0ab));
    uint32_t next = 112;
    put32(area, next);
    const uint32_t ro = node(&next, "ro");
    const uint32_t build_node = node(&next, "build");
    const uint32_t version = node(&next, "version");
    const uint32_t middle = node(&next, "middle");
    const uint32_t sdk = node(&next, "sdk");
    const uint32_t codename = node(&next, "codename");
    const uint32_t sdk_prop = prop(&next, "ro.build.version.sdk", sdk_value);
    const uint32_t codename_prop = prop(&next, "ro.build.version.codename", codename_value);

    store(16, ro);
    store(ro + 16, build_node);
    store(build_node + 16, version);
    store(version + 16, middle);
    /* sdk sorts left of middle by length, codename right by length. */
    store(middle + 8, sdk);
    store(middle + 12, codename);
    store(sdk + 4, sdk_prop);
    store(codename + 4, codename_prop);
    return (struct fixture){ro, version, sdk, codename, sdk_prop, codename_prop};
}

static void expect(const void *bytes, size_t size, enum guest_tree_prop_result expected,
                   uint32_t sdk)
{
    uint32_t actual = 57;
    assert(guest_tree_property_read_release(bytes, size, &actual) == expected);
    assert(actual == sdk);
    ++checks;
}

#define CHECK(status) expect(area, sizeof(area), GUEST_TREE_PROP_##status, 0)

int main(void)
{
    struct fixture f = build("37", "REL");
    expect(area, sizeof(area), GUEST_TREE_PROP_STORED_RELEASE, 37);
    expect(area, 0, GUEST_TREE_PROP_INVALID, 0);
    expect(area, sizeof(area) - 1, GUEST_TREE_PROP_INVALID, 0);
    expect(NULL, sizeof(area), GUEST_TREE_PROP_INVALID, 0);
    assert(guest_tree_property_read_release(area, sizeof(area), NULL) == GUEST_TREE_PROP_INVALID);
    ++checks;

    put32(area + 8, 0);
    CHECK(INVALID);
    build("37", "REL");
    put32(area + 12, UINT32_C(0xfc6ed0ac));
    CHECK(INVALID);
    build("37", "REL");
    put32(area, UINT32_MAX);
    CHECK(INVALID);
    build("37", "REL");
    put32(area, 113);
    CHECK(INVALID);
    build("37", "REL");
    area[127] = 1;
    CHECK(INVALID);
    build("37", "REL");
    store(8, 112);
    CHECK(INVALID);
    build("37", "REL");
    store(16, 0);
    CHECK(MISSING);

    f = build("37", "REL");
    store(f.ro + 16, f.ro);
    CHECK(INVALID);
    f = build("37", "REL");
    store(f.ro + 16, 108);
    CHECK(INVALID);
    f = build("37", "REL");
    store(f.ro + 16, f.ro + 1);
    CHECK(INVALID);
    f = build("37", "REL");
    store(f.version + 16, UINT32_MAX);
    CHECK(INVALID);
    f = build("37", "REL");
    area[HEADER + f.sdk + 20 + 3] = 'x';
    CHECK(INVALID);
    f = build("37", "REL");
    memcpy(area + HEADER + f.sdk + 20, "8.!", 3);
    CHECK(INVALID);
    f = build("37", "REL");
    store(f.sdk + 4, 0);
    CHECK(MISSING);
    f = build("37", "REL");
    store(f.codename + 4, f.sdk_prop);
    CHECK(INVALID);
    f = build("37", "REL");
    store(f.sdk + 4, f.sdk + 4);
    CHECK(INVALID);
    f = build("37", "REL");
    area[HEADER + f.sdk_prop + 96] = 'x';
    CHECK(INVALID);
    f = build("37", "REL");
    store(f.sdk_prop, UINT32_C(0x02000001));
    CHECK(INVALID);
    f = build("37", "REL");
    store(f.sdk_prop, UINT32_C(0x32010000));
    CHECK(UNSUPPORTED);
    f = build("37", "REL");
    store(f.sdk_prop, UINT32_C(0x5c000000));
    CHECK(INVALID);
    f = build("37", "REL");
    area[HEADER + f.sdk_prop + 6] = 'x';
    CHECK(INVALID);
    f = build("37", "REL");
    area[HEADER + f.sdk_prop + 4] = 0;
    CHECK(INVALID);
    f = build("37", "REL");
    put32(area, f.codename_prop + 4);
    CHECK(INVALID);

    build("37", "Preview");
    CHECK(UNSUPPORTED);
    build("0", "REL");
    CHECK(UNSUPPORTED);
    build("037", "REL");
    CHECK(UNSUPPORTED);
    build("", "REL");
    CHECK(UNSUPPORTED);
    build("+37", "REL");
    CHECK(UNSUPPORTED);
    build("2147483648", "REL");
    CHECK(UNSUPPORTED);
    build("2147483647", "REL");
    expect(area, sizeof(area), GUEST_TREE_PROP_STORED_RELEASE, INT32_MAX);
    assert(checks == 35);
    printf("PASS %u donor property-area snapshot checks\n", checks);
    return 0;
}
