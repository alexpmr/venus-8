import unittest
from venus8.synth import Synth

class TestSynth(unittest.TestCase):
 def test_notes(self):
  s=Synth();s.note_on(60);self.assertEqual(len(s.voices),1);self.assertEqual(s.render(128).shape,(128,2));s.note_off(60);self.assertFalse(s.voices)
 def test_panic(self):
  s=Synth();s.note_on(60);s.note_on(64);s.panic();self.assertEqual(len(s.voices),0)
 def test_waves(self):
  s=Synth();s.note_on(69)
  for wave in ('Sine','Saw','Triangle','Square'):
   s.waveform=wave;self.assertEqual(s.render(100).shape,(100,2))
