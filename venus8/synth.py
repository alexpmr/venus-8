import math
import numpy as np

class Synth:
    def __init__(self, sample_rate=44100, max_voices=16):
        self.sample_rate=sample_rate
        self.max_voices=max_voices
        self.voices={}
        self.waveform='Saw'
        self.volume=0.2
        self.cutoff=0.6
        self.pitch_bend=0.0

    def note_on(self,note,velocity=100):
        if len(self.voices)>=self.max_voices and note not in self.voices:
            self.voices.pop(next(iter(self.voices)))
        self.voices[int(note)]={'phase':0.0,'velocity':max(0,min(127,velocity))/127.0}

    def note_off(self,note):
        self.voices.pop(int(note),None)

    def panic(self):
        self.voices.clear()

    def render(self,frames):
        out=np.zeros(frames,dtype=np.float32)
        for note,v in list(self.voices.items()):
            freq=440.0*2**((note-69+self.pitch_bend)/12)
            ph=(v['phase']+np.arange(frames)*freq/self.sample_rate)%1.0
            if self.waveform=='Sine': x=np.sin(2*np.pi*ph)
            elif self.waveform=='Triangle': x=1-4*np.abs(ph-0.5)
            elif self.waveform=='Square': x=np.where(ph<0.5,1.0,-1.0)
            else: x=2*ph-1
            out+=x.astype(np.float32)*v['velocity']
            v['phase']=float((v['phase']+frames*freq/self.sample_rate)%1.0)
        out *= self.volume / max(1, len(self.voices))
        return np.column_stack((out,out))
