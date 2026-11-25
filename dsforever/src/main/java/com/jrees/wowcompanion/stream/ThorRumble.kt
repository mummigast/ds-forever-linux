package com.jrees.wowcompanion.stream

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log
import android.view.InputDevice

/**
 * THE GAME'S RUMBLE ON THE THOR (Linux Streaming Edition, Q10 of the 2026-11-24 research: the stream advertised rumble, LI_CCAP_RUMBLE,
 * but StreamTop never overrode StreamSession.Events.rumble, so every motor command from the PC was dropped). Moonlight sends the
 * pad's two motor levels (0..65535) on every change, 0 / 0 = stop: the built-in controller's own vibrator when it has one, else the
 * handheld's; the level is the stronger motor, and it holds until the next change (a waveform repeating every [HOLD_MS] is cut by
 * the next call). Also [cue]: one short tap for a pop-up that wants the player (a queue pop, a ready check).
 */
object ThorRumble {
    private const val TAG = "DSFSTREAM"
    const val HOLD_MS = 1_000L
    const val CUE_MS = 60L

    @Volatile private var vib: Vibrator? = null
    @Volatile private var lastLevel = 0

    private fun vibrator(ctx: Context): Vibrator? {
        vib?.let { return it }
        val pad = InputDevice.getDeviceIds().asSequence().mapNotNull { InputDevice.getDevice(it) }
            .firstOrNull { (it.sources and InputDevice.SOURCE_GAMEPAD) == InputDevice.SOURCE_GAMEPAD && !it.isVirtual }
        val fromPad = if (pad != null && Build.VERSION.SDK_INT >= 31) pad.vibratorManager.defaultVibrator.takeIf { it.hasVibrator() } else null
        val own = if (Build.VERSION.SDK_INT >= 31) (ctx.getSystemService(VibratorManager::class.java))?.defaultVibrator
                  else @Suppress("DEPRECATION") ctx.getSystemService(Vibrator::class.java)
        return (fromPad ?: own?.takeIf { it.hasVibrator() }).also { if (it != null) vib = it; Log.i(TAG, "rumble: " + if (fromPad != null) "the pad's motor" else if (it != null) "the handheld's motor" else "no motor") }
    }

    /** 0..65535 per motor -> one amplitude 1..255, or 0 = stop (pure: the test) */
    fun amplitude(low: Int, high: Int): Int {
        val m = maxOf(low, high).coerceIn(0, 65535)
        return if (m == 0) 0 else (m * 255 / 65535).coerceAtLeast(1)
    }

    fun rumble(ctx: Context, low: Int, high: Int) {
        val v = vibrator(ctx) ?: return
        val a = amplitude(low, high)
        if (a == lastLevel) return
        lastLevel = a
        runCatching {
            if (a == 0) v.cancel()
            else v.vibrate(VibrationEffect.createWaveform(longArrayOf(0L, HOLD_MS), intArrayOf(0, a), 1))
        }
    }

    /** the stream ended or went away: stop a running rumble (its waveform repeats until cancelled) and forget the motor (the pad
     *  may be another next time) */
    fun stop() {
        val v = vib
        lastLevel = 0
        vib = null
        runCatching { v?.cancel() }
    }

    /** one short tap (never while the game's own rumble runs) */
    fun cue(ctx: Context) {
        if (lastLevel != 0) return
        val v = vibrator(ctx) ?: return
        runCatching { v.vibrate(VibrationEffect.createOneShot(CUE_MS, VibrationEffect.DEFAULT_AMPLITUDE)) }
    }
}
