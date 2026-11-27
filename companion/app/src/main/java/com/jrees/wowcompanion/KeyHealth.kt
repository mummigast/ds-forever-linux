package com.jrees.wowcompanion

/**
 * THE KEYBOARD LINK'S HEALTH, FOR THE PLAYER (Linux Streaming Edition, Q2 of the 2026-11-24 research: "binding health check"; until now a
 * press that fell back to a CLICK - no handshake, a row without keys - was said in logcat only). TapBridge reports every batch here: by
 * keys, or as clicks with the reason; Settings > Help > Keyboard link reads [summary]. Only the last [WINDOW_MS] counts, so an old
 * failure fades once keys work again. Pure (the clock is passed in): the tests drive it.
 */
object KeyHealth {
    enum class State { NONE, OK, PART, OFF }
    data class Summary(val state: State, val text: String)

    /** what counts: presses of the last 5 minutes */
    const val WINDOW_MS = 5 * 60_000L
    /** at most this many row names in the line */
    const val ROWS_SHOWN = 4

    private data class Ev(val at: Long, val keys: Boolean, val rows: List<String>, val why: String?)
    private val evs = ArrayDeque<Ev>()

    /** a batch that went as keys */
    @Synchronized fun keys(rows: List<String>, now: Long) { add(Ev(now, true, rows, null), now) }
    /** a batch that went as clicks, and why ("no handshake", "a cell without keys", "typing", ...; null = the pad publishes no keys) */
    @Synchronized fun clicks(rows: List<String>, why: String?, now: Long) { add(Ev(now, false, rows, why), now) }
    @Synchronized fun reset() { evs.clear() }

    private fun add(e: Ev, now: Long) {
        evs.addLast(e)
        while (evs.isNotEmpty() && now - evs.first().at > WINDOW_MS) evs.removeFirst()
        while (evs.size > 400) evs.removeFirst()
    }

    @Synchronized fun summary(now: Long): Summary {
        val live = evs.filter { now - it.at <= WINDOW_MS }
        if (live.isEmpty()) return Summary(State.NONE, "No presses yet")
        val clicks = live.filter { !it.keys }
        val keys = live.size - clicks.size
        if (clicks.isEmpty()) return Summary(State.OK, "On: every press goes as keys")
        // no handshake (or none published) on the newest click and no key batch since: the link is down
        val newest = live.last()
        if (!newest.keys && keys == 0 && (newest.why == "no handshake" || newest.why == null))
            return Summary(State.OFF, "Not linked yet: presses go as clicks (reload the game UI if it stays)")
        val rows = clicks.flatMap { it.rows }.groupingBy { it }.eachCount().entries.sortedByDescending { it.value }.map { it.key }
        val shown = rows.take(ROWS_SHOWN).joinToString(", ") + if (rows.size > ROWS_SHOWN) " +${rows.size - ROWS_SHOWN}" else ""
        return Summary(State.PART, "On; still clicks: $shown")
    }
}
