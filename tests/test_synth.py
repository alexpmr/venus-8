import unittest
import numpy as np
from venus8.synth import Synth, DEFAULTS, WAVES


class TestSynth(unittest.TestCase):
    def test_shapes_and_finite_audio(self):
        s=Synth(sample_rate=44100)
        s.note_on(60,100)
        sound=s.render(512)
        self.assertEqual(sound.shape,(512,2))
        self.assertTrue(np.isfinite(sound).all())
        self.assertGreater(np.max(np.abs(sound)),0.0001)

    def test_release_tail_and_panic(self):
        s=Synth()
        s.note_on(60)
        s.render(256)
        s.note_off(60)
        self.assertIn(60,s.voices)  # release tail is intentional
        for _ in range(400):
            s.render(512)
            if 60 not in s.voices:
                break
        self.assertNotIn(60,s.voices)
        s.note_on(60)
        s.panic()
        self.assertFalse(s.voices)
        self.assertTrue(np.all(s.render(128)==0))

    def test_oscillator_waveforms(self):
        s=Synth()
        s.note_on(69)
        for wave in WAVES:
            s.waveform=wave
            self.assertEqual(s.render(100).shape,(100,2))
        self.assertEqual(s.waveform,WAVES[-1])
        with self.assertRaises(ValueError):
            s.waveform="Invalid"

    def test_polyphony_limit(self):
        s=Synth(max_voices=8)
        for note in range(48,90):
            s.note_on(note)
        self.assertLessEqual(len(s.voices),8)
        self.assertEqual(s.render(256).shape,(256,2))

    def test_new_parameters_and_patch_roundtrip(self):
        s=Synth()
        s.set_param("osc2_level",0.88)
        s.set_param("osc3_tune",0.64)
        s.set_param("delay_mix",0.35)
        s.set_param("cutoff",2.0)
        self.assertEqual(s.get_param("cutoff"),1.0)
        patch=s.snapshot()
        t=Synth()
        t.load_params(patch)
        self.assertEqual(t.get_param("osc2_level"),0.88)
        self.assertEqual(t.get_param("delay_mix"),0.35)
        with self.assertRaises(KeyError):
            t.set_param("invalid",0.2)

    def test_delay_and_noise(self):
        s=Synth()
        s.note_on(60)
        s.set_param("noise_level",0.1)
        s.set_param("delay_mix",0.3)
        s.set_param("delay_time",0.05)
        s.set_param("delay_feedback",0.5)
        for _ in range(4):
            audio=s.render(512)
            self.assertTrue(np.isfinite(audio).all())


def pitch_of(params, note=57):
    s = Synth()
    s.load_params(dict({"osc1_wave": 1.0, "osc2_level": 0.0, "osc3_level": 0.0,
                        "sub_level": 0.0, "noise_level": 0.0, "cutoff": 1.0,
                        "resonance": 0.0, "drive": 0.0, "lfo_depth": 0.0,
                        "delay_mix": 0.0, "attack": 0.0}, **params))
    s.note_on(note)
    s.render(2048)
    audio = s.render(32768)[:, 0]
    spectrum = np.abs(np.fft.rfft(audio * np.hanning(len(audio))))
    return np.argmax(spectrum) * s.sample_rate / len(audio)


class TestOscillatorTuning(unittest.TestCase):
    def test_octave_switch_and_fine_tune(self):
        base = pitch_of({})
        self.assertAlmostEqual(base, 220.0, delta=1.5)
        self.assertAlmostEqual(pitch_of({"osc1_octave": 0.75}), 440.0, delta=2)
        self.assertAlmostEqual(pitch_of({"osc1_octave": 0.0}), 55.0, delta=1.5)
        self.assertAlmostEqual(pitch_of({"osc1_fine": 1.0}), 220.0 * 2 ** (0.5 / 12), delta=1.5)
        # Between detents the octave rounds to the nearest position.
        self.assertAlmostEqual(pitch_of({"osc1_octave": 0.7}), 440.0, delta=2)

    def test_second_control_for_the_same_parameter(self):
        s = Synth()
        s.set_param("volume@header", 0.25)
        self.assertEqual(s.get_param("volume"), 0.25)
        self.assertEqual(s.get_param("volume@header"), 0.25)


