"""Single K80 display boot from the verified installed iOS 26 UFS root."""
import argparse
import gzip
import io
import json
import struct
import sys
import tomllib
from pathlib import Path

from zorn_ios26_logdirs_boot_trial import ARGS, CURRENT, EXPECTED, STAGE, load, run, sha
from zorn_ios26_metal_root_delta import SCOPE as INSTALL_SCOPE

NONCE = 'bd7de07038da4884b9fec9eb4134129e'
BASE = STAGE / f'k80-metal-timing-display-boot26-{NONCE}' / 'root-trial-display'
RUNNER = Path(__file__).with_name('run-zorn-debug.py')
PACKAGE_SHA = '2a0b6440823a8612fa526660b69a916fe92e730b2d20cf124fb347ce5ebdb4f4'
ROOT_SHA = 'ce6af105a2cc4b90f3921ecc7151098ebfa25f756fdcff5e2d3758ff1cc8f105'
SCOPE = 'single-K80-ios26-installed-metal-display-CPU300s'
FLAG = '--ios26-metal-display-trial'
POLICY = EXPECTED | {'scope': SCOPE}
CPU_FLAG = '--ios26-metal-cpu-presenter-trial'
CPU_NONCE = '8997ed70fead493eb21c4f1bf0e6f47a'
CPU_BASE = STAGE / f'k80-metal-cpu-presenter-boot26-{CPU_NONCE}' / 'root-trial-cpu-presenter'
CPU_SCOPE = 'single-K80-ios26-installed-metal-cpu-presenter-300s'
CPU_PACKAGE_SHA = '2a849d06517fc9c024185affa51f910533924ae4057077c662ceb73819054a13'
CPU_POLICY = POLICY | {'scope': CPU_SCOPE, 'CPU_presenter': True}
CPU_ARGS = ARGS + ' zorn26_cpu_presenter=1'
FIRST_SWAP_FLAG = '--ios26-metal-first-swap-trial'
FIRST_SWAP_NONCE = 'd75096e75ea34f28a51596e230bb7666'
FIRST_SWAP_BASE = STAGE / f'k80-metal-first-swap-boot26-{FIRST_SWAP_NONCE}' / 'root-trial-first-swap'
FIRST_SWAP_SCOPE = 'single-K80-ios26-installed-metal-first-swap-300s'
FIRST_SWAP_PACKAGE_SHA = 'd306ead289ef392c73da24e43f5409594632ec0efdb35c5a247890fa6b6a5fbb'
FIRST_SWAP_POLICY = CPU_POLICY | {'scope': FIRST_SWAP_SCOPE}
CONTROL_FLAG = '--ios26-current-root-userland-control-trial'
CONTROL_NONCE = '5aebd51d85824f5594884bdef014921c'
CONTROL_BASE = STAGE / 'k80-current-root-userland-control26-5aebd51d85824f5594884bdef014921c' / 'root-trial-control'
CONTROL_SCOPE = 'single-K80-ios26-current-root-userland-control-300s-5aebd51d'
CONTROL_PACKAGE_SHA = '37d8d4bf26ea35239fc6aeba11c7c2f2b296e282558944dd341c8f0ffe362d48'
CONTROL_ROOT_SHA = 'fa6b90ea04d56d308bfec97e24f12614f5060994f6a91141c2bda3672e153a9f'
CONTROL_INSTALL_SCOPE = 'K80-persistent-iOS26-metal-handle-lifetime-delta-5b2e86db'
CONTROL_POLICY = CPU_POLICY | {'scope': CONTROL_SCOPE}
TOUCH_USERLAND_FLAG = '--ios26-current-root-finite-touch-userland-trial'
TOUCH_USERLAND_NONCE = 'c74a15c517894a36aec1b4454fa061ff'
TOUCH_USERLAND_BASE = STAGE / 'k80-current-root-finite-touch-userland26-c74a15c517894a36aec1b4454fa061ff' / 'root-trial-finite-touch'
TOUCH_USERLAND_SCOPE = 'single-K80-ios26-current-root-finite-touch-userland-300s-c74a15c5'
TOUCH_USERLAND_PACKAGE_SHA = 'babbef6b4cdd4528ed5284297dd0fcc4ffd5d74f13677888a6c9abf52b07f2fb'
TOUCH_USERLAND_POLICY = CONTROL_POLICY | {'scope': TOUCH_USERLAND_SCOPE, 'touch_startup': True}
TOUCH_USERLAND_ARGS = CPU_ARGS + ' zorn26_touch=1 zorn26_touch_pacing=1 zorn26_touch_limit=64'
VSYNC_FLAG = '--ios26-cpu-display-vsync-trial'
VSYNC_NONCE = 'f317965bc34943da9cc2de89789c34ba'
VSYNC_BASE = STAGE / f'k80-cpu-display-vsync-trial26-{VSYNC_NONCE}' / 'root-trial-vsync'
VSYNC_SCOPE = 'single-K80-ios26-cpu-display-vsync-300s-f317965b'
VSYNC_PACKAGE_SHA = '8089bd430c42ce697828856cec758067ce669646c3363466d8b619901b5072e0'
VSYNC_POLICY = CONTROL_POLICY | {'scope': VSYNC_SCOPE}
FIRST_FRAME_FLAG = '--ios26-cpu-display-first-frame-trial'
FIRST_FRAME_NONCE = '683fffef75e94a2f8c15995a8a63599f'
FIRST_FRAME_BASE = STAGE / f'k80-cpu-display-first-frame-trial26-{FIRST_FRAME_NONCE}' / 'root-trial-first-frame'
FIRST_FRAME_SCOPE = 'single-K80-ios26-cpu-display-first-frame-300s-683fffef'
FIRST_FRAME_PACKAGE_SHA = 'd59069b2d933df229bb5a9a719b19280631223091dbd770f06eaee6e67105b0f'
FIRST_FRAME_POLICY = CONTROL_POLICY | {'scope': FIRST_FRAME_SCOPE}
DISPLAY_WAIT_FLAG = '--ios26-cpu-display-wait-trial'
DISPLAY_WAIT_NONCE = '9a73b7f536f14525b726ed66be2cb91d'
DISPLAY_WAIT_BASE = STAGE / f'k80-cpu-display-wait-trial26-{DISPLAY_WAIT_NONCE}' / 'root-trial-display-wait'
DISPLAY_WAIT_SCOPE = 'single-K80-ios26-cpu-display-wait-300s-9a73b7f5'
DISPLAY_WAIT_PACKAGE_SHA = '216e95894156f5b4311c2b205175f7f42badfa217d9da80b7623b480a36e18ee'
DISPLAY_WAIT_POLICY = CONTROL_POLICY | {'scope': DISPLAY_WAIT_SCOPE}
SOFTWARE_ACCEL_FLAG = '--ios26-cpu-software-accelerator-trial'
SOFTWARE_ACCEL_NONCE = 'e5f4eccd83e84548ba69d2fcda9cba32'
SOFTWARE_ACCEL_BASE = STAGE / f'k80-cpu-software-accelerator26-{SOFTWARE_ACCEL_NONCE}' / 'root-trial-software-accelerator'
SOFTWARE_ACCEL_SCOPE = 'single-K80-ios26-cpu-software-accelerator-300s-e5f4eccd'
SOFTWARE_ACCEL_PACKAGE_SHA = 'a92c49d57b5f2190f9ac9567e668c905442ec5fee8399ed3aeef3022ab156c9f'
SOFTWARE_ACCEL_POLICY = CONTROL_POLICY | {'scope': SOFTWARE_ACCEL_SCOPE}
SOFTWARE_ACCEL_ARGS = CPU_ARGS + ' zorn26_software_accelerator=1'
IOSURFACE_ROOT_FLAG = '--ios26-cpu-iosurface-root-trial'
IOSURFACE_ROOT_NONCE = '7cd831d38aa44929a90f9b35e0fa8e2f'
IOSURFACE_ROOT_BASE = STAGE / f'k80-iosurface-root26-{IOSURFACE_ROOT_NONCE}' / 'root-trial-iosurface'
IOSURFACE_ROOT_SCOPE = 'single-K80-ios26-cpu-iosurface-root-300s-7cd831d3'
IOSURFACE_ROOT_PACKAGE_SHA = '23c05699fd846b6851cf164d40176e8c649b6df52a6bcb2769062a416e55f329'
IOSURFACE_ROOT_POLICY = CONTROL_POLICY | {'scope': IOSURFACE_ROOT_SCOPE}
SURFACE_PLATFORM_FLAG = '--ios26-cpu-iosurface-platform-trial'
SURFACE_PLATFORM_NONCE = 'a8c8da33402e4c5882f1a5a0f8f733f9'
SURFACE_PLATFORM_BASE = STAGE / f'k80-iosurface-platform-order26-{SURFACE_PLATFORM_NONCE}' / 'root-trial-platform-surface'
SURFACE_PLATFORM_SCOPE = 'single-K80-ios26-cpu-iosurface-platform-300s-a8c8da3'
SURFACE_PLATFORM_PACKAGE_SHA = 'a24408c0bd0517dc9e80a852d64e65c03f32bf6d0f305798af5fba98577b026f'
SURFACE_PLATFORM_POLICY = CONTROL_POLICY | {'scope': SURFACE_PLATFORM_SCOPE, 'userland_snapshot_seconds': 10}
SURFACE_CLIENT_FLAG = '--ios26-cpu-iosurface-client-trial'
SURFACE_CLIENT_NONCE = '8c274827f2e54cc1b10d6202d791a86e'
SURFACE_CLIENT_BASE = STAGE / f'k80-iosurface-client26-{SURFACE_CLIENT_NONCE}' / 'root-trial-surface-client'
SURFACE_CLIENT_SCOPE = 'single-K80-ios26-cpu-iosurface-client-300s-8c274827'
SURFACE_CLIENT_PACKAGE_SHA = '5342d1e962b79b22d00728fa3df8fadd5bc2c971e50e13eff49371e0ea9854c1'
SURFACE_CLIENT_POLICY = CONTROL_POLICY | {'scope': SURFACE_CLIENT_SCOPE, 'userland_snapshot_seconds': 45}
SURFACE_RECORD_FLAG = '--ios26-cpu-iosurface-record-lock-trial'
SURFACE_RECORD_NONCE = '3c6e375dbb0240b386dfcde035334d37'
SURFACE_RECORD_BASE = STAGE / f'k80-iosurface-record-lock26-{SURFACE_RECORD_NONCE}' / 'root-trial-record-lock'
SURFACE_RECORD_SCOPE = 'single-K80-ios26-cpu-iosurface-record-lock-300s-3c6e375d'
SURFACE_RECORD_PACKAGE_SHA = 'e592fa3df9fa6287537149cec8a7054c3fccc01d282de3e77f91c2ec6a393333'
SURFACE_RECORD_POLICY = SURFACE_CLIENT_POLICY | {'scope': SURFACE_RECORD_SCOPE}
SURFACE_CREATE_FLAG = '--ios26-cpu-iosurface-create-trial'
SURFACE_CREATE_NONCE = '0ce5f1b5d58b4ef788925efea1fa586a'
SURFACE_CREATE_BASE = STAGE / f'k80-iosurface-create-checkpoint26-{SURFACE_CREATE_NONCE}' / 'root-trial-create'
SURFACE_CREATE_SCOPE = 'single-K80-ios26-cpu-iosurface-create-300s-0ce5f1b5'
SURFACE_CREATE_PACKAGE_SHA = 'ec93f77f76cf7e39026c71a694c086a4d5de0fef8105cbaa6ff21f6d8dad8984'
SURFACE_CREATE_POLICY = SURFACE_RECORD_POLICY | {'scope': SURFACE_CREATE_SCOPE}
SURFACE_INIT_FLAG = '--ios26-cpu-iosurface-init-trial'
SURFACE_INIT_NONCE = 'c791b1460a1a45cf83e59d3f9f388b87'
SURFACE_INIT_BASE = STAGE / f'k80-iosurface-init-record26-{SURFACE_INIT_NONCE}' / 'root-trial-init'
SURFACE_INIT_SCOPE = 'single-K80-ios26-cpu-iosurface-init-300s-c791b146'
SURFACE_INIT_PACKAGE_SHA = 'e9c273e6e93735930e5d1682a9eab1104aa54b9d2ffd9a1b769901e004cd4768'
SURFACE_INIT_POLICY = SURFACE_CREATE_POLICY | {'scope': SURFACE_INIT_SCOPE}
FB_UNSUPPORTED_FLAG = '--ios26-cpu-framebuffer-unsupported-trial'
FB_UNSUPPORTED_NONCE = '1ae185ae1f1a4116b8ffb207b41703b4'
FB_UNSUPPORTED_BASE = STAGE / f'k80-framebuffer-unsupported26-{FB_UNSUPPORTED_NONCE}' / 'root-trial-unsupported'
FB_UNSUPPORTED_SCOPE = 'single-K80-ios26-cpu-framebuffer-unsupported-300s-1ae185ae'
FB_UNSUPPORTED_PACKAGE_SHA = '7cca7ef8b16500eda2cc488f9a301082a51e503e207514d1ef43b4deb1377057'
FB_UNSUPPORTED_POLICY = SURFACE_INIT_POLICY | {'scope': FB_UNSUPPORTED_SCOPE}
THREAD_CENSUS_FLAG = '--ios26-cpu-thread-census-trial'
THREAD_CENSUS_NONCE = '07de2f2c64464e87afe40dde5118a4ec'
THREAD_CENSUS_BASE = STAGE / f'k80-cpu-thread-census26-{THREAD_CENSUS_NONCE}' / 'root-trial-census'
THREAD_CENSUS_SCOPE = 'single-K80-ios26-cpu-thread-census-300s-07de2f2c'
THREAD_CENSUS_PACKAGE_SHA = '43ebdb6c869a197febed8ce290e1d1633f865b04181b46118d6eb84a792e6b69'
THREAD_CENSUS_POLICY = FB_UNSUPPORTED_POLICY | {'scope': THREAD_CENSUS_SCOPE}
CPU_NO_SAMPLING_FLAG = '--ios26-cpu-no-sampling-trial'
CPU_NO_SAMPLING_NONCE = '63f9631a54c744a598be73540dc4b541'
CPU_NO_SAMPLING_BASE = STAGE / f'k80-cpu-no-sampling-boot26-{CPU_NO_SAMPLING_NONCE}' / 'root-trial-no-sampling'
CPU_NO_SAMPLING_SCOPE = 'single-K80-ios26-CPU-no-sampling-300s-63f9631a'
CPU_NO_SAMPLING_PACKAGE_SHA = 'e41766be93ece4cdaef02a173301c714a1bf80fe092313931a5c1b33d8ef44d1'
CPU_NO_SAMPLING_ROOT_SHA = '3b56c850bd9416e7716094a20ea0af0c25bd767b1e94a022aff6945fcf54cd6d'
CPU_NO_SAMPLING_INSTALL_SCOPE = 'K80-persistent-iOS26-CPU-no-sampling-delta-63f9631a'
CPU_NO_SAMPLING_POLICY = THREAD_CENSUS_POLICY | {'scope': CPU_NO_SAMPLING_SCOPE}
SB_LIFECYCLE_FLAG = '--ios26-cpu-sb-lifecycle-trial'
SB_LIFECYCLE_NONCE = 'afed6c22a4dd4a07b0ddb45fe428c0a8'
SB_LIFECYCLE_BASE = STAGE / f'k80-cpu-sb-lifecycle26-{SB_LIFECYCLE_NONCE}' / 'root-trial-sb-lifecycle'
SB_LIFECYCLE_SCOPE = 'single-K80-ios26-CPU-SpringBoard-lifecycle-300s-afed6c22'
SB_LIFECYCLE_PACKAGE_SHA = '9f36a0195233a1e039d8b623278168d64918b9b7f089ee978a551525e9265cc2'
SB_LIFECYCLE_POLICY = CPU_NO_SAMPLING_POLICY | {'scope': SB_LIFECYCLE_SCOPE}
SB_STDERR_FLAG = '--ios26-cpu-sb-stderr-trial'
SB_STDERR_NONCE = '50e6a1f40a944a5189085416166c4ee4'
SB_STDERR_BASE = STAGE / f'k80-cpu-sb-stderr26-{SB_STDERR_NONCE}' / 'root-trial-sb-stderr'
SB_STDERR_SCOPE = 'single-K80-ios26-CPU-SpringBoard-stderr-300s-50e6a1f4'
SB_STDERR_PACKAGE_SHA = '2a4579281e81ea2fcb79275ca97e9e0228f2354713d2ae5745274ab7be1aeee0'
SB_STDERR_POLICY = SB_LIFECYCLE_POLICY | {'scope': SB_STDERR_SCOPE}
CRASH_REPORT_FLAG = '--ios26-cpu-crash-report-trial'
CRASH_REPORT_NONCE = 'cfce615b97d340f3aac992a6b38adfff'
CRASH_REPORT_BASE = STAGE / f'k80-cpu-crash-report26-{CRASH_REPORT_NONCE}' / 'root-trial-crash-report'
CRASH_REPORT_SCOPE = 'single-K80-ios26-CPU-crash-report-300s-cfce615b'
CRASH_REPORT_PACKAGE_SHA = '4441e0df2c4a7c5297b8118914b8ee1e8816e68d406fc6fac97d564ee686dd54'
CRASH_REPORT_ROOT_SHA = '55cf33b108c209a8fbafcc4ad16f2ac3bb39e0645ee9688c0a34908b0a1fccc5'
CRASH_REPORT_INSTALL_SCOPE = 'K80-persistent-iOS26-CPU-crash-report-delta-cfce615b'
CRASH_REPORT_POLICY = SB_STDERR_POLICY | {'scope': CRASH_REPORT_SCOPE}
ATTENDED_FLAGS = (THREAD_CENSUS_FLAG, FB_UNSUPPORTED_FLAG, SURFACE_INIT_FLAG, VSYNC_FLAG, FIRST_FRAME_FLAG, DISPLAY_WAIT_FLAG, SOFTWARE_ACCEL_FLAG, IOSURFACE_ROOT_FLAG,
                  SURFACE_PLATFORM_FLAG, SURFACE_CLIENT_FLAG, SURFACE_RECORD_FLAG, SURFACE_CREATE_FLAG)
DELIVERY_FLAG = '--ios26-cpu-crash-delivery-trial'
DELIVERY_NONCE = '8749f37cf3bc4059a891ec7576f04473'
DELIVERY_BASE = STAGE / f'k80-cpu-crash-delivery26-{DELIVERY_NONCE}' / 'root-trial-crash-delivery'
DELIVERY_SCOPE = 'single-K80-ios26-CPU-crash-delivery-300s-8749f37c'
DELIVERY_PACKAGE_SHA = '218bbe2c6f22c6746b431ba1c43c27cf94004b57a5839b10a397cd717ee5286b'
DELIVERY_POLICY = CRASH_REPORT_POLICY | {'scope': DELIVERY_SCOPE}

FIRST_DELIVERY_FLAG = '--ios26-cpu-crash-delivery-first-trial'
FIRST_DELIVERY_NONCE = 'd09cf4494909450d9e79919be4018b35'
FIRST_DELIVERY_BASE = STAGE / f'k80-cpu-crash-delivery26-{FIRST_DELIVERY_NONCE}' / 'root-trial-crash-delivery'
FIRST_DELIVERY_SCOPE = 'single-K80-ios26-CPU-crash-delivery-first-300s-d09cf449'
FIRST_DELIVERY_PACKAGE_SHA = '08c829bbf2045dbc885d6ebd53b258ad6d0bf2de7f013b0a89f331bca99b8ca9'
FIRST_DELIVERY_POLICY = DELIVERY_POLICY | {'scope': FIRST_DELIVERY_SCOPE}
CORPSE_FLAG = '--ios26-cpu-corpse-notify-trial'
CORPSE_NONCE = '0162bfa3de824abbac6eca061b7b4ff0'
CORPSE_BASE = STAGE / f'k80-cpu-corpse-notify26-{CORPSE_NONCE}' / 'root-trial-crash-delivery'
CORPSE_SCOPE = 'single-K80-ios26-CPU-corpse-notify-300s-0162bfa3'
CORPSE_PACKAGE_SHA = '496d2bf2d468526aac06629cde91ba1561316f4bece629079a69641489657324'
CORPSE_POLICY = DELIVERY_POLICY | {'scope': CORPSE_SCOPE}
FILES_FLAG = '--ios26-cpu-reporter-files-trial'
FILES_NONCE = '21097527010044438c4647151430803c'
FILES_BASE = STAGE / f'k80-cpu-reporter-files26-{FILES_NONCE}' / 'root-trial-crash-delivery'
FILES_SCOPE = 'single-K80-ios26-CPU-reporter-files-300s-21097527'
FILES_PACKAGE_SHA = 'f5b7d517c431c7a6f86ff64009d53716bcac15937c5e964fba2d7f285c5db3a5'
FILES_POLICY = DELIVERY_POLICY | {'scope': FILES_SCOPE}
DELIVERY_FLAGS = (DELIVERY_FLAG, FIRST_DELIVERY_FLAG, CORPSE_FLAG, FILES_FLAG)

TWO_DIR_REPORT_FLAG = '--ios26-cpu-two-directory-report-trial'
TWO_DIR_REPORT_NONCE = 'cce96d56630b4b0680fe31845102c730'
TWO_DIR_REPORT_BASE = STAGE / f'k80-cpu-crash-report-two-dir26-{TWO_DIR_REPORT_NONCE}' / 'root-trial-two-dir-report'
TWO_DIR_REPORT_SCOPE = 'single-K80-ios26-CPU-two-directory-report-300s-cce96d56'
TWO_DIR_REPORT_PACKAGE_SHA = '28db49fe033972c423f53b48b6974d4ed9bbb605188e438a76a0e66c79e4f40b'
TWO_DIR_REPORT_ROOT_SHA = '176355f5ca17520b69014abc73bdf3b937455277425c7a1c810de689f2b9cad1'
TWO_DIR_REPORT_INSTALL_SCOPE = 'K80-persistent-iOS26-CPU-two-directory-delta-cce96d56'
TWO_DIR_REPORT_POLICY = CRASH_REPORT_POLICY | {'scope': TWO_DIR_REPORT_SCOPE}

PATH_FLAG = '--ios26-cpu-reporter-path-trial'
PATH_NONCE = '39e92205768b4df9b252f1351d5c6279'
PATH_BASE = STAGE / f'k80-cpu-reporter-path26-{PATH_NONCE}' / 'root-trial-reporter-path'
PATH_SCOPE = 'single-K80-ios26-CPU-reporter-path-300s-39e92205'
PATH_PACKAGE_SHA = 'a2673c8ee7199df06a24976055603fdb721e2bd2a28ea14b916efb3841c80220'
PATH_POLICY = CRASH_REPORT_POLICY | {'scope': PATH_SCOPE}

LOG_FLAG = '--ios26-cpu-general-log-trial'
LOG_NONCE = 'b2043ae869d04eb2b4dcf33ec001d6f8'
LOG_BASE = STAGE / f'k80-cpu-general-log26-{LOG_NONCE}' / 'root-trial-general-log'
LOG_SCOPE = 'single-K80-ios26-CPU-general-log-300s-b2043ae8'
LOG_PACKAGE_SHA = 'd9b32eedf7c1046edae691965f4317dfd5a52c3bb018972a5801acaaba63ef3f'
LOG_POLICY = CRASH_REPORT_POLICY | {'scope': LOG_SCOPE}

CONTEXT_FLAG = '--ios26-cpu-log-context-trial'
CONTEXT_NONCE = 'd567f31361d346ed95af71053a676a23'
CONTEXT_BASE = STAGE / f'k80-cpu-log-context26-{CONTEXT_NONCE}' / 'root-trial-log-context'
CONTEXT_SCOPE = 'single-K80-ios26-CPU-log-context-300s-d567f313'
CONTEXT_PACKAGE_SHA = '95b79b57d5458fedb36942459d75526f9391413c065f176333c4914751506f76'
CONTEXT_POLICY = CRASH_REPORT_POLICY | {'scope': CONTEXT_SCOPE}

