// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

#include <stdint.h>

namespace ZornPassiveFrameOwnership {

struct Epoch {
    uint32_t sequence = 0;
    uint32_t signature = 0;
    bool gpuFenced = false;

    bool stable() const { return sequence && !(sequence & 1); }

    bool same(const Epoch &other) const
    {
        return stable() && sequence == other.sequence &&
            signature == other.signature && gpuFenced == other.gpuFenced;
    }
};

struct Poll {
    uint64_t beginUs = 0, endUs = 0;
    Epoch before{}, after{};
    uint32_t interfaceFrames = 0, writeLine = 0;
    bool kickoff = false, writePointer = false, done = false;
};

enum class Result { Wait, InvalidBoundary, OverlapOrUnbound, CompleteFirst, CompleteRepeated, CompleteChanged };

class Pending {
public:
    explicit Pending(uint64_t maximumPollGapUs) : maximumPollGapUs_(maximumPollGapUs) {}

    // The caller supplies a verified quiet snapshot after acknowledging only
    // the previous epoch's flags. A dirty or regressed boundary breaks the
    // content comparison with the last transfer.
    void begin(const Poll &quiet)
    {
        active_ = quiet.beginUs && quiet.beginUs <= quiet.endUs &&
            !(quiet.kickoff || quiet.writePointer || quiet.done);
        if (started_ || !active_ || (lastEndUs_ && quiet.beginUs < lastEndUs_)) {
            active_ = false;
            precedingKnown_ = false;
        }
        quiet_ = quiet;
        started_ = advanced_ = false;
        first_ = {};
        lastEndUs_ = quiet.endUs;
    }

    Result observe(const Poll &poll)
    {
        if (!active_ || poll.beginUs < lastEndUs_ || poll.endUs < poll.beginUs ||
            poll.endUs - lastEndUs_ > maximumPollGapUs_ ||
            uint32_t(poll.interfaceFrames - quiet_.interfaceFrames) > 1) {
            return finishUnknown(Result::InvalidBoundary);
        }
        lastEndUs_ = poll.endUs;
        if (!started_ && !poll.kickoff && poll.interfaceFrames != quiet_.interfaceFrames)
            return finishUnknown(Result::OverlapOrUnbound);
        if (!started_ && poll.kickoff) {
            started_ = true;
            first_ = quiet_.after.same(poll.before) ? poll.before : Epoch{};
        }
        if (started_ && (!(poll.kickoff) || !first_.same(poll.before) || !first_.same(poll.after)))
            first_ = {};
        if (started_ && poll.writePointer && poll.writeLine && poll.writeLine != quiet_.writeLine)
            advanced_ = true;
        if (!poll.done) {
            if (!started_ && !poll.writePointer) quiet_ = poll;
            return Result::Wait;
        }
        if (!started_ || !advanced_ || poll.interfaceFrames - quiet_.interfaceFrames != 1u ||
            !first_.stable() || !first_.gpuFenced) {
            return finishUnknown(Result::OverlapOrUnbound);
        }
        const auto result = !precedingKnown_ ? Result::CompleteFirst :
            previousSignature_ == first_.signature ? Result::CompleteRepeated : Result::CompleteChanged;
        precedingKnown_ = true;
        previousSignature_ = first_.signature;
        active_ = started_ = false;
        return result;
    }

private:
    Result finishUnknown(Result result)
    {
        active_ = started_ = false;
        precedingKnown_ = false;
        return result;
    }

    uint64_t maximumPollGapUs_, lastEndUs_ = 0;
    Poll quiet_{};
    Epoch first_{};
    uint32_t previousSignature_ = 0;
    bool active_ = false, started_ = false, advanced_ = false, precedingKnown_ = false;
};

} // namespace ZornPassiveFrameOwnership
