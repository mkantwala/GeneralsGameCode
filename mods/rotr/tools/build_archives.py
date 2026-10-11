"""Rebuild the imported ROTR archives, preserving their original filenames."""

import argparse
import json
from pathlib import Path

from bigfile import pack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Output directory outside mods/rotr")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.is_relative_to(root):
        parser.error("Output directory must be outside mods/rotr")
    manifest = json.loads((root / "manifest.json").read_text())
    for archive in manifest["archives"]:
        destination = output / (Path(archive["archive"]).stem + ".big")
        count = pack(root / "archives" / archive["folder"], destination)
        print(f"{destination.name}: {count} files")


if __name__ == "__main__":
    main()
