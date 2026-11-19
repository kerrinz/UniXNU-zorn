"""Fixed entry for the reviewed K80 iOS 26 Metal root delta."""

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import types


SCRIPTS = Path(__file__).resolve().parent
RUNNER = SCRIPTS / 'run-zorn-debug.py'
ROOT = SCRIPTS.parents[1]
CURRENT = ROOT / 'out/zorn/unattended-active/current.json'
REVIEW = ROOT / ('out/zorn/ios26-feasibility-20261107/build/ios-26.6.2-23G90/'
                 'k80-metal-timing-delta-review26/review-inputs.json')
REVIEW_SHA = '5d48f13aeb2d6700ecb0f16e9d11a7beb3bbfee70fac9a3b8e9a6f8ca27113f3'
SCOPE = 'K80-persistent-iOS26-metal-timing-delta-6bd2957d'
FENCE_SHA = 'ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7'
LIFETIME_FLAG = '--ios26-metal-handle-lifetime-delta'

@dataclass(frozen=True)
class InstallScope:
    review: Path
    digest: str
    name: str
    mode: str = 'unattended-phone-connected'
    check_misc: bool = False

    @property
    def admission(self):
        return self.review.parent / 'admission/admission.json'

    @property
    def run(self):
        return self.admission.parent / 'run'

