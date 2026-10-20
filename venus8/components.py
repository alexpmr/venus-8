"""Independent hardware components for the Venus-8 panel, rendered with Pillow.

The approved artwork is only the static chassis. Knobs, fader caps and keys
painted into it are erased, and every control is drawn as its own sprite so
it can move, rotate or light up on its own. No Tk calls are made here.
"""
import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# Knob LED-ring geometry measured on the 1600 x 959 artwork: (cx, cy, ring radius).
KNOB_GEOMETRY = {
    "osc1_tune": (163, 190, 21), "osc2_tune": (377, 190, 21),
    "osc3_tune": (592, 189, 21),
    "cutoff": (986, 185, 32), "resonance": (1080, 185, 32),
    "drive": (991, 271, 23),
    "lfo_rate": (77, 459, 23), "lfo_depth": (138, 460, 23),
    "lfo2_rate": (315, 459, 23), "lfo2_depth": (376, 459, 23),
    "delay_time": (1060, 660, 18), "delay_feedback": (1115, 660, 18),
    "delay_mix": (1165, 659, 18),
    "volume": (1477, 646, 26),
    "osc1_octave": (88, 193, 19), "osc2_octave": (304, 194, 19), "osc3_octave": (518, 193, 19),
    "osc1_fine": (224, 193, 21), "osc2_fine": (438, 194, 21), "osc3_fine": (653, 193, 21),
    "volume@header": (1517, 44, 26),
    "organ_drive": (1517, 513, 18),
    # FM amount: the second (duplicate) PW knob of each oscillator.
    "osc1_fm": (163, 254, 21), "osc2_fm": (377, 254, 21), "osc3_fm": (592, 253, 21),
    "chorus_depth": (798, 662, 18), "chorus_rate": (860, 661, 18),
    "phaser_depth": (930, 661, 18), "phaser_rate": (993, 662, 18),
    "tube_drive": (442, 36, 15),
    "key_track": (1065, 274, 23),
    "lfo_fade": (197, 465, 20), "lfo2_fade": (434, 464, 20),
    "reverb_size": (1226, 661, 18), "reverb_damp": (1273, 661, 18),
    "reverb_mix": (1324, 661, 18),
    "width": (1407, 650, 26),
    "osc1_pw": (88, 254, 21), "osc1_pwm": (223, 254, 21),
    "osc2_pw": (303, 254, 21), "osc2_pwm": (437, 254, 21),
    "osc3_pw": (518, 253, 21), "osc3_pwm": (653, 253, 21),
    "unison_detune": (339, 769, 19), "glide_time": (475, 770, 17),
    "arp_rate": (80, 644, 18), "arp_gate": (138, 644, 18), "arp_oct": (189, 645, 15),
    "unison_spread": (403, 769, 19), "global_volume": (1252, 778, 20),
    "balance": (1322, 778, 20), "master_tune": (1429, 773, 14),
    "seq_gate": (432, 598, 17), "seq_swing": (487, 598, 17),
}
# Step sequencer: 16 step buttons, REC (painted STEPS) and the info strip.
SEQ_STEP_BOXES = tuple((round(278 + i * 29.25) + 1, 643, round(278 + (i + 1) * 29.25) - 2, 671)
                       for i in range(16))
SEQ_ROW = (274, 638, 750, 676)
SEQ_REC_BOX = (282, 600, 323, 622)
SEQ_INFO = (574, 592, 748, 624)
# SYNC buttons of the arpeggiator and the sequencer (both: MIDI clock sync).
SYNC_BUTTONS = ((211, 644, 247, 667), (528, 600, 570, 622))
# Layer / Split: patch selectors (box, painted text) and the split point.
PART_SELECTORS = {"lower": ((984, 758, 1092, 778), (987, 760, 1075, 776)),
                  "upper": ((984, 783, 1092, 803), (987, 785, 1075, 801))}
SPLIT_SPINNER = ((1128, 777, 1170, 799), (1179, 777, 1193, 788), (1179, 789, 1193, 800))
SPLIT_TAB = (210, 697, 364, 731)
# Up/down value spinners: (value text box, up arrow, down arrow).
SPINNERS = {"transpose": ((595, 766, 633, 792), (634, 765, 652, 779), (634, 780, 652, 795)),
            "octave_shift": ((699, 766, 735, 792), (737, 765, 754, 779), (737, 780, 754, 795)),
            "bend_range": ((209, 852, 236, 879), (238, 852, 254, 865), (238, 866, 254, 879)),
            "polyphony": ((1496, 769, 1527, 797), (1528, 768, 1545, 782), (1528, 783, 1545, 798)),
            "seq_steps": ((350, 594, 377, 622), (378, 595, 394, 607), (378, 608, 394, 621))}
SPINNER_STEPS = {"transpose": 24, "octave_shift": 6, "bend_range": 23, "polyphony": 15,
                 "seq_steps": 15}
TUNE_READOUT = (1401, 794, 1457, 807)
GLIDE_CONST_BOX = (509, 760, 553, 791)
SEARCH_BOX = (1216, 25, 1247, 57)
MIDI_LEDS = ((1276, 51), (1298, 51))      # activity, connection
PANEL_TABS = {"keyboard_tab": (367, 697, 500, 731), "midi_tab": (505, 697, 587, 731)}
# Arpeggiator: mode selector, and the ARP / HOLD buttons of the performance row.
ARP_MODE_BOX = (135, 594, 240, 616)
ARP_MODE_TEXT = (139, 598, 224, 613)
ARP_BUTTONS = {"arp_on": ("ARP", (787, 760, 835, 786)), "arp_hold": ("HOLD", (848, 760, 897, 786))}
# Voice mode buttons (POLY, MONO, LEGATO, UNISON).
VOICE_MODE_BOXES = ((51, 760, 100, 791), (114, 760, 162, 791),
                    (176, 760, 225, 791), (238, 760, 287, 791))
VOICE_MODE_LABELS = ("POLY", "MONO", "LEGATO", "UNISON")
# Effect on/off LEDs (painted lit; unlit until switched on) and the chorus
# title, which reads CHORUS or FLANGER and switches between them on a click.
FX_LEDS = {"chorus_on": (866, 613, 890, 635), "phaser_on": (999, 613, 1023, 635),
           "reverb_on": (1318, 613, 1342, 635), "filter_env_on": (1099, 263, 1119, 285),
           "lfo_sync": (234, 446, 255, 467), "lfo2_sync": (473, 446, 494, 467),
           "arp_on@led": (58, 577, 75, 595),
           "osc1_sync": (59, 302, 73, 316), "osc2_sync": (274, 302, 288, 316),
           "osc1_ring": (237, 302, 249, 316), "osc3_noise": (664, 302, 679, 316),
           "osc2_xmod": (451, 302, 464, 316), "osc3_sync": (488, 302, 502, 316),
           "seq_on": (280, 573, 298, 592),
           "part:lower": (928, 762, 942, 777), "part:upper": (928, 787, 942, 802)}
