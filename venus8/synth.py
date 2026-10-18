"""Venus-8 v0.2 synthesis core. All note/parameter mutations share one lock."""
import math
import threading

import numpy as np

WAVES = ("Saw", "Pulse", "Triangle", "Sine")
DEFAULTS = {
    "osc1_level": 0.75, "osc2_level": 0.48, "osc3_level": 0.30,
    "osc1_tune": 0.5, "osc2_tune": 0.51, "osc3_tune": 0.49,
    "osc1_wave": 0.0, "osc2_wave": 0.0, "osc3_wave": 0.0,
    "sub_level": 0.15, "noise_level": 0.0,
    "cutoff": 0.72, "resonance": 0.20, "drive": 0.12,
    "attack": 0.06, "decay": 0.40, "sustain": 0.72, "release": 0.30,
    "lfo_rate": 0.25, "lfo_depth": 0.0, "lfo2_rate": 0.2, "lfo2_depth": 0.0,
    "delay_mix": 0.0, "delay_time": 0.28, "delay_feedback": 0.25,
    "volume": 0.36, "pitch_bend": 0.5, "modwheel": 0.0,
}

class Synth:
    def __init__(self, sample_rate=44100, max_voices=16):
        self.sample_rate = int(sample_rate)
        self.max_voices = int(max_voices)
        self.lock = threading.RLock()
        self.params = dict(DEFAULTS)
        self.voices = {}
        self.voice_serial = 0
        self.lowpass = 0.0
        self.lfo_phase = 0.0
        self.delay_buffer = np.zeros(self.sample_rate * 2, dtype=np.float32)
        self.delay_index = 0
        self.peak = 0.0

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
        if name not in DEFAULTS:
            raise KeyError(name)
        value = max(0.0, min(1.0, float(value)))
        with self.lock:
            self.params[name] = value

    def get_param(self, name):
        with self.lock:
            return self.params[name]

    def snapshot(self):
        with self.lock:
            return dict(self.params)

    def load_params(self, values):
        if not isinstance(values, dict):
            raise ValueError("Invalid patch")
        for name, value in values.items():
            if name in DEFAULTS:
                self.set_param(name, value)

    def note_on(self, note, velocity=100):
        note = int(note)
        if not (0 <= note <= 127):
            return
        with self.lock:
            if velocity <= 0:
                return self.note_off(note)
            if len(self.voices) >= self.max_voices and note not in self.voices:
                victim = min(self.voices, key=lambda k: self.voices[k]["serial"])
                del self.voices[victim]
            self.voice_serial += 1
            self.voices[note] = {
                "phases": [0.0, 0.0, 0.0, 0.0],
                "level": 0.0, "velocity": min(127, velocity) / 127.0,
                "gate": True, "serial": self.voice_serial,
            }

    def note_off(self, note):
        with self.lock:
            if int(note) in self.voices:
                self.voices[int(note)]["gate"] = False

    def panic(self):
        with self.lock:
            self.voices.clear()
            self.lowpass = 0.0
            self.delay_buffer.fill(0)
            self.peak = 0.0

    def _wave(self, phase, which):
        # Band-limiting is planned; the prototype uses basic waves.
        idx = min(3, round(self.params[f"osc{which}_wave"] * 3))
        if idx == 1:
            return np.where(phase < 0.5, 1.0, -1.0)
        if idx == 2:
            return 1.0 - 4.0 * np.abs(phase - 0.5)
        if idx == 3:
            return np.sin(phase * (2 * np.pi))
        return phase * 2.0 - 1.0

    def render(self, frames):
        frames = int(frames)
        if frames <= 0:
            return np.empty((0, 2), dtype=np.float32)
        with self.lock:
            t = np.arange(frames, dtype=np.float64)
            mono = np.zeros(frames, dtype=np.float64)
            sr = self.sample_rate
            p = self.params
            attack = 0.002 + p["attack"] ** 2 * 3.0
            release = 0.01 + p["release"] ** 2 * 4.0
            decay = 0.01 + p["decay"] ** 2 * 2.0
            sustain = p["sustain"]
            bend = (p["pitch_bend"] - 0.5) * 4.0
            fade_a = min(1.0, 1.0 / (max(0.002, attack) * sr))
            fade_r = min(1.0, 1.0 / (max(0.005, release) * sr))
            for note, voice in list(self.voices.items()):
                freq = 440.0 * 2 ** ((note - 69 + bend) / 12)
                sound = np.zeros(frames, dtype=np.float64)
                for osc in (1, 2, 3):
                    level = p[f"osc{osc}_level"]
                    if level < 0.0001:
                        continue
                    tune = (p[f"osc{osc}_tune"] - 0.5) * 24
                    f = freq * 2 ** (tune / 12)
                    ph = (voice["phases"][osc - 1] + (f / sr) * t) % 1.0
                    sound += level * self._wave(ph, osc)
                    voice["phases"][osc - 1] = (voice["phases"][osc - 1] + f * frames / sr) % 1.0
                if p["sub_level"] > 0:
                    ph = (voice["phases"][3] + freq * 0.5 * t / sr) % 1.0
                    sound += p["sub_level"] * (2 * ph - 1)
                    voice["phases"][3] = (voice["phases"][3] + freq * 0.5 * frames / sr) % 1.0
                if p["noise_level"] > 0:
                    sound += p["noise_level"] * np.random.default_rng().standard_normal(frames) * 0.5
                # Linear per-buffer envelope, with gradual release after note-off.
                start = voice["level"]
                target = 1.0 if voice["gate"] else 0.0
                step = fade_a if voice["gate"] else fade_r
                end = start + (target - start) * min(1.0, step * frames)
                env = np.linspace(start, end, frames, endpoint=True)
                voice["level"] = end
                # Decay/Sustain intentionally reserved for a later ADSR pass.
                mono += sound * env * voice["velocity"]
                if not voice["gate"] and end < 0.0005:
                    del self.voices[note]
            active = max(1, len(self.voices))
            mono /= max(1.5, math.sqrt(active) * 1.5)
            # One-pole low-pass applied after mixing. Resonance is not yet DSP-active.
            hz = 65 * (2 ** (p["cutoff"] * 7.7))
            alpha = 1.0 - math.exp(-2 * math.pi * hz / sr)
            prev = self.lowpass
            for i in range(frames):
                prev += alpha * (mono[i] - prev)
                mono[i] = prev
            self.lowpass = prev
            self.lfo_phase = (self.lfo_phase + frames * (0.05 + 13 * p["lfo_rate"] ** 2) / sr) % 1.0
            lfo = math.sin(self.lfo_phase * 2 * math.pi)
            mono *= (1.0 - p["lfo_depth"] * 0.5) + p["lfo_depth"] * 0.5 * (1.0 + lfo)
            mono = np.tanh(mono * (1.0 + p["drive"] * 2)) * p["volume"] * 0.8
            # Feedback delay (buffer wraps safely across blocks).
            mix = p["delay_mix"]
            if mix > 0.00001:
                period = max(1, int(sr * (0.06 + p["delay_time"] * 0.65)))
                for i in range(frames):
                    ix = (self.delay_index - period) % len(self.delay_buffer)
                    delayed = float(self.delay_buffer[ix])
                    dry = mono[i]
                    self.delay_buffer[self.delay_index] = dry + delayed * p["delay_feedback"] * 0.75
                    mono[i] = dry * (1.0 - mix) + delayed * mix
                    self.delay_index = (self.delay_index + 1) % len(self.delay_buffer)
            else:
                self.delay_index = (self.delay_index + frames) % len(self.delay_buffer)
            mono = np.clip(mono, -0.95, 0.95).astype(np.float32)
            self.peak = float(np.max(np.abs(mono)))
            return np.column_stack((mono, mono))
