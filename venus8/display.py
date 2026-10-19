"""Live central display: oscilloscope, patch name, status table and prompts.

The display's painted contents are fictional, so components.clear_display
blanks them and this module draws real state as persistent canvas items.
Items are created once per window size and then only reconfigured.
"""
import numpy as np

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
    "osc1_fine": "Fine OSC1", "osc2_fine": "Fine OSC2", "osc3_fine": "Fine OSC3",
}


def format_value(param, value):
    """Readout in the control's own unit."""
    if param.endswith("_octave"):
        return f"{round((value - 0.5) * 4):+d}"
    if param.endswith("_fine"):
        return f"{round((value - 0.5) * 100):+d} cents"
    if param.endswith("_tune"):
        return f"{(value - 0.5) * 24:+.1f} st"
    return f"{round(value * 100)}%"
INK = "#e9e2d6"
DIM = "#8f9bb0"
AMBER = "#ffb05e"
ALERT = "#e0574a"


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
        self.items = {}
        self.shown = {}

    # -- construction ------------------------------------------------------
    def font(self, size, bold=False):
        return ("Segoe UI", max(6, round(size * self.app.scale)), "bold" if bold else "normal")

    def text(self, key, x, y, size, color, anchor="center", bold=False):
        sx, sy = self.app.bounds(x, y, x, y)[:2]
        self.items[key] = self.app.canvas.create_text(
            sx, sy, text="", fill=color, font=self.font(size, bold), anchor=anchor)

    def build(self):
        app, canvas = self.app, self.app.canvas
        self.shown = {}
        x1, y1, x2, y2 = SCOPE_AREA
        mid = (y1 + y2) / 2
        canvas.create_line(*app.bounds(x1, mid, x2, mid), fill="#2b3442",
                           width=max(1, app.scale))
        flat = [c for x in np.linspace(x1, x2, SCOPE_POINTS) for c in app.bounds(x, mid, x, mid)[:2]]
        self.items["scope_glow"] = canvas.create_line(*flat, fill="#7a3d10",
                                                      width=max(2, 5 * app.scale), smooth=True)
        self.items["scope"] = canvas.create_line(*flat, fill=AMBER,
                                                 width=max(1, 1.6 * app.scale), smooth=True)

        nx1, ny1, nx2, ny2 = DISPLAY_NAME_BOX
        cx = (nx1 + nx2) / 2
        self.text("name", cx, ny1 + 24, 17, INK, bold=True)
        self.text("description", cx, ny1 + 51, 10, DIM)
        self.text("modified", nx2 - 8, ny1 + 9, 8, AMBER, anchor="e", bold=True)
        self.text("prev", nx1 + 15, ny1 + 37, 15, INK)
        self.text("next", nx2 - 15, ny1 + 37, 15, INK)
        canvas.itemconfigure(self.items["prev"], text="◀")
        canvas.itemconfigure(self.items["next"], text="▶")

        tx1, ty1, tx2, ty2 = DISPLAY_TABLE
        step = (ty2 - ty1) / DISPLAY_ROWS
        for row in range(DISPLAY_ROWS):
            y = ty1 + step * (row + 0.5)
            self.text(f"label{row}", tx1 + 8, y, 8.5, DIM, anchor="w", bold=True)
            self.text(f"value{row}", tx1 + 82, y, 9, INK, anchor="w")

        # Unsaved-changes prompt, hidden until needed.
        prompt = [canvas.create_rectangle(*app.bounds(*PROMPT_BOX), fill="#090c12",
                                          outline=AMBER, width=max(1, 1.5 * app.scale))]
        px1, py1, px2, py2 = PROMPT_BOX
        pcx = (px1 + px2) / 2
        self.text("prompt_title", pcx, py1 + 28, 15, AMBER, bold=True)
        self.text("prompt_body", pcx, py1 + 62, 10.5, INK)
        self.text("prompt_target", pcx, py1 + 88, 10, DIM)
        prompt += [self.items[k] for k in ("prompt_title", "prompt_body", "prompt_target")]
        for key, box in PROMPT_BUTTONS.items():
            primary = key == "prompt_save"
            prompt.append(canvas.create_rectangle(
                *app.bounds(*box), fill="#3a2410" if primary else "#151b25",
                outline=AMBER if primary else "#4a5566", width=max(1, app.scale)))
            bx1, by1, bx2, by2 = box
            sx, sy = app.bounds((bx1 + bx2) / 2, (by1 + by2) / 2, 0, 0)[:2]
            prompt.append(canvas.create_text(sx, sy, text=PROMPT_LABELS[key], fill=INK,
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
        midi = short(getattr(port, "name", ""), 20) if port is not None else "desconectado"
        audio = getattr(app, "audio_name", "") or "—"
        rate = app.synth.sample_rate / 1000
        last = getattr(app, "last_param", None)
        tweak = (f"{PARAM_LABELS.get(last, last)} {format_value(last, app.synth.get_param(last))}"
                 if last else "—")
        load = getattr(app, "dsp_load", 0.0) * 100
        return [
            ("CATEGORIA", short(app.patch_category, 20), INK),
            ("BANCO", app.patch_bank, INK),
            ("VOZES", f"{len(app.synth.voices)} / {app.synth.max_voices}", INK),
            ("MIDI", midi, INK if port is not None else ALERT),
            ("ÁUDIO", short(f"{audio} · {rate:.1f} kHz", 20), INK),
            ("CARGA DSP", f"{load:.0f}%", ALERT if load > 70 else INK),
            ("AJUSTE", short(tweak, 20), AMBER if last else DIM),
        ]

    def update(self):
        app = self.app
        dirty = getattr(app, "patch_dirty", False)
        self.set("name", text=short(app.patch_name, 24) + (" *" if dirty else ""),
                 fill=AMBER if dirty else INK)
        self.set("description", text=short(app.patch_description, 38))
        self.set("modified", text="MODIFICADO" if dirty else "")
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
