package com.jrees.wowcompanion

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Q2 (2026-11-24): Settings > Help > Keyboard link - the player sees whether presses go as keys or fall back to clicks */
class KeyHealthTest {
    @After fun clear() { KeyHealth.reset() }

    @Test fun nothingYet() { assertEquals(KeyHealth.State.NONE, KeyHealth.summary(1_000L).state) }

    @Test fun allKeysIsGreen() {
        KeyHealth.keys(listOf("mapw"), 1_000L); KeyHealth.keys(listOf("prof"), 2_000L)
        assertEquals(KeyHealth.State.OK, KeyHealth.summary(3_000L).state)
    }

    @Test fun clicksNameTheirRows() {
        KeyHealth.keys(listOf("mapw"), 1_000L)
        KeyHealth.clicks(listOf("party"), "a cell without keys", 2_000L)
        KeyHealth.clicks(listOf("party", "gf"), "a cell without keys", 3_000L)
        val s = KeyHealth.summary(4_000L)
        assertEquals(KeyHealth.State.PART, s.state)
        assertTrue(s.text, s.text.startsWith("On; still clicks: party"))
        assertTrue(s.text, "gf" in s.text)
    }

    @Test fun noHandshakeIsRed() {
        KeyHealth.clicks(listOf("bag0"), "no handshake", 1_000L)
        assertEquals(KeyHealth.State.OFF, KeyHealth.summary(2_000L).state)
    }

    @Test fun oldFailuresFade() {
        KeyHealth.clicks(listOf("bag0"), "no handshake", 1_000L)
        KeyHealth.keys(listOf("mapw"), 1_000L + KeyHealth.WINDOW_MS + 10L)
        assertEquals(KeyHealth.State.OK, KeyHealth.summary(1_000L + KeyHealth.WINDOW_MS + 20L).state)
    }
}

/** Q7 (2026-11-24): the Settings tab strip's touch band is the app's 48 dp floor (>= 111 px), not the 64 px art */
class SettingsTabHitTest {
    @Test fun theTouchBandIsAtLeast111Px() {
        val band = SettingsTabBar.TAB_H + SettingsTabBar.HIT_UP + SettingsTabBar.HIT_DOWN
        assertTrue("band $band", band >= 111f)
        assertTrue(SettingsTabBar.hitY(SettingsTabBar.TAB_TOP - 30f))
        assertTrue(!SettingsTabBar.hitY(SettingsTabBar.TAB_TOP - 40f))
        assertTrue("never below the strip", SettingsTabBar.TAB_TOP + SettingsTabBar.TAB_H + SettingsTabBar.HIT_DOWN <= SettingsTabBar.BAR_H)
    }
}
