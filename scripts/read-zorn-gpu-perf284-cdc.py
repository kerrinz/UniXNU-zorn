#!/usr/bin/env python3
"""Receive the exact284 bounded trial; fixed installed-root validation first."""
import zorn_ios26_gpu_v284_system_trial as trial
from zorn_ios26_perf284_receiver import run_capture

if __name__ == '__main__':
    raise SystemExit(run_capture(trial))
