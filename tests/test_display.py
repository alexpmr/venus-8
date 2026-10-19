import unittest
from unittest import mock

import numpy as np

from venus8.app import App
from venus8.display import scope_trace
from venus8.factory_presets import factory_programs
from venus8.synth import Synth


def bare_app():
    app = App.__new__(App)
    app.synth = Synth()
    app.patch_dirty = False
    app.pending = None
    app.last_param = None
    app.patch_name, app.patch_bank = "Ladder Bass", "Factory"
    app.patch_category, app.patch_description = "Bass", "x"
    app.patch_identity = ("Factory", "Ladder Bass")
    app.midi_held = set()
    app.draw = mock.Mock()
    app.root = mock.Mock()
    app.port = None
    app.stream = None
    app._save_settings = mock.Mock()
    return app


def factory_entry(index):
    program = factory_programs()[index]
    return {"name": program["name"], "bank": "Factory", "category": program["category"],
            "description": program["description"], "identity": ("Factory", program["name"]),
            "data": program}


class ScopeTests(unittest.TestCase):
    def test_trace_starts_on_a_rising_zero_crossing(self):
        t = np.arange(1024)
        for phase in (0.3, 1.7, 2.9):
            trace = scope_trace(np.sin(2 * np.pi * t / 100 + phase), points=200)
            self.assertEqual(trace.size, 200)
            self.assertLess(abs(trace[0]), 0.1)
            self.assertGreater(trace[3], trace[0])

    def test_silence_and_short_buffers(self):
        self.assertTrue(np.all(scope_trace(np.zeros(512)) == 0))
        self.assertTrue(np.all(scope_trace([]) == 0))


class UnsavedPromptTests(unittest.TestCase):
    def test_clean_patch_switches_without_asking(self):
        app = bare_app()
        self.assertTrue(app.load_catalog_entry(factory_entry(1)))
        self.assertIsNone(app.pending)
        self.assertEqual(app.patch_name, factory_entry(1)["name"])

    def test_keep_cancels_and_discard_switches(self):
        app = bare_app()
        app.change("cutoff", 0.1)
        self.assertTrue(app.patch_dirty)
        self.assertEqual(app.last_param, "cutoff")
        self.assertFalse(app.load_catalog_entry(factory_entry(1)))
        self.assertEqual(app.pending["kind"], "patch")
        app.answer_unsaved("prompt_keep")
        self.assertIsNone(app.pending)
        self.assertEqual(app.patch_name, "Ladder Bass")
        self.assertTrue(app.patch_dirty)
        app.load_catalog_entry(factory_entry(1))
        app.answer_unsaved("prompt_discard")
        self.assertEqual(app.patch_name, factory_entry(1)["name"])
        self.assertFalse(app.patch_dirty)
        self.assertIsNone(app.pending)

    def test_save_then_switch_and_cancelled_save_asks_again(self):
        app = bare_app()
        app.change("drive", 0.9)
        app.load_catalog_entry(factory_entry(2))
        app.save_patch = mock.Mock()                 # user cancels the save dialog
        app.answer_unsaved("prompt_save")
        self.assertIsNotNone(app.pending)
        self.assertEqual(app.patch_name, "Ladder Bass")
        app.save_patch = mock.Mock(side_effect=lambda: setattr(app, "patch_dirty", False))
        app.answer_unsaved("prompt_save")
        self.assertIsNone(app.pending)
        self.assertEqual(app.patch_name, factory_entry(2)["name"])

    def test_init_and_close_ask_when_modified(self):
        app = bare_app()
        app.change("volume", 0.2)
        app.init_patch()
        self.assertEqual(app.pending["kind"], "init")
        app.answer_unsaved("prompt_discard")
        self.assertEqual(app.patch_name, "Init")
        app.change("volume", 0.3)
        app.close()
        self.assertEqual(app.pending["kind"], "close")
        app.root.destroy.assert_not_called()
        app.answer_unsaved("prompt_discard")
        app.root.destroy.assert_called_once()

    def test_performance_controls_do_not_modify_the_patch(self):
        app = bare_app()
        app.change("pitch_bend", 0.8)
        app.change("modwheel", 0.5)
        self.assertFalse(app.patch_dirty)
        msg = mock.Mock(type="control_change", control=1, value=100)
        app.midi_message(msg)
        self.assertFalse(app.patch_dirty)
        msg = mock.Mock(type="control_change", control=74, value=20)
        app.midi_message(msg)
        self.assertTrue(app.patch_dirty)
        self.assertEqual(app.last_param, "cutoff")


if __name__ == "__main__":
    unittest.main()
