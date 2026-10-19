"""Venus-8 panel: the approved artwork as chassis, with real, independent controls.

Every key, knob and fader cap is its own canvas object (see components.py).
The canvas is rebuilt only when the window is resized; afterwards each control
updates itself in place when its value or state changes.
"""
from pathlib import Path
import math
import time
import sys

from PIL import Image, ImageTk

from .components import (DETENT_KNOBS, DRAWBAR_CAP, DRAWBAR_HEADER, DRAWBAR_STEP,
                         DRAWBAR_TOP, DRAWBAR_WIDTH, DRAWBAR_X, KNOB_GEOMETRY,
                         ORGAN_LABEL_X, ORGAN_SWITCHES, render_switch, FM_BUTTONS,
                         FX_LEDS, CHORUS_TITLE, CHORUS_TITLE_BOX, TUBE_WINDOW, render_tube,
                         drawbar_length, render_drawbar, METER_ROWS, PAINTED_CAPS, CAP_REACH,
                         STATUS_BOX, WAVE_LEFT, KeySprites, cap_half_width,
                         clean_artwork, keyboard_layout, meter_box, panel_sprites,
                         render_knob, wave_box)
from .display import LiveDisplay, format_value

ART_W, ART_H = 1600, 959

# Coordinates are in the exact original 1600 x 959 PNG/JPG artwork.
KNOBS = dict(KNOB_GEOMETRY)
# Faders: (slot x, top, bottom) travel of the cap's glowing line.
SLIDERS = {
    "osc1_level": (722, 171, 276),
    "osc2_level": (765, 171, 276),
    "osc3_level": (809, 171, 276),
    "sub_level": (853, 171, 276),
    "noise_level": (897, 171, 276),
    "attack": (1156, 161, 269),
    "decay": (1186, 161, 269), "sustain": (1215, 161, 269),
    "release": (1245, 161, 269),
    "mod_attack": (1442, 161, 269), "mod_decay": (1472, 161, 269),
    "mod_sustain": (1501, 161, 269), "mod_release": (1532, 161, 269),
    "pitch_bend": (76, 846, 927),
    "modwheel": (166, 846, 927),
}
UPDATE_BUTTON = (1390, 46, 1429, 62)
BUTTONS = {
    "save": (893, 26, 938, 61),
    "browse": (822, 26, 881, 61),
    "bank": (950, 27, 1069, 64),
    "category": (1071, 27, 1205, 64),
    "prev_patch": (528, 22, 559, 66),
    "next_patch": (778, 22, 813, 66),
    "settings": (592, 695, 728, 738),
    "check_update": (1390, 46, 1429, 62),
}
# Four selectable waves on each of the 3 oscillators (keeps waveform order).
for osc, left, step in ((1, 61, 45), (2, 277, 45), (3, 489, 45)):
    for idx in range(4):
        x = left + idx * step
        BUTTONS[f"wave{osc}_{idx}"] = (x, 114, x+42, 154)


def reference_image_path():
    candidates = []
    import os
    user_dir = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")) / "Venus-8" / "assets"
    candidates.extend((user_dir / "venus-8-mockup.png", user_dir / "venus-8-mockup.jpg"))
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    candidates.extend((root / "docs" / "venus-8-mockup.png",
                       root / "docs" / "venus-8-mockup.jpg"))
    # Never enlarge a tiny preview: it looks blurry and degrades the whole UI.
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            with Image.open(candidate) as artwork:
                if artwork.width >= 1500 and artwork.height >= 850 and (1.55 <= artwork.width/artwork.height <= 1.80):
                    return candidate
        except (OSError, ValueError):
            continue
    return None


