// ──────────────────────────────────────────────────────────────
// Nanonautics ALS — Sound Engine (Web Audio API)
// ──────────────────────────────────────────────────────────────
//
// All sounds are synthesized programmatically — no audio files required.
// The engine uses a singleton AudioContext to avoid repeated creation.
// All sounds are designed to be subtle, high-fidelity, and non-intrusive.
// ──────────────────────────────────────────────────────────────

let _ctx = null;

function getCtx() {
  if (!_ctx) {
    _ctx = new (window.AudioContext || window.webkitAudioContext)();
  }
  // Resume if suspended (browser autoplay policy)
  if (_ctx.state === "suspended") _ctx.resume();
  return _ctx;
}

/**
 * Schedules a gainNode fade-out and disconnects the chain at the end.
 */
function autoRelease(gainNode, ctx, duration) {
  gainNode.gain.setTargetAtTime(0, ctx.currentTime + duration * 0.7, 0.05);
  setTimeout(() => {
    try { gainNode.disconnect(); } catch (_) {}
  }, (duration + 0.3) * 1000);
}

// ─────────────────────────────────────────────────────────────────────────────
// SOUND DEFINITIONS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Synthesize: a clean, resonant submit tone.
 * Two-oscillator chord with a soft attack and silky decay.
 * Feels like clicking a premium mechanical button.
 */
export function playSubmit() {
  try {
    const ctx = getCtx();
    const time = ctx.currentTime;

    [[440, 0.12], [880, 0.07]].forEach(([freq, volume]) => {
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, time);
      osc.frequency.exponentialRampToValueAtTime(freq * 0.98, time + 0.4);

      gain.gain.setValueAtTime(0, time);
      gain.gain.linearRampToValueAtTime(volume, time + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.001, time + 0.55);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(time);
      osc.stop(time + 0.6);
    });
  } catch (_) {}
}

/**
 * Question appear: a delicate bell-like tone with a shimmer.
 * A sine wave with a flanging slightly-detuned copy.
 * Feels like a distant Tibetan bowl.
 */
export function playQuestionAppear() {
  try {
    const ctx = getCtx();
    const time = ctx.currentTime;

    const pairs = [
      { freq: 659.25, detune: 0,    vol: 0.08 }, // E5
      { freq: 659.25, detune: 8,    vol: 0.04 }, // slightly sharp shimmer
      { freq: 987.77, detune: 0,    vol: 0.04 }, // B5 — overtone
    ];

    pairs.forEach(({ freq, detune, vol }) => {
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(freq + detune, time);

      gain.gain.setValueAtTime(0, time);
      gain.gain.linearRampToValueAtTime(vol, time + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.001, time + 1.8);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(time);
      osc.stop(time + 2.0);
    });
  } catch (_) {}
}

/**
 * Unlock: an ascending three-note arpeggio.
 * Pure fifths — conveys achievement without being jarring.
 * Inspired by luxury UI (Apple Watch achievement chime).
 */
export function playUnlock() {
  try {
    const ctx = getCtx();
    const time = ctx.currentTime;

    // D4 -> A4 -> D5 (perfect fifths arpeggio)
    [
      { freq: 293.66, delay: 0.00 },
      { freq: 440.00, delay: 0.12 },
      { freq: 587.33, delay: 0.24 },
    ].forEach(({ freq, delay }) => {
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "triangle";
      osc.frequency.setValueAtTime(freq, time + delay);

      gain.gain.setValueAtTime(0, time + delay);
      gain.gain.linearRampToValueAtTime(0.10, time + delay + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.001, time + delay + 0.7);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(time + delay);
      osc.stop(time + delay + 0.8);
    });
  } catch (_) {}
}

/**
 * Recording start: a soft high-pitched click — like a studio talkback button.
 */
export function playRecordingStart() {
  try {
    const ctx = getCtx();
    const time = ctx.currentTime;

    const osc  = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "square";
    osc.frequency.setValueAtTime(1200, time);
    osc.frequency.exponentialRampToValueAtTime(600, time + 0.06);

    gain.gain.setValueAtTime(0, time);
    gain.gain.linearRampToValueAtTime(0.06, time + 0.005);
    gain.gain.exponentialRampToValueAtTime(0.001, time + 0.08);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(time);
    osc.stop(time + 0.1);
  } catch (_) {}
}

/**
 * Recording stop: a softer descending click — like releasing the talkback.
 */
export function playRecordingStop() {
  try {
    const ctx = getCtx();
    const time = ctx.currentTime;

    const osc  = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "square";
    osc.frequency.setValueAtTime(600, time);
    osc.frequency.exponentialRampToValueAtTime(300, time + 0.06);

    gain.gain.setValueAtTime(0, time);
    gain.gain.linearRampToValueAtTime(0.05, time + 0.005);
    gain.gain.exponentialRampToValueAtTime(0.001, time + 0.09);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(time);
    osc.stop(time + 0.1);
  } catch (_) {}
}

/**
 * Confidence tick: a near-silent soft sine click.
 * Like a luxury watch crown ratchet — barely audible but confirming.
 */
export function playConfidenceTick() {
  try {
    const ctx = getCtx();
    const time = ctx.currentTime;

    const osc  = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(800, time);

    gain.gain.setValueAtTime(0, time);
    gain.gain.linearRampToValueAtTime(0.04, time + 0.004);
    gain.gain.exponentialRampToValueAtTime(0.001, time + 0.06);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(time);
    osc.stop(time + 0.07);
  } catch (_) {}
}

/**
 * Image attach: a soft, low-pitched pop.
 * Like attaching a magnetic accessory.
 */
export function playAttach() {
  try {
    const ctx = getCtx();
    const time = ctx.currentTime;

    const osc  = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(220, time);
    osc.frequency.exponentialRampToValueAtTime(110, time + 0.07);

    gain.gain.setValueAtTime(0, time);
    gain.gain.linearRampToValueAtTime(0.07, time + 0.006);
    gain.gain.exponentialRampToValueAtTime(0.001, time + 0.1);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(time);
    osc.stop(time + 0.12);
  } catch (_) {}
}

/**
 * Error / connection failed: a soft descending interval.
 * Distinctly "wrong" but not alarmist.
 */
export function playError() {
  try {
    const ctx = getCtx();
    const time = ctx.currentTime;

    [[440, 0], [330, 0.15]].forEach(([freq, delay]) => {
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, time + delay);

      gain.gain.setValueAtTime(0, time + delay);
      gain.gain.linearRampToValueAtTime(0.07, time + delay + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.001, time + delay + 0.35);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(time + delay);
      osc.stop(time + delay + 0.4);
    });
  } catch (_) {}
}