OSANALYTICS_FLAG = '--ios26-cpu-osanalytics-trial'
OSANALYTICS_NONCE = '471dfed262904668adec5471f5ad3572'
OSANALYTICS_BASE = STAGE / f'k80-cpu-osanalytics-boot26-{OSANALYTICS_NONCE}' / 'root-trial-osanalytics'
OSANALYTICS_SCOPE = 'single-K80-ios26-CPU-osanalytics-300s-471dfed2'
OSANALYTICS_PACKAGE_SHA = 'ba41858ed0dd34622016ffa3a72d485b3ea73f08ca666ea5c9062b2ccb4eae52'
OSANALYTICS_ROOT_SHA = '515fa6c6a231b50556dce7353197f7c908225da8ff51f3d13eec15ee1f7daad5'
OSANALYTICS_INSTALL_SCOPE = 'K80-persistent-iOS26-CPU-osanalytics-delta-471dfed2'
OSANALYTICS_POLICY = CRASH_REPORT_POLICY | {'scope': OSANALYTICS_SCOPE}

OSFILES_FLAG = '--ios26-cpu-osanalytics-files-trial'
OSFILES_NONCE = '2d336139b9b14db5aa3958508cd21429'
OSFILES_BASE = STAGE / f'k80-cpu-osfiles26-{OSFILES_NONCE}' / 'root-trial-osfiles'
OSFILES_SCOPE = 'single-K80-ios26-CPU-osanalytics-files-300s-2d336139'
OSFILES_PACKAGE_SHA = 'a18d7ea949c9a5ee0c15456308dfa519da28eb4a0e6a76d4d2a7c427f486e6e1'
OSFILES_POLICY = CRASH_REPORT_POLICY | {'scope': OSFILES_SCOPE}

SBREASON_FLAG = '--ios26-cpu-springboard-reason-trial'
SBREASON_NONCE = '47ddefb127d943e68e9324b249164bc8'
SBREASON_BASE = STAGE / f'k80-cpu-sbreason26-{SBREASON_NONCE}' / 'root-trial-sbreason'
SBREASON_SCOPE = 'single-K80-ios26-CPU-SpringBoard-reason-300s-47ddefb1'
SBREASON_PACKAGE_SHA = '705ec07ea1edbe1b0f1da61b04439991efb925f6040d8eee562c3e32f74d9041'
SBREASON_POLICY = CRASH_REPORT_POLICY | {'scope': SBREASON_SCOPE}

STDIO_FLAG = '--ios26-cpu-springboard-stdio-trial'
STDIO_NONCE = 'ba26b11293c1405784a075d076f657a6'
STDIO_BASE = STAGE / f'k80-cpu-sbstdio26-{STDIO_NONCE}' / 'root-trial-sbstdio'
STDIO_SCOPE = 'single-K80-ios26-CPU-SpringBoard-stdio-300s-ba26b112'
STDIO_PACKAGE_SHA = 'a74a9f2265cd528036217f3a064fe6261db21301a69c2680a412a09a69b00152'
STDIO_POLICY = CRASH_REPORT_POLICY | {'scope': STDIO_SCOPE}

SERVICE_FLAG = '--ios26-cpu-service-policy-trial'
SERVICE_NONCE = '204e22356d9640b894aa89694272df5a'
SERVICE_BASE = STAGE / f'k80-cpu-service-boot26-{SERVICE_NONCE}' / 'root-trial-service-policy'
SERVICE_SCOPE = 'single-K80-ios26-CPU-service-policy-300s-204e2235'
SERVICE_PACKAGE_SHA = 'f76742dbaebb767d17436245247e75329c005d4ff031434df027da46f437cd61'
SERVICE_ROOT_SHA = '64c099f673837efff9b14d76d23785da072022573b7efd7206771b04bc48f6c2'
SERVICE_INSTALL_SCOPE = 'K80-persistent-iOS26-CPU-service-policy-delta-75fd3a70'
SERVICE_POLICY = CRASH_REPORT_POLICY | {'scope': SERVICE_SCOPE}

PLATFORM_FIX_FLAG = '--ios26-cpu-platform-identity-trial'
PLATFORM_FIX_NONCE = 'b45096798bcf46acaf4f1ce3290c0b16'
PLATFORM_FIX_BASE = STAGE / f'k80-cpu-platform-fix26-{PLATFORM_FIX_NONCE}' / 'root-trial-platform-identity'
PLATFORM_FIX_SCOPE = 'single-K80-ios26-CPU-platform-identity-300s-b4509679'
PLATFORM_FIX_PACKAGE_SHA = '094cd67e7dafe70aa17c96a2beed8754469473a0454b670fce211ec9d492280c'
PLATFORM_FIX_POLICY = CRASH_REPORT_POLICY | {'scope': PLATFORM_FIX_SCOPE}

WORK_INTERVAL_FLAG = '--ios26-cpu-work-interval-trial'
WORK_INTERVAL_NONCE = 'c1d6a802b6df438c8d08414a7bbe125d'
WORK_INTERVAL_BASE = STAGE / f'k80-cpu-work-interval26-{WORK_INTERVAL_NONCE}' / 'root-trial-work-interval'
WORK_INTERVAL_SCOPE = 'single-K80-ios26-CPU-work-interval-300s-c1d6a802'
WORK_INTERVAL_PACKAGE_SHA = '72241217fc2d52d3fe119bf561136a32fc7db98b0230fe32a0b087dee35147b8'
WORK_INTERVAL_POLICY = CRASH_REPORT_POLICY | {'scope': WORK_INTERVAL_SCOPE}

DISPLAY_SCALE_FLAG = '--ios26-cpu-display-scale-trial'
DISPLAY_SCALE_NONCE = '3208dc682a1742f19c78def3bea3ea52'
DISPLAY_SCALE_BASE = STAGE / f'k80-cpu-display-scale26-{DISPLAY_SCALE_NONCE}' / 'root-trial-display-scale'
DISPLAY_SCALE_SCOPE = 'single-K80-ios26-CPU-display-scale-300s-3208dc68'
DISPLAY_SCALE_PACKAGE_SHA = '3c3bf82eb626c66d33cf5067282b80d2ffe086562a3f317a754f053a0a3502a1'
DISPLAY_SCALE_POLICY = CRASH_REPORT_POLICY | {'scope': DISPLAY_SCALE_SCOPE}

CONTINUITY_FLAG = '--ios26-cpu-continuity-trial'
CONTINUITY_NONCE = 'dc884f96563040459656a356903bc0c8'
CONTINUITY_BASE = STAGE / f'k80-cpu-continuity26-{CONTINUITY_NONCE}' / 'root-trial-cpu-continuity'
CONTINUITY_SCOPE = 'single-K80-ios26-CPU-continuity-300s-dc884f96'
CONTINUITY_PACKAGE_SHA = '34f2e2fbe07373800c2bf33911cff11fcd4a26fa700a3475329ece35912e38eb'
CONTINUITY_POLICY = DISPLAY_SCALE_POLICY | {'scope': CONTINUITY_SCOPE, 'userland_snapshot_seconds': 150}

POSTERBOARD_FLAG = '--ios26-cpu-posterboard-trial'
POSTERBOARD_NONCE = '6b4d623251e747fa9ad2c540f625f109'
POSTERBOARD_BASE = STAGE / f'k80-cpu-posterboard26-{POSTERBOARD_NONCE}' / 'root-trial-cpu-posterboard'
POSTERBOARD_SCOPE = 'single-K80-ios26-CPU-posterboard-300s-6b4d6232'
POSTERBOARD_PACKAGE_SHA = 'cb417d6e58e002b7ef4fc3155af001fdfa3619eb97f48b3aa8241b3f141795b5'
POSTERBOARD_POLICY = CONTINUITY_POLICY | {'scope': POSTERBOARD_SCOPE}

POSTERBOARD_REPLY_FLAG = '--ios26-cpu-posterboard-reply-trial'
POSTERBOARD_REPLY_NONCE = '6fc92019c20a417ab4003316bd6d54a0'
POSTERBOARD_REPLY_BASE = STAGE / f'k80-cpu-posterboard-reply26-{POSTERBOARD_REPLY_NONCE}' / 'root-trial-cpu-posterboard-reply'
POSTERBOARD_REPLY_SCOPE = 'single-K80-ios26-CPU-posterboard-reply-300s-6fc92019'
POSTERBOARD_REPLY_PACKAGE_SHA = '11c588e1b4de953be57a31341cb0fdf9fc208b1593e1e8c960270c073c4bed35'
POSTERBOARD_REPLY_ROOT_SHA = 'c6f0709514294393996f9e50394cb35fa82516ca7663727e21358ca90721bc50'
POSTERBOARD_REPLY_INSTALL_SCOPE = 'K80-persistent-iOS26-CPU-posterboard-reply-archive-b85cf512'
POSTERBOARD_REPLY_POLICY = POSTERBOARD_POLICY | {'scope': POSTERBOARD_REPLY_SCOPE}

POSTERBOARD_OUTPUT_FLAG = '--ios26-cpu-posterboard-output-trial'
POSTERBOARD_OUTPUT_NONCE = '0aef6c0db75f44d1b987ad46a5cc893c'
POSTERBOARD_OUTPUT_BASE = STAGE / f'k80-cpu-posterboard-output26-{POSTERBOARD_OUTPUT_NONCE}' / 'root-trial-cpu-posterboard-output'
POSTERBOARD_OUTPUT_SCOPE = 'single-K80-ios26-CPU-posterboard-output-300s-0aef6c0d'
POSTERBOARD_OUTPUT_PACKAGE_SHA = 'e7647a2792e955c1f97e90ef2234c5275c0395c18ac43ccd54c2f20746b2ae86'
POSTERBOARD_OUTPUT_POLICY = POSTERBOARD_POLICY | {'scope': POSTERBOARD_OUTPUT_SCOPE}

POSTERBOARD_TAIL_FLAG = '--ios26-cpu-posterboard-tail-trial'
POSTERBOARD_TAIL_NONCE = 'f2193a0cc6f64e53a1d3b9c7d3d61d83'
POSTERBOARD_TAIL_BASE = STAGE / f'k80-cpu-posterboard-tail26-{POSTERBOARD_TAIL_NONCE}' / 'root-trial-cpu-posterboard-tail'
POSTERBOARD_TAIL_SCOPE = 'single-K80-ios26-CPU-posterboard-tail-300s-f2193a0c'
POSTERBOARD_TAIL_PACKAGE_SHA = '9723ffd181c6b38e15e1f8c6fb976180922f17996f72731df68e82226c952945'
POSTERBOARD_TAIL_POLICY = POSTERBOARD_POLICY | {'scope': POSTERBOARD_TAIL_SCOPE}

POSTERBOARD_ENTRY_FLAG = '--ios26-cpu-posterboard-entry-trial'
POSTERBOARD_ENTRY_NONCE = '52a24c78107e4ed4aaa4679c1ae056cb'
POSTERBOARD_ENTRY_BASE = STAGE / f'k80-cpu-posterboard-entry26-{POSTERBOARD_ENTRY_NONCE}' / 'root-trial-cpu-posterboard-entry'
POSTERBOARD_ENTRY_SCOPE = 'single-K80-ios26-CPU-posterboard-entry-300s-52a24c78'
POSTERBOARD_ENTRY_PACKAGE_SHA = '2fc25e33ddf83d4635739c700a49ba84cf0dbfb55e9ecc4cf76da51d0873ce59'
POSTERBOARD_ENTRY_ROOT_SHA = '7850439114768d67395f43f2bbcaa0e15b14bd526cf05bbf7107c24fe04345bf'
POSTERBOARD_ENTRY_INSTALL_SCOPE = 'K80-persistent-iOS26-CPU-posterboard-entry-52a24c78'
POSTERBOARD_ENTRY_POLICY = POSTERBOARD_POLICY | {'scope': POSTERBOARD_ENTRY_SCOPE}

POSTERBOARD_BITS_FLAG = '--ios26-cpu-posterboard-bits-trial'
POSTERBOARD_BITS_NONCE = '005f4564aaf9425a8edd5c15faa4f71c'
POSTERBOARD_BITS_BASE = STAGE / f'k80-cpu-posterboard-bits26-{POSTERBOARD_BITS_NONCE}' / 'root-trial-cpu-posterboard-bits'
POSTERBOARD_BITS_SCOPE = 'single-K80-ios26-CPU-posterboard-bits-300s-005f4564'
POSTERBOARD_BITS_PACKAGE_SHA = '0fc513f3b50099bf17d9d091ae0480968e898545a0ba614af37c4337ae97acdc'
POSTERBOARD_BITS_POLICY = POSTERBOARD_POLICY | {'scope': POSTERBOARD_BITS_SCOPE}

POSTERBOARD_WIDE_FLAG = '--ios26-cpu-posterboard-wide-trial'
POSTERBOARD_WIDE_NONCE = 'fa7eba4232bd4fbda567a68587d83c7f'
POSTERBOARD_WIDE_BASE = STAGE / f'k80-cpu-posterboard-wide-safe26-{POSTERBOARD_WIDE_NONCE}' / 'root-trial-cpu-posterboard-wide'
POSTERBOARD_WIDE_SCOPE = 'single-K80-ios26-CPU-posterboard-wide-300s-fa7eba42'
POSTERBOARD_WIDE_PACKAGE_SHA = '71eb7aa54662f323fbdca29001a9185e5dd65a69ada35e5db37fc632e3d6a72a'
POSTERBOARD_WIDE_POLICY = POSTERBOARD_POLICY | {'scope': POSTERBOARD_WIDE_SCOPE}

POSTERBOARD_RETURN_FLAG = '--ios26-cpu-posterboard-return-trial'
POSTERBOARD_RETURN_NONCE = '2920148e62df4a96a28e5d2a9b549979'
POSTERBOARD_RETURN_BASE = STAGE / f'k80-cpu-posterboard-return26-{POSTERBOARD_RETURN_NONCE}' / 'root-trial-cpu-posterboard-return'
POSTERBOARD_RETURN_SCOPE = 'single-K80-ios26-CPU-posterboard-return-300s-2920148e'
POSTERBOARD_RETURN_PACKAGE_SHA = '3a7088756cba28cf853839b2bf49c618e1f8da6adf5d1095c51169cc7a765c31'
POSTERBOARD_RETURN_ROOT_SHA = 'aba734228fedd611cb50af0994074f0ddaf5fc19c3d3518e637e1742cc1650f7'
POSTERBOARD_RETURN_INSTALL_SCOPE = 'K80-persistent-iOS26-CPU-posterboard-return-2920148e'
POSTERBOARD_RETURN_POLICY = POSTERBOARD_POLICY | {'scope': POSTERBOARD_RETURN_SCOPE}
POSTERBOARD_WAIT_FLAG = '--ios26-cpu-posterboard-wait-trial'
POSTERBOARD_WAIT_NONCE = '076f6f77a3984ded9b60ea49430bbf15'
POSTERBOARD_WAIT_BASE = STAGE / f'k80-cpu-posterboard-wait-26-{POSTERBOARD_WAIT_NONCE}' / 'root-trial-cpu-posterboard-wait'
POSTERBOARD_WAIT_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-posterboard-wait-300s-076f6f77'}
POSTERBOARD_PASSIVE_FLAG = '--ios26-cpu-posterboard-passive-trial'
POSTERBOARD_PASSIVE_NONCE = 'cc9fbb3b86364db19e8f2ec90256040b'
POSTERBOARD_PASSIVE_BASE = STAGE / f'k80-cpu-posterboard-passive26-{POSTERBOARD_PASSIVE_NONCE}' / 'root-trial-cpu-posterboard-passive'
POSTERBOARD_PASSIVE_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-posterboard-passive-300s-cc9fbb3b'}
POSTERBOARD_PASSIVE_ROOT_SHA = '227ba639a3f765fce15b1bb6f08ccf53f36872fd0a95bba7bb778f067c34e32e'
POSTERBOARD_PASSIVE_INSTALL_SCOPE = 'K80-persistent-iOS26-CPU-posterboard-passive-cc9fbb3b'
SB_WALLPAPER_CONTROL_FLAG = '--ios26-cpu-sb-wallpaper-control-trial'
SB_WALLPAPER_CONTROL_NONCE = 'b90498b584734302999863daafb85075'
SB_WALLPAPER_CONTROL_BASE = STAGE / f'k80-cpu-sb-wallpaper-control26-{SB_WALLPAPER_CONTROL_NONCE}' / 'root-trial-cpu-sb-wallpaper-control'
SB_WALLPAPER_CONTROL_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-sb-wallpaper-control-300s-b90498b5'}
SB_BOOTARGS_FLAG = '--ios26-cpu-sb-bootargs-trial'
SB_BOOTARGS_NONCE = 'a48eb55daa16476fa8a4feea324e9122'
SB_BOOTARGS_BASE = STAGE / f'k80-cpu-sb-bootargs26-{SB_BOOTARGS_NONCE}' / 'root-trial-cpu-sb-bootargs'
SB_BOOTARGS_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-sb-bootargs-300s-a48eb55d'}
UI_DISPLAY_WAIT_FLAG = '--ios26-cpu-ui-display-wait-trial'
UI_DISPLAY_WAIT_NONCE = 'a8a0024426064618b83f7124e3fb0a06'
UI_DISPLAY_WAIT_BASE = STAGE / f'k80-cpu-ui-display-wait26-{UI_DISPLAY_WAIT_NONCE}' / 'root-trial-cpu-ui-display-wait'
UI_DISPLAY_WAIT_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-ui-display-wait-300s-a8a00244'}
SB_ULOCK_FLAG = '--ios26-cpu-sb-ulock-trial'
SB_ULOCK_NONCE = 'd7083d719970431a96bb9af745cfebf8'
SB_ULOCK_BASE = STAGE / f'k80-cpu-sb-ulock26-{SB_ULOCK_NONCE}' / 'root-trial-cpu-sb-ulock'
SB_ULOCK_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-sb-ulock-300s-d7083d71'}
SB_OWNER_FLAG = '--ios26-cpu-sb-owner-trial'
SB_OWNER_NONCE = 'fdf5d4531bff44d2804dc5eb3385c88a'
SB_OWNER_BASE = STAGE / f'k80-cpu-sb-owner26-{SB_OWNER_NONCE}' / 'root-trial-cpu-sb-owner'
SB_OWNER_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-sb-owner-300s-fdf5d453'}
SB_PEER_FLAG = '--ios26-cpu-sb-peer-trial'
SB_PEER_NONCE = '048883009e194aa38440ac58bb8f0725'
SB_PEER_BASE = STAGE / f'k80-cpu-sb-peer26-{SB_PEER_NONCE}' / 'root-trial-cpu-sb-peer'
SB_PEER_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-sb-peer-300s-04888300'}
LSD_VFS_FLAG = '--ios26-cpu-lsd-vfs-trial'
LSD_VFS_NONCE = 'cbb23711582b42b3ac52928bb71dcef3'
LSD_VFS_BASE = STAGE / f'k80-cpu-lsd-vfs26-{LSD_VFS_NONCE}' / 'root-trial-cpu-lsd-vfs'
LSD_VFS_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-lsd-vfs-300s-cbb23711'}
LSD_COPYLEN_FLAG = '--ios26-cpu-lsd-vfs-copylen-trial'
LSD_COPYLEN_NONCE = 'ed2b48d33f94481d95966074a9713cb8'
LSD_COPYLEN_BASE = STAGE / f'k80-cpu-lsd-vfs26-{LSD_COPYLEN_NONCE}' / 'root-trial-cpu-lsd-vfs-copylen'
LSD_COPYLEN_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-lsd-vfs-copylen-300s-ed2b48d3'}
LSD_BUDGET_FLAG = '--ios26-cpu-lsd-vfs-budget-trial'
LSD_BUDGET_NONCE = '998f15fdfd9148f190f2d9b2a041e995'
LSD_BUDGET_BASE = STAGE / f'k80-cpu-lsd-vfs26-{LSD_BUDGET_NONCE}' / 'root-trial-cpu-lsd-vfs-budget'
LSD_BUDGET_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-lsd-vfs-budget-300s-998f15fd'}
LSD_PREFIX_FLAG = '--ios26-cpu-lsd-vfs-prefix-trial'
LSD_PREFIX_NONCE = '56812d907cb74b76b18555be61763ef2'
LSD_PREFIX_BASE = STAGE / f'k80-cpu-lsd-vfs26-{LSD_PREFIX_NONCE}' / 'root-trial-cpu-lsd-vfs-prefix'
LSD_PREFIX_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-lsd-vfs-prefix-300s-56812d90'}
LSD_SUFFIX_FLAG = '--ios26-cpu-lsd-vfs-suffix-trial'
LSD_SUFFIX_NONCE = 'a1c0e5b7d4f64c0a9e2b8d3c6f1a0e91'
LSD_SUFFIX_BASE = STAGE / f'k80-cpu-lsd-vfs26-{LSD_SUFFIX_NONCE}' / 'root-trial-cpu-lsd-vfs-suffix'
LSD_SUFFIX_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-lsd-vfs-suffix-300s-a1c0e5b7'}
NETWORK_IDENTITY_FLAG = '--ios26-cpu-network-identity-trial'
NETWORK_IDENTITY_NONCE = '0035ea43c05041e38f21c88ff8c6e1a9'
NETWORK_IDENTITY_BASE = STAGE / f'k80-cpu-mac-identity26-{NETWORK_IDENTITY_NONCE}' / 'root-trial-cpu-mac-identity'
NETWORK_IDENTITY_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-network-identity-300s-0035ea43'}
LONG_WINDOW_FLAG = '--ios26-cpu-long-window-trial'
LONG_WINDOW_NONCE = '6412899fa15647fab94a6530177d180f'
LONG_WINDOW_BASE = STAGE / f'k80-cpu-long-window26-{LONG_WINDOW_NONCE}' / 'root-trial-cpu-long-window'
LONG_WINDOW_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-long-window-1080s-6412899f', 'trial_seconds': 1080,
    'timeout_seconds': 1500, 'userland_snapshot_seconds': 900}
REPLY_DESTINATION_FLAG = '--ios26-cpu-reply-destination-trial'
REPLY_DESTINATION_NONCE = 'fe04d3023ec7420fba44e905a6e5c815'
REPLY_DESTINATION_BASE = STAGE / f'k80-cpu-reply-destination26-{REPLY_DESTINATION_NONCE}' / 'root-trial-cpu-reply-destination'
REPLY_DESTINATION_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-reply-destination-300s-fe04d302'}
REPLY_HOLDER_FLAG = '--ios26-cpu-reply-holder-trial'
REPLY_HOLDER_NONCE = 'babbbe2bb2af4b318f09b13049d760a6'
REPLY_HOLDER_BASE = STAGE / f'k80-cpu-reply-holder26-{REPLY_HOLDER_NONCE}' / 'root-trial-cpu-reply-holder'
REPLY_HOLDER_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-reply-holder-300s-babbbe2b'}
HOLDER_NAME_FLAG = '--ios26-cpu-holder-name-trial'
HOLDER_NAME_NONCE = '056afd15056746e8878c08f90daf35ad'
HOLDER_NAME_BASE = STAGE / f'k80-cpu-holder-name26-{HOLDER_NAME_NONCE}' / 'root-trial-cpu-holder-name'
HOLDER_NAME_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-holder-name-300s-056afd15'}
SERVICE_NAME_FLAG = '--ios26-cpu-service-name-trial'
SERVICE_NAME_NONCE = '18a1c0e6ca834f38a1dc364094c73857'
SERVICE_NAME_BASE = STAGE / f'k80-cpu-service-name26-{SERVICE_NAME_NONCE}' / 'root-trial-cpu-service-name'
SERVICE_NAME_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-service-name-300s-18a1c0e6'}
KEYSTORE_FLAG = '--ios26-cpu-keystore-trial'
KEYSTORE_NONCE = 'b6440b7e1376411db7adfa9a68bdf345'
KEYSTORE_BASE = STAGE / f'k80-cpu-keystore26-{KEYSTORE_NONCE}' / 'root-trial-cpu-keystore'
KEYSTORE_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-keystore-300s-b6440b7e'}
KEYSTORE_RERUN_FLAG = '--ios26-cpu-keystore-rerun-trial'
KEYSTORE_RERUN_NONCE = 'b6440b7e1376411db7adfa9a68bdf345'
KEYSTORE_RERUN_BASE = STAGE / f'k80-cpu-keystore26-{KEYSTORE_RERUN_NONCE}' / 'root-trial-cpu-keystore-rerun'
KEYSTORE_RERUN_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-keystore-rerun-300s-b6440b7e'}
KEYSTORE_RETAG_FLAG = '--ios26-cpu-keystore-retag-trial'
KEYSTORE_RETAG_NONCE = 'b0da41e98417481f979a24106c21f3bc'
KEYSTORE_RETAG_BASE = STAGE / f'k80-cpu-keystore-retag26-{KEYSTORE_RETAG_NONCE}' / 'root-trial-cpu-keystore-retag'
KEYSTORE_RETAG_POLICY = POSTERBOARD_POLICY | {'scope': 'single-K80-ios26-CPU-keystore-retag-300s-b0da41e9'}
POSTERBOARD_LONG_WAIT_FLAGS = (POSTERBOARD_WAIT_FLAG, POSTERBOARD_PASSIVE_FLAG, SB_WALLPAPER_CONTROL_FLAG, SB_BOOTARGS_FLAG, UI_DISPLAY_WAIT_FLAG, SB_ULOCK_FLAG, SB_OWNER_FLAG, SB_PEER_FLAG, LSD_VFS_FLAG, LSD_COPYLEN_FLAG, LSD_BUDGET_FLAG, LSD_PREFIX_FLAG, LSD_SUFFIX_FLAG, NETWORK_IDENTITY_FLAG, LONG_WINDOW_FLAG, REPLY_DESTINATION_FLAG, REPLY_HOLDER_FLAG, HOLDER_NAME_FLAG, SERVICE_NAME_FLAG, KEYSTORE_FLAG, KEYSTORE_RERUN_FLAG, KEYSTORE_RETAG_FLAG)
POSTERBOARD_WIDE_RECORD_FLAGS = (POSTERBOARD_WIDE_FLAG, POSTERBOARD_RETURN_FLAG, *POSTERBOARD_LONG_WAIT_FLAGS)

