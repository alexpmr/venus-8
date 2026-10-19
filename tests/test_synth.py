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


class TestFilterAndLfos(unittest.TestCase):
    SAW = {"osc2_level": 0.0, "osc3_level": 0.0, "sub_level": 0.0, "resonance": 0.0,
           "drive": 0.0, "attack": 0.0, "sustain": 1.0}

    def play(self, notes=(48,), seconds=1.0, block=512, **params):
        s = Synth()
        s.load_params(dict(self.SAW, **params))
        for note in notes:
            s.note_on(note)
        return np.concatenate([s.render(block) for _ in range(int(seconds * s.sample_rate / block))]), s

    @staticmethod
    def centroid(audio, start=0, size=8192):
        spectrum = np.abs(np.fft.rfft(audio[start:start + size, 0] * np.hanning(size)))
        return (spectrum * np.fft.rfftfreq(size, 1 / 44100)).sum() / spectrum.sum()

    def test_filter_types(self):
        cut = {"cutoff": 0.5}
        lp24, _ = self.play(**cut)
        lp12, _ = self.play(filter_type=1 / 3, **cut)
        bp, _ = self.play(filter_type=2 / 3, **cut)
        hp, _ = self.play(filter_type=1.0, **cut)
        self.assertLess(self.centroid(lp24), self.centroid(lp12))
        self.assertLess(self.centroid(lp12), self.centroid(bp))
        self.assertLess(self.centroid(bp), self.centroid(hp))
        for audio in (lp12, bp, hp):
            self.assertTrue(np.isfinite(audio).all())

    def test_filter_envelope_opens_then_closes(self):
        audio, s = self.play(seconds=1.5, cutoff=0.3, filter_env_on=1.0, fenv_attack=0.0,
                             fenv_decay=0.35, fenv_sustain=0.0)
        early, late = self.centroid(audio, 0, 4096), self.centroid(audio, 44100, 4096)
        self.assertGreater(early, 2 * late)
        off, _ = self.play(seconds=1.5, cutoff=0.3, fenv_decay=0.35, fenv_sustain=0.0)
        self.assertLess(abs(self.centroid(off, 0, 4096) - self.centroid(off, 44100, 4096)), 150)

    def test_filter_envelope_retriggers_and_releases_with_the_keys(self):
        s = Synth()
        s.load_params(dict(self.SAW, filter_env_on=1.0, fenv_attack=0.0, fenv_decay=0.2,
                           fenv_sustain=0.2, fenv_release=0.2))
        s.note_on(60)
        s.render(22050)
        self.assertAlmostEqual(s.fenv["level"], 0.2, delta=0.02)
        s.note_on(64)                          # a new key retriggers the envelope
        s.render(256)
        self.assertGreater(s.fenv["level"], 0.9)
        s.note_off(60)
        s.note_off(64)
        s.render(22050)
        self.assertLess(s.fenv["level"], 0.01)

    def test_key_track_follows_the_note(self):
        low, _ = self.play(notes=(36,), cutoff=0.4, key_track=1.0)
        high, _ = self.play(notes=(84,), cutoff=0.4, key_track=1.0)
        fixed, _ = self.play(notes=(84,), cutoff=0.4)
        rms = lambda a: float(np.sqrt((a ** 2).mean()))
        self.assertGreater(rms(high), 2 * rms(fixed))     # the filter opens for high notes
        self.assertLess(self.centroid(low), self.centroid(high))

    def test_lfo_waves_fade_and_sync(self):
        def tremolo(**params):
            audio, s = self.play(seconds=2.0, cutoff=1.0, lfo_depth=1.0, lfo_rate=0.3, **params)
            usable = len(audio) // 441 * 441
            envelope = np.abs(audio[:usable, 0]).reshape(-1, 441).max(axis=1)
            return envelope, s
        shapes = [tremolo(lfo_wave=w / 3)[0] for w in range(4)]
        for a in range(4):
            for b in range(a + 1, 4):
                self.assertGreater(np.abs(shapes[a] - shapes[b]).max(), 0.02, (a, b))
        faded, _ = tremolo(lfo_fade=0.6)
        sway = lambda e, a, b: e[a:b].max() - e[a:b].min()
        self.assertLess(sway(faded, 2, 30), sway(faded, 150, 199) / 2)
        s = Synth()
        s.set_param("lfo_sync", 1.0)
        s.render(3000)
        self.assertGreater(s.lfo_phase, 0.0)
        s.note_on(60)
        self.assertEqual(s.lfo_phase, 0.0)

    def test_new_controls_do_not_depend_on_block_size(self):
        settings = dict(filter_env_on=1.0, filter_type=1 / 3, key_track=0.5, lfo_depth=0.5,
                        lfo_wave=2 / 3, lfo2_depth=0.3, lfo2_wave=1 / 3, lfo_fade=0.3,
                        reverb_on=1.0, width=0.8, cutoff=0.4)
        whole, _ = self.play(notes=(48, 55), seconds=0.6, block=13230, **settings)
        split, _ = self.play(notes=(48, 55), seconds=0.6, block=441, **settings)
        np.testing.assert_allclose(whole, split, atol=1e-5)


