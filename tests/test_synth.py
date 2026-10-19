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


class TestFullOrgan(unittest.TestCase):
    def play(self, notes=(60,), seconds=1.0, block=512, **params):
        s = Synth()
        s.load_params(dict({"osc1_level": 0.0, "osc2_level": 0.0, "osc3_level": 0.0,
                            "sub_level": 0.0, "cutoff": 1.0, "drive": 0.0, "attack": 0.0,
                            "sustain": 1.0, "drawbar3": 1.0}, **params))
        for note in notes:
            s.note_on(note)
        audio = np.concatenate([s.render(block) for _ in range(int(seconds * s.sample_rate / block))])
        return audio, s

    @staticmethod
    def level_at(audio, sr, hz, start=0, size=4096):
        chunk = audio[start:start + size, 0] * np.hanning(size)
        spectrum = np.abs(np.fft.rfft(chunk))
        return spectrum[int(round(hz * size / sr))]

    def test_percussion_adds_a_decaying_harmonic(self):
        plain, s = self.play(notes=(57,))
        third, _ = self.play(notes=(57,), organ_perc=1.0, organ_perc_third=1.0, organ_perc_fast=1.0)
        second, _ = self.play(notes=(57,), organ_perc=1.0)
        sr = s.sample_rate
        self.assertGreater(self.level_at(third, sr, 660), 20 * self.level_at(plain, sr, 660) + 1)
        self.assertGreater(self.level_at(second, sr, 440), 20 * self.level_at(plain, sr, 440) + 1)
        late = sr // 2
        self.assertLess(self.level_at(third, sr, 660, start=late), self.level_at(third, sr, 660) / 20)

    def test_percussion_is_single_triggered_and_cancels_the_1_foot(self):
        s = Synth()
        s.note_on(60)
        s.note_on(64)
        self.assertTrue(s.voices[60]["perc"])
        self.assertFalse(s.voices[64]["perc"])
        audio, s = self.play(notes=(57,), drawbar9=1.0, organ_perc=1.0)
        self.assertLess(self.level_at(audio, s.sample_rate, 1760), 1.0)

    def test_key_click_only_at_the_start(self):
        clean, s = self.play(seconds=0.2)
        click, _ = self.play(seconds=0.2, organ_click=1.0)
        start = np.abs(click[:200, 0] - clean[:200, 0]).max()
        later = np.abs(click[2000:, 0] - clean[2000:, 0]).max()
        self.assertGreater(start, 0.01)
        self.assertLess(later, 1e-9)

    def test_vibrato_and_chorus_move_the_pitch(self):
        dry, s = self.play(notes=(69,))
        vib, _ = self.play(notes=(69,), organ_vibrato=1.0)
        chorus, _ = self.play(notes=(69,), organ_vibrato=1.0, organ_chorus=1.0)
        sr = s.sample_rate
        def spread(audio):     # energy away from the 440 Hz line
            spectrum = np.abs(np.fft.rfft(audio[4096:4096 + 32768, 0] * np.hanning(32768)))
            bin_ = int(440 * 32768 / sr)
            return 1 - spectrum[bin_ - 3:bin_ + 4].sum() / spectrum[bin_ - 60:bin_ + 61].sum()
        self.assertGreater(spread(vib), spread(dry) + 0.05)
        self.assertGreater(spread(chorus), spread(dry) + 0.02)

    def test_overdrive_adds_harmonics(self):
        clean, s = self.play(notes=(57,))
        driven, _ = self.play(notes=(57,), organ_drive=1.0)
        sr = s.sample_rate
        ratio = lambda a: self.level_at(a, sr, 440) / self.level_at(a, sr, 220)
        self.assertGreater(ratio(driven), 10 * ratio(clean) + 0.01)
        self.assertLess(np.sqrt((driven ** 2).mean()), 2 * np.sqrt((clean ** 2).mean()))

    def test_leslie_is_stereo_and_speeds_up_with_inertia(self):
        mono, _ = self.play()
        np.testing.assert_array_equal(mono[:, 0], mono[:, 1])
        slow, s = self.play(leslie=1.0)
        self.assertGreater(np.abs(slow[:, 0] - slow[:, 1]).max(), 0.01)
        self.assertTrue(np.isfinite(slow).all())
        s.set_param("leslie_fast", 1.0)
        s.render(s.sample_rate)
        horn, drum = s.rotor_speed
        self.assertGreater(horn, 5.0)          # the light horn is nearly at speed
        self.assertLess(drum, 3.0)             # the heavy drum still accelerating
        s.render(int(s.sample_rate * 12))
        self.assertAlmostEqual(s.rotor_speed[1], 5.7, delta=0.15)

    def test_organ_effects_do_not_depend_on_block_size(self):
        settings = dict(organ_perc=1.0, organ_vibrato=1.0, organ_chorus=1.0,
                        organ_drive=0.5, leslie=1.0, leslie_fast=1.0)
        whole, _ = self.play(notes=(48, 55, 64), seconds=0.3, block=13230, **settings)
        split, _ = self.play(notes=(48, 55, 64), seconds=0.3, block=441, **settings)
        np.testing.assert_allclose(whole, split, atol=1e-5)

    def test_switches_are_off_by_default(self):
        for name in ("organ_perc", "organ_click", "organ_vibrato", "leslie", "organ_drive"):
            self.assertEqual(DEFAULTS[name], 0.0)


