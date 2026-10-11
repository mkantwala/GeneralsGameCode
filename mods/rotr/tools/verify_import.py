"""Verify imported ROTR files against the recorded release manifest."""

import hashlib
import json
from pathlib import Path, PureWindowsPath


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "manifest.json").read_text())
    count = 0
    for archive in manifest["archives"]:
        for entry in archive["entries"]:
            path = root / "archives" / archive["folder"]
            path = path.joinpath(*PureWindowsPath(entry["path"]).parts)
            verify(path, entry)
            count += 1
    for entry in manifest["runtime"]:
        verify(root / "runtime" / entry["path"], entry)
    if len(manifest["archives"]) != 14 or count != 11807 or len(manifest["runtime"]) != 34:
        raise ValueError("Unexpected ROTR 1.85 release inventory")
    print(f"Verified {count} archive entries and 34 runtime files")


def verify(path, entry):
    if path.stat().st_size != entry["size"]:
        raise ValueError(f"Size mismatch: {path}")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != entry["sha256"]:
        raise ValueError(f"SHA-256 mismatch: {path}")


if __name__ == "__main__":
    main()
