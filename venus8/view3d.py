"""3D view of the Venus-8 as a physical instrument, rear panel included.

Tkinter has no 3D, so this is a small software renderer: the instrument is a
box whose faces are textures (the live panel on top, wood cheeks, a rear panel
with every connector) projected in perspective with Pillow and drawn back to
front. Hovering a rear connector explains it.
"""
import math
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .components import label_font

# Instrument proportions (units = panel pixels): width, depth, height.
WIDTH, DEPTH, HEIGHT = 1840.0, 959.0, 150.0
REAR_SIZE = (1840, 150)
# Rear connectors, left to right as seen from behind: (id, label, kind, x, help).
CONNECTORS = (
    ("power", "POWER", "iec", 1700, "Entrada de energia (cabo IEC, 100–240 V) e chave liga/desliga."),
    ("usb", "USB", "usb", 1540, "USB-B: MIDI e áudio com o computador. O LED pisca ao receber MIDI."),
    ("midi_in", "MIDI IN", "din", 1420, "MIDI IN (DIN 5 pinos): recebe notas de outro teclado ou módulo."),
    ("midi_out", "MIDI OUT", "din", 1320, "MIDI OUT: envia as notas e os controles do Venus-8."),
    ("midi_thru", "MIDI THRU", "din", 1220, "MIDI THRU: repete o que chega no MIDI IN para outro aparelho."),
    ("sustain", "SUSTAIN", "jack", 1080, "Pedal de sustain (tipo switch). Acende enquanto o pedal está pressionado."),
    ("expression", "EXPRESSION", "jack", 990, "Pedal de expressão (TRS): volume ou filtro."),
    ("footswitch", "FOOTSWITCH", "jack", 900, "Footswitch: troca de timbre ou liga o arpejo."),
    ("cv_out", "CV OUT", "mini", 780, "CV OUT (1 V/oitava) para sintetizadores modulares."),
    ("gate_out", "GATE OUT", "mini", 710, "GATE OUT: +5 V enquanto uma tecla está pressionada."),
    ("clock_in", "CLOCK IN", "mini", 640, "CLOCK IN: sincroniza arpejo e sequencer com pulsos externos."),
    ("out_r", "R", "jack", 500, "Saída principal R (P10 balanceada)."),
    ("out_l", "L / MONO", "jack", 410, "Saída principal L/MONO: use só esta para som mono."),
    ("phones", "PHONES", "jack", 300, "Fones de ouvido (P10 estéreo), com volume próprio."),
)
VIEWS = {"Frente": (0.0, 35.0), "Perfil": (60.0, 20.0), "Trás": (180.0, 25.0), "Cima": (0.0, 80.0)}


