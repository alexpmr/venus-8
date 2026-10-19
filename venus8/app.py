"""VENUS-8 graphical workbench. Control surfaces are shown even when DSP is pending."""
import json
import math
import ctypes
import os
from pathlib import Path
import queue
import re
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import mido
import numpy as np
import psutil
import sounddevice as sd

from . import __version__
from .synth import DEFAULTS, WAVES, Synth
from .factory_presets import factory_programs
from . import updater
from .mockup_ui import MockupRenderer

def setup_windows_dpi():
    """Prevent Windows from bitmap-upscaling and blurring the UI."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (OSError, AttributeError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (OSError, AttributeError):
            pass


BASE_W, BASE_H = 1600, 980
DARK = "#0b0e13"
PANEL = "#191e24"
PANEL2 = "#222831"
EDGE = "#45413d"
ORANGE = "#f68b3b"
GOLD = "#ffb968"
WHITE = "#e8e2d9"
FADED = "#777f8b"
GREEN = "#70dda4"

# The specification includes controls not yet implemented in the audio engine.
# Only controls listed with a parameter are interactive and audible.
SECTIONS = [
    ("OSCILLATOR 1", 35, 87, 268, 330),
    ("OSCILLATOR 2", 273, 87, 506, 330),
    ("OSCILLATOR 3", 511, 87, 699, 330),
    ("MIXER", 704, 87, 938, 330),
    ("FILTER", 943, 87, 1138, 330),
    ("AMP ENV", 1143, 87, 1280, 330),
    ("FILTER ENV", 1285, 87, 1423, 330),
    ("MOD ENV", 1428, 87, 1565, 330),
    ("LFO 1", 35, 338, 275, 531),
    ("LFO 2", 280, 338, 520, 531),
    ("DISPLAY / PATCH", 525, 338, 1080, 531),
    ("MODULATION MATRIX", 1085, 338, 1565, 531),
    ("ARPEGGIATOR", 35, 539, 282, 696),
    ("STEP SEQUENCER", 287, 539, 749, 696),
    ("EFFECTS", 754, 539, 1353, 696),
    ("MASTER", 1358, 539, 1565, 696),
    ("PERFORMANCE  /  SPLIT-LAYER  /  KEYBOARD  /  MIDI  /  SETTINGS", 35, 704, 1565, 819),
]


def match_midi_name(saved, names):
    """Saved controller among current ports; Windows may renumber the suffix."""
    if saved in names:
        return saved
    base = re.sub(r"\s+\d+$", "", saved or "")
    return next((n for n in names if base and re.sub(r"\s+\d+$", "", n) == base), None)


class App:
    def __init__(self):
        setup_windows_dpi()
        self.root = tk.Tk()
        if sys.platform == "win32":
            icon_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
            ico = icon_root / "assets" / "venus-8.ico"
            if ico.is_file():
                try:
                    self.root.iconbitmap(default=str(ico))
                except tk.TclError:
                    pass
        self.root.title(f"VENUS-8 — Virtual Analog Synthesizer v{__version__}")
        self.root.geometry("1550x950")
        self.root.minsize(1050, 690)
        self.root.configure(bg=DARK)
        self.synth = Synth()
        self.process = psutil.Process()
        self.process.cpu_percent(None)
        self.stream = None
        self.port = None
        self.midi_devices = []
        self.audio_devices = []
        self.events = queue.Queue()
        self.release = None
        self.updating = False
        self.update_label = "VERIFICAR UPDATE"
        self.audio_error = ""
        self.last_midi = "MIDI: —"
        self.current_mouse_note = None
        self.midi_held = set()
        self.drag = None
        self.knob_targets = {}
        self.buttons = {}
        self.keys = []
        self.controls = {}
        self.scale = 1.0
        self.offset = (0, 0)
        self.patch_name = "Ladder Bass"
        self.patch_bank = "Factory"
        self.patch_category = "Bass"
        self.patch_description = "Baixo vintage encorpado"
        self.patch_identity = ("Factory", self.patch_name)
        self.synth.load_params(factory_programs()[0]["params"])
        self.patch_dirty = False
        self.pending = None          # change waiting on the unsaved-changes prompt
        self.last_param = None
        self.dsp_load = 0.0
        self.scope_buffer = np.zeros(512, dtype=np.float32)
        self.audio_name = ""
        self.patch_dir = Path(os.environ.get("APPDATA") or Path.home()) / "Venus-8" / "Patches"
        self.patch_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.patch_dir.parent / "settings.json"
        self.settings = self._load_settings()
        self.root.bind("<Escape>", lambda e: self.panic())
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Control-s>", lambda e: self.save_patch())
        self.canvas = tk.Canvas(self.root, bg=DARK, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<Button-1>", self.mouse_down)
        self.canvas.bind("<B1-Motion>", self.mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_up)
        self.canvas.bind("<MouseWheel>", self.mouse_wheel)
        self.canvas.bind("<Button-3>", self.mouse_right)
        self.mockup = MockupRenderer(self)
        self.scan_devices()
        self.root.after(40, self.poll)
        self.root.after(1200, self.check_update)
        self.root.after(2000, self.watch_midi)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.draw()
        self.root.after(50, self.mockup.tick)

    def _load_settings(self):
        try:
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save_settings(self):
        try:
            self.settings_path.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
        except OSError:
            pass

    def toggle_fullscreen(self, event=None):
        self.root.attributes("-fullscreen", not bool(self.root.attributes("-fullscreen")))

    def s(self, value):
        return value * self.scale

    def bounds(self, x1, y1, x2, y2):
        ox, oy = self.offset
        return (ox + self.s(x1), oy + self.s(y1), ox + self.s(x2), oy + self.s(y2))

    def rect(self, x1, y1, x2, y2, color, outline=None, width=1):
        self.canvas.create_rectangle(*self.bounds(x1, y1, x2, y2), fill=color,
                                     outline=outline or color, width=self.s(width))

    def line(self, *coords, fill=EDGE, width=1):
        pts = []
        for x, y in zip(coords[0::2], coords[1::2]):
            ox, oy = self.offset
            pts.extend((ox + self.s(x), oy + self.s(y)))
        self.canvas.create_line(*pts, fill=fill, width=self.s(width))

    def text(self, x, y, value, size=13, color=WHITE, anchor="center", bold=False):
        ox, oy = self.offset
        self.canvas.create_text(ox + self.s(x), oy + self.s(y), text=str(value),
                                fill=color, font=("Segoe UI", max(7, round(size * self.scale)),
                                "bold" if bold else "normal"), anchor=anchor)

    def panel(self, name, x1, y1, x2, y2):
        """Layered steel panel and burnished copper section header."""
        self.rect(x1, y1, x2, y2, "#0b0e12", "#564c42")
        self.rect(x1+3, y1+3, x2-3, y2-3, "#1b1e23", "#303137")
        self.rect(x1+5, y1+5, x2-5, y1+31, "#a55d37", "#bd7850")
        self.rect(x1+6, y1+5, x2-6, y1+7, "#d28b58")
        self.rect(x1+6, y1+29, x2-6, y1+31, "#693b26")
        self.text((x1+x2)/2, y1+18, name, 12, "#111316", bold=True)
        for screwx in (x1+9, x2-9):
            self.circle(screwx,y2-9,2.1,"#65605c","#202123")
            self.line(screwx-1,y2-10,screwx+1,y2-8,fill="#2c2d31",width=0.7)

    def circle(self, x, y, r, color, outline=None, width=1):
        self.canvas.create_oval(*self.bounds(x-r,y-r,x+r,y+r),
                                fill=color, outline=outline or color,
                                width=max(0.5,self.s(width)))

    def button(self, ident, title, x1, y1, x2, y2, enabled=True, selected=False):
        """Backlit tactile pushbutton, preserving existing hit targets."""
        if selected:
            self.rect(x1-2,y1-2,x2+2,y2+2,"#704122","#f4a04a")
            self.rect(x1,y1,x2,y2,"#e68b40","#f8b36b")
            self.rect(x1+2,y1+2,x2-2,y1+4,"#ffc07c")
        else:
            fill = "#242932" if enabled else "#171b20"
            self.rect(x1-1,y1-1,x2+1,y2+1,"#080b0f","#50535a")
            self.rect(x1+1,y1+1,x2-1,y2-1,fill)
            self.line(x1+3,y1+3,x2-3,y1+3,fill="#474a50" if enabled else "#22272b")
        ink = "#111113" if selected else (WHITE if enabled else "#72777f")
        self.text((x1+x2)/2,(y1+y2)/2,title,10,ink,bold=True)
        if enabled:
            self.buttons[ident]=(x1,y1,x2,y2)

    def knob(self, ident, caption, x, y, radius=25, enabled=True):
        """3D rotary control with tick arc, metal bezel and amber pointer."""
        val = self.synth.params.get(ident,0.5) if enabled else 0.5
        ink = ORANGE if enabled else "#656975"
        # Scalloped calibration arc; 0 at 225 degrees, max at 495.
        if radius>=18:
            for tick in range(17):
                deg=math.radians(135+270*tick/16)
                outer=radius+7
                inner=outer-(5 if tick%4==0 else 2.8)
                active=(tick/16 <= val)
                self.line(x+math.cos(deg)*inner,y+math.sin(deg)*inner,
                          x+math.cos(deg)*outer,y+math.sin(deg)*outer,
                          fill=ORANGE if enabled and active else "#51545c",
                          width=1.25)
        self.circle(x+1.3,y+2.6,radius+1.7,"#050608","#0f1318",2)
        self.circle(x,y,radius,"#343942","#777b82",1)
        self.circle(x,y,radius-2,"#191c22","#0d0d10")
        self.circle(x-2,y-2,radius-5,"#353a41","#454951")
        self.circle(x+1,y+1,radius-8,"#1b1f26","#090b0d",1)
        # glossy crescent
        if radius>=19:
            self.line(x-radius*.52,y-radius*.56,x-radius*.17,y-radius*.74,
                      fill="#74777c" if enabled else "#41474e",width=2)
        pointer=math.radians(135+270*val)
        self.line(x+math.cos(pointer)*(radius*.21),y+math.sin(pointer)*(radius*.21),
                  x+math.cos(pointer)*(radius*.82),y+math.sin(pointer)*(radius*.82),
                  fill=ink,width=2.7)
        self.circle(x,y,1.2,"#b7b2ad" if enabled else "#555b62")
        self.text(x,y+radius+17,caption,9.5,WHITE if enabled else FADED)
        if enabled:
            self.controls[ident]=("knob",x-radius-8,y-radius-8,x+radius+8,y+radius+9)
            self.knob_targets[ident]=(x,y)

    def slider(self, ident, title, x, y1, y2, enabled=True):
        """Hardware fader: calibrated steel track, illuminated movable cap."""
        val = self.synth.params.get(ident,0.5) if enabled else 0.5
        self.rect(x-4,y1,x+4,y2,"#080a0d","#51555b")
        self.rect(x-1,y1+2,x+1,y2-2,"#343840")
        if y2-y1>50:
            for idx in range(9):
                py=y1+(y2-y1)*idx/8
                self.line(x-12,py,x-7,py,fill="#777570" if idx%2==0 else "#43454c",width=1)
                self.line(x+7,py,x+12,py,fill="#777570" if idx%2==0 else "#43454c",width=1)
        pos=y2-(y2-y1)*val
        self.rect(x-16,pos-8,x+16,pos+8,"#060709")
        self.rect(x-15,pos-7,x+15,pos+6,
                  "#ea8a3c" if enabled else "#626971",
                  "#f3ae68" if enabled else "#71757c")
        self.rect(x-13,pos-6,x+13,pos-4,
                  "#ffc17f" if enabled else "#858a90")
        self.rect(x-13,pos+3,x+13,pos+5,
                  "#a35927" if enabled else "#383d45")
        self.text(x,y2+17,title,9,WHITE if enabled else FADED)
        if enabled:
            self.controls[ident]=("slider",x-22,y1-10,x+22,y2+12)
            self.knob_targets[ident]=(x,y1,y2)


    def draw(self):
        # Artwork-first presentation keeps the exact final panel geometry.
        if getattr(self, 'mockup', None) is not None and self.mockup.ready:
            self.mockup.draw()
            return
        """Draw the canonical full-size Venus-8 panel; grey controls remain disabled."""
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        self.scale = min(w / BASE_W, h / BASE_H)
        self.offset = ((w-BASE_W*self.scale)/2, (h-BASE_H*self.scale)/2)
        self.canvas.delete("all")
        self.controls.clear()
        self.buttons.clear()
        self.knob_targets.clear()
        self.rect(0,0,1600,980,DARK)
        for left,right in ((0,28),(1572,1600)):
            self.rect(left,0,right,980,"#744526")
            self.rect(left+8,5,left+17,976,"#ac6b39")
        self.rect(30,3,1570,83,"#10151b","#4c5055")
        self.text(49,24,"VENUS",36,WHITE,"w",True)
        self.text(211,24,"-8",36,ORANGE,"w",True)
        self.text(51,66,"VIRTUAL ANALOG SYNTHESIZER",12,FADED,"w")
        self.rect(480,12,835,73,"#0c1421","#4c5967")
        self.text(658,31,self.patch_name[:28],19,GOLD,bold=True)
        self.text(658,55,f"USER / ANALOG PAD  •  v{__version__}",11,FADED)
        self.button("prev_patch","◀",445,20,478,65)
        self.button("next_patch","▶",838,20,870,65)
        self.button("browse","BROWSE",879,23,957,60)
        self.button("save","SAVE",963,23,1021,60)
        self.text(1042,14,"BANK",10,FADED,"w")
        self.button("bank","USER ▾",1037,27,1125,59,enabled=False)
        self.text(1142,14,"CATEGORY",10,FADED,"w")
        self.button("category","ALL ▾",1137,27,1222,59,enabled=False)
        self.button("settings","MIDI / AUDIO",1227,23,1340,60)
        self.text(1366,21,"MIDI",11,GREEN)
        self.rect(1359,34,1376,47,GREEN if self.midi_held else "#304950")
        self.text(1422,20,"CPU",10,GREEN)
        self.text(1422,41,self.cpu_text,12,GOLD)
        self.text(1483,20,"RAM",10,GREEN)
        self.text(1483,41,self.ram_text,11,GOLD)
        self.button("check_update","UPD" if self.release else "↻",1522,17,1561,51,
                    selected=bool(self.release))
        self.text(1538,67,self.update_label[:16],9,GREEN if self.release else FADED)

        for sec in SECTIONS:
            self.panel(*sec)

        # Oscillators — three permanent modules, controls positioned as in the mockup.
        for i,(left,right) in enumerate(((35,268),(273,506),(511,699)),1):
            inner = right-left-19
            step = inner/4
            for j,name in enumerate(("SAW","PUL","TRI","SIN")):
                x=left+8+j*step
                selected=round(self.synth.get_param(f"osc{i}_wave")*3)==j
                self.button(f"wave{i}_{j}",name,x,129,x+step-3,159,selected=selected)
            mx=(left+right)/2
            self.knob(f"osc{i}_oct","OCTAVE",left+40,218,19,enabled=False)
            self.knob(f"osc{i}_tune","TUNE",mx,218,20)
            self.knob(f"osc{i}_level","LEVEL",right-40,218,20)
            self.button(f"sync{i}","SYNC",left+11,286,left+77,316,enabled=False)
            self.button(f"fm{i}","FM",left+82,286,left+143,316,enabled=False)
            self.button(f"ring{i}","RING",left+149,286,right-8,316,enabled=False)

        for ident,title,x in (
            ("osc1_level","OSC1",729),("osc2_level","OSC2",776),
            ("osc3_level","OSC3",823),("sub_level","SUB",870),("noise_level","NOISE",916)
        ):
            self.slider(ident,title,x,165,286)

        self.button("filter_type","LOW PASS 24 dB",955,133,1126,163,enabled=False)
        self.knob("cutoff","CUTOFF",1004,224,28)
        self.knob("resonance","RESONANCE",1085,224,25,enabled=False)
        self.knob("drive","DRIVE",1007,291,17)
        self.knob("filter_track","KEY TRACK",1082,291,17,enabled=False)
        self.button("filter_env","ENV",1103,290,1126,316,enabled=False)

        # ADSR modules — only attack and release are currently wired to DSP.
        for left,prefix in ((1143,"amp"),(1285,"filter"),(1428,"mod")):
            positions=(left+20,left+50,left+80,left+109)
            for idx,(x,label) in enumerate(zip(positions,("A","D","S","R"))):
                key={"A":"attack","D":"decay","S":"sustain","R":"release"}[label]
                active=prefix=="amp" and label in ("A","R")
                self.slider(key if active else f"{prefix}_env_{label}",label,x,165,279,
                            enabled=active)

        self.knob("lfo_rate","RATE",104,444,24)
        self.knob("lfo_depth","DEPTH",203,444,24)
        self.button("lfo_wave","SINE   TRI   SAW   S&H",62,489,247,521,enabled=False)
        self.knob("lfo2_rate","RATE",352,444,24,enabled=False)
        self.knob("lfo2_depth","DEPTH",452,444,24,enabled=False)
        self.button("lfo2_wave","SINE   TRI   SAW   S&H",303,489,491,521,enabled=False)

        # Central display, with the five tabs of the final layout.
        for idx,title in enumerate(("MAIN","MOD MATRIX","ARP / SEQ","FX","GLOBAL")):
            left=535+idx*106
            self.button(f"tab_{idx}",title,left,349,left+102,377,
                        enabled=idx==0,selected=idx==0)
        self.rect(539,387,1066,524,"#0a1725","#425466")
        for j in range(26):
            z=j/26
            self.line(541,390+5*j,1063,390+5*j,
                      fill=f"#{int(15+28*z):02x}{int(26+21*z):02x}{int(46+18*z):02x}")
        self.canvas.create_oval(*self.bounds(670,393,832,520),
                                fill="#915a40",outline="#dc8d57",width=self.s(2))
        self.text(741,427,"VENUS-8",25,GOLD,bold=True)
        self.text(741,461,self.patch_name[:25],16,WHITE,bold=True)
        self.text(741,489,"VINTAGE ANALOG SYNTHESIZER",10,WHITE)
        self.text(931,408,"PATCH",10,FADED,"w")
        self.text(931,433,"CATEGORY   USER",11,WHITE,"w")
        self.text(931,455,"MIDI       USB",11,GREEN,"w")
        self.text(931,478,f"VOICES     {len(self.synth.voices):02d}",11,WHITE,"w")
        self.text(931,505,"GREY = SOON",10,FADED,"w")

        # Modulation matrix preview: routing is explicitly disabled.
        for i,(source,dest) in enumerate((
            ("LFO 1","FILTER CUTOFF"),("MOD WHEEL","RESONANCE"),
            ("ENV 2","OSC PWM"),("AFTERTOUCH","FILTER"),
            ("VELOCITY","AMP LEVEL"),("LFO 2","CHORUS")
        )):
            y=379+24*i
            self.text(1105,y,str(i+1),11,FADED,"w")
            self.text(1140,y,source,10,FADED,"w")
            self.text(1314,y,dest,10,FADED,"w")
            self.text(1538,y,"—",11,FADED)

        self.button("arp_on","ON",54,588,110,620,enabled=False)
        self.button("arp_mode","UP / DOWN",119,588,266,620,enabled=False)
        self.knob("arp_rate","RATE",95,663,21,enabled=False)
        self.knob("arp_gate","GATE",210,663,21,enabled=False)
        self.text(518,587,"STEP SEQUENCER  •  EM BREVE",12,FADED)
        for i in range(16):
            x=300+i*27.0
            self.button(f"step{i}",str(i+1),x,626,x+24,660,enabled=False)
        self.text(519,675,"16 STEPS   •   GATE   •   SWING   •   SYNC",12,FADED)

        # Effects, master.
        for name,x in (("CHORUS",767),("PHASER",913),("DELAY",1059),("REVERB",1205)):
            self.rect(x,587,x+142,690,PANEL2,EDGE)
            self.text(x+71,601,name,12,ORANGE if name=="DELAY" else FADED,bold=True)
            if name=="DELAY":
                self.knob("delay_mix","MIX",x+36,639,18)
                self.knob("delay_time","TIME",x+107,639,18)
                self.slider("delay_feedback","FB",x+73,625,659)
            else:
                self.knob(f"fx_{name}","EM BREVE",x+71,650,23,enabled=False)
        self.knob("volume","LEVEL",1419,624,29)
        self.knob("width","WIDTH",1517,624,22,enabled=False)
        peak=self.synth.peak
        for j in range(10):
            y=671-j*7
            self.rect(1431,y,1540,y+5,
                      GREEN if peak>(j+1)/10 else "#364349")
        self.text(1482,685,f"{peak*100:.0f}%",10,GOLD)

        # Lower performance control strip, fixed keyboard below.
        self.button("poly","POLY",53,743,120,775,selected=True)
        self.button("mono","MONO",127,743,195,775,enabled=False)
        self.button("legato","LEGATO",202,743,281,775,enabled=False)
        self.button("unison","UNISON",287,743,368,775,enabled=False)
        self.text(425,749,"DETUNE / SPREAD",11,FADED)
        self.knob("perf_detune","DETUNE",486,778,15,enabled=False)
        self.knob("perf_spread","SPREAD",558,778,15,enabled=False)
        self.knob("perf_glide","GLIDE",647,779,16,enabled=False)
        self.text(744,756,"TRANSPOSE",11,FADED)
        self.text(744,780,"0",15,WHITE)
        self.text(843,756,"OCTAVE",11,FADED)
        self.text(843,780,"0",15,WHITE)
        self.text(945,757,"LAYER / SPLIT",11,FADED)
        self.text(945,780,"NOT YET ENABLED",10,FADED)
        self.text(1250,758,"MIDI",11,GREEN)
        self.text(1268,783,self.last_midi[:29],11,GREEN)
        self.text(1516,758,"VOICES",11,GOLD)
        self.text(1516,782,f"{len(self.synth.voices)} / {self.synth.max_voices}",14,GOLD)
        self.draw_keyboard()

    def draw_keyboard(self):
        """Large 49-note keyboard with dedicated vintage pitch/mod wheels on the left."""
        self.rect(35,826,1565,968,"#101214","#554e49")
        self.rect(42,832,262,962,"#181c21","#545050")
        self.text(104,844,"PITCH BEND",11,WHITE)
        self.text(201,844,"MOD WHEEL",11,WHITE)
        # Two touch/mouse-operable performance faders styled as hardware wheels.
        self.slider("pitch_bend","±2",107,863,923)
        self.slider("modwheel","MOD",201,863,923)
        self.keys.clear()
        whites = [n for n in range(48,97) if n % 12 in (0,2,4,5,7,9,11)]
        origin=270
        white_width=(1558-origin)/len(whites)
        for i,n in enumerate(whites):
            x=origin+i*white_width
            active=n in self.midi_held or n==self.current_mouse_note
            self.rect(x,833,x+white_width-1,958,GOLD if active else "#f0e6d4","#1d2025")
            self.keys.append((n,x,833,x+white_width-1,958))
        for i,n in enumerate(whites):
            if n%12 in (4,11) or n+1>96:
                continue
            x=origin+(i+1)*white_width-white_width*.31
            note=n+1
            active=note in self.midi_held or note==self.current_mouse_note
            self.rect(x,833,x+white_width*.62,909,
                      ORANGE if active else "#12151a","#30343a")
            self.keys.append((note,x,833,x+white_width*.62,909))

    @property
    def cpu_text(self):
        try:
            return f"{self.process.cpu_percent(None):.1f}%"
        except Exception:
            return "—"

    @property
    def ram_text(self):
        try:
            return f"{self.process.memory_info().rss/1048576:.0f} MB"
        except Exception:
            return "—"

    @property
    def voices_text(self):
        return f"{len(self.synth.voices)}/16 VOICES"

    def coords(self, event):
        ox,oy=self.offset
        return ((event.x-ox)/self.scale,(event.y-oy)/self.scale)

    @staticmethod
    def inside(x,y,box):
        x1,y1,x2,y2=box
        return x1<=x<=x2 and y1<=y<=y2

    def find_note(self,x,y):
        for note,x1,y1,x2,y2 in reversed(self.keys):
            if self.inside(x,y,(x1,y1,x2,y2)):
                return note
        return None

    def mouse_down(self,event):
        x,y=self.coords(event)
        note=self.find_note(x,y)
        if note is not None:
            self.current_mouse_note=note
            self.synth.note_on(note)
            self.draw()
            return
        for ident,box in self.buttons.items():
            if self.inside(x,y,box):
                self.action(ident)
                return
        for ident,(style,x1,y1,x2,y2) in self.controls.items():
            if self.inside(x,y,(x1,y1,x2,y2)):
                self.drag=(ident,style,y,self.synth.get_param(ident))
                if style=="slider":
                    self.apply_slide(ident,y)
                return

    def mouse_move(self,event):
        if self.current_mouse_note is not None:
            x,y=self.coords(event)
            next_note=self.find_note(x,y)
            if next_note != self.current_mouse_note and next_note is not None:
                self.synth.note_off(self.current_mouse_note)
                self.synth.note_on(next_note)
                self.current_mouse_note=next_note
                self.draw()
        if self.drag:
            x,y=self.coords(event)
            ident,style,original_y,start=self.drag
            if style=="slider":
                self.apply_slide(ident,y)
            else:
                self.change(ident,start+(original_y-y)/160)

    def apply_slide(self,ident,y):
        x,y1,y2=self.knob_targets[ident]
        self.change(ident,(y2-y)/max(1,y2-y1))

    def mouse_up(self,event):
        if self.current_mouse_note is not None:
            self.synth.note_off(self.current_mouse_note)
            self.current_mouse_note=None
        if self.drag is not None and self.drag[0]=="pitch_bend":
            self.synth.set_param("pitch_bend",0.5)
        self.drag=None
        self.draw()

    def mouse_wheel(self,event):
        x,y=self.coords(event)
        for ident,(style,x1,y1,x2,y2) in self.controls.items():
            if self.inside(x,y,(x1,y1,x2,y2)):
                self.change(ident,self.synth.get_param(ident)+ (0.02 if event.delta>0 else -0.02))
                return

    def mouse_right(self,event):
        x,y=self.coords(event)
        for ident,(style,x1,y1,x2,y2) in self.controls.items():
            if self.inside(x,y,(x1,y1,x2,y2)):
                menu=tk.Menu(self.root,tearoff=0)
                menu.add_command(label=f"{ident}: {self.synth.get_param(ident):.3f}",state="disabled")
                menu.add_command(label="MIDI Learn — próxima versão",state="disabled")
                menu.add_command(label="Restaurar padrão",command=lambda n=ident:self.change(n,DEFAULTS[n.split("@")[0]]))
                menu.tk_popup(event.x_root,event.y_root)
                return

    def change(self,ident,value):
        if ident.endswith("_octave"):
            value=round(max(0.0,min(1.0,value))*4)/4      # five detented positions
        self.synth.set_param(ident,value)
        ident=ident.split("@")[0]
        self.last_param=ident
        if ident not in ("pitch_bend","modwheel"):
            self.patch_dirty=True
        self.draw()

    def action(self,ident):
        if ident.startswith("wave"):
            _,number,index = ident[0:4],int(ident[4]),int(ident[6])
            self.change(f"osc{number}_wave",index/3)
        elif ident=="settings":
            self.open_settings()
        elif ident=="save":
            self.save_patch()
        elif ident == "browse":
            self.browse_patches()
        elif ident == "load":
            self.load_patch()
        elif ident in ("bank", "category"):
            self.browse_patches(default_bank="Factory" if ident == "bank" else "Todos")
        elif ident=="panic":
            self.panic()
        elif ident=="check_update":
            if self.release:
                self.install_update()
            else:
                self.check_update(manual=True)
        elif ident in ("prev_patch","next_patch"):
            self.cycle_patch(1 if ident=="next_patch" else -1)
        elif ident.startswith("prompt_"):
            if self.pending:
                self.answer_unsaved(ident)
        elif self.pending:
            pass                     # display buttons sit under the prompt
        elif ident in ("display_prev","display_next"):
            self.cycle_patch(1 if ident=="display_next" else -1)
        elif ident=="init":
            self.init_patch()
        self.draw()

    def scan_devices(self):
        try:
            self.audio_devices=[(i,d["name"]) for i,d in enumerate(sd.query_devices()) if d.get("max_output_channels",0)>=2]
        except Exception as exc:
            self.audio_devices=[]
            self.audio_error=str(exc)
        try:
            self.midi_devices=mido.get_input_names()
        except Exception:
            self.midi_devices=[]
        if not self.stream:
            self.open_audio(self.settings.get("audio"))
        if not self.port:
            self.open_midi(self.settings.get("midi"))

    def open_audio(self,desired=None):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream=None
        devices=self.audio_devices
        if not devices:
            return
        selected=next(((i,name) for i,name in devices if name==desired),devices[0])
        i,name=selected
        try:
            try:
                self.stream=sd.OutputStream(device=i,samplerate=self.synth.sample_rate,channels=2,
                                            blocksize=512,callback=self.audio_callback)
            except Exception:
                sr=int(sd.query_devices(i)["default_samplerate"])
                self.synth.sample_rate=sr
                self.stream=sd.OutputStream(device=i,samplerate=sr,channels=2,
                                            blocksize=512,callback=self.audio_callback)
            self.stream.start()
            self.audio_name=name
            self.settings["audio"]=name
            self._save_settings()
            self.audio_error=""
        except Exception as exc:
            self.audio_error=str(exc)
            self.stream=None

    def audio_callback(self,outdata,frames,timing,status):
        started=time.perf_counter()
        try:
            outdata[:]=self.synth.render(frames)
        except Exception:
            outdata.fill(0)
        # Engine load (share of the block's time budget) and scope samples.
        load=(time.perf_counter()-started)*self.synth.sample_rate/max(1,frames)
        self.dsp_load+=(load-self.dsp_load)*0.1
        self.scope_buffer=outdata[:,0].copy()

    def open_midi(self,name=None):
        if self.port:
            try:
                self.port.close()
            except Exception:
                pass
            self.port=None
        if not self.midi_devices:
            return
        name = name if name in self.midi_devices else self.midi_devices[0]
        try:
            self.port=mido.open_input(name,callback=lambda msg:self.events.put(("midi",msg)))
            self.settings["midi"]=name
            self._save_settings()
        except Exception as exc:
            self.last_midi=f"MIDI ERROR: {exc}"

    def watch_midi(self):
        """Reconnect the MIDI controller after hot-plug, or when its port was
        still held by a closing Venus-8 at startup (Windows MIDI is exclusive)."""
        try:
            names=mido.get_input_names()
        except Exception:
            names=[]
        changed=False
        if self.port is not None and getattr(self.port,"name",None) not in names:
            try:
                self.port.close()
            except Exception:
                pass
            self.port=None
            for note in list(self.midi_held):
                self.synth.note_off(note)
            self.midi_held.clear()
            self.last_midi="MIDI: desconectado"
            changed=True
        self.midi_devices=names
        if self.port is None and names:
            saved=self.settings.get("midi")
            target=match_midi_name(saved,names) if saved else names[0]
            if target:
                self.open_midi(target)
                changed=changed or self.port is not None
        if changed:
            self.draw()
        self.root.after(2000,self.watch_midi)

    def release_devices(self):
        """Close MIDI and audio so another Venus-8 process can open them."""
        if self.port:
            try:self.port.close()
            except Exception:pass
            self.port=None
        if self.stream:
            try:self.stream.stop();self.stream.close()
            except Exception:pass
            self.stream=None

    def midi_message(self,msg):
        self.last_midi=f"MIDI: {msg.type}"
        if msg.type=="note_on" and msg.velocity:
            self.synth.note_on(msg.note,msg.velocity)
            self.midi_held.add(msg.note)
        elif msg.type=="note_off" or (msg.type=="note_on" and not msg.velocity):
            self.synth.note_off(msg.note)
            self.midi_held.discard(msg.note)
        elif msg.type=="pitchwheel":
            self.synth.pitch_bend=msg.pitch/8192*2
        elif msg.type=="control_change":
            mapping={1:"modwheel",7:"volume",74:"cutoff",73:"attack",72:"release",91:"delay_mix"}
            if msg.control in mapping:
                ident=mapping[msg.control]
                self.synth.set_param(ident,msg.value/127.0)
                self.last_param=ident
                if ident!="modwheel":
                    self.patch_dirty=True

    def open_settings(self):
        box=tk.Toplevel(self.root)
        box.title("VENUS-8 — Audio e MIDI")
        box.geometry("560x370")
        box.configure(bg=PANEL)
        box.transient(self.root)
        tk.Label(box,text="DISPOSITIVOS DE ÁUDIO E MIDI",bg=PANEL,fg=GOLD,
                 font=("Segoe UI",17,"bold")).pack(pady=14)
        tk.Label(box,text="Interface de saída",bg=PANEL,fg=WHITE).pack()
        audio=ttk.Combobox(box,state="readonly",width=66,values=[name for i,name in self.audio_devices])
        audio.pack(pady=7)
        if self.audio_devices:
            name=self.settings.get("audio")
            audio.current(next((k for k,item in enumerate(self.audio_devices) if item[1]==name),0))
        tk.Label(box,text="Controlador MIDI USB",bg=PANEL,fg=WHITE).pack()
        midi=ttk.Combobox(box,state="readonly",width=66,values=self.midi_devices)
        midi.pack(pady=7)
        if self.midi_devices:
            name=self.settings.get("midi")
            midi.current(self.midi_devices.index(name) if name in self.midi_devices else 0)
        def apply():
            if audio.current()>=0:self.open_audio(self.audio_devices[audio.current()][1])
            if midi.current()>=0:self.open_midi(self.midi_devices[midi.current()])
            box.destroy()
            self.draw()
        def import_reference():
            """Use the original 1600px Venus-8 panel without changing any mappings."""
            filename=filedialog.askopenfilename(parent=box,title="Importar arte oficial do Venus-8",
                      filetypes=[("Imagem PNG", "*.png"),("Imagem JPEG","*.jpg;*.jpeg")])
            if not filename:
                return
            try:
                from PIL import Image
                with Image.open(filename) as img:
                    if img.width < 1500 or img.height < 850:
                        raise ValueError("Escolha a arte original em alta resolução (mínimo 1500 × 850).")
                    if not (1.55 <= img.width/img.height <= 1.80):
                        raise ValueError("A proporção da imagem não corresponde ao painel aprovado.")
                    target=self.patch_dir.parent/"assets"/"venus-8-mockup.png"
                    target.parent.mkdir(parents=True,exist_ok=True)
                    img.convert("RGB").save(target,format="PNG",optimize=True)
                self.mockup=MockupRenderer(self)
                self.draw()
                self.root.after(50,self.mockup.tick)
                messagebox.showinfo("Arte do Venus-8","Arte oficial aplicada. Os controles continuam ativos nas mesmas posições.",parent=box)
            except Exception as exc:
                messagebox.showerror("Importar painel",str(exc),parent=box)

        tk.Button(box,text="IMPORTAR MOCKUP OFICIAL (ALTA RESOLUÇÃO)",
                  command=import_reference).pack(pady=(8,3))
        tk.Label(box,text="Personaliza a aparência; não altera patches nem áudio.",
                 bg=PANEL,fg=FADED).pack()
        row=tk.Frame(box,bg=PANEL);row.pack(pady=14)
        tk.Button(row,text="Reexaminar dispositivos",command=lambda:(self.scan_devices(),box.destroy(),self.open_settings())).pack(side="left",padx=8)
        tk.Button(row,text="Aplicar",command=apply).pack(side="left",padx=8)

    def save_patch(self):
        filename=filedialog.asksaveasfilename(parent=self.root,initialdir=self.patch_dir,
             initialfile=self.patch_name+".json",defaultextension=".json",filetypes=[("Venus Patch","*.json")])
        if not filename:return
        try:
            data={"format":"venus8-patch","schema":2,"name":Path(filename).stem,"category":self.patch_category,"description":self.patch_description,"params":self.synth.snapshot()}
            Path(filename).write_text(json.dumps(data,indent=2),encoding="utf-8")
            self.patch_name=Path(filename).stem
            self.patch_bank="User"
            self.patch_category=self.patch_category if self.patch_category != "Uncategorized" else "User"
            self.patch_identity=("User",str(Path(filename).resolve()))
            self.patch_dirty=False
        except Exception as exc:
            messagebox.showerror("Salvar patch",str(exc),parent=self.root)

    def open_patch(self,path):
        data=json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data,dict):raise ValueError("Invalid patch")
        params=data.get("params")
        if params is None:
            params={k:v for k,v in data.items() if k in DEFAULTS}
            if data.get("wave") in WAVES:params["osc1_wave"]=WAVES.index(data["wave"])/3
        if not isinstance(params,dict):raise ValueError("Invalid patch parameters")
        self.synth.panic()
        # Parameters added after the patch was saved start from their defaults.
        self.synth.load_params({**DEFAULTS,**{k:v for k,v in params.items() if k in DEFAULTS}})
        self.patch_name=str(data.get("name") or Path(path).stem)[:40]
        self.patch_category=str(data.get("category") or "User")
        self.patch_bank="User"
        self.patch_description=str(data.get("description") or "Timbre do usuário")
        self.patch_identity=("User",str(Path(path).resolve()))
        self.patch_dirty=False
        self.draw()

    def load_patch(self):
        filename=filedialog.askopenfilename(parent=self.root,initialdir=self.patch_dir,filetypes=[("Venus Patch","*.json")])
        if not filename:
            return
        entry={"name":Path(filename).stem,"bank":"User","path":Path(filename)}
        if self.patch_dirty:
            self.ask_unsaved({"kind":"patch","entry":entry,"message":f"Abrir: {entry['name']}"})
            return
        self.apply_catalog_entry(entry)

    def catalog(self):
        """Factory programs plus user JSON patches, without altering Factory assets."""
        entries=[]
        for program in factory_programs():
            entries.append({"name":program["name"], "bank":"Factory",
                            "category":program["category"],
                            "description":program["description"],
                            "identity":("Factory",program["name"]),
                            "data":program})
        for path in sorted(self.patch_dir.glob("*.json")):
            try:
                contents=json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(contents,dict):
                    continue
            except (OSError, ValueError):
                continue
            entries.append({"name":str(contents.get("name") or path.stem),
                            "category":str(contents.get("category") or "User"),
                            "bank":"User",
                            "description":str(contents.get("description") or "Timbre do usuário"),
                            "identity":("User",str(path.resolve())), "path":path})
        return entries

    def load_catalog_entry(self,entry):
        """Switch patch, or ask in the display first when there are unsaved edits."""
        if self.patch_dirty:
            self.ask_unsaved({"kind":"patch","entry":entry,
                              "message":f"Trocar para: {entry['name']}"})
            return False
        return self.apply_catalog_entry(entry)

    def apply_catalog_entry(self,entry):
        if entry["bank"] == "Factory":
            self.synth.panic()
            self.synth.load_params(entry["data"]["params"])
            self.patch_name=entry["name"]
            self.patch_bank="Factory"
            self.patch_category=entry["category"]
            self.patch_description=entry["description"]
            self.patch_identity=entry["identity"]
            self.patch_dirty=False
            self.last_param=None
            self.draw()
        else:
            try:
                self.open_patch(entry["path"])
            except (OSError, ValueError, TypeError, KeyError) as exc:
                messagebox.showerror("Abrir patch",str(exc),parent=self.root)
                return False
        return True

    def init_patch(self):
        if self.patch_dirty:
            self.ask_unsaved({"kind":"init","message":"Carregar o timbre inicial (INIT)"})
            return
        self.synth.panic()
        self.synth.load_params(DEFAULTS)
        self.patch_name="Init"
        self.patch_bank="User"
        self.patch_category="Init"
        self.patch_description="Timbre inicial"
        self.patch_identity=("Init","")
        self.patch_dirty=False
        self.last_param=None
        self.draw()

    def ask_unsaved(self,pending):
        """Show the Save / Discard / Keep prompt in the central display."""
        self.pending=pending
        self.draw()

    def answer_unsaved(self,choice):
        pending,self.pending=self.pending,None
        if not pending or choice=="prompt_keep":
            self.draw()
            return
        if choice=="prompt_save":
            self.save_patch()
            if self.patch_dirty:            # save dialog cancelled: ask again
                self.pending=pending
                self.draw()
                return
        self.patch_dirty=False
        if pending["kind"]=="patch":
            self.apply_catalog_entry(pending["entry"])
        elif pending["kind"]=="init":
            self.init_patch()
        elif pending["kind"]=="close":
            self.close(force=True)
            return
        self.draw()

    def browse_patches(self,default_bank="Todos"):
        entries=self.catalog()
        window=tk.Toplevel(self.root)
        window.title("VENUS-8 — Browser de timbres")
        window.configure(bg=PANEL)
        window.geometry("840x525")
        window.minsize(690,425)
        window.transient(self.root)
        bar=tk.Frame(window,bg=PANEL)
        bar.pack(fill="x",padx=15,pady=(16,10))
        tk.Label(bar,text="ANALOG CLASSICS",fg=GOLD,bg=PANEL,
                 font=("Segoe UI",18,"bold")).pack(side="left",padx=(0,24))
        tk.Label(bar,text="Banco",fg=WHITE,bg=PANEL).pack(side="left")
        bank=ttk.Combobox(bar,values=("Todos","Factory","User"),
                          state="readonly",width=11)
        bank.set(default_bank)
        bank.pack(side="left",padx=6)
        tk.Label(bar,text="Categoria",fg=WHITE,bg=PANEL).pack(side="left")
        categories=sorted({x["category"] for x in entries})
        category=ttk.Combobox(bar,values=["Todas"]+categories,
                              state="readonly",width=13)
        category.set("Todas")
        category.pack(side="left",padx=6)
        columns=("bank","category","name")
        table=ttk.Treeview(window,columns=columns,show="headings",selectmode="browse",height=13)
        for key,label,width in (("bank","Banco",110),("category","Categoria",110),("name","Timbre",380)):
            table.heading(key,text=label)
            table.column(key,width=width,anchor="w",stretch=key=="name")
        table.pack(fill="both",expand=True,padx=16)
        desc=tk.StringVar(value="Escolha um timbre Factory ou User.")
        tk.Label(window,textvariable=desc,bg=PANEL,fg=WHITE,
                 wraplength=790,justify="left",anchor="w").pack(fill="x",padx=17,pady=12)
        visible=[]
        def refresh(*unused):
            visible.clear()
            table.delete(*table.get_children())
            for entry in entries:
                if bank.get() != "Todos" and entry["bank"] != bank.get():
                    continue
                if category.get() != "Todas" and entry["category"] != category.get():
                    continue
                visible.append(entry)
                table.insert("", "end", iid=str(len(visible)-1),
                             values=(entry["bank"],entry["category"],entry["name"]))
            for idx,entry in enumerate(visible):
                if entry["identity"] == self.patch_identity:
                    table.selection_set(str(idx))
                    table.see(str(idx))
                    break
            if visible and not table.selection():
                table.selection_set("0")
            show_info()
        def selected_entry():
            selection=table.selection()
            if not selection:
                return None
            return visible[int(selection[0])]
        def show_info(*unused):
            entry=selected_entry()
            desc.set((f"{entry['name']}  •  {entry['bank']} / {entry['category']}\n"
                      f"{entry['description']}") if entry else "Nenhum timbre nesta categoria.")
        def load_current(*unused):
            entry=selected_entry()
            # A pending prompt is answered in the main display, so close the browser.
            if entry and (self.load_catalog_entry(entry) or self.pending):
                window.destroy()
        buttons=tk.Frame(window,bg=PANEL)
        buttons.pack(fill="x",padx=16,pady=(0,15))
        tk.Button(buttons,text="CARREGAR TIMBRE",command=load_current,
                  bg="#b36c3c",fg="white").pack(side="left",padx=4)
        def import_patch():
            window.destroy()
            self.load_patch()
        tk.Button(buttons,text="IMPORTAR JSON",command=import_patch).pack(side="left",padx=8)
        tk.Button(buttons,text="FECHAR",command=window.destroy).pack(side="right")
        bank.bind("<<ComboboxSelected>>",refresh)
        category.bind("<<ComboboxSelected>>",refresh)
        table.bind("<<TreeviewSelect>>",show_info)
        table.bind("<Double-1>",load_current)
        table.bind("<Return>",load_current)
        refresh()

    def cycle_patch(self,direction):
        entries=self.catalog()
        if not entries:
            return
        selected=next((i for i,entry in enumerate(entries)
                       if entry["identity"]==self.patch_identity),-1)
        self.load_catalog_entry(entries[(selected+direction)%len(entries)])

    def panic(self):
        self.synth.panic()
        self.current_mouse_note=None
        self.midi_held.clear()
        self.draw()

    def check_update(self,manual=False):
        if self.updating:return
        self.update_label="VERIFICANDO..."
        self.draw()
        updater.start_check(lambda release,error:self.events.put(("update_check",release,error,manual)))

    def install_update(self):
        release=self.release
        if not release or self.updating:return
        portable=updater.is_portable()
        asset=updater.release_asset(release,portable)
        if not asset:
            messagebox.showwarning("Venus-8","Esta Release não contém um EXE compatível.",parent=self.root)
            return
        msg=(f"Nova versão {release['tag_name']} disponível.\n\n"
             f"Arquivo: {asset['name']}\n"
             f"A atualização baixará e verificará SHA-256 antes de executar.\n"
             f"Os patches e preferências serão preservados.\n\n"
             f"Deseja atualizar?")
        if not messagebox.askyesno("Atualizar Venus-8",msg,parent=self.root):return
        self.updating=True
        self.update_label="DOWNLOAD 0%"
        self.draw()
        def task():
            try:
                tag=release["tag_name"]
                dest=self.patch_dir.parent/"updates"/tag/asset["name"]
                result=updater.download_verified(
                    release,dest,portable,
                    lambda done,total:self.events.put(("update_progress",done,total)))
                self.events.put(("update_ready",result,portable))
            except Exception as exc:
                self.events.put(("update_failed",str(exc)))
        threading.Thread(target=task,daemon=True).start()

    def poll(self):
        dirty=False
        for _ in range(150):
            try:kind,*value=self.events.get_nowait()
            except queue.Empty:break
            if kind=="midi":
                self.midi_message(value[0])
                dirty=True
            elif kind=="update_check":
                rel,error,manual=value
                if rel and updater.is_newer(rel.get("tag_name")) and updater.release_asset(rel,updater.is_portable()):
                    self.release=rel
                    self.update_label="UPDATE "+rel["tag_name"]
                else:
                    self.release=None
                    self.update_label="ATUALIZADO" if not error else "VERIFICAR UPDATE"
                    if manual and error:messagebox.showwarning("Atualização",error,parent=self.root)
                    elif manual:messagebox.showinfo("Venus-8","Você já possui a versão mais recente.",parent=self.root)
                dirty=True
            elif kind=="update_progress":
                done,total=value
                self.update_label=f"DOWNLOAD {100*done//total}%" if total else "BAIXANDO..."
                dirty=True
            elif kind=="update_failed":
                self.updating=False
                self.update_label="TENTAR UPDATE"
                messagebox.showerror("Atualização falhou",value[0],parent=self.root)
                dirty=True
            elif kind=="update_ready":
                path,portable=value
                try:
                    if portable:
                        messagebox.showinfo("Portátil atualizado",
                            "A nova versão será aberta a partir da pasta de atualizações. O EXE antigo não será sobrescrito enquanto estiver em execução.",
                            parent=self.root)
                    # Release the controller first: the new version cannot
                    # open a MIDI port this process still holds.
                    self.release_devices()
                    if portable:
                        updater.run_portable(path)
                    else:
                        updater.run_installer(path)
                    self.close(force=True)
                    return
                except Exception as exc:
                    self.updating=False
                    self.scan_devices()
                    messagebox.showerror("Iniciar atualização",str(exc),parent=self.root)
                dirty=True
        if dirty:self.draw()
        self.root.after(70,self.poll)

    def close(self,force=False):
        if self.patch_dirty and not force:
            self.ask_unsaved({"kind":"close","message":"Fechar o Venus-8"})
            return
        self.release_devices()
        self._save_settings()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    App().run()
