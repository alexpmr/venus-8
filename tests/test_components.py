import unittest

from PIL import Image

from venus8.components import (KEYBOARD, KNOB_GEOMETRY, PAINTED_CAPS, KeySprites,
                               clean_artwork, keyboard_layout, render_knob)


def amber(pixel):
    r, g, b = pixel[:3]
    return r > 200 and 90 < g < 200 and b < 110


class KeyboardLayoutTests(unittest.TestCase):
    def test_real_piano_layout(self):
        keys = keyboard_layout()
        notes = sorted(k[0] for k in keys)
        self.assertEqual(notes, list(range(24, 109)))
        for note, x1, y1, x2, y2, black in keys:
            self.assertEqual(black, note % 12 in (1, 3, 6, 8, 10), note)
            self.assertGreaterEqual(x1, KEYBOARD[0] - 1)
            self.assertLessEqual(x2, KEYBOARD[2] + 1)
        whites = [k for k in keys if not k[5]]
        for left, right in zip(whites, whites[1:]):
            self.assertAlmostEqual(left[3], right[1])

    def test_black_keys_listed_after_white_keys_for_hit_testing(self):
        flags = [k[5] for k in keyboard_layout()]
        self.assertEqual(flags, sorted(flags))


class CleanArtworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with Image.open("docs/venus-8-mockup.png") as image:
            cls.art = image.convert("RGB")
        cls.clean, cls.caps = clean_artwork(cls.art)

    def test_painted_fader_caps_are_removed_and_kept_as_sprites(self):
        for ident, (x, line) in PAINTED_CAPS.items():
            window = [(i, j) for i in range(x - 8, x + 9) for j in range(line - 2, line + 3)]
            self.assertTrue(any(amber(self.art.getpixel(p)) for p in window), ident)
            self.assertFalse(any(amber(self.clean.getpixel(p)) for p in window), ident)
            alpha = self.caps[ident].getchannel("A")
            self.assertEqual(alpha.getextrema()[1], 255, ident)

    def test_painted_lit_keys_are_removed(self):
        lit = [x for x in range(KEYBOARD[0], KEYBOARD[2]) if amber(self.art.getpixel((x, 925)))]
        self.assertTrue(lit)
        self.assertFalse(any(amber(self.clean.getpixel((x, 925))) for x in lit))

    def test_painted_knob_pointers_are_removed(self):
        for ident, (cx, cy, r) in KNOB_GEOMETRY.items():
            box = self.clean.crop((cx - r, cy - r, cx + r, cy + r)).convert("L")
            self.assertLess(box.getextrema()[1], 120, ident)


class SpriteTests(unittest.TestCase):
    def test_knob_rotates_and_lights_with_value(self):
        low, high = render_knob(30, 0.0, 1.0), render_knob(30, 1.0, 1.0)
        self.assertEqual(low.size, high.size)
        self.assertEqual(low.mode, "RGBA")
        self.assertNotEqual(low.tobytes(), high.tobytes())
        lit = lambda image: sum(amber(p) for p in image.getdata() if p[3] > 200)
        self.assertGreater(lit(high), lit(low))

    def test_keys_have_idle_and_lit_faces(self):
        with Image.open("docs/venus-8-mockup.png") as image:
            sprites = KeySprites(image.convert("RGB"))
        for black in (False, True):
            idle = sprites.render(black, False, (24, 100))
            lit = sprites.render(black, True, (24, 100))
            self.assertEqual(idle.size, (24, 100))
            self.assertNotEqual(idle.tobytes(), lit.tobytes())


if __name__ == "__main__":
    unittest.main()
