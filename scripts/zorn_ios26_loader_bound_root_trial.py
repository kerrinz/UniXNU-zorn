"""Corrected-loader-ADT generation; reuses the reviewed one-shot trial core."""
from pathlib import Path
from zorn_ios26_installed_root_trial import main
SPEC = dict(scope='single-K80-ios26-loader-bound-UFS-root300s-bounded-recovery',
            directory='k80-loader-bound-root-trial26-20261110',
            flag='--ios26-loader-bound-root-trial', entry=str(Path(__file__).resolve()),
            fat_sha256='728579af93b059f2a459eb164af9e0f3f75665515a675f81bcbae3dd633712fa',
            adt_sha256='7fdd32a78ea44ac5bce8dedc9ffa34dd684ee73e8623e193c095093fc222bb49',
            nonce='a643f048e0e74a17a8249ed848714c89')
def entry():
    main(SPEC)
if __name__ == '__main__':
    entry()
