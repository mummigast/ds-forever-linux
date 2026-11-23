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

    // TapPad pad34: a typing row stays picked; the row keys go once, then one key per letter
    private fun padSticky() = pad(mapOf("chr" to "DOWN DOWN Y", "chs" to "DOWN DOWN Z", "qact" to "INSERT")).also {
        it.getJSONObject("keys").put("sticky", JSONObject().put("chr", true).put("chs", true))
    }

    @Test fun typingRowKeepsItsPick() {
        val p = padSticky()
        TapKeys.forgetSticky()
        assertEquals("wckeys CTRL-SHIFT DOWN DOWN Y F G G", TapKeys.script(p, listOf("chr" to 5, "chr" to 6, "chr" to 6), 0L, "42"))
        // the next batch, still on chr: the letter alone
        assertEquals("wckeys CTRL-SHIFT H", TapKeys.script(p, listOf("chr" to 7), 0L, "42"))
        // another typing row: its own row keys; a navigation column (36 = INSERT) always with them
        assertEquals("wckeys CTRL-SHIFT DOWN DOWN Z A DOWN DOWN Z INSERT", TapKeys.script(p, listOf("chs" to 0, "chs" to 36), 0L, "42"))
    }

    @Test fun anythingElseEndsThePick() {
        val p = padSticky()
        TapKeys.forgetSticky()
        TapKeys.script(p, listOf("chr" to 5), 0L, "42")
        assertEquals("wckeys CTRL-SHIFT INSERT C", TapKeys.script(p, listOf("qact" to 2), 0L, "42"))
        assertEquals("wckeys CTRL-SHIFT DOWN DOWN Y F", TapKeys.script(p, listOf("chr" to 5), 0L, "42"))
        TapKeys.forgetSticky()
        assertEquals("wckeys CTRL-SHIFT DOWN DOWN Y G", TapKeys.script(p, listOf("chr" to 6), 0L, "42"))
    }
}
