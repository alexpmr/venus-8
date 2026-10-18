"""VENUS-8 graphical workbench. Control surfaces are shown even when DSP is pending."""
import json
import math
import os
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import mido
import psutil
import sounddevice as sd

from . import __version__
from .synth import DEFAULTS, WAVES, Synth
from . import updater

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
    ("OSCILLATOR 1", 35, 93, 265, 335),
    ("OSCILLATOR 2", 270, 93, 500, 335),
    ("OSCILLATOR 3", 505, 93, 735, 335),
    ("MIXER", 740, 93, 980, 335),
    ("FILTER", 985, 93, 1225, 335),
    ("AMP ENV", 1230, 93, 1385, 335),
    ("FILTER ENV", 1390, 93, 1565, 335),
    ("LFO 1", 35, 345, 272, 550),
    ("LFO 2", 277, 345, 514, 550),
    ("DISPLAY / PATCH", 519, 345, 1080, 550),
    ("MODULATION MATRIX", 1085, 345, 1565, 550),
    ("ARPEGGIATOR", 35, 560, 285, 737),
    ("STEP SEQUENCER", 290, 560, 745, 737),
    ("EFFECTS", 750, 560, 1350, 737),
    ("MASTER", 1355, 560, 1565, 737),
    ("PERFORMANCE", 35, 747, 1565, 818),
]


