#!/usr/bin/env python3
"""Fixed CDC receiver entry for the single bounded302 presenter-unlock trial."""
import zorn_ios26_gpu_v302_system_trial as trial
from zorn_ios26_ctx302_receiver import run_capture

if __name__ == '__main__':
    raise SystemExit(run_capture(trial))