class MockupRenderer:
    def __init__(self, app):
        self.app = app
        self.path = reference_image_path()
        self.original = None
        self.original_size = None
        self.built_size = None
        self.photos = {}
        self.knob_frames = {}
        self.key_items = {}
        self.knob_items = {}
        self.cap_items = {}
        self.wheel_items = {}
        if self.path:
            try:
                with Image.open(self.path) as source:
                    self.original_size = source.size
                    art = source.convert("RGB")
                self.original, self.caps = clean_artwork(art)
                self.key_sprites = KeySprites(art)
                self.sprites = panel_sprites(art, self.original)
                self.meter_level = 0.0
            except Exception:
                self.original = None

    @property
    def ready(self):
        return self.original is not None

    def draw(self):
        canvas = self.app.canvas
        size = (max(1, canvas.winfo_width()), max(1, canvas.winfo_height()))
        if size != self.built_size:
            self.build(size)
        self.update()

    def photo(self, image):
        return ImageTk.PhotoImage(image, master=self.app.root)

    def build(self, size):
        """Create the chassis and one canvas object per control."""
        app = self.app
        canvas = app.canvas
        w, h = size
        app.scale = scale = min(w / ART_W, h / ART_H)
        ox, oy = (w - ART_W*scale)/2, (h - ART_H*scale)/2
        app.offset = ox, oy
        for registry in (app.controls, app.buttons, app.knob_targets):
            registry.clear()
        app.keys.clear()
        canvas.delete("all")
        self.photos = {}
        self.knob_frames = {}
        self.key_items, self.knob_items = {}, {}
        self.cap_items, self.wheel_items = {}, {}

        chassis = self.original.resize((max(1, round(ART_W*scale)), max(1, round(ART_H*scale))),
                                       Image.Resampling.LANCZOS)
        self.photos["chassis"] = self.photo(chassis)
        canvas.create_image(ox, oy, image=self.photos["chassis"], anchor="nw")

        # Keyboard: every key is its own object with idle and lit faces.
        for note, x1, y1, x2, y2, black in keyboard_layout():
            sx1, sy1, sx2, sy2 = app.bounds(x1, y1, x2, y2)
            size_px = (round(sx2) - round(sx1), round(sy2) - round(sy1))
            faces = tuple(self.photo(self.key_sprites.render(black, lit, size_px))
                          for lit in (False, True))
            item = canvas.create_image(round(sx1), round(sy1), image=faces[0], anchor="nw")
            self.key_items[note] = [item, faces, False]
            app.keys.append((note, x1, y1, x2, y2))

        for key, (x, y, r) in KNOBS.items():
            app.controls[key] = ("knob", x-r-7, y-r-7, x+r+7, y+r+7)
            app.knob_targets[key] = (x, y)
            sx, sy = app.bounds(x, y, x, y)[:2]
            self.knob_items[key] = [canvas.create_image(sx, sy, anchor="center"), None]

        for key, (x, y1, y2) in SLIDERS.items():
            app.controls[key] = ("slider", x-19, y1-5, x+19, y2+9)
            app.knob_targets[key] = (x, y1, y2)
            if key in self.caps:
                sprite = self.caps[key]
                scaled = sprite.resize((max(1, round(sprite.width*scale)),
                                        max(1, round(sprite.height*scale))),
                                       Image.Resampling.LANCZOS)
                self.photos["cap_" + key] = self.photo(scaled)
                self.cap_items[key] = canvas.create_image(0, 0, image=self.photos["cap_" + key],
                                                          anchor="nw")
            else:
                self.wheel_items[key] = canvas.create_line(0, 0, 0, 0, fill="#ffad63",
                                                           width=max(1, 2*scale))
        # Waveform buttons light up for the selected wave; level meter LEDs.
        self.wave_items = {}
        for key, face in self.sprites["waves"].items():
            photo = self.photo(face.resize((max(1, round(face.width*scale)),
                                            max(1, round(face.height*scale))),
                                           Image.Resampling.LANCZOS))
            self.photos[("wave",) + key] = photo
            x, y = app.bounds(*wave_box(*key))[:2]
            self.wave_items[key] = canvas.create_image(x, y, image=photo, anchor="nw",
                                                       state="hidden")
        self.fm_items = {}
        for osc, face in self.sprites["fm"].items():
            photo = self.photo(face.resize((max(1, round(face.width*scale)),
                                            max(1, round(face.height*scale))),
                                           Image.Resampling.LANCZOS))
            self.photos[("fm", osc)] = photo
            x, y = app.bounds(*FM_BUTTONS[osc])[:2]
            self.fm_items[osc] = canvas.create_image(x, y, image=photo, anchor="nw",
                                                     state="hidden")
            app.buttons[f"switch:osc{osc}_fm_on"] = FM_BUTTONS[osc]
        # Effect LEDs, the CHORUS/FLANGER title and the tube.
        self.led_items = {}
        for ident, face in self.sprites["leds"].items():
            photo = self.photo(face.resize((max(1, round(face.width*scale)),
                                            max(1, round(face.height*scale))),
                                           Image.Resampling.LANCZOS))
            self.photos[("led", ident)] = photo
            x, y = app.bounds(*FX_LEDS[ident])[:2]
            self.led_items[ident] = canvas.create_image(x, y, image=photo, anchor="nw",
                                                        state="hidden")
            app.buttons[f"switch:{ident}"] = FX_LEDS[ident]
        self.chorus_title = canvas.create_text(*app.bounds(*CHORUS_TITLE, 0, 0)[:2], text="CHORUS",
                                               fill="#d2ccc2", font=("Segoe UI", max(6, round(9*scale)), "bold"))
        app.buttons["chorus_type"] = CHORUS_TITLE_BOX
        self.tube_frames = {}
        self.tube_glow = None
        self.tube_item = canvas.create_image(*app.bounds(*TUBE_WINDOW)[:2], anchor="nw")
        x, y, r = KNOB_GEOMETRY["tube_drive"]
        canvas.create_text(*app.bounds(x, y + r + 12, 0, 0)[:2], text="TUBE DRIVE",
                           fill="#b9b4ab", font=("Segoe UI", max(5, round(8*scale)), "bold"))
        self.meter_items = {}
        for key, face in self.sprites["meter"].items():
            box = app.bounds(*meter_box(*key))
            size_px = (max(1, round(box[2] - box[0])), max(1, round(box[3] - box[1])))
            photo = self.photo(face.resize(size_px, Image.Resampling.LANCZOS))
            self.photos[("meter",) + key] = photo
            self.meter_items[key] = canvas.create_image(box[0], box[1], image=photo,
                                                        anchor="nw", state="hidden")
        self.meter_lit = {key: False for key in self.meter_items}
        # Drawbar organ: one object per drawbar, pulled down 0..8.
        self.drawbar_items, self.drawbar_frames = {}, {}
        hx1, hy1, hx2, hy2 = DRAWBAR_HEADER
        for x, title in (((DRAWBAR_X[0] + DRAWBAR_X[-1]) / 2, "DRAWBARS"),
                         (ORGAN_LABEL_X, "ORGAN")):
            canvas.create_text(*app.bounds(x, (hy1+hy2)/2, 0, 0)[:2], text=title,
                               fill="#241208", font=("Segoe UI", max(6, round(12*scale)), "bold"))
        x, y, r = KNOB_GEOMETRY["organ_drive"]
        canvas.create_text(*app.bounds(x - r - 30, y, 0, 0)[:2], text="DRIVE",
                           fill="#c9c4bb", font=("Segoe UI", max(5, round(9*scale)), "bold"))
        # Organ tab switches: lit and unlit faces, toggled by a click.
        self.switch_items = {}
        for ident, (label, box) in ORGAN_SWITCHES.items():
            size_px = (box[2] - box[0], box[3] - box[1])
            faces = tuple(self.photo(render_switch(label, lit, size_px, scale))
                          for lit in (False, True))
            sx, sy = app.bounds(*box)[:2]
            self.switch_items[ident] = [canvas.create_image(round(sx), round(sy), image=faces[0],
                                                            anchor="nw"), faces, False]
            app.buttons[f"switch:{ident}"] = box
        for index, x in enumerate(DRAWBAR_X):
            ident = f"drawbar{index + 1}"
            app.controls[ident] = ("drawbar", x - DRAWBAR_WIDTH/2 - 2, DRAWBAR_TOP,
                                   x + DRAWBAR_WIDTH/2 + 2, DRAWBAR_TOP + drawbar_length(8) + 6)
            app.knob_targets[ident] = (x, DRAWBAR_TOP, DRAWBAR_STEP, DRAWBAR_CAP)
            sx, sy = app.bounds(x - DRAWBAR_WIDTH/2, DRAWBAR_TOP, 0, 0)[:2]
            self.drawbar_items[ident] = [canvas.create_image(round(sx), round(sy), anchor="nw"), None]
        app.buttons.update(BUTTONS)
        self.display = LiveDisplay(app)
        self.display.build(chassis)
        self.built_size = size

    def knob_image(self, ident, value):
        frame = (ident, round(value * 100))
        if frame not in self.knob_frames:
            _, _, r = KNOBS[ident]
            self.knob_frames[frame] = self.photo(render_knob(
                r, frame[1] / 100, self.app.scale, detents=ident in DETENT_KNOBS))
        return self.knob_frames[frame]

    def update(self):
        """Move, rotate or light each control to match the current state."""
        app = self.app
        canvas = app.canvas
        pressed = app.midi_held | {app.current_mouse_note}
        for note, entry in self.key_items.items():
            lit = note in pressed
            if lit != entry[2]:
                canvas.itemconfigure(entry[0], image=entry[1][lit])
                entry[2] = lit
        for key, entry in self.knob_items.items():
            value = app.synth.get_param(key)
            if value != entry[1]:
                canvas.itemconfigure(entry[0], image=self.knob_image(key, value))
                entry[1] = value
        for key, item in self.cap_items.items():
            x, y1, y2 = SLIDERS[key]
            y = y2 - (y2 - y1) * app.synth.get_param(key)
            canvas.coords(item, *app.bounds(x - cap_half_width(key), y - CAP_REACH, x, y)[:2])
        for key, item in self.wheel_items.items():
            x, y1, y2 = SLIDERS[key]
            y = y2 - (y2 - y1) * app.synth.get_param(key)
            canvas.coords(item, *app.bounds(x - 11, y, x + 11, y))
        for ident, entry in self.drawbar_items.items():
            position = round(app.synth.get_param(ident) * 8)
            if position != entry[1]:
                if (ident, position) not in self.drawbar_frames:
                    self.drawbar_frames[(ident, position)] = self.photo(
                        render_drawbar(int(ident[7:]) - 1, position, app.scale))
                canvas.itemconfigure(entry[0], image=self.drawbar_frames[(ident, position)])
                entry[1] = position
        for ident, entry in self.switch_items.items():
            lit = app.synth.get_param(ident) >= 0.5
            if lit != entry[2]:
                canvas.itemconfigure(entry[0], image=entry[1][lit])
                entry[2] = lit
        for ident, item in self.led_items.items():
            on = app.synth.get_param(ident) >= 0.5
            canvas.itemconfigure(item, state="normal" if on else "hidden")
        flanger = app.synth.get_param("chorus_type") >= 0.5
        canvas.itemconfigure(self.chorus_title, text="FLANGER" if flanger else "CHORUS")
        self.update_tube()
        for osc, item in self.fm_items.items():
            on = app.synth.get_param(f"osc{osc}_fm_on") >= 0.5
            canvas.itemconfigure(item, state="normal" if on else "hidden")
        for (osc, index), item in self.wave_items.items():
            selected = round(app.synth.get_param(f"osc{osc}_wave") * 3) == index
            canvas.itemconfigure(item, state="normal" if selected else "hidden")
        self.display.update()
        self.draw_status()

    def tick(self):
        """~20 fps refresh of the live display while this renderer is in use."""
        if getattr(self.app, "mockup", None) is not self or not self.ready:
            return
        if self.built_size:
            self.display.tick()
            self.tick_meter()
            self.update_tube()
            if getattr(self.app, "update_state", "") == "available":
                blink = int(time.time() * 2) % 2
                if blink != getattr(self, "blink", None):
                    self.blink = blink
                    self.draw_status()
        self.app.root.after(50, self.tick)

    def update_tube(self):
        """The heater always glows a little; drive and signal light it up."""
        drive = self.app.synth.get_param("tube_drive")
        glow = 0.12 + 0.5 * drive + (0.38 * min(1.0, self.meter_level * 1.3) if drive > 0.001 else 0.0)
        level = round(min(1.0, glow) * 12)
        if level != self.tube_glow:
            if level not in self.tube_frames:
                self.tube_frames[level] = self.photo(render_tube(level / 12, self.app.scale))
            self.app.canvas.itemconfigure(self.tube_item, image=self.tube_frames[level])
            self.tube_glow = level

    def tick_meter(self):
        """Peak meter: −48 dB..0 dB over 12 LEDs, fast attack, slow fall."""
        peak = float(getattr(self.app.synth, "peak", 0.0))
        level = 0.0 if peak <= 0.004 else min(1.0, (20 * math.log10(peak) + 48) / 48)
        self.meter_level = max(level, self.meter_level * 0.86)
        lit_rows = round(self.meter_level * len(METER_ROWS))
        for (column, row), item in self.meter_items.items():
            lit = len(METER_ROWS) - row <= lit_rows
            if lit != self.meter_lit[(column, row)]:
                self.app.canvas.itemconfigure(item, state="normal" if lit else "hidden")
                self.meter_lit[(column, row)] = lit

    def draw_status(self):
        """Patch, update, MIDI and value readouts: small texts redrawn each update."""
        app = self.app
        canvas = app.canvas
        canvas.delete("status")
        before = set(canvas.find_all())
        # Mask fictional patch metadata, show actual patch name and status.
        app.rect(566,18,777,67,"#080d17")
        dirty = getattr(app, "patch_dirty", False)
        app.text(672,37,app.patch_name[:21] + (" *" if dirty else ""),15,
                 "#ffb05e" if dirty else "#eed9bf",bold=True)
        if dirty:
            # Edited: the sound no longer matches the stored patch.
            app.rect(735,20,775,30,"#3a2008","#ffb05e")
            app.text(755,25,"EDITADO",6,"#ffd08b",bold=True,minimum=4)
        app.text(672,57,f"{app.patch_bank.upper()} / {app.patch_category.upper()}  ·  v{__version__()}",9,"#a2b2c6")
        # The bank/category selectors must reflect the real patch, not the
        # text that happened to be photographed in the reference artwork.
        app.rect(963,29,1057,59,"#10151c","#434850")
        app.text(1008,43,app.patch_bank[:11],11,"#f0e0c9")
        app.text(1045,43,"▾",10,"#d8d5cc")
        app.rect(1082,29,1199,59,"#10151c","#434850")
        app.text(1128,43,app.patch_category[:12],11,"#f0e0c9")
        app.text(1186,43,"▾",10,"#d8d5cc")
        # Top bar, two aligned columns: CPU and RAM (label left, value right),
        # then the running version above the update button.
        x1, y1, x2, y2 = STATUS_BOX
        split = x1 + 64
        for row, (label, value) in enumerate((("CPU", app.cpu_text), ("RAM", app.ram_text))):
            y = y1 + 13 + row * 18
            app.text(x1+5,y,label,6,"#8f9bb0","w",True,minimum=4)
            app.text(split-5,y,value,8,"#44dfe7","e",True,minimum=4)
        app.line(split,y1+6,split,y2-6,fill="#2c3038",width=1)
        state = getattr(app, "update_state", "idle")
        app.text((split+x2)/2,y1+13,f"v{__version__()}",7,
                 "#59d98e" if state == "current" else "#e8e2d9",bold=True,minimum=4)
        # UPD: green check when current, blinking orange when a new version
        # exists (a click starts the update), progress while downloading.
        blink_on = int(time.time() * 2) % 2 == 0
        face = {
            "checking": ("#1b1f26", "#4a5060", "…", "#b3b5ba"),
            "current": ("#10251a", "#3fae6c", "✓ OK", "#59d98e"),
            "downloading": ("#2b1a0c", "#fca34e", f"{getattr(app, 'update_progress', 0)}%", "#fca34e"),
            "error": ("#2a1212", "#e0574a", "ERRO", "#ff8a7a"),
        }.get(state, ("#1b1f26", "#4a5060", "UPD", "#b3b5ba"))
        if state == "available" and app.release:
            tag = "↑" + app.release["tag_name"].lstrip("v")
            face = (("#3a2008", "#ffb05e", tag, "#ffd08b") if blink_on
                    else ("#1b1f26", "#6a4a2a", tag, "#a4703c"))
        bx1, by1, bx2, by2 = UPDATE_BUTTON
        app.rect(bx1,by1,bx2,by2,face[0],face[1])
        app.text((bx1+bx2)/2,(by1+by2)/2,face[2],7,face[3],bold=True,minimum=4)
        # MIDI: red when no controller is open, green when connected, cyan while playing.
        connected = getattr(app, "port", None) is not None
        app.text(1290,46, "●" if connected else "○", 11,
                 "#37cbff" if app.midi_held else "#4fd08a" if connected else "#e0574a")
        # Numerical value appears only while a control is being dragged.
        if app.drag and app.drag[0] in KNOBS:
            x, y, r = KNOBS[app.drag[0]]
            app.rect(x-33,y+r+9,x+33,y+r+28,"#10151b")
            app.text(x,y+r+18,format_value(app.drag[0].split("@")[0],app.synth.get_param(app.drag[0])),11,"#ffb16d",bold=True)
        elif app.drag and app.drag[0] in SLIDERS:
            x, y1, y2 = SLIDERS[app.drag[0]]
            y = y2 - (y2 - y1) * app.synth.get_param(app.drag[0])
            app.rect(x-22,y-36,x+22,y-20,"#0c141f")
            app.text(x,y-28,str(round(app.synth.get_param(app.drag[0])*100)),10,"#ffab5d",bold=True)
        # Persistent feature notice, small and outside the functional panel.
        app.text(797,954,"CONTROLES FUTUROS: VISÍVEIS, NÃO INTERATIVOS",9,"#7c828a")
        for item in set(canvas.find_all()) - before:
            canvas.addtag_withtag("status", item)


def __version__():
    from . import __version__
    return __version__