def rear_panel(state=None):
    """Rear panel texture (seen from behind: left edge is the instrument's right)."""
    state = state or {}
    w, h = REAR_SIZE
    image = Image.new("RGB", (w, h), (26, 27, 30))
    draw = ImageDraw.Draw(image)
    for y in range(h):                                   # brushed metal
        shade = 30 + int(8 * math.sin(y * 0.9) ** 2)
        draw.line((0, y, w, y), fill=(shade, shade + 1, shade + 4))
    draw.rectangle((0, 0, w - 1, 6), fill=(12, 12, 14))
    draw.rectangle((0, h - 7, w - 1, h - 1), fill=(12, 12, 14))
    small, tiny = label_font(13), label_font(10)
    for ident, label, kind, x, _ in CONNECTORS:
        cy = 70
        if kind == "din":
            draw.ellipse((x - 26, cy - 26, x + 26, cy + 26), fill=(150, 152, 156), outline=(40, 40, 44), width=3)
            draw.ellipse((x - 19, cy - 19, x + 19, cy + 19), fill=(14, 14, 16))
            for angle in (-90, -45, 0, 45, 90):
                a = math.radians(angle + 90)
                draw.ellipse((x + 11 * math.cos(a) - 2.5, cy + 11 * math.sin(a) - 2.5,
                              x + 11 * math.cos(a) + 2.5, cy + 11 * math.sin(a) + 2.5), fill=(190, 170, 110))
            draw.rectangle((x - 3, cy + 15, x + 3, cy + 20), fill=(150, 152, 156))
        elif kind == "jack":
            draw.ellipse((x - 18, cy - 18, x + 18, cy + 18), fill=(170, 172, 176), outline=(60, 60, 64), width=2)
            draw.ellipse((x - 8, cy - 8, x + 8, cy + 8), fill=(6, 6, 8))
        elif kind == "mini":
            draw.ellipse((x - 12, cy - 12, x + 12, cy + 12), fill=(170, 172, 176), outline=(60, 60, 64), width=2)
            draw.ellipse((x - 5, cy - 5, x + 5, cy + 5), fill=(6, 6, 8))
        elif kind == "usb":
            draw.rounded_rectangle((x - 20, cy - 18, x + 20, cy + 18), radius=4, fill=(160, 162, 166))
            draw.polygon(((x - 13, cy - 11), (x + 13, cy - 11), (x + 13, cy + 5), (x + 7, cy + 11),
                          (x - 7, cy + 11), (x - 13, cy + 5)), fill=(8, 8, 10))
            draw.rectangle((x - 7, cy - 5, x + 7, cy + 2), fill=(230, 230, 232))
        elif kind == "iec":
            draw.rounded_rectangle((x - 34, cy - 24, x + 34, cy + 24), radius=6, fill=(14, 14, 16),
                                   outline=(80, 80, 84), width=2)
            for dx in (-14, 0, 14):
                draw.rectangle((x + dx - 3, cy - 10, x + dx + 3, cy + 8), fill=(170, 172, 176))
            draw.rounded_rectangle((x + 50, cy - 18, x + 80, cy + 18), radius=3, fill=(20, 20, 22),
                                   outline=(90, 90, 94), width=2)
            draw.rectangle((x + 56, cy - 12, x + 74, cy + 12), fill=(150, 40, 30))
        draw.text((x, 118), label, font=small, anchor="mm", fill=(226, 222, 214))
    # Live LEDs: power, USB/MIDI activity, sustain.
    for x, on, colour in ((1700 - 60, True, (90, 230, 120)), (1540 + 34, state.get("midi"), (80, 200, 255)),
                          (1080 + 30, state.get("sustain"), (255, 150, 50))):
        draw.ellipse((x - 5, 65, x + 5, 75), fill=colour if on else (40, 40, 44), outline=(10, 10, 10))
    # Section captions and the name plate.
    for x1, x2, caption in ((1180, 1460, "MIDI"), (860, 1120, "PEDAIS"), (600, 820, "CV / GATE"),
                            (260, 540, "SAÍDAS")):
        draw.line((x1, 22, x2, 22), fill=(120, 120, 124))
        draw.text(((x1 + x2) / 2, 18), caption, font=tiny, anchor="mb", fill=(170, 168, 160))
    draw.rounded_rectangle((40, 32, 220, 112), radius=6, fill=(18, 18, 20), outline=(160, 150, 120), width=2)
    draw.text((130, 52), "VENUS-8", font=label_font(20), anchor="mm", fill=(240, 150, 60))
    draw.text((130, 76), "VIRTUAL ANALOG SYNTHESIZER", font=label_font(8), anchor="mm", fill=(200, 196, 188))
    draw.text((130, 96), f"S/N VN8-000001 · v{state.get('version', '')}", font=label_font(9),
              anchor="mm", fill=(170, 166, 158))
    return image


