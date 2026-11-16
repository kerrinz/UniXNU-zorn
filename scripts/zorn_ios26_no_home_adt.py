"""Describe the K80's button hardware in an isolated iOS 26 Apple device tree."""

import argparse
import struct
from pathlib import Path


BUTTON_PROPERTIES = {
    "name": b"buttons\0",
    "compatible": b"buttons\0",
    "device_type": b"buttons\0",
    "button-names": b"hold\0voldown\0volup\0",
    "home-button-type": struct.pack("<I", 2),
}


def add_buttons(root, node_type):
    if root.get("model") != b"iPhone18,1\0" or root.get("target-type") != b"V53\0":
        raise ValueError("expected the iOS 26 phone identity")
    if b"xiaomi,zorn" not in (root.get("compatible") or b"").split(b"\0"):
        raise ValueError("expected the K80 device tree")
    if any(child.name == "buttons" for child in root.children):
        raise ValueError("button configuration already present")
    buttons = node_type()
    for name, value in BUTTON_PROPERTIES.items():
        buttons.set(name, value)
    root.children.append(buttons)


def main():
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--adt-codec-directory", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.adt_codec_directory.resolve()))
    from ios26_adt import Node, parse, serialize

    original = args.source.read_bytes()
    tree = parse(original)
    if serialize(tree) != original:
        raise ValueError("input ADT cannot round trip byte for byte")
    add_buttons(tree, Node)
    encoded = serialize(tree)
    check = parse(encoded)
    buttons = check.children.pop()
    if dict((key, value) for key, flags, value in buttons.properties) != BUTTON_PROPERTIES:
        raise ValueError("button property readback differs")
    if serialize(check) != original:
        raise ValueError("unrelated ADT input changed")
    with args.output.open("xb") as stream:
        stream.write(encoded)


if __name__ == "__main__":
    main()
