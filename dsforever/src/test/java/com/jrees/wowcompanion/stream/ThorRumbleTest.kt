package com.jrees.wowcompanion.stream

import org.junit.Assert.assertEquals
import org.junit.Test

/** Q10 (2026-11-24): the PC game's two motor levels (0..65535) become one Thor motor amplitude (1..255; 0 = stop) */
class ThorRumbleTest {
    @Test fun stopIsZero() = assertEquals(0, ThorRumble.amplitude(0, 0))
    @Test fun theStrongerMotorCounts() = assertEquals(255, ThorRumble.amplitude(65535, 10))
    @Test fun aWhisperIsStillFelt() = assertEquals(1, ThorRumble.amplitude(1, 0))
    @Test fun half() = assertEquals(127, ThorRumble.amplitude(0, 32767))
}
