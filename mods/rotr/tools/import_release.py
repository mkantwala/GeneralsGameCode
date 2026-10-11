"""Import the verified ROTR 1.85 release without executing its installer."""

import argparse
import bz2
import hashlib
import json
import mmap
from pathlib import Path, PureWindowsPath
import shutil
import struct
import tempfile
import urllib.request
import zipfile
import zlib

from bigfile import extract, index

PACKAGE_SHA256 = "d0f13e9e16af69349122c1d895e0cfd68145d6eb2b2f6a88e86d9882c6f84c10"
DOWNLOAD = "https://www.moddb.com/downloads/mirror/82709/135/2e40fb4558bd58127ccf5c3bb3bc064e/"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def decompress(data, method):
    if method == 0:
        return data
    if method == 1:
        decoder = zlib.decompressobj()
    elif method == 2:
        decoder = bz2.BZ2Decompressor()
    else:
        raise ValueError(f"Unsupported compression: {method}")
    result = decoder.decompress(data)
    if not decoder.eof:
        raise ValueError("Truncated compressed stream")
    return result


def unpack_installer(installer, destination, upstream):
    with installer.open("rb") as stream:
        data = mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)
        signature = data.find(bytes.fromhex("777767542948"))
        if signature < 0:
            raise ValueError("Installer data signature missing")
        position = signature + 6
        listing = None
        file_data = None
        while position + 8 <= len(data):
            kind, _, length = struct.unpack_from("<HHI", data, position)
            position += 8
            if position + length > len(data):
                raise ValueError("Installer block exceeds file size")
            if kind == 0x7F7F:
                file_data = position
                break
            if kind in (0x143A, 0x143E):
                size, method = struct.unpack_from("<IB", data, position)
                decoded = decompress(data[position + 5:position + length], method)
                if len(decoded) != size:
                    raise ValueError("Installer block length mismatch")
                if kind == 0x143A:
                    listing = decoded
                else:
                    start = decoded.index(b"All content contained")
                    end = decoded.index(b"\0", start)
                    (upstream / "Installer-License.txt").write_bytes(decoded[start:end] + b"\n")
            position += length
        if listing is None or file_data is None:
            raise ValueError("Missing installer file listing or data block")
        position = 4
        for _ in range(struct.unpack_from("<H", listing)[0]):
            length, kind = struct.unpack_from("<IH", listing, position)
            end = position + length
            if not position + 6 <= end <= len(listing):
                raise ValueError("Invalid installer node")
            if kind == 0:
                cursor = position + 9
                flag = listing[cursor]
                cursor += 1
                if flag == 0xE2:
                    cursor += 30
                    size = offset = compressed = 0
                else:
                    cursor += 14
                    size, offset, compressed = struct.unpack_from("<III", listing, cursor)
                    cursor += 40
                name = listing[cursor:end].split(b"\0")[0].decode("cp1252")
                parts = PureWindowsPath(name)
                if not name or parts.drive or parts.root or ".." in parts.parts:
                    raise ValueError(f"Unsafe installer path: {name}")
                target = destination.joinpath(*parts.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                if size:
                    start = file_data + offset + 4
                    if start + compressed > len(data):
                        raise ValueError(f"Installer entry exceeds file size: {name}")
                    result = decompress(data[start + 1:start + compressed], data[start])
                    if len(result) != size:
                        raise ValueError(f"Installer entry length mismatch: {name}")
                else:
                    result = b""
                target.write_bytes(result)
            position = end
        data.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="Existing ROTRBeta_185.zip; otherwise download it")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if (root / "manifest.json").exists():
        raise SystemExit("Release is already imported; refusing to overwrite development files")
    with tempfile.TemporaryDirectory(prefix="rotr-import-") as temporary:
        temporary = Path(temporary)
        package = args.package or temporary / "ROTRBeta_185.zip"
        if args.package is None:
            request = urllib.request.Request(DOWNLOAD, headers={"User-Agent": "ROTR-development-import"})
            with urllib.request.urlopen(request, timeout=120) as response, package.open("wb") as output:
                shutil.copyfileobj(response, output)
        if digest(package) != PACKAGE_SHA256:
            raise ValueError("Package SHA-256 does not match the verified ROTR 1.85 release")
        upstream = root / "upstream"
        upstream.mkdir(parents=True, exist_ok=True)
        installer = temporary / "ROTRBeta_185.exe"
        with zipfile.ZipFile(package) as archive:
            for name in ("Readme.txt", "Changelog.txt"):
                (upstream / name).write_bytes(archive.read(name))
            with archive.open(installer.name) as source, installer.open("wb") as output:
                shutil.copyfileobj(source, output)
        unpacked = temporary / "unpacked"
        unpack_installer(installer, unpacked, upstream)
        manifest = {"version": "1.85", "source": "https://www.moddb.com/downloads/rise-of-the-reds-version-185",
                    "package": "ROTRBeta_185.zip", "package_sha256": PACKAGE_SHA256,
                    "archives": [], "runtime": []}
        for archive in sorted(unpacked.glob("*.gib")):
            folder = archive.stem.replace("!", "")
            destination = root / "archives" / folder
            count = extract(archive, destination)
            entries = [{"path": name, "size": size,
                        "sha256": digest(destination.joinpath(*PureWindowsPath(name).parts))}
                       for name, _, size in index(archive)]
            manifest["archives"].append({"archive": archive.name, "folder": folder,
                                         "sha256": digest(archive), "entries": entries})
            print(f"{archive.name}: {count} files", flush=True)
        for path in sorted(unpacked.rglob("*")):
            if not path.is_file() or path.suffix == ".gib":
                continue
            relative = path.relative_to(unpacked)
            destination = root / "runtime" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            manifest["runtime"].append({"path": relative.as_posix(), "size": path.stat().st_size,
                                         "sha256": digest(path)})
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
