"""Venus-8 v0.2 synthesis core. All note/parameter mutations share one lock."""
import math
import threading

import numpy as np

WAVES = ("Saw", "Pulse", "Triangle", "Sine")
DEFAULTS = {
    "osc1_level": 0.75, "osc2_level": 0.48, "osc3_level": 0.30,
    "osc1_tune": 0.5, "osc2_tune": 0.51, "osc3_tune": 0.49,
    "osc1_wave": 0.0, "osc2_wave": 0.0, "osc3_wave": 0.0,
    "osc1_octave": 0.5, "osc2_octave": 0.5, "osc3_octave": 0.5,
    "osc1_fine": 0.5, "osc2_fine": 0.5, "osc3_fine": 0.5,
    "sub_level": 0.15, "noise_level": 0.0,
    "cutoff": 0.72, "resonance": 0.20, "drive": 0.12,
    "attack": 0.06, "decay": 0.40, "sustain": 0.72, "release": 0.30,
    "lfo_rate": 0.25, "lfo_depth": 0.0, "lfo2_rate": 0.2, "lfo2_depth": 0.0,
    "delay_mix": 0.0, "delay_time": 0.28, "delay_feedback": 0.25,
    "volume": 0.36, "pitch_bend": 0.5, "modwheel": 0.0,
}
# Tonewheel organ drawbars: footage and harmonic of the 8' fundamental.
DRAWBARS = (("16'", 0.5), ("5⅓'", 1.5), ("8'", 1.0), ("4'", 2.0), ("2⅔'", 3.0),
            ("2'", 4.0), ("1⅗'", 5.0), ("1⅓'", 6.0), ("1'", 8.0))
TONEWHEEL_TOP = 5900.0     # highest tonewheel; partials above fold back an octave
DEFAULTS.update({f"drawbar{i}": 0.0 for i in range(1, len(DRAWBARS) + 1)})
# FM: each oscillator's FM switch lets the next one modulate its phase
# (OSC3 -> OSC2 -> OSC1, as a 3-operator stack); OSC3's FM is self-feedback.
# The index follows the MOD ENV and the key velocity.
DEFAULTS.update({f"osc{i}_fm": 0.35 for i in (1, 2, 3)})
DEFAULTS.update({f"osc{i}_fm_on": 0.0 for i in (1, 2, 3)})
DEFAULTS.update({"mod_attack": 0.0, "mod_decay": 0.4, "mod_sustain": 1.0, "mod_release": 0.3})
FM_MAX_INDEX = 10.0               # radians of phase deviation at full amount
# Electric piano layer (tine model): level, tone (bell/brightness), bark, decay.
DEFAULTS.update({"ep_level": 0.0, "ep_tone": 0.5, "ep_bark": 0.3, "ep_decay": 0.5})
EP_SLOT = 4 + len(DRAWBARS)
# Electric grand (CP-70 style): ep_model 1 swaps the tine for struck strings
# with piezo pickups. Ten stiff-string partials, each with its own phase slot.
DEFAULTS["ep_model"] = 0.0
GRAND_PARTIALS = 10
GRAND_SLOT = EP_SLOT + 1
UNISON_SLOT = GRAND_SLOT + 10      # 4 copies x (OSC1-3 + sub) phase slots
PHASE_SLOTS = UNISON_SLOT + 4 * 4
# Effects: one modulation unit (chorus_type: Chorus, the Juno-60/106 chorus
# modes I, II and I+II, or Flanger) and a 4-stage phaser.
CHORUS_TYPES = ("CHORUS", "JUNO I", "JUNO II", "JUNO I+II", "FLANGER")
# Juno BBD chorus: (LFO Hz, centre delay ms, sweep ms), triangle LFO, fixed.
JUNO_CHORUS = {1: (0.513, 3.5, 1.85), 2: (0.863, 3.5, 1.85), 3: (9.75, 3.3, 0.25)}
DEFAULTS.update({"chorus_on": 0.0, "chorus_type": 0.0, "chorus_depth": 0.5,
                 "chorus_rate": 0.3, "phaser_on": 0.0, "phaser_depth": 0.6,
                 "phaser_rate": 0.25})
# Tube stage on the whole instrument (triode-like, even harmonics). 0 = bypass.
DEFAULTS["tube_drive"] = 0.0
# Filter: type (LP24, LP12, BP12, HP12 from the ladder's stages), key tracking
# and a paraphonic filter envelope (one envelope for the shared filter,
# retriggered by each new note, released when no key is held).
FILTER_TYPES = ("Low Pass 24 dB", "Low Pass 12 dB", "Band Pass 12 dB", "High Pass 12 dB")
DEFAULTS.update({"filter_type": 0.0, "key_track": 0.0, "filter_env_on": 0.0,
                 "fenv_attack": 0.02, "fenv_decay": 0.4, "fenv_sustain": 0.4,
                 "fenv_release": 0.3})
FILTER_ENV_OCTAVES = 4.5
# LFO waves (Sine, Tri, Saw, S&H), fade-in after the first key and key sync.
LFO_WAVES = ("Sine", "Tri", "Saw", "S&H")
DEFAULTS.update({"lfo_wave": 0.0, "lfo2_wave": 0.0, "lfo_fade": 0.0, "lfo2_fade": 0.0,
                 "lfo_sync": 0.0, "lfo2_sync": 0.0})
# Reverb (Freeverb-style combs and all-passes) and master stereo width.
DEFAULTS.update({"reverb_on": 0.0, "reverb_size": 0.5, "reverb_damp": 0.4,
                 "reverb_mix": 0.3, "width": 0.5})
REVERB_COMBS = (1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617)
REVERB_ALLPASSES = (556, 441, 341, 225)
REVERB_SPREAD = 23
# Performance: voice mode (Poly, Mono, Legato, Unison), unison detune, glide,
# and pulse width / PWM (by LFO 1) on each oscillator.
VOICE_MODES = ("Poly", "Mono", "Legato", "Unison")
DEFAULTS.update({"voice_mode": 0.0, "unison_detune": 0.3, "glide_time": 0.0})
DEFAULTS.update({f"osc{i}_pw": 0.0 for i in (1, 2, 3)})
DEFAULTS.update({f"osc{i}_pwm": 0.0 for i in (1, 2, 3)})
UNISON_COPIES = 4
UNISON_CENTS = 30.0               # outer copies at full DETUNE
# Arpeggiator: 1/16 steps at 40..240 BPM, gate 5..100 %, 1..4 octaves, hold.
ARP_MODES = ("Up", "Down", "Up/Down", "Random", "As Played")
DEFAULTS.update({"arp_on": 0.0, "arp_mode": 0.0, "arp_rate": 0.4, "arp_gate": 0.5,
                 "arp_oct": 0.0, "arp_hold": 0.0})
# Vintage synthesis (Prophet-5, Minimoog, Jupiter-8):
# - SYNC: OSC1 hard-synced to OSC2, OSC2 to OSC3 (same chain as FM); RING on
#   OSC1 multiplies it by OSC2; NOISE turns OSC3 into a noise source.
# - POLY-MOD: filter envelope and OSC B (OSC2) modulate OSC A's pitch, its
#   pulse width and/or the filter.
# - Minimoog modulation: OSC3 (optionally LO, a slow LFO not following the
#   keys) mixed with noise, amount on the mod wheel, to the oscillators and/or filter.
# - VINTAGE: per-voice analog drift of pitch and envelope timing.
# - HPF: non-resonant high-pass after the ladder (Jupiter-8 style).
DEFAULTS.update({"osc1_sync": 0.0, "osc2_sync": 0.0, "osc1_ring": 0.0, "osc3_noise": 0.0,
                 "polymod_env": 0.0, "polymod_osc": 0.0, "polymod_freq": 0.0,
                 "polymod_pw": 0.0, "polymod_filter": 0.0, "moog_mix": 0.0,
                 "moog_osc": 0.0, "moog_filter": 0.0, "osc3_lo": 0.0, "vintage": 0.0,
                 "hpf": 0.0})