class TestDrawbarOrgan(unittest.TestCase):
    def organ_pitch(self, drawbar, note=57):
        silent = {"osc1_level": 0.0, "osc2_level": 0.0, "osc3_level": 0.0}
        return pitch_of(dict(silent, **{f"drawbar{drawbar}": 1.0}), note)

    def test_footages_follow_the_tonewheel_harmonics(self):
        self.assertAlmostEqual(self.organ_pitch(3), 220.0, delta=1.5)        # 8'
        self.assertAlmostEqual(self.organ_pitch(1), 110.0, delta=1.5)        # 16'
        self.assertAlmostEqual(self.organ_pitch(2), 330.0, delta=1.5)        # 5 1/3'
        self.assertAlmostEqual(self.organ_pitch(9), 1760.0, delta=3)         # 1'

    def test_top_partials_fold_back_below_the_last_tonewheel(self):
        self.assertLess(self.organ_pitch(9, note=105), 5900)

    def test_drawbars_silent_by_default(self):
        s = Synth()
        s.load_params({"osc1_level": 0.0, "osc2_level": 0.0, "osc3_level": 0.0,
                       "sub_level": 0.0, "noise_level": 0.0})
        s.note_on(60)
        self.assertEqual(float(np.max(np.abs(s.render(2048)))), 0.0)


class TestElectricPiano(unittest.TestCase):
    def play(self, velocity=100, note=60, seconds=2.0, release_at=None, **params):
        s = Synth()
        s.load_params(dict({"ep_level": 1.0, "osc1_level": 0.0, "osc2_level": 0.0,
                            "osc3_level": 0.0, "sub_level": 0.0, "cutoff": 1.0,
                            "drive": 0.0, "attack": 0.0, "sustain": 1.0,
                            "release": 0.12}, **params))
        s.note_on(note, velocity)
        blocks = []
        for i in range(int(seconds * s.sample_rate / 512)):
            if release_at is not None and i * 512 >= release_at * s.sample_rate:
                s.note_off(note)
                release_at = None
            blocks.append(s.render(512)[:, 0])
        return np.concatenate(blocks), s.sample_rate

    @staticmethod
    def brightness(audio, sr):
        spectrum = np.abs(np.fft.rfft(audio[:8192] * np.hanning(8192)))
        freqs = np.fft.rfftfreq(8192, 1 / sr)
        return (spectrum * freqs).sum() / spectrum.sum()

    def test_pitch_and_natural_decay(self):
        audio, sr = self.play(note=57, seconds=3.0)
        spectrum = np.abs(np.fft.rfft(audio[:16384] * np.hanning(16384)))
        self.assertAlmostEqual(np.argmax(spectrum) * sr / 16384, 220.0, delta=3)
        early = np.abs(audio[2000:6000]).max()
        late = np.abs(audio[-6000:]).max()
        self.assertLess(late, early * 0.85)
        bass, _ = self.play(note=36, seconds=3.0)
        treble, _ = self.play(note=84, seconds=3.0)
        ratio = lambda a: np.abs(a[-6000:]).max() / np.abs(a[2000:6000]).max()
        self.assertGreater(ratio(bass), ratio(treble))      # bass rings longer

    def test_harder_is_brighter_and_louder(self):
        soft, sr = self.play(velocity=35)
        hard, _ = self.play(velocity=125)
        self.assertGreater(self.brightness(hard, sr), self.brightness(soft, sr) * 1.4)
        self.assertGreater(np.abs(hard).max(), np.abs(soft).max() * 1.4)

    def test_damper_stops_the_note(self):
        held, _ = self.play(seconds=1.0)
        released, _ = self.play(seconds=1.0, release_at=0.3)
        self.assertLess(np.abs(released[-4000:]).max(), np.abs(held[-4000:]).max() * 0.05)


class TestKeysBypassTheFilter(unittest.TestCase):
    def test_organ_and_piano_ignore_a_closed_filter(self):
        for params in ({"drawbar3": 1.0}, {"ep_level": 1.0}):
            levels = []
            for cutoff in (0.0, 1.0):
                s = Synth()
                s.load_params(dict({"osc1_level": 0.0, "osc2_level": 0.0, "osc3_level": 0.0,
                                    "sub_level": 0.0, "cutoff": cutoff, "drive": 0.0},
                                   **params))
                s.note_on(72)
                levels.append(np.abs(np.concatenate([s.render(512) for _ in range(8)])).max())
            self.assertAlmostEqual(levels[0], levels[1], delta=levels[1] * 0.05, msg=params)


