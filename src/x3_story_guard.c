/* Ver x3_story_guard.h. */
#include "x3_story_guard.h"

#include <string.h>

const unsigned char kX3StoryExpectedSha256[32] = {
    0x65, 0xb0, 0x32, 0x68, 0xaf, 0xac, 0x29, 0x63,
    0x30, 0xe8, 0xff, 0x8d, 0x60, 0xdd, 0x08, 0x25,
    0x87, 0x9e, 0x13, 0xed, 0x65, 0x8b, 0x37, 0x71,
    0x3c, 0x03, 0x4a, 0x3b, 0xd0, 0x74, 0xf1, 0xd7,
};

int X3Story_DigestMatches(const unsigned char *digest) {
  if (!digest) return 0;
  return memcmp(digest, kX3StoryExpectedSha256, 32) == 0;
}

void X3Story_DigestHex(const unsigned char *digest, char *out, size_t cap) {
  static const char hex[] = "0123456789abcdef";
  if (!out || cap == 0) return;
  if (cap < 65 || !digest) {
    out[0] = '\0';
    return;
  }
  for (unsigned i = 0; i < 32; ++i) {
    out[2 * i] = hex[digest[i] >> 4];
    out[2 * i + 1] = hex[digest[i] & 0x0F];
  }
  out[64] = '\0';
}
