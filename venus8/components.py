"""Independent hardware components for the Venus-8 panel, rendered with Pillow.

The approved artwork is only the static chassis. Knobs, fader caps and keys
painted into it are erased, and every control is drawn as its own sprite so
it can move, rotate or light up on its own. No Tk calls are made here.
"""
import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

# Knob LED-ring geometry measured on the 1600 x 959 artwork: (cx, cy, ring radius).
KNOB_GEOMETRY = {
    "osc1_tune": (163, 190, 21), "osc2_tune": (377, 190, 21),
    "osc3_tune": (592, 189, 21),
    "cutoff": (986, 185, 32), "resonance": (1080, 185, 32),
    "drive": (991, 271, 23),
    "lfo_rate": (77, 459, 23), "lfo_depth": (138, 460, 23),
    "delay_time": (1060, 660, 18), "delay_feedback": (1115, 660, 18),
    "delay_mix": (1165, 659, 18),
    "volume": (1477, 640, 26),
}
KNOB_START, KNOB_SWEEP = 135.0, 270.0      # degrees, clockwise from +x (screen)
KNOB_DOTS = 31

# Painted knobs with no function yet: (cx, cy, radius incl. LED ring/scale).
# They are greyed out so working and future controls are easy to tell apart.
INACTIVE_KNOBS = {
    "osc1_octave": (88, 193, 30), "osc1_fine": (224, 193, 25),
    "osc1_pw": (90, 251, 28), "osc1_pw2": (165, 251, 28), "osc1_pwm": (224, 251, 28),
    "osc2_octave": (304, 194, 30), "osc2_fine": (438, 194, 25),
    "osc2_pw": (304, 252, 28), "osc2_pw2": (380, 252, 28), "osc2_pwm": (438, 251, 28),
    "osc3_octave": (518, 193, 30), "osc3_fine": (653, 193, 25),
    "osc3_pw": (519, 251, 28), "osc3_pw2": (594, 251, 28), "osc3_pwm": (654, 252, 28),
    "key_track": (1065, 274, 27),
    "lfo1_fade": (197, 465, 23),
    "lfo2_rate": (317, 462, 27), "lfo2_depth": (377, 462, 27), "lfo2_fade": (434, 464, 23),
    "arp_rate": (82, 648, 23), "arp_gate": (140, 647, 23), "arp_oct": (190, 644, 21),
    "seq_gate": (433, 601, 22), "seq_swing": (488, 600, 22),
    "chorus_depth": (798, 662, 22), "chorus_rate": (860, 661, 22),
    "phaser_depth": (930, 661, 22), "phaser_rate": (993, 662, 22),
    "reverb_size": (1226, 661, 22), "reverb_damp": (1273, 661, 22),
    "reverb_mix": (1324, 661, 22),
    "width": (1407, 644, 29),
    "detune": (341, 767, 24), "spread": (405, 767, 24), "glide_time": (476, 768, 22),
    "global_volume": (1254, 773, 28), "global_balance": (1321, 773, 28),
    "global_tune": (1429, 770, 22),
    "header_volume": (1517, 44, 31),
}
# Fader banks with no function yet (Filter Env and Mod Env): boxes.
INACTIVE_FADER_BANKS = {
    "filter_env": (1280, 122, 1400, 284),
    "mod_env": (1424, 122, 1546, 284),
}

# Fader caps painted into the artwork: (slot centre x, glowing line y).
PAINTED_CAPS = {
    "osc1_level": (722, 190), "osc2_level": (765, 226),
    "osc3_level": (809, 210), "sub_level": (853, 252),
    "noise_level": (897, 216),
    "attack": (1156, 225), "decay": (1186, 199),
    "sustain": (1215, 180), "release": (1245, 165),
}
CAP_REACH = 16
FADER_TRACK = {"osc": (161, 285), "env": (151, 278)}   # slot top/bottom rows

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
    return "osc" if PAINTED_CAPS[ident][0] < 1000 else "env"


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


def clean_artwork(art):
    """Chassis without painted knobs, caps or keys, plus the real fader cap sprites."""
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
        fill = tuple(round(sum(p[i] for p in ring) / len(ring)) for i in range(3))
        mask = Image.new("L", clean.size, 0)
        ImageDraw.Draw(mask).ellipse((cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(2))
        clean.paste(fill, (0, 0) + clean.size, mask)
    grey_out(clean, inactive_mask(clean.size))
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
    return mask.filter(ImageFilter.GaussianBlur(1.2))


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def render_knob(radius, value, scale, enabled=True):
    """Rotary knob with LED ring, RGBA, sized (2*(radius+4))*scale square."""
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
    for i in range(KNOB_DOTS):
        t = i / (KNOB_DOTS - 1)
        angle = math.radians(KNOB_START + KNOB_SWEEP * t)
        x, y = c + ring*math.cos(angle), c + ring*math.sin(angle)
        lit = enabled and t <= value + 1e-6
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
    angle = math.radians(KNOB_START + KNOB_SWEEP * value)
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
