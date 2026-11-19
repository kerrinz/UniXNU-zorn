// SPDX-License-Identifier: MIT
#pragma once
#include "NativeAdrenoABI.h"

// The selected K80 backend implements ABI v1. In v2, method 17 and flag bit 1
// have different meanings; selecting that header must fail before compilation.
static_assert(NativeAdrenoAbiVersion == 1, "K80 backend requires its actual ABI v1");
static_assert(NativeAdrenoAbiMaxBuffers == 16, "K80 legacy Submit has 16 IBs");
static_assert(NativeAdrenoAbiMaxBatchBuffers == 128, "K80 batch extension has 128 IBs");
static_assert(NativeAdrenoMethodSubmitBatch == 17, "K80 method 17 is SubmitBatch");
static_assert(NativeAdrenoParamsSubmitBatch == 2, "K80 flag bit 1 means SubmitBatch");
static_assert(sizeof(NativeAdrenoAbiParams) == 24, "K80 Query layout");
static_assert(sizeof(NativeAdrenoAbiSubmit) == 416, "K80 legacy Submit layout");
static_assert(sizeof(NativeAdrenoAbiSubmitBatch) == 3104, "K80 batch layout");
