package com.jrees.wowcompanion.stream

import android.os.SystemClock
import android.util.Log

/**
 * Linux Streaming Edition (2026-11-23, the user: "did it relog me? I got a new wow window open"; the PC had THREE WoWs: Battle.net's
 * window was in front and a key of ours - the keyboard's Enter - pressed its Play). The helper watches which window has the PC's
 * focus while a Thor is connected ({"t":"pcfocus","wow":bool,"what":class}); while it is not WoW, NO key and NO click of the app
 * goes to the PC ([StreamKeys] asks [allowed]) - the player's own controller is not touched - and the helper is asked (at most every
 * [ASK_MS]) to bring WoW to the front (its existing "focus"). An older helper never says: WoW counts as in front, as before.
 */
object PcFront {
    @Volatile var wowFront = true
        private set
    @Volatile var what = ""
        private set
    /** the bridge's "focus" request (set by BridgeLog while connected) */
    @Volatile var asker: (() -> Unit)? = null
    private var askedAt = 0L
    private var told = false
    const val ASK_MS = 5_000L

    fun set(wow: Boolean, w: String) {
        if (wow != wowFront) Log.i("DSFTAP", "pc focus: ${if (wow) "WoW in front" else "another window in front ($w): app keys and clicks held back"}")
        val back = wow && !wowFront
        wowFront = wow; what = w; told = false
        if (back) runCatching { com.jrees.wowcompanion.TapBridge.frontBack() }    // the held-back handshake ask goes again
    }

    /** true = the app may send a key / click now; false = dropped (another window has the PC's focus) */
    fun allowed(): Boolean {
        if (wowFront) return true
        val now = SystemClock.uptimeMillis()
        if (!told) { told = true; Log.i("DSFTAP", "pc focus: a key or click held back ($what in front)") }
        if (now - askedAt >= ASK_MS) { askedAt = now; runCatching { asker?.invoke() } }
        return false
    }

    /** a new connection: nothing known yet (WoW counts as in front until the helper says otherwise) */
    fun reset() { wowFront = true; what = ""; told = false }
}
