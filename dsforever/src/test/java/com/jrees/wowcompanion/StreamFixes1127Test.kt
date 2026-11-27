package com.jrees.wowcompanion

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Linux Streaming Edition, the 2026-11-27 test session's fixes:
 *  - the Controller room's switches by keys (padtab's page-3 codes 30-35, Book b85), never the spells row's stream click;
 *  - the background art waits while a stream runs ([PlayGate.artGameBusy]), as the indoor bake does.
 */
class StreamFixes1127Test {
    private val prefix = listOf(PadMapModel.ROW_PADTAB to 39, PadMapModel.ROW_PADTAB to 38, PadMapModel.ROW_PADTAB to 37)

    @Test fun switchesGoAsPadtabPage3Codes() {
        assertEquals(prefix + (PadMapModel.ROW_PADTAB to 31), PadMapModel.switchCells("dpad", true))
        assertEquals(prefix + (PadMapModel.ROW_PADTAB to 30), PadMapModel.switchCells("dpad", false))
        assertEquals(prefix + (PadMapModel.ROW_PADTAB to 33), PadMapModel.switchCells("cc", true))
        assertEquals(prefix + (PadMapModel.ROW_PADTAB to 32), PadMapModel.switchCells("cc", false))
        assertEquals(prefix + (PadMapModel.ROW_PADTAB to 35), PadMapModel.switchCells("sa", true))
        assertEquals(prefix + (PadMapModel.ROW_PADTAB to 34), PadMapModel.switchCells("sa", false))
        assertEquals(PadMapModel.switchCells("dpad", true), PadMapModel.dpadCells(true))
        assertNull(PadMapModel.switchCells("cbshow", true))                // the app's own settings send nothing
        assertTrue("every switch cell is on padtab, a key row", PadMapModel.switchCells("cc", true)!!.all { it.first == PadMapModel.ROW_PADTAB })
    }

    @Test fun switchCodesDoNotOverlapOtherPage3Codes() {
        val ranges = PadMapModel.PAGE3_CODES.values.toList()
        for (i in ranges.indices) for (j in i + 1 until ranges.size) {
            assertTrue("${ranges[i]} and ${ranges[j]} overlap", ranges[i].last < ranges[j].first || ranges[j].last < ranges[i].first)
        }
        assertTrue("page-3 codes stay below the page prefix's 37-39", ranges.all { it.last < 37 })
    }

    @Test fun backgroundArtWaitsWhileStreaming() {
        assertTrue(PlayGate.artGameBusy(localGame = false, streamOnly = true, streaming = true))
        assertFalse(PlayGate.artGameBusy(localGame = false, streamOnly = true, streaming = false))
        assertTrue(PlayGate.artGameBusy(localGame = true, streamOnly = true, streaming = false))
        assertFalse("upstream's rule: a stream alone never pauses the art", PlayGate.artGameBusy(localGame = false, streamOnly = false, streaming = true))
    }
}