CPU_NO_SAMPLING_FLAG = '--ios26-cpu-no-sampling-root-delta'
CRASH_REPORT_FLAG = '--ios26-cpu-crash-report-root-delta'
TWO_DIR_FLAG = '--ios26-cpu-two-directory-root-delta'
OSANALYTICS_FLAG = '--ios26-cpu-osanalytics-root-delta'
SERVICE_FLAG = '--ios26-cpu-service-policy-root-delta'
POSTERBOARD_REPLY_FLAG = '--ios26-cpu-posterboard-reply-root-delta'
POSTERBOARD_ARCHIVE_FLAG = '--ios26-cpu-posterboard-reply-archive-root-delta'
POSTERBOARD_ENTRY_FLAG = '--ios26-cpu-posterboard-entry-root-delta'
POSTERBOARD_RETURN_FLAG = '--ios26-cpu-posterboard-return-root-delta'
POSTERBOARD_PASSIVE_FLAG = '--ios26-cpu-posterboard-passive-root-delta'
APPLICATION186_FLAG = '--ios26-gpu-application186-root-delta'
METAL193_FLAG = '--ios26-metal193-root-delta'
METAL195_FLAG = '--ios26-metal195-root-delta'
METAL197_FLAG = '--ios26-metal197-root-delta'
METAL198_FLAG = '--ios26-metal198-root-delta'
METAL199_FLAG = '--ios26-metal199-root-delta'
METAL204_FLAG = '--ios26-metal204-root-delta'
METAL207_FLAG = '--ios26-metal207-root-delta'
METAL208_FLAG = '--ios26-metal208-root-delta'
METAL209_FLAG = '--ios26-metal209-root-delta'
METAL211_FLAG = '--ios26-metal211-root-delta'
METAL213_FLAG = '--ios26-metal213-root-delta'
METAL214_FLAG = '--ios26-metal214-root-delta'
METAL215_FLAG = '--ios26-metal215-root-delta'
METAL224_FLAG = '--ios26-metal224-root-delta'
KNOWN281_FLAG = '--ios26-known281-root-delta'
GLASS307_FLAG = '--ios26-glass307-root-delta'
KNOWN306_FLAG = '--ios26-known306-root-delta'
GLASS297_FLAG = '--ios26-glass297-root-delta'
DOCK296_FLAG = '--ios26-dock296-root-delta'
FRAME293_FLAG = '--ios26-frame293-root-delta'
KNOWN291_FLAG = '--ios26-known291-root-delta'
ASYNC290_FLAG = '--ios26-async290-root-delta'
CPU289_FLAG = '--ios26-cpu289-root-delta'
QUERY288_FLAG = '--ios26-query288-root-delta'
RPC287_FLAG = '--ios26-rpc287-root-delta'
SCALAR286_FLAG = '--ios26-scalar286-root-delta'
SCALAR285_FLAG = '--ios26-scalar285-root-delta'
DESKTOP283_FLAG = '--ios26-desktop283-root-delta'
UPSTREAM280_FLAG = '--ios26-upstream280-root-delta'
DESKTOP271_FLAG = '--ios26-desktop271-root-delta'
METAL267_FLAG = '--ios26-metal267-root-delta'
METAL252_FLAG = '--ios26-metal252-root-delta'
METAL251_FLAG = '--ios26-metal251-root-delta'
METAL250_FLAG = '--ios26-metal250-root-delta'
METAL249_FLAG = '--ios26-metal249-root-delta'
METAL247_FLAG = '--ios26-metal247-root-delta'
METAL229_FLAG = '--ios26-metal229-root-delta'
METAL228_FLAG = '--ios26-metal228-root-delta'
METAL226_FLAG = '--ios26-metal226-root-delta'
INSTALLS = {
    GLASS307_FLAG: InstallScope(REVIEW.parent.with_name('k80-glass307-restore-root-delta-review-ad7f16b4') / REVIEW.name,
        'c739480619199c047104ab2b63ee64137bba6af1a945b0f778177ada5c632f11', 'K80-persistent-iOS26-glass307-ad7f16b4', 'unattended-phone-connected', True),
    KNOWN306_FLAG: InstallScope(REVIEW.parent.with_name('k80-known306-root-delta-review-ba667cc7') / REVIEW.name,
        'b7028c014e0cca22f30d428c4b3d6e3d689218ac551c21576be911939558fd04', 'K80-persistent-iOS26-known306-ba667cc7', 'unattended-phone-connected', True),
    GLASS297_FLAG: InstallScope(REVIEW.parent.with_name('k80-glass297-root-delta-review-9c373859') / REVIEW.name,
        '1bc9c826900924d4e48c4ad58cbd3d26c1ca1c75f0046746e0c8e5d395e70ae6', 'K80-persistent-iOS26-glass297-9c373859', 'unattended-phone-connected', True),
    DOCK296_FLAG: InstallScope(REVIEW.parent.with_name('k80-dock296-root-delta-review-30ac366e') / REVIEW.name,
        '4a8cf15a015ce01b8076a2381974c40e96532ed0c66c7ae19651c3df08935b43', 'K80-persistent-iOS26-dock296-30ac366e', 'unattended-phone-connected', True),
    FRAME293_FLAG: InstallScope(REVIEW.parent.with_name('k80-frame293-root-delta-review-92a822b2') / REVIEW.name,
        '4ea342237467ac12c4fe671e9aef4810ee5306b0ad468af6c4e3f0d743f9c541', 'K80-persistent-iOS26-frame293-92a822b2', 'unattended-phone-connected', True),
    KNOWN291_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-known291-root-delta-review-ea69910e') / REVIEW.name,
        '92e69719b2fc4b3a08fa400d24ad90e0f11f44b1e67e45586cd8c79d4d6dad5e',
        'K80-persistent-iOS26-known291-ea69910e', 'unattended-phone-connected', True),
    ASYNC290_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-async290-root-delta-review-71e14658') / REVIEW.name,
        '7a2a696c8cc345defad04b406850f9d59ec56cf882e9e137b50dbe2e4313fe68',
        'K80-persistent-iOS26-async290-71e14658', 'unattended-phone-connected', True),
    CPU289_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-cpu289-root-delta-review-b584642f') / REVIEW.name,
        '34a6f19742d71af2bf53c6668a26cbc047b7784e4f80dc735761522daedb6df7',
        'K80-persistent-iOS26-cpu289-b584642f', 'unattended-phone-connected', True),
    QUERY288_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-query288-root-delta-review-9f68f2c1') / REVIEW.name,
        'ba11099cba193dc7ecea57903bd9850fc359687349bde73de83f87817b9c1861',
        'K80-persistent-iOS26-query288-9f68f2c1', 'unattended-phone-connected', True),
    RPC287_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-rpc287-root-delta-review-b6847f4e') / REVIEW.name,
        '2ed7b822a3fbeda1611a3e856cb5136e9e340aee40980e59fd84443efa12c88f',
        'K80-persistent-iOS26-rpc287-b6847f4e', 'unattended-phone-connected', True),
    SCALAR286_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-scalar286-root-delta-review-f9280b9b') / REVIEW.name,
        'f3bec719c16e0bbfefffa9ddd35c3be094f90bb84546c1fd02df86bb9be63049',
        'K80-persistent-iOS26-scalar286-f9280b9b', 'unattended-phone-connected', True),
    SCALAR285_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-scalar285-root-delta-review-878c2b95') / REVIEW.name,
        'bdc63f4de9937197673d8d1cac508f9962342a45aae5ec2f41d08ad0b981770a',
        'K80-persistent-iOS26-scalar285-878c2b95', 'unattended-phone-connected', True),
    DESKTOP283_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-desktop283-root-delta-review-45267e58') / REVIEW.name,
        '751288c0c55e84ca5939979f1c1e9f6e8cd40e6e2e5dc4e8de93184d056b06bf',
        'K80-persistent-iOS26-desktop283-45267e58', 'unattended-phone-connected', True),
    KNOWN281_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-known281-root-delta-review-36e46149') / REVIEW.name,
        '680b0ec4db336248fcdfe402958bb63a22e03f8262d19d3e624bd2efa1c7fe94',
        'K80-persistent-iOS26-known281-36e46149', 'unattended-phone-connected', True),
    UPSTREAM280_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-upstream280-root-delta-review-434fe1f2') / REVIEW.name,
        '6629293a398d57e563d2fffd393b25c9fec3e3d3ebbd6cadc485c654910124cd',
        'K80-persistent-iOS26-upstream280-434fe1f2', 'unattended-phone-connected', True),
    DESKTOP271_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-desktop271-root-delta-review-2073ff14') / REVIEW.name,
        'f76f0756dd294dfde0d94209fe3931784d28ce7ca2eaee6be5d1bba2be94f87d',
        'K80-persistent-iOS26-desktop271-2073ff14', 'unattended-phone-connected', True),
    METAL267_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal267-root-delta-review-ddb9c864') / REVIEW.name,
        '57064ffa047be7dc648f66c95b0496be5f5a8d6f36c9e02c5386d0ee873c62a1',
        'K80-persistent-iOS26-Metal267-ddb9c864', 'unattended-phone-connected', True),
    METAL252_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal252-root-delta-review-f5bb017e') / REVIEW.name,
        'e298cbd5bf8e09cd5428c621cfd317a104ffd8f0b0f607f8411e854db8ab81f5',
        'K80-persistent-iOS26-Metal252-f5bb017e', 'unattended-phone-connected', True),
    METAL251_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal251-root-delta-review-f80eb140') / REVIEW.name,
        '516675dd9f5cb93693ed1f3508ca2dcb4732e760eb8fda17253a339f77b7ee36',
        'K80-persistent-iOS26-Metal251-f80eb140', 'unattended-phone-connected', True),
    METAL250_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal250-root-delta-review-9735df98') / REVIEW.name,
        '113215ec11fa5acc375d0871c51fe8b781fe0d5b0bec3062cc674af25252d59d',
        'K80-persistent-iOS26-Metal250-9735df98', 'unattended-phone-connected', True),
    METAL249_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal249-root-delta-review-fe1bff87') / REVIEW.name,
        'cf9aad78da409201ac92c8f3254f91eaf6b7c2c2f50279ebbe4f20cae46bd6f2',
        'K80-persistent-iOS26-Metal249-fe1bff87', 'unattended-phone-connected', True),
    METAL247_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal247-root-delta-review-c0bed9d9') / REVIEW.name,
        '6087b95bbe49c6e0a65d636a0586f4b57a59605f839ad218140abbddaf500127',
        'K80-persistent-iOS26-Metal247-c0bed9d9', 'unattended-phone-connected', True),
    METAL229_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal229-root-delta-review-65f3efb4') / REVIEW.name,
        '894954dfdfdc15184894c221401bbc808b02e1fed4beacb140a1c16b76132cc8',
        'K80-persistent-iOS26-Metal229-65f3efb4', 'unattended-phone-connected', True),
    METAL228_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal228-root-delta-review-554a4178') / REVIEW.name,
        '2b4595ccc7f7548da10b3e269a4e98d05dff3a8394de41939ecbd7fb39613475',
        'K80-persistent-iOS26-Metal228-554a4178', 'unattended-phone-connected', True),
    METAL226_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal226-root-delta-review-01e033d5') / REVIEW.name,
        '321ddff72d5fccfb3db4f26f72c509bf4a0219aae8094d0f8b5ccc953bb17bf5',
        'K80-persistent-iOS26-Metal226-01e033d5', 'unattended-phone-connected', True),
    METAL224_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal224-root-delta-review-19a4a5e9') / REVIEW.name,
        '7754672d3f0fc3288371af93598497a8adacb4074d3d1f957cc56e82472cded2',
        'K80-persistent-iOS26-Metal224-19a4a5e9', 'unattended-phone-connected', True),
    METAL215_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal215-root-delta-review-e24d087c') / REVIEW.name,
        '7e5c09477a89bd4ebde36cad09605dee6e874c63d2975a691b708625dd909579',
        'K80-persistent-iOS26-Metal215-e24d087c', 'unattended-phone-connected', True),
    METAL214_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal214-root-delta-review-7a16d3fe') / REVIEW.name,
        'b219de558ec90b712bc70e89d1c4418df921f317f4fafb7305e6e2f2b860ba08',
        'K80-persistent-iOS26-Metal214-7a16d3fe', 'unattended-phone-connected', True),
    METAL213_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal213-root-delta-review-1a86e916') / REVIEW.name,
        '9654ff2826d58c68cd6356db32669139cf32c20dc4ae430c1b895a26dd945c9d',
        'K80-persistent-iOS26-Metal213-1a86e916', 'unattended-phone-connected', True),
    METAL211_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal211-root-delta-review-9e17dfb9') / REVIEW.name,
        '674db5bd1c2df1dadd84bf860e3604c4ce62523724630d9c7cfee09310767b52',
        'K80-persistent-iOS26-Metal211-9e17dfb9', 'unattended-phone-connected', True),
    METAL209_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal209-root-delta-review-74efc416') / REVIEW.name,
        'a3e5c30966ea2e1c874a911809e5681b04bcdedb6422816604f652735fa24d03',
        'K80-persistent-iOS26-Metal209-74efc416', 'unattended-phone-connected', True),
    METAL208_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal208-root-delta-review-704a8add') / REVIEW.name,
        '22cedff50f6887f2d13a5058a34a68d2b3f7a395092413170bbc443d087118a6',
        'K80-persistent-iOS26-Metal208-704a8add', 'unattended-phone-connected', True),
    METAL207_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal207-root-delta-review-20d8898a') / REVIEW.name,
        'ec72e8b5d76f514eda9e8d1647d6fdd4c611772d7ff1585cf32505c5176a2d40',
        'K80-persistent-iOS26-Metal207-20d8898a', 'unattended-phone-connected', True),
    METAL204_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal204-root-delta-review-0302d047') / REVIEW.name,
        'e2f002c2e42a9bcd6f1beb91b89b67bff2ad48a5859a8aec9b5187c69b2ca805',
        'K80-persistent-iOS26-Metal204-0302d047', 'unattended-phone-connected', True),
    METAL199_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal199-root-delta-review-e1fa9af7') / REVIEW.name,
        '48b7b2d4785b0143e0cedb756117713e7775b99fbedabb9c0b32d62bd41a851c',
        'K80-persistent-iOS26-Metal199-e1fa9af7', 'unattended-phone-connected', True),
    METAL198_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal198-root-delta-review-5af90dbd') / REVIEW.name,
        '457ee1693cf550db639289b2bf16832f85815707355fc95d9ed6bd3f5fbff6ab',
        'K80-persistent-iOS26-Metal198-5af90dbd', 'unattended-phone-connected', True),
    METAL197_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal197-root-delta-review-7d13f747') / REVIEW.name,
        'f6b044f43714e3ee9d54e37aafd56be2dc7b577561ccc090fd105187b888db7b',
        'K80-persistent-iOS26-Metal197-7d13f747', 'unattended-phone-connected', True),
    METAL195_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal195-root-delta-review-064848b2') / REVIEW.name,
        '37f9aedccaeaff012c2b0be1626bfd993ea4f37a8b250c65aa7cef9004c2b150',
        'K80-persistent-iOS26-Metal195-064848b2', 'unattended-phone-connected', True),
    METAL193_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal193-root-delta-review-754c203f') / REVIEW.name,
        '2c19da3dc791d0c4605047c11d04a85b63bd210b57a43c8016852a5e0cd07902',
        'K80-persistent-iOS26-Metal193-754c203f', 'unattended-phone-connected', True),
    APPLICATION186_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-gpu-application186-root-delta-review-d55c2bab') / REVIEW.name,
        'caf3d5346eecc7b68f2516a6a4a5c344f7f3e5bfdfde73a401bfb272704cef47',
        'K80-persistent-iOS26-GPU-application186-d55c2bab', 'unattended-phone-connected', True),
    POSTERBOARD_PASSIVE_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-cpu-posterboard-passive-delta-review26-cc9fbb3b') / REVIEW.name,
        'c2bf5950dee1b2b1ba504ec87a52458581f0c97a941b4ce4f16ce55c7742fa2f',
        'K80-persistent-iOS26-CPU-posterboard-passive-cc9fbb3b',
        'unattended-phone-connected', True),
    POSTERBOARD_RETURN_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-cpu-posterboard-return-delta-review26-2920148e') / REVIEW.name,
        '4f88009d4a01adf670dedfbff587e6b19c4da0dba7bc6a694f5b0beda1fa4fc0',
        'K80-persistent-iOS26-CPU-posterboard-return-2920148e',
        'unattended-phone-connected', True),
    POSTERBOARD_ENTRY_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-cpu-posterboard-entry-delta-review26-52a24c78') / REVIEW.name,
        'bdb51a11106ee8b18f4b951f2dfa56245f9cc5ac8686a567b299454e4448333f',
        'K80-persistent-iOS26-CPU-posterboard-entry-52a24c78',
        'unattended-phone-connected', True),
    POSTERBOARD_ARCHIVE_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-cpu-posterboard-reply-archive-review26-b85cf512') / REVIEW.name,
        '3481c95bb68eff87b0ea1184689838788e36eb5d47a56d00283440fb83ab44d3',
        'K80-persistent-iOS26-CPU-posterboard-reply-archive-b85cf512',
        'unattended-phone-connected', True),
    POSTERBOARD_REPLY_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-cpu-posterboard-reply-delta-review26-6fc92019') / REVIEW.name,
        'eb9edff13ee760a135a1cabba0d8864c5f4bb80605e619c591781c3293e5d333',
        'K80-persistent-iOS26-CPU-posterboard-reply-delta-6fc92019',
        'unattended-phone-connected', True),
    SERVICE_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-cpu-service-delta-review26-75fd3a70') / REVIEW.name,
        '013b4d897012da53995da5ea6a7c98f9636d6247205c39dd7e3fd5ba696163e4',
        'K80-persistent-iOS26-CPU-service-policy-delta-75fd3a70',
        'unattended-phone-connected', True),
    OSANALYTICS_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-cpu-osanalytics-delta-review26-471dfed2') / REVIEW.name,
        '34ca1815b312d4f96062377fa77e89e3246e8dd2a0dd9f51041f802cbda67f6e',
        'K80-persistent-iOS26-CPU-osanalytics-delta-471dfed2',
        'unattended-phone-connected', True),
    TWO_DIR_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-cpu-two-dir-delta-review26-cce96d56') / REVIEW.name,
        'f8170792c1a8ea7d99fc969cdb84884ebbf19852ef47148c75642cb1f20274c8',
        'K80-persistent-iOS26-CPU-two-directory-delta-cce96d56',
        'unattended-phone-connected', True),
    CRASH_REPORT_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-cpu-crash-report-delta-review26-cfce615b') / REVIEW.name,
        '9ab52b6833c971e1b3f0ac1bd871f792cbe38452d689b7773a82b12dd4d84b4c',
        'K80-persistent-iOS26-CPU-crash-report-delta-cfce615b',
        'unattended-phone-connected', True),
    CPU_NO_SAMPLING_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-cpu-no-sampling-delta-review26') / REVIEW.name,
        '3d6bb52cf3aac5e81e3f64250cb268111d613da49b9f6f4c5618fdeaa8a5e787',
        'K80-persistent-iOS26-CPU-no-sampling-delta-63f9631a',
        'unattended-phone-connected'),
    '--ios26-metal-root-delta': InstallScope(REVIEW, REVIEW_SHA, SCOPE),
    LIFETIME_FLAG: InstallScope(
        REVIEW.parent.with_name('k80-metal-handle-lifetime-delta-review26') / REVIEW.name,
        'b6376b1a2b7adc17c7ab2a12ac4943220ce8be8eaef441c138030fb6930f5787',
        'K80-persistent-iOS26-metal-handle-lifetime-delta-5b2e86db'),
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def exact(document, expected):
    return all(type(document.get(key)) is type(value) and document[key] == value
               for key, value in expected.items())


