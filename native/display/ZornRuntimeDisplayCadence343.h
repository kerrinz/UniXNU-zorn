// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <stdint.h>

namespace ZornRuntimeDisplayCadence343 {
enum Result : uint32_t {
    NotRun, RouteUnavailable, PublicationClosed, ProducerDeadline, GopUnavailable,
    ConfigUnavailable, ArmUnavailable, Interrupted, Completed,
};
enum Field : unsigned {
    Status, Retain, StartedMs, ElapsedUs, ReadinessChecks, InterfaceAdvances, FreshDsi,
    UnknownContent, ChangedContent, RepeatedContent, FirstContent, PollingGaps,
    FirstDsiUs, LastDsiUs, LastKnownSwap, LastKnownFence, Words,
};
constexpr unsigned OwnerWindowMs = 85000;
constexpr unsigned SampleWindowUs = 8000000;
}