CURRENT_ROOT_FLAGS = (CONTROL_FLAG, TOUCH_USERLAND_FLAG, CPU_NO_SAMPLING_FLAG, SB_LIFECYCLE_FLAG, SB_STDERR_FLAG, CRASH_REPORT_FLAG, DELIVERY_FLAG, FIRST_DELIVERY_FLAG, CORPSE_FLAG, FILES_FLAG, TWO_DIR_REPORT_FLAG, PATH_FLAG, LOG_FLAG, CONTEXT_FLAG, OSANALYTICS_FLAG, OSFILES_FLAG, SBREASON_FLAG, STDIO_FLAG, SERVICE_FLAG, PLATFORM_FIX_FLAG, WORK_INTERVAL_FLAG, DISPLAY_SCALE_FLAG, CONTINUITY_FLAG, POSTERBOARD_FLAG, POSTERBOARD_REPLY_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS, POSTERBOARD_OUTPUT_FLAG, *ATTENDED_FLAGS)
TRIAL_INPUTS = {
    KEYSTORE_RETAG_FLAG: (KEYSTORE_RETAG_BASE, KEYSTORE_RETAG_NONCE, KEYSTORE_RETAG_POLICY,
                    '29082504ffdc753ee2a1fd25de65a8604b91b67776c69ae7caf4041cd67156d7', 'rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 zorn26_trial_seconds=300 zorn26_userland_progress=1 zorn26_cpu_presenter=1 zorn26_software_accelerator=1 sample=0 sb_wallpaper=0'),
    KEYSTORE_RERUN_FLAG: (KEYSTORE_RERUN_BASE, KEYSTORE_RERUN_NONCE, KEYSTORE_RERUN_POLICY,
                    '366a49d060906f9e93ab06ec00e1c69d4a1c2b72154443c551ae700d8677754d', 'rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 zorn26_trial_seconds=300 zorn26_userland_progress=1 zorn26_cpu_presenter=1 zorn26_software_accelerator=1 sample=0 sb_wallpaper=0'),
    KEYSTORE_FLAG: (KEYSTORE_BASE, KEYSTORE_NONCE, KEYSTORE_POLICY,
                    '366a49d060906f9e93ab06ec00e1c69d4a1c2b72154443c551ae700d8677754d', 'rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 zorn26_trial_seconds=300 zorn26_userland_progress=1 zorn26_cpu_presenter=1 zorn26_software_accelerator=1 sample=0 sb_wallpaper=0'),
    SERVICE_NAME_FLAG: (SERVICE_NAME_BASE, SERVICE_NAME_NONCE, SERVICE_NAME_POLICY,
                    '0273e04bb008fb14d0ee596450d30d9b05b1c326215630bed0f24f04cfe4c528', 'rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 zorn26_trial_seconds=300 zorn26_userland_progress=1 zorn26_cpu_presenter=1 zorn26_software_accelerator=1 sample=0 sb_wallpaper=0'),
    HOLDER_NAME_FLAG: (HOLDER_NAME_BASE, HOLDER_NAME_NONCE, HOLDER_NAME_POLICY,
                    '1169a07c262e7676126d02cd4d9c4115aca8f48e963c44d5e905d9041a001dc2', 'rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 zorn26_trial_seconds=300 zorn26_userland_progress=1 zorn26_cpu_presenter=1 zorn26_software_accelerator=1 sample=0 sb_wallpaper=0'),
    REPLY_HOLDER_FLAG: (REPLY_HOLDER_BASE, REPLY_HOLDER_NONCE, REPLY_HOLDER_POLICY,
                    '574f562b80007fdecba891cb7a3619577f2bf3cfaf5788c560c53b120efb0064', 'rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 zorn26_trial_seconds=300 zorn26_userland_progress=1 zorn26_cpu_presenter=1 zorn26_software_accelerator=1 sample=0 sb_wallpaper=0'),
    REPLY_DESTINATION_FLAG: (REPLY_DESTINATION_BASE, REPLY_DESTINATION_NONCE, REPLY_DESTINATION_POLICY,
                    '89c9ee3c62b74f1c8a393bc24592dd553eb8d995e84a809a9b415c1782521410', 'rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 zorn26_trial_seconds=300 zorn26_userland_progress=1 zorn26_cpu_presenter=1 zorn26_software_accelerator=1 sample=0 sb_wallpaper=0'),
    LONG_WINDOW_FLAG: (LONG_WINDOW_BASE, LONG_WINDOW_NONCE, LONG_WINDOW_POLICY,
                    'e7785c3029ca0691048d5c61234b651680a24a3f2917949fde7c9387c7fceb9b', 'rd=md0 -v keepsyms=1 houji_native_root=1 zorn26_root=1 zorn26_installed_root_trial=1 zorn_wdt=1 zorn26_prearmed_recovery=1 zorn26_trial_seconds=1080 zorn26_userland_progress=1 zorn26_cpu_presenter=1 zorn26_software_accelerator=1 sample=0 sb_wallpaper=0'),
    NETWORK_IDENTITY_FLAG: (NETWORK_IDENTITY_BASE, NETWORK_IDENTITY_NONCE, NETWORK_IDENTITY_POLICY,
                    '7e94ea72dc7e4e0edaef0296792c1327e0a7d041076285b2ce21e1c470b5edd1', SOFTWARE_ACCEL_ARGS + ' sample=0 sb_wallpaper=0'),
    LSD_SUFFIX_FLAG: (LSD_SUFFIX_BASE, LSD_SUFFIX_NONCE, LSD_SUFFIX_POLICY,
                    '7af4ae5e82f19a2e23bf21a70f0af59d68c6ec2feb4ffc489b6c0dc0abd7cf83', SOFTWARE_ACCEL_ARGS + ' sample=0 sb_wallpaper=0'),
    LSD_PREFIX_FLAG: (LSD_PREFIX_BASE, LSD_PREFIX_NONCE, LSD_PREFIX_POLICY,
                    '25cb6fc87e462a5d4cff333104a866dfd72fc6e9ac62ba7c918c0913767f4138', SOFTWARE_ACCEL_ARGS + ' sample=0 sb_wallpaper=0'),
    LSD_BUDGET_FLAG: (LSD_BUDGET_BASE, LSD_BUDGET_NONCE, LSD_BUDGET_POLICY,
                    '292be11dbf3efb3364320f2a32c26cb5e0f603d207207af364fe7035487b5cb4', SOFTWARE_ACCEL_ARGS + ' sample=0 sb_wallpaper=0'),
    LSD_COPYLEN_FLAG: (LSD_COPYLEN_BASE, LSD_COPYLEN_NONCE, LSD_COPYLEN_POLICY,
                    '882437280bd73b5d04bf6db09c40b16c65514759b3c3dfabc814a05d7206ce7b', SOFTWARE_ACCEL_ARGS + ' sample=0 sb_wallpaper=0'),
    LSD_VFS_FLAG: (LSD_VFS_BASE, LSD_VFS_NONCE, LSD_VFS_POLICY,
                    '2452239b8b6470e8a8182c92b9e865cd40e8eb2f2d94ab66639bc12e4a2d31c8', SOFTWARE_ACCEL_ARGS + ' sample=0 sb_wallpaper=0'),
    SB_PEER_FLAG: (SB_PEER_BASE, SB_PEER_NONCE, SB_PEER_POLICY,
                    '6dfade37d603a485be3828c22317bcd55d2186df1018d43a7d990fb8204936eb', SOFTWARE_ACCEL_ARGS + ' sample=0 sb_wallpaper=0'),
    SB_OWNER_FLAG: (SB_OWNER_BASE, SB_OWNER_NONCE, SB_OWNER_POLICY,
                    '40cdd0b984d2d577bdb73ca0d0c4c66e8cb3cc131923d4ee4a70c4108a51f70d', SOFTWARE_ACCEL_ARGS + ' sample=0 sb_wallpaper=0'),
    SB_ULOCK_FLAG: (SB_ULOCK_BASE, SB_ULOCK_NONCE, SB_ULOCK_POLICY,
                    '6ed746cde439dd6c1a028d55f0f70d2df2951c0b81c8fffa3727972973eccd58', SOFTWARE_ACCEL_ARGS + ' sample=0 sb_wallpaper=0'),
    UI_DISPLAY_WAIT_FLAG: (UI_DISPLAY_WAIT_BASE, UI_DISPLAY_WAIT_NONCE, UI_DISPLAY_WAIT_POLICY,
                           'b7c1e1581cbc720fe936a75e1e44c57cbcc98017c21431517c680d0041e323e1', SOFTWARE_ACCEL_ARGS + ' sample=0 sb_wallpaper=0'),
    SB_BOOTARGS_FLAG: (SB_BOOTARGS_BASE, SB_BOOTARGS_NONCE, SB_BOOTARGS_POLICY,
                       '5c38999721e66bf749f60dbddf989398f36f0e5636f582ee1298319175d50b71', SOFTWARE_ACCEL_ARGS + ' sample=0 sb_wallpaper=0'),
    SB_WALLPAPER_CONTROL_FLAG: (SB_WALLPAPER_CONTROL_BASE, SB_WALLPAPER_CONTROL_NONCE, SB_WALLPAPER_CONTROL_POLICY,
                                '1dc88b59c21c113d2bf8457e11c915bb3dc2bfb4c45fb6551030a199a50bce8a', SOFTWARE_ACCEL_ARGS + ' sample=0 sb_wallpaper=0'),
    POSTERBOARD_PASSIVE_FLAG: (POSTERBOARD_PASSIVE_BASE, POSTERBOARD_PASSIVE_NONCE, POSTERBOARD_PASSIVE_POLICY,
                              '056d2375c5efc7889fcf7327a0b2487d4619d91ce012103f160e64deefccf010', SOFTWARE_ACCEL_ARGS + ' sample=0'),
    POSTERBOARD_WAIT_FLAG: (POSTERBOARD_WAIT_BASE, POSTERBOARD_WAIT_NONCE, POSTERBOARD_WAIT_POLICY,
                           'ddb5318ba59f6a8c8fa382439ac1eaa0e1f2a026bec3dd6c6f814d0a6d75909e', SOFTWARE_ACCEL_ARGS + ' sample=0'),
    POSTERBOARD_RETURN_FLAG: (POSTERBOARD_RETURN_BASE, POSTERBOARD_RETURN_NONCE, POSTERBOARD_RETURN_POLICY,
                              POSTERBOARD_RETURN_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    POSTERBOARD_WIDE_FLAG: (POSTERBOARD_WIDE_BASE, POSTERBOARD_WIDE_NONCE, POSTERBOARD_WIDE_POLICY,
                            POSTERBOARD_WIDE_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    POSTERBOARD_BITS_FLAG: (POSTERBOARD_BITS_BASE, POSTERBOARD_BITS_NONCE, POSTERBOARD_BITS_POLICY,
                            POSTERBOARD_BITS_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    POSTERBOARD_ENTRY_FLAG: (POSTERBOARD_ENTRY_BASE, POSTERBOARD_ENTRY_NONCE, POSTERBOARD_ENTRY_POLICY,
                             POSTERBOARD_ENTRY_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    POSTERBOARD_TAIL_FLAG: (POSTERBOARD_TAIL_BASE, POSTERBOARD_TAIL_NONCE, POSTERBOARD_TAIL_POLICY,
                              POSTERBOARD_TAIL_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    POSTERBOARD_OUTPUT_FLAG: (POSTERBOARD_OUTPUT_BASE, POSTERBOARD_OUTPUT_NONCE, POSTERBOARD_OUTPUT_POLICY,
                              POSTERBOARD_OUTPUT_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    POSTERBOARD_REPLY_FLAG: (POSTERBOARD_REPLY_BASE, POSTERBOARD_REPLY_NONCE, POSTERBOARD_REPLY_POLICY,
                             POSTERBOARD_REPLY_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    POSTERBOARD_FLAG: (POSTERBOARD_BASE, POSTERBOARD_NONCE, POSTERBOARD_POLICY,
                       POSTERBOARD_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    CONTINUITY_FLAG: (CONTINUITY_BASE, CONTINUITY_NONCE, CONTINUITY_POLICY,
                      CONTINUITY_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    DISPLAY_SCALE_FLAG: (DISPLAY_SCALE_BASE, DISPLAY_SCALE_NONCE, DISPLAY_SCALE_POLICY,
                        DISPLAY_SCALE_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    WORK_INTERVAL_FLAG: (WORK_INTERVAL_BASE, WORK_INTERVAL_NONCE, WORK_INTERVAL_POLICY,
                        WORK_INTERVAL_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    PLATFORM_FIX_FLAG: (PLATFORM_FIX_BASE, PLATFORM_FIX_NONCE, PLATFORM_FIX_POLICY,
                        PLATFORM_FIX_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    SERVICE_FLAG: (SERVICE_BASE, SERVICE_NONCE, SERVICE_POLICY,
                   SERVICE_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    STDIO_FLAG: (STDIO_BASE, STDIO_NONCE, STDIO_POLICY,
                 STDIO_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    SBREASON_FLAG: (SBREASON_BASE, SBREASON_NONCE, SBREASON_POLICY,
                    SBREASON_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    OSFILES_FLAG: (OSFILES_BASE, OSFILES_NONCE, OSFILES_POLICY,
                   OSFILES_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    OSANALYTICS_FLAG: (OSANALYTICS_BASE, OSANALYTICS_NONCE, OSANALYTICS_POLICY,
                       OSANALYTICS_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    CONTEXT_FLAG: (CONTEXT_BASE, CONTEXT_NONCE, CONTEXT_POLICY, CONTEXT_PACKAGE_SHA,
                   SOFTWARE_ACCEL_ARGS + ' sample=0'),
    LOG_FLAG: (LOG_BASE, LOG_NONCE, LOG_POLICY, LOG_PACKAGE_SHA,
               SOFTWARE_ACCEL_ARGS + ' sample=0'),
    PATH_FLAG: (PATH_BASE, PATH_NONCE, PATH_POLICY, PATH_PACKAGE_SHA,
                SOFTWARE_ACCEL_ARGS + ' sample=0'),
    TWO_DIR_REPORT_FLAG: (TWO_DIR_REPORT_BASE, TWO_DIR_REPORT_NONCE, TWO_DIR_REPORT_POLICY,
                          TWO_DIR_REPORT_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    FILES_FLAG: (FILES_BASE, FILES_NONCE, FILES_POLICY,
                 FILES_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    CORPSE_FLAG: (CORPSE_BASE, CORPSE_NONCE, CORPSE_POLICY,
                  CORPSE_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    FIRST_DELIVERY_FLAG: (FIRST_DELIVERY_BASE, FIRST_DELIVERY_NONCE, FIRST_DELIVERY_POLICY,
                          FIRST_DELIVERY_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    DELIVERY_FLAG: (DELIVERY_BASE, DELIVERY_NONCE, DELIVERY_POLICY,
                    DELIVERY_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    CRASH_REPORT_FLAG: (CRASH_REPORT_BASE, CRASH_REPORT_NONCE, CRASH_REPORT_POLICY,
                        CRASH_REPORT_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    SB_STDERR_FLAG: (SB_STDERR_BASE, SB_STDERR_NONCE, SB_STDERR_POLICY,
                     SB_STDERR_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    SB_LIFECYCLE_FLAG: (SB_LIFECYCLE_BASE, SB_LIFECYCLE_NONCE, SB_LIFECYCLE_POLICY,
                         SB_LIFECYCLE_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    CPU_NO_SAMPLING_FLAG: (CPU_NO_SAMPLING_BASE, CPU_NO_SAMPLING_NONCE, CPU_NO_SAMPLING_POLICY,
                            CPU_NO_SAMPLING_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS + ' sample=0'),
    THREAD_CENSUS_FLAG: (THREAD_CENSUS_BASE, THREAD_CENSUS_NONCE, THREAD_CENSUS_POLICY,
                         THREAD_CENSUS_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS),
    FB_UNSUPPORTED_FLAG: (FB_UNSUPPORTED_BASE, FB_UNSUPPORTED_NONCE, FB_UNSUPPORTED_POLICY,
                          FB_UNSUPPORTED_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS),
    SURFACE_INIT_FLAG: (SURFACE_INIT_BASE, SURFACE_INIT_NONCE, SURFACE_INIT_POLICY,
                        SURFACE_INIT_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS),
    SURFACE_CREATE_FLAG: (SURFACE_CREATE_BASE, SURFACE_CREATE_NONCE, SURFACE_CREATE_POLICY,
                          SURFACE_CREATE_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS),
    SURFACE_RECORD_FLAG: (SURFACE_RECORD_BASE, SURFACE_RECORD_NONCE, SURFACE_RECORD_POLICY,
                          SURFACE_RECORD_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS),
    SURFACE_CLIENT_FLAG: (SURFACE_CLIENT_BASE, SURFACE_CLIENT_NONCE, SURFACE_CLIENT_POLICY,
                          SURFACE_CLIENT_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS),
    SURFACE_PLATFORM_FLAG: (SURFACE_PLATFORM_BASE, SURFACE_PLATFORM_NONCE, SURFACE_PLATFORM_POLICY,
                            SURFACE_PLATFORM_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS),
    IOSURFACE_ROOT_FLAG: (IOSURFACE_ROOT_BASE, IOSURFACE_ROOT_NONCE, IOSURFACE_ROOT_POLICY,
                          IOSURFACE_ROOT_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS),
    SOFTWARE_ACCEL_FLAG: (SOFTWARE_ACCEL_BASE, SOFTWARE_ACCEL_NONCE, SOFTWARE_ACCEL_POLICY,
                          SOFTWARE_ACCEL_PACKAGE_SHA, SOFTWARE_ACCEL_ARGS),
    DISPLAY_WAIT_FLAG: (DISPLAY_WAIT_BASE, DISPLAY_WAIT_NONCE, DISPLAY_WAIT_POLICY, DISPLAY_WAIT_PACKAGE_SHA, CPU_ARGS),
    FIRST_FRAME_FLAG: (FIRST_FRAME_BASE, FIRST_FRAME_NONCE, FIRST_FRAME_POLICY, FIRST_FRAME_PACKAGE_SHA, CPU_ARGS),
    VSYNC_FLAG: (VSYNC_BASE, VSYNC_NONCE, VSYNC_POLICY, VSYNC_PACKAGE_SHA, CPU_ARGS),
    TOUCH_USERLAND_FLAG: (TOUCH_USERLAND_BASE, TOUCH_USERLAND_NONCE, TOUCH_USERLAND_POLICY,
                          TOUCH_USERLAND_PACKAGE_SHA, TOUCH_USERLAND_ARGS),
    CONTROL_FLAG: (CONTROL_BASE, CONTROL_NONCE, CONTROL_POLICY, CONTROL_PACKAGE_SHA, CPU_ARGS),
    FLAG: (BASE, NONCE, POLICY, PACKAGE_SHA, ARGS),
    CPU_FLAG: (CPU_BASE, CPU_NONCE, CPU_POLICY, CPU_PACKAGE_SHA, CPU_ARGS),
    FIRST_SWAP_FLAG: (FIRST_SWAP_BASE, FIRST_SWAP_NONCE, FIRST_SWAP_POLICY, FIRST_SWAP_PACKAGE_SHA, CPU_ARGS),
}
ROLES = {
    'boot','FAT','fd','kernel','menu','ADT','loader','manager','package','offline_check',
    'installed_result','install_claim','install_admission','install_review','local_replay',
    'record_identity','record_decoder','source_build_proof','previous_runner',
    'primary_GPT','backup_GPT','root_manifest','Data_header','Data_metadata',
    'root_first_page','root_before','root_after','fixed_builder','fixed_runner','entry',
    'device_helpers','recovery_identity','record_helpers','transport_core',
    'adb_binary','fastboot_binary','host_adb_proof',
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def exact(actual, expected):
    return all(type(actual.get(key)) is type(value) and actual[key] == value
               for key, value in expected.items())


def root_lineage(flag):
    if flag in (POSTERBOARD_PASSIVE_FLAG, SB_WALLPAPER_CONTROL_FLAG, SB_BOOTARGS_FLAG, UI_DISPLAY_WAIT_FLAG, SB_ULOCK_FLAG, SB_OWNER_FLAG, SB_PEER_FLAG, LSD_VFS_FLAG, LSD_COPYLEN_FLAG, LSD_BUDGET_FLAG, LSD_PREFIX_FLAG, LSD_SUFFIX_FLAG, NETWORK_IDENTITY_FLAG, LONG_WINDOW_FLAG, REPLY_DESTINATION_FLAG, REPLY_HOLDER_FLAG, HOLDER_NAME_FLAG, SERVICE_NAME_FLAG, KEYSTORE_FLAG, KEYSTORE_RERUN_FLAG, KEYSTORE_RETAG_FLAG):
        return POSTERBOARD_PASSIVE_ROOT_SHA, POSTERBOARD_PASSIVE_INSTALL_SCOPE, 66
    if flag in (POSTERBOARD_RETURN_FLAG, POSTERBOARD_WAIT_FLAG):
        return POSTERBOARD_RETURN_ROOT_SHA, POSTERBOARD_RETURN_INSTALL_SCOPE, 65
    if flag in (POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS):
        return POSTERBOARD_ENTRY_ROOT_SHA, POSTERBOARD_ENTRY_INSTALL_SCOPE, 64
    if flag == POSTERBOARD_ENTRY_FLAG:
        return POSTERBOARD_ENTRY_ROOT_SHA, POSTERBOARD_ENTRY_INSTALL_SCOPE, 64
    if flag in (POSTERBOARD_REPLY_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS, POSTERBOARD_OUTPUT_FLAG):
        return POSTERBOARD_REPLY_ROOT_SHA, POSTERBOARD_REPLY_INSTALL_SCOPE, 64
    if flag in (DISPLAY_SCALE_FLAG, CONTINUITY_FLAG, POSTERBOARD_FLAG, POSTERBOARD_REPLY_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS, POSTERBOARD_OUTPUT_FLAG):
        return SERVICE_ROOT_SHA, SERVICE_INSTALL_SCOPE, 81
    if flag == WORK_INTERVAL_FLAG:
        return SERVICE_ROOT_SHA, SERVICE_INSTALL_SCOPE, 81
    if flag == PLATFORM_FIX_FLAG:
        return SERVICE_ROOT_SHA, SERVICE_INSTALL_SCOPE, 81
    if flag == SERVICE_FLAG:
        return SERVICE_ROOT_SHA, SERVICE_INSTALL_SCOPE, 81
    if flag in (OSANALYTICS_FLAG, OSFILES_FLAG, SBREASON_FLAG, STDIO_FLAG):
        return OSANALYTICS_ROOT_SHA, OSANALYTICS_INSTALL_SCOPE, 86
    if flag in (TWO_DIR_REPORT_FLAG, PATH_FLAG, LOG_FLAG, CONTEXT_FLAG):
        return TWO_DIR_REPORT_ROOT_SHA, TWO_DIR_REPORT_INSTALL_SCOPE, 61
    if flag in (CRASH_REPORT_FLAG, TWO_DIR_REPORT_FLAG, PATH_FLAG, LOG_FLAG, CONTEXT_FLAG, OSANALYTICS_FLAG, OSFILES_FLAG, SBREASON_FLAG, STDIO_FLAG, SERVICE_FLAG, PLATFORM_FIX_FLAG, WORK_INTERVAL_FLAG, DISPLAY_SCALE_FLAG, CONTINUITY_FLAG, POSTERBOARD_FLAG, POSTERBOARD_REPLY_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS, POSTERBOARD_OUTPUT_FLAG, *DELIVERY_FLAGS):
        return CRASH_REPORT_ROOT_SHA, CRASH_REPORT_INSTALL_SCOPE, 110
    if flag in (CPU_NO_SAMPLING_FLAG, SB_LIFECYCLE_FLAG, SB_STDERR_FLAG):
        return CPU_NO_SAMPLING_ROOT_SHA, CPU_NO_SAMPLING_INSTALL_SCOPE, 57
    if flag in CURRENT_ROOT_FLAGS:
        return CONTROL_ROOT_SHA, CONTROL_INSTALL_SCOPE, 5621
    return ROOT_SHA, INSTALL_SCOPE, 5597


def validate_bundle(path, flag=FLAG):
    base, nonce, policy, package_sha, boot_args = TRIAL_INPUTS[flag]
    cpu = policy['CPU_presenter']
    root_preserved = flag not in (POSTERBOARD_REPLY_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_RETURN_FLAG, POSTERBOARD_PASSIVE_FLAG)
    root_sha, install_scope, pages = root_lineage(flag)
    require(path == base/'bundle.json' and path.resolve() == path, 'canonical trial bundle required')
    bundle = load(path)
    require(exact(bundle, policy | {'allow_boot': False}), 'unexpected trial policy')
    pins = bundle['pins']
    require(set(pins) == ROLES, 'incomplete boot, protection or host inputs')
    for name, row in pins.items():
        source, copy = Path(row['path']), Path(row['archive'])
        require(source.is_absolute() and source.resolve() == source and copy.parent == base/'archive'
                and copy.resolve() == copy and not source.samefile(copy)
                and sha(source) == sha(copy) == row['sha256'], 'changed or shared input ' + name)
    def path_of(role):
        return Path(pins[role]['path'])
    def digest(role):
        return pins[role]['sha256']

    siblings = Path(__file__).resolve().parent
    for role, name in {'entry': Path(__file__).name, 'fixed_runner': RUNNER.name,
                       'fixed_builder':'build-zorn-debug.py','transport_core':'zorn_ios26_logdirs_boot_trial.py',
                       'device_helpers':'zorn_gpu_resource_trial.py','recovery_identity':'zorn_recovery_identity.py',
                       'record_helpers':'zorn_gpu_ios26_platform_record.py'}.items():
        require(path_of(role) == siblings/name, 'fixed source differs: ' + role)

    pack = load(path_of('package'))
    require(digest('package') == package_sha and pack['root']['sha256'] == root_sha
            and pack['artifact_identity']['run_id'] == nonce and pack['boot_args'] == boot_args
            and pack.get('CPU_presenter_selected', False) is cpu
            and pack['timer_seconds'] == (1080 if flag == LONG_WINDOW_FLAG else 300)
            and pack['userland_progress_snapshot_seconds'] == policy['userland_snapshot_seconds']
            and pack['actual_file_loader_parser_pass'] and pack['WDT1_markers_both_present']
            and not any(pack[k] for k in ('OS_embedded_in_FAT_or_RAM', 'GPU_startup_selected'))
            and pack['touch_startup_selected'] is policy['touch_startup'],
            'reviewed boot composition differs')
    expected = {role:pack[role]['sha256'] for role in ('boot','FAT')}
    expected.update({role:pack['pins'][field]['sha256'] for role,field in [('fd','FD'),('kernel','kernel'),('ADT','ADT')]})
    for role,suffix in {'loader':'DarwinBoot26.efi','manager':'BOOTAA64.EFI','menu':'unixnu.toml'}.items():
        expected[role] = next(row['sha256'] for row in pack['FAT_members'] if row['FAT_path'].endswith('/'+suffix))
    require(all(digest(role)==value for role,value in expected.items()), 'carrier or FAT members differ')
    proof = load(path_of('offline_check'))
    require(exact(proof,dict(boot_sha256=expected['boot'], kernel_sha256=expected['kernel'],
            root_sha256=root_sha, record_id=nonce, actual_PID1_guard=True,
            registered_root_match_and_source_atomic_once_gate=True,
            checkpoint_delay_ms=1000 * policy['userland_snapshot_seconds'],
            existing_record_relative_lba=2291712, record_pages=1))
            and load(path_of('record_identity'))['run_id'] == nonce, 'PID 1 checkpoint binding differs')
    if cpu:
        expected_cpu = {'CPU_presenter_selected': True}
        expected_cpu['CPU_presenter_source_path_preserved' if flag in (CRASH_REPORT_FLAG, TWO_DIR_REPORT_FLAG, PATH_FLAG, LOG_FLAG, CONTEXT_FLAG, OSANALYTICS_FLAG, OSFILES_FLAG, SBREASON_FLAG, STDIO_FLAG, SERVICE_FLAG, PLATFORM_FIX_FLAG, WORK_INTERVAL_FLAG, DISPLAY_SCALE_FLAG, CONTINUITY_FLAG, POSTERBOARD_FLAG, POSTERBOARD_REPLY_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS, POSTERBOARD_OUTPUT_FLAG, *DELIVERY_FLAGS)
                     else 'presenter_actual_return_in_existing_record'] = True
        require(exact(proof,expected_cpu), 'CPU presenter source or observation differs')
    if flag == FIRST_SWAP_FLAG or (flag in CURRENT_ROOT_FLAGS and flag not in (CRASH_REPORT_FLAG, TWO_DIR_REPORT_FLAG, PATH_FLAG, LOG_FLAG, CONTEXT_FLAG, OSANALYTICS_FLAG, OSFILES_FLAG, SBREASON_FLAG, STDIO_FLAG, SERVICE_FLAG, PLATFORM_FIX_FLAG, WORK_INTERVAL_FLAG, DISPLAY_SCALE_FLAG, CONTINUITY_FLAG, POSTERBOARD_FLAG, POSTERBOARD_REPLY_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS, POSTERBOARD_OUTPUT_FLAG, *DELIVERY_FLAGS)):
        require(exact(proof,{'framebuffer_first_return_in_existing_record': True}),
                'framebuffer observation differs')
    if flag == FIRST_FRAME_FLAG:
        require(exact(proof, {'first_frame_stages_in_existing_record': True})
                and path_of('record_decoder') == base.parent / 'inspect-userland-first-frame26.py',
                'BackBoard first-frame observation or decoder differs')
    if flag == DISPLAY_WAIT_FLAG:
        require(exact(proof, {'first_frame_stages_in_existing_record': True,
                              'first_thread_wait_metadata_only': True})
                and path_of('record_decoder') == base.parent / 'inspect-userland-display-wait26.py',
                'Display wait observation or decoder differs')
    if flag == SOFTWARE_ACCEL_FLAG:
        require(exact(proof, {'first_frame_stages_in_existing_record': True,
                              'software_accelerator_submission_in_existing_record': True,
                              'metal_properties_disabled': True})
                and path_of('record_decoder') == base.parent / 'inspect-userland-software-accelerator26.py',
                'Software display service or decoder differs')
    if flag == IOSURFACE_ROOT_FLAG:
        require(exact(proof, {'iosurface_started_before_framebuffer': True,
                              'iosurface_backboard_clients_in_existing_record': True,
                              'metal_properties_disabled': True})
                and path_of('record_decoder') == base.parent / 'inspect-userland-iosurface-root26.py',
                'IOSurface startup or decoder differs')
    if flag == SURFACE_PLATFORM_FLAG:
        require(exact(proof, {'original_iosurface_object_preserved': True,
                              'platform_surface_call_precedes_presenter_schedule': True})
                and path_of('record_decoder') == base.parent / 'inspect-userland-iosurface-platform26.py',
                'Platform IOSurface startup or early checkpoint differs')
    if flag in (SURFACE_CLIENT_FLAG, SURFACE_RECORD_FLAG):
        require(exact(proof, {'platform_surface_call_precedes_presenter_schedule': True,
                              'backboard_surface_open_and_create_return_in_existing_record': True})
                and path_of('record_decoder') == base.parent / 'inspect-userland-iosurface-client26.py',
                'IOSurface client or checkpoint differs')
    if flag in (SURFACE_RECORD_FLAG, SURFACE_CREATE_FLAG, SURFACE_INIT_FLAG, FB_UNSUPPORTED_FLAG, THREAD_CENSUS_FLAG, CPU_NO_SAMPLING_FLAG, SB_LIFECYCLE_FLAG, SB_STDERR_FLAG, CRASH_REPORT_FLAG, TWO_DIR_REPORT_FLAG, PATH_FLAG, LOG_FLAG, CONTEXT_FLAG, OSANALYTICS_FLAG, OSFILES_FLAG, SBREASON_FLAG, STDIO_FLAG, SERVICE_FLAG, PLATFORM_FIX_FLAG, WORK_INTERVAL_FLAG, DISPLAY_SCALE_FLAG, CONTINUITY_FLAG, POSTERBOARD_FLAG, POSTERBOARD_REPLY_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS, POSTERBOARD_OUTPUT_FLAG, *DELIVERY_FLAGS):
        require(exact(proof, {'final_gpt_read_and_existing_log_share_transport_lock': True,
                              'single_existing_log_write_no_retry': True}),
                'IOSurface record transport scope differs')
    if flag == SURFACE_CREATE_FLAG:
        require(exact(proof, {'platform_surface_call_precedes_presenter_schedule': True,
                              'first_BackBoard_Create_entry_and_return_in_existing_record': True,
                              'IOSurface_Create_lifetime_repair_linked': True})
                and path_of('record_decoder') == base.parent / 'inspect-userland-iosurface-create26.py',
                'IOSurface Create observation, lifetime repair or decoder differs')
    if flag == SURFACE_INIT_FLAG:
        require(exact(proof, {'platform_surface_call_precedes_presenter_schedule': True,
                              'first_BackBoard_Create_entry_and_return_in_existing_record': True,
                              'IOSurface_Create_lifetime_repair_linked': True,
                              'first_BackBoard_Init_entry_return_and_lengths_in_existing_record': True})
                and path_of('record_decoder') == base.parent / 'inspect-userland-iosurface-init26.py',
                'IOSurface Init observation, lifetime repair or decoder differs')
    if flag == FB_UNSUPPORTED_FLAG:
        require(exact(proof, {'platform_surface_call_precedes_presenter_schedule': True,
                              'first_BackBoard_Create_entry_and_return_in_existing_record': True,
                              'IOSurface_Create_lifetime_repair_linked': True,
                              'first_BackBoard_Init_entry_return_and_lengths_in_existing_record': True,
                              'unknown_framebuffer_methods_refused_and_observed': True})
                and path_of('record_decoder') == base.parent / 'inspect-userland-framebuffer-unsupported26.py',
                'CPU framebuffer unsupported-method behavior or decoder differs')
    if flag == THREAD_CENSUS_FLAG:
        require(exact(proof, {'platform_surface_call_precedes_presenter_schedule': True,
                              'first_BackBoard_Create_entry_and_return_in_existing_record': True,
                              'IOSurface_Create_lifetime_repair_linked': True,
                              'first_BackBoard_Init_entry_return_and_lengths_in_existing_record': True,
                              'unknown_framebuffer_methods_refused_and_observed': True,
                              'source_thread_census_bounded_retained_and_no_stacks': True})
                and path_of('record_decoder') == base.parent / 'inspect-userland-thread-census26.py',
                'CPU thread census bounds, source observation or decoder differs')
    if flag == CPU_NO_SAMPLING_FLAG:
        require(exact(proof, {'platform_surface_call_precedes_presenter_schedule': True,
                              'first_BackBoard_Create_entry_and_return_in_existing_record': True,
                              'IOSurface_Create_lifetime_repair_linked': True,
                              'first_BackBoard_Init_entry_return_and_lengths_in_existing_record': True,
                              'unknown_framebuffer_methods_refused_and_observed': True,
                              'source_thread_census_bounded_retained_and_no_stacks': True,
                              'native_HID_userland_sampler_compiled_out': True,
                              'actual_root_consumer_recompiled_and_bound': True})
                and pack['root_installed'] is True and pack['phone_root_matches_candidate'] is True
                and pack['installation_receipt_sha256'] == digest('installed_result')
                and path_of('record_decoder') == base.parent / 'inspect-userland-thread-census26.py',
                'CPU no-sampling root binding or diagnostic source differs')
    if flag in (SB_LIFECYCLE_FLAG, SB_STDERR_FLAG):
        require(exact(proof, {'platform_surface_call_precedes_presenter_schedule': True,
                              'first_BackBoard_Create_entry_and_return_in_existing_record': True,
                              'IOSurface_Create_lifetime_repair_linked': True,
                              'first_BackBoard_Init_entry_return_and_lengths_in_existing_record': True,
                              'unknown_framebuffer_methods_refused_and_observed': True,
                              'source_thread_census_bounded_retained_and_no_stacks': True,
                              'native_HID_userland_sampler_compiled_out': True,
                              'actual_root_consumer_recompiled_and_bound': True,
                              'SpringBoard_kernel_lifecycle_correlated_by_uniqueid': True})
                and pack['root_installed'] is True and pack['phone_root_matches_candidate'] is True
                and Path(pack['root_installed_delta_receipt']) == path_of('installed_result')
                and path_of('record_decoder') == base.parent / ('inspect-userland-sb-stderr26.py' if flag == SB_STDERR_FLAG else 'inspect-userland-sb-lifecycle26.py'),
                'SpringBoard lifecycle source, process identity or root binding differs')
    if flag == SB_STDERR_FLAG:
        require(exact(proof, {'SpringBoard_successful_scalar_stderr_only': True,
                              'SpringBoard_stderr_native_result_preserved': True,
                              'SpringBoard_stderr_copy_budget': 32,
                              'SpringBoard_stderr_copy_bytes_max': 48,
                              'SpringBoard_stderr_exact_backend_adapter_host_checked': True}),
                'SpringBoard stderr scope, bounds or native result preservation differs')
    if flag in (CRASH_REPORT_FLAG, TWO_DIR_REPORT_FLAG, PATH_FLAG, LOG_FLAG, CONTEXT_FLAG, OSANALYTICS_FLAG, OSFILES_FLAG, SBREASON_FLAG, STDIO_FLAG, SERVICE_FLAG, PLATFORM_FIX_FLAG, WORK_INTERVAL_FLAG, DISPLAY_SCALE_FLAG, CONTINUITY_FLAG, POSTERBOARD_FLAG, POSTERBOARD_REPLY_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS, POSTERBOARD_OUTPUT_FLAG, *DELIVERY_FLAGS):
        require(exact(proof, {'framebuffer_counts_and_stages_in_existing_record': True,
                              'SpringBoard_kernel_lifecycle_correlated_by_uniqueid': True,
                              'collector_only_ordinary_error_fields': True,
                              'collector_RAMFS_gate_implemented': True,
                              'collector_helper_uniqueid_runid_first_target_checked': True,
                              'collector_input_data_owned': True,
                              'actual_root_consumer_recompiled_and_bound': True,
                              'native_HID_userland_sampler_compiled_out': True,
                              'root_installed_receipt_bound': True})
                and pack['root_installed'] is True and pack['phone_root_matches_candidate'] is True
                and pack['installation_receipt_sha256'] == digest('installed_result')
                and Path(pack['root_installed_delta_receipt']) == path_of('installed_result')
                and path_of('record_decoder') == base.parent / ('inspect-userland-lsd-vfs-26.py' if flag in (LSD_VFS_FLAG, LSD_COPYLEN_FLAG, LSD_BUDGET_FLAG, LSD_PREFIX_FLAG, LSD_SUFFIX_FLAG, NETWORK_IDENTITY_FLAG, LONG_WINDOW_FLAG, REPLY_DESTINATION_FLAG, REPLY_HOLDER_FLAG, HOLDER_NAME_FLAG, SERVICE_NAME_FLAG, KEYSTORE_FLAG, KEYSTORE_RERUN_FLAG, KEYSTORE_RETAG_FLAG) else 'inspect-userland-sb-peer-26.py' if flag == SB_PEER_FLAG else 'inspect-userland-sb-owner-26.py' if flag == SB_OWNER_FLAG else 'inspect-userland-sb-ulock-26.py' if flag == SB_ULOCK_FLAG else 'inspect-userland-ui-display-wait-26.py' if flag == UI_DISPLAY_WAIT_FLAG else 'inspect-userland-posterboard-wait-26.py' if flag in POSTERBOARD_LONG_WAIT_FLAGS else 'inspect-userland-posterboard-return26.py' if flag == POSTERBOARD_RETURN_FLAG else 'inspect-userland-posterboard-wide26.py' if flag in POSTERBOARD_WIDE_RECORD_FLAGS else 'inspect-userland-posterboard-bits26.py' if flag == POSTERBOARD_BITS_FLAG else 'inspect-userland-posterboard-tail26.py' if flag in (POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS) else 'inspect-userland-posterboard-output26.py' if flag == POSTERBOARD_OUTPUT_FLAG else 'inspect-userland-posterboard26.py' if flag in (POSTERBOARD_FLAG, POSTERBOARD_REPLY_FLAG) else 'inspect-userland-cpu-continuity26.py' if flag == CONTINUITY_FLAG else 'inspect-userland-display-scale26.py' if flag == DISPLAY_SCALE_FLAG else 'inspect-userland-service26.py' if flag in (SERVICE_FLAG, PLATFORM_FIX_FLAG, WORK_INTERVAL_FLAG) else 'inspect-userland-sbstdio26.py' if flag == STDIO_FLAG else 'inspect-userland-sbreason26.py' if flag == SBREASON_FLAG else 'inspect-userland-osfiles26.py' if flag == OSFILES_FLAG else 'inspect-userland-osanalytics26.py' if flag == OSANALYTICS_FLAG else 'inspect-userland-log-context26.py' if flag == CONTEXT_FLAG else 'inspect-userland-general-log26.py' if flag == LOG_FLAG else 'inspect-userland-reporter-path26.py' if flag == PATH_FLAG else 'inspect-userland-two-dir-report26.py' if flag == TWO_DIR_REPORT_FLAG else 'inspect-userland-reporter-files26.py' if flag == FILES_FLAG else 'inspect-userland-corpse-notify26.py' if flag == CORPSE_FLAG else 'inspect-userland-crash-delivery26.py' if flag in DELIVERY_FLAGS else 'inspect-userland-crash-report26.py'),
                'ordinary crash-report source,installed root or decoder differs')
    if flag in DELIVERY_FLAGS:
        require(exact(proof, {'native_crash_notification_result_preserved': True,
                              'first_ReportCrash_exact_path_only': True,
                              'bounded_ReportCrash_scalar_stderr_only': True,
                              'reporter_stderr_attempt_limit': 32,
                              'reporter_stderr_copy_bytes_max': 64,
                              'delivery_backend_adapter_host_checked': True,
                              'diagnostic_parser_host_checked': True,
                              'helper_protocol_unchanged': True,
                              'installed_root_unchanged': root_preserved})
                and pack['artifact_identity']['helper_protocol_run_id'] == CRASH_REPORT_NONCE
                and nonce != CRASH_REPORT_NONCE,
                'native delivery/reporter observation or retained helper protocol differs')
    if flag in (CORPSE_FLAG, FILES_FLAG, PATH_FLAG, LOG_FLAG, CONTEXT_FLAG, OSANALYTICS_FLAG):
        require(exact(proof, {'marked_corpse_scalar_identity_correlated': True,
                              'corpse_native_calls_and_results_preserved': True,
                              'corpse_no_task_pointer_retention': True,
                              'corpse_first_notification_bounded_atomic': True,
                              'task_source_baseline_byte_identical': True,
                              'corpse_backend_host_checked': True,
                              'corpse_formatter_decoder_host_checked': True}),
                'asynchronous corpse source/identity/result observation differs')
    if flag in (FILES_FLAG, PATH_FLAG):
        require(exact(proof, {'file_metadata_first_ReportCrash_only': True,
                              'file_native_return_values_preserved': True,
                              'file_post_native_copy_best_effort': True,
                              'file_copy_budget': 32,
                              'file_path_prefix_bytes': 63,
                              'readonly_file_opens_counted_without_copy': True,
                              'file_observer_backend_adapter_host_checked': True,
                              'file_formatter_decoder_host_checked': True,
                              'VFS_baseline_byte_identical': True,
                              'original_VFS_source_tokens_preserved': True,
                              'file_last_sample_not_complete_history': True}),
                'ordinary reporter file metadata/native return/copy scope differs')
    if flag == TWO_DIR_REPORT_FLAG:
        require(exact(proof, {'collector_fixed_root_mobile_directories': True,
                              'collector_independent_RAMFS_gate': True,
                              'collector_total_file_budget': 64,
                              'collector_entries_per_directory': 64,
                              'collector_two_directory_host_checked': True,
                              'new_helper_protocol_bound_to_package': True,
                              'async_notification_and_report_message_in_record': True})
                and pack['artifact_identity']['helper_protocol_run_id'] == nonce,
                'root/mobile collector budget,protocol or diagnostic record differs')
    if flag == PATH_FLAG:
        require(exact(proof, {'first_write_and_priority_candidate_in_record': True,
                              'path_priority_metadata_heuristic_only': True,
                              'collector_two_directory_source_preserved': True,
                              'installed_root_unchanged': root_preserved,
                              'helper_protocol_unchanged': True,
                              'native_crash_notification_result_preserved': True,
                              'first_ReportCrash_exact_path_only': True})
                and pack['artifact_identity']['helper_protocol_run_id'] == TWO_DIR_REPORT_NONCE
                and nonce != TWO_DIR_REPORT_NONCE,
                'priority path/source or retained two-directory helper differs')
    if flag in (LOG_FLAG, CONTEXT_FLAG):
        require(exact(proof,{'ordinary_log_exact_fileproc_path': True, 'ordinary_log_first_ReportCrash_uniqueid': True, 'ordinary_log_native_write_result_preserved': True, 'ordinary_log_vnode_get_put_scoped': True, 'ordinary_log_no_pointer_retention': True, 'ordinary_log_only_successful_bytes': True, 'ordinary_log_post_native_best_effort': True, 'ordinary_log_host_checked': True, 'ordinary_log_formatter_decoder_host_checked': True, 'ordinary_log_heuristic_not_crash_cause': True, 'ordinary_log_POSIX_write_writev_only': True, 'helper_protocol_unchanged': True, 'installed_root_unchanged': root_preserved, 'ordinary_log_probe_budget': 32, 'ordinary_log_iovec_limit': 4, 'ordinary_log_copy_bytes': 512, 'ordinary_log_message_bytes': 127})
                and pack['artifact_identity']['helper_protocol_run_id'] == TWO_DIR_REPORT_NONCE
                and nonce != TWO_DIR_REPORT_NONCE,
                'ordinary log scope,retained helper protocol or source constraints differ')
    if flag == CONTEXT_FLAG:
        require(exact(proof,{'ordinary_log_fragments_assembled': True, 'ordinary_log_hex_spans_redacted': True, 'ordinary_log_explicit_machine_rows_excluded': True, 'platform_context_CRC_runid_checked': True, 'platform_single_CDB_and_lock_sequence_preserved': True, 'platform_legacy_zero_tail_preserved': True, 'platform_actual_selected_IO_source_host_checked': True, 'platform_context_formatter_decoder_host_checked': True, 'kernel_root_and_helper_unchanged': True, 'ordinary_log_context_limit': 2048, 'ordinary_log_pending_line_limit': 1024, 'platform_base_record_bytes': 544, 'platform_context_record_bytes': (3552 if flag in POSTERBOARD_WIDE_RECORD_FLAGS else 2080), 'platform_context_record_offset': 544, 'platform_page_bytes': 4096}),
                'ordinary context,CRC,bounds or exact source IO proof differs')
    if flag == OSANALYTICS_FLAG:
        require(exact(proof,{'ordinary_log_exact_fileproc_path': True, 'ordinary_log_first_ReportCrash_uniqueid': True, 'ordinary_log_native_write_result_preserved': True, 'ordinary_log_vnode_get_put_scoped': True, 'ordinary_log_no_pointer_retention': True, 'ordinary_log_only_successful_bytes': True, 'ordinary_log_post_native_best_effort': True, 'ordinary_log_host_checked': True, 'ordinary_log_formatter_decoder_host_checked': True, 'ordinary_log_heuristic_not_crash_cause': True, 'ordinary_log_POSIX_write_writev_only': True, 'helper_protocol_unchanged': True, 'ordinary_log_fragments_assembled': True, 'ordinary_log_hex_spans_redacted': True, 'ordinary_log_explicit_machine_rows_excluded': True, 'platform_context_CRC_runid_checked': True, 'platform_single_CDB_and_lock_sequence_preserved': True, 'platform_legacy_zero_tail_preserved': True, 'platform_actual_selected_IO_source_host_checked': True, 'platform_context_formatter_decoder_host_checked': True, 'osanalytics_stock_derived_demand_service_installed': True, 'osanalytics_first_exact_exec_uniqueid_lifecycle': True, 'osanalytics_native_exec_exit_source_preserved': True, 'osanalytics_host_checked': True, 'collector_full_ordinary_message_in_context': True, 'collector_message_identity_flags_UTF8_host_checked': True, 'ordinary_log_probe_budget': 32, 'ordinary_log_iovec_limit': 4, 'ordinary_log_copy_bytes': 512, 'ordinary_log_message_bytes': 127, 'ordinary_log_context_limit': 2048, 'ordinary_log_pending_line_limit': 1024, 'platform_base_record_bytes': 544, 'platform_context_record_bytes': (3552 if flag in POSTERBOARD_WIDE_RECORD_FLAGS else 2080), 'platform_context_record_offset': 544, 'platform_page_bytes': 4096, 'ordinary_log_history_record_cap': 1536, 'collector_message_record_cap': 127, 'installed_root_unchanged': False, 'kernel_root_and_helper_unchanged': False})
                and pack['artifact_identity']['helper_protocol_run_id'] == TWO_DIR_REPORT_NONCE
                and nonce != TWO_DIR_REPORT_NONCE,
                'installed diagnostic service,source observer or full report payload scope differs')
    if flag in (OSFILES_FLAG, SBREASON_FLAG):
        require(exact(proof,{'helper_protocol_unchanged': True, 'installed_root_unchanged': root_preserved, 'osanalytics_first_exact_exec_uniqueid_lifecycle': True, 'osanalytics_successful_exec_family_eligibility': True, 'osanalytics_foreign_exec_exit_withdraw': True, 'osanalytics_observation_drop_fail_closed': True, 'osanalytics_no_pointer_retention': True, 'osanalytics_readonly_opens_no_extra_copy': True, 'osanalytics_file_native_return_preserved': True, 'osanalytics_first_write_and_priority_sourcePID': True, 'osanalytics_file_metadata_only': True, 'osanalytics_file_priority_is_heuristic': True, 'osanalytics_host_checked': True, 'osanalytics_metadata_formatter_parser_host_checked': True, 'platform_single_CDB_and_lock_sequence_preserved': True, 'platform_legacy_zero_tail_preserved': True, 'platform_actual_selected_IO_source_host_checked': True, 'source_owned_metadata_JSON_only': True, 'full_ordinary_message_capacity_retained': True, 'native_crash_notification_source_preserved': True, 'osanalytics_deduplicated_identity_slots': 4, 'osanalytics_family_file_copy_budget': 64, 'osanalytics_path_prefix_bytes': 127, 'platform_base_record_bytes': 544, 'platform_context_record_bytes': (3552 if flag in POSTERBOARD_WIDE_RECORD_FLAGS else 2080), 'platform_context_record_offset': 544, 'platform_page_bytes': 4096, 'collector_message_record_cap': 127})
                and pack['artifact_identity']['helper_protocol_run_id'] == TWO_DIR_REPORT_NONCE
                and nonce != TWO_DIR_REPORT_NONCE,
                'helper family file metadata,eligibility,bounds or retained root protocol differs')
    if flag == SBREASON_FLAG:
        require(exact(proof,{'SpringBoard_reason_first_uniqueid_once': True, 'SpringBoard_reason_kernel_owned_public_description_only': True, 'SpringBoard_reason_no_other_KCData_payload': True, 'SpringBoard_reason_no_user_or_task_memory': True, 'SpringBoard_reason_no_pointer_retention': True, 'SpringBoard_reason_native_exit_preserved': True, 'SpringBoard_reason_ASCII_sanitized_hex_redacted_machine_text_rejected': True, 'SpringBoard_reason_adapter_backend_host_checked': True, 'SpringBoard_reason_formatter_decoder_host_checked': True, 'SpringBoard_reason_actual_native_dependencies_checked': True, 'SpringBoard_reason_item_budget': 32, 'SpringBoard_reason_scan_bytes': 512, 'SpringBoard_reason_text_bytes': 191, 'SpringBoard_reason_buffer_max': 5120}), 'first SpringBoard ordinary reason,bounds or native preservation differs')
    if flag == STDIO_FLAG:
        require(exact(proof,{'stdio_first_process_uniqueid_gate': True, 'stdio_shared_scalar_vector_path_native_preserved': True, 'stdio_stdout_stderr_separate': True, 'stdio_socket_payloads_excluded': True, 'stdio_pre_native_UIO_metadata_ephemeral': True, 'stdio_post_native_successful_accepted_bytes_only': True, 'stdio_native_error_and_fileproc_drop_preserved': True, 'stdio_gap_marks_prevent_cross_gap_join': True, 'stdio_line_assembler_source_reused': True, 'stdio_machine_rows_excluded_hex_redacted': True, 'stdio_host_checks': True, 'stdio_actual_formatter_CRC_decoder_checks': True, 'stdio_actual_native_dependencies_checked': True, 'stdio_no_root_or_helper_change': True, 'stdio_record_omissions_explicit': True, 'platform_single_CDB_and_lock_sequence_preserved': True, 'platform_legacy_zero_tail_preserved': True, 'platform_actual_selected_IO_source_host_checked': True, 'source_owned_metadata_JSON_only': True, 'helper_protocol_unchanged': True, 'installed_root_unchanged': root_preserved, 'stdio_shared_reservations': 32, 'stdio_iov_max': 4, 'stdio_copy_bytes': 512, 'stdio_history_record_cap': 256, 'stdio_selected_message_cap': 127, 'platform_base_record_bytes': 544, 'platform_context_record_bytes': (3552 if flag in POSTERBOARD_WIDE_RECORD_FLAGS else 2080), 'platform_context_record_offset': 544, 'platform_page_bytes': 4096})
                and pack['artifact_identity']['helper_protocol_run_id'] == TWO_DIR_REPORT_NONCE
                and nonce != TWO_DIR_REPORT_NONCE,
                'first SpringBoard scalar/vector ordinary streams,bounds or native preservation differs')
    if flag == SERVICE_FLAG:
        require(exact(proof,{'stdio_first_process_uniqueid_gate': True, 'stdio_shared_scalar_vector_path_native_preserved': True, 'stdio_stdout_stderr_separate': True, 'stdio_socket_payloads_excluded': True, 'stdio_pre_native_UIO_metadata_ephemeral': True, 'stdio_post_native_successful_accepted_bytes_only': True, 'stdio_native_error_and_fileproc_drop_preserved': True, 'stdio_gap_marks_prevent_cross_gap_join': True, 'stdio_line_assembler_source_reused': True, 'stdio_machine_rows_excluded_hex_redacted': True, 'stdio_host_checks': True, 'stdio_actual_formatter_CRC_decoder_checks': True, 'stdio_actual_native_dependencies_checked': True, 'stdio_record_omissions_explicit': True, 'platform_single_CDB_and_lock_sequence_preserved': True, 'platform_legacy_zero_tail_preserved': True, 'platform_actual_selected_IO_source_host_checked': True, 'source_owned_metadata_JSON_only': True, 'helper_protocol_unchanged': True, 'stdio_first_skip_native_metadata_scalar_only': True, 'stdio_skip_classification_host_checked': True, 'project_machine_diag_excluded_native_preprocessor': True, 'project_machine_diag_inert_callbacks_host_checked': True, 'userland_machine_diag_excluded': True, 'two_existing_job_Disabled_only': True, 'service_policy_root_delta_receipt_bound': True, 'source_root_lineage_preserved': True, 'stdio_shared_reservations': 32, 'stdio_iov_max': 16, 'stdio_copy_bytes': 512, 'stdio_history_record_cap': 256, 'stdio_selected_message_cap': 127, 'platform_base_record_bytes': 544, 'platform_context_record_bytes': (3552 if flag in POSTERBOARD_WIDE_RECORD_FLAGS else 2080), 'platform_context_record_offset': 544, 'platform_page_bytes': 4096, 'stdio_skip_reasons': 4, 'installed_root_unchanged': False})
                and pack['artifact_identity']['helper_protocol_run_id'] == TWO_DIR_REPORT_NONCE
                and nonce != TWO_DIR_REPORT_NONCE
                and pack['previous_root_sha256'] == OSANALYTICS_ROOT_SHA,
                'service policy,disabled machine diagnostics,stdio metadata or source-root cohort differs')
    if flag == PLATFORM_FIX_FLAG:
        require(exact(proof,{'stdio_first_process_uniqueid_gate': True, 'stdio_shared_scalar_vector_path_native_preserved': True, 'stdio_stdout_stderr_separate': True, 'stdio_socket_payloads_excluded': True, 'stdio_pre_native_UIO_metadata_ephemeral': True, 'stdio_post_native_successful_accepted_bytes_only': True, 'stdio_native_error_and_fileproc_drop_preserved': True, 'stdio_gap_marks_prevent_cross_gap_join': True, 'stdio_line_assembler_source_reused': True, 'stdio_machine_rows_excluded_hex_redacted': True, 'stdio_host_checks': True, 'stdio_actual_formatter_CRC_decoder_checks': True, 'stdio_actual_native_dependencies_checked': True, 'stdio_record_omissions_explicit': True, 'platform_single_CDB_and_lock_sequence_preserved': True, 'platform_legacy_zero_tail_preserved': True, 'platform_actual_selected_IO_source_host_checked': True, 'source_owned_metadata_JSON_only': True, 'helper_protocol_unchanged': True, 'stdio_first_skip_native_metadata_scalar_only': True, 'stdio_skip_classification_host_checked': True, 'project_machine_diag_excluded_native_preprocessor': True, 'project_machine_diag_inert_callbacks_host_checked': True, 'userland_machine_diag_excluded': True, 'two_existing_job_Disabled_only': True, 'service_policy_root_delta_receipt_bound': True, 'source_root_lineage_preserved': True, 'installed_root_unchanged': root_preserved, 'stdio_preparation_after_native_residual_calculation': True, 'stdio_actual_native_calculation_placement_host_checked': True, 'documented_chosen_status_overlay_source_checked': True, 'documented_chosen_status_only_four_u32': True, 'documented_chosen_overlay_hardware_unchanged': True, 'root_image_and_helper_unchanged': root_preserved, 'stdio_shared_reservations': 32, 'stdio_iov_max': 16, 'stdio_copy_bytes': 512, 'stdio_history_record_cap': 256, 'stdio_selected_message_cap': 127, 'platform_base_record_bytes': 544, 'platform_context_record_bytes': (3552 if flag in POSTERBOARD_WIDE_RECORD_FLAGS else 2080), 'platform_context_record_offset': 544, 'platform_page_bytes': 4096, 'stdio_skip_reasons': 4, 'documented_chosen_status_count': 4})
                and pack['artifact_identity']['helper_protocol_run_id'] == TWO_DIR_REPORT_NONCE
                and nonce != TWO_DIR_REPORT_NONCE
                and pack['previous_root_sha256'] == (POSTERBOARD_RETURN_ROOT_SHA if flag in POSTERBOARD_LONG_WAIT_FLAGS else POSTERBOARD_ENTRY_ROOT_SHA if flag in (POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS) else POSTERBOARD_REPLY_ROOT_SHA if flag in (POSTERBOARD_OUTPUT_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS) else SERVICE_ROOT_SHA),
                'public platform status,normalized stdio placement or unchanged root/helper differs')
    if flag == WORK_INTERVAL_FLAG:
        require(exact(proof,{'stdio_first_process_uniqueid_gate': True, 'stdio_shared_scalar_vector_path_native_preserved': True, 'stdio_stdout_stderr_separate': True, 'stdio_socket_payloads_excluded': True, 'stdio_pre_native_UIO_metadata_ephemeral': True, 'stdio_post_native_successful_accepted_bytes_only': True, 'stdio_native_error_and_fileproc_drop_preserved': True, 'stdio_gap_marks_prevent_cross_gap_join': True, 'stdio_line_assembler_source_reused': True, 'stdio_machine_rows_excluded_hex_redacted': True, 'stdio_host_checks': True, 'stdio_actual_formatter_CRC_decoder_checks': True, 'stdio_actual_native_dependencies_checked': True, 'stdio_record_omissions_explicit': True, 'platform_single_CDB_and_lock_sequence_preserved': True, 'platform_legacy_zero_tail_preserved': True, 'platform_actual_selected_IO_source_host_checked': True, 'source_owned_metadata_JSON_only': True, 'helper_protocol_unchanged': True, 'stdio_first_skip_native_metadata_scalar_only': True, 'stdio_skip_classification_host_checked': True, 'project_machine_diag_excluded_native_preprocessor': True, 'project_machine_diag_inert_callbacks_host_checked': True, 'userland_machine_diag_excluded': True, 'two_existing_job_Disabled_only': True, 'service_policy_root_delta_receipt_bound': True, 'source_root_lineage_preserved': True, 'installed_root_unchanged': root_preserved, 'stdio_preparation_after_native_residual_calculation': True, 'stdio_actual_native_calculation_placement_host_checked': True, 'documented_chosen_status_overlay_source_checked': True, 'documented_chosen_status_only_four_u32': True, 'documented_chosen_overlay_hardware_unchanged': True, 'root_image_and_helper_unchanged': root_preserved, 'work_interval_K80_policy_only': True, 'work_interval_native_backend_preserved': True, 'work_interval_other_privileges_preserved': True, 'work_interval_policy_host_checked': True, 'work_interval_policy_native_bound': True, 'stdio_shared_reservations': 32, 'stdio_iov_max': 16, 'stdio_copy_bytes': 512, 'stdio_history_record_cap': 256, 'stdio_selected_message_cap': 127, 'platform_base_record_bytes': 544, 'platform_context_record_bytes': (3552 if flag in POSTERBOARD_WIDE_RECORD_FLAGS else 2080), 'platform_context_record_offset': 544, 'platform_page_bytes': 4096, 'stdio_skip_reasons': 4, 'documented_chosen_status_count': 4})
                and pack['artifact_identity']['helper_protocol_run_id'] == TWO_DIR_REPORT_NONCE
                and nonce != TWO_DIR_REPORT_NONCE
                and pack['previous_root_sha256'] == (POSTERBOARD_RETURN_ROOT_SHA if flag in POSTERBOARD_LONG_WAIT_FLAGS else POSTERBOARD_ENTRY_ROOT_SHA if flag in (POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS) else POSTERBOARD_REPLY_ROOT_SHA if flag in (POSTERBOARD_OUTPUT_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS) else SERVICE_ROOT_SHA),
                'work interval policy, native backend or inherited source differs')
    if flag in (DISPLAY_SCALE_FLAG, CONTINUITY_FLAG, POSTERBOARD_FLAG, POSTERBOARD_REPLY_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS, POSTERBOARD_OUTPUT_FLAG):
        require(exact(proof,{'stdio_first_process_uniqueid_gate': True, 'stdio_shared_scalar_vector_path_native_preserved': True, 'stdio_stdout_stderr_separate': True, 'stdio_socket_payloads_excluded': True, 'stdio_pre_native_UIO_metadata_ephemeral': True, 'stdio_post_native_successful_accepted_bytes_only': True, 'stdio_native_error_and_fileproc_drop_preserved': True, 'stdio_gap_marks_prevent_cross_gap_join': True, 'stdio_line_assembler_source_reused': True, 'stdio_machine_rows_excluded_hex_redacted': True, 'stdio_host_checks': True, 'stdio_actual_formatter_CRC_decoder_checks': True, 'stdio_actual_native_dependencies_checked': True, 'stdio_record_omissions_explicit': True, 'platform_single_CDB_and_lock_sequence_preserved': True, 'platform_legacy_zero_tail_preserved': True, 'platform_actual_selected_IO_source_host_checked': True, 'source_owned_metadata_JSON_only': True, 'helper_protocol_unchanged': True, 'stdio_first_skip_native_metadata_scalar_only': True, 'stdio_skip_classification_host_checked': True, 'project_machine_diag_excluded_native_preprocessor': True, 'project_machine_diag_inert_callbacks_host_checked': True, 'userland_machine_diag_excluded': True, 'two_existing_job_Disabled_only': True, 'service_policy_root_delta_receipt_bound': True, 'source_root_lineage_preserved': True, 'installed_root_unchanged': root_preserved, 'stdio_preparation_after_native_residual_calculation': True, 'stdio_actual_native_calculation_placement_host_checked': True, 'documented_chosen_status_overlay_source_checked': True, 'documented_chosen_status_only_four_u32': True, 'documented_chosen_overlay_hardware_unchanged': True, 'root_image_and_helper_unchanged': root_preserved, 'work_interval_K80_policy_only': True, 'work_interval_native_backend_preserved': True, 'work_interval_other_privileges_preserved': True, 'work_interval_policy_host_checked': True, 'work_interval_policy_native_bound': True, 'documented_display_scale_matches_product': True, 'only_display_scale_added_to_parent_ADT': flag not in (POSTERBOARD_REPLY_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS, POSTERBOARD_OUTPUT_FLAG), 'stdio_shared_history_roundtrip_checked': True, 'stdio_shared_reservations': 32, 'stdio_iov_max': 16, 'stdio_copy_bytes': 512, 'stdio_selected_message_cap': 127, 'platform_base_record_bytes': 544, 'platform_context_record_bytes': (3552 if flag in POSTERBOARD_WIDE_RECORD_FLAGS else 2080), 'platform_context_record_offset': 544, 'platform_page_bytes': 4096, 'stdio_skip_reasons': 4, 'documented_chosen_status_count': 4, 'stdio_stdout_history_record_cap': 256, 'stdio_shared_history_record_cap': (1920 if flag in POSTERBOARD_LONG_WAIT_FLAGS else 1216 if flag in POSTERBOARD_WIDE_RECORD_FLAGS else 512), 'chosen_display_scale': 3})
                and pack['artifact_identity']['helper_protocol_run_id'] == TWO_DIR_REPORT_NONCE
                and nonce != TWO_DIR_REPORT_NONCE
                and pack['previous_root_sha256'] == (POSTERBOARD_RETURN_ROOT_SHA if flag in POSTERBOARD_LONG_WAIT_FLAGS else POSTERBOARD_ENTRY_ROOT_SHA if flag in (POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS) else POSTERBOARD_REPLY_ROOT_SHA if flag in (POSTERBOARD_OUTPUT_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS) else SERVICE_ROOT_SHA),
                'display scale, shared history, or inherited native policy differs')
    if flag in (CONTINUITY_FLAG, POSTERBOARD_FLAG, POSTERBOARD_REPLY_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS, POSTERBOARD_OUTPUT_FLAG):
        require(exact(proof, {'continuity_early_checkpoint_ms': 45000, 'continuity_first_checkpoint_memory_only': True, 'continuity_existing_page_and_context_preserved': flag not in POSTERBOARD_WIDE_RECORD_FLAGS, 'continuity_checkpoint_sequence_checked': True, 'continuity_selected_3x_ADT_unchanged': root_preserved}),
                'dual CPU display checkpoint contract differs')
    if flag in (POSTERBOARD_FLAG, POSTERBOARD_REPLY_FLAG, POSTERBOARD_TAIL_FLAG, POSTERBOARD_ENTRY_FLAG, POSTERBOARD_BITS_FLAG, *POSTERBOARD_WIDE_RECORD_FLAGS, POSTERBOARD_OUTPUT_FLAG):
        require(exact(proof, {'posterboard_exact_installed_launch_program': True, 'posterboard_first_native_lifecycle_same_process': True, 'posterboard_host_formatter_and_lifecycle_checked': True, 'posterboard_existing_base_and_context_preserved': flag not in POSTERBOARD_WIDE_RECORD_FLAGS, 'posterboard_no_userland_service_or_IPC_changes': True}),
                'PosterBoard lifecycle source or wire contract differs')
    if flag == POSTERBOARD_REPLY_FLAG:
        require(exact(proof, {'reply_root_only_ordinary_log_delta': True,
                              'reply_ADT_only_root_identity_changed': True,
                              'reply_native_only_identity_and_root_binding_changed': True,
                              'reply_installation_64_pages_verified': True,
                              'root_image_changed_helper_protocol_preserved': True}),
                'PosterBoard reply root and native binding differs')
        parity = proof['reply_native_parity']
        require(Path(parity['path']) == base.parent / 'posterboard-reply-native-parity.json'
                and sha(Path(parity['path'])) == parity['sha256']
                and load(Path(parity['path']))['only_identity_and_root_native_changes'] is True,
                'PosterBoard reply native source parity differs')
    if flag == POSTERBOARD_OUTPUT_FLAG:
        require(exact(proof, {'output_first_successful_PosterBoard_image': True,
                              'output_reexec_exit_revoke': True,
                              'output_post_native_copy_gate': True,
                              'output_machine_rows_excluded': True,
                              'output_source_checks_bound': True}),
                'PosterBoard ordinary-output source contract differs')
        parity = proof['output_native_parity']
        require(Path(parity['path']) == base.parent / 'posterboard-output-native-parity.json'
                and sha(Path(parity['path'])) == parity['sha256'], 'output native parity differs')
        binding = load(Path(parity['path']))
        require(exact(binding, {'only_bound_identity_output_selector_lifecycle_guards_and_prefix_changed': True,
                                'root_header_byte_identical': True, 'root_unchanged': True,
                                'source_owned_context_unchanged': True}), 'output delta extends native scope')
        for role, name in [('host_check', 'posterboard-output-host-check.json'),
                           ('decoder', 'inspect-userland-posterboard-output26.py'),
                           ('native_proof', 'observer-native-binding-proof.json')]:
            row = binding[role]
            require(Path(row['path']) == base.parent / name and sha(Path(row['path'])) == row['sha256'],
                    'output source check changed: ' + role)
    if flag == POSTERBOARD_TAIL_FLAG:
        require(exact(proof, {'output_first_successful_PosterBoard_image': True,
                              'output_reexec_exit_revoke': True,
                              'output_post_native_copy_gate': True,
                              'output_machine_rows_excluded': True,
                              'output_source_checks_bound': True,
                              'output_history_tail_selected': True,
                              'output_tail_fixed_capacity': True}),
                'PosterBoard ordinary-output source contract differs')
        parity = proof['output_native_parity']
        require(Path(parity['path']) == base.parent / 'posterboard-tail-native-parity.json'
                and sha(Path(parity['path'])) == parity['sha256'], 'output native parity differs')
        binding = load(Path(parity['path']))
        require(exact(binding, {'only_bound_identity_output_selector_lifecycle_guards_and_prefix_changed': True,
                                'root_header_byte_identical': True, 'root_unchanged': True,
                                'source_owned_context_unchanged': True}), 'output delta extends native scope')
        for role, name in [('host_check', 'posterboard-tail-host-check.json'),
                           ('decoder', 'inspect-userland-posterboard-tail26.py'),
                           ('native_proof', 'observer-native-binding-proof.json')]:
            row = binding[role]
            require(Path(row['path']) == base.parent / name and sha(Path(row['path'])) == row['sha256'],
                    'output source check changed: ' + role)
    if flag == POSTERBOARD_ENTRY_FLAG:
        require(exact(proof, {'entry_library_only_three_ordinary_logs': True,
                              'entry_native_only_identity_root_changed': True,
                              'entry_ADT_only_root_identity_changed': True,
                              'entry_installation_64_pages_verified': True,
                              'root_image_changed_helper_protocol_preserved': True,
                              'output_first_successful_PosterBoard_image': True,
                              'output_reexec_exit_revoke': True, 'output_post_native_copy_gate': True,
                              'output_machine_rows_excluded': True, 'output_source_checks_bound': True,
                              'output_history_tail_selected': True, 'output_tail_fixed_capacity': True}),
                'entry-marker source contract differs')
        binding = proof['entry_source_binding']
        require(Path(binding['path']) == base.parent / 'entry-trial-source-binding.json'
                and sha(Path(binding['path'])) == binding['sha256'], 'entry source binding changed')
        checks = load(Path(binding['path']))
        for role in ('native_parity', 'parent_host', 'library', 'decoder', 'native_proof'):
            row = checks[role]
            require(sha(Path(row['path'])) == row['sha256'], 'entry dependency changed: ' + role)
        require(Path(checks['native_parity']['path']) == base.parent / 'entry-native-parity.json'
                and exact(load(Path(checks['native_parity']['path'])),
                    {'only_record_identity_and_root_digest_changed': True,
                     'CPU_display_and_ordinary_output_observer_unchanged': True,
                     'root_sha256': root_sha}), 'entry native behavior changed')
        require(load(Path(checks['parent_host']['path']))['result'] == 'PASS'
                and load(Path(checks['library']['path']))['exact_source_restored_after_reversing_three_log_edits']
                and Path(checks['decoder']['path']) == path_of('record_decoder'), 'entry code checks differ')
    if flag == POSTERBOARD_BITS_FLAG:
        require(exact(proof, {'source_marker_bits_from_complete_sanitized_ordinary_lines_only': True,
                              'source_marker_bits_not_call_completion': True,
                              'source_marker_bits_exact_first_successful_image_only': True,
                              'source_marker_bits_capacity': 3, 'marker_root_and_ADT_unchanged': True,
                              'output_first_successful_PosterBoard_image': True,
                              'output_reexec_exit_revoke': True, 'output_post_native_copy_gate': True,
                              'output_machine_rows_excluded': True, 'output_source_checks_bound': True,
                              'output_history_tail_selected': True, 'output_tail_fixed_capacity': True}),
                'ordinary source-marker contract differs')
        binding = proof['bits_source_binding']
        require(Path(binding['path']) == base.parent / 'bits-trial-source-binding.json'
                and sha(Path(binding['path'])) == binding['sha256'], 'marker binding changed')
        checks = load(Path(binding['path']))
        names = {'source':'marker-source-binding.json','host':'posterboard-bits-host-check.json',
                 'integration':'bits-integration-check.json','parser':'sbstdio-parser-check.json',
                 'native':'observer-native-binding-proof.json','decoder':'inspect-userland-posterboard-bits26.py'}
        require(set(checks) == set(names), 'marker checks incomplete')
        for role, name in names.items():
            row = checks[role]
            require(Path(row['path']) == base.parent / name and sha(Path(row['path'])) == row['sha256'],
                    'marker dependency changed: ' + role)
            if role != 'decoder':
                require(load(Path(row['path']))['result'] == 'PASS', 'marker check failed: ' + role)
        require(exact(load(Path(checks['source']['path'])), {'root_headers_byte_identical': True,
                    'actual_installed_root_sha256': root_sha, 'ordinary_text_markers': 3})
                and exact(load(Path(checks['integration']['path'])),
                    {'actual_backend_to_snapshot_to_formatter_to_CRC_decoder': True,
                     'ordinary_marker_bits': 7, 'all_marker_texts_omitted_from_retained_tail': True}),
                'marker native/root/integration evidence differs')
    if flag == LSD_VFS_FLAG:
        binding = proof['lsd_vfs_source_binding']
        binding_path = base.parent/'lsd-vfs-trial-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'LaunchServices VFS source binding differs')
        checks = load(binding_path)
        sources = {
            'comparison': SB_PEER_BASE.parent/'boot-package/verified.json',
            'host': base.parent/'lsd-vfs-host-check.json',
            'root_audit': SB_PEER_BASE.parent/'lsd-root-and-ramfs-audit.json',
            'native': base.parent/'compile-result.json',
            'source_selection': base.parent/'source-selection.json',
            'decoder': path_of('record_decoder'),
            'previous_peer_binding': SB_PEER_BASE.parent/'sb-peer-trial-source-binding.json',
        }
        require(set(checks) == set(sources), 'LaunchServices VFS checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'LaunchServices VFS check changed: ' + role)
        host = load(sources['host'])
        require(exact(host, {'result': 'PASS', 'actual_candidate_collector_and_formatter': True,
                    'copy_budget': 512, 'full_history_split_count': 257, 'history_capacity_bytes': 1920,
                    'diagnostic_page_bytes': 4096, 'positive_formatter_cases': 339,
                    'rejected_malformed_lsd_records': 10})
                and 0 < host['maximum_fixture_base_bytes'] < 512
                and 0 < host['maximum_fixture_context_payload_bytes'] < 3520
                and exact(pack['lsd_vfs_host_check'], checks['host'])
                and exact(pack['lsd_root_ramfs_audit'], checks['root_audit']),
                'LaunchServices VFS formatter or read-only audit differs')
        comparison = load(sources['comparison'])
        native = load(sources['native'])
        source_inputs = load(sources['source_selection'])
        audit = load(sources['root_audit'])
        frames = proof['compiler_stack_frames']
        require(exact(pack['comparison_package'], checks['comparison'])
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and pack['root'] == comparison['root']
                and boot_args == comparison['boot_args']
                and all(pack['pins'][key]['sha256'] == comparison['pins'][key]['sha256'] for key in ('ADT','FD'))
                and exact(source_inputs, {'record_id': nonce, 'root_sha256': root_sha,
                                          'parent': str(SB_PEER_BASE.parent)})
                and exact(audit, {'result': 'PASS', 'read_only_mount': True,
                                  'media_device_access': False})
                and audit['image']['sha256'] == root_sha
                and exact(pack['link'], {'inputs': 1397, 'replaced': 6, 'undefined_symbols': 0})
                and {row['object'] for row in native['objects']} == {
                    'houji_recovery26.o','ZornHfsRoot26.cpo','ZornUfsOwner26.cpo','ZornUfsCore26.cpo',
                    'ZornPlatformRecordStart26.cpo','vfs_syscalls.o'}
                and 0 < frames['zorn_userland_progress_worker26'] < 8192
                and len(frames) == 6 and sum(frames.values()) < 8192,
                'LaunchServices VFS preserved storage, inputs or scheduler limits differ')
    elif flag == LSD_COPYLEN_FLAG:
        binding = proof['lsd_vfs_source_binding']
        binding_path = base.parent/'lsd-vfs-trial-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'LaunchServices copyinstr source binding differs')
        checks = load(binding_path)
        sources = {
            'comparison': SB_PEER_BASE.parent/'boot-package/verified.json',
            'host': base.parent/'lsd-vfs-host-check.json',
            'root_audit': SB_PEER_BASE.parent/'lsd-root-and-ramfs-audit.json',
            'native': base.parent/'compile-result.json',
            'source_selection': base.parent/'source-selection.json',
            'decoder': path_of('record_decoder'),
            'previous_peer_binding': SB_PEER_BASE.parent/'sb-peer-trial-source-binding.json',
            'copyinstr_proof': base.parent/'offline-lsd-vfs-verification.json',
        }
        require(set(checks) == set(sources), 'LaunchServices copyinstr checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'LaunchServices copyinstr check changed: ' + role)
        host = load(sources['host'])
        require(exact(host, {'result': 'PASS', 'actual_candidate_collector_and_formatter': True,
                    'concurrent_collector_threads': 4,
                    'copyinstr_length_output_required_and_written': True,
                    'previous_null_call_rejected': True,
                    'tested_scope_and_path_boundary': True,
                    'copy_budget': 512, 'full_history_split_count': 257, 'history_capacity_bytes': 1920,
                    'diagnostic_page_bytes': 4096, 'positive_formatter_cases': 339,
                    'rejected_malformed_lsd_records': 10})
                and 0 < host['maximum_fixture_base_bytes'] < 512
                and 0 < host['maximum_fixture_context_payload_bytes'] < 3520
                and exact(pack['lsd_vfs_host_check'], checks['host'])
                and exact(pack['lsd_root_ramfs_audit'], checks['root_audit'])
                and exact(pack['lsd_vfs_copyinstr_proof'], checks['copyinstr_proof']),
                'LaunchServices copyinstr formatter or read-only audit differs')
        copy_proof = load(sources['copyinstr_proof'])
        comparison = load(sources['comparison'])
        native = load(sources['native'])
        source_inputs = load(sources['source_selection'])
        audit = load(sources['root_audit'])
        frames = proof['compiler_stack_frames']
        prior = load(LSD_VFS_BASE/'trial/one-shot.claim.json')
        require(exact(prior, {'scope': LSD_VFS_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': '2deb82f0b18b02e6fe1a5b7e64b71a51494bf3412d792f8e6c443b429abb5bed',
                              'before_first_USB': True})
                and policy['scope'] != prior['scope']
                and expected['boot'] != prior['boot_sha256']
                and expected['kernel'] == 'd66f61b46b2cc25b21a1d33e022dc1b1f1dad2879297c2a34a19c0dafa9af37e'
                and expected['kernel'] != 'b0cf9d818c25daccd1d9994385b24ae4cbd6e2f98b97a9eafa3e221159609e05'
                and pack['device_ready'] is False
                and pack['phone_or_target_executed'] is False
                and pack['scope_or_claim_created'] is False
                and copy_proof['result'] == 'PASS'
                and copy_proof['candidate_copyinstr_length_output_nonnull'] is True
                and copy_proof['previous_null_copyinstr_fixture_reproduces_UBSan_rejection'] is True
                and copy_proof['concurrent_collector_host_fixture'] is True
                and copy_proof['bounded_absolute_path_categories'] is True
                and copy_proof['native_syscall_result_bitmaps'] is True
                and copy_proof['physical_device_access'] is False
                and copy_proof['record_id'] == nonce
                and copy_proof['root_sha256'] == root_sha
                and copy_proof['compiler_stack_frames']['zorn_userland_progress_worker26'] == 6176,
                'copyinstr length-output proof or consumed prior claim differs')
        require(exact(pack['comparison_package'], checks['comparison'])
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and pack['root'] == comparison['root']
                and boot_args == comparison['boot_args']
                and all(pack['pins'][key]['sha256'] == comparison['pins'][key]['sha256'] for key in ('ADT','FD'))
                and exact(source_inputs, {'record_id': nonce, 'root_sha256': root_sha,
                                          'parent': str(SB_PEER_BASE.parent)})
                and exact(audit, {'result': 'PASS', 'read_only_mount': True,
                                  'media_device_access': False})
                and audit['image']['sha256'] == root_sha
                and exact(pack['link'], {'inputs': 1397, 'replaced': 6, 'undefined_symbols': 0})
                and {row['object'] for row in native['objects']} == {
                    'houji_recovery26.o','ZornHfsRoot26.cpo','ZornUfsOwner26.cpo','ZornUfsCore26.cpo',
                    'ZornPlatformRecordStart26.cpo','vfs_syscalls.o'}
                and frames['zorn_userland_progress_worker26'] == 6176
                and len(frames) == 6 and sum(frames.values()) < 8192,
                'LaunchServices copyinstr preserved storage, inputs or scheduler limits differ')
    elif flag == LSD_BUDGET_FLAG:
        binding = proof['lsd_budget_source_binding']
        binding_path = base.parent/'lsd-vfs-budget-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'LaunchServices budget source binding differs')
        checks = load(binding_path)
        sources = {
            'comparison': Path(pack['comparison_package']['path']),
            'host': base.parent/'lsd-vfs-host-check.json',
            'root_audit': Path(pack['lsd_root_ramfs_audit']['path']),
            'native': base.parent/'compile-result.json',
            'source_selection': base.parent/'source-selection.json',
            'decoder': path_of('record_decoder'),
            'budget_proof': base.parent/'offline-lsd-vfs-verification.json',
        }
        require(set(checks) == set(sources), 'LaunchServices budget checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'LaunchServices budget check changed: ' + role)
        host = load(sources['host'])
        budget = load(sources['budget_proof'])
        require(exact(host, {'result': 'PASS', 'watched_prefix_budget_only': True,
                    'unclassified_paths_do_not_consume_budget': True,
                    'copyinstr_length_output_required_and_written': True,
                    'scripted_watched_reservations': 6, 'scripted_unclassified': 2,
                    'scripted_copy_errors': 2, 'budget_after_classified_flood': 512,
                    'unclassified_after_parallel_flood': 1202, 'diagnostic_header_bytes': 12,
                    'device_access': False})
                and exact(pack['lsd_vfs_host_check'], checks['host'])
                and budget['watched_reservations_taken_only_after_prefix_match'] is True
                and budget['template_directory_private_var_db_lsd_present'] is True
                and budget['single_stat_enoent_is_an_unspecified_child_path'] is True
                and budget['physical_device_access'] is False
                and budget['record_id'] == nonce,
                'LaunchServices watched-budget proof differs')
        frames = proof['compiler_stack_frames']
        prior = load(LSD_COPYLEN_BASE/'trial/one-shot.claim.json')
        require(exact(prior, {'scope': LSD_COPYLEN_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': '8cce968485462fd2a30e9b3c3d8d8e7b46c0ce23be7fb0824362003d1cdbfdc9', 'before_first_USB': True})
                and policy['scope'] != prior['scope']
                and expected['boot'] != prior['boot_sha256']
                and expected['kernel'] == '00c6cd11a5b03938a845509c8ed64b3814f60173b63ca6ccffa311e6d647fac0'
                and pack['device_ready'] is False and pack['phone_or_target_executed'] is False
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and exact(pack['link'], {'inputs': 1397, 'replaced': 6, 'undefined_symbols': 0})
                and frames['zorn_userland_progress_worker26'] == 6176,
                'watched-budget package reuses a consumed boot or changes more than the kernel')
    elif flag == LSD_PREFIX_FLAG:
        binding = proof['lsd_prefix_source_binding']
        binding_path = base.parent/'lsd-vfs-prefix-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'LaunchServices prefix source binding differs')
        checks = load(binding_path)
        sources = {
            'host': base.parent/'lsd-vfs-host-check.json',
            'decoder': path_of('record_decoder'),
            'prefix_proof': base.parent/'offline-lsd-vfs-verification.json',
            'native': base.parent/'compile-result.json',
        }
        require(set(checks) == set(sources), 'LaunchServices prefix checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'LaunchServices prefix check changed: ' + role)
        host = load(sources['host'])
        prefix = load(sources['prefix_proof'])
        require(exact(host, {'result': 'PASS', 'com_apple_lsd_prefix_distinct_from_var_db_lsd': True,
                    'diagnostic_header_bytes': 12, 'device_access': False})
                and exact(pack['lsd_vfs_host_check'], checks['host'])
                and prefix['installed_root_lacks_private_var_db_com_apple_lsd'] is True
                and prefix['watched_var_db_lsd_prefix_does_not_match_com_apple_lsd'] is True
                and prefix['physical_device_access'] is False
                and prefix['record_id'] == nonce,
                'LaunchServices com.apple.lsd prefix proof differs')
        frames = proof['compiler_stack_frames']
        prior = load(LSD_BUDGET_BASE/'trial/one-shot.claim.json')
        require(exact(prior, {'scope': LSD_BUDGET_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': '287962e818571736e21963360217922513c77776f0647374178661eae194f092', 'before_first_USB': True})
                and policy['scope'] != prior['scope']
                and expected['boot'] != prior['boot_sha256']
                and expected['kernel'] == '510082418f6660fb312d34b6da21d122929ce6bc6d7d81276415ce170fff2ffe'
                and pack['device_ready'] is False and pack['phone_or_target_executed'] is False
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and exact(pack['link'], {'inputs': 1397, 'replaced': 6, 'undefined_symbols': 0})
                and frames['zorn_userland_progress_worker26'] == 6176,
                'com.apple.lsd prefix package reuses a consumed boot or changes more than the kernel')
    elif flag == LSD_SUFFIX_FLAG:
        binding = proof['lsd_suffix_source_binding']
        binding_path = base.parent/'lsd-vfs-suffix-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'LaunchServices suffix source binding differs')
        checks = load(binding_path)
        sources = {
            'host': base.parent/'lsd-vfs-host-check.json',
            'decoder': path_of('record_decoder'),
            'suffix_proof': base.parent/'offline-lsd-vfs-verification.json',
            'native': base.parent/'compile-result.json',
        }
        require(set(checks) == set(sources), 'LaunchServices suffix checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'LaunchServices suffix check changed: ' + role)
        host = load(sources['host'])
        suffix = load(sources['suffix_proof'])
        require(exact(host, {'result': 'PASS', 'first_var_db_lsd_enoent_suffix_retained': True,
                    'later_suffix_not_overwritten': True,
                    'com_apple_lsd_prefix_not_stored_as_db_suffix': True, 'device_access': False})
                and exact(pack['lsd_vfs_host_check'], checks['host'])
                and suffix['suffix_budget_bytes'] == 31 and suffix['physical_device_access'] is False
                and suffix['record_id'] == nonce,
                'LaunchServices ENOENT suffix proof differs')
        frames = proof['compiler_stack_frames']
        prior = load(LSD_PREFIX_BASE/'trial/one-shot.claim.json')
        require(exact(prior, {'scope': LSD_PREFIX_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': 'd60000a5533c2a4e867f7ea74ae2b5d4aa1f072a5f3f22638fbc624e407bf377', 'before_first_USB': True})
                and policy['scope'] != prior['scope'] and expected['boot'] != prior['boot_sha256']
                and expected['kernel'] == '95cd68b4d0a71632035e735ae7a7281a3371ac1375b19f54d2e0c262956d17a0'
                and pack['device_ready'] is False and pack['phone_or_target_executed'] is False
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and exact(pack['link'], {'inputs': 1397, 'replaced': 6, 'undefined_symbols': 0})
                and frames['zorn_userland_progress_worker26'] == 6304,
                'ENOENT suffix package reuses a consumed boot or changes more than the kernel')
    elif flag == NETWORK_IDENTITY_FLAG:
        binding = proof['network_identity_source_binding']
        binding_path = base.parent/'network-identity-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'network identity source binding differs')
        checks = load(binding_path)
        sources = {
            'adt': base.parent/'adt-identity-check.json',
            'decoder': path_of('record_decoder'),
            'native': base.parent/'compile-result.json',
            'parent_package': LSD_SUFFIX_BASE.parent/'boot-package/verified.json',
        }
        require(set(checks) == set(sources), 'network identity checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'network identity check changed: ' + role)
        identity = load(sources['adt'])
        parent_pack = load(sources['parent_package'])
        require(exact(identity, {'result': 'PASS', 'removing_added_properties_restores_parent_bytes': True,
                    'locally_administered_unicast': True, 'factory_mac_claimed': False,
                    'network_driver_claimed': False, 'device_access': False,
                    'added_properties': ['/chosen/mac-address-wifi0', '/chosen/mac-address-bluetooth0',
                                         '/chosen/mac-address-ethernet0']})
                and identity['parent_adt']['sha256'] == parent_pack['pins']['ADT']['sha256'] == 'f79dcb8991000102081283863628e4b5b99ec449f84ceca0cf964df5a117dc1e'
                and identity['output']['sha256'] == expected['ADT'] == '7d0e29c1c4622df3a118be49ff7da01c6ebf8a5146d46712e260074921d9db2d'
                and len(set(identity['addresses'].values())) == 3
                and exact(pack['network_identity_ADT_check'], checks['adt'])
                and pack['pins']['FD']['sha256'] == parent_pack['pins']['FD']['sha256']
                and pack['boot_args'] == parent_pack['boot_args'] and pack['root'] == parent_pack['root'],
                'network identity ADT proof or preserved carrier differs')
        native = load(sources['native'])
        require(sorted(row['object'] for row in native['objects']) == sorted(
                    ['houji_recovery26.o', 'ZornHfsRoot26.cpo', 'ZornUfsOwner26.cpo', 'ZornUfsCore26.cpo',
                     'ZornPlatformRecordStart26.cpo'])
                and all(row['dependency_names_unchanged'] is True for row in native['objects']),
                'network identity kernel changes more than record identity')
        frames = proof['compiler_stack_frames']
        prior = load(LSD_SUFFIX_BASE/'trial/one-shot.claim.json')
        require(exact(prior, {'scope': LSD_SUFFIX_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': '71444f5a266a197009fe73ba80c7be747311d60f6756d83b4cfdad8a5457e6a9', 'before_first_USB': True})
                and policy['scope'] != prior['scope'] and expected['boot'] != prior['boot_sha256']
                and expected['kernel'] == 'dce060a80921ee7efca11e59a7ade920247905939695f4dc6bf1cd7305cb4d80'
                and pack['device_ready'] is False and pack['phone_or_target_executed'] is False
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho', 'EFI/UniXNU/Payloads/kernel.macho.adt']
                and pack['root_installation_this_trial'] is False
                and exact(pack['link'], {'inputs': 1397, 'replaced': 5, 'undefined_symbols': 0})
                and frames['zorn_userland_progress_worker26'] == 6304,
                'network identity package reuses a consumed boot or changes more than kernel identity and ADT')
    elif flag == LONG_WINDOW_FLAG:
        binding = proof['long_window_source_binding']
        binding_path = base.parent/'long-window-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'long window source binding differs')
        checks = load(binding_path)
        sources = {
            'decoder': path_of('record_decoder'),
            'native': base.parent/'compile-result.json',
            'watchdog': base.parents[3]/'source/os/ios26/cpu-long-window-6412899fa15647fab94a6530177d180f/ZornPlatformTrial26.c',
            'peer': base.parents[3]/'source/os/ios26/cpu-long-window-6412899fa15647fab94a6530177d180f/bsd_kern.c',
            'owner': base.parents[3]/'source/os/ios26/cpu-long-window-6412899fa15647fab94a6530177d180f/ZornUfsOwner26.cpp',
            'parent_package': NETWORK_IDENTITY_BASE.parent/'boot-package/verified.json',
            'adt': NETWORK_IDENTITY_BASE.parent/'adt-identity-check.json',
        }
        require(set(checks) == set(sources), 'long window checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'long window check changed: ' + role)
        parent_pack = load(sources['parent_package'])
        identity = load(sources['adt'])
        native = load(sources['native'])
        require(policy['trial_seconds'] == 1080 and policy['timeout_seconds'] == 1500
                and policy['userland_snapshot_seconds'] == 900
                and pack['timer_seconds'] == 1080 and pack['late_checkpoint_seconds'] == 900
                and pack['host_deadline_seconds'] == 1500
                and pack['boot_args'] == boot_args and 'zorn26_trial_seconds=1080' in boot_args
                and expected['ADT'] == parent_pack['pins']['ADT']['sha256'] == '7d0e29c1c4622df3a118be49ff7da01c6ebf8a5146d46712e260074921d9db2d'
                and pack['pins']['FD']['sha256'] == parent_pack['pins']['FD']['sha256']
                and pack['root'] == parent_pack['root']
                and identity['result'] == 'PASS' and identity['output']['sha256'] == expected['ADT']
                and sorted(row['object'] for row in native['objects']) == sorted(
                    ['houji_recovery26.o', 'ZornHfsRoot26.cpo', 'ZornUfsOwner26.cpo', 'ZornUfsCore26.cpo',
                     'ZornPlatformRecordStart26.cpo', 'bsd_kern.o', 'ZornPlatformTrial26.o']),
                'long window carrier, inherited ADT or kernel objects differ')
        frames = proof['compiler_stack_frames']
        prior = load(NETWORK_IDENTITY_BASE/'trial/one-shot.claim.json')
        require(exact(prior, {'scope': NETWORK_IDENTITY_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': '4bdd47113d264ae6fbb56726951d72048e1d042e6988a34460426fa14973ee82', 'before_first_USB': True})
                and policy['scope'] != prior['scope'] and expected['boot'] != prior['boot_sha256']
                and expected['kernel'] == '4ad42760b8780bd9ece6d0d69a4385462856cd2c2c0780c7fbe9fac157a65f8f'
                and pack['device_ready'] is False and pack['phone_or_target_executed'] is False
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho', 'EFI/UniXNU/unixnu.toml']
                and pack['root_installation_this_trial'] is False
                and exact(pack['link'], {'inputs': 1397, 'replaced': 7, 'undefined_symbols': 0})
                and frames['zorn_userland_progress_worker26'] == 6304,
                'long window package reuses a consumed boot or changes the root or ADT')
    elif flag == REPLY_DESTINATION_FLAG:
        binding = proof['reply_destination_source_binding']
        binding_path = base.parent/'reply-destination-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'reply destination source binding differs')
        checks = load(binding_path)
        sources = {
            'decoder': path_of('record_decoder'),
            'native': base.parent/'compile-result.json',
            'peer': base.parents[3]/'source/os/ios26/cpu-reply-destination-fe04d3023ec7420fba44e905a6e5c815/bsd_kern.c',
            'owner': base.parents[3]/'source/os/ios26/cpu-reply-destination-fe04d3023ec7420fba44e905a6e5c815/ZornUfsOwner26.cpp',
            'parent_package': LONG_WINDOW_BASE.parent/'boot-package/verified.json',
        }
        require(set(checks) == set(sources), 'reply destination checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'reply destination check changed: ' + role)
        parent_pack = load(sources['parent_package'])
        native = load(sources['native'])
        require(policy['trial_seconds'] == 300 and policy['timeout_seconds'] == 600
                and policy['userland_snapshot_seconds'] == 150
                and pack['timer_seconds'] == 300 and pack['late_checkpoint_seconds'] == 150
                and pack['host_deadline_seconds'] == 600
                and pack['boot_args'] == boot_args and 'zorn26_trial_seconds=300' in boot_args
                and '1080' not in boot_args
                and expected['ADT'] == parent_pack['pins']['ADT']['sha256'] == '7d0e29c1c4622df3a118be49ff7da01c6ebf8a5146d46712e260074921d9db2d'
                and pack['pins']['FD']['sha256'] == parent_pack['pins']['FD']['sha256']
                and pack['root'] == parent_pack['root']
                and sorted(row['object'] for row in native['objects']) == sorted(
                    ['houji_recovery26.o', 'ZornHfsRoot26.cpo', 'ZornUfsOwner26.cpo', 'ZornUfsCore26.cpo',
                     'ZornPlatformRecordStart26.cpo', 'bsd_kern.o']),
                'reply destination carrier, inherited ADT or kernel objects differ')
        frames = proof['compiler_stack_frames']
        prior = load(LONG_WINDOW_BASE/'trial/one-shot.claim.json')
        require(exact(prior, {'scope': LONG_WINDOW_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': 'e34e7ee098282b9142f727d9a4f64b2ae74ba257e6fb30298759e8bcb4058da6', 'before_first_USB': True})
                and policy['scope'] != prior['scope'] and expected['boot'] != prior['boot_sha256']
                and expected['kernel'] == 'a32691479a64fb3bc947cbeece37854bc406f862fcc4696759ed56af58302080'
                and pack['device_ready'] is False and pack['phone_or_target_executed'] is False
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho', 'EFI/UniXNU/unixnu.toml']
                and pack['root_installation_this_trial'] is False
                and exact(pack['link'], {'inputs': 1397, 'replaced': 6, 'undefined_symbols': 0})
                and frames['zorn_userland_progress_worker26'] == 6304,
                'reply destination package reuses a consumed boot or changes the root or ADT')
    elif flag == REPLY_HOLDER_FLAG:
        binding = proof['reply_holder_source_binding']
        binding_path = base.parent/'reply-holder-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'reply holder source binding differs')
        checks = load(binding_path)
        sources = {
            'decoder': path_of('record_decoder'),
            'native': base.parent/'compile-result.json',
            'peer': base.parents[3]/'source/os/ios26/cpu-reply-holder-babbbe2bb2af4b318f09b13049d760a6/bsd_kern.c',
            'owner': base.parents[3]/'source/os/ios26/cpu-reply-holder-babbbe2bb2af4b318f09b13049d760a6/ZornUfsOwner26.cpp',
            'parent_package': REPLY_DESTINATION_BASE.parent/'boot-package/verified.json',
        }
        require(set(checks) == set(sources), 'reply holder checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'reply holder check changed: ' + role)
        parent_pack = load(sources['parent_package'])
        native = load(sources['native'])
        require(policy['trial_seconds'] == 300 and policy['timeout_seconds'] == 600
                and policy['userland_snapshot_seconds'] == 150
                and pack['timer_seconds'] == 300 and pack['late_checkpoint_seconds'] == 150
                and pack['host_deadline_seconds'] == 600
                and pack['boot_args'] == boot_args and 'zorn26_trial_seconds=300' in boot_args
                and '1080' not in boot_args
                and expected['ADT'] == parent_pack['pins']['ADT']['sha256'] == '7d0e29c1c4622df3a118be49ff7da01c6ebf8a5146d46712e260074921d9db2d'
                and pack['pins']['FD']['sha256'] == parent_pack['pins']['FD']['sha256']
                and pack['root'] == parent_pack['root']
                and sorted(row['object'] for row in native['objects']) == sorted(
                    ['houji_recovery26.o', 'ZornHfsRoot26.cpo', 'ZornUfsOwner26.cpo', 'ZornUfsCore26.cpo',
                     'ZornPlatformRecordStart26.cpo', 'bsd_kern.o']),
                'reply holder carrier, inherited ADT or kernel objects differ')
        frames = proof['compiler_stack_frames']
        prior = load(REPLY_DESTINATION_BASE/'trial/one-shot.claim.json')
        require(exact(prior, {'scope': REPLY_DESTINATION_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': 'f330fb86c71d7494bb282956f692b60afdad0b95670fa190c895714f5673a5d9', 'before_first_USB': True})
                and policy['scope'] != prior['scope'] and expected['boot'] != prior['boot_sha256']
                and expected['kernel'] == '2a71ef64c5c7ab3d623d62a13799ffc02a2969aace99b41cfb6ffdf524789c45'
                and pack['device_ready'] is False and pack['phone_or_target_executed'] is False
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and exact(pack['link'], {'inputs': 1397, 'replaced': 6, 'undefined_symbols': 0})
                and frames['zorn_userland_progress_worker26'] == 6304,
                'reply holder package reuses a consumed boot or changes the root or ADT')
    elif flag == HOLDER_NAME_FLAG:
        binding = proof['holder_name_source_binding']
        binding_path = base.parent/'holder-name-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'holder name source binding differs')
        checks = load(binding_path)
        sources = {
            'decoder': path_of('record_decoder'),
            'native': base.parent/'compile-result.json',
            'peer': base.parents[3]/'source/os/ios26/cpu-holder-name-056afd15056746e8878c08f90daf35ad/bsd_kern.c',
            'owner': base.parents[3]/'source/os/ios26/cpu-holder-name-056afd15056746e8878c08f90daf35ad/ZornUfsOwner26.cpp',
            'parent_package': REPLY_HOLDER_BASE.parent/'boot-package/verified.json',
        }
        require(set(checks) == set(sources), 'holder name checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'holder name check changed: ' + role)
        parent_pack = load(sources['parent_package'])
        native = load(sources['native'])
        require(policy['trial_seconds'] == 300 and policy['timeout_seconds'] == 600
                and policy['userland_snapshot_seconds'] == 150
                and pack['timer_seconds'] == 300 and pack['late_checkpoint_seconds'] == 150
                and pack['host_deadline_seconds'] == 600
                and pack['boot_args'] == boot_args and 'zorn26_trial_seconds=300' in boot_args
                and '1080' not in boot_args
                and expected['ADT'] == parent_pack['pins']['ADT']['sha256'] == '7d0e29c1c4622df3a118be49ff7da01c6ebf8a5146d46712e260074921d9db2d'
                and pack['pins']['FD']['sha256'] == parent_pack['pins']['FD']['sha256']
                and pack['root'] == parent_pack['root']
                and sorted(row['object'] for row in native['objects']) == sorted(
                    ['houji_recovery26.o', 'ZornHfsRoot26.cpo', 'ZornUfsOwner26.cpo', 'ZornUfsCore26.cpo',
                     'ZornPlatformRecordStart26.cpo', 'bsd_kern.o']),
                'holder name carrier, inherited ADT or kernel objects differ')
        frames = proof['compiler_stack_frames']
        prior = load(REPLY_HOLDER_BASE/'trial/one-shot.claim.json')
        require(exact(prior, {'scope': REPLY_HOLDER_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': '05ab0ba700563e99a88b4d56f5c4282d3e3dea97f861424ec0316e503f363d6e', 'before_first_USB': True})
                and policy['scope'] != prior['scope'] and expected['boot'] != prior['boot_sha256']
                and expected['kernel'] == 'b49a6624986fc8a8a8405c235e49344c1625624f9a2a78463015e75f4b69c081'
                and pack['device_ready'] is False and pack['phone_or_target_executed'] is False
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and exact(pack['link'], {'inputs': 1397, 'replaced': 6, 'undefined_symbols': 0})
                and frames['zorn_userland_progress_worker26'] == 6304,
                'holder name package reuses a consumed boot or changes the root or ADT')
    elif flag == SERVICE_NAME_FLAG:
        binding = proof['service_name_source_binding']
        binding_path = base.parent/'service-name-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'service name source binding differs')
        checks = load(binding_path)
        sources = {
            'decoder': path_of('record_decoder'),
            'native': base.parent/'compile-result.json',
            'peer': base.parents[3]/'source/os/ios26/cpu-service-name-18a1c0e6ca834f38a1dc364094c73857/bsd_kern.c',
            'owner': base.parents[3]/'source/os/ios26/cpu-service-name-18a1c0e6ca834f38a1dc364094c73857/ZornUfsOwner26.cpp',
            'parent_package': HOLDER_NAME_BASE.parent/'boot-package/verified.json',
        }
        require(set(checks) == set(sources), 'service name checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'service name check changed: ' + role)
        parent_pack = load(sources['parent_package'])
        native = load(sources['native'])
        require(policy['trial_seconds'] == 300 and policy['timeout_seconds'] == 600
                and policy['userland_snapshot_seconds'] == 150
                and pack['timer_seconds'] == 300 and pack['late_checkpoint_seconds'] == 150
                and pack['host_deadline_seconds'] == 600
                and pack['boot_args'] == boot_args and 'zorn26_trial_seconds=300' in boot_args
                and '1080' not in boot_args
                and expected['ADT'] == parent_pack['pins']['ADT']['sha256'] == '7d0e29c1c4622df3a118be49ff7da01c6ebf8a5146d46712e260074921d9db2d'
                and pack['pins']['FD']['sha256'] == parent_pack['pins']['FD']['sha256']
                and pack['root'] == parent_pack['root']
                and sorted(row['object'] for row in native['objects']) == sorted(
                    ['houji_recovery26.o', 'ZornHfsRoot26.cpo', 'ZornUfsOwner26.cpo', 'ZornUfsCore26.cpo',
                     'ZornPlatformRecordStart26.cpo', 'bsd_kern.o']),
                'service name carrier, inherited ADT or kernel objects differ')
        frames = proof['compiler_stack_frames']
        prior = load(HOLDER_NAME_BASE/'trial/one-shot.claim.json')
        require(exact(prior, {'scope': HOLDER_NAME_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': 'b6840969609184bbfd559245e5c9335f415050a725dbcb39b0838d1f513abe1d', 'before_first_USB': True})
                and policy['scope'] != prior['scope'] and expected['boot'] != prior['boot_sha256']
                and expected['kernel'] == 'be86c6d55affa784fda2985f14bbcafc4ea1da40895f759798c731e6eddc1b4a'
                and pack['device_ready'] is False and pack['phone_or_target_executed'] is False
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and exact(pack['link'], {'inputs': 1397, 'replaced': 6, 'undefined_symbols': 0})
                and frames['zorn_userland_progress_worker26'] == 6336,
                'service name package reuses a consumed boot or changes the root or ADT')
    elif flag == KEYSTORE_FLAG:
        binding = proof['keystore_source_binding']
        binding_path = base.parent/'keystore-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'keystore source binding differs')
        checks = load(binding_path)
        sources = {
            'decoder': path_of('record_decoder'),
            'native': base.parent/'compile-result.json',
            'platform': base.parents[3]/'source/os/ios26/cpu-keystore-b6440b7e1376411db7adfa9a68bdf345/GenericARMPE.cpp',
            'owner': base.parents[3]/'source/os/ios26/cpu-keystore-b6440b7e1376411db7adfa9a68bdf345/ZornUfsOwner26.cpp',
            'parent_package': SERVICE_NAME_BASE.parent/'boot-package/verified.json',
        }
        require(set(checks) == set(sources), 'keystore checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'keystore check changed: ' + role)
        parent_pack = load(sources['parent_package'])
        native = load(sources['native'])
        require(policy['trial_seconds'] == 300 and policy['timeout_seconds'] == 600
                and policy['userland_snapshot_seconds'] == 150
                and pack['timer_seconds'] == 300 and pack['late_checkpoint_seconds'] == 150
                and pack['host_deadline_seconds'] == 600
                and pack['boot_args'] == boot_args and 'zorn26_trial_seconds=300' in boot_args
                and '1080' not in boot_args
                and expected['ADT'] == parent_pack['pins']['ADT']['sha256'] == '7d0e29c1c4622df3a118be49ff7da01c6ebf8a5146d46712e260074921d9db2d'
                and pack['pins']['FD']['sha256'] == parent_pack['pins']['FD']['sha256']
                and pack['root'] == parent_pack['root']
                and sorted(row['object'] for row in native['objects']) == sorted(
                    ['houji_recovery26.o', 'ZornHfsRoot26.cpo', 'ZornUfsOwner26.cpo', 'ZornUfsCore26.cpo',
                     'ZornPlatformRecordStart26.cpo', 'GenericARMPE.cpo']),
                'keystore carrier, inherited ADT or kernel objects differ')
        frames = proof['compiler_stack_frames']
        prior = load(SERVICE_NAME_BASE/'trial/one-shot.claim.json')
        require(exact(prior, {'scope': SERVICE_NAME_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': '2e102b2ccaf49c7d73fb3f04b2ab201ebcd7fa4f3c3b3e2f238df05549643b03', 'before_first_USB': True})
                and policy['scope'] != prior['scope'] and expected['boot'] != prior['boot_sha256']
                and expected['kernel'] == '31c1b11daec4dbe6043492253574916b07548a6fe7f61c8474ae7d56087abd60'
                and pack['device_ready'] is False and pack['phone_or_target_executed'] is False
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and exact(pack['link'], {'inputs': 1397, 'replaced': 6, 'undefined_symbols': 0})
                and frames['zorn_userland_progress_worker26'] == 6304,
                'keystore package reuses a consumed boot or changes the root or ADT')
    elif flag == KEYSTORE_RERUN_FLAG:
        binding = proof['keystore_source_binding']
        binding_path = base.parent/'keystore-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'keystore rerun source binding differs')
        checks = load(binding_path)
        sources = {
            'decoder': path_of('record_decoder'),
            'native': base.parent/'compile-result.json',
            'platform': base.parents[3]/'source/os/ios26/cpu-keystore-b6440b7e1376411db7adfa9a68bdf345/GenericARMPE.cpp',
            'owner': base.parents[3]/'source/os/ios26/cpu-keystore-b6440b7e1376411db7adfa9a68bdf345/ZornUfsOwner26.cpp',
            'parent_package': SERVICE_NAME_BASE.parent/'boot-package/verified.json',
        }
        require(set(checks) == set(sources), 'keystore rerun checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'keystore rerun check changed: ' + role)
        parent_pack = load(sources['parent_package'])
        native = load(sources['native'])
        require(policy['trial_seconds'] == 300 and policy['timeout_seconds'] == 600
                and policy['userland_snapshot_seconds'] == 150
                and pack['timer_seconds'] == 300 and pack['late_checkpoint_seconds'] == 150
                and pack['host_deadline_seconds'] == 600
                and pack['boot_args'] == boot_args and 'zorn26_trial_seconds=300' in boot_args
                and '1080' not in boot_args
                and expected['ADT'] == parent_pack['pins']['ADT']['sha256'] == '7d0e29c1c4622df3a118be49ff7da01c6ebf8a5146d46712e260074921d9db2d'
                and pack['pins']['FD']['sha256'] == parent_pack['pins']['FD']['sha256']
                and pack['root'] == parent_pack['root']
                and sorted(row['object'] for row in native['objects']) == sorted(
                    ['houji_recovery26.o', 'ZornHfsRoot26.cpo', 'ZornUfsOwner26.cpo', 'ZornUfsCore26.cpo',
                     'ZornPlatformRecordStart26.cpo', 'GenericARMPE.cpo']),
                'keystore rerun carrier, inherited ADT or kernel objects differ')
        frames = proof['compiler_stack_frames']
        first_run = load(KEYSTORE_BASE/'trial/one-shot.claim.json')
        require(exact(first_run, {'scope': KEYSTORE_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': '50a7e999e4de22196c96df6e53ab95be69fb4abfdc24b3da4831e50814662435', 'before_first_USB': True})
                and policy['scope'] != first_run['scope']
                and expected['boot'] == first_run['boot_sha256'] == '50a7e999e4de22196c96df6e53ab95be69fb4abfdc24b3da4831e50814662435'
                and expected['kernel'] == '31c1b11daec4dbe6043492253574916b07548a6fe7f61c8474ae7d56087abd60'
                and pack['device_ready'] is False and pack['phone_or_target_executed'] is False
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and exact(pack['link'], {'inputs': 1397, 'replaced': 6, 'undefined_symbols': 0})
                and frames['zorn_userland_progress_worker26'] == 6304,
                'keystore rerun reuses the consumed scope or changes the kernel, root or ADT')
    elif flag == KEYSTORE_RETAG_FLAG:
        binding = proof['keystore_retag_source_binding']
        binding_path = base.parent/'keystore-retag-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'keystore retag source binding differs')
        checks = load(binding_path)
        sources = {
            'decoder': path_of('record_decoder'),
            'native': base.parent/'compile-result.json',
            'platform': base.parents[3]/'source/os/ios26/cpu-keystore-b6440b7e1376411db7adfa9a68bdf345/GenericARMPE.cpp',
            'owner': base.parents[3]/'source/os/ios26/cpu-keystore-b6440b7e1376411db7adfa9a68bdf345/ZornUfsOwner26.cpp',
            'parent_package': KEYSTORE_BASE.parent/'boot-package/verified.json',
        }
        require(set(checks) == set(sources), 'keystore retag checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'keystore retag check changed: ' + role)
        parent_pack = load(sources['parent_package'])
        native = load(sources['native'])
        parent_native = load(KEYSTORE_BASE.parent/'compile-result.json')
        platform_object = next(row for row in parent_native['objects'] if row['object'] == 'GenericARMPE.cpo')
        require(policy['trial_seconds'] == 300 and policy['timeout_seconds'] == 600
                and policy['userland_snapshot_seconds'] == 150
                and pack['timer_seconds'] == 300 and pack['late_checkpoint_seconds'] == 150
                and pack['host_deadline_seconds'] == 600
                and pack['boot_args'] == boot_args and 'zorn26_trial_seconds=300' in boot_args
                and '1080' not in boot_args
                and expected['ADT'] == parent_pack['pins']['ADT']['sha256'] == '7d0e29c1c4622df3a118be49ff7da01c6ebf8a5146d46712e260074921d9db2d'
                and pack['pins']['FD']['sha256'] == parent_pack['pins']['FD']['sha256']
                and pack['root'] == parent_pack['root']
                and sorted(row['object'] for row in native['objects']) == sorted(
                    ['houji_recovery26.o', 'ZornHfsRoot26.cpo', 'ZornUfsOwner26.cpo', 'ZornUfsCore26.cpo',
                     'ZornPlatformRecordStart26.cpo'])
                and all(row['change'] == 'record identity tag only' for row in native['objects'])
                and native['inherited_platform']['sha256'] == platform_object['candidate']['sha256'],
                'keystore retag carrier, inherited ADT or kernel objects differ')
        frames = proof['compiler_stack_frames']
        first_run = load(KEYSTORE_BASE/'trial/one-shot.claim.json')
        refused = load(KEYSTORE_RERUN_BASE/'trial/one-shot.claim.json')
        require(exact(first_run, {'scope': KEYSTORE_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': '50a7e999e4de22196c96df6e53ab95be69fb4abfdc24b3da4831e50814662435', 'before_first_USB': True})
                and exact(refused, {'scope': KEYSTORE_RERUN_POLICY['scope'], 'status': 'consumed-no-repeat',
                              'boot_sha256': '50a7e999e4de22196c96df6e53ab95be69fb4abfdc24b3da4831e50814662435', 'before_first_USB': True})
                and policy['scope'] not in (first_run['scope'], refused['scope'])
                and expected['boot'] not in (first_run['boot_sha256'], refused['boot_sha256'])
                and expected['kernel'] == '9f6474ce789a8ac860417e3e7526ca5e241366c4dd7bd3c8b1731712c409a091'
                and parent_pack['pins']['kernel']['sha256'] == '31c1b11daec4dbe6043492253574916b07548a6fe7f61c8474ae7d56087abd60'
                and pack['device_ready'] is False and pack['phone_or_target_executed'] is False
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and exact(pack['link'], {'inputs': 1397, 'replaced': 5, 'undefined_symbols': 0})
                and frames['zorn_userland_progress_worker26'] == 6304
                and proof['record_identity_retag_only'] is True,
                'keystore retag reuses a consumed boot or changes the root, ADT or platform')
    elif flag == SB_PEER_FLAG:
        binding = proof['sb_peer_source_binding']
        binding_path = base.parent/'sb-peer-trial-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'SpringBoard Mach peer source binding differs')
        checks = load(binding_path)
        sources = {
            'comparison': SB_OWNER_BASE.parent/'boot-package/verified.json',
            'formatter': base.parent/'sb-peer-formatter-check.json',
            'owner': base.parent/'sb-peer-native-check.json',
            'native': base.parent/'compile-result.json',
            'source_selection': base.parent/'source-selection.json',
            'decoder': path_of('record_decoder'),
            'previous_owner_binding': SB_OWNER_BASE.parent/'sb-owner-trial-source-binding.json',
        }
        require(set(checks) == set(sources), 'SpringBoard Mach peer checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'SpringBoard Mach peer check changed: ' + role)
        formatter = load(sources['formatter'])
        require(exact(formatter, {'result': 'PASS', 'actual_candidate_formatter_and_packers': True,
                    'full_history_split_count': 257, 'history_capacity_bytes': 1920,
                    'diagnostic_page_bytes': 4096, 'positive_formatter_cases': 339,
                    'new_peer_refusals': 7})
                and 0 < formatter['maximum_fixture_base_bytes'] < 512
                and 0 < formatter['maximum_fixture_context_payload_bytes'] < 3520
                and exact(pack['sb_peer_formatter_check'], checks['formatter'])
                and exact(load(sources['owner']), {'result': 'PASS',
                    'native_reply_and_scheduler_source': True, 'native_cases': 22,
                    'balanced_native_refs_and_no_nested_port_or_scheduler_locks': True,
                    'sender_receiver_and_waiter_changes_checked': True})
                and exact(pack['sb_peer_native_check'], checks['owner']),
                'SpringBoard Mach peer formatter or native identity proof differs')
        comparison = load(sources['comparison'])
        native = load(sources['native'])
        source_inputs = load(sources['source_selection'])
        frames = proof['compiler_stack_frames']
        require(exact(pack['comparison_package'], checks['comparison'])
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and pack['root'] == comparison['root']
                and boot_args == comparison['boot_args']
                and all(pack['pins'][key]['sha256'] == comparison['pins'][key]['sha256'] for key in ('ADT','FD'))
                and exact(source_inputs, {'record_id': nonce, 'root_sha256': root_sha,
                                          'parent': str(SB_OWNER_BASE.parent)})
                and exact(pack['link'], {'inputs': 1397, 'replaced': 7, 'undefined_symbols': 0})
                and {row['object'] for row in native['objects']} == {
                    'houji_recovery26.o','ZornHfsRoot26.cpo','ZornUfsOwner26.cpo','ZornUfsCore26.cpo',
                    'ZornPlatformRecordStart26.cpo','kern_proc.o','bsd_kern.o'}
                and 0 < frames['zorn_userland_progress_worker26'] < 8192
                and len(frames) == 6 and sum(frames.values()) < 8192,
                'SpringBoard Mach peer preserved storage, inputs or scheduler limits differ')
    elif flag == SB_OWNER_FLAG:
        binding = proof['sb_owner_source_binding']
        binding_path = base.parent/'sb-owner-trial-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'SpringBoard lock owner source binding differs')
        checks = load(binding_path)
        sources = {
            'comparison': SB_ULOCK_BASE.parent/'boot-package/verified.json',
            'formatter': base.parent/'sb-owner-formatter-check.json',
            'owner': base.parent/'sb-owner-native-check.json',
            'native': base.parent/'compile-result.json',
            'source_selection': base.parent/'source-selection.json',
            'decoder': path_of('record_decoder'),
            'previous_ulock_binding': SB_ULOCK_BASE.parent/'sb-ulock-trial-source-binding.json',
        }
        require(set(checks) == set(sources), 'SpringBoard lock owner checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'SpringBoard lock owner check changed: ' + role)
        formatter = load(sources['formatter'])
        require(exact(formatter, {'result': 'PASS', 'actual_candidate_formatter_and_packers': True,
                    'full_history_split_count': 257, 'history_capacity_bytes': 1920,
                    'diagnostic_page_bytes': 4096, 'positive_formatter_cases': 325,
                    'new_owner_refusals': 7})
                and 0 < formatter['maximum_fixture_base_bytes'] < 512
                and 0 < formatter['maximum_fixture_context_payload_bytes'] < 3520
                and exact(pack['sb_owner_formatter_check'], checks['formatter'])
                and exact(load(sources['owner']), {'result': 'PASS',
                    'native_sampler_body': True, 'native_publisher_body': True, 'maximum_threads_examined': 32,
                    'balanced_refs_and_no_nested_scheduler_locks': True, 'waiter_rechecked': True,
                    'three_waiter_change_paths': True, 'owner_state_and_mach_sync_checked': True})
                and exact(pack['sb_owner_native_check'], checks['owner']),
                'SpringBoard lock owner formatter or native identity proof differs')
        comparison = load(sources['comparison'])
        native = load(sources['native'])
        source_inputs = load(sources['source_selection'])
        frames = proof['compiler_stack_frames']
        require(exact(pack['comparison_package'], checks['comparison'])
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and pack['root'] == comparison['root']
                and boot_args == comparison['boot_args']
                and all(pack['pins'][key]['sha256'] == comparison['pins'][key]['sha256'] for key in ('ADT','FD'))
                and exact(source_inputs, {'record_id': nonce, 'root_sha256': root_sha,
                                          'parent': str(SB_ULOCK_BASE.parent)})
                and exact(pack['link'], {'inputs': 1397, 'replaced': 8, 'undefined_symbols': 0})
                and {row['object'] for row in native['objects']} == {
                    'houji_recovery26.o','ZornHfsRoot26.cpo','ZornUfsOwner26.cpo','ZornUfsCore26.cpo',
                    'ZornPlatformRecordStart26.cpo','kern_proc.o','bsd_kern.o','sys_ulock.o'}
                and 0 < frames['zorn_userland_progress_worker26'] < 8192
                and len(frames) == 6 and sum(frames.values()) < 8192,
                'SpringBoard lock owner preserved storage, inputs or scheduler limits differ')
    elif flag == SB_ULOCK_FLAG:
        binding = proof['sb_ulock_source_binding']
        binding_path = base.parent/'sb-ulock-trial-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'SpringBoard ulock source binding differs')
        checks = load(binding_path)
        sources = {
            'comparison': UI_DISPLAY_WAIT_BASE.parent/'boot-package/verified.json',
            'formatter': base.parent/'sb-ulock-formatter-check.json',
            'owner': base.parent/'sb-ulock-owner-check.json',
            'native': base.parent/'compile-result.json',
            'source_selection': base.parent/'source-selection.json',
            'decoder': path_of('record_decoder'),
            'previous_ui_binding': UI_DISPLAY_WAIT_BASE.parent/'ui-display-trial-source-binding.json',
        }
        require(set(checks) == set(sources), 'SpringBoard ulock checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'SpringBoard ulock check changed: ' + role)
        formatter = load(sources['formatter'])
        require(exact(formatter, {'result': 'PASS', 'actual_candidate_formatter_and_packers': True,
                    'full_history_split_count': 257, 'history_capacity_bytes': 1920,
                    'diagnostic_page_bytes': 4096, 'positive_formatter_cases': 318,
                    'new_ulock_refusals': 8})
                and 0 < formatter['maximum_fixture_base_bytes'] < 512
                and 0 < formatter['maximum_fixture_context_payload_bytes'] < 3520
                and exact(pack['sb_ulock_formatter_check'], checks['formatter'])
                and exact(load(sources['owner']), {'result': 'PASS',
                    'native_helper_sequence_checked': True, 'waitq_admission_source_bound': True})
                and exact(pack['sb_ulock_owner_check'], checks['owner']),
                'SpringBoard ulock formatter or native identity proof differs')
        comparison = load(sources['comparison'])
        native = load(sources['native'])
        source_inputs = load(sources['source_selection'])
        frames = proof['compiler_stack_frames']
        require(exact(pack['comparison_package'], checks['comparison'])
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and pack['root'] == comparison['root']
                and boot_args == comparison['boot_args']
                and all(pack['pins'][key]['sha256'] == comparison['pins'][key]['sha256'] for key in ('ADT','FD'))
                and exact(source_inputs, {'record_id': nonce, 'root_sha256': root_sha,
                                          'parent': str(UI_DISPLAY_WAIT_BASE.parent)})
                and exact(pack['link'], {'inputs': 1397, 'replaced': 8, 'undefined_symbols': 0})
                and {row['object'] for row in native['objects']} == {
                    'houji_recovery26.o','ZornHfsRoot26.cpo','ZornUfsOwner26.cpo','ZornUfsCore26.cpo',
                    'ZornPlatformRecordStart26.cpo','kern_proc.o','bsd_kern.o','sys_ulock.o'}
                and 0 < frames['zorn_userland_progress_worker26'] < 8192
                and len(frames) == 6 and sum(frames.values()) < 8192,
                'SpringBoard ulock preserved storage, inputs or scheduler limits differ')
    elif flag == UI_DISPLAY_WAIT_FLAG:
        binding = proof['ui_display_source_binding']
        binding_path = base.parent/'ui-display-trial-source-binding.json'
        require(exact(binding, {'path': str(binding_path), 'sha256': sha(binding_path)}),
                'UI display source binding differs')
        checks = load(binding_path)
        sources = {
            'comparison': SB_BOOTARGS_BASE.parent/'boot-package/verified.json',
            'formatter': base.parent/'ui-display-formatter-check.json',
            'owner': base.parent/'ui-display-owner-check.json',
            'native': base.parent/'compile-result.json',
            'source_selection': base.parent/'source-selection.json',
            'decoder': path_of('record_decoder'),
            'original_context_io': SB_BOOTARGS_BASE.parent/'context-io-check.json',
            'source_gate': SB_WALLPAPER_CONTROL_BASE.parent/'source-gate-check.json',
        }
        require(set(checks) == set(sources), 'UI display checks incomplete')
        for role, source_path in sources.items():
            require(exact(checks[role], {'path': str(source_path), 'sha256': sha(source_path)}),
                    'UI display check changed: ' + role)
        formatter = load(sources['formatter'])
        require(exact(formatter, {'result': 'PASS', 'actual_candidate_formatter_and_packers': True,
                    'full_history_split_count': 257, 'history_capacity_bytes': 1920,
                    'diagnostic_page_bytes': 4096, 'positive_formatter_cases': 314,
                    'new_refusal_cases': 14})
                and 0 < formatter['maximum_fixture_base_bytes'] < 512
                and 0 < formatter['maximum_fixture_context_payload_bytes'] < 3520
                and exact(pack['ui_display_formatter_check'], checks['formatter'])
                and exact(load(sources['owner']), {'result': 'PASS', 'cases': 17,
                    'exact_native_census_wrapper': True, 'staged_first_client_publication': True,
                    'rejects_unpublished_wrong_pid_identity_reexec_shadow_and_exit': True,
                    'balances_proc_task_references': True})
                and exact(pack['ui_display_owner_check'], checks['owner']),
                'UI display formatter or native identity proof differs')
        comparison = load(sources['comparison'])
        gate = load(sources['source_gate'])
        io_proof = load(sources['original_context_io'])
        native = load(sources['native'])
        source_inputs = load(sources['source_selection'])
        frames = proof['compiler_stack_frames']
        require(exact(pack['comparison_package'], checks['comparison'])
                and exact(pack['source_gate_check'], checks['source_gate'])
                and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                and pack['root_installation_this_trial'] is False
                and pack['root'] == comparison['root']
                and boot_args == comparison['boot_args'] == gate['control_args']
                and all(pack['pins'][key]['sha256'] == comparison['pins'][key]['sha256'] for key in ('ADT','FD'))
                and exact(source_inputs, {'record_id': nonce, 'root_sha256': root_sha,
                                          'parent': str(SB_BOOTARGS_BASE.parent)})
                and exact(pack['link'], {'inputs': 1397, 'replaced': 7, 'undefined_symbols': 0})
                and {row['object'] for row in native['objects']} == {
                    'houji_recovery26.o','ZornHfsRoot26.cpo','ZornUfsOwner26.cpo','ZornUfsCore26.cpo',
                    'ZornPlatformRecordStart26.cpo','kern_proc.o','MiniIOMobileFramebuffer.cpo'}
                and exact(io_proof, {'result': 'PASS', 'context_bytes': 3552, 'context_offset': 544,
                    'native_single_4KiB_CDB_and_GPT_lock_health_once_guards_preserved': True})
                and frames['zorn_userland_progress_worker26'] == 6064
                and len(frames) == 5 and sum(frames.values()) < 8192,
                'UI display preserved storage, inputs or scheduler limits differ')
    elif flag in POSTERBOARD_LONG_WAIT_FLAGS:
        bootargs_observer = flag == SB_BOOTARGS_FLAG
        wallpaper_control = flag in (SB_WALLPAPER_CONTROL_FLAG, SB_BOOTARGS_FLAG)
        passive = flag != POSTERBOARD_WAIT_FLAG
        require(exact(proof, {
            'source_marker_bits_capacity': 5, 'marker_root_and_ADT_unchanged': flag != POSTERBOARD_PASSIVE_FLAG,
            'wide_existing_single_page_preserved': True, 'wide_source_history2048_unchanged': True,
            'wide_fixed_buffers_existing_once_gate': True, 'wide_native_stack_checked': True,
            'wide_actual_IO_header_bound': True, 'output_first_successful_PosterBoard_image': True,
            'output_reexec_exit_revoke': True, 'output_post_native_copy_gate': True,
            'output_machine_rows_excluded': True, 'output_history_tail_selected': True,
            'output_tail_fixed_capacity': True}), 'PosterBoard wait observation contract differs')
        binding = proof['posterboard_wait_source_binding']
        binding_path = base.parent / 'posterboard-wait-trial-source-binding.json'
        require(Path(binding['path']) == binding_path and sha(binding_path) == binding['sha256'],
                'PosterBoard wait source binding differs')
        checks = load(binding_path)
        source_name = ('posterboard-wallpaper-native-binding.json' if wallpaper_control
                       else 'posterboard-passive-native-binding.json' if passive
                       else 'posterboard-wait-native-binding.json')
        names = {'source':source_name, 'owner':'posterboard-wait-owner-check.json',
                 'parser':'sbstdio-parser-check.json','integration':'base64-integration-check.json',
                 'native':'observer-native-binding-proof.json','IO':'context-io-check.json',
                 'decoder':'inspect-userland-posterboard-wait-26.py'}
        if passive:
            names['library'] = 'passive-library-source.json'
        if wallpaper_control:
            names['wallpaper_gate'] = 'source-gate-check.json'
        if bootargs_observer:
            names['bootargs_host'] = 'sb-bootargs-host-check.json'
            names['stack'] = 'compiler-stack-usage.json'
        require(set(checks) == set(names), 'PosterBoard wait checks incomplete')
        results = {}
        for role, name in names.items():
            row = checks[role]
            directory = SB_WALLPAPER_CONTROL_BASE.parent if bootargs_observer and role == 'wallpaper_gate' else base.parent
            source_path = directory / name
            require(Path(row['path']) == source_path and sha(source_path) == row['sha256'],
                    'PosterBoard wait check changed: ' + role)
            if role != 'decoder':
                results[role] = load(source_path)
                if role == 'library':
                    require(exact(results[role], {'passive_delayed_report': True,
                        'native_build_and_SpringBoard_prewarm_unchanged': True,
                        'signature_verified': True}), 'PosterBoard passive library proof differs')
                else:
                    require(results[role]['result'] == 'PASS', 'PosterBoard wait check failed: ' + role)
        if wallpaper_control:
            gate = results['wallpaper_gate']
            parent = Path(pack['prior_package']['path'])
            require(parent == POSTERBOARD_PASSIVE_BASE.parent/'boot-package/verified-installed-root.json'
                    and sha(parent) == pack['prior_package']['sha256'],
                    'wallpaper control comparison package differs')
            parent_pack = load(parent)
            require(exact(gate, {'exact_springboard_fixes_body': True, 'only_bootarg_added': 'sb_wallpaper=0',
                                'base_args': parent_pack['boot_args'], 'control_args': boot_args,
                                'installed_root_sha256': root_sha,
                                'setup_and_activation_hook_calls_and_status_log_preserved': True})
                    and exact(pack['source_gate_check'], checks['wallpaper_gate'])
                    and pack['root_installation_this_trial'] is False
                    and boot_args == parent_pack['boot_args'] + ' sb_wallpaper=0'
                    and parent_pack['pins']['ADT']['sha256'] == expected['ADT']
                    and parent_pack['pins']['FD']['sha256'] == expected['fd'],
                    'wallpaper control source gate or preserved hardware inputs differ')
        root_identity = ({'root_digest_only_change_in_geometry': True, 'native_census_and_formatter_unchanged': True}
                         if passive else {'root_headers_byte_identical': True, 'ADT_byte_identical': True,
                                           'source_history_bytes': 2048, 'wait_checkpoint_seconds': [45, 150]})
        if wallpaper_control:
            root_identity = {'root_headers_byte_identical': True, 'ADT_byte_identical': True,
                             'record_identity_headers_only': True, 'native_census_and_formatter_unchanged': True}
        if bootargs_observer:
            reference = SB_WALLPAPER_CONTROL_BASE.parent/'boot-package/verified.json'
            require(exact(pack['comparison_package'], {'path': str(reference), 'sha256': sha(reference)})
                    and pack['same_boot_args_as_wallpaper_control'] is True
                    and pack['changed_FAT_members'] == ['EFI/UniXNU/Payloads/kernel.macho']
                    and load(reference)['boot_args'] == boot_args
                    and pack['root'] == load(reference)['root'],
                    'SpringBoard bootargs comparison carrier differs')
            require(exact(results['bootargs_host'], {'cases': 13, 'exact_userland_sysctl_body': True,
                              'original_native_returns_and_retry_preserved': True, 'read_probe_budget': 8,
                              'exact_source_markers': True, 'stderr_copy_budget': 96, 'existing_tail_bytes': 48})
                    and exact(pack['springboard_bootargs_host_check'], checks['bootargs_host'])
                    and exact(results['stack'], {'object_identical': True, 'worker_frame_bytes': 5472})
                    and exact(results['parser'], {'SpringBoard_bootargs_positive_cases': 3,
                                                   'SpringBoard_bootargs_refusal_cases': 8}),
                    'SpringBoard bootargs and source marker evidence differs')
            root_identity = {'root_headers_byte_identical': True, 'ADT_byte_identical': True,
                             'springboard_bootargs_observer_added': True, 'context_formatter_unchanged': True}
        require(exact(results['source'], root_identity | {
            'root_sha256': root_sha, 'physical_page_bytes': 4096, 'context_bytes': 3552,
            'history_pool_bytes': 1920, 'worker_frame_bytes': 5472 if bootargs_observer else 5424})
            and exact(results['owner'], {'modes': 14, 'exact_source_body': True})
            and exact(results['parser'], {'full_history_split_cases': 257, 'census_refusals': 6,
                                         'marker_mask_positive_cases': 31})
            and exact(results['IO'], {'context_bytes': 3552, 'context_offset': 544,
                     'native_single_4KiB_CDB_and_GPT_lock_health_once_guards_preserved': True}),
            'PosterBoard wait source, ownership or page proof differs')
    elif flag in POSTERBOARD_WIDE_RECORD_FLAGS:
        return_trial = flag == POSTERBOARD_RETURN_FLAG
        require(exact(proof, {'wide_existing_single_page_preserved': True,
                              'wide_source_history2048_unchanged': True,
                              'wide_fixed_buffers_existing_once_gate': True,
                              'wide_native_stack_checked': True, 'wide_actual_IO_header_bound': True,
                              'source_marker_bits_from_complete_sanitized_ordinary_lines_only': True,
                              'source_marker_bits_not_call_completion': True,
                              'source_marker_bits_exact_first_successful_image_only': True,
                              'source_marker_bits_capacity': 5 if return_trial else 3, 'marker_root_and_ADT_unchanged': not return_trial,
                              'output_first_successful_PosterBoard_image': True,
                              'output_reexec_exit_revoke': True, 'output_post_native_copy_gate': True,
                              'output_machine_rows_excluded': True, 'output_source_checks_bound': True,
                              'output_history_tail_selected': True, 'output_tail_fixed_capacity': True}),
                'wider ordinary log contract differs')
        binding = proof['wide_source_binding']
        require(Path(binding['path']) == base.parent / 'wide-trial-source-binding.json'
                and sha(Path(binding['path'])) == binding['sha256'], 'wide source binding changed')
        checks = load(Path(binding['path']))
        names = {'source':'wide-source-binding.json','host':'posterboard-wide-host-check.json',
                 'integration':'wide-integration-check.json','parser':'sbstdio-parser-check.json',
                 'native':'observer-native-binding-proof.json','IO':'context-io-check.json',
                 'native_IO':'actual-IO-native-binding.json','decoder':'inspect-userland-posterboard-wide26.py'}
        if return_trial:
            names.update(source='return-native-source-binding.json',
                         decoder='inspect-userland-posterboard-return26.py')
        require(set(checks) == set(names), 'wide checks incomplete')
        for role, name in names.items():
            row = checks[role]
            require(Path(row['path']) == base.parent / name and sha(Path(row['path'])) == row['sha256'],
                    'wide dependency changed: ' + role)
            if role != 'decoder':
                require(load(Path(row['path']))['result'] == 'PASS', 'wide check failed: ' + role)
        source = load(Path(checks['source']['path']))
        if return_trial:
            require(exact(source, {'only_root_digest_changed_in_geometry_headers': True,
                                   'old_worker_and_fixed_buffers_preserved': True,
                                   'checked_previous_stack_budget_preserved': True,
                                   'ordinary_message_count': 5}), 'return trial source or root window differs')
        else:
            require(exact(source, {'root_headers_byte_identical': True,
                                   'once_gate_64_threads_success_and_failure': True}), 'wide source ownership differs')
        require(exact(source, {'root_sha256': root_sha,
                    'source_history_bytes': 2048, 'record_history_pool_bytes': 1216,
                    'context_record_bytes': 3552, 'total_page_bytes': 4096,
                    'worker_frame_bytes': 7168, 'known_nested_observer_frames_bytes': 10736,
                    'kernel_stack_bytes': 16384})
                and exact(load(Path(checks['integration']['path'])),
                    {'actual_backend_to_snapshot_to_native_formatter_to_CRC_decoder': True,
                     'record_bytes': 4096, 'source_history_bytes': 2048, 'ordinary_marker_bits': 31 if return_trial else 7,
                     'physical_log_extent_unchanged': True, 'full_history_byte_identical': True})
                and exact(load(Path(checks['IO']['path'])),
                    {'context_bytes': 3552, 'context_offset': 544,
                     'native_single_4KiB_CDB_and_GPT_lock_health_once_guards_preserved': True})
                and load(Path(checks['native_IO']['path']))['byte_identical_to_actual1397_link_input'],
                'wide native,stack,root or single-page transport evidence differs')
    if flag == TOUCH_USERLAND_FLAG:
        require(exact(pack, dict(touch_frame_limit=64, touch_record_selected=False))
                and exact(proof, dict(touch_startup_selected=True, touch_record_selected=False,
                                      GPU_startup_selected=False)), 'finite FT3683 checkpoint composition differs')
    menu = tomllib.loads(path_of('menu').read_text())
    require(len(menu['entry']) == 1 and menu['entry'][0]['args'] == boot_args
            and not menu['boot']['connect_all'] and not menu['kits']['autoload'], 'bounded root menu differs')
    boot = path_of('boot').read_bytes()
    size, ramdisk = struct.unpack_from('<II', boot, 8)
    require(boot[:8] == b'ANDROID!' and struct.unpack_from('<I',boot,40)[0] == 4
            and ramdisk == 0 and len(boot) == 4096 + ((size+4095)&~4095), 'unexpected boot carrier')
    with gzip.GzipFile(fileobj=io.BytesIO(boot[4096:4096+size])) as image:
        payload = image.read(256*1024**2+1)
    fat = path_of('FAT').read_bytes()
    marker = b'ZORNGHWD' + struct.pack('<II', 1, 0xfffffffe)
    require(len(payload) <= 256*1024**2 and payload[56:60] == b'ARM\x64'
            and struct.unpack_from('<QQ', payload, 8) == (0xA7100000,len(payload))
            and payload[4096:] == path_of('fd').read_bytes()+fat
            and all(fat[i*512+0x180:i*512+0x190]==marker for i in (0,6)), 'shim/FD/FAT or watchdog differs')

    receipt = load(path_of('installed_result'))
    review = load(path_of('install_review'))
    install = load(path_of('install_admission'))
    claim = load(path_of('install_claim'))
    replay = load(path_of('local_replay'))
    require(exact(receipt,dict(scope=install_scope,installed=True,booted=False,pages_written=pages,
                protected_metadata_and_fences_unchanged=True,full_root_readback_performed=False,
                expected_image_sha256=root_sha))
            and receipt['readback']==dict(scope='written4KiB-root-pages-only',blocks=pages,bytes=pages*4096,
                sha256=replay['replay']['changed_page_readback_sha256'])
            and review['window']['new_root_sha256']==root_sha
            and review['pins']['local_replay']['sha256']==digest('local_replay')
            and exact(install,dict(scope=install_scope,review_sha256=digest('install_review'),
                runner_sha256=digest('previous_runner'),new_root_sha256=root_sha))
            and exact(claim,dict(scope=install_scope,admission_sha256=digest('install_admission'),
                consumed_before_first_USB=True,reusable=False)), 'installed root/receipt lineage differs')
    require(exact(load(path_of('host_adb_proof')),dict(adb_sha256=digest('adb_binary'),
                archive_sha1_matched=True)), 'host ADB proof differs')
    return bundle


def main():
    flags = [flag for flag in TRIAL_INPUTS if flag in sys.argv]
    require(len(flags) == 1, 'one exact display trial flag required')
    flag, = flags
    base, nonce, policy, _, _ = TRIAL_INPUTS[flag]
    root_sha, _, _ = root_lineage(flag)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(flag, type=Path, required=True, dest='bundle')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check-only', action='store_true')
    action.add_argument('--admission', type=Path)
    args = parser.parse_args()
    require(Path(sys.argv[0]).resolve() == RUNNER, 'fixed runner required')
    bundle = validate_bundle(args.bundle, flag)
    if args.check_only:
        print(json.dumps(dict(scope=policy['scope'], host_inputs_match=True, device_access=False)))
        return
    admission_path = base/'admission.json'
    claim = base/'trial/one-shot.claim.json'
    require(args.admission == admission_path and admission_path.resolve() == admission_path
            and not claim.exists() and not claim.is_symlink(), 'canonical fresh admission required')
    admission = load(admission_path)
    binding = dict(scope=policy['scope'],nonce=nonce,bundle_sha256=sha(args.bundle),
                   boot_sha256=bundle['pins']['boot']['sha256'],root_sha256=root_sha,allow_boot=True)
    require(exact(admission, policy | binding), 'admission policy differs')
    for role, state in [('owner','approved'),('ready','ready')]:
        p = base/(role+'.json')
        require(p.resolve()==p and admission[role]==dict(path=str(p),sha256=sha(p))
                and exact(load(p),binding | {state:True}), 'missing exact ' + role)
    current = load(CURRENT)
    gpu = current['gpu_discovery']
    expected_mode = 'attended-phone-connected' if flag in ATTENDED_FLAGS else 'unattended-phone-connected'
    require(not any(current.get(k) for k in ('active_run','active_build','active_admission','runner_session','stop_device_operations'))
            and not gpu.get('active_admission') and gpu.get('allow_boot') is False
            and gpu.get('current_mode')==expected_mode
            and gpu.get('current_phone_root_expected_sha256')==root_sha, 'phone mode/root/run changed')
    run(bundle, claim)