def save(path, value, exclusive=False):
    with path.open('x' if exclusive else 'w') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def save_current(value):
    temporary = CURRENT.with_name('current.metal-root-delta.tmp')
    save(temporary, value, True)
    os.replace(temporary, CURRENT)


def validate_review(path, scope):
    if path != scope.review or path.resolve() != path or sha(path) != scope.digest:
        raise ValueError('exact canonical Metal root delta review required')
    review = load(path)
    for role, pin in review['pins'].items():
        source, archive = (Path(pin[key]) for key in ('path', 'archive'))
        for file in (source, archive):
            if (file.is_symlink() or not file.is_file() or file.stat().st_size != pin['bytes']
                    or sha(file) != pin['sha256']):
                raise ValueError(f'changed review input {role}')
        if source.samefile(archive):
            raise ValueError(f'review archive shares inode for {role}')
    for role, name in {'grouping_implementation': 'zorn_ios26_root_delta.py',
                       'transport_implementation': 'zorn_ios26_root_install.py',
                       'recovery_identity': 'zorn_recovery_identity.py'}.items():
        if Path(review['pins'][role]['path']) != SCRIPTS / name:
            raise ValueError(f'fixed transport input differs for {role}')
    if scope.check_misc and (review.get('BCB_read_only_full_page_and_tail_guard') is not True
            or review['pins']['previous_misc']['bytes'] != 4096):
        raise ValueError('CPU root delta full-page BCB protection missing')
    return review


