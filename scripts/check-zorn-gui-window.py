#!/usr/bin/env python3
"""Check the actual GUI schedule and absolute watchdog-pet deadline with host stubs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "out/zorn/gui-window-host-checks.json")
    args = parser.parse_args()
    native = (ROOT / "UniXNU-zorn/native/ufs-read/ZornUfsRead.cpp").read_text()
    begin = native.index('extern "C" void zorn_ufs_gui_hold_tick(void)')
    at = native.index("{", begin) + 1
    depth = 1
    while depth:
        depth += (native[at] == "{") - (native[at] == "}")
        at += 1
    helper = native[begin:at]
    init = next(line.strip() for line in native.splitlines() if "gGuiHoldSeconds = gGuiWatch &&" in line)
    observer = (ROOT / "UniXNU/out/zorn/tree/.cache/xnu-work/bsd/kern/bsd_init.c").read_text()
    begin = observer.index("\tunsigned period = hold > 900")
    end = observer.index("\tfor (unsigned sample =", begin)
    schedule = observer[begin:end]
    harness = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
static bool gGuiWatch, gLogArmed, gWatchdogArmed;
static unsigned gGuiHoldSeconds, gWatchdogMode;
static uint64_t gTraceEpoch, now;
static unsigned pets, words;
static uint64_t result;
static uint64_t mach_absolute_time() { return now; }
static void absolutetime_to_nanoseconds(uint64_t ticks, uint64_t *ns) { *ns = ticks; }
struct Result { uint64_t status; };
static Result zorn_wdt_call(uint64_t id, uint64_t a, uint64_t b) {
    assert(id == 0x86000007U && !a && !b); ++pets; return {result};
}
static void zorn_ufs_log_word(const char *word) {
    assert(!strcmp(word, result ? "GHOLDERR" : "GHOLDOK")); ++words;
}
@HELPER@
static void reset(int guiHold) {
    gGuiWatch = gLogArmed = gWatchdogArmed = true;
    gWatchdogMode = 1; gTraceEpoch = 100; now = 100;
    pets = words = 0; result = 0;
    @INIT@
}
struct Schedule { unsigned period, limit; };
static Schedule inspect(unsigned hold) {
@SCHEDULE@
    return {period, sample_limit};
}
int main() {
    for (int hold = 0; hold <= 2200; ++hold) {
        reset(hold);
        const bool valid = hold >= 30 && hold <= 1800;
        assert(gGuiHoldSeconds == (valid ? unsigned(hold) : 0));
        Schedule s = inspect(hold);
        assert(s.limit >= 1 && s.limit <= 60 && s.period < 55);
        assert(pets == unsigned(hold > 900 && hold <= 1800));
        assert(words == pets);
        if (hold <= 900 || hold > 1800) assert(s.period == 15);
        else assert(s.period == 30 && s.limit * s.period >= unsigned(hold));
        if (!valid) continue;
        pets = words = 0;
        now = gTraceEpoch + uint64_t(hold) * 1000000000ULL - 1;
        zorn_ufs_gui_hold_tick(); assert(pets == 1 && words == 1);
        now += 1;
        zorn_ufs_gui_hold_tick(); assert(pets == 1 && words == 1);
        now += 1000000000000ULL;
        zorn_ufs_gui_hold_tick(); assert(pets == 1 && words == 1);
    }
    reset(-1); assert(gGuiHoldSeconds == 0);
    reset(1800); gGuiHoldSeconds = 0; zorn_ufs_gui_hold_tick(); assert(!pets);
    reset(1800); gLogArmed = false; zorn_ufs_gui_hold_tick(); assert(!pets);
    reset(1800); gWatchdogArmed = false; zorn_ufs_gui_hold_tick(); assert(!pets);
    reset(1800); gWatchdogMode = 2; zorn_ufs_gui_hold_tick(); assert(!pets);
    reset(1800); result = 1; zorn_ufs_gui_hold_tick(); assert(pets == 1 && words == 1);
}
'''.replace("@HELPER@", helper).replace("@INIT@", init).replace("@SCHEDULE@", schedule)
    with tempfile.TemporaryDirectory(prefix="zorn-gui-window-") as directory:
        cpp = Path(directory) / "check.cpp"
        executable = Path(directory) / "check"
        cpp.write_text(harness)
        subprocess.run(["xcrun", "clang++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        str(cpp), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)
    report = {"actual_hold_helper_sha256": hashlib.sha256(helper.encode()).hexdigest(),
              "actual_schedule_sha256": hashlib.sha256(schedule.encode()).hexdigest(),
              "input_range_tested": [-1, 2200], "max_samples": 60,
              "sample_period_seconds": [15, 30], "max_hold_seconds": 1800,
              "no_pet_at_or_after_absolute_deadline": True,
              "original_55_second_watchdog_not_disabled": True, "hardware_qualified": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