def panel_snapshot(renderer, synth):
    """The panel as it looks now: chassis plus keys, knobs, fader caps and
    drawbars at their current values (artwork units)."""
    from .components import (DRAWBAR_TOP, DRAWBAR_WIDTH, DRAWBAR_X, CAP_REACH, KeySprites,
                             cap_half_width, keyboard_layout, render_drawbar, render_knob)
    from .mockup_ui import KNOBS, SLIDERS
    top = renderer.original.convert("RGBA")
    for note, x1, y1, x2, y2, black in keyboard_layout():
        size = (round(x2) - round(x1), round(y2) - round(y1))
        top.paste(renderer.key_sprites.render(black, False, size), (round(x1), round(y1)))
    for ident, (x, y, r) in KNOBS.items():
        knob = render_knob(r, synth.get_param(ident), 1.0)
        top.alpha_composite(knob, (round(x - knob.width / 2), round(y - knob.height / 2)))
    for ident, sprite in renderer.caps.items():
        x, y1, y2 = SLIDERS[ident]
        y = y2 - (y2 - y1) * synth.get_param(ident)
        top.alpha_composite(sprite, (x - cap_half_width(ident), round(y) - CAP_REACH))
    for index, x in enumerate(DRAWBAR_X):
        bar = render_drawbar(index, round(synth.get_param(f"drawbar{index + 1}") * 8), 1.0)
        top.alpha_composite(bar, (round(x - DRAWBAR_WIDTH / 2), DRAWBAR_TOP))
    return top.convert("RGB")


def press_keys(top, pressed, scale):
    """Light the keys being played on a copy of the panel texture."""
    from .components import keyboard_layout
    if not pressed:
        return top
    lit = top.copy()
    draw = ImageDraw.Draw(lit)
    for note, x1, y1, x2, y2, black in keyboard_layout():
        if note in pressed:
            draw.rectangle((x1 * scale, y1 * scale, x2 * scale, y2 * scale),
                           fill=(250, 150, 60) if not black else (200, 110, 40))
    return lit


def wood(art, size):
    """Wood cheek texture from the artwork's side strip."""
    strip = art.crop((2, 100, 26, 860)).transpose(Image.Transpose.ROTATE_90)
    return strip.resize(size, Image.Resampling.BICUBIC)


def _perspective(src, dst):
    """Pillow PERSPECTIVE coefficients mapping output points ``dst`` to ``src``."""
    rows, rhs = [], []
    for (x, y), (u, v) in zip(dst, src):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        rhs += [u, v]
    return np.linalg.solve(np.array(rows, dtype=float), np.array(rhs, dtype=float))


