package com.jrees.wowcompanion

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.Log
import android.view.MotionEvent
import android.view.View
import org.json.JSONArray
import org.json.JSONObject

/**
 * THE GAME'S AUCTION HOUSE, THE BOTTOM SCREEN'S KEYBOARD (Linux Streaming Edition 2026-11-21, Interact i180 / i181; the user: "AH in the
 * bottom screen should go ... we will be using WoW's own interface, and basically nothing from the bottom screen. It could show non
 * interactive stuff, like listed auctions, and recently bought items"; "we could use the screen below just for typing in AH").
 *
 * The auction house is the game's own window on the top screen, worked with WoW Forever's own controller navigation: the app never
 * takes the controller for it (this panel is not in the host's "bottom wants the pad"). While the add-on's doc.ahinfo is there:
 *  - the Chat keyboard (the host's, touch) types the game's search box: every letter goes into the field Chat.lua lent Interact
 *    (chat22, [stream]: the typed rows, now one key per letter after the row's keys - TapPad pad34), and Done puts the words into the
 *    game's box (SetText only: the search is the player's own press on the game's Search);
 *  - [view] shows, read only: what is typed, your auctions and what you bought lately.
 */
class AhPanel(private val ctx: Context, private val kb: ChatKeyboard, private val padOf: () -> JSONObject?) {
    val view = AhInfoView(ctx).apply { visibility = View.GONE }
    private var kbOpen = false
    private var typed = ""
    /** beta 3 LIVE TYPING (Interact i182): the game's search box has the keyboard focus (doc.ahinfo.focus) - every change on the
     *  keyboard goes straight into it as real keys ([InputSink.gameKeys]: letters, digits, space, Backspace), Done = the game's Enter
     *  (its own search). [liveSent] = what the game's box holds by our keys (its text when the focus came) */
    private var live = false
    private var liveSent = ""
    /** which focus the add-on reported last (its fid; -1 = none): another box = start again from that box's text */
    private var liveFid = -1
    private var lastDbg = ""
    /** the box in focus as the add-on says: "search", "min", "max", "other" or "" */
    private var focusKind = ""
    private val stream = ChatStream({ cells, gap ->
        TapBridge.tapsSpaced(ctx, padOf(), cells, gap) { why -> view.post { view.note = why; view.invalidate() } }
    }, field = true).apply { onEvent = { view.post { view.invalidate() } } }
    private val tick = object : Runnable {
        override fun run() { stream.tick(); if (stream.sending) view.postDelayed(this, 500L) }
    }

    init {
        view.onTypeTap = { reopen() }
        // i184: "Min level" / "Max level": one key (iact ahlv min|max) puts the game's focus in that box, then the keyboard types live
        view.onLevel = { which ->
            val col = view.info?.optInt(if (which == "max") "lvmax" else "lvmin", -1) ?: -1
            val inBox = if (live) focusKind else ""
            // a text box has the game's focus: it takes the keys, so our key would land IN it (the user: Min then Max closed the
            // window). Between the level boxes the game's own Tab moves the focus (their template links them); from another box
            // nothing is sent - the player leaves it first (Done)
            if (inBox == which) { /* already there */ }
            else if (inBox == "min" || inBox == "max") InputSink.signInTab()
            else if (inBox.isNotEmpty()) { view.note = "Press Done first, then pick the level box"; view.invalidate() }
            else if (col >= 0) {
                TapBridge.taps(ctx, padOf(), listOf("iact" to col)) { why -> view.post { view.note = why; view.invalidate() } }
                reopen()
            } else { view.note = "The game gave this no key"; view.invalidate() }
        }
    }

    /** every current interact document */
    fun update(msg: JSONObject) {
        val ah = msg.optJSONObject("ahinfo")
        if (ah == null) { close(); return }
        view.info = ah
        if (view.visibility != View.VISIBLE) view.visibility = View.VISIBLE
        // i183: ANY of the game's AH text boxes in focus ("search", or "other" = the filter's level range ...): each box its own text
        val fkind = if (InputSink.sink != null) ah.optString("focus", "") else ""
        focusKind = fkind
        ah.optString("fdbg", "").let { d -> if (d.isNotEmpty() && d != lastDbg) { lastDbg = d; Log.i("WCHOME", "ah keyboard: game focus = $d") } }
        val fid = if (fkind.isNotEmpty()) ah.optInt("fid", 0) else -1
        if (fid != liveFid) {
            liveFid = fid
            live = fkind.isNotEmpty()
            // the focus came (or moved to another box): that box's own text is where our keys start; it went: no key goes any more
            if (live) {
                liveSent = ah.optString("ftext", ah.optString("text", "")).filter { GameTyping.allowed(it) }
                typed = liveSent
                if (kbOpen) kb.open()
            }
            view.note = if (live) (if (fkind == "search") LIVE_NOTE else LIVE_NOTE_OTHER) else null
            if (!live) { typed = ah.optString("text", ""); if (kbOpen) kb.open() }      // the keyboard shows the game's search text again
            Log.i("WCHOME", "ah keyboard: live typing ${if (live) "on ($fkind box in focus)" else "off"}")
        }
        if (ah.optString("kbd") == "ahsearch") {
            if (!kbOpen && !view.kbDismissed) openKb(ah.optString("text", ""))
        } else if (kbOpen) closeKb()
        view.typed = if (kbOpen) typed else ah.optString("text", "")
        view.invalidate()
    }

