import unittest
import numpy as np

from venus8.factory_presets import PROGRAMS, factory_programs, find_factory
from venus8.synth import Synth, DEFAULTS


class FactoryPresetsTest(unittest.TestCase):
    def test_distinct_programs_and_categories(self):
        programs=factory_programs()
        self.assertGreaterEqual(len(programs), 12)
        self.assertEqual(len({p["name"] for p in programs}),len(programs))
        self.assertTrue({"Bass","Lead","Brass","Pad","Keys","FX"}.issubset(
            {p["category"] for p in programs}))
        for patch in programs:
            self.assertEqual(patch["bank"],"Factory")
            self.assertEqual(set(patch["params"]),set(DEFAULTS))
            self.assertTrue(all(0.0<=v<=1.0 for v in patch["params"].values()))
            self.assertGreater(len(patch["description"]),5)

    def test_snapshots_are_independent(self):
        programs=factory_programs()
        old=programs[0]["params"]["cutoff"]
        programs[0]["params"]["cutoff"]=0.99
        self.assertEqual(find_factory(programs[0]["name"])["params"]["cutoff"],old)

    def test_factory_patches_generate_distinct_audible_signals(self):
        signals=[]
        for p in factory_programs():
            synth=Synth()
            synth.load_params(p["params"])
            synth.note_on(48)
            audio=synth.render(3072)
            self.assertEqual(audio.shape,(3072,2))
            self.assertTrue(np.isfinite(audio).all(),p["name"])
            self.assertGreater(float(np.max(np.abs(audio))),0.00001,p["name"])
            signals.append(np.round(audio[:,0],4))
        self.assertGreater(len({signal.tobytes() for signal in signals}),10)

    def test_full_amp_adsr_and_filter_resonance(self):
        synth=Synth()
        synth.set_param("attack",0.003)
        synth.set_param("decay",0.02)
        synth.set_param("sustain",0.10)
        synth.note_on(60)
        synth.render(4096)
        self.assertAlmostEqual(synth.voices[60]["level"],0.10,delta=0.025)
        synth.note_off(60)
        for _ in range(300):
            synth.render(512)
            if 60 not in synth.voices:
                break
        self.assertNotIn(60,synth.voices)
        def render_at(reso):
            s=Synth()
            s.set_param("resonance",reso)
            s.note_on(57)
            return s.render(2048)
        self.assertGreater(float(np.max(np.abs(render_at(0.9)-render_at(0.1)))),1e-6)


if __name__=="__main__":
    unittest.main()
