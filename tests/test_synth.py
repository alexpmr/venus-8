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
