"""Live central display: oscilloscope, patch name, status table and prompts.

The display's painted contents are fictional, so components.clear_display
blanks them and this module draws real state as persistent canvas items.
Items are created once per window size and then only reconfigured.
"""
import numpy as np
from PIL import Image, ImageDraw

from .components import DISPLAY_NAME_BOX, DISPLAY_ROWS, DISPLAY_SCREEN, DISPLAY_TABLE

# Clickable display areas (artwork coordinates).
DISPLAY_BUTTONS = {
    "display_prev": (550, 480, 578, 522),
    "display_next": (830, 480, 858, 522),
    "init": (545, 546, 620, 571),
}
PROMPT_BOX = (548, 381, 1067, 541)
PROMPT_BUTTONS = {
    "prompt_save": (566, 500, 718, 530),
    "prompt_discard": (730, 500, 882, 530),
    "prompt_keep": (894, 500, 1050, 530),
}
PROMPT_LABELS = {"prompt_save": "SALVAR", "prompt_discard": "SAIR SEM SALVAR",
                 "prompt_keep": "MANTER COMO ESTÁ"}
SCOPE_AREA = (DISPLAY_SCREEN[0] + 8, DISPLAY_SCREEN[1] + 8,
              DISPLAY_SCREEN[2] - 8, DISPLAY_NAME_BOX[1] - 6)
SCOPE_POINTS = 160

