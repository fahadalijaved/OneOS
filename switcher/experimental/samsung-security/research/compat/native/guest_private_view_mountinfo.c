/* First-party bounded metadata grammar. No Linux headers or OS operations. */
#include "guest_private_view_mountinfo.h"
#include <string.h>

struct span { const char *p; size_t n; };

static int equal(struct span s, const char *literal) {
    size_t n = strlen(literal);
    return s.n == n && !memcmp(s.p, literal, n);
}

static int decimal(struct span s, uint64_t *value) {
    uint64_t n = 0;
    size_t i;
    if (!s.n) return GPV_INVALID;
    for (i = 0; i < s.n; ++i) {
        unsigned d = (unsigned char)s.p[i] - (unsigned)'0';
        if (d > 9 || n > (UINT64_MAX - d) / 10U) return GPV_INVALID;
        n = n * 10U + d;
    }
    *value = n;
    return GPV_OK;
}

/* Path escapes; source/type mangle additionally escapes '#', and encoded
 * options can escape a comma. No NUL or slash aliases are accepted. */
static int escape_byte(struct span s, size_t *i, unsigned char *value,
                        int extra) {
    const char *p;
    if (s.n - *i < 4) return GPV_INVALID;
    p = s.p + *i + 1;
    if (!memcmp(p, "040", 3)) *value = ' ';
    else if (!memcmp(p, "011", 3)) *value = '\t';
    else if (!memcmp(p, "012", 3)) *value = '\n';
    else if (!memcmp(p, "134", 3)) *value = '\\';
    else if (extra && !memcmp(p, "043", 3)) *value = '#';
    else if (extra == 2 && !memcmp(p, "054", 3)) *value = ',';
    else return GPV_INVALID;
    *i += 3;
    return GPV_OK;
}

static int decode(struct span s, char *out, size_t capacity, int absolute) {
    size_t i, n = 0;
    if (!s.n) return GPV_INVALID;
    for (i = 0; i < s.n; ++i) {
        unsigned char c = (unsigned char)s.p[i];
        if (c == '\\') {
            if (escape_byte(s, &i, &c, absolute ? 0 : 1) != GPV_OK)
                return GPV_INVALID;
        } else if (c <= 32 || c == 127) return GPV_INVALID;
        if (n + 1 >= capacity) return GPV_LIMIT;
        out[n++] = (char)c;
    }
    out[n] = 0;
    return absolute && out[0] != '/' ? GPV_INVALID : GPV_OK;
}

/* Exact single-space field separation, with no leading/trailing delimiter. */
static int field(struct span line, size_t *offset, struct span *out) {
    size_t start = *offset;
    if (start >= line.n || line.p[start] == ' ') return GPV_INVALID;
    while (*offset < line.n && line.p[*offset] != ' ') ++*offset;
    out->p = line.p + start;
    out->n = *offset - start;
    if (*offset < line.n) {
        ++*offset;
        if (*offset == line.n) return GPV_INVALID;
    }
    return GPV_OK;
}

static int options(struct span s, char *out, size_t capacity) {
    size_t start = 0, i;
    if (!s.n) return GPV_INVALID;
    if (s.n >= capacity) return GPV_LIMIT;
    for (i = 0; i <= s.n; ++i) {
        if (i < s.n && s.p[i] != ',') {
            unsigned char c = (unsigned char)s.p[i];
            if (c <= 32 || c == 127) return GPV_INVALID;
            if (c == '\\') {
                if (escape_byte(s, &i, &c, 2) != GPV_OK) return GPV_INVALID;
            }
        } else {
            size_t earlier = 0, key = start, j;
            if (i == start) return GPV_INVALID;
            while (key < i && s.p[key] != '=') ++key;
            if (key == start) return GPV_INVALID;
            /* Duplicate keys, including conflicting values, are ambiguous. */
            while (earlier < start) {
                size_t end = earlier, previous_key;
                while (end < start && s.p[end] != ',') ++end;
                previous_key = earlier;
                while (previous_key < end && s.p[previous_key] != '=') ++previous_key;
                if (previous_key - earlier == key - start &&
                    !memcmp(s.p + earlier, s.p + start, key - start))
                    return GPV_INVALID;
                earlier = end + 1;
            }
            /* ro and rw cannot coexist in one of the two option sets. */
            if (i - start == 2 && s.p[start] == 'r' &&
                (s.p[start + 1] == 'o' || s.p[start + 1] == 'w')) {
                for (j = 0; j + 2 <= start; ++j)
                    if ((!j || s.p[j - 1] == ',') && s.p[j] == 'r' &&
                        s.p[j + 1] != s.p[start + 1] &&
                        (s.p[j + 1] == 'o' || s.p[j + 1] == 'w') &&
                        (j + 2 == s.n || s.p[j + 2] == ','))
                        return GPV_INVALID;
            }
            start = i + 1;
        }
    }
    memcpy(out, s.p, s.n);
    out[s.n] = 0;
    return GPV_OK;
}

