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


class LcdTests(unittest.TestCase):
    def test_modes_tint_the_display_and_keep_its_size(self):
        from PIL import Image
        from venus8.display import PALETTES, lcd_screen
        source = Image.new("RGB", (90, 60), (200, 120, 60))
        for mode, palette in PALETTES.items():
            out = lcd_screen(source, mode)
            self.assertEqual(out.size, source.size)
            r, g, b = out.getpixel((0, 0))
            if palette["tint"]:
                tint = palette["tint"]
                self.assertEqual(max(range(3), key=lambda i: (r, g, b)[i]),
                                 max(range(3), key=lambda i: tint[i]), mode)
        self.assertNotEqual(lcd_screen(source, "color").getpixel((2, 0)),
                            lcd_screen(source, "color").getpixel((0, 0)))   # pixel grid


class MidiPerformanceTests(unittest.TestCase):
    def test_sustain_pedal_and_program_change(self):
        app = bare_app()
        app.patch_dir = mock.Mock()
        app.patch_dir.glob.return_value = []
        app.midi_message(mock.Mock(type="control_change", control=64, value=127))
        self.assertTrue(app.synth.sustain)
        self.assertFalse(app.patch_dirty)
        app.midi_message(mock.Mock(type="control_change", control=64, value=0))
        self.assertFalse(app.synth.sustain)
        app.midi_message(mock.Mock(type="program_change", program=3))
        self.assertEqual(app.patch_name, factory_entry(3)["name"])
        app.change("cutoff", 0.2)
        app.midi_message(mock.Mock(type="program_change", program=5))
        self.assertEqual(app.pending["kind"], "patch")
        self.assertEqual(app.patch_name, factory_entry(3)["name"])


class UpdateButtonTests(unittest.TestCase):
    def setUp(self):
        self.app = bare_app()
        self.app.updating = False
        self.app.release = None
        self.app.update_state = "idle"
        self.app.update_label = ""
        self.app.check_update = mock.Mock()
        self.app.install_update = mock.Mock()

    def test_click_checks_when_nothing_is_pending(self):
        for state in ("idle", "current", "error"):
            self.app.update_state = state
            self.app.action("check_update")
        self.assertEqual(self.app.check_update.call_count, 3)
        self.app.install_update.assert_not_called()

    def test_click_installs_when_a_new_version_is_available(self):
        self.app.release = {"tag_name": "v9.9.9"}
        self.app.update_state = "available"
        self.app.action("check_update")
        self.app.install_update.assert_called_once()
        self.app.update_state = "downloading"
        self.app.action("check_update")
        self.app.install_update.assert_called_once()
        self.app.check_update.assert_not_called()


class UpdateResultTests(unittest.TestCase):
    def poll(self, *event):
        import queue
        from venus8 import updater
        app = bare_app()
        app.events = queue.Queue()
        app.release, app.updating, app.update_state = None, False, "checking"
        app.events.put(event)
        with mock.patch.object(updater, "is_portable", return_value=False):
            app.poll()
        return app

    def test_results_drive_the_button_without_message_boxes(self):
        from venus8 import app as app_module
        with mock.patch.object(app_module, "messagebox") as boxes:
            self.assertEqual(self.poll("update_check", None, None, True).update_state, "current")
            self.assertEqual(self.poll("update_check", None, "offline", True).update_state, "error")
            newer = {"tag_name": "v99.0.0",
                     "assets": [{"name": "Venus-8-v99.0.0-Windows-Setup.exe"}]}
            app = self.poll("update_check", newer, None, False)
            self.assertEqual(app.update_state, "available")
            self.assertEqual(app.release, newer)
            self.assertEqual(self.poll("update_failed", "hash").update_state, "error")
        self.assertFalse(boxes.method_calls)


class ReadoutTests(unittest.TestCase):
    def test_controls_show_their_own_units(self):
        from venus8.display import format_value
        self.assertEqual(format_value("osc1_octave", 0.75), "+1")
        self.assertEqual(format_value("osc2_fine", 0.25), "-25 cents")
        self.assertEqual(format_value("osc3_tune", 1.0), "+12.0 st")
        self.assertEqual(format_value("cutoff", 0.42), "42%")

    def test_octave_knob_snaps_to_detents(self):
        app = bare_app()
        app.change("osc1_octave", 0.81)
        self.assertEqual(app.synth.get_param("osc1_octave"), 0.75)
        self.assertEqual(app.last_param, "osc1_octave")
        app.change("volume@header", 0.3)
        self.assertEqual(app.synth.get_param("volume"), 0.3)
        self.assertEqual(app.last_param, "volume")


    def test_old_patch_files_reset_new_parameters(self):
        import json, tempfile
        from pathlib import Path
        app = bare_app()
        app.synth.set_param("osc1_octave", 1.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Old.json"
            path.write_text(json.dumps({"name": "Old", "params": {"cutoff": 0.3}}), encoding="utf-8")
            app.open_patch(path)
        self.assertEqual(app.synth.get_param("osc1_octave"), 0.5)
        self.assertEqual(app.synth.get_param("cutoff"), 0.3)


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