# LEDs painted unlit in the artwork borrow the lit face of a twin.
LED_DONOR = {"osc1_ring": "osc1_sync", "osc2_xmod": "osc1_sync", "osc3_sync": "osc1_sync"}
# Click areas larger than the LED (LED plus its ENV / SYNC button).
LED_CLICK = {"part:lower": (924, 759, 981, 780), "part:upper": (924, 784, 981, 805),
             "seq_on": (277, 570, 332, 596), "osc1_sync": (56, 297, 121, 321), "osc1_ring": (188, 297, 250, 321),
             "osc2_xmod": (403, 297, 466, 321), "osc3_sync": (486, 297, 551, 321),
             "osc2_sync": (271, 297, 335, 321), "osc3_noise": (618, 297, 681, 321),
             "arp_on@led": (55, 574, 110, 600), "filter_env_on": (1095, 260, 1121, 300), "lfo_sync": (226, 444, 264, 492),
             "lfo2_sync": (464, 444, 502, 492)}
# Filter type selector (a dropdown) and its painted text.
FILTER_TYPE_BOX = (953, 113, 1114, 142)
FILTER_TYPE_TEXT = (960, 117, 1082, 137)
# LFO waveform buttons (SINE, TRI, SAW, S&H) with their labels.
LFO_WAVE_BOXES = {(lfo, index): (round(left + index * step), 368,
                                 round(left + (index + 1) * step) - 2, 424)
                  for lfo, left, step in ((1, 52, 52.5), (2, 288, 53.0)) for index in range(4)}
CHORUS_TITLE = (826, 624)
CHORUS_TITLE_BOX = (796, 612, 858, 636)
# Tube in the top bar, where the "VIRTUAL ANALOG SYNTHESIZER" subtitle was.
SUBTITLE_BOX = (362, 20, 506, 62)
TUBE_WINDOW = (368, 11, 400, 69)
# Painted "PW" labels under the FM knobs, repainted as "FM".
FM_LABELS = {1: (163, 284), 2: (377, 284), 3: (592, 284)}
# FM buttons of the SYNC / FM / RING row (artwork boxes).
FM_BUTTONS = {1: (131, 297, 179, 320), 2: (346, 297, 394, 320), 3: (560, 297, 608, 320)}
KNOB_START, KNOB_SWEEP = 135.0, 270.0      # degrees, clockwise from +x (screen)
KNOB_DOTS = 31
# Octave switches follow the painted −2..+2 scale over the top half circle.
# Switch knobs: number of detented positions (octave -2..+2, arpeggio 1..4).
DETENT_KNOBS = {"osc1_octave": 5, "osc2_octave": 5, "osc3_octave": 5, "arp_oct": 4}
DETENT_START, DETENT_SWEEP, DETENT_POSITIONS = 180.0, 180.0, 5