def reviewed_module(review, role, name):
    pin = review['pins'][role]
    path = Path(pin['path'])
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != pin['sha256']:
        raise ValueError(f'reviewed source changed for {role}')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(source, str(path), 'exec'), module.__dict__)
    return module


def require_admission_state(review, scope, active_run=None):
    current = load(CURRENT)
    gpu = current.get('gpu_discovery', {})
    if (gpu.get('current_mode') != scope.mode or
            gpu.get('active_admission') != str(scope.admission) or
            gpu.get('allow_boot') is not False or gpu.get('allow_readback') is not False or
            gpu.get('current_phone_root_expected_sha256') != review['window']['old_root_sha256'] or
            current.get('active_run') != active_run or
            any(current.get(key) for key in ('active_admission', 'active_build', 'runner_session', 'stop_device_operations'))):
        raise ValueError('Metal root delta device admission is closed')
    return current


def validate_admission(path, review, scope):
    require_admission_state(review, scope)
    if path != scope.admission or path.resolve() != path or scope.run.exists() or scope.run.is_symlink():
        raise ValueError('fresh canonical Metal root delta admission required')
    window = review['window']
    required = dict(scope=scope.name, review_sha256=scope.digest, serial='92988a43', product='zorn', slot='a',
                    partition='unixnu', relative_first_lba=window['relative_first_lba'],
                    old_root_sha256=window['old_root_sha256'], new_root_sha256=window['new_root_sha256'],
                    blocks=window['blocks'], changed_pages=review['changed_pages'], write_groups=review['write_groups'],
                    timeout_seconds=review['proposed_timeout_seconds'], retries=0, allow_install=True,
                    allow_boot=False, full_phone_root_readback=False, layout_change=False,
                    entry_sha256=sha(__file__), runner_sha256=sha(RUNNER))
    admission = load(path)
    if not exact(admission, required):
        raise ValueError('Metal root delta admission does not bind this exact operation')
    for role, flag in (('owner', 'approved'), ('ready', 'ready')):
        record = path.parent / (role + '.json')
        if (record.resolve() != record or not record.is_file() or
                admission[role] != dict(path=str(record), sha256=sha(record)) or
                not exact(load(record), required | {flag: True})):
            raise ValueError(f'fresh exact Metal root delta {role} record required')
    return required