PARAM_LABELS = {
    "osc1_level": "Nível OSC1", "osc2_level": "Nível OSC2", "osc3_level": "Nível OSC3",
    "osc1_tune": "Tune OSC1", "osc2_tune": "Tune OSC2", "osc3_tune": "Tune OSC3",
    "osc1_wave": "Onda OSC1", "osc2_wave": "Onda OSC2", "osc3_wave": "Onda OSC3",
    "sub_level": "Sub", "noise_level": "Ruído", "cutoff": "Cutoff",
    "resonance": "Resonance", "drive": "Drive", "attack": "Attack", "decay": "Decay",
    "sustain": "Sustain", "release": "Release", "lfo_rate": "LFO Rate",
    "lfo_depth": "LFO Depth", "delay_mix": "Delay Mix", "delay_time": "Delay Time",
    "delay_feedback": "Delay Feedback", "volume": "Volume", "pitch_bend": "Pitch Bend",
    "modwheel": "Mod Wheel",
    "osc1_octave": "Oitava OSC1", "osc2_octave": "Oitava OSC2", "osc3_octave": "Oitava OSC3",
    "lfo2_rate": "Vibrato Rate", "lfo2_depth": "Vibrato",
    **{f"drawbar{i + 1}": f"Drawbar {f}" for i, f in enumerate(
        ("16'", "5⅓'", "8'", "4'", "2⅔'", "2'", "1⅗'", "1⅓'", "1'"))},
    "osc1_fine": "Fine OSC1", "osc2_fine": "Fine OSC2", "osc3_fine": "Fine OSC3",
    "organ_perc": "Percussão", "organ_perc_third": "Perc 3ª harm.",
    "organ_perc_fast": "Perc rápida", "organ_click": "Key click",
    "organ_vibrato": "Vibrato órgão", "organ_chorus": "Chorus órgão",
    "leslie": "Leslie", "leslie_fast": "Leslie rápido", "organ_drive": "Drive órgão",
    "osc1_fm": "FM OSC1", "osc2_fm": "FM OSC2", "osc3_fm": "FM OSC3 (feedback)",
    "osc1_fm_on": "FM OSC1", "osc2_fm_on": "FM OSC2", "osc3_fm_on": "FM OSC3",
    "mod_attack": "Mod Attack", "mod_decay": "Mod Decay", "mod_sustain": "Mod Sustain",
    "mod_release": "Mod Release",
    "chorus_on": "Chorus/Flanger", "chorus_type": "Tipo de chorus", "chorus_depth": "Chorus Depth",
    "chorus_rate": "Chorus Rate", "phaser_on": "Phaser", "phaser_depth": "Phaser Depth",
    "phaser_rate": "Phaser Rate", "tube_drive": "Válvula (drive)",
    "ep_model": "Modelo de piano",
    "filter_type": "Tipo de filtro", "key_track": "Key Track", "filter_env_on": "Filter Env",
    "fenv_attack": "FEnv Attack", "fenv_decay": "FEnv Decay", "fenv_sustain": "FEnv Sustain",
    "fenv_release": "FEnv Release", "lfo_wave": "Onda LFO 1", "lfo2_wave": "Onda LFO 2",
    "lfo_fade": "Fade LFO 1", "lfo2_fade": "Fade LFO 2", "lfo_sync": "Sync LFO 1",
    "lfo2_sync": "Sync LFO 2", "reverb_on": "Reverb", "reverb_size": "Reverb Size",
    "reverb_damp": "Reverb Damp", "reverb_mix": "Reverb Mix", "width": "Width",
    "osc1_sync": "Sync OSC1", "osc2_sync": "Sync OSC2", "osc1_ring": "Ring OSC1",
    "osc3_noise": "Noise OSC3", "polymod_env": "Poly-Mod Filt Env", "polymod_osc": "Poly-Mod Osc B",
    "polymod_freq": "Poly-Mod Freq A", "polymod_pw": "Poly-Mod PW A",
    "polymod_filter": "Poly-Mod Filter", "moog_mix": "Mod Mix", "moog_osc": "Osc Mod",
    "moog_filter": "Filter Mod", "osc3_lo": "OSC3 LO", "vintage": "Vintage", "hpf": "HPF",
    "voice_mode": "Modo de voz", "unison_detune": "Detune (unison)", "glide_time": "Glide",
    "arp_on": "Arpeggiator", "arp_mode": "Modo do arpejo", "arp_rate": "Arp Rate",
    "arp_gate": "Arp Gate", "arp_oct": "Arp Oitavas", "arp_hold": "Arp Hold",
    **{f"osc{i}_pw": f"PW OSC{i}" for i in (1, 2, 3)},
    **{f"osc{i}_pwm": f"PWM OSC{i}" for i in (1, 2, 3)},
}
# Classic instrument each engine is modelled on, shown in the display.
ANALOG_STYLE = {"Bass": "Minimoog Model D", "Lead": "Minimoog Model D", "Pad": "Prophet-5",
                "Brass": "Oberheim OB-Xa", "Strings": "Roland Jupiter-8", "Keys": "Prophet-5",
                "Pluck": "Roland Jupiter-8", "Bells": "Prophet-5", "FX": "ARP 2600",
                "Ambient": "Roland Jupiter-8"}


def instrument_style(params, category=""):
    """Which instrument(s) the current sound simulates, e.g. "Hammond B-3 + Leslie"."""
    get = lambda name: params.get(name, 0.0)
    layers = []
    if any(get(f"osc{i}_level") > 0.0001 for i in (1, 2, 3)) or get("sub_level") > 0.0001:
        if any(get(f"osc{i}_fm_on") >= 0.5 for i in (1, 2, 3)):
            layers.append("Yamaha DX7")
        elif get("chorus_on") >= 0.5 and 1 <= round(get("chorus_type") * 4) <= 3:
            layers.append("Roland Juno-60")
        elif (get("polymod_env") > 0.001 or get("polymod_osc") > 0.001) and any(
                get(name) >= 0.5 for name in ("polymod_freq", "polymod_pw", "polymod_filter")):
            layers.append("Prophet-5")
        elif get("moog_osc") >= 0.5 or get("moog_filter") >= 0.5 or get("osc3_lo") >= 0.5:
            layers.append("Minimoog Model D")
        else:
            layers.append(ANALOG_STYLE.get(category, "Minimoog Model D"))
    if any(get(f"drawbar{i}") > 0 for i in range(1, 10)) or get("organ_perc") >= 0.5:
        layers.append("Hammond B-3" + (" + Leslie" if get("leslie") >= 0.5 else ""))
    if get("ep_level") > 0.0001:
        layers.append("Yamaha CP-70" if get("ep_model") >= 0.5 else "Fender Rhodes")
    return " + ".join(layers) or "—"
