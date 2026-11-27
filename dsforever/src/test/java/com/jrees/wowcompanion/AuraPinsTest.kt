package com.jrees.wowcompanion

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** a9 (the user, 2026-11-24: "pin buffs for fight"): pins in the auras doc, the pin flow's acks, the pause wheel's Cancel slices */
class AuraPinsTest {
    private val pad = """"pad":{"rows":{"aurapick":43,"auracancel":44}}"""
    private fun doc(extra: String) = JSONObject("""{"type":"auras","v":"a9","now":100,"b":[{"id":7,"n":"Divine Shield","slot":3}],"d":[],"e":[],$pad,$extra}""")

    @Test fun pinsAreRead() {
        val a = HomeAuras()
        a.update(doc(""""pins":[{"n":"Divine Shield","col":25,"i":1}],"pinCell":12,"unpinCells":[13,14]"""), true, 1_000L)
        assertEquals(listOf(HomeAuras.Pin("Divine Shield", 25, 1)), a.pins)
        assertEquals(12, a.pinCell)
        assertEquals(13, a.unpinCell(a.pins[0]))
        assertEquals(a.pins[0], a.pinOf("Divine Shield"))
    }

    @Test fun pinPicksThenPins() {
        val a = HomeAuras()
        a.update(doc(""""pins":[],"pinCell":12,"unpinCells":[13,14]"""), true, 1_000L)
        val t = a.pin(7, true, 1_100L)
        assertTrue(t is AuraTap.Send)
        assertEquals(AuraAck.Pin, a.ack(JSONObject("""{"type":"auraack","op":"pick","id":7,"ok":true}"""), 1_200L))
        val n = a.ack(JSONObject("""{"type":"auraack","op":"pin","id":7,"ok":true,"n":"Divine Shield"}"""), 1_300L)
        assertEquals(AuraAck.Note("Pinned for fights: Divine Shield"), n)
    }

    @Test fun noPinCellFromAnOldAddon() {
        val a = HomeAuras()
        a.update(doc(""""x":1"""), true, 1_000L)
        assertNull(a.pinCell)
        assertTrue(a.pin(7, true, 1_100L) is AuraTap.Refused)
    }

    @Test fun thePauseWheelShowsOnlyPinnedOnes() {
        val f = HomePauseModel.Flow(); f.turn(+1)
        assertTrue(f.slices().none { it?.key == "pin1" || it?.key == "pin2" })
        f.pinNames = listOf("Divine Shield")
        val s = f.slices().first { it?.key == "pin1" }!!
        assertEquals("Cancel Divine Shield", s.label)
        assertTrue(f.slices().none { it?.key == "pin2" })
    }
}
