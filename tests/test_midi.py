import unittest
from unittest import mock

from venus8 import app as app_module
from venus8.app import App, match_midi_name
from venus8.synth import DEFAULTS, Synth


class FakePort:
    def __init__(self, name):
        self.name = name
        self.closed = False

    def close(self):
        self.closed = True


class FakeMido:
    def __init__(self):
        self.names = []
        self.opened = []

    def get_input_names(self):
        return list(self.names)

    def open_input(self, name, callback=None):
        if name not in self.names:
            raise OSError("no such port")
        port = FakePort(name)
        self.opened.append(port)
        return port


def bare_app(saved=None):
    app = App.__new__(App)
    app.settings = {"midi": saved} if saved else {}
    app.port = None
    app.stream = None
    app.midi_devices = []
    app.midi_held = set()
    app.last_midi = ""
    app.synth = Synth()
    app.root = mock.Mock()
    app.draw = mock.Mock()
    app._save_settings = mock.Mock()
    return app


class MidiNameTests(unittest.TestCase):
    def test_saved_controller_survives_windows_renumbering(self):
        names = ["loopMIDI Port 0", "Arturia KeyLab mkII 88 2"]
        self.assertEqual(match_midi_name("Arturia KeyLab mkII 88 1", names), names[1])
        self.assertEqual(match_midi_name("loopMIDI Port 0", names), names[0])
        self.assertIsNone(match_midi_name("Arturia MiniLab 0", names))
        self.assertIsNone(match_midi_name(None, names))


class StartupPortTests(unittest.TestCase):
    NAMES = ["MIDIIN2 (KeyLab mkII 88) 0", "loopMIDI Port 1", "KeyLab mkII 88 2"]

    def test_pick_saved_renumbered_or_a_keyboard_never_a_stand_in(self):
        from venus8.app import pick_midi_port
        self.assertEqual(pick_midi_port("KeyLab mkII 88 0", self.NAMES), "KeyLab mkII 88 2")
        self.assertEqual(pick_midi_port(None, self.NAMES), "KeyLab mkII 88 2")
        self.assertIsNone(pick_midi_port("Arturia MiniLab 0", self.NAMES))
        self.assertEqual(pick_midi_port("loopMIDI Port 0", self.NAMES), "loopMIDI Port 1")
        # A DAW port saved by an older version moves to the controller's keys.
        self.assertEqual(pick_midi_port("MIDIIN2 (KeyLab mkII 88) 3", self.NAMES), "KeyLab mkII 88 2")

    def test_startup_with_renumbered_ports_keeps_the_saved_controller(self):
        fake = FakeMido()
        fake.names = list(self.NAMES)
        app = bare_app(saved="KeyLab mkII 88 0")
        app.midi_devices = list(self.NAMES)
        with mock.patch.object(app_module, "mido", fake):
            app.open_midi(app.settings["midi"])
        self.assertEqual(app.port.name, "KeyLab mkII 88 2")
        busy = bare_app(saved="Arturia MiniLab 0")
        busy.midi_devices = list(self.NAMES)
        with mock.patch.object(app_module, "mido", fake):
            busy.open_midi(busy.settings["midi"])
        self.assertIsNone(busy.port)                          # nothing else grabbed
        self.assertEqual(busy.settings["midi"], "Arturia MiniLab 0")
        self.assertEqual(busy.midi_error, "não encontrado")

    def test_busy_port_is_reported_and_retried(self):
        fake = FakeMido()
        fake.names = ["KeyLab mkII 88 0"]
        fake.open_input = mock.Mock(side_effect=OSError("MMSYSERR_ALLOCATED"))
        app = bare_app(saved="KeyLab mkII 88 0")
        with mock.patch.object(app_module, "mido", fake):
            app.watch_midi()
        self.assertIsNone(app.port)
        self.assertEqual(app.midi_error, "ocupado")
        self.assertEqual(app.root.after.call_args[0][0], 1000)   # quick retry


