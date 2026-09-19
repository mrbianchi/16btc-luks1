#!/usr/bin/env python3
"""
Independent reference implementation of the LUKS1 key-slot unlock algorithm.

This generator builds a *synthetic* LUKS1 header for a known passphrase and
writes it to wasm/tests/fixtures/test-luks-header.bin. The Rust test suite then
verifies that the header unlocks with the same passphrase and rejects others.

Both implementations are written independently from the cryptsetup spec, so
agreement between them catches endianness / PBKDF2 / ESSIV / AF-merge bugs.

Uses only the stdlib (hashlib/hmac) plus pycryptodome (AES).
"""
import hashlib
import hmac
import struct

from Crypto.Cipher import AES

PASSPHRASE = b"testpass"
MASTER_KEY = bytes(range(32))          # 0x00 .. 0x1f
SLOT_SALT = bytes([0x11]) * 32
MK_SALT = bytes([0x22]) * 32
SLOT_ITERS = 1000
MK_ITERS = 1000
STRIPES = 4000
KEY_BYTES = 32
KM_OFFSET = 8
PAYLOAD_OFFSET = 2056
UUID = "11111111-2222-3333-4444-555555555555"


def pbkdf2_sha1(password, salt, iters, dklen):
    return hashlib.pbkdf2_hmac("sha1", password, salt, iters, dklen)


def sha256(data):
    return hashlib.sha256(data).digest()


def hash_buf(src, iv, length):
    """dst = SHA1( BE32(iv) || src[:length] )[:length]"""
    h = hashlib.sha1()
    h.update(struct.pack(">I", iv))
    h.update(src[:length])
    return h.digest()[:length]


def diffuse(src, size):
    digest_size = 20  # sha1
    dst = bytearray(size)
    blocks = size // digest_size
    padding = size % digest_size
    for i in range(blocks):
        d = hash_buf(src[digest_size * i:], i, digest_size)
        dst[digest_size * i:digest_size * i + digest_size] = d
    if padding:
        i = blocks
        d = hash_buf(src[digest_size * i:], i, padding)
        dst[digest_size * i:digest_size * i + padding] = d
    return bytes(dst)


def af_split(master, stripes):
    blocksize = len(master)
    dst = bytearray(blocksize * stripes)
    buf = bytearray(blocksize)
    rng = 0x9E3779B97F4A7C15
    for i in range(stripes - 1):
        stripe = bytearray()
        for _ in range(blocksize):
            rng = (rng * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
            stripe.append((rng >> 33) & 0xFF)
        dst[blocksize * i:blocksize * (i + 1)] = stripe
        for j in range(blocksize):
            buf[j] ^= stripe[j]
        buf = bytearray(diffuse(bytes(buf), blocksize))
    for j in range(blocksize):
        dst[blocksize * (stripes - 1) + j] = master[j] ^ buf[j]
    return bytes(dst)


def af_merge(src, blocksize, stripes):
    buf = bytearray(blocksize)
    for i in range(stripes - 1):
        stripe = src[blocksize * i:blocksize * (i + 1)]
        for j in range(blocksize):
            buf[j] ^= stripe[j]
        buf = bytearray(diffuse(bytes(buf), blocksize))
    last = src[blocksize * (stripes - 1):blocksize * stripes]
    dst = bytearray(blocksize)
    for j in range(blocksize):
        dst[j] = last[j] ^ buf[j]
    return bytes(dst)


def essiv_iv(salt_key, sector):
    block = struct.pack("<Q", sector) + b"\x00" * 8
    return AES.new(salt_key, AES.MODE_ECB).encrypt(block)


def crypt_key_material(data, key, encrypt):
    salt_key = sha256(key)
    out = bytearray()
    n = len(data) // 512
    for j in range(n):
        iv = essiv_iv(salt_key, j)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        chunk = data[j * 512:(j + 1) * 512]
        out += cipher.encrypt(chunk) if encrypt else cipher.decrypt(chunk)
    return bytes(out)


def write_cstring(buf, off, size, text):
    raw = text.encode("ascii")
    assert len(raw) <= size
    buf[off:off + len(raw)] = raw


def build_header():
    derived = pbkdf2_sha1(PASSPHRASE, SLOT_SALT, SLOT_ITERS, KEY_BYTES)
    material = af_split(MASTER_KEY, STRIPES)
    material = crypt_key_material(material, derived, encrypt=True)
    mk_digest = pbkdf2_sha1(MASTER_KEY, MK_SALT, MK_ITERS, 20)

    total = PAYLOAD_OFFSET * 512
    h = bytearray(total)
    h[0:6] = b"LUKS\xba\xbe"
    h[6:8] = struct.pack(">H", 1)
    write_cstring(h, 8, 32, "aes")
    write_cstring(h, 40, 32, "cbc-essiv:sha256")
    write_cstring(h, 72, 32, "sha1")
    h[104:108] = struct.pack(">I", PAYLOAD_OFFSET)
    h[108:112] = struct.pack(">I", KEY_BYTES)
    h[112:132] = mk_digest
    h[132:164] = MK_SALT
    h[164:168] = struct.pack(">I", MK_ITERS)
    write_cstring(h, 168, 40, UUID)

    off = 208  # keyslot 0
    h[off:off + 4] = struct.pack(">I", 0x00AC71F3)  # active
    h[off + 4:off + 8] = struct.pack(">I", SLOT_ITERS)
    h[off + 8:off + 40] = SLOT_SALT
    h[off + 40:off + 44] = struct.pack(">I", KM_OFFSET)
    h[off + 44:off + 48] = struct.pack(">I", STRIPES)

    km = KM_OFFSET * 512
    h[km:km + len(material)] = material
    return bytes(h)


def verify(header, passphrase):
    derived = pbkdf2_sha1(passphrase, SLOT_SALT, SLOT_ITERS, KEY_BYTES)
    km = KM_OFFSET * 512
    af_size = ((KEY_BYTES * STRIPES + 511) // 512) * 512
    material = bytearray(header[km:km + af_size])
    material = crypt_key_material(material, derived, encrypt=False)
    master = af_merge(bytes(material), KEY_BYTES, STRIPES)
    return pbkdf2_sha1(master, MK_SALT, MK_ITERS, 20) == header[112:132], master


def main():
    header = build_header()
    ok, master = verify(header, PASSPHRASE)
    assert ok, "self-verification failed"
    assert master == MASTER_KEY, "master key mismatch"
    bad, _ = verify(header, b"nope")
    assert not bad, "false positive!"
    out = "wasm/tests/fixtures/test-luks-header.bin"
    with open(out, "wb") as f:
        f.write(header)
    print(f"wrote {out} ({len(header)} bytes)")
    print("self-verification OK, master_key =", MASTER_KEY.hex())


if __name__ == "__main__":
    main()
