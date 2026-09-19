# Target source verification

The saved cracking header was checked against the matching full USB image on
2026-09-10.

The persistence partition begins at sector 3,072,000 of
`cruzer_backup.img`. Reading 4,097 sectors (2,097,664 bytes) from that offset
produced:

```text
SHA-256  6a8c5add8c8110867771123c378d0a67efb2def92ad3dd82aa1e76080b2d1250
```

The included `myluksdrive-luks-header` independently produces the same digest.
The second saved local header copy also produces the same digest. This proves
that the compact target in this package matches the LUKS partition in the full
Tails 0.20.1 USB image.

The full image remains on the owner's external backup drive and is omitted
from the handoff ZIP because it is approximately 8.1 GB and unnecessary for
offline passphrase testing.
