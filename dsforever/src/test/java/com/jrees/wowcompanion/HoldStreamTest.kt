package com.jrees.wowcompanion

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * Linux Streaming Edition (2026-11-25): HOLD TO CAST OVER THE STREAM. StreamTop sends Moonlight's button flags through the same gate as the
 * launcher (HoldCast.streamFilter): every button passes untouched while the gate is off; with a hold spell on bare A, a tap goes on
 * release and a hold goes at the hold time with Moonlight's Guide (0x0400) as the marker; the triggers go as the pad has them.
 */
class HoldStreamTest {
    private val mA = 0x1000; private val mB = 0x2000; private val mX = 0x4000; private val mY = 0x8000
    private val mLB = 0x0100; private val mBack = 0x0020; private val mUp = 0x0001; private val mLeft = 0x0004
    private val guide = HoldCast.M_GUIDE

    @After fun off() { HoldCast.gate.reset(); HoldCast.gate.configure(false, emptySet(), 0L) }

    @Test fun offEveryFlagPassesAsItIs() {
        HoldCast.gate.configure(false, emptySet(), 0L)
        for (f in listOf(0, mA, mB or mX, mY or mLB, mBack, mUp or mLeft, mA or mB or mX or mY or mUp, 0x0400))
            assertEquals("flags 0x%x".format(f), f, HoldCast.streamFilter(f, 0, 0, 1_000L))
        HoldCast.streamFilter(0, 200, 0, 1_100L)
        assertEquals("the triggers as the pad has them", 200, HoldCast.streamLt(200)); assertEquals(0, HoldCast.streamRt(0))
    }

    @Test fun aButtonWithoutAHoldSpellPassesAtOnce() {
        HoldCast.gate.configure(true, setOf(HoldGate.key(0, 8)), 0L)          // a hold spell on bare A only
        assertEquals(mB, HoldCast.streamFilter(mB, 0, 0, 1_000L))
        assertEquals(0, HoldCast.streamFilter(0, 0, 0, 1_010L))
        assertEquals(mUp or mX, HoldCast.streamFilter(mUp or mX, 0, 0, 1_020L))
    }

    @Test fun aTapGoesOnReleaseAndAHoldWithTheGuide() {
        HoldCast.gate.configure(true, setOf(HoldGate.key(0, 8)), 0L)
        // the tap: held back, then on release A goes down for a moment, never with the Guide
        assertEquals("held back", 0, HoldCast.streamFilter(mA, 0, 0, 1_000L))
        val tap = HoldCast.streamFilter(0, 0, 0, 1_100L)
        assertEquals("the tap goes on release", mA, tap)
        var t = 1_101L; while (t < 1_400L && HoldCast.streamFilter(0, 0, 0, t) != 0) t++
        assertEquals(0, HoldCast.streamFilter(0, 0, 0, 1_500L))
        // the hold: the Guide first at the hold time, then A with it
        HoldCast.gate.holdMs = HoldGate.NORMAL_MS
        assertEquals(0, HoldCast.streamFilter(mA, 0, 0, 2_000L))
        var seen = 0
        for (k in 2_001L..2_000L + HoldGate.NORMAL_MS + HoldGate.LEAD_MS + 5) seen = seen or HoldCast.streamFilter(mA, 0, 0, k)
        assertEquals("the hold sent A with Moonlight's Guide as the marker", mA or guide, seen and (mA or guide))
        assertEquals("let go: nothing stays down", 0, HoldCast.streamFilter(0, 0, 0, 3_000L) and (mA or guide))
    }
}
