import unittest
from venus8.app import SECTIONS, BASE_W, BASE_H

class TestCanonicalLayout(unittest.TestCase):
    def test_reference_geometry_and_keyboard_space(self):
        self.assertEqual((BASE_W, BASE_H), (1600, 980))
        sections={name:(x1,y1,x2,y2) for name,x1,y1,x2,y2 in SECTIONS}
        for title in ("OSCILLATOR 1","OSCILLATOR 2","OSCILLATOR 3",
                      "MIXER","FILTER","AMP ENV","FILTER ENV","MOD ENV",
                      "LFO 1","LFO 2","DISPLAY / PATCH",
                      "MODULATION MATRIX","ARPEGGIATOR",
                      "STEP SEQUENCER","EFFECTS","MASTER"):
            self.assertIn(title,sections)
        self.assertLess(sections["MOD ENV"][3], 338)
        self.assertLess(sections["STEP SEQUENCER"][3], 704)
        for name,box in sections.items():
            x1,y1,x2,y2=box
            self.assertGreater(x2,x1,name)
            self.assertGreater(y2,y1,name)
            self.assertLessEqual(x2,BASE_W,name)
            self.assertLessEqual(y2,BASE_H,name)

if __name__=="__main__":
    unittest.main()