class MidiWatchdogTests(unittest.TestCase):
    def test_reconnects_after_unplug_and_busy_start(self):
        fake = FakeMido()
        app = bare_app(saved="Arturia KeyLab 0")
        with mock.patch.object(app_module, "mido", fake):
            app.watch_midi()                      # controller not present yet
            self.assertIsNone(app.port)
            fake.names = ["Arturia KeyLab 1"]     # plugged in, renumbered
            app.watch_midi()
            self.assertEqual(app.port.name, "Arturia KeyLab 1")
            app.midi_held.add(60)
            app.synth.note_on(60)
            port = app.port
            fake.names = []                       # cable pulled
            app.watch_midi()
            self.assertIsNone(app.port)
            self.assertTrue(port.closed)
            self.assertFalse(app.midi_held)
            self.assertFalse(app.synth.voices[60]["gate"])
            fake.names = ["Arturia KeyLab 0"]     # plugged back
            app.watch_midi()
            self.assertEqual(app.port.name, "Arturia KeyLab 0")
        self.assertTrue(app.root.after.called)

    def test_other_controllers_are_not_grabbed_when_one_is_saved(self):
        fake = FakeMido()
        fake.names = ["loopMIDI Port 0"]
        app = bare_app(saved="Arturia KeyLab 0")
        with mock.patch.object(app_module, "mido", fake):
            app.watch_midi()
        self.assertIsNone(app.port)

    def test_release_devices_frees_midi_and_audio(self):
        app = bare_app()
        port, stream = FakePort("Arturia KeyLab 0"), mock.Mock()
        app.port, app.stream = port, stream
        app.release_devices()
        self.assertTrue(port.closed)
        stream.stop.assert_called_once()
        stream.close.assert_called_once()
        self.assertIsNone(app.port)
        self.assertIsNone(app.stream)


class OrganSwitchTests(unittest.TestCase):
    def test_switch_click_toggles_and_marks_patch_modified(self):
        app = bare_app()
        app.patch_dirty = False
        app.action("switch:leslie")
        self.assertEqual(app.synth.get_param("leslie"), 1.0)
        self.assertTrue(app.patch_dirty)
        app.action("switch:leslie")
        self.assertEqual(app.synth.get_param("leslie"), 0.0)


class LowLatencyTests(unittest.TestCase):
    def test_notes_sound_on_the_midi_thread_and_the_ui_catches_up(self):
        import queue
        app = bare_app()
        app.events = queue.Queue()
        note = mock.Mock(type="note_on", note=60, velocity=100)
        app.midi_callback(note)
        self.assertIn(60, app.synth.voices)             # sounding before any UI poll
        self.assertFalse(app.midi_held)
        kind, msg, played = app.events.get_nowait()
        self.assertTrue(played)
        serial = app.synth.voices[60]["serial"]
        app.midi_message(msg, played=played)
        self.assertEqual(app.midi_held, {60})
        self.assertEqual(app.synth.voices[60]["serial"], serial)   # not retriggered
        app.midi_callback(mock.Mock(type="control_change", control=64, value=127))
        self.assertTrue(app.synth.sustain)
        app.midi_callback(mock.Mock(type="pitchwheel", pitch=8191))
        self.assertGreater(app.synth.pitch_bend, 1.9)

    def test_fast_drivers_come_first_and_old_settings_still_match(self):
        from venus8.app import audio_outputs, pick_output
        hostapis = [{"name": "MME"}, {"name": "Windows DirectSound"}, {"name": "Windows WASAPI"}]
        devices = [{"name": "Speakers", "hostapi": 0, "max_output_channels": 2},
                   {"name": "Mic", "hostapi": 0, "max_output_channels": 0},
                   {"name": "Speakers", "hostapi": 1, "max_output_channels": 2},
                   {"name": "Speakers", "hostapi": 2, "max_output_channels": 2}]
        outputs = audio_outputs(devices, hostapis)
        self.assertEqual(outputs[0], (3, "Speakers [Windows WASAPI]"))
        self.assertEqual([label for _, label in outputs][-1], "Speakers [MME]")
        self.assertEqual(pick_output(outputs, "Speakers"), outputs[0])         # pre-0.2.24 setting
        self.assertEqual(pick_output(outputs, "Speakers [MME]"), (0, "Speakers [MME]"))
        self.assertEqual(pick_output(outputs, None), outputs[0])