POLYMOD_SEMITONES = 24.0
MOOG_SEMITONES = 12.0
MOD_FX_HISTORY = 0.025             # seconds of delay line for chorus and flanger
# Organ section switches (0/1) and drive: percussion (2nd/3rd harmonic, fast or
# slow decay, single-triggered, cancels the 1' drawbar like a B-3), key click,
# scanner vibrato/chorus, tube-style overdrive and a two-rotor Leslie.
ORGAN_SWITCHES = ("organ_perc", "organ_perc_third", "organ_perc_fast", "organ_click",
                  "organ_vibrato", "organ_chorus", "leslie", "leslie_fast")
DEFAULTS.update({name: 0.0 for name in ORGAN_SWITCHES})
DEFAULTS["organ_drive"] = 0.0
PERC_BARS = (3, 4)                 # 4' (2nd harmonic) and 2⅔' (3rd) drawbar slots
# Leslie rotors (Hz): horn and drum, slow (chorale) and fast (tremolo), and how
# long each takes to speed up / slow down. The heavy drum is much slower.
HORN_SPEED, DRUM_SPEED = (0.83, 6.7), (0.67, 5.7)
HORN_INERTIA, DRUM_INERTIA = (0.9, 0.6), (4.0, 3.2)
DELAY_HISTORY = 0.001              # seconds kept by the short modulated delay lines
CROSSOVER = 24                     # moving-average split between drum and horn (~800 Hz)


def modulated_delay(history, block, delay):
    """Read ``block`` through a delay line at a per-sample fractional delay
    (1..len(history) samples). Returns the output and the new history."""
    line = np.concatenate((history, block))
    pos = len(history) + np.arange(len(block)) - delay
    index = np.floor(pos).astype(np.int64)
    frac = pos - index
    return line[index] * (1.0 - frac) + line[index + 1] * frac, line[-len(history):]