def inspect_misc_page(misc, prior):
    if (len(misc)!=4096 or len(prior)!=4096 or misc[2048:]!=prior[2048:]
            or misc[:32].split(bytes(1),1)[0] not in (b'',b'boot-recovery')):
        raise RuntimeError('BCB full-page command/tail protection differs')


def run(review, admission_path, scope):
    binding = validate_admission(admission_path, review, scope)
    run_dir = scope.run
    # Host-only availability check precedes the one-shot claim and state changes.
    # Never consume an installation admission merely because its existing server
    # is absent;this does not start a server or send an ADB request.
    with socket.create_connection(('127.0.0.1', 5039), timeout=.2):
        pass
    adapter = reviewed_module(review, 'recovery_adapter', 'recovery_metal_root_delta')
    from zorn_ios26_root_install import Recovery

    class ReviewedRecovery(Recovery):
        def protections(self):
            state = super().protections()
            if any(hashlib.sha256(state[key]).hexdigest() != FENCE_SHA for key in ('before', 'after')):
                raise RuntimeError('root window fences differ from the retained readback')
            if scope.check_misc:
                if self.command(['shell','readlink','-f','/dev/block/by-name/misc']).decode().strip() != '/dev/block/sda11':
                    raise RuntimeError('fixed BCB device differs')
                misc=self.command(['exec-out','dd if=/dev/block/by-name/misc bs=4096 count=1 2>/dev/null'])
                prior=Path(review['pins']['previous_misc']['path']).read_bytes()
                inspect_misc_page(misc,prior)
                state['misc']=misc
            return state

    run_dir.mkdir()
    save(run_dir / 'one-shot.claim.json', dict(scope=scope.name, admission_sha256=sha(admission_path),
         consumed_before_first_USB=True, reusable=False), True)
    status = dict(scope=scope.name, installed=False, writes_attempted=False, pages_written=0, booted=False,
                  full_root_readback_performed=False, phase='claimed')
    receipt = run_dir / 'result.json'
    save(receipt, status, True)
    current = require_admission_state(review, scope)
    current['active_run'] = str(run_dir)
    save_current(current)
    try:
        pins = review['pins']
        transport = ReviewedRecovery(dict(pins={key: pins['previous_' + key]
            for key in ('adb', 'primary_GPT', 'backup_GPT', 'Data', 'root_manifest')},
            timeout_seconds=binding['timeout_seconds'], existing_server_only=True), run_dir)

        def before_write(identity):
            require_admission_state(review, scope, str(run_dir))
            status.update(phase='writing', writes_attempted=True, recovery_identity_before=identity)
            save(receipt, status)

        def group_verified(index, block, pages):
            status.update(last_verified_group=index, last_verified_block=block, pages_written=pages)
            save(receipt, status)
            require_admission_state(review, scope, str(run_dir))

        result = adapter.install(transport, run_dir, before_write, group_verified)
        expected = load(pins['local_replay']['path'])['replay']['changed_page_readback_sha256']
        if result['readback']['sha256'] != expected:
            raise RuntimeError('aggregate changed-page readback does not match the exact local replay')
        status.update(result, installed=True, phase='root-delta-installed-written-blocks-readback-verified',
                      expected_image_sha256=binding['new_root_sha256'])
    except BaseException as error:
        status.update(phase='stopped-no-retry', error=repr(error))
        raise
    finally:
        save(receipt, status)
        current = load(CURRENT)
        if current.get('active_run') == str(run_dir):
            current['active_run'] = None
            gpu = current['gpu_discovery']
            if gpu.get('active_admission') == str(scope.admission):
                gpu['active_admission'] = None
            gpu['latest_metal_root_delta_installation'] = str(receipt)
            if status['installed']:
                gpu.update(current_phone_root_expected_sha256=binding['new_root_sha256'],
                           current_phone_root_input=load(pins['composed_root']['path'])['image'],
                           current_phone_root_verification=f"{status['pages_written']} written pages and protected metadata verified in Recovery")
            elif status['writes_attempted'] or scope.check_misc:
                current.update(stop_device_operations=True, stop_device_reason='Metal root delta incomplete; preserve Recovery and evidence')
            save_current(current)
        print(json.dumps(status), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    flags = [flag for flag in INSTALLS if flag in sys.argv]
    if len(flags) != 1:
        parser.error('one exact root install flag required')
    flag, = flags
    scope = INSTALLS[flag]
    parser.add_argument(flag, required=True, type=Path, dest='review')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check', action='store_true')
    action.add_argument('--admission', type=Path)
    args = parser.parse_args()
    try:
        if Path(sys.argv[0]).resolve() != RUNNER:
            raise ValueError('maintained fixed runner required')
        review = validate_review(args.review, scope)
        if args.admission:
            require_admission_state(review, scope)
        plan = reviewed_module(review, 'plan_source', 'metal_root_delta_plan')
        _, parts, retained = plan.load_plan()
        if args.check:
            print(json.dumps(dict(scope=scope.name, changed_pages=review['changed_pages'],
                write_groups=len(parts), prior_changed_pages=sum(len(raw)//plan.PAGE for _,raw in retained), device_access=False, claim_created=False)))
            return
        run(review, args.admission, scope)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