class PanelControlTests(unittest.TestCase):
    def test_spinners_step_and_clamp(self):
        app = bare_app()
        app.action("spin:transpose:1")
        self.assertAlmostEqual(app.synth.get_param("transpose"), 0.5 + 1 / 24)
        for _ in range(30):
            app.action("spin:polyphony:-1")
        self.assertEqual(app.synth.voice_limit, 1)
        app.action("spin:bend_range:1")
        self.assertEqual(app.synth.bend_semitones(), 3)

    def test_velocity_curves(self):
        from venus8.app import velocity_curve
        self.assertEqual(velocity_curve(64, "normal"), 64)
        self.assertGreater(velocity_curve(64, "soft"), 64)
        self.assertLess(velocity_curve(64, "hard"), 64)
        self.assertEqual(velocity_curve(10, "fixed"), 100)
        app = bare_app()
        app.settings["velocity_curve"] = "fixed"
        app.play_midi(mock.Mock(type="note_on", note=60, velocity=20))
        self.assertAlmostEqual(app.synth.voices[60]["velocity"], 100 / 127)


class LayerSplitTests(unittest.TestCase):
    def app_with_lower(self, split=None):
        from venus8.factory_presets import factory_programs
        app = bare_app()
        program = factory_programs()[3]
        app.set_lower({"name": program["name"], "bank": "Factory", "data": program})
        app.split_note = split
        return app

    def test_split_routes_keys_by_the_split_point(self):
        app = self.app_with_lower(split=60)
        app.key_on(48)
        app.key_on(72)
        self.assertEqual(list(app.lower.voices), [48])
        self.assertEqual(list(app.synth.voices), [72])
        app.key_off(48)
        self.assertFalse(app.lower.voices[48]["gate"])

    def test_layer_plays_both_and_parts_can_be_switched_off(self):
        app = self.app_with_lower(split=None)
        app.key_on(60)
        self.assertIn(60, app.lower.voices)
        self.assertIn(60, app.synth.voices)
        app.toggle_part("lower")
        self.assertFalse(app.lower_on)
        app.key_on(64)
        self.assertNotIn(64, app.lower.voices)
        app.toggle_part("lower")
        app.toggle_part("upper")
        app.key_on(67)
        self.assertIn(67, app.lower.voices)
        self.assertNotIn(67, app.synth.voices)

    def test_split_point_steps_from_layer(self):
        app = self.app_with_lower()
        app.step_split(1)
        self.assertEqual(app.split_note, 24)
        app.step_split(-5)
        self.assertIsNone(app.split_note)
        self.assertIsNone(app.settings["split_note"])

    def test_audio_mixes_both_parts_and_shares_the_wheels(self):
        import numpy as np
        app = self.app_with_lower(split=None)
        app.dsp_load = 0.0
        app.synth.set_param("modwheel", 0.7)
        app.key_on(60)
        out = np.zeros((256, 2), dtype=np.float32)
        app.audio_callback(out, 256, None, None)
        self.assertEqual(app.lower.params["modwheel"], 0.7)
        self.assertGreater(np.abs(out).max(), 0.0)