class Synth:
    def __init__(self, sample_rate=44100, max_voices=16):
        self.sample_rate = int(sample_rate)
        self.max_voices = int(max_voices)
        self.lock = threading.RLock()
        self.params = dict(DEFAULTS)
        self.voices = {}
        self.voice_serial = 0
        self.lowpass = 0.0
        self.filter_states = [0.0, 0.0, 0.0, 0.0]
        self.hpf_state = (0.0, 0.0)
        self.lfo_phase = 0.0
        self.lfo2_phase = 0.0
        self.lfo_hold = [0.0, 0.0]          # S&H values of LFO 1 and 2
        self.lfo_age = 0.0                  # seconds since the first key (LFO fade)
        self.last_note = 60
        self.fenv = {"level": 0.0, "time": 0.0, "gate": False, "from": 0.0}
        self.sustain = False            # sustain pedal (MIDI CC64)
        self.held = []                  # keys held, in order (mono modes)
        self.arp_keys, self.arp_pressed = [], set()
        self.arp_note, self.arp_index, self.arp_clock = None, 0, 0
        self.arp_gate_left, self.arp_velocity = 0, 100
        self.rng = np.random.default_rng()
        self.delay_buffer = np.zeros(self.sample_rate * 2, dtype=np.float32)
        self.delay_index = 0
        self.peak = 0.0
        self._reset_organ()
        self._reset_effects()

    def _lfo_wave(self, which, phase, wave):
        """LFO shape over ``phase`` (turns, from the block start, unwrapped)."""
        index = round(wave * 3)
        if index == 0:
            return np.sin(2 * np.pi * phase)
        frac = phase % 1.0
        if index == 1:
            return 1.0 - 4.0 * np.abs(frac - 0.5)
        if index == 2:
            return 1.0 - 2.0 * frac                     # falling ramp
        # Sample & hold: a new random level each cycle.
        cycles = np.floor(phase).astype(np.int64)
        fresh = self.rng.uniform(-1.0, 1.0, int(cycles[-1]) + 1)
        fresh[0] = self.lfo_hold[which]
        self.lfo_hold[which] = float(fresh[-1])
        return fresh[cycles]

    def _fade(self, fade, t):
        """LFO fade-in after the first key: 0..~5 s."""
        if fade < 0.001:
            return 1.0
        return np.clip((self.lfo_age + t / self.sample_rate) / (fade ** 2 * 5.0), 0.0, 1.0)

    def _filter_envelope(self, frames):
        """Paraphonic filter envelope, per sample (0..1)."""
        p, sr, env = self.params, self.sample_rate, self.fenv
        if env["gate"] and not any(v["gate"] for v in self.voices.values()):
            env.update(gate=False, time=0.0, start=env["level"])
        attack, decay, release = self.env_times(p["fenv_attack"], p["fenv_decay"], p["fenv_release"])
        time = env["time"] + np.arange(frames) / sr
        start = env.get("start", 0.0)
        if env["gate"]:
            sustain = p["fenv_sustain"]
            up = start + (1.0 - start) * np.clip(time / attack, 0.0, 1.0)
            down = sustain + (1.0 - sustain) * np.clip(1.0 - (time - attack) / decay, 0.0, 1.0)
            level = np.where(time < attack, up, down)
        else:
            level = start * np.clip(1.0 - time / release, 0.0, 1.0)
        env["time"] += frames / sr
        env["level"] = float(level[-1])
        return level

    def _reverb(self, left, right):
        """Freeverb-style stereo reverb: 8 damped combs and 4 all-passes per
        side. Every delay is longer than a block chunk, so chunks run as arrays."""
        p = self.params
        x = (left + right) * 0.5 * 0.05
        frames = len(x)
        feedback = 0.75 + 0.235 * p["reverb_size"]
        damp = p["reverb_damp"] * 0.4
        out = []
        for side, lines in enumerate(self.reverb_lines):
            wet = np.zeros(frames)
            for c, (buffer, delay) in enumerate(lines["combs"]):
                wet += self._comb(lines, c, buffer, delay, x, feedback, damp)
            for a, (buffer, delay) in enumerate(lines["allpasses"]):
                wet = self._allpass(lines, a, buffer, delay, wet)
            out.append(wet)
        mix = p["reverb_mix"]
        return left * (1.0 - 0.5 * mix) + out[0] * mix, right * (1.0 - 0.5 * mix) + out[1] * mix

    @staticmethod
    def _comb(lines, c, buffer, delay, x, feedback, damp):
        """Comb with a two-tap damping filter in its loop (block-safe: delay > chunk)."""
        index = lines["comb_index"][c]
        size = len(buffer)
        out = np.empty(len(x))
        for start in range(0, len(x), delay):
            chunk = x[start:start + delay]
            read = (index + np.arange(len(chunk))) % size
            delayed = buffer[read]
            previous = np.concatenate(([lines["comb_last"][c]], delayed[:-1]))
            filtered = (1.0 - damp) * delayed + damp * previous
            buffer[(read + delay) % size] = chunk + filtered * feedback
            lines["comb_last"][c] = float(delayed[-1])
            out[start:start + len(chunk)] = delayed
            index = (index + len(chunk)) % size
        lines["comb_index"][c] = index
        return out

    @staticmethod
    def _allpass(lines, a, buffer, delay, x):
        index = lines["allpass_index"][a]
        size = len(buffer)
        out = np.empty(len(x))
        for start in range(0, len(x), delay):
            chunk = x[start:start + delay]
            read = (index + np.arange(len(chunk))) % size
            delayed = buffer[read]
            buffer[(read + delay) % size] = chunk + delayed * 0.5
            out[start:start + len(chunk)] = delayed - chunk
            index = (index + len(chunk)) % size
        lines["allpass_index"][a] = index
        return out

    def set_sample_rate(self, sample_rate):
        """Follow the output device (e.g. 48 kHz on WASAPI): delay lines are
        sized in samples, so they are rebuilt."""
        with self.lock:
            self.sample_rate = int(sample_rate)
            self.delay_buffer = np.zeros(self.sample_rate * 2, dtype=np.float32)
            self.delay_index = 0
            self._reset_organ()
            self._reset_effects()

    def _reset_effects(self):
        self.phaser_phase = 0.0
        self.phaser_state = [0.0] * 9
        self.mod_fx_phase = 0.0
        self.mod_fx_history = np.zeros(int(MOD_FX_HISTORY * self.sample_rate) + 4)
        scale = self.sample_rate / 44100
        self.reverb_lines = []
        for side in range(2):
            spread = REVERB_SPREAD * side
            combs = [round((d + spread) * scale) for d in REVERB_COMBS]
            allpasses = [round((d + spread) * scale) for d in REVERB_ALLPASSES]
            self.reverb_lines.append({
                "combs": [(np.zeros(2 * d), d) for d in combs],
                "allpasses": [(np.zeros(2 * d), d) for d in allpasses],
                "comb_index": [0] * len(combs), "comb_last": [0.0] * len(combs),
                "allpass_index": [0] * len(allpasses)})

    def _reset_organ(self):
        self.scanner_phase = 0.0
        self.history = size = int(DELAY_HISTORY * self.sample_rate) + 4
        self.scanner_history = np.zeros(size)
        self.horn_history = np.zeros(size)
        self.drum_history = np.zeros(size)
        self.crossover_history = np.zeros(CROSSOVER - 1)
        self.rotor_phase = [0.0, 0.0]            # horn, drum (turns)
        self.rotor_speed = [HORN_SPEED[0], DRUM_SPEED[0]]

    @property
    def waveform(self):
        return WAVES[min(3, round(self.params["osc1_wave"] * 3))]

    @waveform.setter
    def waveform(self, name):
        if name not in WAVES:
            raise ValueError("Unknown waveform")
        self.set_param("osc1_wave", WAVES.index(name) / 3)

    @property
    def volume(self):
        return self.params["volume"]

    @volume.setter
    def volume(self, value):
        self.set_param("volume", value)

    @property
    def cutoff(self):
        return self.params["cutoff"]

    @cutoff.setter
    def cutoff(self, value):
        self.set_param("cutoff", value)

    @property
    def pitch_bend(self):
        return (self.params["pitch_bend"] - 0.5) * 4.0

    @pitch_bend.setter
    def pitch_bend(self, semitones):
        self.set_param("pitch_bend", 0.5 + float(semitones) / 4)

    def set_param(self, name, value):
        name = name.split("@")[0]       # "volume@header": a second control for volume
        if name not in DEFAULTS:
            raise KeyError(name)
        value = max(0.0, min(1.0, float(value)))
        with self.lock:
            self.params[name] = value
            # Switching the arpeggiator (or HOLD with no key down) off lets go
            # of the pattern, so no arpeggio note is left hanging.
            if name == "arp_on" and value < 0.5:
                self._arp_stop()
                self.arp_pressed = set()
            elif name == "arp_hold" and value < 0.5 and not self.arp_pressed:
                self._arp_stop()

    def get_param(self, name):
        with self.lock:
            return self.params[name.split("@")[0]]

    def snapshot(self):
        with self.lock:
            return dict(self.params)

    def load_params(self, values):
        if not isinstance(values, dict):
            raise ValueError("Invalid patch")
        for name, value in values.items():
            if name in DEFAULTS:
                self.set_param(name, value)

    # -- arpeggiator ----------------------------------------------------------
    @property
    def arp_active(self):
        return self.params["arp_on"] >= 0.5

    def arp_bpm(self):
        return 40.0 + 200.0 * self.params["arp_rate"]

    def arp_octaves(self):
        return 1 + round(self.params["arp_oct"] * 3)

    def arp_sequence(self):
        """Notes of one arpeggio cycle for the keys being held (or latched)."""
        keys = self.arp_keys
        if not keys:
            return []
        mode = round(self.params["arp_mode"] * 4)
        base = list(keys) if mode == 4 else sorted(keys)
        up = [note + 12 * octave for octave in range(self.arp_octaves()) for note in base]
        up = [note for note in up if note <= 127]
        if mode == 1:
            return up[::-1]
        if mode == 2:
            return up + up[-2:0:-1]
        return up

    def _arp_step(self):
        """Start the next arpeggio note; returns its length in samples."""
        sequence = self.arp_sequence()
        step = max(1, round(self.sample_rate * 60.0 / (self.arp_bpm() * 4)))
        if self.arp_note is not None:
            self._note_off(self.arp_note)
            self.arp_note = None
        if sequence:
            if round(self.params["arp_mode"] * 4) == 3:
                note = sequence[int(self.rng.integers(len(sequence)))]
            else:
                note = sequence[self.arp_index % len(sequence)]
            self.arp_index += 1
            self._note_on(note, self.arp_velocity)
            self.arp_note = note
            self.arp_gate_left = max(1, round(step * (0.05 + 0.95 * self.params["arp_gate"])))
        return step

    def _arp_stop(self):
        if self.arp_note is not None:
            self._note_off(self.arp_note)
        self.arp_note = None
        self.arp_keys = []
        self.arp_index = 0
        self.arp_clock = 0

    def note_on(self, note, velocity=100):
        note = int(note)
        if not (0 <= note <= 127):
            return
        with self.lock:
            if velocity <= 0:
                return self.note_off(note)
            if self.arp_active:
                if not self.arp_pressed:          # a fresh chord replaces a held one
                    self.arp_keys = []
                    self.arp_index = 0
                    self.arp_clock = 0            # first step right away
                self.arp_pressed.add(note)
                if note not in self.arp_keys:
                    self.arp_keys.append(note)
                self.arp_velocity = velocity
                return
            self._note_on(note, velocity)

    def note_off(self, note):
        with self.lock:
            note = int(note)
            if self.arp_active:
                self.arp_pressed.discard(note)
                if self.params["arp_hold"] < 0.5:
                    if note in self.arp_keys:
                        self.arp_keys.remove(note)
                    if not self.arp_keys:
                        self._arp_stop()
                return
            self._note_off(note)

    def _note_on(self, note, velocity=100):
        with self.lock:
            mode = self.voice_mode
            glide = 0.0
            if self.params["glide_time"] > 0.001 and self.voices:
                glide = self.sounding_pitch() - note
            if mode:
                if note in self.held:
                    self.held.remove(note)
                self.held.append(note)
                current = max(self.voices.values(), key=lambda v: v["serial"], default=None)
                if mode == 2 and current is not None and current["gate"]:
                    # Legato: the sounding voice slides to the new note, no retrigger.
                    self._move_voice(current, note, glide)
                    self.last_note = note
                    return
                attack_from = current["level"] if current is not None else 0.0
                phases = list(current["phases"]) if current is not None else None
                self.voices.clear()
            if len(self.voices) >= self.max_voices and note not in self.voices:
                victim = min(self.voices, key=lambda k: self.voices[k]["serial"])
                del self.voices[victim]
            self.voice_serial += 1
            # Percussion is single-triggered: legato notes don't retrigger it.
            percussion = not any(v["gate"] for n, v in self.voices.items() if n != note)
            if percussion:                  # first key: LFO fade and key sync restart
                self.lfo_age = 0.0
                if self.params["lfo_sync"] >= 0.5:
                    self.lfo_phase = 0.0
                if self.params["lfo2_sync"] >= 0.5:
                    self.lfo2_phase = 0.0
            self.last_note = note
            # Filter envelope retriggers from its current level.
            self.fenv.update(gate=True, time=0.0, start=self.fenv["level"])
            self.voices[note] = {
                "perc": percussion,
                "phases": [0.0] * PHASE_SLOTS, "age": 0.0,
                "level": 0.0, "velocity": min(127, velocity) / 127.0,
                "gate": True, "serial": self.voice_serial,
                "env_time": 0.0, "release_time": 0.0,
                "release_start": 0.0, "mod_level": 0.0, "mod_release_start": 0.0,
                "glide": glide, "attack_from": 0.0,
                # Analog drift seeds: two slow rates and phases, static
                # offsets for OSC1-3 and sub, and the envelope timing spread.
                "drift": self.rng.uniform(0.0, 1.0, 9),
            }
            if mode:
                # Mono and Unison retrigger from the current level (no click).
                self.voices[note]["attack_from"] = attack_from
                if phases is not None:
                    self.voices[note]["phases"] = phases

    @property
    def voice_mode(self):
        return round(self.params["voice_mode"] * 3)

    def sounding_pitch(self):
        """Pitch (note number) of the newest voice, including any glide left."""
        note, voice = max(self.voices.items(), key=lambda item: item[1]["serial"])
        return note + voice.get("glide", 0.0)

    def _move_voice(self, voice, note, glide):
        for key in [k for k, v in self.voices.items() if v is voice]:
            del self.voices[key]
        voice["glide"] = glide if self.params["glide_time"] > 0.001 else 0.0
        self.voice_serial += 1
        voice["serial"] = self.voice_serial
        self.voices[note] = voice

    def _note_off(self, note):
        with self.lock:
            note = int(note)
            if self.voice_mode:
                if note in self.held:
                    self.held.remove(note)
                voice = self.voices.get(note)
                if voice is not None and voice["gate"] and self.held and not self.sustain:
                    # Last-note priority: fall back to the previous held key.
                    back = self.held[-1]
                    self._move_voice(voice, back, note + voice.get("glide", 0.0) - back)
                    self.last_note = back
                    return
            if int(note) in self.voices:
                voice = self.voices[int(note)]
                if self.sustain:
                    voice["sustained"] = True       # released when the pedal lifts
                elif voice["gate"]:
                    self._release(voice)

    @staticmethod
    def _release(voice):
        voice["release_start"] = voice["level"]
        voice["mod_release_start"] = voice.get("mod_level", 0.0)
        voice["release_time"] = 0.0
        voice["gate"] = False
        voice["sustained"] = False

    def set_sustain(self, down):
        with self.lock:
            self.sustain = bool(down)
            if not self.sustain:
                for voice in self.voices.values():
                    if voice.get("sustained") and voice["gate"]:
                        self._release(voice)

    def panic(self):
        with self.lock:
            self.voices.clear()
            self.held = []
            self.arp_keys, self.arp_pressed = [], set()
            self.arp_note, self.arp_index, self.arp_clock = None, 0, 0
            self.sustain = False
            self.lowpass = 0.0
            self.filter_states = [0.0, 0.0, 0.0, 0.0]
            self.delay_buffer.fill(0)
            self.peak = 0.0
            self._reset_organ()
            self._reset_effects()
            self.fenv = {"level": 0.0, "time": 0.0, "gate": False, "from": 0.0}

    def detune(self, osc):
        """Oscillator offset in semitones: tune ±12, octave −2..+2, fine ±50 cents."""
        p = self.params
        octave = round((p[f"osc{osc}_octave"] - 0.5) * 4)
        return (p[f"osc{osc}_tune"] - 0.5) * 24 + octave * 12 + (p[f"osc{osc}_fine"] - 0.5)

    def _electric_piano(self, voices, freq, t, bend_curve):
        """Tine electric piano: 1:1 FM whose brightness fades, a short bell
        'ping', pitch-dependent natural decay and a pickup that barks when
        played hard. Velocity shapes tone and loudness, not only level."""
        p, sr = self.params, self.sample_rate
        age = np.array([voice.get("age", 0.0) for voice in voices])[:, None] + t / sr
        velocity = np.array([voice["velocity"] for voice in voices])[:, None]
        step = (freq / sr)[:, None]
        start = np.array([voice["phases"][EP_SLOT] for voice in voices])[:, None]
        if bend_curve is None:
            ph = start + step * t
            end = start + step * len(t)
        else:
            step = step * bend_curve
            run = np.cumsum(step, axis=1)
            ph = start + run - step
            end = start + run[:, -1:]
        for voice, phase in zip(voices, (end % 1.0)[:, 0]):
            voice["phases"][EP_SLOT] = float(phase)
        angle = 2 * np.pi * ph
        index = (0.3 + 2.4 * p["ep_tone"]) * (0.3 + 0.7 * velocity ** 1.5) * np.exp(-age / 0.5)
        body = np.sin(angle + index * np.sin(angle))
        bell = (0.08 + 0.4 * p["ep_tone"]) * velocity * np.exp(-age / 0.03) * np.sin(7 * angle)
        decay = (0.8 + 5.0 * p["ep_decay"]) * np.sqrt(261.6 / freq)[:, None]
        tone = (body + bell) * np.exp(-age / decay)
        drive = 1.0 + p["ep_bark"] * 5.0 * velocity ** 2
        tone = np.tanh(drive * (tone + 0.2 * p["ep_bark"] * tone * tone)) / np.tanh(drive)
        return tone * (0.3 + 0.7 * velocity) * 1.1

    def _electric_grand(self, voices, freq, t, bend_curve):
        """Electric grand (CP-70 style): hammered stiff strings, so partials run
        slightly sharp; upper partials die first; paired strings beat gently;
        the piezo pickup is bright and barks a little when played hard."""
        p, sr = self.params, self.sample_rate
        frames = len(t)
        start_age = np.array([voice.get("age", 0.0) for voice in voices])[:, None]
        age = start_age + t / sr
        # Envelopes and beating move slowly: evaluated at both block edges and
        # interpolated, so only the partials' sines run per sample.
        edges = np.hstack((start_age, start_age + frames / sr))
        ramp = (t / frames)[None, :]
        velocity = np.array([voice["velocity"] for voice in voices])[:, None]
        stiffness = np.clip(0.00012 * (freq / 130.0) ** 0.9, 0.00005, 0.002)
        sustain = (0.4 + 2.0 * p["ep_decay"]) * (261.6 / freq) ** 0.55
        bright = 1.9 - 0.9 * p["ep_tone"] - 0.6 * velocity           # spectral slope
        tone = np.zeros((len(voices), len(t)))
        for n in range(1, GRAND_PARTIALS + 1):
            hz = freq * n * np.sqrt(1.0 + stiffness * n * n)
            audible = hz < sr * 0.45
            if not audible.any():
                break
            step = (hz / sr)[:, None]
            slot = GRAND_SLOT + n - 1
            start = np.array([voice["phases"][slot] for voice in voices])[:, None]
            if bend_curve is None:
                ph = start + step * t
                end = start + step * len(t)
            else:
                step = step * bend_curve
                run = np.cumsum(step, axis=1)
                ph = start + run - step
                end = start + run[:, -1:]
            for voice, phase in zip(voices, (end % 1.0)[:, 0]):
                voice["phases"][slot] = float(phase)
            tau = (sustain / (1.0 + 0.45 * (n - 1)))[:, None]
            # Two-stage decay (prompt sound, then a longer aftersound) and the
            # slow beating of the string pair.
            gain = (0.75 * np.exp(-edges / tau) + 0.25 * np.exp(-edges / (tau * 3.0))) \
                * (1.0 + 0.12 * np.cos(2 * np.pi * (0.7 + 0.25 * n) * edges)) \
                * n ** -bright * audible[:, None]
            tone += (gain[:, :1] + (gain[:, 1:] - gain[:, :1]) * ramp) * np.sin(2 * np.pi * ph)
        tone = tone * 0.8
        young = start_age[:, 0] < 0.05
        if young.any():         # hammer thump in the first few milliseconds
            a = age[young]
            tone[young] += 0.25 * velocity[young] * np.exp(-a / 0.006) * np.sin(2 * np.pi * 90.0 * a)
        drive = 1.0 + p["ep_bark"] * 4.0 * velocity ** 2
        tone = np.tanh(drive * tone) / np.tanh(drive)
        return tone * (0.3 + 0.7 * velocity)

    @staticmethod
    def env_times(attack, decay, release):
        """Fader positions (0..1) to seconds, shared by the AMP and MOD envelopes."""
        return 0.002 + attack ** 2 * 3.0, 0.01 + decay ** 2 * 2.0, 0.01 + release ** 2 * 4.0

    @staticmethod
    def _adsr(gate, held, gone, start_level, attack, decay, sustain, release, attack_from=0.0):
        """Sample-accurate ADSR; the release starts from the current level and
        the attack from ``attack_from`` (mono retrigger)."""
        up = attack_from + (1.0 - attack_from) * np.clip(held / max(0.002, attack), 0.0, 1.0)
        down = sustain + (1.0 - sustain) * np.clip(
            1.0 - (held - attack) / max(0.005, decay), 0.0, 1.0)
        return np.where(gate, np.where(held < attack, up, down),
                        start_level * np.clip(1.0 - gone / max(0.005, release), 0.0, 1.0))

    @staticmethod
    def _blep(phase, step):
        """PolyBLEP residual that rounds off each wrap of a unit-phase ramp."""
        x = phase / step
        y = (phase - 1.0) / step
        return np.where(phase < step, x + x - x*x - 1.0,
                        np.where(phase > 1.0 - step, y*y + y + y + 1.0, 0.0))

    def _analog(self, voices, freq, t, bend_curve, mod_env, fm_on, lfo, base, fenv):
        """The three oscillators and the sub of every voice, (voice, sample),
        plus the audio-rate filter modulation (octaves) from POLY-MOD and the
        Minimoog modulation. ``base`` offsets the phase slots (unison copies)."""
        p, sr, frames = self.params, self.sample_rate, len(t)
        on = lambda name: p[name] >= 0.5
        sound = np.zeros((len(voices), frames))
        filter_mod = 0.0
        widths = {osc: (np.clip(0.5 - 0.45 * p[f"osc{osc}_pw"] - 0.4 * p[f"osc{osc}_pwm"] * lfo,
                                0.05, 0.95)
                        if p[f"osc{osc}_pw"] > 0 or p[f"osc{osc}_pwm"] > 0 else 0.5)
                  for osc in (1, 2, 3)}
        poly = (p["polymod_env"] > 0.001 or p["polymod_osc"] > 0.001) and (
            on("polymod_freq") or on("polymod_pw") or on("polymod_filter"))
        moog_amount = p["modwheel"] ** 2 if (on("moog_osc") or on("moog_filter")) else 0.0
        # Oscillators needed as sources even when their level is down.
        needed = {3: fm_on[1] or on("osc2_sync") or moog_amount > 0,
                  2: fm_on[0] or on("osc1_sync") or on("osc1_ring")
                  or (poly and p["polymod_osc"] > 0.001)}
        drift = self._drift(voices, t) if p["vintage"] > 0.001 else None
        multiply = lambda a, b: b if a is None else a * b
        outputs, unwrapped, steps = {}, {}, {}
        moog = None
        # POLY-MOD signal: filter envelope now, OSC B added once it is computed.
        poly_signal = p["polymod_env"] * fenv[None, :] if poly else None
        # OSC3 first: it can modulate or sync OSC2, which can modulate or sync OSC1.
        for osc in (3, 2, 1, None):
            if osc is None:
                slot, level, hz = base + 3, p["sub_level"], freq * 0.5
            else:
                slot, level = base + osc - 1, p[f"osc{osc}_level"]
                hz = freq * 2 ** (self.detune(osc) / 12)
            if level < 0.0001 and not needed.get(osc, False):
                continue
            lo = osc == 3 and on("osc3_lo")
            curve = None if lo else bend_curve
            if lo:                  # Minimoog LO range: 0.1..25 Hz on the TUNE knob
                hz = np.full_like(freq, 0.1 * 250 ** p["osc3_tune"])
            if drift is not None and not lo:
                curve = multiply(curve, drift[0] * 2 ** (drift[1][:, [0, 1, 2, 3].index(osc or 0)]
                                                         [:, None] / 1200))
            if osc in (1, 2) and moog is not None and on("moog_osc"):
                curve = multiply(curve, 2 ** (MOOG_SEMITONES * moog_amount * moog / 12))
            if osc == 1 and poly_signal is not None and on("polymod_freq"):
                curve = multiply(curve, 2 ** (POLYMOD_SEMITONES * poly_signal / 12))
            step = (hz / sr)[:, None]
            start = np.array([voice["phases"][slot] for voice in voices])[:, None]
            if curve is None:
                phase = start + step * t
                end = start + step * frames
            else:                   # integrate the per-sample frequency
                step = step * curve
                run = np.cumsum(step, axis=1)
                phase = start + run - step
                end = start + run[:, -1:]
            master = osc + 1 if osc in (1, 2) and on(f"osc{osc}_sync") else None
            if master in unwrapped:
                # Hard sync: restart with the master's cycle, at the slave's speed.
                ph = ((unwrapped[master] % 1.0) * (step / steps[master])) % 1.0
            else:
                ph = phase % 1.0
            unwrapped[osc], steps[osc] = phase, step
            if osc is None:         # sub oscillator: band-limited saw an octave down
                out = 2 * ph - 1 - self._blep(ph, np.minimum(step, 0.5))
            elif osc == 3 and on("osc3_noise"):
                out = self.rng.standard_normal((len(voices), frames)) * 0.5
            else:
                width = widths[osc]
                if osc == 1 and poly_signal is not None and on("polymod_pw"):
                    width = np.clip(width + 0.4 * poly_signal, 0.05, 0.95)
                modulator = outputs.get(osc + 1)
                if fm_on[osc - 1]:
                    index = FM_MAX_INDEX * p[f"osc{osc}_fm"] ** 2 * mod_env / (2 * np.pi)
                    if osc == 3:    # self-feedback, unrolled twice
                        out = self._wave(ph, osc, step, width)
                        for _ in range(2):
                            out = self._wave((ph + index * out) % 1.0, osc, step, width)
                    elif modulator is not None:
                        out = self._wave((ph + index * modulator) % 1.0, osc, step, width)
                    else:
                        out = self._wave(ph, osc, step, width)
                else:
                    out = self._wave(ph, osc, step, width)
                if osc == 1 and on("osc1_ring") and modulator is not None:
                    out = out * modulator
            outputs[osc] = out
            if osc == 3 and moog_amount > 0:
                # Modulation mix: OSC3 and (smoothed) noise.
                noise = self.rng.standard_normal((len(voices), frames))
                noise = np.cumsum(noise, axis=1) * 0.05
                noise -= noise.mean(axis=1, keepdims=True)
                moog = (1.0 - p["moog_mix"]) * out + p["moog_mix"] * np.clip(noise, -1.0, 1.0)
                if on("moog_filter"):
                    filter_mod = filter_mod + 3.0 * moog_amount * moog.mean(axis=0)
            if osc == 2 and poly and p["polymod_osc"] > 0.001:
                poly_signal = poly_signal + p["polymod_osc"] * out
            if level >= 0.0001:
                sound += level * out
            for voice, value in zip(voices, (end % 1.0)[:, 0]):
                voice["phases"][slot] = float(value)
        if poly and on("polymod_filter"):
            filter_mod = filter_mod + 4.0 * poly_signal.mean(axis=0)
        return sound, filter_mod

    def _drift(self, voices, t):
        """VINTAGE: slow per-voice pitch wander (two sines, a few cents) and a
        fixed small detune per oscillator. Evaluated at the block edges and
        interpolated (it moves far slower than a block)."""
        p, sr = self.params, self.sample_rate
        seeds = np.array([voice["drift"] for voice in voices])
        age = np.array([voice.get("age", 0.0) for voice in voices])[:, None]
        edges = np.hstack((age, age + len(t) / sr))
        rates = 0.05 + 0.35 * seeds[:, :2]
        cents = p["vintage"] * (5.0 * np.sin(2 * np.pi * (rates[:, :1] * edges + seeds[:, 2:3]))
                                + 3.0 * np.sin(2 * np.pi * (rates[:, 1:2] * edges + seeds[:, 3:4])))
        ramp = (t / len(t))[None, :]
        cents = cents[:, :1] + (cents[:, 1:] - cents[:, :1]) * ramp
        static = p["vintage"] * 8.0 * (seeds[:, 4:8] - 0.5)
        return 2 ** (cents / 1200), static

    def _highpass(self, x, amount):
        """One-pole high-pass, 20 Hz .. ~2 kHz (Jupiter-8 style, no resonance)."""
        hz = 20.0 * 100.0 ** amount
        a = 1.0 / (1.0 + 2.0 * math.pi * hz / self.sample_rate)
        x_prev, y_prev = self.hpf_state
        out = []
        store = out.append
        for sample in x.tolist():
            y_prev = a * (y_prev + sample - x_prev)
            x_prev = sample
            store(y_prev)
        self.hpf_state = (x_prev, y_prev)
        return np.asarray(out)

    def _wave(self, phase, which, step, width=0.5):
        # Saw and pulse are band-limited with PolyBLEP so high notes do not
        # alias; triangle and sine are left as is (little or no aliasing).
        idx = min(3, round(self.params[f"osc{which}_wave"] * 3))
        step = np.minimum(step, 0.5)
        if idx == 1:
            if np.ndim(width) == 0 and width == 0.5:
                square = np.where(phase < 0.5, 1.0, -1.0)
                return square + self._blep(phase, step) - self._blep((phase + 0.5) % 1.0, step)
            # Variable width: two band-limited edges, DC removed.
            pulse = np.where(phase < width, 1.0, -1.0)
            pulse = pulse + self._blep(phase, step) - self._blep((phase + 1.0 - width) % 1.0, step)
            return pulse - (2.0 * width - 1.0)
        if idx == 2:
            return 1.0 - 4.0 * np.abs(phase - 0.5)
        if idx == 3:
            return np.sin(phase * (2 * np.pi))
        return phase * 2.0 - 1.0 - self._blep(phase, step)

    def render(self, frames):
        """Audio for ``frames`` samples. With the arpeggiator running, the block
        is cut at each arpeggio step and gate end, so timing is sample exact."""
        frames = int(frames)
        if frames <= 0:
            return np.empty((0, 2), dtype=np.float32)
        with self.lock:
            if not (self.arp_active and (self.arp_keys or self.arp_note is not None)):
                return self._render(frames)
            parts, done = [], 0
            while done < frames:
                if self.arp_clock <= 0 and self.arp_keys:
                    self.arp_clock = self._arp_step()
                elif self.arp_clock <= 0:
                    self.arp_clock = frames
                if self.arp_note is not None and self.arp_gate_left <= 0:
                    self._note_off(self.arp_note)
                    self.arp_note = None
                length = min(frames - done, self.arp_clock)
                if self.arp_note is not None:
                    length = min(length, self.arp_gate_left)
                length = max(1, length)
                parts.append(self._render(length))
                done += length
                self.arp_clock -= length
                self.arp_gate_left -= length
            peak = max(float(np.max(np.abs(part))) for part in parts)
            out = np.concatenate(parts)
            self.peak = peak
            return out

    def _render(self, frames):
        with self.lock:
            t = np.arange(frames, dtype=np.float64)
            mono = np.zeros(frames, dtype=np.float64)
            sr = self.sample_rate
            p = self.params
            attack, decay, release = self.env_times(p["attack"], p["decay"], p["release"])
            sustain = p["sustain"]
            bend = (p["pitch_bend"] - 0.5) * 4.0
            # All voices are rendered together as (voice, sample) arrays; a
            # per-voice loop of small numpy calls costs more than the maths.
            # LFO 2 is a vibrato, deepened by the mod wheel (up to ±0.6 semitone).
            # The mod wheel deepens the vibrato, unless it drives the Minimoog
            # modulation (OSC MOD / FILT MOD on).
            moog_on = p["moog_osc"] >= 0.5 or p["moog_filter"] >= 0.5
            vibrato = min(1.0, p["lfo2_depth"] + (0.0 if moog_on else p["modwheel"])) * 0.6
            fenv = self._filter_envelope(frames)
            filter_mod = 0.0
            vib_rate = (0.1 + 9.9 * p["lfo2_rate"] ** 2) / sr
            bend_curve = None
            if vibrato > 1e-6:
                wave = self._lfo_wave(1, self.lfo2_phase + vib_rate * t, p["lfo2_wave"])
                bend_curve = 2 ** (vibrato * wave * self._fade(p["lfo2_fade"], t) / 12)[None, :]
            self.lfo2_phase = (self.lfo2_phase + frames * vib_rate) % 1.0
            # LFO 1 (tremolo and PWM), evaluated per sample so it has no steps.
            rate = (0.05 + 13 * p["lfo_rate"] ** 2) / sr
            lfo = self._lfo_wave(0, self.lfo_phase + rate * t, p["lfo_wave"])
            self.lfo_phase = (self.lfo_phase + frames * rate) % 1.0
            # Organ and electric piano have no synth filter: they are mixed
            # after the ladder, like the real instruments.
            keys_mono = np.zeros(frames, dtype=np.float64)
            organ_mono = np.zeros(frames, dtype=np.float64)
            playing = list(self.voices.items())
            if playing:
                voices = [voice for _, voice in playing]
                freq = 440.0 * 2 ** ((np.array([note for note, _ in playing], dtype=np.float64)
                                      - 69 + bend) / 12)
                # Glide: each voice starts off-pitch by "glide" semitones and
                # settles exponentially; it multiplies into the pitch curve.
                glides = np.array([voice.get("glide", 0.0) for voice in voices])
                if np.any(glides):
                    tau = (0.01 + p["glide_time"] ** 2 * 1.5) * sr
                    offset = glides[:, None] * np.exp(-(t + 1)[None, :] / tau)
                    glide_curve = 2 ** (offset / 12)
                    bend_curve = glide_curve if bend_curve is None else glide_curve * bend_curve
                    for voice, left in zip(voices, offset[:, -1]):
                        voice["glide"] = float(left) if abs(left) > 0.005 else 0.0
                sound = np.zeros((len(voices), frames), dtype=np.float64)
                gate = np.array([voice["gate"] for voice in voices])[:, None]
                held = np.array([voice["env_time"] for voice in voices])[:, None] + t / sr
                gone = np.array([voice["release_time"] for voice in voices])[:, None] + t / sr
                if p["vintage"] > 0.001:
                    # Each voice's envelopes run a little faster or slower.
                    spread = 1.0 + p["vintage"] * 0.3 * (np.array([v["drift"][8] for v in voices]) - 0.5)
                    held, gone = held * spread[:, None], gone * spread[:, None]
                velocity = np.array([voice["velocity"] for voice in voices])[:, None]
                fm_on = [p[f"osc{osc}_fm_on"] >= 0.5 for osc in (1, 2, 3)]
                mod_env = None
                if any(fm_on):
                    m_attack, m_decay, m_release = self.env_times(
                        p["mod_attack"], p["mod_decay"], p["mod_release"])
                    mod_env = self._adsr(
                        gate, held, gone,
                        np.array([voice["mod_release_start"] for voice in voices])[:, None],
                        m_attack, m_decay, p["mod_sustain"], m_release)
                    for voice, level in zip(voices, mod_env[:, -1]):
                        voice["mod_level"] = float(level)
                    mod_env = mod_env * (0.5 + 0.5 * velocity)
                if self.voice_mode == 3:
                    # Unison: four detuned copies of the oscillators per voice.
                    spread = p["unison_detune"] * UNISON_CENTS / 1200
                    for copy in range(UNISON_COPIES):
                        cents = spread * (2 * copy / (UNISON_COPIES - 1) - 1)
                        copy_sound, copy_mod = self._analog(
                            voices, freq * 2 ** cents, t, bend_curve, mod_env, fm_on, lfo,
                            UNISON_SLOT + 4 * copy, fenv)
                        sound += 0.5 * copy_sound
                        filter_mod = filter_mod + copy_mod / UNISON_COPIES
                else:
                    voice_sound, filter_mod = self._analog(voices, freq, t, bend_curve, mod_env,
                                                           fm_on, lfo, 0, fenv)
                    sound += voice_sound
                organ = np.zeros_like(sound)
                perc_bar, perc_amp = None, 0.0
                if p["organ_perc"] >= 0.5:
                    perc_bar = PERC_BARS[p["organ_perc_third"] >= 0.5]
                    tau = 0.12 if p["organ_perc_fast"] >= 0.5 else 0.45
                    age = np.array([voice["age"] for voice in voices])[:, None] + t / sr
                    struck = np.array([voice.get("perc", False) for voice in voices])[:, None]
                    perc_amp = 0.3 * struck * np.exp(-age / tau)
                # Drawbar organ: one sine per drawbar, 0..8 in ~3 dB steps.
                for index, (_, ratio) in enumerate(DRAWBARS):
                    position = round(p[f"drawbar{index + 1}"] * 8)
                    if perc_bar is not None and index == len(DRAWBARS) - 1:
                        position = 0            # percussion takes the 1' bus
                    if position == 0 and index != perc_bar:
                        continue
                    level = 0.32 * 10 ** (-(8 - position) * 3 / 20) if position else 0.0
                    if index == perc_bar:
                        level = level + perc_amp
                    hz = freq * ratio
                    for _ in range(4):
                        hz = np.where(hz > TONEWHEEL_TOP, hz / 2, hz)
                    step = (hz / sr)[:, None]
                    slot = 4 + index
                    start = np.array([voice["phases"][slot] for voice in voices])[:, None]
                    if bend_curve is None:
                        ph = start + step * t
                        end = start + step * frames
                    else:
                        step = step * bend_curve
                        run = np.cumsum(step, axis=1)
                        ph = start + run - step
                        end = start + run[:, -1:]
                    organ += level * np.sin(2 * np.pi * ph)
                    for voice, phase in zip(voices, (end % 1.0)[:, 0]):
                        voice["phases"][slot] = float(phase)
                organ_on = perc_bar is not None or any(
                    p[f"drawbar{i}"] > 0 for i in range(1, len(DRAWBARS) + 1))
                if organ_on and p["organ_click"] >= 0.5:
                    # Key contacts closing: a few ms of bright noise per new note.
                    for row, voice in enumerate(voices):
                        if voice["age"] < 0.02:
                            age = voice["age"] + t / sr
                            noise = self.rng.standard_normal(frames)
                            noise = noise - np.concatenate(([0.0], noise[:-1])) * 0.6
                            organ[row] += 0.22 * noise * np.exp(-age / 0.0025)
                keys = np.zeros_like(sound)
                if p["ep_level"] > 0.0001:
                    engine = (self._electric_grand if p["ep_model"] >= 0.5
                              else self._electric_piano)
                    keys += p["ep_level"] * engine(voices, freq, t, bend_curve)
                if p["noise_level"] > 0:
                    sound += p["noise_level"] * self.rng.standard_normal(sound.shape) * 0.5
                # Sample-accurate ADSR with release from current amplitude.
                start_level = np.array([voice["release_start"] for voice in voices])[:, None]
                attack_from = np.array([voice.get("attack_from", 0.0) for voice in voices])[:, None]
                env = self._adsr(gate, held, gone, start_level, attack, decay, sustain, release,
                                 attack_from)
                mono += (sound * env * velocity).sum(axis=0)
                keys_mono += (keys * env).sum(axis=0)
                organ_mono += (organ * env).sum(axis=0)
                for (note, voice), level in zip(playing, env[:, -1]):
                    voice["level"] = float(level)
                    voice["age"] = voice.get("age", 0.0) + frames / sr
                    if voice["gate"]:
                        voice["env_time"] += frames / sr
                    else:
                        voice["release_time"] += frames / sr
                        if voice["release_time"] > release:
                            del self.voices[note]
            active = max(1, len(self.voices))
            mono /= max(1.5, math.sqrt(active) * 1.5)
            keys_mono /= max(1.5, math.sqrt(active) * 1.5)
            organ_mono /= max(1.5, math.sqrt(active) * 1.5)
            # Four-pole resonant subtractive filter, vintage-ladder inspired.
            # Soft nonlinear feedback is intentionally bounded to avoid runaway.
            # Cutoff in octaves: knob, key tracking (last note) and the filter
            # envelope; per sample only while the envelope is on.
            octaves = p["cutoff"] * 8.3 + p["key_track"] * (self.last_note - 60) / 12
            if p["filter_env_on"] >= 0.5 or np.ndim(filter_mod):
                if p["filter_env_on"] >= 0.5:
                    octaves = octaves + FILTER_ENV_OCTAVES * fenv
                hz = np.minimum(sr * 0.40, 55 * 2 ** (octaves + filter_mod))
                coefficients = np.minimum(0.94, 1.0 - np.exp(-2.0 * np.pi * hz / sr)).tolist()
            else:
                hz = min(sr * 0.40, 55 * (2 ** octaves))
                coefficients = None
            g = min(0.94, 1.0 - math.exp(-2.0 * math.pi * float(np.max(hz)) / sr))
            feedback = p["resonance"] * 3.4
            drive = 1 + p["drive"] * 1.5
            tanh = math.tanh
            s0, s1, s2, s3 = self.filter_states
            # The ladder is recursive, so it runs per sample; plain floats and
            # a local tanh keep it about 5x faster than indexing numpy arrays.
            filtered = []
            store = filtered.append
            mode = round(p["filter_type"] * 3)
            if mode == 0 and coefficients is None:
                for sample in mono.tolist():
                    x = tanh(sample * drive - feedback * s3)
                    s0 += g * (x - s0)
                    s1 += g * (s0 - s1)
                    s2 += g * (s1 - s2)
                    s3 += g * (s2 - s3)
                    store(s3)
            else:
                # Stage mixes of the same ladder (Xpander style):
                # LP12 = y2, BP12 = y1 - y2, HP12 = x - 2y1 + y2 (with make-up gain).
                for sample, g in zip(mono.tolist(), coefficients or [g] * frames):
                    x = tanh(sample * drive - feedback * s3)
                    s0 += g * (x - s0)
                    s1 += g * (s0 - s1)
                    s2 += g * (s1 - s2)
                    s3 += g * (s2 - s3)
                    store(s3 if mode == 0 else s1 if mode == 1 else
                          3.0 * (s0 - s1) if mode == 2 else 2.0 * (x - 2.0 * s0 + s1))
            self.filter_states = [s0, s1, s2, s3]
            mono = np.asarray(filtered) * (1.0 + p["resonance"] * 0.7)
            self.lowpass = s3
            if p["hpf"] > 0.001:
                mono = self._highpass(mono, p["hpf"])
            organ_mono, side = self._organ_effects(organ_mono, t)
            mono += keys_mono + organ_mono
            if p["tube_drive"] > 0.001:
                mono = self._tube(mono, p["tube_drive"])
                if side is not None:
                    side = side * (1.0 + 2.0 * p["tube_drive"]) ** -0.3
            depth = p["lfo_depth"] * self._fade(p["lfo_fade"], t)
            tremolo = (1.0 - depth * 0.5) + depth * 0.5 * (1.0 + lfo)
            self.lfo_age += frames / sr
            mono *= tremolo
            mono = np.tanh(mono * (1.0 + p["drive"] * 2)) * p["volume"] * 0.8
            # Feedback delay. The shortest delay is longer than any chunk, so a
            # chunk only reads samples written by earlier chunks and can be
            # processed as whole arrays.
            mix = p["delay_mix"]
            buffer = self.delay_buffer
            size = len(buffer)
            if mix > 0.00001:
                period = max(1, int(sr * (0.06 + p["delay_time"] * 0.65)))
                for start in range(0, frames, period):
                    dry = mono[start:start + period]
                    write = (self.delay_index + np.arange(len(dry))) % size
                    delayed = buffer[(write - period) % size].astype(np.float64)
                    buffer[write] = dry + delayed * p["delay_feedback"] * 0.75
                    mono[start:start + period] = dry * (1.0 - mix) + delayed * mix
                    self.delay_index = (self.delay_index + len(dry)) % size
            else:
                self.delay_index = (self.delay_index + frames) % size
            mono = self._phaser(mono, t)
            left, right = self._chorus(mono, t)
            if p["reverb_on"] >= 0.5:
                left, right = self._reverb(left, right)
            if side is None and left is right:
                mono = np.clip(left, -0.95, 0.95).astype(np.float32)
                self.peak = float(np.max(np.abs(mono)))
                return np.column_stack((mono, mono))
            if side is not None:
                # The Leslie's stereo spread rides on top of the mono chain.
                side = side * tremolo * p["volume"] * 0.8
                left, right = left + side, right - side
            if p["width"] != 0.5:
                # WIDTH: 0 = mono, 0.5 = as produced, 1 = twice as wide.
                mid, spread = (left + right) * 0.5, (left - right) * p["width"]
                left, right = mid + spread, mid - spread
            stereo = np.clip(np.column_stack((left, right)), -0.95, 0.95)
            stereo = stereo.astype(np.float32)
            self.peak = float(np.max(np.abs(stereo)))
            return stereo

    @staticmethod
    def _tube(x, amount):
        """Triode-like stage: biased so it clips asymmetrically (even harmonics),
        with the level roughly kept as the drive goes up."""
        gain = 1.0 + 9.0 * amount ** 2
        bias = 0.3 * amount
        return (np.tanh(gain * x + bias) - math.tanh(bias)) / gain ** 0.55

    def _phaser(self, x, t):
        """Four first-order all-pass stages swept by an LFO, with feedback."""
        p, sr = self.params, self.sample_rate
        if p["phaser_on"] < 0.5:
            self.phaser_state = [0.0] * 9
            return x
        rate = (0.05 + 4.95 * p["phaser_rate"] ** 2) / sr
        lfo = 0.5 + 0.5 * np.sin(2 * np.pi * (self.phaser_phase + rate * t))
        self.phaser_phase = (self.phaser_phase + rate * len(x)) % 1.0
        low, span = 180.0, 1.0 + 4.0 * p["phaser_depth"]          # up to ~5 octaves
        hz = np.minimum(low * 2 ** (span * lfo), sr * 0.4)
        tan = np.tan(np.pi * hz / sr)
        coef = ((tan - 1.0) / (tan + 1.0)).tolist()
        feedback = 0.25 + 0.45 * p["phaser_depth"]
        x1a, y1a, x1b, y1b, x1c, y1c, x1d, y1d, last = self.phaser_state
        out = []
        store = out.append
        for sample, a in zip(x.tolist(), coef):
            v = sample + feedback * last
            y1a = a * v + x1a - a * y1a; x1a = v
            y1b = a * y1a + x1b - a * y1b; x1b = y1a
            y1c = a * y1b + x1c - a * y1c; x1c = y1b
            y1d = a * y1c + x1d - a * y1d; x1d = y1c
            last = y1d
            store(y1d)
        self.phaser_state = [x1a, y1a, x1b, y1b, x1c, y1c, x1d, y1d, last]
        return 0.7 * (x + np.asarray(out))

    def _chorus(self, x, t):
        """Stereo chorus (two voices swept in opposite phase) or a flanger
        (short swept delay with feedback). Returns (left, right)."""
        p, sr = self.params, self.sample_rate
        history = self.mod_fx_history
        if p["chorus_on"] < 0.5:
            self.mod_fx_history = np.concatenate((history, x))[-len(history):]
            return x, x
        frames = len(x)
        kind = round(p["chorus_type"] * 4)
        if kind in JUNO_CHORUS:
            # Juno: a triangle LFO sweeps the BBD delay, opposite on each side;
            # the modes are fixed, as on the instrument (DEPTH/RATE unused).
            hz, centre, sweep_ms = JUNO_CHORUS[kind]
            rate = hz / sr
            phase = (self.mod_fx_phase + rate * t) % 1.0
            tri = 1.0 - 4.0 * np.abs(phase - 0.5)
            centre, depth = centre * 0.001 * sr, sweep_ms * 0.001 * sr
            left, _ = modulated_delay(history, x, centre + depth * tri)
            right, _ = modulated_delay(history, x, centre - depth * tri)
            self.mod_fx_history = np.concatenate((history, x))[-len(history):]
            self.mod_fx_phase = (self.mod_fx_phase + rate * frames) % 1.0
            return 0.7 * x + 0.6 * left, 0.7 * x + 0.6 * right
        if kind == 0:
            rate = (0.1 + 4.9 * p["chorus_rate"] ** 2) / sr
            sweep = 2 * np.pi * (self.mod_fx_phase + rate * t)
            centre, depth = 0.007 * sr, 0.0035 * sr * p["chorus_depth"]
            left, _ = modulated_delay(history, x, centre + depth * np.sin(sweep))
            right, _ = modulated_delay(history, x, centre + depth * np.sin(sweep + np.pi))
            self.mod_fx_history = np.concatenate((history, x))[-len(history):]
            self.mod_fx_phase = (self.mod_fx_phase + rate * frames) % 1.0
            return 0.7 * x + 0.55 * left, 0.7 * x + 0.55 * right
        # Flanger: 0.3..~6 ms sweep, feedback through the delay line. Each
        # chunk is shorter than the shortest delay, so it only reads samples
        # already written.
        rate = (0.03 + 1.97 * p["chorus_rate"] ** 2) / sr
        lfo = 0.5 - 0.5 * np.cos(2 * np.pi * (self.mod_fx_phase + rate * t))
        self.mod_fx_phase = (self.mod_fx_phase + rate * frames) % 1.0
        shortest = 0.0003 * sr
        delay = shortest + 0.0055 * sr * p["chorus_depth"] * lfo
        feedback = 0.55
        chunk = max(1, int(delay.min()) - 1)
        line = np.concatenate((history, np.zeros(frames)))
        h = len(history)
        wet = np.empty(frames)
        for start in range(0, frames, chunk):
            stop = min(frames, start + chunk)
            pos = h + np.arange(start, stop) - delay[start:stop]
            index = np.floor(pos).astype(np.int64)
            frac = pos - index
            delayed = line[index] * (1.0 - frac) + line[index + 1] * frac
            line[h + start:h + stop] = x[start:stop] + feedback * delayed
            wet[start:stop] = delayed
        self.mod_fx_history = line[-h:]
        out = 0.6 * x + 0.6 * wet
        return out, out

    def _organ_effects(self, x, t):
        """Organ chain: scanner vibrato/chorus, overdrive, then the Leslie.
        Returns the mid signal and the Leslie's stereo side (or None)."""
        p, sr = self.params, self.sample_rate
        if not (x.any() or self.scanner_history.any() or self.horn_history.any()
                or self.drum_history.any()):
            self._spin_rotors(t)
            return x, None
        frames = len(x)
        # Scanner vibrato (~6.9 Hz, about ±25 cents); chorus mixes in the dry tone.
        rate = 6.9 / sr
        sweep = np.sin(2 * np.pi * (self.scanner_phase + rate * t))
        self.scanner_phase = (self.scanner_phase + rate * frames) % 1.0
        depth = 0.00026 * sr
        wet, self.scanner_history = modulated_delay(self.scanner_history, x,
                                                    1.0 + depth * (1.0 + sweep))
        if p["organ_vibrato"] >= 0.5:
            x = 0.5 * (x + wet) if p["organ_chorus"] >= 0.5 else wet
        # Tube-style overdrive: asymmetric, so it adds even harmonics.
        if p["organ_drive"] > 0.001:
            gain = 1.0 + 14.0 * p["organ_drive"] ** 2
            bias = 0.25 * p["organ_drive"]
            x = (np.tanh(gain * x + bias) - math.tanh(bias)) / gain ** 0.4
        horn_turns, drum_turns = self._spin_rotors(t)
        line = np.concatenate((self.crossover_history, x))
        total = np.cumsum(np.concatenate(([0.0], line)))
        drum = (total[CROSSOVER:] - total[:-CROSSOVER]) / CROSSOVER
        self.crossover_history = line[len(line) - (CROSSOVER - 1):]
        horn = x - drum
        if p["leslie"] < 0.5:
            self.horn_history = np.concatenate((self.horn_history, horn))[-self.history:]
            self.drum_history = np.concatenate((self.drum_history, drum))[-self.history:]
            return x, None
        # Two microphones 90° apart: each hears the rotors' Doppler (delay)
        # and the swirl of level as horn and drum point towards and away.
        channels = []
        horn_line = np.concatenate((self.horn_history, horn))
        drum_line = np.concatenate((self.drum_history, drum))
        for mic in (0.0, 0.25):
            ha = 2 * np.pi * (horn_turns - mic)
            da = 2 * np.pi * (drum_turns - mic)
            h, _ = modulated_delay(self.horn_history, horn, 1.0 + 0.0003 * sr * (1.0 + np.sin(ha)))
            d, _ = modulated_delay(self.drum_history, drum, 1.0 + 0.0001 * sr * (1.0 + np.sin(da)))
            channels.append(h * (1.0 + 0.45 * np.cos(ha)) * 0.8 + d * (1.0 + 0.25 * np.cos(da)))
        self.horn_history = horn_line[-self.history:]
        self.drum_history = drum_line[-self.history:]
        left, right = channels
        return (left + right) * 0.5, (left - right) * 0.5

    def _spin_rotors(self, t):
        """Rotor angles (turns) per sample; speeds glide to slow/fast with inertia."""
        sr, fast = self.sample_rate, self.params["leslie_fast"] >= 0.5
        turns = []
        for rotor, (speeds, inertia) in enumerate(((HORN_SPEED, HORN_INERTIA),
                                                   (DRUM_SPEED, DRUM_INERTIA))):
            target = speeds[fast]
            tau = inertia[fast] * sr
            speed = target + (self.rotor_speed[rotor] - target) * np.exp(-(t + 1) / tau)
            angle = self.rotor_phase[rotor] + np.cumsum(speed) / sr
            turns.append(angle - speed / sr)
            self.rotor_phase[rotor] = float(angle[-1] % 1.0)
            self.rotor_speed[rotor] = float(speed[-1])
        return turns