class TestReverbAndWidth(unittest.TestCase):
    def test_reverb_tail_stereo_and_bypass(self):
        def run(**params):
            s = Synth()
            s.load_params(params)
            s.note_on(60)
            sound = [s.render(512) for _ in range(20)]
            s.note_off(60)
            sound += [s.render(512) for _ in range(120)]
            return np.concatenate(sound)
        dry, wet = run(), run(reverb_on=1.0, reverb_size=0.8, reverb_mix=0.5)
        tail = slice(30000, 60000)
        self.assertLess(np.abs(dry[tail]).max(), 1e-4)
        self.assertGreater(np.abs(wet[tail]).max(), 0.002)
        self.assertGreater(np.abs(wet[:, 0] - wet[:, 1]).max(), 0.001)
        np.testing.assert_array_equal(dry, run(reverb_size=1.0, reverb_mix=1.0))
        self.assertTrue(np.isfinite(wet).all())

    def test_width_narrows_and_widens(self):
        def side(width):
            s = Synth()
            s.load_params({"chorus_on": 1.0, "width": width})
            s.note_on(60)
            audio = np.concatenate([s.render(512) for _ in range(20)])
            return np.abs(audio[:, 0] - audio[:, 1]).max()
        self.assertLess(side(0.0), 1e-6)
        self.assertGreater(side(1.0), 1.5 * side(0.5))


class TestPerformanceModes(unittest.TestCase):
    SINE = {"osc1_wave": 1.0, "osc2_level": 0.0, "osc3_level": 0.0, "sub_level": 0.0,
            "cutoff": 1.0, "resonance": 0.0, "attack": 0.0, "sustain": 1.0}

    @staticmethod
    def pitch(audio, sr=44100):
        spectrum = np.abs(np.fft.rfft(audio * np.hanning(len(audio))))
        return np.argmax(spectrum) * sr / len(audio)

    def synth(self, **params):
        s = Synth()
        s.load_params(dict(self.SINE, **params))
        return s

    def test_mono_plays_one_voice_with_last_note_priority(self):
        s = self.synth(voice_mode=1 / 3)
        s.note_on(57)
        s.render(2048)
        s.note_on(69)
        self.assertEqual(list(s.voices), [69])
        self.assertAlmostEqual(self.pitch(s.render(16384)[:, 0]), 440, delta=3)
        s.note_off(69)                          # back to the key still held
        self.assertEqual(list(s.voices), [57])
        self.assertTrue(s.voices[57]["gate"])
        self.assertAlmostEqual(self.pitch(s.render(16384)[:, 0]), 220, delta=3)
        s.note_off(57)
        self.assertFalse(s.voices[57]["gate"])

    def test_legato_slides_without_retriggering(self):
        s = self.synth(voice_mode=2 / 3, attack=0.5)
        s.note_on(57)
        s.render(22050)
        level = s.voices[57]["level"]
        s.note_on(60)
        s.render(64)
        self.assertEqual(list(s.voices), [60])
        self.assertGreaterEqual(s.voices[60]["level"], level)    # no restart from zero
        mono = self.synth(voice_mode=1 / 3, attack=0.5)
        mono.note_on(57)
        mono.render(22050)
        mono.note_on(60)
        self.assertEqual(mono.voices[60]["env_time"], 0.0)       # mono retriggers

    def test_glide_moves_the_pitch_gradually(self):
        s = self.synth(glide_time=0.4)
        s.note_on(57)
        s.render(4096)
        s.note_off(57)
        s.note_on(69)
        self.assertAlmostEqual(s.voices[69]["glide"], -12.0)
        s.render(4410)
        self.assertTrue(-12.0 < s.voices[69]["glide"] < -1.0)
        s.render(44100 * 2)
        self.assertEqual(s.voices[69]["glide"], 0.0)
        plain = self.synth()
        plain.note_on(57)
        plain.note_on(69)
        self.assertEqual(plain.voices[69]["glide"], 0.0)

    def test_unison_stacks_detuned_copies(self):
        s = self.synth(voice_mode=1.0, unison_detune=0.8, osc1_wave=0.0)
        s.note_on(57)
        s.note_on(60)
        self.assertEqual(len(s.voices), 1)
        wide = np.concatenate([s.render(512) for _ in range(40)])[:, 0]
        narrow_synth = self.synth(voice_mode=1.0, unison_detune=0.0, osc1_wave=0.0)
        narrow_synth.note_on(60)
        narrow = np.concatenate([narrow_synth.render(512) for _ in range(40)])[:, 0]
        self.assertTrue(np.isfinite(wide).all())
        self.assertGreater(np.abs(wide - narrow).max(), 0.05)

    def test_pulse_width_and_pwm(self):
        def tone(**params):
            s = self.synth(osc1_wave=1 / 3, **params)
            s.note_on(57)
            return np.concatenate([s.render(512) for _ in range(60)])[:, 0]
        square, narrow = tone(), tone(osc1_pw=0.9)
        spectrum = lambda a: np.abs(np.fft.rfft(a[:16384] * np.hanning(16384)))
        bin_ = round(220 * 16384 / 44100)
        second = lambda a: spectrum(a)[2 * bin_ - 2:2 * bin_ + 3].max() / spectrum(a)[bin_ - 2:bin_ + 3].max()
        self.assertLess(second(square), 0.05)            # square: no even harmonics
        self.assertGreater(second(narrow), 0.3)
        self.assertLess(abs(float(narrow.mean())), 0.02)  # DC removed
        moving = tone(osc1_pwm=0.8, lfo_rate=0.4)
        self.assertGreater(np.abs(moving - square).max(), 0.05)
        self.assertTrue(np.isfinite(moving).all())


