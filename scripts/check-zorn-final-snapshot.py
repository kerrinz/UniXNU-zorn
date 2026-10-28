#!/usr/bin/env python3
"""Execute the actual final-flush helper with bounded host fault injection."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "UniXNU-zorn/native/ufs-read/ZornUfsRead.cpp"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "out/zorn/gui-final-snapshot-host-checks.json")
    args = parser.parse_args()
    source = SOURCE.read_text()
    start = source.index('extern "C" void zorn_ufs_gui_flush(void)')
    brace = source.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    helper = source[start:end]
    harness = r'''
#include <cassert>
#include <cstring>
using IOReturn = int;
static constexpr int kIOReturnSuccess = 0;
static bool gGuiWatch, gLogArmed;
static volatile int gLogBusy;
static char gLogBlock[4096];
static unsigned writes, sleeps, markers, successes, fail_count;
static bool release_on_sleep, expect_busy_on_return;
static IOReturn (*gZornWriteLog)(const void *);
static void zorn_log_put(const char *word) {
    assert(gLogBusy == 1 && !strcmp(word, "GUIEND"));
    ++markers;
}
static void IOSleep(unsigned ms) {
    assert(ms == 10 && writes <= 3 && ++sleeps <= 2);
    if (release_on_sleep) gLogBusy = 0;
}
static IOReturn write_log(const void *source) {
    assert(source == &gLogBlock && gLogBusy == 1 && ++writes <= 3);
    if (writes <= fail_count) return 1;
    ++successes;
    return kIOReturnSuccess;
}
@HELPER@
static void reset() {
    gGuiWatch = gLogArmed = true;
    gLogBusy = 0;
    writes = sleeps = markers = successes = fail_count = 0;
    release_on_sleep = expect_busy_on_return = false;
    gZornWriteLog = write_log;
}
static void check(unsigned w, unsigned s, unsigned ok) {
    assert(writes == w && sleeps == s && successes == ok && markers == writes);
    assert(gLogBusy == (expect_busy_on_return ? 1 : 0));
}
int main() {
    reset(); gGuiWatch = false; zorn_ufs_gui_flush(); check(0, 0, 0);
    reset(); gLogArmed = false; zorn_ufs_gui_flush(); check(0, 0, 0);
    reset(); gZornWriteLog = nullptr; zorn_ufs_gui_flush(); check(0, 0, 0);
    reset(); zorn_ufs_gui_flush(); check(1, 0, 1);
    reset(); fail_count = 1; zorn_ufs_gui_flush(); check(2, 1, 1);
    reset(); fail_count = 2; zorn_ufs_gui_flush(); check(3, 2, 1);
    reset(); fail_count = 3; zorn_ufs_gui_flush(); check(3, 2, 0);
    reset(); gLogBusy = 1; expect_busy_on_return = true;
    zorn_ufs_gui_flush(); check(0, 2, 0);
    reset(); gLogBusy = 1; release_on_sleep = true;
    zorn_ufs_gui_flush(); check(1, 1, 1);
    reset(); gLogBusy = 1; release_on_sleep = true; fail_count = 1;
    zorn_ufs_gui_flush(); check(2, 2, 1);
}
'''.replace("@HELPER@", helper)
    # No watchdog symbol or unrelated writer is stubbed: either would fail linking.
    with tempfile.TemporaryDirectory(prefix="zorn-final-snapshot-") as directory:
        cpp = Path(directory) / "check.cpp"
        executable = Path(directory) / "check"
        cpp.write_text(harness)
        subprocess.run(["xcrun", "clang++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        str(cpp), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)
    result = {"actual_helper_sha256": hashlib.sha256(helper.encode()).hexdigest(),
              "cases": 10, "same_4096_byte_buffer": True,
              "max_writes": 3, "max_scheduled_waits": 2,
              "scheduled_wait_ms": 10, "no_watchdog_pet": True,
              "hardware_qualified": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