static int tag(struct span s, const char *prefix, uint64_t *value) {
    size_t n = strlen(prefix);
    struct span number;
    if (s.n < n || memcmp(s.p, prefix, n)) return 0;
    if (*value) return GPV_INVALID;
    number.p = s.p + n; number.n = s.n - n;
    if (decimal(number, value) != GPV_OK || !*value) return GPV_INVALID;
    return 1;
}

static int parse_row(struct span line, struct gpv_mount_row *r) {
    struct span s[6], token, number;
    uint64_t v;
    size_t offset = 0, i, colon;
    int result;
    memset(r, 0, sizeof(*r));
    for (i = 0; i < 6; ++i)
        if (field(line, &offset, &s[i]) != GPV_OK) return GPV_INVALID;
    if (decimal(s[0], &r->id) != GPV_OK || !r->id ||
        decimal(s[1], &r->parent) != GPV_OK || !r->parent) return GPV_INVALID;
    for (colon = 0; colon < s[2].n && s[2].p[colon] != ':'; ++colon) {}
    if (colon == s[2].n) return GPV_INVALID;
    number.p = s[2].p; number.n = colon;
    if (decimal(number, &v) != GPV_OK || v > UINT32_MAX) return GPV_INVALID;
    r->major = (uint32_t)v;
    number.p = s[2].p + colon + 1; number.n = s[2].n - colon - 1;
    if (decimal(number, &v) != GPV_OK || v > UINT32_MAX) return GPV_INVALID;
    r->minor = (uint32_t)v;
    result = decode(s[3], r->root, sizeof(r->root), 1);
    if (result != GPV_OK) return result;
    result = decode(s[4], r->point, sizeof(r->point), 1);
    if (result != GPV_OK) return result;
    result = options(s[5], r->options, sizeof(r->options));
    if (result != GPV_OK) return result;
    for (;;) {
        if (field(line, &offset, &token) != GPV_OK) return GPV_INVALID;
        if (equal(token, "-")) break;
        result = tag(token, "shared:", &r->shared);
        if (!result) result = tag(token, "master:", &r->master);
        if (!result) result = tag(token, "propagate_from:", &r->propagate);
        if (result < 0) return result;
        if (result) continue;
        if (!equal(token, "unbindable") || r->unbindable) return GPV_INVALID;
        r->unbindable = 1;
    }
    if ((r->propagate && !r->master) ||
        (r->unbindable && (r->shared || r->master || r->propagate)))
        return GPV_INVALID;
    if (field(line, &offset, &token) != GPV_OK) return GPV_INVALID;
    result = decode(token, r->type, sizeof(r->type), 0);
    if (result != GPV_OK) return result;
    if (field(line, &offset, &token) != GPV_OK) return GPV_INVALID;
    result = decode(token, r->source, sizeof(r->source), 0);
    if (result != GPV_OK) return result;
    if (field(line, &offset, &token) != GPV_OK || offset != line.n)
        return GPV_INVALID;
    return options(token, r->super_options, sizeof(r->super_options));
}

