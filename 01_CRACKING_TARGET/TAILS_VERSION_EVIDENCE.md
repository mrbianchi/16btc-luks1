# Tails version evidence

The version was read directly from the unencrypted boot filesystem inside the
matching full USB image, not inferred from dates or LUKS settings.

Source image on the owner's backup disk:

`/Volumes/UNTITLED/cruzer_usb/cruzer_backup.img`

Image size: 8,065,646,592 bytes.

Partition layout:

- GPT partition 1, label `Tails`, FAT32, offset 17,408 bytes, size
  1,572,846,592 bytes.
- GPT partition 2, label `TailsData`, LUKS1, offset 1,572,864,000 bytes, size
  6,490,685,440 bytes.

The boot partition's `etc/amnesia/version` inside `live/filesystem.squashfs`
contains:

```text
0.20.1
c5418a86304abd6c99c42e644a6775a8175499ef
live-build: 2.0.12-2
live-boot: 3.0.1-1
live-config: 3.0.23-1
```

Its `etc/os-release` contains:

```text
TAILS_PRODUCT_NAME="Tails"
TAILS_VERSION_ID="0.20.1"
```

The boot filesystem reports build timestamps from 2013-09-15. Therefore the
matching installation is conclusively **Tails 0.20.1**.
