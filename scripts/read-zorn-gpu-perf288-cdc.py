#!/usr/bin/env python3
"""Receive the exact288 bounded trial; fixed installed-root validation first."""
import zorn_ios26_gpu_v288_system_trial as trial
from zorn_ios26_perf288_receiver import run_capture

if __name__ == '__main__':
    raise SystemExit(run_capture(trial))
