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
