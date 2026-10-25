// Incremental SHA-256. Included after the kernel headers. Host-tested against
// the SHNGROOT manifest digest.
#pragma once

struct ZornSha256 {
	uint32_t state[8];
	uint64_t bits;
	uint8_t block[64];
	unsigned filled;
};

static uint32_t zornShaRotr(uint32_t value, unsigned bits)
{
	return (value >> bits) | (value << (32 - bits));
}

static void zornShaBlock(uint32_t state[8], const uint8_t block[64])
{
	static const uint32_t k[64] = {
		0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
		0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
		0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
		0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
		0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
		0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
		0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
		0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
	};
	uint32_t w[64];
	for (unsigned i = 0; i < 16; i++) {
		w[i] = (uint32_t)block[i * 4] << 24 | (uint32_t)block[i * 4 + 1] << 16 |
		       (uint32_t)block[i * 4 + 2] << 8 | block[i * 4 + 3];
	}
	for (unsigned i = 16; i < 64; i++) {
		uint32_t s0 = zornShaRotr(w[i - 15], 7) ^ zornShaRotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
		uint32_t s1 = zornShaRotr(w[i - 2], 17) ^ zornShaRotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
		w[i] = w[i - 16] + s0 + w[i - 7] + s1;
	}
	uint32_t a = state[0], b = state[1], c = state[2], d = state[3];
	uint32_t e = state[4], f = state[5], g = state[6], h = state[7];
	for (unsigned i = 0; i < 64; i++) {
		uint32_t s1 = zornShaRotr(e, 6) ^ zornShaRotr(e, 11) ^ zornShaRotr(e, 25);
		uint32_t ch = (e & f) ^ (~e & g);
		uint32_t t1 = h + s1 + ch + k[i] + w[i];
		uint32_t s0 = zornShaRotr(a, 2) ^ zornShaRotr(a, 13) ^ zornShaRotr(a, 22);
		uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
		uint32_t t2 = s0 + maj;
		h = g;
		g = f;
		f = e;
		e = d + t1;
		d = c;
		c = b;
		b = a;
		a = t1 + t2;
	}
	state[0] += a;
	state[1] += b;
	state[2] += c;
	state[3] += d;
	state[4] += e;
	state[5] += f;
	state[6] += g;
	state[7] += h;
}

static void zornShaInit(ZornSha256 *sha)
{
	static const uint32_t iv[8] = {
		0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
	};
	memcpy(sha->state, iv, sizeof(iv));
	sha->bits = 0;
	sha->filled = 0;
}

static void zornShaUpdate(ZornSha256 *sha, const void *data, size_t length)
{
	const uint8_t *bytes = static_cast<const uint8_t *>(data);
	sha->bits += (uint64_t)length * 8;
	while (length > 0) {
		unsigned space = 64 - sha->filled;
		unsigned take = length < space ? (unsigned)length : space;
		memcpy(sha->block + sha->filled, bytes, take);
		sha->filled += take;
		bytes += take;
		length -= take;
		if (sha->filled == 64) {
			zornShaBlock(sha->state, sha->block);
			sha->filled = 0;
		}
	}
}

static void zornShaFinal(ZornSha256 *sha, uint8_t out[32])
{
	sha->block[sha->filled++] = 0x80;
	if (sha->filled > 56) {
		while (sha->filled < 64) {
			sha->block[sha->filled++] = 0;
		}
		zornShaBlock(sha->state, sha->block);
		sha->filled = 0;
	}
	while (sha->filled < 56) {
		sha->block[sha->filled++] = 0;
	}
	for (int shift = 56; shift >= 0; shift -= 8) {
		sha->block[sha->filled++] = (uint8_t)(sha->bits >> shift);
	}
	zornShaBlock(sha->state, sha->block);
	for (unsigned i = 0; i < 8; i++) {
		out[i * 4] = (uint8_t)(sha->state[i] >> 24);
		out[i * 4 + 1] = (uint8_t)(sha->state[i] >> 16);
		out[i * 4 + 2] = (uint8_t)(sha->state[i] >> 8);
		out[i * 4 + 3] = (uint8_t)sha->state[i];
	}
}
