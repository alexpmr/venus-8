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


if __name__=="__main__":
    unittest.main()
