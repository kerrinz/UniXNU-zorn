#!/usr/bin/env python3
"""Capture the fixed K80 CDC trial on macOS and verify its boot marker."""

import array
import fcntl
import json
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import termios
from threading import Event, Thread
import time

PRODUCT = "Redmi K80 XNU CDC"


def find_port(registry, identity):
    if not all(re.search(rf'"{key}" = {value}$', registry, re.M)
               for key, value in (("idVendor", 0x1209), ("idProduct", 1))):
        return None
    serials = set(re.findall(r'"USB Serial Number" = "([^"]+)"$', registry, re.M))
    ports = set(re.findall(r'"IOCalloutDevice" = "(/dev/cu\.usbmodem[A-Za-z0-9._-]+)"$',
                           registry, re.M))
    if serials != {identity} or len(ports) != 1:
        return None
    return ports.pop()


def capture(port, output, stop, deadline):
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        fcntl.ioctl(fd, termios.TIOCEXCL)
        original = termios.tcgetattr(fd)
        attrs = termios.tcgetattr(fd)
        attrs[:6] = [0, 0, termios.CS8 | termios.CREAD | termios.CLOCAL, 0,
                     termios.B115200, termios.B115200]
        attrs[6][termios.VMIN] = 1
        attrs[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        try:
            fcntl.ioctl(fd, termios.TIOCMBIS, array.array("i", [termios.TIOCM_DTR]))
            with output.open("xb") as stream:
                while not stop.is_set() and time.monotonic() < deadline:
                    ready, _, _ = select.select([fd], [], [], 0.25)
                    if not ready:
                        continue
                    try:
                        chunk = os.read(fd, 4096)
                    except BlockingIOError:
                        continue
                    except OSError as error:
                        if error.errno in (5, 6):
                            break
                        raise
                    if not chunk:
                        break
                    if stream.tell() + len(chunk) > 65536:
                        raise ValueError("unexpected CDC data volume")
                    stream.write(chunk)
                    stream.flush()
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSANOW, original)
            except (OSError, termios.error):
                pass  # The device may already have detached.
    finally:
        os.close(fd)


