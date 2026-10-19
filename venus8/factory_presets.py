"""Original vintage-analog factory sounds for Venus-8.

These programs are original parameter sets inspired by the broad character of
classic subtractive synthesizers. They are not commercial Moog patch dumps.
"""
from .synth import DEFAULTS

FACTORY_BANK = "Analog Classics"
# Each program lists only deviations from the initial patch. The renderer
# receives a full independent parameter snapshot for reliable patch switching.
PROGRAMS = (
    ("Ladder Bass", "Bass", "Gordo, escuro e encorpado, com dois osciladores.", {
        "osc1_level": 0.94, "osc2_level": 0.80, "osc3_level": 0.18,
        "osc1_wave": 0.0, "osc2_wave": 0.0, "osc3_wave": 0.33,
        "osc2_tune": 0.500, "osc3_tune": 0.460, "sub_level": 0.55,
        "cutoff": 0.27, "resonance": 0.20, "drive": 0.45,
        "attack": 0.008, "decay": 0.25, "sustain": 0.68, "release": 0.14,
        "delay_mix": 0.0, "volume": 0.43,
    }),
    ("Subterranean", "Bass", "Subgrave redondo e grave estável.", {
        "osc1_wave": 1.0, "osc2_wave": 0.33, "osc3_wave": 1.0,
        "osc1_level": 0.80, "osc2_level": 0.19, "osc3_level": 0.04,
        "sub_level": 0.88, "cutoff": 0.21, "drive": 0.16,
        "attack": 0.01, "decay": 0.32, "sustain": 0.85, "release": 0.10,
        "volume": 0.47,
    }),
    ("Funky Filter Bass", "Bass", "Baixo percussivo com filtro ressonante.", {
        "osc1_wave": 0.0, "osc2_wave": 0.33, "osc3_wave": 0.0,
        "osc1_level": 0.87, "osc2_level": 0.47, "osc3_level": 0.05,
        "sub_level": 0.34, "cutoff": 0.42, "resonance": 0.69, "drive": 0.39,
        "attack": 0.003, "decay": 0.15, "sustain": 0.24, "release": 0.11,
        "volume": 0.40,
    }),
    ("Minivintage Lead", "Lead", "Lead agressivo de serras levemente desafinadas.", {
        "osc1_wave": 0.0, "osc2_wave": 0.0, "osc3_wave": 0.33,
        "osc1_level": 0.80, "osc2_level": 0.68, "osc3_level": 0.36,
        "osc2_tune": 0.507, "osc3_tune": 0.493, "sub_level": 0.18,
        "cutoff": 0.68, "resonance": 0.16, "drive": 0.45,
        "attack": 0.005, "decay": 0.12, "sustain": 0.94, "release": 0.17,
        "lfo_rate": 0.25, "lfo_depth": 0.05, "volume": 0.38,
    }),
    ("Searing Solo", "Lead", "Solo cortante, com sustain e vibrato suave.", {
        "osc1_wave": 0.0, "osc2_wave": 0.33, "osc3_wave": 0.0,
        "osc1_level": 0.86, "osc2_level": 0.45, "osc3_level": 0.37,
        "osc2_tune": 0.503, "osc3_tune": 0.497,
        "sub_level": 0.12, "cutoff": 0.75, "drive": 0.58,
        "attack": 0.01, "decay": 0.27, "sustain": 0.82, "release": 0.23,
        "lfo_rate": 0.33, "lfo_depth": 0.11, "delay_mix": 0.12,
        "delay_time": 0.22, "delay_feedback": 0.18, "volume": 0.33,
    }),
    ("Velvet Portamento", "Lead", "Lead macio, ligeiramente modulado; glide futuro.", {
        "osc1_wave": 0.33, "osc2_wave": 1.0, "osc3_wave": 0.0,
        "osc1_level": 0.70, "osc2_level": 0.55, "osc3_level": 0.22,
        "cutoff": 0.47, "resonance": 0.15, "drive": 0.23,
        "attack": 0.04, "decay": 0.31, "sustain": 0.83, "release": 0.37,
        "lfo_rate": 0.27, "lfo_depth": 0.09, "delay_mix": 0.12,
        "volume": 0.40,
    }),
    ("Copper Brass", "Brass", "Metais sintéticos com ataque incisivo.", {
        "osc1_wave": 0.0, "osc2_wave": 0.0, "osc3_wave": 0.33,
        "osc1_level": 0.74, "osc2_level": 0.64, "osc3_level": 0.24,
        "osc2_tune": 0.506, "osc3_tune": 0.494,
        "cutoff": 0.59, "resonance": 0.24, "drive": 0.28,
        "attack": 0.06, "decay": 0.28, "sustain": 0.72, "release": 0.24,
        "volume": 0.39,
    }),
    ("Brass Stab", "Brass", "Stab curto e expressivo.", {
        "osc1_level": 0.78, "osc2_level": 0.70, "osc3_level": 0.14,
        "osc2_wave": 0.33, "osc3_wave": 0.0,
        "cutoff": 0.51, "resonance": 0.17, "drive": 0.36,
        "attack": 0.008, "decay": 0.12, "sustain": 0.22, "release": 0.16,
        "volume": 0.41,
    }),
    ("Solar Poly Pad", "Pad", "Pad macio, lento e com leve batimento dos osciladores.", {
        "osc1_wave": 0.0, "osc2_wave": 0.0, "osc3_wave": 0.66,
        "osc1_level": 0.62, "osc2_level": 0.50, "osc3_level": 0.41,
        "osc2_tune": 0.502, "osc3_tune": 0.498,
        "sub_level": 0.13, "cutoff": 0.44, "resonance": 0.13, "drive": 0.06,
        "attack": 0.42, "decay": 0.58, "sustain": 0.86, "release": 0.67,
        "lfo_rate": 0.16, "lfo_depth": 0.13, "delay_mix": 0.19,
        "delay_time": 0.46, "delay_feedback": 0.32, "volume": 0.47,
    }),
    ("Nebula Strings", "Pad", "Cordas analógicas suaves com cauda longa.", {
        "osc1_wave": 0.0, "osc2_wave": 0.66, "osc3_wave": 0.0,
        "osc1_level": 0.66, "osc2_level": 0.54, "osc3_level": 0.47,
        "osc2_tune": 0.504, "osc3_tune": 0.496,
        "sub_level": 0.09, "cutoff": 0.56, "drive": 0.09,
        "attack": 0.32, "decay": 0.63, "sustain": 0.90, "release": 0.83,
        "lfo_rate": 0.13, "lfo_depth": 0.19,
        "delay_mix": 0.23, "delay_time": 0.40, "delay_feedback": 0.27,
        "volume": 0.37,
    }),
    ("Dreamy Poly", "Pad", "Atmosfera polifônica com delay e filtro fechado.", {
        "osc1_wave": 0.66, "osc2_wave": 0.0, "osc3_wave": 1.0,
        "osc1_level": 0.60, "osc2_level": 0.45, "osc3_level": 0.31,
        "cutoff": 0.37, "resonance": 0.30, "drive": 0.11,
        "attack": 0.56, "decay": 0.58, "sustain": 0.88, "release": 0.76,
        "lfo_rate": 0.18, "lfo_depth": 0.17,
        "delay_mix": 0.31, "delay_time": 0.47, "delay_feedback": 0.38,
        "volume": 0.41,
    }),
    ("Amber Keys", "Keys", "Teclas arredondadas, com envelope percussivo.", {
        "osc1_wave": 0.66, "osc2_wave": 1.0, "osc3_wave": 0.0,
        "osc1_level": 0.74, "osc2_level": 0.28, "osc3_level": 0.10,
        "cutoff": 0.63, "drive": 0.16,
        "attack": 0.004, "decay": 0.24, "sustain": 0.18, "release": 0.30,
        "delay_mix": 0.12, "volume": 0.48,
    }),
    ("Analog Pluck", "Keys", "Pluck seco e brilhante, com decaimento curto.", {
        "osc1_wave": 0.0, "osc2_wave": 0.33, "osc3_wave": 1.0,
        "osc1_level": 0.63, "osc2_level": 0.41, "osc3_level": 0.21,
        "cutoff": 0.72, "resonance": 0.38, "drive": 0.20,
        "attack": 0.003, "decay": 0.08, "sustain": 0.05, "release": 0.09,
        "delay_mix": 0.20, "delay_time": 0.21, "delay_feedback": 0.18,
        "volume": 0.48,
    }),
    ("Space Beacons", "FX", "Pulsos espaciais, modulação e ecos.", {
        "osc1_wave": 0.0, "osc2_wave": 0.33, "osc3_wave": 0.0,
        "osc1_level": 0.63, "osc2_level": 0.37, "osc3_level": 0.30,
        "noise_level": 0.18, "cutoff": 0.36, "resonance": 0.65,
        "drive": 0.34, "attack": 0.05, "decay": 0.44,
        "sustain": 0.40, "release": 0.66,
        "lfo_rate": 0.72, "lfo_depth": 0.49,
        "delay_mix": 0.38, "delay_time": 0.71,
        "delay_feedback": 0.55, "volume": 0.28,
    }),
)


def factory_programs():
    """Return separate mutable patch data; never share DEFAULTS with callers."""
    result = []
    for name, category, description, overrides in PROGRAMS:
        params = dict(DEFAULTS)
        params.update(overrides)
        result.append({
            "name": name, "category": category, "description": description,
            "bank": "Factory", "author": "Venus-8",
            "format": "venus8-patch", "schema": 2, "params": params,
        })
    return result


def find_factory(name):
    return next((p for p in factory_programs() if p["name"] == name), None)
