import unittest
from venus8.mockup_ui import ART_W, ART_H, KNOBS, SLIDERS, BUTTONS


class MockupLayoutTests(unittest.TestCase):
    def test_reference_resolution(self):
        self.assertEqual((ART_W, ART_H), (1600, 959))

    def test_control_hotspots_cover_supported_synth_parameters(self):
        for ident in ("osc1_tune", "osc2_tune", "osc3_tune",
                      "cutoff", "drive", "lfo_rate", "lfo_depth",
                      "delay_time", "delay_mix", "delay_feedback", "volume"):
            self.assertIn(ident, KNOBS)
        for ident in ("osc1_level", "osc2_level", "osc3_level",
                      "sub_level", "noise_level", "attack", "release",
                      "pitch_bend", "modwheel"):
            self.assertIn(ident, SLIDERS)

    def test_buttons_and_geometry(self):
        self.assertIn("check_update", BUTTONS)
        self.assertIn("settings", BUTTONS)
        self.assertIn("save", BUTTONS)
        for i in (1,2,3):
            for j in range(4):
                self.assertIn(f"wave{i}_{j}", BUTTONS)
        for label,box in BUTTONS.items():
            x1,y1,x2,y2=box
            self.assertGreater(x2,x1,label)
            self.assertGreater(y2,y1,label)
            self.assertLessEqual(x2,ART_W,label)
            self.assertLessEqual(y2,ART_H,label)


if __name__=="__main__":
    unittest.main()
