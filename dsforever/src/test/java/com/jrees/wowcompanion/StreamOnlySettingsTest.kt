package com.jrees.wowcompanion

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Linux Edition 2026-11-20 (the user: "yes hide it" / "hide 1"): stream-only hides what only the Thor's own game uses */
class StreamOnlySettingsTest {
    private fun <T> streamOnly(body: () -> T): T {
        val was = StartMode.STREAM_ONLY
        StartMode.STREAM_ONLY = true
        try { return body() } finally { StartMode.STREAM_ONLY = was }
    }

    @Test fun performanceHasNoFrameTiles() = streamOnly {
        assertEquals(listOf(SettingsTabs.Block.LIGHTER, SettingsTabs.Block.INDOOR, SettingsTabs.Block.STREAMING),
            SettingsTabs.blocks(SettingsTabs.Tab.PERFORMANCE))
    }

    @Test fun generalHasNoAccountGroup() = streamOnly {
        val blocks = SettingsTabs.blocks(SettingsTabs.Tab.GENERAL)
        assertTrue(blocks.none { it.group == SettingsTabs.Group.ACCOUNT })
        assertTrue(GeneralTiles.rows(SettingsTabs.Group.ACCOUNT, loginRow = true, winIdRestart = true).isEmpty())
        assertTrue(SettingsTabs.Block.RESET in blocks && SettingsTabs.Block.HELP in blocks)
    }
}
