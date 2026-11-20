package com.jrees.wowcompanion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** Linux Edition 2026-11-20 (TapPad pad27, THE FAR ROWS): "DOWN DOWN <selector>" rows go as keys; columns 36-39 of a far row click. */
class TapKeysFarTest {
    private val cols = ((('A'..'Z').map { it.toString() }) + ('0'..'9').map { it.toString() } + listOf("INSERT", "HOME", "END", "PAGEUP"))
    private fun pad(rows: Map<String, String>) = JSONObject().put("keys", JSONObject()
        .put("mods", "CTRL-SHIFT").put("s", "42").put("cols", JSONArray(cols)).put("rows", JSONObject(rows)))

    @Test fun farRowGoesAsKeys() {
        val p = pad(mapOf("bag0" to "DOWN DOWN D", "qact" to "INSERT"))
        assertEquals("wckeys CTRL-SHIFT DOWN DOWN D F", TapKeys.script(p, listOf("bag0" to 5), 0L, "42"))
        assertEquals("wckeys CTRL-SHIFT INSERT C", TapKeys.script(p, listOf("qact" to 2), 0L, "42"))
    }

    @Test fun farRowNavColumnsAndBadShapesClick() {
        val p = pad(mapOf("bag0" to "DOWN DOWN D", "x" to "DOWN UP D", "y" to "DOWN DOWN HOME", "z" to "DOWN DOWN F5"))
        assertNull(TapKeys.script(p, listOf("bag0" to 37), 0L, "42"))   // column 37 = HOME: never rebound
        assertNull(TapKeys.script(p, listOf("x" to 1), 0L, "42"))
        assertNull(TapKeys.script(p, listOf("y" to 1), 0L, "42"))
        assertNull(TapKeys.script(p, listOf("z" to 1), 0L, "42"))
        assertNull(TapKeys.script(p, listOf("bag0" to 1), 0L, "41"))     // no live handshake token: clicks
    }
}