    /** Chat.lua's answers ({"type":"chatt"}): the field's check and its hand-over */
    fun onChatAnswer(msg: JSONObject) {
        if (!kbOpen || msg.optString("type") != "chatt") return
        stream.heard(ChatStream.Heard("chatt", msg.optString("op"), msg.optBoolean("ok"),
            if (msg.has("why")) msg.optString("why") else null, msg.optString("ty", ""),
            msg.optInt("len", -1), msg.optInt("h", -1), msg.optInt("tlen", -1), msg.optInt("th", -1), msg.optString("into")))
    }

    private fun openKb(text: String) {
        kbOpen = true
        typed = stream.clean(text, MAX)
        stream.startField(typed)
        kb.sendWord = "Done"
        kb.text = { typed }
        kb.onText = { t ->
            typed = stream.clean(t, MAX)
            // beta 3: in the auction house the keyboard only types LIVE (a game box in focus); without one nothing is sent (the old
            // typed rows pressed many keys for every word, and their text went into the search box whatever box was meant)
            if (live) liveType(typed) else { view.note = NO_FOCUS_NOTE; view.invalidate() }
            view.typed = typed; view.invalidate()
        }
        kb.onSend = {
            if (live) InputSink.gameEnter()           // the game's own Enter in its search box: its search
            else { view.note = NO_FOCUS_NOTE; view.invalidate() }
        }
        // the keyboard's own close: it goes down, the panel stays (a finger on the search line brings it back)
        kb.onClose = { view.kbDismissed = true; closeKb(); view.invalidate() }
        kb.voiceBox = true
        kb.voiceAppend = false
        kb.voiceMax = MAX
        kb.copyLeftMs = { stream.copyLeftMs() }
        kb.open(); kb.visibility = View.VISIBLE
    }

    /** the keyboard's text [t] into the focused game box: Backspaces for what differs, then the new letters (a character the game may
     *  not be typed - not a letter, digit or space - is left out, and [liveSent] says what the box really got) */
    private fun liveType(t: String) {
        val ops = GameTyping.diff(liveSent, t)
        if (ops.back == 0 && ops.type.isEmpty()) return
        InputSink.gameKeys(ops.back, ops.type)
        liveSent = liveSent.dropLast(ops.back) + ops.type
    }

    private fun reopen() {
        val ah = view.info ?: return
        view.kbDismissed = false
        if (!kbOpen && ah.optString("kbd") == "ahsearch") openKb(ah.optString("text", ""))
        view.invalidate()
    }

    private fun closeKb() {
        if (!kbOpen) return
        kbOpen = false
        kb.stopVoice(restore = false)
        view.removeCallbacks(tick)
        kb.visibility = View.GONE
    }

    private fun close() {
        closeKb()
        view.kbDismissed = false
        view.info = null; view.note = null
        if (view.visibility != View.GONE) view.visibility = View.GONE
    }

    companion object {
        const val MAX = 63
        const val LIVE_NOTE = "Typing live into the game's search box (Done = Search)"
        const val LIVE_NOTE_OTHER = "Typing live into the game's text box (Done = Enter)"
        const val NO_FOCUS_NOTE = "Select a text box in the game first"
    }
}