class TestFM(unittest.TestCase):
    SINES = {"osc1_wave": 1.0, "osc2_wave": 1.0, "osc3_wave": 1.0, "osc1_level": 1.0,
             "osc2_level": 0.0, "osc3_level": 0.0, "sub_level": 0.0, "cutoff": 1.0,
             "resonance": 0.0, "drive": 0.0, "attack": 0.0, "sustain": 1.0}

    def play(self, note=57, velocity=100, seconds=0.5, **params):
        s = Synth()
        s.load_params(dict(self.SINES, **params))
        s.note_on(note, velocity)
        return np.concatenate([s.render(512) for _ in range(int(seconds * s.sample_rate / 512))])[:, 0], s

    @staticmethod
    def centroid(audio, sr, start=0):
        spectrum = np.abs(np.fft.rfft(audio[start:start + 8192] * np.hanning(8192)))
        return (spectrum * np.fft.rfftfreq(8192, 1 / sr)).sum() / spectrum.sum()

    def test_fm_switch_and_amount_add_sidebands(self):
        plain, s = self.play()
        sr = s.sample_rate
        off, _ = self.play(osc1_fm=1.0)                       # amount alone: no FM
        np.testing.assert_allclose(off, plain, atol=1e-6)
        soft, _ = self.play(osc1_fm_on=1.0, osc1_fm=0.4)
        hard, _ = self.play(osc1_fm_on=1.0, osc1_fm=0.9)
        self.assertLess(self.centroid(plain, sr), 260)
        self.assertGreater(self.centroid(soft, sr), self.centroid(plain, sr) + 50)
        self.assertGreater(self.centroid(hard, sr), self.centroid(soft, sr) + 200)
        self.assertAlmostEqual(pitch_of(dict(self.SINES, osc1_fm_on=1.0, osc1_fm=0.3), 57), 220.0, delta=1.5)

    def test_silent_modulator_still_modulates(self):
        # OSC2 at level 0 is a pure modulator, like a DX operator.
        bell, s = self.play(osc1_fm_on=1.0, osc1_fm=0.7, osc2_tune=0.5 + 7 / 24, osc2_octave=0.75)
        self.assertGreater(self.centroid(bell, s.sample_rate), 400)

    def test_osc3_feedback(self):
        plain, s = self.play(osc1_level=0.0, osc3_level=1.0)
        fed, _ = self.play(osc1_level=0.0, osc3_level=1.0, osc3_fm_on=1.0, osc3_fm=0.6)
        self.assertGreater(self.centroid(fed, s.sample_rate), 2 * self.centroid(plain, s.sample_rate))

    def test_mod_env_and_velocity_shape_the_brightness(self):
        params = dict(osc1_fm_on=1.0, osc1_fm=0.8, mod_decay=0.4, mod_sustain=0.0)
        audio, s = self.play(seconds=1.5, **params)
        sr = s.sample_rate
        self.assertGreater(self.centroid(audio, sr), self.centroid(audio, sr, start=sr) + 150)
        soft, _ = self.play(velocity=20, osc1_fm_on=1.0, osc1_fm=0.8)
        loud, _ = self.play(velocity=127, osc1_fm_on=1.0, osc1_fm=0.8)
        self.assertGreater(self.centroid(loud, sr), self.centroid(soft, sr))

    def test_fm_finite_with_all_operators_and_old_patches_unchanged(self):
        audio, _ = self.play(osc2_level=0.5, osc3_level=0.5, osc1_fm_on=1.0, osc2_fm_on=1.0,
                             osc3_fm_on=1.0, osc1_fm=1.0, osc2_fm=1.0, osc3_fm=1.0, osc1_wave=0.0)
        self.assertTrue(np.isfinite(audio).all())
        for i in (1, 2, 3):
            self.assertEqual(DEFAULTS[f"osc{i}_fm_on"], 0.0)


