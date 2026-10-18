import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json, threading, time
import sounddevice as sd
import mido
import psutil
from .synth import Synth

BG='#161b21'; PANEL='#283039'; AMBER='#f8bb64'; FG='#eee5d3'

class App:
 def __init__(self):
  self.root=tk.Tk(); self.root.title('VENUS-8 v0.1.0'); self.root.geometry('1360x770'); self.root.configure(bg=BG)
  self.synth=Synth(); self.stream=None; self.port=None; self.device_names=[]
  self.draw(); self.open_audio(); self.root.after(800,self.status_tick); self.root.protocol('WM_DELETE_WINDOW',self.close)

 def label(self,parent,text,size=11,color=FG):
  return tk.Label(parent,text=text,font=('Segoe UI',size,'bold'),bg=PANEL,fg=color)

 def draw(self):
  top=tk.Frame(self.root,bg='#101418',height=72); top.pack(fill='x')
  tk.Label(top,text='VENUS-8',font=('Segoe UI',30,'bold'),fg=AMBER,bg='#101418').pack(side='left',padx=28)
  tk.Label(top,text='VIRTUAL ANALOG SYNTHESIZER  •  v0.1.0',fg='#a5afb9',bg='#101418').pack(side='left')
  self.status=tk.Label(top,text='CPU --  RAM --  VOICES 0/16',fg='#a8d9bc',bg='#101418',font=('Segoe UI',10)); self.status.pack(side='right',padx=20)
  main=tk.Frame(self.root,bg=BG);main.pack(fill='both',expand=True,padx=12,pady=12)
  osc=tk.LabelFrame(main,text='  OSCILLATOR  ',fg=AMBER,bg=PANEL,bd=1,font=('Segoe UI',11,'bold'));osc.pack(side='left',fill='both',expand=True,padx=5)
  self.wave=tk.StringVar(value='Saw')
  for w in ('Saw','Sine','Triangle','Square'): tk.Radiobutton(osc,text=w,variable=self.wave,value=w,command=self.update_wave,bg=PANEL,fg=FG,selectcolor=BG,activebackground=PANEL,activeforeground=AMBER).pack(anchor='w',padx=22,pady=8)
  fl=tk.LabelFrame(main,text='  FILTER & AMP  ',fg=AMBER,bg=PANEL,font=('Segoe UI',11,'bold'));fl.pack(side='left',fill='both',expand=True,padx=5)
  for title,val,cb in [('FILTER CUTOFF',0.6,self.set_cutoff),('MASTER VOLUME',0.2,self.set_volume)]:
   self.label(fl,title,10,AMBER).pack(pady=(25,2));s=tk.Scale(fl,from_=0.0,to=1.0,resolution=.01,orient='horizontal',length=280,bg=PANEL,fg=FG,highlightthickness=0,command=cb);s.set(val);s.pack(pady=4)
  out=tk.LabelFrame(main,text='  AUDIO / MIDI / PATCH  ',fg=AMBER,bg=PANEL,font=('Segoe UI',11,'bold'));out.pack(side='left',fill='both',expand=True,padx=5)
  self.label(out,'AUDIO OUTPUT',10,AMBER).pack(pady=(22,2));self.audio_box=ttk.Combobox(out,state='readonly',width=37);self.audio_box.pack();self.audio_box.bind('<<ComboboxSelected>>',lambda e:self.open_audio())
  self.label(out,'MIDI INPUT',10,AMBER).pack(pady=(24,2));self.midi_box=ttk.Combobox(out,state='readonly',width=37);self.midi_box.pack();self.midi_box.bind('<<ComboboxSelected>>',lambda e:self.open_midi())
  tk.Button(out,text='SCAN DEVICES',command=self.scan).pack(pady=12)
  row=tk.Frame(out,bg=PANEL);row.pack(pady=18)
  for text,fn in [('SAVE',self.save),('LOAD',self.load),('PANIC',self.panic)]:tk.Button(row,text=text,width=9,command=fn).pack(side='left',padx=5)
  self.scan()
  bottom=tk.Frame(self.root,bg='#11161a');bottom.pack(fill='x',side='bottom',padx=12,pady=12)
  self.keys=[];self.canvas=tk.Canvas(bottom,height=218,bg='#101418',highlightthickness=0);self.canvas.pack(fill='x',expand=True)
  self.canvas.bind('<Configure>',self.draw_keys)
  self.canvas.bind('<ButtonPress-1>',self.key_down);self.canvas.bind('<ButtonRelease-1>',self.key_up)
  self.current_note=None

 def draw_keys(self,event=None):
  c=self.canvas;c.delete('all');self.keys=[];width=max(1,c.winfo_width());white_notes=[n for n in range(48,97) if n%12 in (0,2,4,5,7,9,11)];ww=width/len(white_notes)
  for i,n in enumerate(white_notes):
   x=i*ww;item=c.create_rectangle(x,0,x+ww-1,214,fill='#fff2d9',outline='#202020',tags=('key',));self.keys.append((item,n))
  for i,n in enumerate(white_notes):
   if n%12 in (4,11):continue
   x=(i+1)*ww-ww*.31; bn=n+1
   if bn>96:continue
   item=c.create_rectangle(x,0,x+ww*.62,130,fill='#15171a',outline='#333',tags=('key',));self.keys.append((item,bn))

 def key_down(self,e):
  items=self.canvas.find_overlapping(e.x,e.y,e.x,e.y)
  for item,n in reversed(self.keys):
   if item in items:self.current_note=n;self.synth.note_on(n);self.canvas.itemconfigure(item,fill=AMBER);break

 def key_up(self,e):
  if self.current_note is not None:self.synth.note_off(self.current_note);self.current_note=None;self.draw_keys()

 def set_cutoff(self,v):self.synth.cutoff=float(v)
 def set_volume(self,v):self.synth.volume=float(v)
 def update_wave(self):self.synth.waveform=self.wave.get()
 def scan(self):
  self.audio_devices=[(i,d['name']) for i,d in enumerate(sd.query_devices()) if d['max_output_channels']>=2]
  self.audio_box['values']=[n for _,n in self.audio_devices]
  if self.audio_devices:self.audio_box.current(0)
  try:self.midi_devices=mido.get_input_names()
  except Exception:self.midi_devices=[]
  self.midi_box['values']=self.midi_devices
  if self.midi_devices:self.midi_box.current(0);self.open_midi()

 def open_audio(self):
  try:
   if self.stream:self.stream.stop();self.stream.close()
   ix=self.audio_box.current();dev=self.audio_devices[ix][0] if ix>=0 else None
   self.stream=sd.OutputStream(device=dev,samplerate=44100,channels=2,blocksize=512,callback=self.callback);self.stream.start()
  except Exception as ex: self.stream=None;print('Audio:',ex)

 def callback(self,outdata,frames,t,status):
  outdata[:]=self.synth.render(frames)

 def open_midi(self):
  if self.port:self.port.close();self.port=None
  ix=self.midi_box.current()
  if ix<0:return
  try:self.port=mido.open_input(self.midi_devices[ix],callback=self.midi_event)
  except Exception as ex:print('MIDI:',ex)

 def midi_event(self,msg):
  if msg.type=='note_on' and msg.velocity:self.synth.note_on(msg.note,msg.velocity)
  elif msg.type=='note_off' or (msg.type=='note_on' and not msg.velocity):self.synth.note_off(msg.note)
  elif msg.type=='pitchwheel':self.synth.pitch_bend=msg.pitch/8192*2
  elif msg.type=='control_change':
   if msg.control==7:self.synth.volume=msg.value/127
   if msg.control==74:self.synth.cutoff=msg.value/127

 def save(self):
  path=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('Venus patch','*.json')]);
  if path:
   with open(path,'w',encoding='utf-8') as f:json.dump({'version':1,'wave':self.synth.waveform,'volume':self.synth.volume,'cutoff':self.synth.cutoff},f,indent=2)

 def load(self):
  path=filedialog.askopenfilename(filetypes=[('Venus patch','*.json')]);
  if path:
   try:
    with open(path,encoding='utf-8') as f:d=json.load(f)
    self.synth.waveform=d['wave'];self.synth.volume=float(d['volume']);self.synth.cutoff=float(d['cutoff']);self.wave.set(self.synth.waveform)
   except Exception as ex:messagebox.showerror('Patch',str(ex))

 def panic(self):self.synth.panic();self.draw_keys()
 def status_tick(self):
  p=psutil.Process();self.status.configure(text=f'CPU {p.cpu_percent():.1f}%   RAM {p.memory_info().rss/1048576:.0f} MB   VOZES {len(self.synth.voices)}/16');self.root.after(800,self.status_tick)
 def close(self):
  if self.port:self.port.close()
  if self.stream:self.stream.stop();self.stream.close()
  self.root.destroy()
 def run(self):self.root.mainloop()

def main():App().run()
