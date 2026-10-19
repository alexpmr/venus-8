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
        self.lfo_phase = 0.0
        self.rng = np.random.default_rng()
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
        name = name.split("@")[0]       # "volume@header": a second control for volume
        if name not in DEFAULTS:
            raise KeyError(name)
        value = max(0.0, min(1.0, float(value)))
        with self.lock:
            self.params[name] = value

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
                "env_time": 0.0, "release_time": 0.0,
                "release_start": 0.0,
            }

    def note_off(self, note):
        with self.lock:
            if int(note) in self.voices:
                voice = self.voices[int(note)]
                if voice["gate"]:
                    voice["release_start"] = voice["level"]
                    voice["release_time"] = 0.0
                    voice["gate"] = False

    def panic(self):
        with self.lock:
            self.voices.clear()
            self.lowpass = 0.0
            self.filter_states = [0.0, 0.0, 0.0, 0.0]
            self.delay_buffer.fill(0)
            self.peak = 0.0

    def detune(self, osc):
        """Oscillator offset in semitones: tune ±12, octave −2..+2, fine ±50 cents."""
        p = self.params
        octave = round((p[f"osc{osc}_octave"] - 0.5) * 4)
        return (p[f"osc{osc}_tune"] - 0.5) * 24 + octave * 12 + (p[f"osc{osc}_fine"] - 0.5)

    @staticmethod
    def _blep(phase, step):
        """PolyBLEP residual that rounds off each wrap of a unit-phase ramp."""
        x = phase / step
        y = (phase - 1.0) / step
        return np.where(phase < step, x + x - x*x - 1.0,
                        np.where(phase > 1.0 - step, y*y + y + y + 1.0, 0.0))

    def _wave(self, phase, which, step):
        # Saw and pulse are band-limited with PolyBLEP so high notes do not
        # alias; triangle and sine are left as is (little or no aliasing).
        idx = min(3, round(self.params[f"osc{which}_wave"] * 3))
        step = np.minimum(step, 0.5)
        if idx == 1:
            square = np.where(phase < 0.5, 1.0, -1.0)
            return square + self._blep(phase, step) - self._blep((phase + 0.5) % 1.0, step)
        if idx == 2:
            return 1.0 - 4.0 * np.abs(phase - 0.5)
        if idx == 3:
            return np.sin(phase * (2 * np.pi))
        return phase * 2.0 - 1.0 - self._blep(phase, step)

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
            # All voices are rendered together as (voice, sample) arrays; a
            # per-voice loop of small numpy calls costs more than the maths.
            playing = list(self.voices.items())
            if playing:
                voices = [voice for _, voice in playing]
                freq = 440.0 * 2 ** ((np.array([note for note, _ in playing], dtype=np.float64)
                                      - 69 + bend) / 12)
                sound = np.zeros((len(voices), frames), dtype=np.float64)
                oscillators = [(osc - 1, p[f"osc{osc}_level"],
                                freq * 2 ** (self.detune(osc) / 12), osc)
                               for osc in (1, 2, 3)]
                oscillators.append((3, p["sub_level"], freq * 0.5, None))
                for slot, level, hz, osc in oscillators:
                    if level < 0.0001:
                        continue
                    step = (hz / sr)[:, None]
                    start = np.array([voice["phases"][slot] for voice in voices])[:, None]
                    ph = (start + step * t) % 1.0
                    if osc is None:     # sub oscillator: band-limited saw an octave down
                        sound += level * (2 * ph - 1 - self._blep(ph, np.minimum(step, 0.5)))
                    else:
                        sound += level * self._wave(ph, osc, step)
                    for voice, phase in zip(voices, ((start + step * frames) % 1.0)[:, 0]):
                        voice["phases"][slot] = float(phase)
                if p["noise_level"] > 0:
                    sound += p["noise_level"] * self.rng.standard_normal(sound.shape) * 0.5
                # Sample-accurate ADSR with release from current amplitude.
                gate = np.array([voice["gate"] for voice in voices])[:, None]
                held = np.array([voice["env_time"] for voice in voices])[:, None] + t / sr
                gone = np.array([voice["release_time"] for voice in voices])[:, None] + t / sr
                start_level = np.array([voice["release_start"] for voice in voices])[:, None]
                up = np.clip(held / max(0.002, attack), 0.0, 1.0)
                down = sustain + (1.0 - sustain) * np.clip(
                    1.0 - (held - attack) / max(0.005, decay), 0.0, 1.0)
                env = np.where(gate, np.where(held < attack, up, down),
                               start_level * np.clip(1.0 - gone / max(0.005, release), 0.0, 1.0))
                velocity = np.array([voice["velocity"] for voice in voices])[:, None]
                mono += (sound * env * velocity).sum(axis=0)
                for (note, voice), level in zip(playing, env[:, -1]):
                    voice["level"] = float(level)
                    if voice["gate"]:
                        voice["env_time"] += frames / sr
                    else:
                        voice["release_time"] += frames / sr
                        if voice["release_time"] > release:
                            del self.voices[note]
            active = max(1, len(self.voices))
            mono /= max(1.5, math.sqrt(active) * 1.5)
            # Four-pole resonant subtractive filter, vintage-ladder inspired.
            # Soft nonlinear feedback is intentionally bounded to avoid runaway.
            hz = min(sr * 0.40, 55 * (2 ** (p["cutoff"] * 8.3)))
            g = min(0.94, 1.0 - math.exp(-2.0 * math.pi * hz / sr))
            feedback = p["resonance"] * 3.4
            drive = 1 + p["drive"] * 1.5
            tanh = math.tanh
            s0, s1, s2, s3 = self.filter_states
            # The ladder is recursive, so it runs per sample; plain floats and
            # a local tanh keep it about 5x faster than indexing numpy arrays.
            filtered = []
            store = filtered.append
            for sample in mono.tolist():
                x = tanh(sample * drive - feedback * s3)
                s0 += g * (x - s0)
                s1 += g * (s0 - s1)
                s2 += g * (s1 - s2)
                s3 += g * (s2 - s3)
                store(s3)
            self.filter_states = [s0, s1, s2, s3]
            mono = np.asarray(filtered) * (1.0 + p["resonance"] * 0.7)
            self.lowpass = s3
            # LFO evaluated per sample so the tremolo has no block steps.
            rate = (0.05 + 13 * p["lfo_rate"] ** 2) / sr
            lfo = np.sin((self.lfo_phase + rate * t) * 2 * math.pi)
            self.lfo_phase = (self.lfo_phase + frames * rate) % 1.0
            mono *= (1.0 - p["lfo_depth"] * 0.5) + p["lfo_depth"] * 0.5 * (1.0 + lfo)
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
            mono = np.clip(mono, -0.95, 0.95).astype(np.float32)
            self.peak = float(np.max(np.abs(mono)))
            return np.column_stack((mono, mono))