SWITCH_PARAMS = {"osc1_sync", "osc2_sync", "osc1_ring", "osc3_noise", "polymod_freq",
                 "polymod_pw", "polymod_filter", "moog_osc", "moog_filter", "osc3_lo", "arp_on", "arp_hold", "chorus_on", "phaser_on", "reverb_on", "filter_env_on", "lfo_sync",
                 "lfo2_sync", "organ_perc", "organ_perc_third", "organ_perc_fast", "organ_click",
                 "organ_vibrato", "organ_chorus", "leslie", "leslie_fast",
                 "osc1_fm_on", "osc2_fm_on", "osc3_fm_on"}


def format_value(param, value):
    """Readout in the control's own unit."""
    if param.startswith("drawbar"):
        return str(round(value * 8))
    if param in SWITCH_PARAMS:
        return "ON" if value >= 0.5 else "OFF"
    if param == "filter_type":
        from .synth import FILTER_TYPES
        return FILTER_TYPES[round(value * 3)]
    if param == "chorus_type":
        from .synth import CHORUS_TYPES
        return CHORUS_TYPES[round(value * 4)].title()
    if param == "arp_mode":
        from .synth import ARP_MODES
        return ARP_MODES[round(value * 4)]
    if param == "arp_rate":
        return f"{round(40 + 200 * value)} BPM"
    if param == "arp_oct":
        return f"{1 + round(value * 3)} oit."
    if param == "voice_mode":
        from .synth import VOICE_MODES
        return VOICE_MODES[round(value * 3)]
    if param in ("lfo_wave", "lfo2_wave"):
        from .synth import LFO_WAVES
        return LFO_WAVES[round(value * 3)]
    if param.endswith("_octave"):
        return f"{round((value - 0.5) * 4):+d}"
    if param.endswith("_fine"):
        return f"{round((value - 0.5) * 100):+d} cents"
    if param.endswith("_tune"):
        return f"{(value - 0.5) * 24:+.1f} st"
    return f"{round(value * 100)}%"

# Display looks: the original colours, or a monochrome LCD tint.
LCD_AREA = (DISPLAY_SCREEN[0], DISPLAY_TABLE[1], DISPLAY_TABLE[2], DISPLAY_TABLE[3])
DISPLAY_MODES = {"color": "Colorido", "amber": "Âmbar", "green": "Verde", "blue": "Azul"}
PALETTES = {
    "color": {"ink": "#e9e2d6", "dim": "#8f9bb0", "accent": "#ffb05e", "alert": "#e0574a",
              "glow": "#7a3d10", "grid": "#2b3442", "panel": "#090c12", "button": "#151b25",
              "edge": "#4a5566", "primary": "#3a2410", "font": "Segoe UI", "tint": None},
    "amber": {"ink": "#ffb347", "dim": "#a8661f", "accent": "#ffe0a8", "alert": "#ff6a2a",
              "glow": "#5a2c04", "grid": "#3a2006", "panel": "#140a02", "button": "#211104",
              "edge": "#7a4a14", "primary": "#4a2606", "font": "Consolas", "tint": (255, 170, 60)},
    "green": {"ink": "#7dff8a", "dim": "#3f9a4a", "accent": "#d8ffc8", "alert": "#f0ff60",
              "glow": "#0e4a16", "grid": "#123a18", "panel": "#03120a", "button": "#071c0e",
              "edge": "#2c6a36", "primary": "#0e3a18", "font": "Consolas", "tint": (110, 255, 130)},
    "blue": {"ink": "#7fd4ff", "dim": "#3f7fa8", "accent": "#e0f6ff", "alert": "#ff8a7a",
             "glow": "#0c3550", "grid": "#12304a", "panel": "#020c16", "button": "#061828",
             "edge": "#2a5a80", "primary": "#0a2e4a", "font": "Consolas", "tint": (110, 200, 255)},
}