class App:
    def __init__(self):
        self.root = tk.Tk()
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
        self.patch_name = "INIT ANALOG"
        self.patch_dirty = False
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
        self.scan_devices()
        self.root.after(40, self.poll)
        self.root.after(1200, self.check_update)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.draw()

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
        self.rect(x1, y1, x2, y2, PANEL, EDGE)
        self.rect(x1 + 2, y1 + 2, x2 - 2, y1 + 32, "#ae5e32")
        self.text((x1 + x2) / 2, y1 + 18, name, 13, "#0d1015", bold=True)

    def button(self, ident, title, x1, y1, x2, y2, enabled=True, selected=False):
        color = ORANGE if selected else (PANEL2 if enabled else "#14191f")
        ink = "#15171b" if selected else (WHITE if enabled else FADED)
        self.rect(x1, y1, x2, y2, color, "#565354" if enabled else "#32363b")
        self.text((x1 + x2) / 2, (y1 + y2) / 2, title, 11, ink, bold=True)
        if enabled:
            self.buttons[ident] = (x1, y1, x2, y2)

    def knob(self, ident, caption, x, y, radius=25, enabled=True):
        val = self.synth.params.get(ident, 0.5)
        if not enabled:
            val = 0.5
        ink = ORANGE if enabled else "#505865"
        p = self.bounds(x-radius, y-radius, x+radius, y+radius)
        self.canvas.create_oval(*p, fill="#090c11", outline=ink, width=self.s(2))
        ang = math.radians(225 + 270 * val)
        px = x + radius * 0.73 * math.cos(ang)
        py = y + radius * 0.73 * math.sin(ang)
        self.line(x, y, px, py, fill=ink, width=3)
        self.text(x, y+radius+16, caption, 11, WHITE if enabled else FADED)
        if enabled:
            self.controls[ident] = ("knob", x-radius-8, y-radius-8, x+radius+8, y+radius+9)
            self.knob_targets[ident] = (x, y)

    def slider(self, ident, title, x, y1, y2, enabled=True):
        val = self.synth.params.get(ident, 0.50) if enabled else 0.5
        self.rect(x-5, y1, x+5, y2, "#090b0f", "#4b4f56")
        pos = y2 - (y2 - y1) * val
        self.rect(x-15, pos-6, x+15, pos+6, ORANGE if enabled else "#666a72")
        self.text(x, y2+18, title, 10, WHITE if enabled else FADED)
        if enabled:
            self.controls[ident] = ("slider", x-22, y1-10, x+22, y2+12)
            self.knob_targets[ident] = (x, y1, y2)

    def draw(self):
        w, h = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        self.scale = min(w / BASE_W, h / BASE_H)
        self.offset = ((w - BASE_W * self.scale) / 2, (h - BASE_H * self.scale) / 2)
        self.controls.clear()
        self.buttons.clear()
        self.knob_targets.clear()
        self.canvas.delete("all")
        self.rect(0, 0, 1600, 980, "#0b0e12")
        self.rect(0, 0, 24, 979, "#77472a")
        self.rect(1576, 0, 1599, 979, "#77472a")
        self.rect(26, 2, 1574, 85, "#131820", EDGE)
        self.text(48, 33, "VENUS", 36, WHITE, "w", True)
        self.text(201, 33, "-8", 36, ORANGE, "w", True)
        self.text(50, 69, "VIRTUAL ANALOG SYNTHESIZER", 12, "#9ea6b1", "w")
        self.rect(440, 13, 855, 71, "#080f1c", "#49505b")
        self.text(647, 33, self.patch_name, 20, GOLD, bold=True)
        self.text(647, 55, f"USER PATCH  •  v{__version__}", 11, FADED)
        self.button("prev_patch", "◀", 405, 18, 438, 67)
        self.button("next_patch", "▶", 857, 18, 892, 67)
        self.button("save", "SAVE", 909, 22, 985, 62)
        self.button("load", "LOAD", 989, 22, 1064, 62)
        self.button("settings", "AUDIO / MIDI", 1069, 22, 1191, 62)
        self.button("check_update", self.update_label, 1195, 22, 1358, 62, selected=bool(self.release))
        self.button("panic", "PANIC", 1365, 22, 1446, 62)
        self.text(1550, 28, f"CPU {self.cpu_text}", 12, GREEN, "e")
        self.text(1550, 51, f"RAM {self.ram_text}  •  {self.voices_text}", 11, GOLD, "e")

        for sec in SECTIONS:
            self.panel(*sec)
        # Three oscillators with usable wave, tune and levels.
        for i, x in enumerate((35, 270, 505), 1):
            ox = x + 115
            for j, shape in enumerate(WAVES):
                ident = f"wave{i}_{j}"
                self.button(ident, shape.upper()[:3], x+10+j*55, 135,
                            x+61+j*55, 167, selected=(round(self.synth.get_param(f"osc{i}_wave")*3)==j))
            self.knob(f"osc{i}_tune", "TUNE ±12", x+66, 232, 26)
            self.knob(f"osc{i}_level", "LEVEL", x+167, 232, 26)
            self.button(f"sync{i}", "SYNC", x+16, 288, x+82, 319, enabled=False)
            self.button(f"fm{i}", "FM", x+91, 288, x+148, 319, enabled=False)
            self.button(f"ring{i}", "RING", x+156, 288, x+220, 319, enabled=False)
        for ident, label, x in [
            ("osc1_level","OSC1",784),("osc2_level","OSC2",826),
            ("osc3_level","OSC3",868),("sub_level","SUB",910),("noise_level","NOISE",952)
        ]:
            self.slider(ident,label,x,155,284)
        self.text(857,310,"MIXER / LEVELS",11,FADED)
        self.button("filter_type","LOW PASS 24 dB",1000,137,1210,170,enabled=False)
        self.knob("cutoff","CUTOFF",1041,237,31)
        self.knob("drive","DRIVE",1133,237,26)
        self.knob("resonance","RESO • SOON",1185,306,15,enabled=False)
        for ident, name, x in [
            ("attack","A",1252),("decay","D",1290),("sustain","S",1328),("release","R",1365)
        ]:
            self.slider(ident,name,x,152,284,enabled=ident in ("attack","release"))
        for title, x in [("A",1415),("D",1456),("S",1497),("R",1538)]:
            self.slider("_filter_env_"+title,title,x,152,284,enabled=False)
        # Modulation / display.
        self.knob("lfo_rate","RATE",100,450)
        self.knob("lfo_depth","DEPTH",204,450)
        self.button("lfo_wave","SINE",75,503,231,535,enabled=False)
        self.knob("lfo2_rate","RATE",348,450,enabled=False)
        self.knob("lfo2_depth","DEPTH",448,450,enabled=False)
        self.button("lfo2_wave","FUTURE ENGINE",310,503,480,535,enabled=False)
        self.rect(531,382,1067,535,"#101726","#364552")
        for j in range(35):
            fraction = j / 35
            self.line(536,387+j*4.1,1062,387+j*4.1,fill=f"#{int(12+17*fraction):02x}{int(22+16*fraction):02x}{int(41+18*fraction):02x}")
        self.canvas.create_oval(*self.bounds(706,400,875,528),fill="#9a562f",outline="#d48342",width=self.s(2))
        self.text(800,420,"VENUS-8",23,GOLD,bold=True)
        self.text(800,455,self.patch_name,18,WHITE,bold=True)
        self.text(800,482,"ANALOG WORKBENCH",12,WHITE)
        self.text(800,512,"ENABLED CONTROLS = AMBER   |   FUTURE = GREY",10,FADED)
        for i,(source,dest) in enumerate([
            ("LFO 1","FILTER CUTOFF"),("MOD WHEEL","FILTER RESO"),
            ("ENV 2","OSC PWM"),("AFTERTOUCH","FILTER"),
            ("VELOCITY","AMP LEVEL"),("LFO 2","CHORUS"),
        ]):
            y=390+i*25
            self.text(1108,y,str(i+1),10,FADED,anchor="w")
            self.text(1133,y,source,11,FADED,anchor="w")
            self.text(1320,y,dest,11,FADED,anchor="w")
            self.text(1518,y,"SOON",10,FADED)
        # Arpeggiator and step sequencer remain deliberately disabled.
        self.button("arp_on","ON",52,609,124,645,enabled=False)
        self.button("arp_mode","UP / DOWN",134,609,268,645,enabled=False)
        self.knob("arp_rate","RATE",98,690,enabled=False)
        self.knob("arp_gate","GATE",208,690,enabled=False)
        for i in range(16):
            x=311+i*25.7
            self.button(f"step{i}",str(i+1),x,648,x+23,681,enabled=False)
        self.text(515,615,"16-STEP SEQUENCER  •  EM BREVE",12,FADED)
        self.text(515,702,"PLAY     STOP     GATE     SWING",12,FADED)
        for name,x in [("CHORUS",760),("PHASER",907),("DELAY",1052),("REVERB",1198)]:
            self.rect(x,599,x+144,728,PANEL2,EDGE)
            self.text(x+72,614,name,12,ORANGE if name=="DELAY" else FADED,bold=True)
            if name=="DELAY":
                self.knob("delay_mix","MIX",x+40,666,20)
                self.knob("delay_time","TIME",x+106,666,20)
                self.slider("delay_feedback","FB",x+72,642,683)
            else:
                self.knob("_fx_"+name,"EM BREVE",x+72,671,23,enabled=False)
        self.knob("volume","VOLUME",1420,661,32)
        self.text(1501,618,"MASTER",13,WHITE)
        barx = 1503
        peak = self.synth.peak
        for i in range(10):
            v = (10-i)/10
            self.rect(barx,635+i*8,barx+15,641+i*8, GREEN if peak>=v else "#2e373b")
        self.text(1530,710,f"{peak*100:.0f}%",11,GREEN)
        # Performance strip.
        self.button("poly","POLY",51,775,121,804,selected=True)
        self.button("mono","MONO",128,775,199,804,enabled=False)
        self.button("legato","LEGATO",206,775,293,804,enabled=False)
        self.button("unison","UNISON",300,775,385,804,enabled=False)
        self.text(490,790,"PITCH BEND  ±2",12,WHITE)
        self.slider("pitch_bend","",590,770,800)
        self.text(719,790,"MOD WHEEL",12,WHITE)
        self.slider("modwheel","",812,770,800)
        self.text(1048,791,self.last_midi,12,GREEN)
        self.text(1498,790,f"VOICES: {len(self.synth.voices)}/{self.synth.max_voices}",12,GOLD,anchor="e")
        self.draw_keyboard()

    def draw_keyboard(self):
        self.rect(35,826,1565,968,"#101214","#554e49")
        self.keys.clear()
        white = [n for n in range(48,97) if n % 12 in (0,2,4,5,7,9,11)]
        width = 1514 / len(white)
        for i,n in enumerate(white):
            x=43+i*width
            active=n in self.midi_held or n==self.current_mouse_note
            self.rect(x,835,x+width-1,959,GOLD if active else "#eee7d9","#1a1c20")
            self.keys.append((n,x,835,x+width-1,959))
        for i,n in enumerate(white):
            if n%12 in (4,11) or n+1>96:
                continue
            x=43+(i+1)*width-width*.31
            note=n+1
            active=note in self.midi_held or note==self.current_mouse_note
            self.rect(x,835,x+width*.62,913,ORANGE if active else "#101317","#30343a")
            self.keys.append((note,x,835,x+width*.62,913))

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
                menu.add_command(label="Restaurar padrão",command=lambda n=ident:self.change(n,DEFAULTS[n]))
                menu.tk_popup(event.x_root,event.y_root)
                return

    def change(self,ident,value):
        self.synth.set_param(ident,value)
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
        elif ident=="load":
            self.load_patch()
        elif ident=="panic":
            self.panic()
        elif ident=="check_update":
            if self.release:
                self.install_update()
            else:
                self.check_update(manual=True)
        elif ident in ("prev_patch","next_patch"):
            self.cycle_patch(1 if ident=="next_patch" else -1)
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
            self.settings["audio"]=name
            self._save_settings()
            self.audio_error=""
        except Exception as exc:
            self.audio_error=str(exc)
            self.stream=None

    def audio_callback(self,outdata,frames,timing,status):
        try:
            outdata[:]=self.synth.render(frames)
        except Exception:
            outdata.fill(0)

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
                self.synth.set_param(mapping[msg.control],msg.value/127.0)

    def open_settings(self):
        box=tk.Toplevel(self.root)
        box.title("VENUS-8 — Audio e MIDI")
        box.geometry("530x300")
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
        row=tk.Frame(box,bg=PANEL);row.pack(pady=14)
        tk.Button(row,text="Reexaminar dispositivos",command=lambda:(self.scan_devices(),box.destroy(),self.open_settings())).pack(side="left",padx=8)
        tk.Button(row,text="Aplicar",command=apply).pack(side="left",padx=8)

    def save_patch(self):
        filename=filedialog.asksaveasfilename(parent=self.root,initialdir=self.patch_dir,
             initialfile=self.patch_name+".json",defaultextension=".json",filetypes=[("Venus Patch","*.json")])
        if not filename:return
        try:
            data={"format":"venus8-patch","schema":2,"name":Path(filename).stem,"params":self.synth.snapshot()}
            Path(filename).write_text(json.dumps(data,indent=2),encoding="utf-8")
            self.patch_name=Path(filename).stem
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
        self.synth.load_params(params)
        self.patch_name=str(data.get("name") or Path(path).stem)[:40]
        self.patch_dirty=False
        self.draw()

    def load_patch(self):
        filename=filedialog.askopenfilename(parent=self.root,initialdir=self.patch_dir,filetypes=[("Venus Patch","*.json")])
        if filename:
            try:self.open_patch(filename)
            except Exception as exc:messagebox.showerror("Abrir patch",str(exc),parent=self.root)

    def cycle_patch(self,direction):
        paths=sorted(self.patch_dir.glob("*.json"))
        if not paths:return
        names=[p.stem for p in paths]
        i=names.index(self.patch_name) if self.patch_name in names else -1
        self.open_patch(paths[(i+direction)%len(paths)])

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
                        updater.run_portable(path)
                    else:
                        updater.run_installer(path)
                    self.close()
                    return
                except Exception as exc:
                    self.updating=False
                    messagebox.showerror("Iniciar atualização",str(exc),parent=self.root)
                dirty=True
        if dirty:self.draw()
        self.root.after(70,self.poll)

    def close(self):
        if self.port:
            try:self.port.close()
            except Exception:pass
        if self.stream:
            try:self.stream.stop();self.stream.close()
            except Exception:pass
        self._save_settings()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    App().run()