class TestElectricGrand(unittest.TestCase):
    GRAND = {"ep_level": 1.0, "ep_model": 1.0, "osc1_level": 0.0, "osc2_level": 0.0,
             "osc3_level": 0.0, "sub_level": 0.0, "cutoff": 1.0, "drive": 0.0,
             "attack": 0.0, "sustain": 1.0, "release": 0.12}

    def play(self, note=57, velocity=100, seconds=2.0, **params):
        s = Synth()
        s.load_params(dict(self.GRAND, **params))
        s.note_on(note, velocity)
        return np.concatenate([s.render(512) for _ in range(int(seconds * s.sample_rate / 512))])[:, 0], s

    def test_pitch_and_stretched_partials(self):
        audio, s = self.play(note=45, seconds=1.0)
        sr = s.sample_rate
        size = 32768
        spectrum = np.abs(np.fft.rfft(audio[:size] * np.hanning(size)))
        freqs = np.fft.rfftfreq(size, 1 / sr)
        def peak(near):
            band = (freqs > near * 0.97) & (freqs < near * 1.04)
            return freqs[band][np.argmax(spectrum[band])]
        self.assertAlmostEqual(peak(110.0), 110.0, delta=1.0)
        self.assertGreater(peak(880.0), 880.0 + 0.5)     # stiff strings: 8th partial sharp

    def test_decays_and_differs_from_the_tine(self):
        audio, s = self.play(seconds=3.0)
        sr = s.sample_rate
        rms = lambda a: float(np.sqrt((a ** 2).mean()))
        self.assertLess(rms(audio[int(2.5 * sr):]), rms(audio[:int(0.3 * sr)]) / 2.5)
        tine, _ = self.play(seconds=1.0, ep_model=0.0)
        self.assertGreater(np.abs(audio[:len(tine)] - tine).max(), 0.05)
        self.assertTrue(np.isfinite(audio).all())


class TestEffectsAndTube(unittest.TestCase):
    def play(self, seconds=0.6, block=512, notes=(48, 55, 64), **params):
        s = Synth()
        s.load_params(params)
        for note in notes:
            s.note_on(note)
        return np.concatenate([s.render(block) for _ in range(int(seconds * s.sample_rate / block))])

    def test_effects_off_by_default_and_bypass_exactly(self):
        for name in ("chorus_on", "phaser_on", "tube_drive"):
            self.assertEqual(DEFAULTS[name], 0.0)
        plain = self.play()
        np.testing.assert_array_equal(plain, self.play(chorus_depth=1.0, phaser_depth=1.0))

    def test_chorus_is_stereo_flanger_and_phaser_colour_the_sound(self):
        plain = self.play()
        chorus = self.play(chorus_on=1.0)
        self.assertGreater(np.abs(chorus[:, 0] - chorus[:, 1]).max(), 0.01)
        for params in ({"chorus_on": 1.0, "chorus_type": 1.0}, {"phaser_on": 1.0}):
            wet = self.play(**params)
            self.assertTrue(np.isfinite(wet).all())
            self.assertGreater(np.abs(wet[:, 0] - plain[:, 0]).max(), 0.02, params)
            np.testing.assert_array_equal(wet[:, 0], wet[:, 1])

    def test_effects_do_not_depend_on_block_size(self):
        settings = dict(chorus_on=1.0, phaser_on=1.0, tube_drive=0.6, chorus_rate=0.8)
        np.testing.assert_allclose(self.play(block=13230, **settings),
                                   self.play(block=441, **settings), atol=1e-5)
        settings["chorus_type"] = 1.0
        np.testing.assert_allclose(self.play(block=13230, **settings),
                                   self.play(block=441, **settings), atol=1e-5)

    def test_tube_adds_even_harmonics_on_any_engine(self):
        sine = dict(osc1_wave=1.0, osc2_level=0.0, osc3_level=0.0, sub_level=0.0, cutoff=1.0,
                    resonance=0.0, drive=0.0, attack=0.0, sustain=1.0, volume=0.3)
        def second(audio):
            spectrum = np.abs(np.fft.rfft(audio[4096:4096 + 16384, 0] * np.hanning(16384)))
            bin_ = round(220 * 16384 / 44100)
            return spectrum[2 * bin_ - 2:2 * bin_ + 3].max() / spectrum[bin_ - 2:bin_ + 3].max()
        clean = self.play(notes=(57,), **sine)
        tube = self.play(notes=(57,), tube_drive=0.8, **sine)
        self.assertGreater(second(tube), 5 * second(clean) + 0.01)
        organ = self.play(notes=(57,), tube_drive=0.8, drawbar3=1.0, osc1_level=0.0,
                          osc2_level=0.0, osc3_level=0.0, sub_level=0.0)
        self.assertTrue(np.isfinite(organ).all())


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
