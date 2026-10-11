"""Extract and rebuild SAGE BIGF/BIG4 archives without running an installer."""

import argparse
from pathlib import Path, PureWindowsPath
import shutil
import struct


def index(path):
    with path.open("rb") as stream:
        header = stream.read(16)
        if len(header) != 16 or header[:4] not in (b"BIGF", b"BIG4"):
            raise ValueError(f"Not a BIG archive: {path}")
        count, end = struct.unpack(">II", header[8:])
        length = path.stat().st_size
        if not 16 <= end <= length:
            raise ValueError("Invalid index boundary")
        entries = []
        names = set()
        for _ in range(count):
            raw = stream.read(8)
            if len(raw) != 8:
                raise ValueError("Truncated index")
            offset, size = struct.unpack(">II", raw)
            name = bytearray()
            while stream.tell() < end:
                byte = stream.read(1)
                if byte == b"\0":
                    break
                name.extend(byte)
            else:
                raise ValueError("Unterminated archive path")
            name = name.decode("cp1252")
            parts = PureWindowsPath(name)
            key = name.replace("\\", "/").casefold()
            if (not name or parts.drive or parts.root or ".." in parts.parts
                    or key in names or offset < end or offset + size > length):
                raise ValueError(f"Invalid archive entry: {name}")
            names.add(key)
            entries.append((name, offset, size))
        return entries


def extract(archive, destination):
    entries = index(archive)
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with archive.open("rb") as stream:
        for name, offset, size in entries:
            target = destination.joinpath(*PureWindowsPath(name).parts)
            if not target.resolve().is_relative_to(root):
                raise ValueError(f"Path escapes destination: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            stream.seek(offset)
            data = stream.read(size)
            if len(data) != size:
                raise ValueError(f"Truncated entry: {name}")
            target.write_bytes(data)
    return len(entries)


def pack(source, archive):
    source = source.resolve()
    if archive.resolve().is_relative_to(source):
        raise ValueError("Output archive must be outside its source directory")
    files = sorted((p for p in source.rglob("*") if p.is_file()),
                   key=lambda p: p.relative_to(source).as_posix().casefold())
    names = [str(PureWindowsPath(p.relative_to(source))).encode("cp1252") for p in files]
    if len({n.lower() for n in names}) != len(names):
        raise ValueError("Duplicate case-insensitive paths")
    sizes = [p.stat().st_size for p in files]
    offset = 16 + sum(9 + len(n) for n in names)
    total = offset + sum(sizes)
    if total >= 2 ** 32:
        raise ValueError("Archive exceeds the BIG format size limit")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with archive.open("wb") as stream:
        stream.write(b"BIGF" + struct.pack("<I", total)
                     + struct.pack(">II", len(files), offset))
        for name, size in zip(names, sizes):
            stream.write(struct.pack(">II", offset, size) + name + b"\0")
            offset += size
        for path in files:
            with path.open("rb") as input_stream:
                shutil.copyfileobj(input_stream, stream)
    return len(files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("extract", "pack"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    action = extract if args.action == "extract" else pack
    print(f"{action(args.source, args.destination)} files: {args.destination}")