def lcd_screen(image, mode):
    """LCD look for the display area: dot-matrix grid, mono tint when asked."""
    tint = PALETTES[mode]["tint"]
    if tint:
        lum = image.convert("L").point(lambda v: min(255, round(v * 1.6)))
        image = Image.merge("RGB", [lum.point(lambda v, c=c: round(c * v / 255) + 3) for c in tint])
    else:
        image = image.convert("RGB")
    # Pixel matrix: a darker line every third pixel in both directions.
    grid = Image.new("L", image.size, 255)
    draw = ImageDraw.Draw(grid)
    for x in range(2, image.width, 3):
        draw.line((x, 0, x, image.height), fill=170)
    for y in range(2, image.height, 3):
        draw.line((0, y, image.width, y), fill=170)
    dark = Image.new("RGB", image.size, (0, 0, 0))
    return Image.composite(image, dark, grid.point(lambda v: v))


def scope_trace(samples, points=SCOPE_POINTS):
    """Stable oscilloscope trace: start at a rising zero crossing, resample."""
    data = np.asarray(samples, dtype=np.float64)
    if data.size < 8:
        return np.zeros(points)
    half = data[: data.size // 2]
    rising = np.flatnonzero((half[:-1] < 0) & (half[1:] >= 0))
    start = int(rising[0]) + 1 if rising.size else 0
    window = data[start:start + data.size // 2]
    positions = np.linspace(0, window.size - 1, points)
    return np.interp(positions, np.arange(window.size), window)


def short(text, length):
    text = str(text)
    return text if len(text) <= length else text[:length - 1] + "…"


class LiveDisplay:
    def __init__(self, app):
        self.app = app
        mode = getattr(app, "settings", {}).get("display_mode", "color")
        self.mode = mode if mode in PALETTES else "color"
        self.pal = PALETTES[self.mode]
        self.items = {}
        self.shown = {}

    # -- construction ------------------------------------------------------
    def font(self, size, bold=False):
        return (self.pal["font"], max(6, round(size * self.app.scale)), "bold" if bold else "normal")

    def text(self, key, x, y, size, color, anchor="center", bold=False):
        sx, sy = self.app.bounds(x, y, x, y)[:2]
        self.items[key] = self.app.canvas.create_text(
            sx, sy, text="", fill=color, font=self.font(size, bold), anchor=anchor)

    def build(self, chassis=None):
        app, canvas = self.app, self.app.canvas
        self.shown = {}
        if chassis is not None:
            # LCD glass over the display, cut from the already scaled chassis.
            x1, y1, x2, y2 = (round(v * app.scale) for v in LCD_AREA)
            from PIL import ImageTk
            self.lcd_photo = ImageTk.PhotoImage(lcd_screen(chassis.crop((x1, y1, x2, y2)), self.mode),
                                                master=app.root)
            ox, oy = app.offset
            canvas.create_image(ox + x1, oy + y1, image=self.lcd_photo, anchor="nw")
        x1, y1, x2, y2 = SCOPE_AREA
        mid = (y1 + y2) / 2
        canvas.create_line(*app.bounds(x1, mid, x2, mid), fill=self.pal["grid"],
                           width=max(1, app.scale))
        flat = [c for x in np.linspace(x1, x2, SCOPE_POINTS) for c in app.bounds(x, mid, x, mid)[:2]]
        self.items["scope_glow"] = canvas.create_line(*flat, fill=self.pal["glow"],
                                                      width=max(2, 5 * app.scale), smooth=True)
        self.items["scope"] = canvas.create_line(*flat, fill=self.pal["accent"],
                                                 width=max(1, 1.6 * app.scale), smooth=True)

        sx1, sy1 = SCOPE_AREA[:2]
        self.text("style_label", sx1 + 2, sy1 + 7, 8, self.pal["dim"], anchor="w", bold=True)
        canvas.itemconfigure(self.items["style_label"], text="ESTILO")
        self.text("style", sx1 + 46, sy1 + 7, 9, self.pal["accent"], anchor="w", bold=True)
        nx1, ny1, nx2, ny2 = DISPLAY_NAME_BOX
        cx = (nx1 + nx2) / 2
        self.text("name", cx, ny1 + 24, 17, self.pal["ink"], bold=True)
        self.text("description", cx, ny1 + 51, 10, self.pal["dim"])
        self.text("modified", nx2 - 8, ny1 + 9, 8, self.pal["accent"], anchor="e", bold=True)
        self.text("prev", nx1 + 15, ny1 + 37, 15, self.pal["ink"])
        self.text("next", nx2 - 15, ny1 + 37, 15, self.pal["ink"])
        canvas.itemconfigure(self.items["prev"], text="◀")
        canvas.itemconfigure(self.items["next"], text="▶")

        tx1, ty1, tx2, ty2 = DISPLAY_TABLE
        step = (ty2 - ty1) / DISPLAY_ROWS
        for row in range(DISPLAY_ROWS):
            y = ty1 + step * (row + 0.5)
            self.text(f"label{row}", tx1 + 8, y, 8.5, self.pal["dim"], anchor="w", bold=True)
            self.text(f"value{row}", tx1 + 82, y, 9, self.pal["ink"], anchor="w")

        # Unsaved-changes prompt, hidden until needed.
        prompt = [canvas.create_rectangle(*app.bounds(*PROMPT_BOX), fill=self.pal["panel"],
                                          outline=self.pal["accent"], width=max(1, 1.5 * app.scale))]
        px1, py1, px2, py2 = PROMPT_BOX
        pcx = (px1 + px2) / 2
        self.text("prompt_title", pcx, py1 + 28, 15, self.pal["accent"], bold=True)
        self.text("prompt_body", pcx, py1 + 62, 10.5, self.pal["ink"])
        self.text("prompt_target", pcx, py1 + 88, 10, self.pal["dim"])
        prompt += [self.items[k] for k in ("prompt_title", "prompt_body", "prompt_target")]
        for key, box in PROMPT_BUTTONS.items():
            primary = key == "prompt_save"
            prompt.append(canvas.create_rectangle(
                *app.bounds(*box), fill=self.pal["primary"] if primary else self.pal["button"],
                outline=self.pal["accent"] if primary else self.pal["edge"], width=max(1, app.scale)))
            bx1, by1, bx2, by2 = box
            sx, sy = app.bounds((bx1 + bx2) / 2, (by1 + by2) / 2, 0, 0)[:2]
            prompt.append(canvas.create_text(sx, sy, text=PROMPT_LABELS[key], fill=self.pal["ink"],
                                             font=self.font(9.5, True)))
        self.prompt_items = prompt
        for item in prompt:
            canvas.itemconfigure(item, state="hidden")
        self.prompt_visible = False
        app.buttons.update(DISPLAY_BUTTONS)
        app.buttons.update(PROMPT_BUTTONS)

    # -- updates -----------------------------------------------------------
    def set(self, key, **options):
        if self.shown.get(key) != options:
            self.app.canvas.itemconfigure(self.items[key], **options)
            self.shown[key] = options

    def rows(self):
        app = self.app
        port = getattr(app, "port", None)
        if port is not None:
            midi = short(getattr(port, "name", ""), 20)
        elif getattr(app, "other_instances", 0):
            midi = "outro Venus-8 aberto"
        else:
            midi = getattr(app, "midi_error", "") or "desconectado"
        audio = getattr(app, "audio_name", "") or "—"
        rate = app.synth.sample_rate / 1000
        last = getattr(app, "last_param", None)
        tweak = (f"{PARAM_LABELS.get(last, last)} {format_value(last, app.synth.get_param(last))}"
                 if last else "—")
        load = getattr(app, "dsp_load", 0.0) * 100
        return [
            ("CATEGORIA", short(app.patch_category, 20), self.pal["ink"]),
            ("BANCO", app.patch_bank, self.pal["ink"]),
            ("VOZES", f"{len(app.synth.voices)} / {app.synth.max_voices}", self.pal["ink"]),
            ("MIDI", midi, self.pal["ink"] if port is not None else self.pal["alert"]),
            ("ÁUDIO", short(self.audio_text(audio, rate), 20), self.pal["ink"]),
            ("CARGA DSP", f"{load:.0f}%", self.pal["alert"] if load > 70 else self.pal["ink"]),
            self.adjust_row(tweak, last),
        ]

    def audio_text(self, audio, rate):
        """Output latency first: it is what the player feels."""
        latency = getattr(self.app, "audio_latency", 0.0) * 1000
        if latency > 0:
            return f"{latency:.0f} ms · {rate:.1f} kHz · {audio}"
        return f"{audio} · {rate:.1f} kHz"

    def adjust_row(self, tweak, last):
        """Last tweak, or the MIDI Learn state while assigning a controller."""
        learning = getattr(self.app, "learning", None)
        if learning:
            return ("MIDI LEARN", short("mova: " + PARAM_LABELS.get(learning, learning), 20),
                    self.pal["alert"])
        note = getattr(self.app, "midi_note", None)
        if note:
            return ("MIDI", short(note, 20), self.pal["accent"])
        return ("AJUSTE", short(tweak, 20), self.pal["accent"] if last else self.pal["dim"])

    def update(self):
        app = self.app
        dirty = getattr(app, "patch_dirty", False)
        self.set("name", text=short(app.patch_name, 24) + (" *" if dirty else ""),
                 fill=self.pal["accent"] if dirty else self.pal["ink"])
        self.set("description", text=short(app.patch_description, 38))
        self.set("modified", text="● EDITADO" if dirty else "")
        self.set("style", text=short(instrument_style(app.synth.params, app.patch_category), 34))
        for row, (label, value, color) in enumerate(self.rows()):
            self.set(f"label{row}", text=label)
            self.set(f"value{row}", text=value, fill=color)
        pending = getattr(app, "pending", None)
        if bool(pending) != self.prompt_visible:
            for item in self.prompt_items:
                app.canvas.itemconfigure(item, state="normal" if pending else "hidden")
            self.prompt_visible = bool(pending)
        if pending:
            self.set("prompt_title", text="TIMBRE MODIFICADO")
            self.set("prompt_body", text=f"“{short(app.patch_name, 28)}” tem alterações não salvas.")
            self.set("prompt_target", text=pending.get("message", ""))
            for item in self.prompt_items:
                app.canvas.tag_raise(item)

    def tick(self):
        """Fast refresh: oscilloscope trace and the live table rows."""
        app = self.app
        x1, y1, x2, y2 = SCOPE_AREA
        mid, half = (y1 + y2) / 2, (y2 - y1) / 2 * 0.92
        trace = np.clip(scope_trace(getattr(app, "scope_buffer", ())) * 2.2, -1, 1)
        xs = np.linspace(x1, x2, trace.size)
        ox, oy = app.offset
        coords = np.empty(trace.size * 2)
        coords[0::2] = ox + xs * app.scale
        coords[1::2] = oy + (mid - trace * half) * app.scale
        coords = coords.tolist()
        app.canvas.coords(self.items["scope_glow"], *coords)
        app.canvas.coords(self.items["scope"], *coords)
        for row, (label, value, color) in enumerate(self.rows()):
            self.set(f"value{row}", text=value, fill=color)
