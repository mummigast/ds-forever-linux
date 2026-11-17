package com.jrees.wowcompanion

import com.jrees.wowcompanion.StartMode.By
import com.jrees.wowcompanion.StartMode.Mode
import com.jrees.wowcompanion.StartMode.Route
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

/** Linux Streaming Edition: the app opens straight on Stream; no chooser, no Local checks, no way back to them */
class StreamOnlyTest {
    @Before fun on() { StartMode.STREAM_ONLY = true }
    @After fun off() { StartMode.STREAM_ONLY = false }

    @Test fun iconOpensStream() {
        assertEquals(Route.Into(Mode.STREAM, By.PICKED), StartMode.resolve(null))
        assertEquals(Route.Into(Mode.STREAM, By.PICKED), StartMode.resolve("local"))
        assertFalse(StartMode.runsChecks(StartMode.resolve(null)))
    }

    @Test fun reopenStaysAndNoBack() {
        val r = Route.Into(Mode.STREAM, By.PICKED)
        assertNull(StartMode.onCreate(r, null, recreated = false, gameUp = false, restarting = false))
        assertFalse(StartMode.canGoBack(r, gameUp = false, busy = false, restarting = false, loginFormOpen = false))
    }
}