def main():
    from zorn_ios26_gpu_v161_mmu_readback_trial import TAG, TRIAL, validate

    bundle = TRIAL / "bundle.json"
    validate(bundle)
    out = TRIAL / "trial"
    raw = out / "cdc.raw"
    report = out / "cdc-capture.json"
    if any(path.exists() or path.is_symlink()
           for path in (raw, report, out / "one-shot.claim.json")):
        raise ValueError("CDC trial has existing evidence or a claim")
    stop, polling = Event(), Event()
    errors, ports = [], []

    def receive():
        deadline = time.monotonic() + 610
        identity = "ZORN26" + TAG[:12].upper()
        try:
            while not stop.is_set() and time.monotonic() < deadline:
                result = subprocess.run(
                    ["/usr/sbin/ioreg", "-r", "-n", PRODUCT, "-l", "-w0"],
                    text=True, timeout=3, capture_output=True, check=False,
                )
                polling.set()
                port = find_port(result.stdout, identity) if result.returncode == 0 else None
                if port:
                    ports.append(port)
                    capture(port, raw, stop, deadline)
                    return
                stop.wait(0.25)
        except (OSError, subprocess.SubprocessError, ValueError, termios.error) as error:
            errors.append(str(error))
        finally:
            polling.set()

    receiver = Thread(target=receive)
    receiver.start()
    try:
        if not polling.wait(5) or errors:
            raise RuntimeError("CDC listener could not start")
        result = subprocess.run(
            [sys.executable, "-B", str(Path(__file__).with_name("zorn_ios26_gpu_v161_mmu_readback_trial.py")),
             "--bundle", str(bundle), "--admission", str(TRIAL / "admission.json")],
            check=False,
        )
    finally:
        stop.set()
        receiver.join()

    run_file = out / "run.json"
    run = json.loads(run_file.read_text()) if run_file.is_file() else {}
    data = raw.read_bytes() if raw.is_file() else b""
    received = False
    smr_stage = None
    scm_return = None
    irq_readback = None
    qos_readback = None
    armed_mask = None
    cm3 = None
    pdc = None
    hfi = None
    query = None
    perf = None
    bw = None
    core = None
    dcvs = None
    tables = None
    preflight = None
    actlr = None
    contexts = None
    if result.returncode == 0 and run.get("recovery_identity_after", {}).get("family"):
        from inspect_ios26_lockscreen_touch_cpu_record import inspect_envelope
        try:
            record = inspect_envelope((out / "after-log.bin").read_bytes(), bytes.fromhex(TAG),
                                      (out / "before-log.bin").read_bytes())
            _, separator, gpu = record["text"].rpartition("; gpu=")
            if separator:
                prefix = f"K80 GPU CDC {TAG} gpu={gpu},m=".encode("ascii")
                match = re.fullmatch(re.escape(prefix) + rb"(6[34]|5[0-6]|4[0-9]|3[0-9]|2[0-9]|1[0-9]|[0-9])(?:,s=([0-9a-f]{16}))?(?:,j=([0-9a-f]{16}))?(?:,q=([0-9a-f]{8}))?(?:,a=([0-3]))?(?:,c=([0-9a-f]{8}))?(?:,p=([0-9a-f]{8}))?(?:,h=([0-9a-f]{8}))?(?:,e=([0-9a-f]{8}(?:/[0-9a-f]{8}){4}))?(?:,f=([0-9a-f]{8}(?:/[0-9a-f]{8}){4}))?(?:,b=([0-9a-f]{8}(?:/[0-9a-f]{8}){4}))?(?:,k=([0-9a-f]{8}(?:/[0-9a-f]{8}){3}))?(?:,d=([0-9a-f]{8}(?:/[0-9a-f]{8}){4}))?(?:,v=([0-9a-f]{8}))?(?:,w=([0-9a-f]{8}))?(?:,x=([0-9a-f]{8})/([0-9a-f]{8}),y=([0-9a-f]{8})/([0-9a-f]{8}))?\r\n", data)
                if match:
                    smr_stage = int(match[1])
                    scm_return = int(match[2], 16) if match[2] else None
                    irq_readback = int(match[3], 16) if match[3] else None
                    qos_readback = int(match[4], 16) if match[4] else None
                    armed_mask = int(match[5], 16) if match[5] else None
                    cm3 = int(match[6],16) if match[6] else None
                    pdc = int(match[7],16) if match[7] else None
                    hfi = int(match[8],16) if match[8] else None
                    query = [int(word,16) for word in match[9].split(b"/")] if match[9] else None
                    perf = [int(word,16) for word in match[10].split(b"/")] if match[10] else None
                    bw = [int(word,16) for word in match[11].split(b"/")] if match[11] else None
                    core = [int(word,16) for word in match[12].split(b"/")] if match[12] else None
                    dcvs = [int(word,16) for word in match[13].split(b"/")] if match[13] else None
                    tables = int(match[14],16) if match[14] else None
                    preflight = int(match[15],16) if match[15] else None
                    actlr = [int(match[i],16) for i in (16,17)] if match[16] else None
                    contexts = [int(match[i],16) for i in (18,19)] if match[18] else None
                    s2cr = run.get("reset_observation") or {}
                    received = bool(s2cr.get("s2cr_complete")) == bool(smr_stage)
        except (OSError, ValueError) as error:
            errors.append(str(error))
    if received and ((scm_return is not None) != (smr_stage >= 19) or
                     (smr_stage >= 20 and scm_return != 0)):
        errors.append("SCM completion and returned status disagree")
    if received and ((irq_readback is not None) != (smr_stage >= 21)):
        errors.append("missing or unexpected GIC readback")
    if received and ((qos_readback is not None) != (smr_stage >= 31) or
                     (smr_stage >= 32 and qos_readback != 0xffffffff)):
        errors.append("QoS stage and observed port masks disagree")
    if received and ((armed_mask is not None) != (smr_stage >= 33) or
                     (smr_stage >= 34 and armed_mask != 3)):
        errors.append("GMU IRQ stage and checked enables disagree")
    if received and ((cm3 is not None) != (smr_stage >= 37) or
                     (smr_stage >= 38 and cm3 != 0xf0000100)):
        errors.append("CM3 stage and init result disagree")
    if received and ((pdc is not None) != (smr_stage >= 39) or
                     (smr_stage >= 40 and pdc != 0xc3130000)):
        errors.append("PDC/RSC stage and source store record disagree")
    if received and ((hfi is not None) != (smr_stage >= 41) or
                     (smr_stage >= 42 and (hfi & 0xffff0001) != 0xe0000001)):
        errors.append("HFI stage and control register record disagree")
    if received and ((query is not None) != (smr_stage >= 43) or
                     (smr_stage >= 44 and ((query[0] & 0xff000000) != 0x82000000 or
                      (query[2] & ~(1 << 19)) != 0x0010030c))):
        errors.append("HFI query stage and returned ACK disagree")
    if received and ((perf is not None) != (smr_stage >= 45) or
                     (smr_stage >= 46 and (perf[0] or (perf[1] >> 8) not in (0x0f3402,0x043b02) or
                      (perf[2] & ~(1 << 19)) != 0x00200000 | ((perf[1] >> 8) & 0xff00) | (perf[1] >> 24) or perf[3]))):
        errors.append("HFI PERF stage and returned ACK disagree")
    if received and ((bw is not None) != (smr_stage >= 47) or
                     (smr_stage >= 48 and (bw[0] or (bw[1] >> 8) != 0x03a002 or
                      (bw[2] & ~(1 << 19)) != 0x0030a003 or bw[3]))):
        errors.append("HFI bandwidth stage and returned ACK disagree")
    if received and ((core is not None) != (smr_stage >= 49) or
                     (smr_stage >= 50 and (any(word >> 24 != (i+1)*16+2
                        for i,word in enumerate(core[:3])) or
                        (core[3] & ~(1 << 19)) != 0x0060020e))):
        errors.append("HFI core stage and returned ACKs disagree")
    if received and ((dcvs is not None) != (smr_stage >= 51) or
                     (smr_stage >= 52 and (any(word >> 24 != 2 for word in dcvs[:3]) or
                        (dcvs[3] & ~(1 << 19)) != 0x0090030c or dcvs[4] not in (0,1)))):
        errors.append("HFI DCVS stage and returned ACKs disagree")
    if received and ((tables is not None) != (smr_stage >= 53) or
                     (smr_stage >= 54 and tables != 0x07000000)):
        errors.append("Native GPU table stage and returned results disagree")
    if received and ((preflight is not None) != (smr_stage >= 55) or
                     (smr_stage >= 55 and ((smr_stage == 56 and preflight != 0x1f000000) or (smr_stage == 64) != (preflight == 0xff000000)))):
        errors.append("SMMU preflight stage and returned results disagree")
    if received and ((actlr is not None) != (smr_stage >= 63) or
                     (smr_stage == 64 and actlr != [0x7000032b, 0x7000032b])):
        errors.append("ACTLR stage and USER/LPAC observations disagree")
    verified = received and not errors
    verdict = dict(verified=verified, marker_received=received, port=ports[0] if ports else None,
                   smr_stage=smr_stage, smr_valid_readback=(smr_stage is not None and smr_stage >= 7),
                   tcm_readback=(smr_stage is not None and smr_stage >= 10),
                   board_tcm_handoff=(smr_stage is not None and smr_stage >= 13),
                   cx_metadata_ready=(smr_stage is not None and smr_stage >= 16),
                   cx_scm_complete=(smr_stage is not None and smr_stage >= 20),
                   gmu_irq_and_config=(smr_stage is not None and smr_stage >= 24),
                   direct_hfi_receiver_bound=(smr_stage is not None and smr_stage >= 26),
                   gpu_icc_inputs_bound=(smr_stage is not None and smr_stage >= 28),
                   gpu_icc_initial_votes_complete=(smr_stage is not None and smr_stage >= 30),
                   qos_ports_observed=(qos_readback >> 16 if qos_readback is not None else None),
                   qos_ports_matching=(qos_readback & 0xffff if qos_readback is not None else None),
                   qos_ready=(smr_stage is not None and smr_stage >= 32),
                   gmu_spi_readback=irq_readback,
                   checked_irq_enable_mask=armed_mask,
                   hfi_control_observation=hfi, hfi_control_initialized=(smr_stage is not None and smr_stage >= 42),
                   hfi_query_observation=query, hfi_query_acknowledged=(smr_stage is not None and smr_stage >= 44),
                   hfi_perf_observation=perf, hfi_perf_acknowledged=(smr_stage is not None and smr_stage >= 46),
                   hfi_bw_observation=bw, hfi_bw_acknowledged=(smr_stage is not None and smr_stage >= 48),
                   hfi_core_observation=core, hfi_core_acknowledged=(smr_stage is not None and smr_stage >= 50),
                   hfi_dcvs_observation=dcvs, hfi_dcvs_acknowledged=(smr_stage is not None and smr_stage >= 52),
                   gpu_tables_observation=tables, gpu_tables_prepared=(smr_stage is not None and smr_stage >= 54),
                   host_actlr_observations=actlr, host_context_observations=contexts,
                   host_mmu_preflight_observation=preflight, host_mmu_preflight_complete=(smr_stage in (56,63,64)), host_context_programming_complete=(smr_stage == 64),
                   cm3_observation=cm3, cm3_initialized=(smr_stage is not None and smr_stage >= 38),
                   pdc_rsc_observation=pdc, pdc_rsc_stores_complete=(smr_stage is not None and smr_stage >= 40),
                   bootstrap_bandwidth_complete=(smr_stage is not None and smr_stage >= 36),
                   cx_scm_raw_return_available=(scm_return is not None),
                   cx_scm_raw_return=scm_return,
                   bytes=len(data), runner_exit=result.returncode, errors=errors)
    with report.open("x") as stream:
        json.dump(verdict, stream, indent=2)
        stream.write("\n")
    print(json.dumps(verdict))
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
