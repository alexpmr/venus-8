import unittest
from unittest import mock

from venus8 import app as app_module
from venus8.app import App, match_midi_name
from venus8.synth import Synth


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


if __name__ == "__main__":
    unittest.main()
