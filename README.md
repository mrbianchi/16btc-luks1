# LUKS Finder (web) · Tails 0.20.1

Web version of the
[`decrypter16btc-web-with-verifier`](https://github.com/mrbianchi/decrypter16btc-web-with-verifier)
repo, but pointed at the real target in `./01_CRACKING_TARGET`: the **LUKS1**
header of the persistent partition of a Tails 0.20.1 USB image.

The app lets you manually test passphrases (fully offline, in the browser),
inspect the LUKS header metadata, and verify a recovered master key against the
header digest. Nothing is uploaded anywhere: everything runs in WebAssembly
compiled from Rust.

## Structure

```
.
├── 01_CRACKING_TARGET/          # Original target (untouched)
│   ├── myluksdrive-luks-header  # LUKS1 header (2 MiB, embedded in the WASM)
│   ├── hashcat-29511.txt        # Same hash in hashcat format (mode 14600)
│   └── ...
├── wasm/                        # Rust core → WebAssembly
│   ├── src/lib.rs               # LUKS1 verifier + WASM wrappers
│   └── tests/i_test.rs          # Native tests (round-trip + real header)
├── tools/gen_test_luks.py       # Independent Python implementation (fixture)
└── ui/                          # Svelte + Vite
    └── src/App.svelte           # Interface
```

## Build & run

Requirements: Node.js, `npm`, Rust, `wasm-pack` and the `wasm32-unknown-unknown`
target.

```bash
# 1. Build the WASM
cd wasm
wasm-pack build --target web

# 2. Install and build the UI
cd ../ui
npm ci
npm run build          # produces ui/dist (static)

# Optional: development server
npm run dev
```

The production build lives in `ui/dist` and uses relative paths (`base: './'`),
so it can be served from any subpath, for example:

```bash
cd ui/dist && python3 -m http.server 8000
```

The app has two targets: **Real target** (the embedded Tails LUKS1 header) and
**Test data** (a synthetic header with passphrase `testpass`).

## Tests

```bash
cd wasm
cargo test             # 4 native tests
```

- `test_pbkdf2_sha1_known_vector`: well-known PBKDF2-HMAC-SHA1 vector.
- `test_roundtrip_synthetic_header`: split+encrypt → verify (round trip).
- `test_python_fixture_unlocks`: validates the fixture produced by an
  **independent** Python implementation (`tools/gen_test_luks.py`), confirming
  cross-language compatibility.
- `test_real_target_parse_and_reject`: parses the real header and checks that a
  wrong passphrase does **not** produce a false positive.

To regenerate the fixture (requires `pycryptodome`):

```bash
python3 tools/gen_test_luks.py
```

## Algorithm (LUKS1)

Faithful implementation of the `cryptsetup` source (`lib/luks1/keymanage.c`,
`lib/luks1/af.c`, `lib/crypto_backend/crypto_storage.c`):

1. `key = PBKDF2-HMAC-SHA1(passphrase, slot.salt, iterations, 32)`.
2. Read the slot *key material* (32 bytes × 4000 stripes = 128 000 bytes) and
   decrypt it with `AES-256-CBC` using `ESSIV:sha256`:
   `IV = AES-ECB(SHA256(key), LE64(sector) || 0x00×8)`, with sector relative 0..
3. *Anti-forensic merge*: chained XOR with SHA1 diffusion (`diffuse`/`hash_buf`).
4. Verification: `PBKDF2-HMAC-SHA1(master_key, mk_digest_salt, mk_digest_iter, 20)`
   must equal `mk-digest` (20 bytes).

Real target data (read directly from the header):

| Field | Value |
|---|---|
| UUID | `55645f1a-f8fd-490f-b3e4-862dddde4e08` |
| Version | LUKS1 |
| Cipher | `aes-cbc-essiv:sha256` |
| Hash | `sha1` |
| Master key | 32 bytes |
| Active slots | 1 (slot 0, 105 474 PBKDF2 iterations) |
| Digest iterations | 34 000 |

> Note: the correct passphrase is unknown; this tool is meant to test candidate
> passphrases safely and verify them when one succeeds.