class ClockAndSaveTests(unittest.TestCase):
    def test_clock_messages_reach_the_synth_without_ui_traffic(self):
        import queue
        app = bare_app()
        app.events = queue.Queue()
        app.midi_callback(mock.Mock(type="clock"))
        app.midi_callback(mock.Mock(type="clock"))
        self.assertTrue(app.events.empty())
        self.assertGreater(app.synth.clock_seen, 0)
        app.midi_callback(mock.Mock(type="start"))
        self.assertEqual(app.synth.arp_index, 0)

    def test_write_patch_saves_name_category_and_description(self):
        import json, tempfile
        from pathlib import Path
        app = bare_app()
        app.patch_name, app.patch_category, app.patch_description = "X", "Bass", "x"
        app.patch_dirty = True
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Meu Baixo.json"
            app.write_patch(path, "Meu Baixo", "Bass", "Gordo")
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual((data["name"], data["category"], data["description"]), ("Meu Baixo", "Bass", "Gordo"))
        self.assertEqual(app.patch_name, "Meu Baixo")
        self.assertFalse(app.patch_dirty)


class VoiceModeButtonTests(unittest.TestCase):
    def test_mode_buttons_switch_and_silence_hanging_notes(self):
        app = bare_app()
        app.synth.note_on(60)
        app.action("voicemode3")
        self.assertEqual(round(app.synth.get_param("voice_mode") * 3), 3)
        self.assertFalse(app.synth.voices)
        app.action("lfowave2_3")
        self.assertEqual(app.synth.get_param("lfo2_wave"), 1.0)


class Msg:
    def __init__(self, control, value):
        self.type, self.control, self.value = "control_change", control, value


class MidiLearnTests(unittest.TestCase):
    def test_default_map_still_works(self):
        app = bare_app()
        app.midi_message(Msg(74, 0))
        self.assertEqual(app.synth.get_param("cutoff"), 0.0)

    def test_learn_assigns_the_next_cc_and_is_saved(self):
        app = bare_app()
        app.start_learn("resonance")
        app.midi_message(Msg(21, 90))
        self.assertIsNone(app.learning)
        self.assertEqual(app.settings["midi_map"]["21"], "resonance")
        app._save_settings.assert_called()
        app.midi_message(Msg(21, 127))
        self.assertEqual(app.synth.get_param("resonance"), 1.0)
        # Learning again moves the control to the new CC (one CC per control).
        app.start_learn("resonance")
        app.midi_message(Msg(22, 0))
        self.assertNotIn("21", app.settings["midi_map"])
        self.assertEqual(app.midi_cc_for("resonance"), 22)
        app.forget_midi("resonance")
        self.assertIsNone(app.midi_cc_for("resonance"))

    def test_learned_cc_can_take_over_a_default(self):
        app = bare_app()
        app.start_learn("drawbar3")
        app.midi_message(Msg(74, 64))
        # Drawbars are inverted by default: fader up pushes the drawbar in.
        app.midi_message(Msg(74, 127))
        self.assertEqual(app.synth.get_param("drawbar3"), 0.0)
        self.assertEqual(app.synth.get_param("cutoff"), DEFAULTS["cutoff"])
        app.midi_message(Msg(74, 0))
        self.assertEqual(app.synth.get_param("drawbar3"), 1.0)
        app.midi_message(Msg(74, 60))
        self.assertEqual(app.synth.get_param("drawbar3") * 8, round(67 / 127 * 8))
        app.settings["invert_drawbars"] = False
        app.midi_message(Msg(74, 127))
        self.assertEqual(app.synth.get_param("drawbar3"), 1.0)

    def test_buttons_toggle_switches_on_press(self):
        app = bare_app()
        app.start_learn("leslie_fast")
        app.midi_message(Msg(30, 127))
        for value, expected in ((127, 1.0), (0, 1.0), (127, 0.0), (127, 0.0), (0, 0.0), (127, 1.0)):
            app.midi_message(Msg(30, value))
            self.assertEqual(app.synth.get_param("leslie_fast"), expected)


if __name__ == "__main__":
    unittest.main()