class Instrument3D:
    """Box model with textured faces, a camera orbit and back-to-front drawing."""

    def __init__(self, panel, art):
        self.textures = {"top": panel, "front": Image.new("RGB", (920, 75), (16, 16, 18)),
                         "left": wood(art, (480, 75)), "right": wood(art, (480, 75)),
                         "back": rear_panel()}
        self.back_quad = None
        self.back_coeffs = None

    def faces(self):
        """Faces as (name, corners in texture order: TL, TR, BR, BL)."""
        x0, x1 = -WIDTH / 2, WIDTH / 2
        z0, z1 = -DEPTH / 2, DEPTH / 2              # z1 = player side
        y0, y1 = 0.0, HEIGHT
        return (("top", ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1))),
                ("front", ((x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1))),
                ("back", ((x1, y1, z0), (x0, y1, z0), (x0, y0, z0), (x1, y0, z0))),
                ("left", ((x0, y1, z0), (x0, y1, z1), (x0, y0, z1), (x0, y0, z0))),
                ("right", ((x1, y1, z1), (x1, y1, z0), (x1, y0, z0), (x1, y0, z1))))

    def render(self, size, yaw, pitch, zoom=1.0):
        w, h = size
        out = Image.new("RGB", size, (14, 15, 18))
        bg = ImageDraw.Draw(out)
        for y in range(h):                             # studio backdrop
            c = int(18 + 22 * y / h)
            bg.line((0, y, w, y), fill=(c, c, c + 4))
        yr, pr = math.radians(yaw), math.radians(pitch)
        cy_, sy_, cp, sp = math.cos(yr), math.sin(yr), math.cos(pr), math.sin(pr)
        dist = 2600.0 / zoom
        focal = min(w, h) * 1.25

        def rotate(point):
            x, y, z = point[0], point[1] - HEIGHT / 2, point[2]
            x, z = x * cy_ - z * sy_, x * sy_ + z * cy_          # yaw around the vertical
            y, z = y * cp - z * sp, y * sp + z * cp              # tilt towards the camera
            return x, y, z

        def project(point):
            x, y, z = rotate(point)
            depth = dist - z
            return (w / 2 + focal * x / depth, h * 0.55 - focal * y / depth), depth

        # Soft shadow under the instrument.
        shadow = Image.new("L", size, 0)
        corners = [project((x, 0, z))[0] for x, z in ((-WIDTH / 2, -DEPTH / 2), (WIDTH / 2, -DEPTH / 2),
                                                     (WIDTH / 2, DEPTH / 2), (-WIDTH / 2, DEPTH / 2))]
        ImageDraw.Draw(shadow).polygon([(x, y + 12) for x, y in corners], fill=150)
        out.paste((0, 0, 0), (0, 0) + size, shadow.filter(ImageFilter.GaussianBlur(18)))
        drawn = []
        for name, corners3d in self.faces():
            rotated = [rotate(c) for c in corners3d]
            a, b, c = (np.array(rotated[i]) for i in (0, 1, 3))
            normal = np.cross(c - a, b - a)
            centre = np.mean(rotated, axis=0)
            to_camera = np.array((0.0, 0.0, dist)) - centre
            if np.dot(normal, to_camera) <= 0:
                continue                              # facing away
            points = [project(c) for c in corners3d]
            depth = float(np.mean([d for _, d in points]))
            light = abs(float(np.dot(normal / np.linalg.norm(normal), (0.3, 0.8, 0.5))))
            drawn.append((depth, name, [p for p, _ in points], light))
        self.back_quad = self.back_coeffs = None
        for depth, name, quad, light in sorted(drawn, reverse=True):
            texture = self.textures[name]
            tw, th = texture.size
            coeffs = _perspective(((0, 0), (tw, 0), (tw, th), (0, th)), quad)
            warped = texture.transform(size, Image.Transform.PERSPECTIVE, tuple(coeffs),
                                       Image.Resampling.BILINEAR)
            if light < 0.95:                          # faces away from the light are darker
                warped = Image.eval(warped, lambda v, k=0.45 + 0.55 * light: int(v * k))
            mask = Image.new("L", size, 0)
            ImageDraw.Draw(mask).polygon(quad, fill=255)
            out.paste(warped, (0, 0), mask)
            if name == "back":
                self.back_quad, self.back_coeffs = quad, coeffs
        return out

    def connector_at(self, x, y):
        """Rear connector under a screen point, if the rear panel is in view."""
        if self.back_coeffs is None:
            return None
        a, b, c, d, e, f, g, h = self.back_coeffs
        mask = Image.new("L", (1, 1))
        quad = self.back_quad
        # Inside the projected rear panel?
        if not _inside(quad, x, y):
            return None
        u = (a * x + b * y + c) / (g * x + h * y + 1)
        v = (d * x + e * y + f) / (g * x + h * y + 1)
        best = min(CONNECTORS, key=lambda item: abs(item[3] - u))
        return best if abs(best[3] - u) < 45 and 20 < v < 130 else None


def _inside(quad, x, y):
    """Point in a convex quad (any winding)."""
    signs = []
    for (x1, y1), (x2, y2) in zip(quad, quad[1:] + quad[:1]):
        signs.append((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1) > 0)
    return all(signs) or not any(signs)