int gpv_parse_mountinfo(const char *input, size_t length,
                        struct gpv_mount_row *rows, size_t capacity,
                        size_t *count) {
    size_t start = 0, used = 0, end, i;
    struct gpv_mount_row row;
    if (!count) return GPV_INVALID;
    *count = 0;
    if (!input || !rows || !length || !capacity) return GPV_INVALID;
    if (length > GPV_MOUNTINFO_MAX_BYTES || capacity > GPV_MOUNTINFO_MAX_ROWS)
        return GPV_LIMIT;
    while (start < length) {
        struct span line;
        int result;
        end = start;
        while (end < length && input[end] != '\n') {
            unsigned char c = (unsigned char)input[end];
            if (c < 32 || c == 127) return GPV_INVALID;
            if (end - start >= GPV_MOUNTINFO_MAX_LINE) return GPV_LIMIT;
            ++end;
        }
        if (end == length || end == start) return GPV_INVALID;
        if (used == capacity || used == GPV_MOUNTINFO_MAX_ROWS) return GPV_LIMIT;
        line.p = input + start; line.n = end - start;
        result = parse_row(line, &row);
        if (result != GPV_OK) return result;
        for (i = 0; i < used; ++i)
            if (rows[i].id == row.id) return GPV_INVALID;
        rows[used++] = row;
        start = end + 1;
    }
    if (!used) return GPV_INVALID;
    *count = used;
    return GPV_OK;
}

int gpv_parse_fdinfo_mnt_id(const char *input, size_t length, uint64_t *id) {
    size_t start = 0, end;
    uint64_t found = 0;
    if (!id) return GPV_INVALID;
    *id = 0;
    if (!input || !length) return GPV_INVALID;
    if (length > GPV_FDINFO_MAX_BYTES) return GPV_LIMIT;
    while (start < length) {
        size_t colon, value;
        end = start;
        while (end < length && input[end] != '\n') {
            unsigned char c = (unsigned char)input[end];
            if ((!c || c < 32 || c == 127) && c != '\t') return GPV_INVALID;
            ++end;
        }
        if (end == length || start == end) return GPV_INVALID;
        colon = start;
        while (colon < end && input[colon] != ':') ++colon;
        if (colon == start || colon == end) return GPV_INVALID;
        if (colon - start == 6 && !memcmp(input + start, "mnt_id", 6)) {
            struct span number;
            if (found) return GPV_INVALID;
            value = colon + 1;
            if (value == end || (input[value] != ' ' && input[value] != '\t'))
                return GPV_INVALID;
            while (value < end && (input[value] == ' ' || input[value] == '\t')) ++value;
            number.p = input + value; number.n = end - value;
            if (decimal(number, &found) != GPV_OK || !found) return GPV_INVALID;
        } else {
            /* Ignore other printable proc fields, including repeated locks or
             * epoll entries. A malformed spelling of mnt_id is not an alias. */
            size_t i;
            for (i = start; i < colon; ++i)
                if (input[i] == ' ' || input[i] == '\t') return GPV_INVALID;
        }
        start = end + 1;
    }
    if (!found) return GPV_INVALID;
    *id = found;
    return GPV_OK;
}

const struct gpv_mount_row *gpv_mount_by_id(const struct gpv_mount_row *rows,
                                          size_t count, uint64_t id) {
    const struct gpv_mount_row *found = NULL;
    size_t i;
    if (!rows || !id || !count || count > GPV_MOUNTINFO_MAX_ROWS) return NULL;
    for (i = 0; i < count; ++i) if (rows[i].id == id) {
        if (found) return NULL;
        found = &rows[i];
    }
    return found;
}

int gpv_mount_path_count(const struct gpv_mount_row *rows, size_t count,
                         const char *decoded_path, size_t *matches) {
    size_t length = 0, i, found = 0;
    if (!matches) return GPV_INVALID;
    *matches = 0;
    if (!rows || !decoded_path || !count || count > GPV_MOUNTINFO_MAX_ROWS)
        return GPV_INVALID;
    while (length < GPV_PATH_CAPACITY && decoded_path[length]) ++length;
    if (!length || decoded_path[0] != '/') return GPV_INVALID;
    if (length == GPV_PATH_CAPACITY) return GPV_LIMIT;
    for (i = 0; i < count; ++i)
        if (!memcmp(rows[i].point, decoded_path, length + 1)) ++found;
    *matches = found;
    return GPV_OK;
}
