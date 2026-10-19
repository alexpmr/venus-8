import unittest

from PIL import Image, ImageDraw

from venus8.components import (INACTIVE_AREAS, INACTIVE_FADER_BANKS, INACTIVE_KNOBS,
                               KEYBOARD, KNOB_GEOMETRY, METER_BOX, PAINTED_CAPS,
                               WAVE_LEFT, KeySprites, clean_artwork, keyboard_layout,
                               meter_box, panel_sprites, render_knob, wave_box)


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
            disc = Image.new("L", box.size, 0)
            ImageDraw.Draw(disc).ellipse((0, 0, box.width - 1, box.height - 1), fill=255)
            inside = Image.new("L", box.size, 0)
            inside.paste(box, (0, 0), disc)
            self.assertLess(inside.getextrema()[1], 120, ident)


    def test_future_controls_are_greyed_out(self):
        def lit(image, box):
            return sum(amber(p) for p in image.crop(box).getdata())
        for ident, (cx, cy, r) in INACTIVE_KNOBS.items():
            box = (cx - r, cy - r, cx + r, cy + r)
            self.assertEqual(lit(self.clean, box), 0, ident)
        for ident, box in INACTIVE_FADER_BANKS.items():
            self.assertGreater(lit(self.art, box), 0, ident)
            self.assertEqual(lit(self.clean, box), 0, ident)

    def test_working_controls_are_not_greyed_out(self):
        for ident, (x, y, r) in KNOB_GEOMETRY.items():
            for other, (ox, oy, orad) in INACTIVE_KNOBS.items():
                self.assertGreater((x - ox) ** 2 + (y - oy) ** 2, (r + orad) ** 2, (ident, other))
        for ident, (x, line) in PAINTED_CAPS.items():
            for bank, (x1, y1, x2, y2) in INACTIVE_FADER_BANKS.items():
                self.assertFalse(x1 <= x <= x2 and y1 <= line <= y2, (ident, bank))


    def test_inactive_buttons_and_graphs_are_greyed_out(self):
        for ident, box in INACTIVE_AREAS.items():
            lit = sum(amber(p) for p in self.clean.crop(box).getdata())
            self.assertEqual(lit, 0, ident)

    def test_wave_buttons_start_unlit_and_have_lit_faces(self):
        sprites = panel_sprites(self.art, self.clean)
        for osc in WAVE_LEFT:
            saw = wave_box(osc, 0)
            self.assertGreater(sum(amber(p) for p in self.art.crop(saw).getdata()), 0, osc)
            self.assertEqual(sum(amber(p) for p in self.clean.crop(saw).getdata()), 0, osc)
            for index in range(4):
                face = sprites["waves"][(osc, index)]
                self.assertEqual(face.size, self.clean.crop(wave_box(osc, index)).size)
                self.assertGreater(face.getchannel("A").getextrema()[1], 200)

    def test_level_meter_is_dark_until_driven(self):
        sprites = panel_sprites(self.art, self.clean)
        self.assertEqual(len(sprites["meter"]), 24)
        lum = lambda image: max(sum(p) / 3 for p in image.getdata())
        self.assertLess(lum(self.clean.crop(METER_BOX)), 80)
        self.assertGreater(lum(sprites["meter"][(0, 11)]), 150)


class SpriteTests(unittest.TestCase):
    def test_knob_rotates_and_lights_with_value(self):
        low, high = render_knob(30, 0.0, 1.0), render_knob(30, 1.0, 1.0)
        self.assertEqual(low.size, high.size)
        self.assertEqual(low.mode, "RGBA")
        self.assertNotEqual(low.tobytes(), high.tobytes())
        lit = lambda image: sum(amber(p) for p in image.getdata() if p[3] > 200)
        self.assertGreater(lit(high), lit(low))

    def test_octave_switch_lights_one_detent(self):
        def lit(image):
            return sum(amber(p) for p in image.getdata() if p[3] > 200)
        positions = [render_knob(19, v / 4, 2.0, detents=True) for v in range(5)]
        self.assertEqual(len({p.tobytes() for p in positions}), 5)
        sweep = render_knob(19, 1.0, 2.0)
        self.assertLess(lit(positions[4]), lit(sweep))

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