/** Read only: the search words, your auctions, what you bought lately. A finger on the search line only brings the keyboard back. */
class AhInfoView(ctx: Context) : View(ctx) {
    var info: JSONObject? = null
    var typed = ""
    var note: String? = null
    var kbDismissed = false
    var onTypeTap: () -> Unit = {}
    var onLevel: (String) -> Unit = {}
    private var searchBottom = 0f
    private val lvMin = android.graphics.RectF()
    private val lvMax = android.graphics.RectF()
    private val bg = Paint().apply { color = Color.argb(235, 12, 10, 8) }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        // the search line only; everything else passes through (the panel has no functions)
        if (e.y > searchBottom) return false
        if (e.action == MotionEvent.ACTION_UP) {
            val lv = info?.optBoolean("lv", false) == true
            when {
                lv && lvMin.contains(e.x, e.y) -> onLevel("min")
                lv && lvMax.contains(e.x, e.y) -> onLevel("max")
                else -> onTypeTap()
            }
        }
        return true
    }

    override fun onDraw(c: Canvas) {
        val a = info ?: return
        val w = width.toFloat()
        c.drawRect(0f, 0f, w, height.toFloat(), bg)
        val pad = w * 0.03f
        var y = pad
        val title = UiKit.titlePaint(w * 0.045f)
        y += title.textSize
        c.drawText("Auction House", pad, y, title)
        val sub = UiKit.bodyPaint(w * 0.024f, Theme.dim)
        c.drawText("on the top screen: the game's own window, with the controller", pad, y + sub.textSize * 1.4f, sub)
        y += sub.textSize * 2.6f
        val body = UiKit.bodyPaint(w * 0.03f)
        val label = UiKit.bodyPaint(w * 0.026f, Theme.gold)
        c.drawText("Search", pad, y + label.textSize, label)
        val shown = typed.ifEmpty { if (kbDismissed) "tap here to type" else "" }
        c.drawText(shown, pad + w * 0.14f, y + label.textSize, if (typed.isEmpty()) sub else body)
        // i184: the game's Filter menu open: its level range's two boxes, a finger each
        if (a.optBoolean("lv", false)) {
            val bw = w * 0.17f; val bh = label.textSize * 1.6f; val top = y - label.textSize * 0.3f
            lvMax.set(w - pad - bw, top, w - pad, top + bh)
            lvMin.set(lvMax.left - pad - bw, top, lvMax.left - pad, top + bh)
            val fill = Paint().apply { color = Color.argb(255, 60, 48, 28) }
            val txt = UiKit.bodyPaint(w * 0.024f).apply { textAlign = Paint.Align.CENTER }
            for ((r, t) in listOf(lvMin to "Min level", lvMax to "Max level")) {
                c.drawRoundRect(r, bh * 0.25f, bh * 0.25f, fill)
                c.drawText(t, r.centerX(), r.centerY() + txt.textSize * 0.35f, txt)
            }
        } else { lvMin.setEmpty(); lvMax.setEmpty() }
        y += label.textSize * 1.9f
        searchBottom = y
        note?.let { c.drawText(it, pad, y, UiKit.bodyPaint(w * 0.022f, Color.rgb(230, 90, 70))); y += w * 0.03f }
        val half = (w - pad * 3) / 2f
        val owned = a.optJSONArray("owned") ?: JSONArray()
        val bought = a.optJSONArray("bought") ?: JSONArray()
        column(c, pad, y, half, "Your auctions (${a.optInt("nOwned", owned.length())})", owned, true)
        column(c, pad * 2 + half, y, half, "Bought lately", bought, false)
    }

    private fun column(c: Canvas, x: Float, y0: Float, w: Float, head: String, rows: JSONArray, owned: Boolean) {
        val label = UiKit.bodyPaint(width * 0.026f, Theme.gold)
        val row = UiKit.bodyPaint(width * 0.024f)
        val num = UiKit.numberPaint(width * 0.024f, Theme.dim).apply { textAlign = Paint.Align.RIGHT }
        var y = y0 + label.textSize
        c.drawText(head, x, y, label)
        y += label.textSize * 0.6f
        if (rows.length() == 0) {
            c.drawText(if (owned) "none listed" else "nothing yet", x, y + row.textSize * 1.3f, UiKit.bodyPaint(width * 0.022f, Theme.dim))
            return
        }
        val line = row.textSize * 1.55f
        for (i in 0 until rows.length()) {
            val r = rows.optJSONObject(i) ?: continue
            y += line
            if (y > height - line) break
            val n = r.optInt("n", 1)
            val name = r.optString("name", "?").let { if (n > 1) "$it ×$n" else it }
            val price = r.optLong("price", 0L).takeIf { it > 0 } ?: r.optLong("bid", 0L)
            val right = buildString {
                append(gsc(price))
                if (owned) append(if (r.optBoolean("sold")) "  sold" else "  " + left(r.optInt("left", -1)))
            }
            val rw = num.measureText(right)
            c.drawText(fit(name, row, w - rw - width * 0.02f), x, y, row)
            c.drawText(right, x + w, y, num)
        }
    }

    private fun fit(s: String, p: Paint, max: Float): String {
        if (p.measureText(s) <= max) return s
        var t = s
        while (t.length > 1 && p.measureText("$t…") > max) t = t.dropLast(1)
        return "$t…"
    }

    companion object {
        /** copper -> "1g 2s 3c" (the zero parts left out) */
        fun gsc(copper: Long): String {
            if (copper <= 0) return ""
            val g = copper / 10000; val s = copper / 100 % 100; val cc = copper % 100
            return listOfNotNull(if (g > 0) "${g}g" else null, if (s > 0) "${s}s" else null, if (cc > 0 || (g == 0L && s == 0L)) "${cc}c" else null)
                .joinToString(" ")
        }
        /** the game's Enum.AuctionHouseTimeLeftBand: 0 short .. 3 very long */
        fun left(band: Int): String = when (band) { 0 -> "<30m"; 1 -> "<2h"; 2 -> "<12h"; 3 -> "12-48h"; else -> "" }
    }
}
