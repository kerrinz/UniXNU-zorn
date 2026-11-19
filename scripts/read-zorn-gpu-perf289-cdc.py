#!/usr/bin/env python3
"""Receive the exact289 bounded trial; fixed installed-root validation first."""
import zorn_ios26_gpu_v289_system_trial as trial
from zorn_ios26_perf289_receiver import run_capture

if __name__ == '__main__':
    raise SystemExit(run_capture(trial))
