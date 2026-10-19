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
        self.lfo_phase = 0.0
        self.lfo2_phase = 0.0
        self.sustain = False            # sustain pedal (MIDI CC64)
        self.rng = np.random.default_rng()
        self.delay_buffer = np.zeros(self.sample_rate * 2, dtype=np.float32)
        self.delay_index = 0
        self.peak = 0.0
        self._reset_organ()

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
            # Percussion is single-triggered: legato notes don't retrigger it.
            percussion = not any(v["gate"] for n, v in self.voices.items() if n != note)
            self.voices[note] = {
                "perc": percussion,
                "phases": [0.0] * (EP_SLOT + 1), "age": 0.0,
                "level": 0.0, "velocity": min(127, velocity) / 127.0,
                "gate": True, "serial": self.voice_serial,
                "env_time": 0.0, "release_time": 0.0,
                "release_start": 0.0, "mod_level": 0.0, "mod_release_start": 0.0,
            }

    def note_off(self, note):
        with self.lock:
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
            self.sustain = False
            self.lowpass = 0.0
            self.filter_states = [0.0, 0.0, 0.0, 0.0]
            self.delay_buffer.fill(0)
            self.peak = 0.0
            self._reset_organ()

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
            step = step * bend_curve[None, :]
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

    @staticmethod
    def env_times(attack, decay, release):
        """Fader positions (0..1) to seconds, shared by the AMP and MOD envelopes."""
        return 0.002 + attack ** 2 * 3.0, 0.01 + decay ** 2 * 2.0, 0.01 + release ** 2 * 4.0

    @staticmethod
    def _adsr(gate, held, gone, start_level, attack, decay, sustain, release):
        """Sample-accurate ADSR; the release starts from the current level."""
        up = np.clip(held / max(0.002, attack), 0.0, 1.0)
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
            attack, decay, release = self.env_times(p["attack"], p["decay"], p["release"])
            sustain = p["sustain"]
            bend = (p["pitch_bend"] - 0.5) * 4.0
            # All voices are rendered together as (voice, sample) arrays; a
            # per-voice loop of small numpy calls costs more than the maths.
            # LFO 2 is a vibrato, deepened by the mod wheel (up to ±0.6 semitone).
            vibrato = min(1.0, p["lfo2_depth"] + p["modwheel"]) * 0.6
            vib_rate = (0.1 + 9.9 * p["lfo2_rate"] ** 2) / sr
            bend_curve = None
            if vibrato > 1e-6:
                bend_curve = 2 ** (vibrato * np.sin((self.lfo2_phase + vib_rate * t) * 2 * math.pi) / 12)
            self.lfo2_phase = (self.lfo2_phase + frames * vib_rate) % 1.0
            # Organ and electric piano have no synth filter: they are mixed
            # after the ladder, like the real instruments.
            keys_mono = np.zeros(frames, dtype=np.float64)
            organ_mono = np.zeros(frames, dtype=np.float64)
            playing = list(self.voices.items())
            if playing:
                voices = [voice for _, voice in playing]
                freq = 440.0 * 2 ** ((np.array([note for note, _ in playing], dtype=np.float64)
                                      - 69 + bend) / 12)
                sound = np.zeros((len(voices), frames), dtype=np.float64)
                gate = np.array([voice["gate"] for voice in voices])[:, None]
                held = np.array([voice["env_time"] for voice in voices])[:, None] + t / sr
                gone = np.array([voice["release_time"] for voice in voices])[:, None] + t / sr
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
                # OSC3 first: it can modulate OSC2, which can modulate OSC1.
                oscillators = [(osc - 1, p[f"osc{osc}_level"],
                                freq * 2 ** (self.detune(osc) / 12), osc)
                               for osc in (3, 2, 1)]
                oscillators.append((3, p["sub_level"], freq * 0.5, None))
                modulator = None
                for slot, level, hz, osc in oscillators:
                    feeds = osc in (2, 3) and fm_on[osc - 2]   # next oscillator's FM is on
                    if level < 0.0001 and not feeds:
                        modulator = None
                        continue
                    step = (hz / sr)[:, None]
                    start = np.array([voice["phases"][slot] for voice in voices])[:, None]
                    if bend_curve is None:
                        ph = (start + step * t) % 1.0
                        end = start + step * frames
                    else:               # vibrato: integrate the per-sample frequency
                        step = step * bend_curve[None, :]
                        run = np.cumsum(step, axis=1)
                        ph = (start + run - step) % 1.0
                        end = start + run[:, -1:]
                    if osc is None:     # sub oscillator: band-limited saw an octave down
                        sound += level * (2 * ph - 1 - self._blep(ph, np.minimum(step, 0.5)))
                    else:
                        if fm_on[osc - 1]:
                            index = FM_MAX_INDEX * p[f"osc{osc}_fm"] ** 2 * mod_env / (2 * np.pi)
                            if osc == 3:    # self-feedback, unrolled twice
                                out = self._wave(ph, osc, step)
                                for _ in range(2):
                                    out = self._wave((ph + index * out) % 1.0, osc, step)
                            elif modulator is not None:
                                out = self._wave((ph + index * modulator) % 1.0, osc, step)
                            else:
                                out = self._wave(ph, osc, step)
                        else:
                            out = self._wave(ph, osc, step)
                        modulator = out
                        if level >= 0.0001:
                            sound += level * out
                    for voice, phase in zip(voices, (end % 1.0)[:, 0]):
                        voice["phases"][slot] = float(phase)
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
                        step = step * bend_curve[None, :]
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
                    keys += p["ep_level"] * self._electric_piano(voices, freq, t, bend_curve)
                if p["noise_level"] > 0:
                    sound += p["noise_level"] * self.rng.standard_normal(sound.shape) * 0.5
                # Sample-accurate ADSR with release from current amplitude.
                start_level = np.array([voice["release_start"] for voice in voices])[:, None]
                env = self._adsr(gate, held, gone, start_level, attack, decay, sustain, release)
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
            organ_mono, side = self._organ_effects(organ_mono, t)
            mono += keys_mono + organ_mono
            # LFO evaluated per sample so the tremolo has no block steps.
            rate = (0.05 + 13 * p["lfo_rate"] ** 2) / sr
            lfo = np.sin((self.lfo_phase + rate * t) * 2 * math.pi)
            self.lfo_phase = (self.lfo_phase + frames * rate) % 1.0
            tremolo = (1.0 - p["lfo_depth"] * 0.5) + p["lfo_depth"] * 0.5 * (1.0 + lfo)
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
            if side is None:
                mono = np.clip(mono, -0.95, 0.95).astype(np.float32)
                self.peak = float(np.max(np.abs(mono)))
                return np.column_stack((mono, mono))
            # The Leslie's stereo spread rides on top of the mono chain.
            side = side * tremolo * p["volume"] * 0.8
            stereo = np.clip(np.column_stack((mono + side, mono - side)), -0.95, 0.95)
            stereo = stereo.astype(np.float32)
            self.peak = float(np.max(np.abs(stereo)))
            return stereo

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