class TestPerformanceControls(unittest.TestCase):
    def test_sustain_pedal_holds_released_notes(self):
        s = Synth()
        s.note_on(60)
        s.render(512)
        s.set_sustain(True)
        s.note_off(60)
        s.render(512)
        self.assertTrue(s.voices[60]["gate"])
        s.set_sustain(False)
        self.assertFalse(s.voices[60]["gate"])
        s.note_on(62)
        s.note_off(62)
        self.assertFalse(s.voices[62]["gate"])     # pedal up: normal release

    def test_vibrato_from_lfo2_and_mod_wheel(self):
        def spread(params):
            s = Synth()
            s.load_params(dict({"osc1_wave": 1.0, "osc2_level": 0.0, "osc3_level": 0.0,
                                "sub_level": 0.0, "cutoff": 1.0, "drive": 0.0,
                                "lfo2_rate": 0.5}, **params))
            s.note_on(69)
            audio = np.concatenate([s.render(512) for _ in range(64)])[:, 0]
            crossings = np.flatnonzero((audio[:-1] < 0) & (audio[1:] >= 0))
            periods = np.diff(crossings[5:])
            return periods.std()
        steady = spread({})
        self.assertLess(steady, 0.6)
        self.assertGreater(spread({"lfo2_depth": 1.0}), steady + 0.5)
        self.assertGreater(spread({"modwheel": 1.0}), steady + 0.5)


class TestSynthQuality(unittest.TestCase):
    def test_polyblep_reduces_aliasing(self):
        sr, f = 44100, 3001.0
        phase = ((f / sr) * np.arange(sr)) % 1.0

        def alias_energy(signal):
            spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal)))) ** 2
            harmonic = np.zeros_like(spectrum, bool)
            for k in range(1, int(sr / 2 / f) + 1):
                centre = int(round(k * f))
                harmonic[centre - 3:centre + 4] = True
            return spectrum[~harmonic].sum() / spectrum.sum()

        s = Synth()
        for value, naive in ((0.0, 2 * phase - 1), (1 / 3, np.where(phase < 0.5, 1.0, -1.0))):
            s.set_param("osc1_wave", value)
            band_limited = s._wave(phase, 1, f / sr)
            self.assertGreater(alias_energy(naive) / alias_energy(band_limited), 10.0)

    def test_output_does_not_depend_on_block_size(self):
        def play(blocks):
            s = Synth()
            s.load_params({"lfo_depth": 0.8, "lfo_rate": 0.6, "delay_mix": 0.4,
                           "delay_time": 0.0, "delay_feedback": 0.7, "resonance": 0.6})
            s.note_on(48)
            s.note_on(55)
            return np.concatenate([s.render(n) for n in blocks])
        whole = play([6000])
        split = play([512] * 11 + [368])
        np.testing.assert_allclose(whole, split, atol=1e-6)

    def test_delay_matches_per_sample_reference(self):
        def play(mix):
            s = Synth()
            s.load_params({"volume": 0.2, "delay_mix": mix, "delay_time": 0.05,
                           "delay_feedback": 0.8})
            s.note_on(60)
            sound = np.concatenate([s.render(700) for _ in range(12)])[:, 0]
            return sound, s.sample_rate
        dry, sr = play(0.0)
        wet, _ = play(0.5)
        period = int(sr * (0.06 + 0.05 * 0.65))
        buffer = np.zeros(sr * 2, dtype=np.float32)
        expected = np.empty_like(dry, dtype=np.float64)
        for i, sample in enumerate(dry.astype(np.float64)):
            delayed = float(buffer[(i - period) % len(buffer)])
            buffer[i % len(buffer)] = sample + delayed * 0.8 * 0.75
            expected[i] = sample * 0.5 + delayed * 0.5
        np.testing.assert_allclose(wet, expected, atol=1e-5)

    def test_sixteen_voices_render_together(self):
        s = Synth()
        for note in range(48, 64):
            s.note_on(note, 64 + note)
        audio = s.render(512)
        self.assertEqual(len(s.voices), 16)
        self.assertTrue(np.isfinite(audio).all())
        levels = {s.voices[n]["level"] for n in s.voices}
        self.assertEqual(len(levels), 1)


if __name__=="__main__":
    unittest.main()