def open_view(app):
    """Window with the rotating instrument; the main panel keeps playing."""
    import tkinter as tk
    from PIL import ImageTk
    if getattr(app, "view3d_window", None) is not None:
        try:
            app.view3d_window.lift()
            return
        except Exception:
            pass
    renderer = getattr(app, "mockup", None)
    if renderer is None or renderer.original is None:
        return
    from PIL import Image as _Image
    with _Image.open(renderer.path) as source:
        art = source.convert("RGB")
    snapshot = panel_snapshot(renderer, app.synth)
    scale = 1200 / snapshot.width
    base_top = snapshot.resize((1200, round(snapshot.height * scale)), Image.Resampling.LANCZOS)
    model = Instrument3D(base_top, art)
    window = tk.Toplevel(app.root)
    window.title("VENUS-8 — Vista 3D")
    window.geometry("1100x700")
    window.configure(bg="#0e0f12")
    app.view3d_window = window
    state = {"yaw": 0.0, "pitch": 35.0, "zoom": 1.0, "drag": None, "photo": None, "midi": None,
             "pending": False}
    bar = tk.Frame(window, bg="#0e0f12")
    bar.pack(fill="x")
    canvas = tk.Canvas(window, bg="#0e0f12", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    tip = tk.StringVar(value="Arraste para girar · roda do mouse para aproximar · passe o mouse nas conexões de trás")
    tk.Label(window, textvariable=tip, bg="#0e0f12", fg="#e8e2d8", anchor="w").pack(fill="x", padx=10, pady=6)

    def draw():
        state["pending"] = False
        size = (max(200, canvas.winfo_width()), max(150, canvas.winfo_height()))
        image = model.render(size, state["yaw"], state["pitch"], state["zoom"])
        state["photo"] = ImageTk.PhotoImage(image, master=window)
        canvas.delete("all")
        canvas.create_image(0, 0, image=state["photo"], anchor="nw")

    def redraw(*_):
        if not state["pending"]:
            state["pending"] = True
            window.after(15, draw)

    def view(name):
        state["yaw"], state["pitch"] = VIEWS[name]
        redraw()

    for name in VIEWS:
        tk.Button(bar, text=name, command=lambda n=name: view(n)).pack(side="left", padx=4, pady=6)

    def press(event):
        state["drag"] = (event.x, event.y, state["yaw"], state["pitch"])

    def move(event):
        if state["drag"] is None:
            return
        x0, y0, yaw, pitch = state["drag"]
        state["yaw"] = (yaw + (event.x - x0) * 0.4) % 360
        state["pitch"] = max(-5.0, min(85.0, pitch + (event.y - y0) * 0.3))
        redraw()

    def release(_):
        state["drag"] = None

    def wheel(event):
        state["zoom"] = max(0.6, min(3.0, state["zoom"] * (1.1 if event.delta > 0 else 0.9)))
        redraw()

    def hover(event):
        found = model.connector_at(event.x, event.y)
        if found:
            tip.set(f"{found[1]}: {found[4]}")

    def live():
        """Rear LEDs follow MIDI activity and the sustain pedal."""
        if not window.winfo_exists():
            return
        midi = time.time() - getattr(app, "midi_activity", 0.0) < 0.2
        sustain = bool(getattr(app.synth, "sustain", False))
        pressed = frozenset(app.midi_held | {app.current_mouse_note} - {None})
        key = (midi, sustain, pressed)
        if key != state["midi"]:
            if state["midi"] is None or key[:2] != state["midi"][:2]:
                from . import __version__
                model.textures["back"] = rear_panel({"midi": midi, "sustain": sustain,
                                                     "version": __version__})
            model.textures["top"] = press_keys(base_top, pressed, scale)
            state["midi"] = key
            redraw()
        window.after(80, live)

    def close():
        app.view3d_window = None
        window.destroy()

    canvas.bind("<Configure>", redraw)
    canvas.bind("<Button-1>", press)
    canvas.bind("<B1-Motion>", move)
    canvas.bind("<ButtonRelease-1>", release)
    canvas.bind("<MouseWheel>", wheel)
    canvas.bind("<Motion>", hover)
    window.protocol("WM_DELETE_WINDOW", close)
    live()