# Painted knobs with no function yet: (cx, cy, radius incl. LED ring/scale).
# They are greyed out so working and future controls are easy to tell apart.
INACTIVE_KNOBS = {
}
# Drawbar organ panel, in place of the painted modulation matrix.
DRAWBAR_PANEL = (1104, 368, 1552, 543)
DRAWBAR_HEADER = (1112, 348, 1546, 367)
DRAWBAR_X = tuple(round(1130 + i * 33) for i in range(9))
DRAWBAR_TOP, DRAWBAR_STEP, DRAWBAR_CAP, DRAWBAR_WIDTH = 386, 15, 24, 28
DRAWBAR_COLORS = ("brown", "brown", "white", "white", "black", "white", "black", "black", "white")
DRAWBAR_FOOTAGES = ("16'", "5⅓'", "8'", "4'", "2⅔'", "2'", "1⅗'", "1⅓'", "1'")
# Organ switches beside the drawbars: (param, label) -> box, two per row.
ORGAN_SWITCHES = {}
for _row, _pair in enumerate((("organ_perc", "PERC"), ("organ_perc_third", "3RD"),
                              ("organ_perc_fast", "P.FAST"), ("organ_click", "CLICK"),
                              ("organ_vibrato", "VIB"), ("organ_chorus", "CHORUS"),
                              ("leslie", "LESLIE"), ("leslie_fast", "FAST"))):
    _x = 1420 + (_row % 2) * 66
    _y = 374 + (_row // 2) * 28
    ORGAN_SWITCHES[_pair[0]] = (_pair[1], (_x, _y, _x + 60, _y + 22))
ORGAN_LABEL_X = 1483                  # centre of the switch column
_DRAWBAR_PAINT = {"brown": ((112, 58, 30), (150, 86, 48), (240, 220, 200)),
                  "white": ((222, 214, 198), (246, 240, 228), (40, 34, 30)),
                  "black": ((30, 30, 32), (64, 64, 68), (230, 224, 214))}

# Oscillator waveform buttons: left edge of SAW per oscillator, 46 px pitch.
WAVE_LEFT = {1: 61, 2: 277, 3: 489}
WAVE_STEP = 46
# Master level meter: two LED columns of 12 segments, top (red) first.
# The MASTER panel is lowered to line up with EFFECTS (see align_master):
# its knobs move down by MASTER_CONTENT_SHIFT and the meter by METER_SHIFT.
MASTER_PANEL = (1361, 1557)              # x range of the panel
MASTER_SHIFT, MASTER_CONTENT_SHIFT, METER_SHIFT = 24, 6, 14
METER_SOURCE_BOX = (1520, 600, 1545, 687)
METER_BOX = (1520, 600 + METER_SHIFT, 1545, 687 + METER_SHIFT)
METER_COLUMNS = ((1522, 1531), (1533, 1542))
METER_ROWS = (605, 611.5, 618, 625, 632, 639, 646, 652.5, 659.5, 666.5, 673.5, 681)
# Top bar status area between the MIDI and VOL separators.
STATUS_BOX = (1322, 22, 1433, 66)

# Painted buttons, LEDs, selectors and bar graphs with no function yet.
INACTIVE_AREAS = {

}

# Fader banks with no function yet (Filter Env and Mod Env): boxes.
INACTIVE_FADER_BANKS = {
}

# Central display (artwork coordinates). Its painted patch name and info
# table are fictional, so they are cleared and redrawn live by the app.
DISPLAY_SCREEN = (544, 377, 869, 545)        # wallpaper area, used by the scope
DISPLAY_NAME_BOX = (549, 464, 859, 537)
DISPLAY_TABLE = (870, 379, 1071, 545)
DISPLAY_ROWS = 7
DISPLAY_INACTIVE = (
    (650, 347, 1066, 374),                   # MOD MATRIX, ARP/SEQ, FX, GLOBAL tabs
    (621, 546, 1076, 571),                   # RANDOM, A/B, UNDO, REDO
)

# Fader caps painted into the artwork: (slot centre x, glowing line y).
PAINTED_CAPS = {
    "osc1_level": (722, 190), "osc2_level": (765, 226),
    "osc3_level": (809, 210), "sub_level": (853, 252),
    "noise_level": (897, 216),
    "attack": (1156, 225), "decay": (1186, 199),
    "sustain": (1215, 180), "release": (1245, 165),
    "fenv_attack": (1296, 234), "fenv_decay": (1328, 199),
    "fenv_sustain": (1357, 188), "fenv_release": (1388, 197),
    "mod_attack": (1442, 220), "mod_decay": (1472, 168),
    "mod_sustain": (1501, 200), "mod_release": (1532, 189),
}
CAP_REACH = 16
FADER_TRACK = {"osc": (161, 285), "env": (151, 278), "fenv": (151, 278), "mod": (151, 278)}   # slot top/bottom rows

# The painted keyboard has an irregular black-key pattern and keys lit in the
# mockup, so the key bed is rebuilt as a real piano layout (C1-C8).
KEYBOARD = (274, 822, 1532, 941)
BLACK_KEY_BOTTOM = 894
LOWEST_NOTE, HIGHEST_NOTE = 24, 108
WHITE_PROFILE_X = 318            # unobstructed ivory key column in the art
BLACK_KEY_SAMPLE = (327, 822, 345, 894)
KEY_GAP = (8, 7, 5)


def keyboard_layout():
    """(note, x1, y1, x2, y2, black) in artwork coordinates, white keys first."""
    x1, y1, x2, y2 = KEYBOARD
    whites = [n for n in range(LOWEST_NOTE, HIGHEST_NOTE + 1)
              if n % 12 in (0, 2, 4, 5, 7, 9, 11)]
    width = (x2 - x1) / len(whites)
    keys = [(n, x1 + i*width, y1, x1 + (i+1)*width, y2, False)
            for i, n in enumerate(whites)]
    black_w = width * 0.66
    for i, n in enumerate(whites):
        if n % 12 in (0, 2, 5, 7, 9) and n + 1 <= HIGHEST_NOTE:
            centre = x1 + (i+1)*width
            keys.append((n + 1, centre - black_w/2, y1,
                         centre + black_w/2, BLACK_KEY_BOTTOM, True))
    return keys


class KeySprites:
    """Ivory/amber white keys and ebony/lit black keys sampled from the art."""

    def __init__(self, art):
        _, y1, _, y2 = KEYBOARD
        self.ivory = art.crop((WHITE_PROFILE_X, y1, WHITE_PROFILE_X + 1, y2))
        self.amber = Image.merge("RGB", [
            band.point(lambda v, k=k: min(255, int(v*k)))
            for band, k in zip(self.ivory.split(), (1.07, 0.93, 0.5))])
        self.ebony = art.crop(BLACK_KEY_SAMPLE)
        self.lit_ebony = Image.blend(
            self.ebony, Image.new("RGB", self.ebony.size, (255, 150, 60)), 0.62)

    def render(self, black, lit, size):
        """One key at screen size (width, height)."""
        w, h = max(3, size[0]), max(3, size[1])
        if black:
            source = self.lit_ebony if lit else self.ebony
            return source.resize((w, h), Image.Resampling.LANCZOS)
        column = (self.amber if lit else self.ivory).resize((1, h), Image.Resampling.LANCZOS)
        key = column.resize((w, h), Image.Resampling.NEAREST)
        key.paste(KEY_GAP, (0, 0, 1, h))
        key.paste((215, 208, 202) if not lit else (240, 200, 120), (1, 0, 2, h))
        return key


def _bank(ident):
    x = PAINTED_CAPS[ident][0]
    return "osc" if x < 1000 else "env" if x < 1280 else "fenv" if x < 1410 else "mod"


def cap_half_width(ident):
    """Cap body plus glow, kept under half the fader pitch."""
    return 17 if _bank(ident) == "osc" else 15


def _cap_body(ident):
    """Opaque cap body (without glow) in artwork coordinates."""
    x, line = PAINTED_CAPS[ident]
    half = 14 if _bank(ident) == "osc" else 12
    return (x - half - 1, line - 11, x + half + 2, line + 12)


def _cap_box(ident):
    x, line = PAINTED_CAPS[ident]
    half = cap_half_width(ident)
    return (x - half, line - CAP_REACH, x + half + 1, line + CAP_REACH + 1)


def align_master(art):
    """Lower the MASTER panel so its top lines up with the EFFECTS panel."""
    image = art.copy()
    x1, x2 = MASTER_PANEL
    median = lambda box: tuple(int(v) for v in np.median(
        np.asarray(image.crop(box)).reshape(-1, 3), axis=0))
    gap = median((x1, 550, x2, 558))
    panel = median((1372, 600, 1392, 700))
    meter = image.crop(METER_SOURCE_BOX)
    mx1, my1, mx2, my2 = METER_SOURCE_BOX
    image.paste(panel, (mx1 - 2, my1 - 2, mx2 + 2, my2 + 2))
    image.paste(image.crop((x1, 590, x2, 694)), (x1, 590 + MASTER_CONTENT_SHIFT))
    image.paste(gap, (x1, 554, x2, 560 + MASTER_SHIFT))
    image.paste(art.crop((x1, 560, x2, 590)), (x1, 560 + MASTER_SHIFT))
    image.paste(meter, METER_BOX[:2])
    return image


def clean_artwork(art):
    """Chassis without painted knobs, caps or keys, plus the real fader cap sprites."""
    art = align_master(art)
    clean = art.copy()
    grey = np.asarray(art.convert("L"), dtype=np.float32)
    for ident, (x, line) in PAINTED_CAPS.items():
        # Ticks line up across each fader bank, so a neighbour's track at the
        # same height (with its own cap far away) replaces the painted cap.
        # The slots are not evenly spaced, so the donor offset is registered
        # on rows where both tracks are clean.
        bank = [o for o in PAINTED_CAPS if _bank(o) == _bank(ident)]
        donor = max(bank, key=lambda o: abs(PAINTED_CAPS[o][1] - line))
        top, bottom = FADER_TRACK[_bank(ident)]
        busy = set()
        for o in (ident, donor):
            busy.update(range(PAINTED_CAPS[o][1] - CAP_REACH - 2, PAINTED_CAPS[o][1] + CAP_REACH + 3))
        rows = [y for y in range(top, bottom) if y not in busy]
        half = cap_half_width(ident)
        target = grey[rows, x - half:x + half + 1]
        nominal = PAINTED_CAPS[donor][0] - x
        dx = min(range(nominal - 3, nominal + 4),
                 key=lambda d: float(np.abs(grey[rows, x + d - half:x + d + half + 1] - target).mean()))
        bx1, by1, bx2, by2 = _cap_box(ident)
        clean.paste(art.crop((bx1 + dx, by1, bx2 + dx, by2)), (bx1, by1))
    caps = {}
    for ident in PAINTED_CAPS:
        box = _cap_box(ident)
        sprite = art.crop(box).convert("RGBA")
        diff = ImageChops.difference(art.crop(box), clean.crop(box)).convert("L")
        alpha = diff.point(lambda v: 0 if v < 14 else min(255, v*4))
        # Keep the cap and its glow only; stray background differences go.
        bx1, by1, bx2, by2 = _cap_body(ident)
        body = Image.new("L", sprite.size, 0)
        ImageDraw.Draw(body).rectangle((bx1 - box[0], by1 - box[1], bx2 - box[0] - 1, by2 - box[1] - 1), fill=255)
        alpha = ImageChops.multiply(alpha, body.filter(ImageFilter.MaxFilter(5)))
        alpha.paste(255, (bx1 - box[0], by1 - box[1], bx2 - box[0], by2 - box[1]))
        sprite.putalpha(alpha)
        caps[ident] = sprite
    for cx, cy, r in KNOB_GEOMETRY.values():
        # Panel colour just outside the LED ring fills the painted knob, with
        # a feathered edge so no seam shows around the new knob.
        ring = [art.getpixel((round(cx + (r+10)*math.cos(a/8)), round(cy + (r+10)*math.sin(a/8))))
                for a in range(0, 50)]
        fill = tuple(sorted(p[i] for p in ring)[len(ring) // 2] for i in range(3))
        mask = Image.new("L", clean.size, 0)
        ImageDraw.Draw(mask).ellipse((cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(2))
        clean.paste(fill, (0, 0) + clean.size, mask)
    grey_out(clean, inactive_mask(clean.size))
    relabel_fm_knobs(clean)
    blank_text(clean, (CHORUS_TITLE[0] - 26, CHORUS_TITLE[1] - 8,
                       CHORUS_TITLE[0] + 26, CHORUS_TITLE[1] + 8))
    blank_text(clean, SUBTITLE_BOX)
    blank_text(clean, FILTER_TYPE_TEXT)
    blank_text(clean, ARP_MODE_TEXT)
    for text_box, _, _ in (*SPINNERS.values(), SPLIT_SPINNER):   # painted "0", "2", "16", "C4"
        blank_text(clean, text_box)
    for _, text in PART_SELECTORS.values():                 # painted "Init Sound"
        blank_text(clean, text)
    blank_text(clean, TUNE_READOUT)
    x1, y1, x2, y2 = MIDI_LEDS[0][0] - 9, MIDI_LEDS[0][1] - 9, MIDI_LEDS[1][0] + 10, MIDI_LEDS[1][1] + 9
    blank_text(clean, (x1, y1, x2, y2))                     # painted lit LEDs, drawn live now
    for left, right in ((52, 264), (288, 502)):          # painted LFO wave labels
        blank_text(clean, (left, 404, right, 426))
    drawbar_panel(clean)
    clear_display(clean)
    # SAW is painted lit on every oscillator: show all wave buttons unlit;
    # the app lights the selected one.
    for osc in WAVE_LEFT:
        # Rebuild SAW on PULSE's unlit background with SAW's icon and label.
        base = clean.crop(wave_box(osc, 1))
        marks = base.convert("L").point(lambda v: 255 if v > 60 else 0).filter(ImageFilter.MaxFilter(3))
        fill = tuple(int(np.median(np.asarray(base)[..., i])) for i in range(3))
        base.paste(fill, (0, 0) + base.size, marks)
        saw = clean.crop(wave_box(osc, 0)).convert("L")
        ink = saw.point(lambda v: 255 if v > 95 else 0)
        grey = saw.point(lambda v: min(235, round(v * 1.2)))
        base.paste(Image.merge("RGB", (grey,) * 3), (0, 0), ink)
        clean.paste(base, wave_box(osc, 0)[:2])
    meter_off = clean.crop(METER_BOX).convert("L").point(lambda v: round(v * 0.25 + 8))
    clean.paste(Image.merge("RGB", (meter_off,) * 3), METER_BOX[:2])
    ImageDraw.Draw(clean).rounded_rectangle(STATUS_BOX, radius=3, fill=(14, 16, 20),
                                            outline=(38, 41, 46))
    x1, y1, x2, y2 = KEYBOARD
    clean.paste(KEY_GAP, (x1, y1, x2, y2))
    # The mockup's lit keys also glow onto the key slip below the keyboard.
    slip = art.crop((x1, y2, x1 + 1, y2 + 10)).resize((x2 - x1, 10))
    clean.paste(slip, (x1, y2))
    return clean, caps


def grey_out(image, mask):
    """Desaturate and darken ``image`` where ``mask`` is set (an "off" control)."""
    dim = image.convert("L").point(lambda v: round(v * 0.42 + 10)).convert("RGB")
    image.paste(dim, (0, 0), mask)


def inactive_mask(size):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for cx, cy, r in INACTIVE_KNOBS.values():
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    for box in INACTIVE_FADER_BANKS.values():
        draw.rectangle(box, fill=255)
    for box in INACTIVE_AREAS.values():
        draw.rectangle(box, fill=255)
    for x1, y1, x2, y2 in FX_LEDS.values():
        draw.rectangle((x1 - 2, y1 - 2, x2 + 2, y2 + 2), fill=255)
    for box in LFO_WAVE_BOXES.values():
        draw.rectangle(box, fill=255)
    for _, (x1, y1, x2, y2) in ARP_BUTTONS.values():
        draw.rectangle((x1 - 3, y1 - 3, x2 + 3, y2 + 3), fill=255)
    for x1, y1, x2, y2 in (GLIDE_CONST_BOX, SEQ_REC_BOX, SEQ_ROW, *SYNC_BUTTONS):
        draw.rectangle((x1 - 3, y1 - 3, x2 + 3, y2 + 3), fill=255)
    for x1, y1, x2, y2 in VOICE_MODE_BOXES:
        draw.rectangle((x1 - 3, y1 - 3, x2 + 3, y2 + 3), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(1.2))


def clear_display(clean):
    """Dim the display wallpaper and blank its fictional name and info table."""
    x1, y1, x2, y2 = DISPLAY_SCREEN
    screen = clean.crop(DISPLAY_SCREEN).point(lambda v: round(v * 0.5))
    clean.paste(screen, (x1, y1))
    draw = ImageDraw.Draw(clean)
    draw.rounded_rectangle(DISPLAY_NAME_BOX, radius=4, fill=(10, 13, 19), outline=(42, 49, 62))
    x1, y1, x2, y2 = DISPLAY_TABLE
    draw.rectangle(DISPLAY_TABLE, fill=(13, 16, 22))
    step = (y2 - y1) / DISPLAY_ROWS
    for row in range(1, DISPLAY_ROWS):
        y = round(y1 + row * step)
        draw.line((x1 + 4, y, x2 - 4, y), fill=(30, 35, 44))
    mask = Image.new("L", clean.size, 0)
    for box in DISPLAY_INACTIVE:
        ImageDraw.Draw(mask).rectangle(box, fill=255)
    grey_out(clean, mask)


def drawbar_panel(clean):
    """Blank the painted modulation matrix into a drawbar panel with a rail."""
    x1, y1, x2, y2 = DRAWBAR_PANEL
    draw = ImageDraw.Draw(clean)
    draw.rectangle(DRAWBAR_PANEL, fill=(22, 23, 26))
    header = np.asarray(clean.crop(DRAWBAR_HEADER)).reshape(-1, 3)
    draw.rectangle(DRAWBAR_HEADER, fill=tuple(int(v) for v in np.median(header, axis=0)))
    # Metal rail the drawbars slide out of, and a dark slot for each.
    right = DRAWBAR_X[-1] + DRAWBAR_WIDTH // 2 + 8
    draw.rectangle((x1 + 8, DRAWBAR_TOP - 10, right, DRAWBAR_TOP), fill=(70, 72, 76))
    draw.line((x1 + 8, DRAWBAR_TOP - 10, right, DRAWBAR_TOP - 10), fill=(120, 122, 126))
    draw.line((x1 + 8, DRAWBAR_TOP, right, DRAWBAR_TOP), fill=(12, 12, 14), width=2)
    # Organ switch plate, divided from the drawbars by a groove.
    draw.line((right + 5, y1 + 4, right + 5, y2 - 4), fill=(8, 8, 10), width=2)
    draw.line((right + 7, y1 + 4, right + 7, y2 - 4), fill=(46, 48, 52))
    for _, box in ORGAN_SWITCHES.values():
        draw.rounded_rectangle(box, radius=3, fill=(10, 10, 12))
    for x in DRAWBAR_X:
        half = DRAWBAR_WIDTH // 2 + 2
        draw.rectangle((x - half, DRAWBAR_TOP - 8, x + half, DRAWBAR_TOP), fill=(8, 8, 10))


def label_font(size):
    """Bold font with fraction glyphs (⅓ ⅔ ⅗): Segoe UI on Windows, else DejaVu."""
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_switch(label, lit, size, scale):
    """Organ tab switch: dark key with an LED and its name, RGBA."""
    k = 4
    w, h = size[0] * k, size[1] * k
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((k, k, w - k - 1, h - k - 1), radius=3 * k,
                           fill=(40, 42, 46, 255) if lit else (28, 29, 32, 255),
                           outline=(96, 98, 104, 255), width=k)
    draw.line((3 * k, 2 * k, w - 4 * k, 2 * k), fill=(110, 112, 118, 255), width=k)
    led = (5 * k, h // 2 - 3 * k, 11 * k, h // 2 + 3 * k)
    if lit:
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((led[0] - 4 * k, led[1] - 4 * k, led[2] + 4 * k, led[3] + 4 * k),
                                     fill=(255, 96, 20, 170))
        image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(3 * k)))
        draw = ImageDraw.Draw(image)
    draw.ellipse(led, fill=(255, 128, 44, 255) if lit else (70, 40, 30, 255),
                 outline=(12, 12, 12, 255))
    draw.text(((led[2] + w) // 2, h // 2), label, font=label_font(8 * k), anchor="mm",
              fill=(246, 232, 210, 255) if lit else (150, 150, 152, 255))
    return image.resize((max(1, round(size[0] * scale)), max(1, round(size[1] * scale))),
                        Image.Resampling.LANCZOS)


def drawbar_length(position):
    return position * DRAWBAR_STEP + DRAWBAR_CAP


def render_drawbar(index, position, scale):
    """Visible part of a pulled drawbar (rod with 1..8 marks and its cap), RGBA."""
    k = 4
    width = DRAWBAR_WIDTH * k
    height = drawbar_length(position) * k
    rod, cap, ink = _DRAWBAR_PAINT[DRAWBAR_COLORS[index]]
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    inset = 4 * k
    rod_end = position * DRAWBAR_STEP * k
    if rod_end:
        draw.rectangle((inset, 0, width - inset, rod_end + 2 * k), fill=rod + (255,))
        draw.line((inset + k, 0, inset + k, rod_end), fill=tuple(min(255, c + 40) for c in rod) + (255,),
                  width=k)
        font = label_font(7 * k)
        for number in range(1, position + 1):
            y = number * DRAWBAR_STEP * k - DRAWBAR_STEP * k // 2
            draw.text((width // 2, y), str(number), fill=ink + (255,), font=font, anchor="mm")
            draw.line((inset, number * DRAWBAR_STEP * k, width - inset, number * DRAWBAR_STEP * k),
                      fill=tuple(max(0, c - 40) for c in rod) + (255,), width=k)
    top = rod_end
    draw.rounded_rectangle((0, top, width - 1, top + DRAWBAR_CAP * k - 1), radius=4 * k,
                           fill=cap + (255,), outline=(10, 10, 10, 255), width=k)
    draw.rectangle((2 * k, top + 2 * k, width - 3 * k, top + 5 * k),
                   fill=tuple(min(255, c + 35) for c in cap) + (255,))
    font = label_font(8 * k)
    draw.text((width // 2, top + DRAWBAR_CAP * k // 2 + k), DRAWBAR_FOOTAGES[index],
              fill=ink + (255,), font=font, anchor="mm")
    size = (max(1, round(DRAWBAR_WIDTH * scale)), max(1, round(drawbar_length(position) * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def wave_box(osc, index):
    x = WAVE_LEFT[osc] + index * WAVE_STEP
    return (x, 110, x + WAVE_STEP - 1, 157)


def meter_box(column, row, source=False):
    """LED box on the panel, or in the original artwork when ``source``."""
    x1, x2 = METER_COLUMNS[column]
    y = METER_ROWS[row] + (0 if source else METER_SHIFT)
    return (x1, round(y - 3), x2, round(y + 3))


def panel_sprites(art, clean):
    """Lit faces for controls whose painted state is fixed in the artwork."""
    waves = {}
    for osc in WAVE_LEFT:
        for index in range(4):
            box = wave_box(osc, index)
            face = clean.crop(box)
            lum = face.convert("L")
            icon = lum.point(lambda v: 255 if v > 105 else 0)
            icon.paste(0, (0, 28, face.width, face.height))      # icon only, not the label
            glow = icon.filter(ImageFilter.GaussianBlur(2.5)).point(lambda v: min(255, v * 2))
            lit = Image.new("RGBA", face.size, (255, 132, 40, 0))
            lit.putalpha(glow)
            core = Image.merge("RGB", [lum.point(lambda v, k=k: min(255, int(v * k)))
                                       for k in (1.25, 0.72, 0.25)]).convert("RGBA")
            core.putalpha(icon)
            lit.alpha_composite(core)
            underline = ImageDraw.Draw(lit)
            underline.line((3, 29, face.width - 4, 29), fill=(255, 150, 60, 230), width=2)
            waves[(osc, index)] = lit
    meter = {(column, row): art.crop(meter_box(column, row, source=True))
             for column in range(2) for row in range(len(METER_ROWS))}
    fm = {}
    for osc, box in FM_BUTTONS.items():
        # Lit FM button: amber legend with a glow and an amber rim.
        lum = clean.crop(box).convert("L")
        legend = lum.point(lambda v: 255 if v > 120 else 0)
        lit = Image.new("RGBA", lum.size, (255, 132, 40, 0))
        lit.putalpha(legend.filter(ImageFilter.GaussianBlur(2.5)).point(lambda v: min(255, v * 3)))
        core = Image.new("RGBA", lum.size, (255, 170, 80, 255))
        core.putalpha(legend)
        lit.alpha_composite(core)
        ImageDraw.Draw(lit).rounded_rectangle((1, 1, lum.width - 2, lum.height - 2), radius=3,
                                              outline=(255, 128, 44, 200), width=1)
        fm[osc] = lit
    leds = {}
    for ident, box in FX_LEDS.items():
        donor = FX_LEDS[LED_DONOR.get(ident, ident)]
        leds[ident] = art.crop(donor).convert("RGBA").resize((box[2] - box[0], box[3] - box[1]))
    return {"waves": waves, "meter": meter, "fm": fm, "leds": leds}


def blank_text(clean, box):
    """Paint over painted lettering with the panel colour around it."""
    x1, y1, x2, y2 = box
    edge = np.concatenate([np.asarray(clean.crop((x1, y1 - 3, x2, y1))).reshape(-1, 3),
                           np.asarray(clean.crop((x1, y2, x2, y2 + 3))).reshape(-1, 3)])
    ImageDraw.Draw(clean).rectangle(box, fill=tuple(int(v) for v in np.median(edge, axis=0)))


def render_tube(glow, scale):
    """Glass vacuum tube in its window; ``glow`` 0..1 lights the heater/plate."""
    k = 4
    x1, y1, x2, y2 = TUBE_WINDOW
    w, h = (x2 - x1) * k, (y2 - y1) * k
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Window bezel and dark recess.
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=5 * k, fill=(12, 10, 9, 255),
                           outline=(70, 66, 62, 255), width=k)
    cx = w // 2
    # Orange glow behind the plate, growing with ``glow``.
    halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    radius = (6 + 8 * glow) * k
    ImageDraw.Draw(halo).ellipse((cx - radius, h * 0.52 - radius * 1.3, cx + radius, h * 0.52 + radius * 1.3),
                                 fill=(255, 110, 20, round(60 + 170 * glow)))
    image = Image.alpha_composite(image, halo.filter(ImageFilter.GaussianBlur(5 * k)))
    draw = ImageDraw.Draw(image)
    # Glass envelope with a domed top and a highlight.
    gx1, gx2, gy1, gy2 = cx - 10 * k, cx + 10 * k, 4 * k, h - 9 * k
    draw.rounded_rectangle((gx1, gy1, gx2, gy2), radius=10 * k, outline=(170, 176, 180, 200), width=k)
    draw.line((gx1 + 3 * k, gy1 + 9 * k, gx1 + 3 * k, gy2 - 8 * k), fill=(230, 236, 240, 150), width=k)
    # Plate (anode), heater filament and getter.
    draw.rectangle((cx - 5 * k, 17 * k, cx + 5 * k, 36 * k), outline=(120, 118, 114, 255),
                   fill=(52, 50, 48, 255), width=k)
    heat = (255, round(120 + 110 * glow), round(40 + 80 * glow), 255)
    draw.line((cx, 19 * k, cx, 34 * k), fill=heat, width=round((1.2 + 1.6 * glow) * k))
    draw.ellipse((cx - 5 * k, 7 * k, cx + 5 * k, 12 * k), fill=(90, 92, 96, 255))
    # Base and pins.
    draw.rounded_rectangle((cx - 11 * k, h - 9 * k, cx + 11 * k, h - 3 * k), radius=2 * k,
                           fill=(30, 28, 26, 255), outline=(80, 76, 70, 255), width=k)
    size = (max(1, round((x2 - x1) * scale)), max(1, round((y2 - y1) * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


LFO_LABELS = ("SINE", "TRI", "SAW", "S&H")


def render_step(on, playing, note, size, scale):
    """Sequencer step: amber when on, the playing one ringed in white, with
    its note offset printed on it."""
    k = 4
    w, h = size[0] * k, size[1] * k
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if on:
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle((2 * k, 2 * k, w - 2 * k, h - 2 * k), radius=3 * k,
                                               fill=(255, 120, 30, 170))
        image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(2 * k)))
    draw = ImageDraw.Draw(image)
    face = (255, 150, 50, 255) if on else (70, 70, 72, 255)
    draw.rounded_rectangle((2 * k, 2 * k, w - 3 * k, h - 3 * k), radius=3 * k, fill=face,
                           outline=(250, 250, 250, 255) if playing else (14, 14, 14, 255),
                           width=2 * k if playing else k)
    draw.text((w / 2, h / 2), f"{note:+d}" if note else "0", font=label_font(7 * k), anchor="mm",
              fill=(50, 22, 4, 255) if on else (170, 170, 170, 255))
    return image.resize((max(1, round(size[0] * scale)), max(1, round(size[1] * scale))),
                        Image.Resampling.LANCZOS)


def render_mode_button(label, lit, size, scale):
    """Performance button: amber when selected, dark otherwise, RGBA."""
    k = 4
    w, h = size[0] * k, size[1] * k
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if lit:
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle((2 * k, 2 * k, w - 2 * k, h - 2 * k), radius=4 * k,
                                               fill=(255, 120, 30, 200))
        image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(2 * k)))
    draw = ImageDraw.Draw(image)
    face = ((250, 170, 70, 255), (232, 128, 36, 255)) if lit else ((44, 45, 49, 255), (26, 27, 30, 255))
    draw.rounded_rectangle((2 * k, 2 * k, w - 3 * k, h - 3 * k), radius=3 * k, fill=face[1],
                           outline=(12, 12, 12, 255), width=k)
    draw.rounded_rectangle((3 * k, 3 * k, w - 4 * k, h // 2), radius=3 * k, fill=face[0])
    draw.text((w / 2, h / 2), label, font=label_font(7 * k), anchor="mm",
              fill=(40, 20, 6, 255) if lit else (200, 198, 194, 255))
    return image.resize((max(1, round(size[0] * scale)), max(1, round(size[1] * scale))),
                        Image.Resampling.LANCZOS)


def render_lfo_button(index, lit, size, scale):
    """LFO wave button: icon on a dark key and the label below, RGBA."""
    k = 4
    w, h = size[0] * k, size[1] * k
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    key_h = round(h * 0.68)
    draw.rounded_rectangle((k, k, w - k - 1, key_h), radius=3 * k,
                           fill=(30, 31, 34, 255) if lit else (20, 21, 23, 255),
                           outline=(58, 60, 64, 255), width=k)
    ink = (255, 150, 60, 255) if lit else (176, 176, 178, 255)
    cx, cy, rx, ry = w / 2, key_h / 2 + k, w * 0.2, key_h * 0.2
    xs = [cx - rx + 2 * rx * i / 40 for i in range(41)]
    if index == 0:
        points = [(x, cy - ry * math.sin(2 * math.pi * i / 40)) for i, x in enumerate(xs)]
    elif index == 1:
        points = [(cx - rx, cy + ry), (cx, cy - ry), (cx + rx, cy + ry)]
    elif index == 2:
        points = [(cx - rx, cy - ry), (cx + rx, cy + ry), (cx + rx, cy - ry)]
    else:
        steps = (0.3, -0.8, 0.6, -0.2)
        points = []
        for i, level in enumerate(steps):
            x1, x2 = cx - rx + 2 * rx * i / 4, cx - rx + 2 * rx * (i + 1) / 4
            points += [(x1, cy - ry * level), (x2, cy - ry * level)]
    if lit:
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(glow).line(points, fill=(255, 110, 30, 200), width=5 * k)
        image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(3 * k)))
        draw = ImageDraw.Draw(image)
    draw.line(points, fill=ink, width=round(1.6 * k), joint="curve")
    draw.text((w / 2, (key_h + h) / 2 + k), LFO_LABELS[index], font=label_font(8 * k), anchor="mm",
              fill=(255, 196, 140, 255) if lit else (196, 194, 190, 255))
    return image.resize((max(1, round(size[0] * scale)), max(1, round(size[1] * scale))),
                        Image.Resampling.LANCZOS)


def relabel_fm_knobs(clean):
    """The second PW knob of each oscillator is the FM amount: "PW" -> "FM"."""
    draw = ImageDraw.Draw(clean)
    font = label_font(10)
    for x, y in FM_LABELS.values():
        box = (x - 14, y - 7, x + 14, y + 7)
        ring = np.asarray(clean.crop((box[0] - 3, box[1] - 3, box[2] + 3, box[1]))).reshape(-1, 3)
        draw.rectangle(box, fill=tuple(int(v) for v in np.median(ring, axis=0)))
        draw.text((x, y), "FM", font=font, anchor="mm", fill=(226, 222, 214))


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def render_knob(radius, value, scale, enabled=True, detents=False):
    """Rotary knob with LED ring, RGBA, sized (2*(radius+4))*scale square.

    With ``detents`` (True = 5, or a count) it is a switch over the top half circle and
    only the selected position's LED is lit.
    """
    positions = DETENT_POSITIONS if detents is True else int(detents)
    start, sweep, dots = ((DETENT_START, DETENT_SWEEP, positions) if detents
                          else (KNOB_START, KNOB_SWEEP, KNOB_DOTS))
    k = 4                                   # supersampling for clean edges
    unit = scale * k
    size = max(8, math.ceil(2 * (radius + 4) * scale))
    n = size * k
    c = n / 2
    value = max(0.0, min(1.0, float(value)))
    image = Image.new("RGBA", (n, n), (0, 0, 0, 0))

    # LED ring: lit dots up to the value with a soft amber glow.
    glow = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    leds = ImageDraw.Draw(image)
    halo = ImageDraw.Draw(glow)
    dot = (1.15 if radius >= 28 else 0.95) * unit
    ring = (radius - 1.5) * unit
    for i in range(dots):
        t = i / (dots - 1)
        angle = math.radians(start + sweep * t)
        x, y = c + ring*math.cos(angle), c + ring*math.sin(angle)
        lit = enabled and (abs(t - value) < 0.5 / (dots - 1) if detents else t <= value + 1e-6)
        color = (255, 128, 44, 255) if lit else (150, 146, 140, 200)
        leds.ellipse((x-dot, y-dot, x+dot, y+dot), fill=color)
        if lit:
            g = dot * 2.6
            halo.ellipse((x-g, y-g, x+g, y+g), fill=(255, 96, 20, 150))
    glow = glow.filter(ImageFilter.GaussianBlur(dot * 1.6))
    image = Image.alpha_composite(glow, image)

    body = radius * 0.66 * unit
    # Drop shadow under the knob skirt.
    shadow = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((c-body, c-body + 1.5*unit, c+body, c+body + 2.5*unit),
                                   fill=(0, 0, 0, 200))
    image = Image.alpha_composite(image, shadow.filter(ImageFilter.GaussianBlur(1.5*unit)))
    draw = ImageDraw.Draw(image)
    # Knurled skirt: dark metal lit from the top-left.
    steps = 24
    for i in range(steps):
        t = i / steps
        r = body * (1 - 0.12*t)
        draw.ellipse((c-r - 0.08*body*t, c-r - 0.08*body*t, c+r - 0.08*body*t, c+r - 0.08*body*t),
                     fill=_mix((14, 15, 18), (70, 74, 80), t**2) + (255,))
    draw.ellipse((c-body, c-body, c+body, c+body), outline=(92, 96, 102, 255), width=max(1, round(0.6*unit)))
    # Cap face with a soft radial gradient.
    face = body * 0.80
    for i in range(steps):
        t = i / steps
        r = face * (1 - 0.85*t)
        off = -0.22 * face * t
        draw.ellipse((c-r+off, c-r+off, c+r+off, c+r+off),
                     fill=_mix((10, 11, 13), (52, 55, 60), t**1.5) + (255,))
    # Pointer.
    angle = math.radians(start + sweep * value)
    x1, y1 = c + body*0.28*math.cos(angle), c + body*0.28*math.sin(angle)
    x2, y2 = c + body*0.92*math.cos(angle), c + body*0.92*math.sin(angle)
    width = max(2, round(body * 0.15))
    draw.line((x1, y1, x2, y2), fill=(244, 240, 232, 255) if enabled else (120, 120, 120, 255),
              width=width)
    for x, y in ((x1, y1), (x2, y2)):
        draw.ellipse((x - width/2, y - width/2, x + width/2, y + width/2),
                     fill=(244, 240, 232, 255) if enabled else (120, 120, 120, 255))
    return image.resize((size, size), Image.Resampling.LANCZOS)


def compose_preview(art, values, sliders, pressed=(), scale=1.0):
    """Whole panel as one image, for tests and visual review (not used by the UI).

    ``sliders`` maps fader ids to (x, top, bottom) cap-line travel.
    """
    clean, caps = clean_artwork(art)
    out = clean.convert("RGBA")
    sprites = KeySprites(art)
    for note, x1, y1, x2, y2, black in keyboard_layout():
        key = sprites.render(black, note in pressed, (round(x2) - round(x1), round(y2) - round(y1)))
        out.paste(key, (round(x1), round(y1)))
    for ident, (cx, cy, r) in KNOB_GEOMETRY.items():
        knob = render_knob(r, values.get(ident, 0.5), 1.0)
        out.alpha_composite(knob, (round(cx - knob.width/2), round(cy - knob.height/2)))
    for ident, sprite in caps.items():
        x, top, bottom = sliders[ident]
        y = bottom - (bottom - top) * values.get(ident, 0.5)
        out.alpha_composite(sprite, (x - cap_half_width(ident), round(y) - CAP_REACH))
    out = out.convert("RGB")
    if scale != 1.0:
        out = out.resize((round(out.width*scale), round(out.height*scale)), Image.Resampling.LANCZOS)
    return out


# ---- Panel extension (v0.2.25): a column of vintage-synth sections added
# to the right of the original artwork, which is cut at EXT_CUT and widened.
EXT_CUT, EXT_W = 1558, 240
VIEW3D_BUTTON = (1600, 28, 1712, 60)        # "VISTA 3D" in the widened top bar
EXT_SECTIONS = (("POLY-MOD", (1564, 90, 1792, 292)), ("MODULATION", (1564, 298, 1792, 478)),
                ("CHARACTER", (1564, 484, 1792, 628)), ("E.PIANO", (1564, 634, 1792, 806)))
EXT_KNOBS = {"polymod_env": (1620, 156, 21), "polymod_osc": (1736, 156, 21),
             "moog_mix": (1622, 362, 21), "vintage": (1620, 550, 21), "hpf": (1736, 550, 21),
             "ep_level": (1592, 728, 16), "ep_tone": (1650, 728, 16), "ep_bark": (1708, 728, 16),
             "ep_decay": (1764, 728, 16)}
EXT_SWITCHES = {"polymod_freq": ("FREQ A", (1568, 226, 1638, 250)),
                "polymod_pw": ("PW A", (1643, 226, 1713, 250)),
                "polymod_filter": ("FILTER", (1718, 226, 1788, 250)),
                "osc3_lo": ("OSC3 LO", (1694, 348, 1788, 372)),
                "moog_osc": ("OSC MOD", (1568, 420, 1674, 444)),
                "moog_filter": ("FILT MOD", (1682, 420, 1788, 444))}
# Radio buttons: one value of a parameter each (electric piano model).
EXT_RADIOS = {"ep_model": (("RHODES", (1568, 666, 1640, 690)), ("WURLI", (1643, 666, 1713, 690)),
                           ("CP-70", (1716, 666, 1788, 690)))}
EXT_LABELS = ((1620, 190, "FILT ENV", 11, "ink"), (1736, 190, "OSC B", 11, "ink"),
              (1678, 212, "DESTINO", 9, "dim"), (1678, 272, "OSC A = OSC 1   ·   OSC B = OSC 2", 8, "dim"),
              (1622, 398, "MIX", 11, "ink"), (1584, 384, "OSC3", 8, "dim"), (1662, 384, "NOISE", 8, "dim"),
              (1741, 384, "LFO LENTO", 8, "dim"), (1678, 464, "QUANTIDADE: MOD WHEEL", 9, "dim"),
              (1620, 584, "VINTAGE", 11, "ink"), (1736, 584, "HPF", 11, "ink"),
              (1678, 610, "DERIVA ANALÓGICA  ·  PASSA-ALTAS", 8, "dim"),
              (1592, 758, "LEVEL", 9, "ink"), (1650, 758, "TONE", 9, "ink"), (1708, 758, "BARK", 9, "ink"),
              (1764, 758, "DECAY", 9, "ink"), (1678, 784, "TREMOLO: LFO 1  ·  EFEITOS: CHORUS/PHASER", 8, "dim"))


def extend_chassis(clean, art):
    """Widen the chassis by EXT_W at EXT_CUT and draw the new sections there.
    Everything left of the cut keeps its coordinates."""
    width, height = clean.size
    wide = Image.new("RGB", (width + EXT_W, height))
    wide.paste(clean.crop((0, 0, EXT_CUT, height)), (0, 0))
    wide.paste(clean.crop((EXT_CUT, 0, width, height)), (EXT_CUT + EXT_W, 0))
    # The strip continues the top bar, the panel frame and the key cheek.
    column = clean.crop((EXT_CUT - 2, 0, EXT_CUT - 1, height)).resize((EXT_W, height))
    wide.paste(column, (EXT_CUT, 0))
    draw = ImageDraw.Draw(wide)
    header = tuple(int(v) for v in np.median(np.asarray(art.crop(DRAWBAR_HEADER)).reshape(-1, 3), axis=0))
    draw.rectangle((EXT_CUT, 88, EXT_CUT + EXT_W - 1, 812), fill=(12, 12, 14))
    for title, (x1, y1, x2, y2) in EXT_SECTIONS:
        draw.rounded_rectangle((x1, y1, x2, y2), radius=6, fill=(24, 25, 28), outline=(56, 58, 62))
        draw.rounded_rectangle((x1 + 6, y1 + 4, x2 - 6, y1 + 24), radius=3, fill=header)
        draw.text(((x1 + x2) / 2, y1 + 14), title, font=label_font(13), anchor="mm", fill=(36, 18, 8))
    boxes = [box for _, box in EXT_SWITCHES.values()]
    boxes += [box for options in EXT_RADIOS.values() for _, box in options]
    for x1, y1, x2, y2 in boxes:
        draw.rounded_rectangle((x1, y1, x2, y2), radius=3, fill=(10, 10, 12))
    x1, y1, x2, y2 = VIEW3D_BUTTON
    draw.rounded_rectangle(VIEW3D_BUTTON, radius=4, fill=(22, 24, 28), outline=(90, 94, 100))
    draw.text(((x1 + x2) / 2, (y1 + y2) / 2), "VISTA 3D", font=label_font(13), anchor="mm",
              fill=(255, 176, 94))
    colours = {"ink": (226, 222, 214), "dim": (140, 138, 134)}
    for x, y, text, size, colour in EXT_LABELS:
        draw.text((x, y), text, font=label_font(size), anchor="mm", fill=colours[colour])
    return wide