class TestSampleRate(unittest.TestCase):
    def test_48k_device_renders_every_effect(self):
        s = Synth()
        s.set_sample_rate(48000)
        s.load_params({"chorus_on": 1.0, "phaser_on": 1.0, "reverb_on": 1.0, "delay_mix": 0.3,
                       "leslie": 1.0, "drawbar3": 1.0, "organ_vibrato": 1.0})
        s.note_on(60)
        audio = np.concatenate([s.render(480) for _ in range(50)])
        self.assertEqual(len(s.delay_buffer), 96000)
        self.assertTrue(np.isfinite(audio).all())
        self.assertGreater(np.abs(audio).max(), 0.01)


class TestArpeggiator(unittest.TestCase):
    def run_arp(self, keys=(60, 64, 67), steps=8, block=64, **params):
        s = Synth()
        s.load_params(dict({"arp_on": 1.0, "arp_rate": 1.0, "attack": 0.0, "sustain": 1.0,
                            "release": 0.01}, **params))
        for key in keys:
            s.note_on(key)
        played = []
        for _ in range(4000):
            s.render(block)
            if s.arp_note is not None and (not played or played[-1][1] != s.arp_index):
                played.append((s.arp_note, s.arp_index))
            if len(played) >= steps:
                break
        return [note for note, _ in played], s

    def test_modes_and_octaves(self):
        self.assertEqual(self.run_arp()[0], [60, 64, 67] * 2 + [60, 64])
        self.assertEqual(self.run_arp(arp_mode=0.25)[0][:3], [67, 64, 60])
        self.assertEqual(self.run_arp(arp_mode=0.5)[0][:6], [60, 64, 67, 64, 60, 64])
        self.assertEqual(self.run_arp(keys=(64, 60, 67), arp_mode=1.0)[0][:3], [64, 60, 67])
        self.assertEqual(self.run_arp(arp_oct=1 / 3)[0][:6], [60, 64, 67, 72, 76, 79])
        randoms = self.run_arp(arp_mode=0.75, steps=20)[0]
        self.assertTrue(set(randoms) <= {60, 64, 67})

    def test_timing_is_sample_exact_and_block_independent(self):
        def onsets(block):
            s = Synth()
            s.load_params({"arp_on": 1.0, "arp_rate": 0.5, "arp_gate": 0.5})
            s.note_on(60)
            s.note_on(67)
            audio = np.concatenate([s.render(block) for _ in range(44100 // block)])
            return audio
        np.testing.assert_allclose(onsets(441), onsets(4410), atol=1e-6)
        s = Synth()
        s.load_params({"arp_on": 1.0, "arp_rate": 0.5})           # 140 BPM, 1/16 notes
        self.assertAlmostEqual(s.arp_bpm(), 140.0)

    def test_gate_releases_before_the_next_step(self):
        _, s = self.run_arp(steps=1, arp_gate=0.2, arp_rate=0.0)
        step = round(44100 * 60 / (40 * 4))
        s.render(int(step * 0.5))
        self.assertIsNone(s.arp_note)

    def test_release_stops_and_hold_latches(self):
        _, s = self.run_arp(steps=2)
        for key in (60, 64, 67):
            s.note_off(key)
        self.assertIsNone(s.arp_note)
        self.assertFalse(s.arp_keys)
        _, s = self.run_arp(steps=2, arp_hold=1.0)
        for key in (60, 64, 67):
            s.note_off(key)
        s.render(20000)
        self.assertIsNotNone(s.arp_note)               # still playing, latched
        s.note_on(72)                                  # a new chord replaces it
        self.assertEqual(s.arp_keys, [72])
        s.set_param("arp_on", 0.0)
        self.assertIsNone(s.arp_note)
        s.render(4096)
        self.assertTrue(all(not v["gate"] for v in s.voices.values()))


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
