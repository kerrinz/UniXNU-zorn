"""Add the Pineapple K80 GPU QTB to the isolated iOS 26 candidate ADT."""

import argparse
from pathlib import Path
import struct
import sys


SMMU_COMPATIBLE = b'qcom,qsmmu-v500\0qcom,adreno-smmu\0'
SMMU_REG = struct.pack('<QQ', 0x2DA0000, 0x40000)
PROPERTIES = {
    'name': b'gpu-qtb\0',
    'compatible': b'qcom,qsmmuv500-tbu\0qcom,qtb500\0',
    'reg': struct.pack('<III', 0x3DE8000, 0, 0x1000),
    'reg-names': b'base\0',
    'qcom,stream-id-range': struct.pack('<II', 0, 0x400),
    'qcom,iova-width': struct.pack('<I', 49),
    'qcom,num-qtb-ports': struct.pack('<I', 2),
    'k80,source-icc-route': struct.pack('>II', 0, 512),
}


def qtb_parent(root):
    if (root.get('model') != b'iPhone18,1\0' or
            b'xiaomi,zorn' not in (root.get('compatible') or b'').split(b'\0')):
        raise ValueError('expected the K80 iOS 26 candidate ADT')
    arm_io, = (node for node in root.children if node.name == 'arm-io')
    smmu, = (node for node in arm_io.children if node.name == 'gpu-smmu')
    if smmu.get('compatible') != SMMU_COMPATIBLE or smmu.get('reg') != SMMU_REG:
        raise ValueError('unexpected K80 GPU SMMU controller')
    return smmu


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--adt-codec-directory', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.adt_codec_directory.resolve()))
    from ios26_adt import Node, parse, serialize

    original = args.source.read_bytes()
    tree = parse(original)
    if serialize(tree) != original:
        raise ValueError('input ADT cannot round trip')
    smmu = qtb_parent(tree)
    if smmu.children or any(smmu.get(key) is not None for key in
                            ('#address-cells', '#size-cells', 'ranges')):
        raise ValueError('unexpected GPU SMMU child addressing')
    # The Apple arm64 resolver defaults to two address cells and one size
    # cell. Keep Linux's MMIO coordinates and use the resolver's cell format.
    qtb = Node()
    for key, value in PROPERTIES.items():
        qtb.set(key, value)
    smmu.children.append(qtb)
    encoded = serialize(tree)
    check = parse(encoded)
    child = qtb_parent(check).children.pop()
    if {key: value for key, _, value in child.properties} != PROPERTIES:
        raise ValueError('GPU QTB property readback differs')
    if serialize(check) != original:
        raise ValueError('unrelated ADT input changed')
    with args.output.open('xb') as output:
        output.write(encoded)


if __name__ == '__main__':
    main()
