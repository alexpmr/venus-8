"""Pixel-aligned interactive layer over the approved Venus-8 concept art.

The artwork is the permanent visual source; drawing primitives are not used to
reproduce the panel. This module only adds interaction and changing state.
"""
from pathlib import Path
import sys
import math

from PIL import Image, ImageTk

ART_W, ART_H = 1600, 959

# Coordinates are in the exact original 1600 x 959 PNG/JPG artwork.
KNOBS = {
    "osc1_tune": (161, 189, 22), "osc2_tune": (377, 188, 22),
    "osc3_tune": (591, 188, 22),
    "cutoff": (988, 187, 33), "resonance": (1080, 188, 30),
    "drive": (990, 274, 23),
    "lfo_rate": (78, 460, 22), "lfo_depth": (138, 460, 22),
    "delay_time": (1060, 660, 20), "delay_feedback": (1115, 660, 19),
    "delay_mix": (1167, 661, 20),
    "volume": (1477, 638, 23),
}
SLIDERS = {
    "osc1_level": (722, 163, 274),
    "osc2_level": (766, 163, 274),
    "osc3_level": (809, 163, 274),
    "sub_level": (854, 163, 274),
    "noise_level": (896, 163, 274),
    "attack": (1157, 159, 274),
    "decay": (1186, 159, 274), "sustain": (1216, 159, 274),
    "release": (1245, 159, 274),
    "pitch_bend": (76, 846, 927),
    "modwheel": (166, 846, 927),
}
BUTTONS = {
    "save": (893, 26, 938, 61),
    "browse": (822, 26, 881, 61),
    "bank": (950, 27, 1069, 64),
    "category": (1071, 27, 1205, 64),
    "prev_patch": (528, 22, 559, 66),
    "next_patch": (778, 22, 813, 66),
    "settings": (592, 695, 728, 738),
    "check_update": (1394, 17, 1450, 65),
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
        self.cache_size = None
        self.cache_photo = None
        self.original_size = None
        if self.path:
            try:
                with Image.open(self.path) as source:
                    self.original_size = source.size
                    self.original = source.convert("RGB")
            except Exception:
                self.original = None

    @property
    def ready(self):
        return self.original is not None

    def draw(self):
        app = self.app
        canvas = app.canvas
        w, h = max(1, canvas.winfo_width()), max(1,canvas.winfo_height())
        app.scale = min(w / ART_W, h / ART_H)
        ox = (w - ART_W*app.scale)/2
        oy = (h - ART_H*app.scale)/2
        app.offset = ox,oy
        app.controls.clear()
        app.buttons.clear()
        app.keys.clear()
        app.knob_targets.clear()
        canvas.delete("all")

        img_w = max(1, round(ART_W * app.scale))
        img_h = max(1, round(ART_H * app.scale))
        if self.cache_size != (img_w, img_h):
            image = self.original.resize((img_w,img_h), Image.Resampling.LANCZOS)
            self.cache_photo = ImageTk.PhotoImage(image,master=app.root)
            self.cache_size=(img_w,img_h)
        canvas.create_image(ox,oy,image=self.cache_photo,anchor="nw")

        for key,(x,y,r) in KNOBS.items():
            app.controls[key]=("knob",x-r-7,y-r-7,x+r+7,y+r+7)
            app.knob_targets[key]=(x,y)
            self.marker(key,x,y,r)
        for key,(x,y1,y2) in SLIDERS.items():
            app.controls[key]=("slider",x-19,y1-5,x+19,y2+9)
            app.knob_targets[key]=(x,y1,y2)
            self.fader_marker(key,x,y1,y2)
        app.buttons.update(BUTTONS)

        # Mask fictional patch metadata, show actual patch name and status.
        app.rect(566,18,777,67,"#080d17")
        app.text(672,37,app.patch_name[:21],15,"#eed9bf",bold=True)
        app.text(672,57,f"{app.patch_bank.upper()} / {app.patch_category.upper()}  ·  v{__version__()}",9,"#a2b2c6")
        app.rect(1370,43,1450,74,"#10151b")
        status = f"↑ {app.release['tag_name']}" if app.release else "UPD"
        app.text(1411,56,status,10,"#fca34e" if app.release else "#b3b5ba",bold=True)
        app.text(1290,46, "●" if app.midi_held else "○", 11,
                 "#37cbff" if app.midi_held else "#6a747b")
        app.text(1356,67,f"{app.cpu_text}",10,"#44dfe7",bold=True)

        # Overdraw only active notes, preserving all original white/black key proportions.
        start, end = 270, 1543
        whites=[n for n in range(48,97) if n%12 in (0,2,4,5,7,9,11)]
        width=(end-start)/len(whites)
        for i,n in enumerate(whites):
            x=start+i*width
            app.keys.append((n,x,822,x+width,944))
            if n in app.midi_held or n==app.current_mouse_note:
                self.overlay_rect(x+1,824,x+width-1,942,"#f0b76a",stipple="gray50")
        for i,n in enumerate(whites):
            if n%12 in (4,11) or n+1>96:
                continue
            x=start+(i+1)*width-width*0.31
            note=n+1
            app.keys.append((note,x,822,x+width*0.62,893))
            if note in app.midi_held or note==app.current_mouse_note:
                self.overlay_rect(x,825,x+width*0.62,894,"#ff8c3d",stipple="gray50")
        # Persistent feature notice, small and outside the functional panel.
        app.text(797,954,"CONTROLES FUTUROS: VISÍVEIS, NÃO INTERATIVOS",9,"#7c828a")

    def overlay_rect(self,x1,y1,x2,y2,fill,stipple=None):
        app=self.app
        app.canvas.create_rectangle(*app.bounds(x1,y1,x2,y2),fill=fill,
                                    stipple=stipple,outline="")

    def marker(self,ident,x,y,r):
        app=self.app
        val=app.synth.get_param(ident)
        # Tiny luminous arc/value mark over the hardware dial's bezel.
        angle=math.radians(135+270*val)
        px=x+math.cos(angle)*(r+5)
        py=y+math.sin(angle)*(r+5)
        app.canvas.create_oval(*app.bounds(px-3,py-3,px+3,py+3),
                               fill="#ffa454",outline="#ffd08b")
        # Numerical value appears only during interaction.
        if app.drag and app.drag[0]==ident:
            app.rect(x-33,y+r+9,x+33,y+r+28,"#10151b")
            app.text(x,y+r+18,f"{round(val*100)}%",11,"#ffb16d",bold=True)

    def fader_marker(self,ident,x,y1,y2):
        app=self.app
        val=app.synth.get_param(ident)
        y=y2-(y2-y1)*val
        app.line(x-11,y,x+11,y,fill="#ffad63",width=2)
        if app.drag and app.drag[0]==ident:
            app.rect(x-22,y-28,x+22,y-12,"#0c141f")
            app.text(x,y-20,str(round(val*100)),10,"#ffab5d",bold=True)


def __version__():
    from . import __version__
    return __version__
