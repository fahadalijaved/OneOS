#include "guest_tree_sha256.h"

#include <string.h>

/* SHA-256, RFC 6234 sections 4.1, 5.1, 6.1 and 6.2. */
static const uint32_t rounds[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
};

static uint32_t rotate(uint32_t word, unsigned bits) {
    return (word >> bits) | (word << (32 - bits));
}

static void block(struct guest_tree_sha256 *hash, const unsigned char bytes[64]) {
    uint32_t schedule[64];
    for (size_t i = 0; i < 16; ++i) {
        const unsigned char *word = bytes + 4 * i;
        schedule[i] = (uint32_t)word[0] << 24 | (uint32_t)word[1] << 16 |
                      (uint32_t)word[2] << 8 | word[3];
    }
    for (size_t i = 16; i < 64; ++i) {
        uint32_t a = schedule[i - 15], b = schedule[i - 2];
        uint32_t low = rotate(a, 7) ^ rotate(a, 18) ^ (a >> 3);
        uint32_t high = rotate(b, 17) ^ rotate(b, 19) ^ (b >> 10);
        schedule[i] = schedule[i - 16] + low + schedule[i - 7] + high;
    }
    uint32_t a = hash->words[0], b = hash->words[1], c = hash->words[2], d = hash->words[3];
    uint32_t e = hash->words[4], f = hash->words[5], g = hash->words[6], h = hash->words[7];
    for (size_t i = 0; i < 64; ++i) {
        uint32_t choose = (e & f) ^ (~e & g);
        uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
        uint32_t high = rotate(e, 6) ^ rotate(e, 11) ^ rotate(e, 25);
        uint32_t low = rotate(a, 2) ^ rotate(a, 13) ^ rotate(a, 22);
        uint32_t next = h + high + choose + rounds[i] + schedule[i];
        h = g; g = f; f = e; e = d + next;
        d = c; c = b; b = a; a = next + low + majority;
    }
    const uint32_t result[] = {a, b, c, d, e, f, g, h};
    for (size_t i = 0; i < 8; ++i) hash->words[i] += result[i];
}

void guest_tree_sha256_init(struct guest_tree_sha256 *hash) {
    *hash = (struct guest_tree_sha256){.words = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    }};
}

void guest_tree_sha256_update(struct guest_tree_sha256 *hash, const void *data, size_t length) {
    if (!length) return;
    const unsigned char *cursor = data;
    size_t pending = (size_t)(hash->length % 64);
    hash->length += length;
    if (pending) {
        size_t need = 64 - pending;
        size_t take = need < length ? need : length;
        memcpy(hash->pending + pending, cursor, take);
        if (take < need) return;
        block(hash, hash->pending);
        cursor += take;
        length -= take;
    }
    while (length >= 64) {
        block(hash, cursor);
        cursor += 64;
        length -= 64;
    }
    if (length) memcpy(hash->pending, cursor, length);
}

void guest_tree_sha256_final(struct guest_tree_sha256 *hash, unsigned char digest[32]) {
    size_t pending = (size_t)(hash->length % 64);
    uint64_t bits = hash->length * 8;
    hash->pending[pending++] = 0x80;
    if (pending > 56) {
        memset(hash->pending + pending, 0, 64 - pending);
        block(hash, hash->pending);
        pending = 0;
    }
    memset(hash->pending + pending, 0, 56 - pending);
    for (unsigned i = 0; i < 8; ++i) hash->pending[63 - i] = (unsigned char)(bits >> (i * 8));
    block(hash, hash->pending);
    for (size_t i = 0; i < 8; ++i) {
        uint32_t word = hash->words[i];
        for (unsigned j = 0; j < 4; ++j) digest[4 * i + j] = (unsigned char)(word >> (24 - 8 * j));
    }
}
