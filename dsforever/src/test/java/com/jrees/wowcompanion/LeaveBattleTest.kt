package com.jrees.wowcompanion

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Linux Streaming Edition (the user, 2026-11-24: "i cannot leave the BG"; "yes add leaving mid-match too"): the pause wheel's page 3
 * Leave Battle - only while a battleground is active, asks first, and its tap is Spells' pause row column 11 (Radial.lua pr4).
 */
class LeaveBattleTest {
    private fun page3(inBg: Boolean): List<HomePauseModel.Slice?> {
        val f = HomePauseModel.Flow(); f.inBg = inBg
        f.turn(+1)                                   // the centre page -> page 3
        return f.slices()
    }

    @Test fun shownOnlyInABattleground() {
        assertFalse(page3(false).any { it?.key == "leavebg" })
        val s = page3(true).first { it?.key == "leavebg" }!!
        assertEquals("Leave Battle", s.label)
        assertTrue("asks first", s.confirm)
        assertEquals(HomePauseModel.Kind.GAME, s.kind)
    }

    @Test fun itsTapIsPauseColumn11() {
        assertEquals(11, HomePauseModel.col("leavebg"))
        assertEquals(10, HomePauseModel.col("menu"))       // the old columns did not move
        assertEquals(1, HomePauseModel.col("pvp"))
    }
}
