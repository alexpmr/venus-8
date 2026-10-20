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


    def test_master_and_effects_headers_line_up(self):
        def orange(p):
            return p[0] > 150 and 60 < p[1] < 140 and p[2] < 90
        for y in range(592, 606):
            self.assertTrue(orange(self.clean.getpixel((800, y))), y)
            self.assertTrue(orange(self.clean.getpixel((1390, y))), y)
        self.assertFalse(orange(self.clean.getpixel((1390, 575))))

    def test_modulation_matrix_became_the_drawbar_panel(self):
        from venus8.components import DRAWBAR_PANEL
        self.assertGreater(sum(amber(p) for p in self.art.crop(DRAWBAR_PANEL).getdata()), 0)
        self.assertEqual(sum(amber(p) for p in self.clean.crop(DRAWBAR_PANEL).getdata()), 0)


class OrganPanelTests(unittest.TestCase):
    def test_switches_and_drive_fit_beside_the_drawbars(self):
        from venus8.components import (DRAWBAR_PANEL, DRAWBAR_WIDTH, DRAWBAR_X,
                                       ORGAN_SWITCHES)
        x1, y1, x2, y2 = DRAWBAR_PANEL
        right = DRAWBAR_X[-1] + DRAWBAR_WIDTH / 2
        boxes = [box for _, box in ORGAN_SWITCHES.values()]
        cx, cy, r = KNOB_GEOMETRY["organ_drive"]
        boxes.append((cx - r, cy - r, cx + r, cy + r))
        for bx1, by1, bx2, by2 in boxes:
            self.assertGreater(bx1, right + 4)
            self.assertTrue(x1 <= bx1 < bx2 <= x2 and y1 <= by1 < by2 <= y2)
        for a in boxes:
            for b in boxes:
                if a is not b:
                    self.assertTrue(a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
        for left, nxt in zip(DRAWBAR_X, DRAWBAR_X[1:]):
            self.assertGreater(nxt - left, DRAWBAR_WIDTH)

    def test_switch_lights_its_led(self):
        from venus8.components import render_switch
        lit = lambda image: sum(amber(p) for p in image.getdata() if p[3] > 200)
        off, on = render_switch("PERC", False, (60, 22), 1.0), render_switch("PERC", True, (60, 22), 1.0)
        self.assertEqual(off.size, (60, 22))
        self.assertEqual(lit(off), 0)
        self.assertGreater(lit(on), 5)


class FMPanelTests(unittest.TestCase):
    def test_fm_buttons_have_lit_faces_and_are_not_greyed(self):
        from venus8.components import FM_BUTTONS
        with Image.open("docs/venus-8-mockup.png") as image:
            art = image.convert("RGB")
        clean, _ = clean_artwork(art)
        sprites = panel_sprites(art, clean)
        for osc, box in FM_BUTTONS.items():
            face = sprites["fm"][osc]
            self.assertEqual(face.size, clean.crop(box).size)
            self.assertGreater(sum(amber(p) for p in face.getdata() if p[3] > 200), 5)
            self.assertGreater(max(clean.crop(box).convert("L").getdata()), 120)   # legend readable
            for name, area in INACTIVE_AREAS.items():
                self.assertFalse(box[0] < area[2] and area[0] < box[2]
                                 and box[1] < area[3] and area[1] < box[3], (osc, name))

    def test_fm_knobs_and_mod_env_are_live_controls(self):
        for osc in (1, 2, 3):
            self.assertIn(f"osc{osc}_fm", KNOB_GEOMETRY)
            self.assertNotIn(f"osc{osc}_pw2", INACTIVE_KNOBS)
        for stage in ("attack", "decay", "sustain", "release"):
            self.assertIn(f"mod_{stage}", PAINTED_CAPS)
        self.assertNotIn("mod_env", INACTIVE_FADER_BANKS)


class EffectsAndTubeTests(unittest.TestCase):
    def test_effect_leds_start_unlit_and_light_from_the_art(self):
        from venus8.components import FX_LEDS
        with Image.open("docs/venus-8-mockup.png") as image:
            art = image.convert("RGB")
        clean, _ = clean_artwork(art)
        sprites = panel_sprites(art, clean)
        for ident, box in FX_LEDS.items():
            self.assertEqual(sum(amber(p) for p in clean.crop(box).getdata()), 0, ident)
            self.assertGreater(sum(amber(p) for p in sprites["leds"][ident].getdata()), 5, ident)
        for ident in ("chorus_depth", "chorus_rate", "phaser_depth", "phaser_rate", "tube_drive"):
            self.assertIn(ident, KNOB_GEOMETRY)
            self.assertNotIn(ident, INACTIVE_KNOBS)

    def test_tube_glows_brighter_with_drive(self):
        from venus8.components import render_tube
        warm = lambda image: sum(max(0, p[0] - p[2]) * p[3] // 255 for p in image.getdata())
        cold, hot = render_tube(0.1, 1.0), render_tube(1.0, 1.0)
        self.assertEqual(cold.size, hot.size)
        self.assertGreater(warm(hot), 3 * warm(cold))


class FilterLfoReverbPanelTests(unittest.TestCase):
    def test_new_controls_are_live(self):
        from venus8.components import FX_LEDS, LFO_WAVE_BOXES, render_lfo_button
        for ident in ("key_track", "lfo_fade", "lfo2_fade", "reverb_size", "reverb_damp",
                      "reverb_mix", "width"):
            self.assertIn(ident, KNOB_GEOMETRY)
        for ident in ("fenv_attack", "fenv_decay", "fenv_sustain", "fenv_release"):
            self.assertIn(ident, PAINTED_CAPS)
        self.assertFalse(INACTIVE_FADER_BANKS)
        for ident in ("reverb_on", "filter_env_on", "lfo_sync", "lfo2_sync"):
            self.assertIn(ident, FX_LEDS)
        self.assertEqual(len(LFO_WAVE_BOXES), 8)
        lit = lambda image: sum(amber(p) for p in image.getdata() if p[3] > 200)
        for index in range(4):
            off, on = (render_lfo_button(index, state, (50, 56), 1.0) for state in (False, True))
            self.assertEqual(lit(off), 0)
            self.assertGreater(lit(on), 5)


class VintageColumnTests(unittest.TestCase):
    def test_widened_chassis_keeps_the_artwork_and_holds_the_new_controls(self):
        from venus8.components import (EXT_CUT, EXT_KNOBS, EXT_SECTIONS, EXT_SWITCHES, EXT_W,
                                       extend_chassis)
        with Image.open("docs/venus-8-mockup.png") as image:
            art = image.convert("RGB")
        clean, _ = clean_artwork(art)
        wide = extend_chassis(clean, art)
        self.assertEqual(wide.size, (clean.width + EXT_W, clean.height))
        self.assertEqual(wide.crop((0, 0, EXT_CUT, 959)).tobytes(),
                         clean.crop((0, 0, EXT_CUT, 959)).tobytes())
        self.assertEqual(wide.crop((EXT_CUT + EXT_W, 0, wide.width, 959)).tobytes(),
                         clean.crop((EXT_CUT, 0, clean.width, 959)).tobytes())
        boxes = [box for _, box in EXT_SWITCHES.values()]
        boxes += [(x - r, y - r, x + r, y + r) for x, y, r in EXT_KNOBS.values()]
        for x1, y1, x2, y2 in boxes:
            self.assertTrue(EXT_CUT <= x1 < x2 <= EXT_CUT + EXT_W)
            self.assertTrue(any(sx1 <= x1 and x2 <= sx2 and sy1 <= y1 and y2 <= sy2
                                for _, (sx1, sy1, sx2, sy2) in EXT_SECTIONS))
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                self.assertTrue(a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

    def test_osc_sync_ring_noise_leds_start_unlit(self):
        from venus8.components import FX_LEDS
        with Image.open("docs/venus-8-mockup.png") as image:
            art = image.convert("RGB")
        clean, _ = clean_artwork(art)
        sprites = panel_sprites(art, clean)
        for ident in ("osc1_sync", "osc2_sync", "osc1_ring", "osc3_noise"):
            self.assertEqual(sum(amber(p) for p in clean.crop(FX_LEDS[ident]).getdata()), 0, ident)
            self.assertGreater(sum(amber(p) for p in sprites["leds"][ident].getdata()), 5, ident)


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

    def test_drawbar_grows_with_its_position(self):
        from venus8.components import render_drawbar
        sizes = [render_drawbar(2, position, 1.0).size for position in range(9)]
        self.assertEqual(len({w for w, h in sizes}), 1)
        self.assertEqual([h for w, h in sizes], sorted(h for w, h in sizes))
        self.assertLess(sizes[0][1], sizes[8][1])

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
