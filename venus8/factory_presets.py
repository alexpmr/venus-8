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


# ---- Expanded library (v0.2.16): built only from parameters the engine has.
# octave 0.25/0.75/1.0 = -1/+1/+2; tune 0.5 + semitones/24; fine 0.5 ± cents/100.
FIFTH = 0.5 + 7 / 24


def drawbars(registration):
    """Classic registration string ("888000000") with the oscillators silenced."""
    values = {f"drawbar{i + 1}": int(digit) / 8 for i, digit in enumerate(registration)}
    values.update(osc1_level=0.0, osc2_level=0.0, osc3_level=0.0, sub_level=0.0,
                  noise_level=0.0, cutoff=1.0, resonance=0.0)
    return values


def organ(perc="", click=False, vibrato="", leslie=""):
    """Organ switches in words: perc "second"/"third" (+ " fast"), vibrato
    "vibrato"/"chorus", leslie "slow"/"fast"."""
    return dict(organ_perc=float(bool(perc)), organ_perc_third=float("third" in perc),
                organ_perc_fast=float("fast" in perc), organ_click=float(click),
                organ_vibrato=float(bool(vibrato)), organ_chorus=float(vibrato == "chorus"),
                leslie=float(bool(leslie)), leslie_fast=float(leslie == "fast"))


def electric_piano(tone, bark, decay):
    """Tine electric piano layer with the analog oscillators and filter out."""
    return dict(ep_level=1.0, ep_tone=tone, ep_bark=bark, ep_decay=decay,
                osc1_level=0.0, osc2_level=0.0, osc3_level=0.0, sub_level=0.0,
                noise_level=0.0, cutoff=1.0, resonance=0.0, drive=0.0,
                attack=0.0, decay=0.3, sustain=1.0, release=0.12)


MORE_PROGRAMS = (
    # Strings
    ("Velvet Ensemble", "Strings", "Cordas de serras desafinadas, ataque lento e vibrato.", {
        "osc1_level": 0.62, "osc2_level": 0.58, "osc3_level": 0.40,
        "osc2_fine": 0.42, "osc3_fine": 0.58, "osc3_octave": 0.75,
        "cutoff": 0.55, "resonance": 0.08, "drive": 0.05,
        "attack": 0.45, "decay": 0.60, "sustain": 0.92, "release": 0.62,
        "lfo2_rate": 0.42, "lfo2_depth": 0.12, "delay_mix": 0.18, "delay_time": 0.42,
        "delay_feedback": 0.30, "volume": 0.36,
    }),
    ("Chamber Strings", "Strings", "Seção pequena, mais escura e íntima.", {
        "osc1_level": 0.66, "osc2_level": 0.52, "osc3_level": 0.0,
        "osc2_fine": 0.45, "cutoff": 0.42, "drive": 0.04,
        "attack": 0.34, "decay": 0.55, "sustain": 0.90, "release": 0.50,
        "lfo2_rate": 0.40, "lfo2_depth": 0.10, "volume": 0.40,
    }),
    ("Octave Strings", "Strings", "Cordas em oitavas, largas e brilhantes.", {
        "osc1_level": 0.58, "osc2_level": 0.50, "osc3_level": 0.44,
        "osc2_octave": 0.75, "osc3_octave": 0.25, "osc2_fine": 0.46, "osc3_fine": 0.54,
        "cutoff": 0.62, "attack": 0.38, "decay": 0.6, "sustain": 0.94, "release": 0.66,
        "lfo2_rate": 0.45, "lfo2_depth": 0.10, "delay_mix": 0.22, "delay_time": 0.5,
        "delay_feedback": 0.35, "volume": 0.34,
    }),
    ("Pizzicato", "Strings", "Cordas pinçadas curtas.", {
        "osc1_level": 0.70, "osc2_level": 0.40, "osc3_level": 0.0, "osc2_fine": 0.46,
        "cutoff": 0.48, "resonance": 0.18, "attack": 0.002, "decay": 0.16,
        "sustain": 0.0, "release": 0.14, "delay_mix": 0.12, "volume": 0.50,
    }),
    ("Solina Dream", "Strings", "Ensemble de cordas vintage com tremolo.", {
        "osc1_wave": 0.33, "osc2_wave": 0.0, "osc1_level": 0.55, "osc2_level": 0.55,
        "osc3_level": 0.35, "osc3_octave": 0.75, "osc2_fine": 0.40, "osc3_fine": 0.60,
        "cutoff": 0.58, "attack": 0.30, "decay": 0.5, "sustain": 0.95, "release": 0.70,
        "lfo_rate": 0.42, "lfo_depth": 0.16, "lfo2_rate": 0.55, "lfo2_depth": 0.14,
        "delay_mix": 0.20, "delay_time": 0.36, "delay_feedback": 0.32, "volume": 0.36,
    }),
    # Pluck
    ("Glass Pluck", "Pluck", "Pluck cristalino em oitava alta.", {
        "osc1_wave": 0.33, "osc2_wave": 1.0, "osc2_octave": 0.75,
        "osc1_level": 0.6, "osc2_level": 0.45, "osc3_level": 0.0,
        "cutoff": 0.66, "resonance": 0.32, "attack": 0.002, "decay": 0.12,
        "sustain": 0.0, "release": 0.22, "delay_mix": 0.26, "delay_time": 0.30,
        "delay_feedback": 0.34, "volume": 0.46,
    }),
    ("Muted Pluck", "Pluck", "Pluck abafado e percussivo.", {
        "osc1_level": 0.72, "osc2_level": 0.30, "osc3_level": 0.0, "osc2_fine": 0.47,
        "cutoff": 0.34, "resonance": 0.40, "drive": 0.15, "attack": 0.001,
        "decay": 0.09, "sustain": 0.0, "release": 0.08, "volume": 0.52,
    }),
    ("Kalimba Pluck", "Pluck", "Pluck de seno e triângulo, delicado.", {
        "osc1_wave": 1.0, "osc2_wave": 0.66, "osc2_octave": 0.75, "osc3_wave": 1.0,
        "osc3_octave": 1.0, "osc1_level": 0.7, "osc2_level": 0.3, "osc3_level": 0.12,
        "cutoff": 0.8, "attack": 0.001, "decay": 0.22, "sustain": 0.0,
        "release": 0.25, "delay_mix": 0.15, "volume": 0.50,
    }),
    ("Fifth Pluck", "Pluck", "Pluck em quinta, ótimo para riffs.", {
        "osc2_tune": FIFTH, "osc1_level": 0.7, "osc2_level": 0.5, "osc3_level": 0.0,
        "cutoff": 0.55, "resonance": 0.28, "drive": 0.2, "attack": 0.002,
        "decay": 0.14, "sustain": 0.05, "release": 0.15, "delay_mix": 0.2,
        "delay_time": 0.25, "volume": 0.44,
    }),
    ("Harp Glide", "Pluck", "Pluck longo, como harpa sintetizada.", {
        "osc1_wave": 0.66, "osc2_wave": 1.0, "osc2_octave": 0.75, "osc1_level": 0.7,
        "osc2_level": 0.35, "osc3_level": 0.0, "cutoff": 0.7, "attack": 0.002,
        "decay": 0.42, "sustain": 0.0, "release": 0.45, "delay_mix": 0.2,
        "delay_time": 0.38, "delay_feedback": 0.25, "volume": 0.48,
    }),
    # Bells
    ("Crystal Bell", "Bells", "Sino brilhante com parciais em oitava e quinta.", {
        "osc1_wave": 1.0, "osc2_wave": 1.0, "osc3_wave": 0.66,
        "osc2_octave": 1.0, "osc2_fine": 0.53, "osc3_octave": 0.75, "osc3_tune": FIFTH,
        "osc1_level": 0.6, "osc2_level": 0.4, "osc3_level": 0.25,
        "cutoff": 0.85, "attack": 0.001, "decay": 0.7, "sustain": 0.0, "release": 0.7,
        "delay_mix": 0.25, "delay_time": 0.5, "delay_feedback": 0.4, "volume": 0.42,
    }),
    ("Music Box", "Bells", "Caixinha de música, curta e doce.", {
        "osc1_wave": 1.0, "osc2_wave": 0.66, "osc1_octave": 0.75, "osc2_octave": 1.0,
        "osc1_level": 0.6, "osc2_level": 0.3, "osc3_level": 0.0, "cutoff": 0.9,
        "attack": 0.001, "decay": 0.35, "sustain": 0.0, "release": 0.4,
        "delay_mix": 0.18, "volume": 0.46,
    }),
    ("Temple Bell", "Bells", "Sino grave e longo, com batimento.", {
        "osc1_wave": 1.0, "osc2_wave": 1.0, "osc3_wave": 1.0, "osc2_fine": 0.56,
        "osc3_octave": 0.75, "osc3_tune": FIFTH, "osc1_level": 0.6, "osc2_level": 0.55,
        "osc3_level": 0.2, "cutoff": 0.7, "attack": 0.002, "decay": 0.9,
        "sustain": 0.0, "release": 0.9, "delay_mix": 0.3, "delay_time": 0.62,
        "delay_feedback": 0.45, "volume": 0.40,
    }),
    ("Vibraphone", "Bells", "Vibrafone com tremolo suave.", {
        "osc1_wave": 1.0, "osc2_wave": 1.0, "osc2_octave": 1.0, "osc1_level": 0.7,
        "osc2_level": 0.18, "osc3_level": 0.0, "cutoff": 0.8, "attack": 0.001,
        "decay": 0.6, "sustain": 0.0, "release": 0.55, "lfo_rate": 0.45,
        "lfo_depth": 0.35, "volume": 0.46,
    }),
    # Organ: real drawbar registrations (16' 5⅓' 8' 4' 2⅔' 2' 1⅗' 1⅓' 1')
    ("Full Drawbars", "Organ", "Órgão cheio (888888888), drive e Leslie rápido.", dict(
        drawbars("888888888"), organ_drive=0.3, leslie=1.0, leslie_fast=1.0,
        attack=0.0, decay=0.3, sustain=1.0, release=0.06, volume=0.26)),
    ("Jazz Organ", "Organ", "Jazz clássico (888000000): percussão 3ª rápida, click e Leslie lento.", dict(
        drawbars("888000000"), **organ(perc="third fast", click=True, vibrato="chorus", leslie="slow"),
        organ_drive=0.12, attack=0.0, decay=0.3, sustain=1.0, release=0.05, volume=0.42)),
    ("Rock Organ", "Organ", "Rock saturado (888800000) com Leslie rápido.", dict(
        drawbars("888800000"), **organ(perc="second fast", click=True, leslie="fast"),
        organ_drive=0.75, attack=0.0, decay=0.3, sustain=1.0, release=0.05, volume=0.34)),
    ("Church Organ", "Organ", "Órgão de igreja amplo (876556678) com cauda.", dict(
        drawbars("876556678"), attack=0.12, decay=0.4, sustain=1.0, release=0.45,
        delay_mix=0.3, delay_time=0.7, delay_feedback=0.5, volume=0.26)),
    ("Soft Combo", "Organ", "Órgão combo suave, flautado (008800000), com vibrato.", dict(
        drawbars("008800000"), **organ(vibrato="vibrato"), attack=0.003, decay=0.3,
        sustain=1.0, release=0.07, volume=0.5)),
    ("Ballad Organ", "Organ", "Balada gospel (838000000), chorus e Leslie lento.", dict(
        drawbars("838000000"), **organ(vibrato="chorus", leslie="slow"), attack=0.0,
        decay=0.3, sustain=1.0, release=0.08, volume=0.44)),
    ("Blues Bar", "Organ", "Blues (886000000): percussão 3ª, drive quente e Leslie lento.", dict(
        drawbars("886000000"), **organ(perc="third", click=True, leslie="slow"),
        organ_drive=0.4, attack=0.0, decay=0.3, sustain=1.0, release=0.05, volume=0.40)),
    ("Gospel Shout", "Organ", "Gospel (888000008) com Leslie rápido, click e drive.", dict(
        drawbars("888000008"), **organ(click=True, vibrato="chorus", leslie="fast"),
        organ_drive=0.45, attack=0.0, decay=0.3, sustain=1.0, release=0.05, volume=0.36)),
    ("Perc Groove", "Organ", "Groove seco (800000000) só com percussão 2ª rápida, sem Leslie.", dict(
        drawbars("800000000"), **organ(perc="second fast", click=True), attack=0.0,
        decay=0.3, sustain=1.0, release=0.04, volume=0.66)),
    ("Leslie Swell", "Organ", "Registro aveludado (688600000) com Leslie lento e chorus.", dict(
        drawbars("688600000"), **organ(vibrato="chorus", leslie="slow"), organ_drive=0.2,
        attack=0.02, decay=0.3, sustain=1.0, release=0.1, volume=0.4)),
    # E.Piano: tine engine (ep_*), no synth oscillators or filter.
    ("Suitcase Tine", "E.Piano", "Piano de tines clássico: redondo baixo, ataque de sino forte.", dict(
        electric_piano(tone=0.5, bark=0.35, decay=0.6), lfo_rate=0.45, lfo_depth=0.0,
        volume=0.62)),
    ("Mellow Stage", "E.Piano", "Stage piano macio e escuro, ótimo para baladas.", dict(
        electric_piano(tone=0.22, bark=0.15, decay=0.7), delay_mix=0.12,
        delay_time=0.4, delay_feedback=0.25, volume=0.66)),
    ("Funky Bark", "E.Piano", "Ataque agressivo que 'late' quando tocado forte.", dict(
        electric_piano(tone=0.75, bark=0.85, decay=0.45), volume=0.52)),
    ("Tremolo Ballad", "E.Piano", "Tines com tremolo estéreo de amplificador vintage.", dict(
        electric_piano(tone=0.4, bark=0.3, decay=0.65), lfo_rate=0.42, lfo_depth=0.55,
        delay_mix=0.15, delay_time=0.45, delay_feedback=0.3, volume=0.62)),
    ("Reed Piano", "E.Piano", "Piano de palheta, mais anasalado e curto.", dict(
        electric_piano(tone=0.85, bark=0.65, decay=0.3), drive=0.15, volume=0.55)),
    # Ambient
    ("Deep Space", "Ambient", "Drone escuro com ruído e ecos longos.", {
        "osc1_wave": 1.0, "osc2_wave": 0.66, "osc2_octave": 0.25, "osc2_fine": 0.53,
        "osc1_level": 0.5, "osc2_level": 0.5, "osc3_level": 0.0, "noise_level": 0.12,
        "cutoff": 0.35, "resonance": 0.35, "attack": 0.8, "decay": 0.8,
        "sustain": 0.9, "release": 0.95, "lfo_rate": 0.1, "lfo_depth": 0.3,
        "delay_mix": 0.45, "delay_time": 0.9, "delay_feedback": 0.65, "volume": 0.38,
    }),
    ("Aurora", "Ambient", "Pad luminoso que respira.", {
        "osc1_wave": 0.66, "osc2_wave": 0.0, "osc2_octave": 0.75, "osc2_fine": 0.55,
        "osc3_wave": 1.0, "osc3_octave": 1.0, "osc1_level": 0.55, "osc2_level": 0.35,
        "osc3_level": 0.25, "cutoff": 0.5, "resonance": 0.25, "attack": 0.7,
        "decay": 0.7, "sustain": 0.9, "release": 0.9, "lfo_rate": 0.12,
        "lfo_depth": 0.35, "lfo2_rate": 0.3, "lfo2_depth": 0.08, "delay_mix": 0.4,
        "delay_time": 0.75, "delay_feedback": 0.55, "volume": 0.36,
    }),
    ("Ocean Wind", "Ambient", "Vento e ondas de ruído filtrado.", {
        "osc1_level": 0.0, "osc2_level": 0.0, "osc3_level": 0.0, "noise_level": 0.9,
        "cutoff": 0.55, "resonance": 0.55, "attack": 0.7, "decay": 0.8,
        "sustain": 0.8, "release": 0.95, "lfo_rate": 0.08, "lfo_depth": 0.6,
        "delay_mix": 0.3, "delay_time": 0.8, "delay_feedback": 0.5, "volume": 0.6,
    }),
    ("Frozen Choir", "Ambient", "Coro sintético etéreo com vibrato.", {
        "osc1_wave": 0.66, "osc2_wave": 0.66, "osc2_fine": 0.44, "osc3_wave": 1.0,
        "osc3_octave": 0.75, "osc1_level": 0.55, "osc2_level": 0.55, "osc3_level": 0.2,
        "cutoff": 0.45, "resonance": 0.3, "attack": 0.55, "decay": 0.6,
        "sustain": 0.9, "release": 0.8, "lfo2_rate": 0.4, "lfo2_depth": 0.14,
        "delay_mix": 0.35, "delay_time": 0.6, "delay_feedback": 0.45, "volume": 0.38,
    }),
    # More Bass
    ("Reese Bass", "Bass", "Baixo de duas serras com batimento lento.", {
        "osc1_level": 0.8, "osc2_level": 0.8, "osc3_level": 0.0, "osc2_fine": 0.62,
        "sub_level": 0.4, "cutoff": 0.38, "resonance": 0.15, "drive": 0.4,
        "attack": 0.004, "decay": 0.4, "sustain": 0.9, "release": 0.12, "volume": 0.40,
    }),
    ("Octave Bass", "Bass", "Baixo em oitavas, firme e cheio.", {
        "osc1_wave": 0.33, "osc2_wave": 0.0, "osc2_octave": 0.25, "osc1_level": 0.7,
        "osc2_level": 0.7, "osc3_level": 0.0, "cutoff": 0.33, "resonance": 0.22,
        "drive": 0.3, "attack": 0.003, "decay": 0.22, "sustain": 0.7,
        "release": 0.1, "volume": 0.44,
    }),
    ("Sine Sub", "Bass", "Subgrave puro de senoide.", {
        "osc1_wave": 1.0, "osc1_level": 0.9, "osc2_level": 0.0, "osc3_level": 0.0,
        "sub_level": 0.0, "cutoff": 0.6, "drive": 0.1, "attack": 0.004,
        "decay": 0.3, "sustain": 1.0, "release": 0.1, "volume": 0.52,
    }),
    # More Lead
    ("Square Lead", "Lead", "Lead de onda quadrada com vibrato.", {
        "osc1_wave": 0.33, "osc2_wave": 0.33, "osc2_octave": 0.75, "osc1_level": 0.7,
        "osc2_level": 0.35, "osc3_level": 0.0, "cutoff": 0.7, "drive": 0.25,
        "attack": 0.005, "decay": 0.2, "sustain": 0.9, "release": 0.2,
        "lfo2_rate": 0.5, "lfo2_depth": 0.18, "delay_mix": 0.15, "volume": 0.38,
    }),
    ("Fifth Lead", "Lead", "Lead em quintas, grande e agressivo.", {
        "osc2_tune": FIFTH, "osc3_octave": 0.25, "osc1_level": 0.7, "osc2_level": 0.55,
        "osc3_level": 0.3, "cutoff": 0.65, "resonance": 0.2, "drive": 0.5,
        "attack": 0.004, "decay": 0.2, "sustain": 0.9, "release": 0.18,
        "lfo2_rate": 0.48, "lfo2_depth": 0.1, "volume": 0.34,
    }),
    ("Whistle", "Lead", "Assobio de senoide aguda com vibrato.", {
        "osc1_wave": 1.0, "osc1_octave": 0.75, "osc1_level": 0.75, "osc2_level": 0.0,
        "osc3_level": 0.0, "noise_level": 0.03, "cutoff": 0.85, "attack": 0.05,
        "decay": 0.3, "sustain": 0.9, "release": 0.25, "lfo2_rate": 0.55,
        "lfo2_depth": 0.25, "delay_mix": 0.2, "volume": 0.42,
    }),
    # More Brass and FX
    ("Synth Horns", "Brass", "Metais largos com ataque lento.", {
        "osc1_level": 0.7, "osc2_level": 0.65, "osc3_level": 0.3, "osc2_fine": 0.44,
        "osc3_fine": 0.56, "osc3_octave": 0.25, "cutoff": 0.52, "resonance": 0.15,
        "drive": 0.3, "attack": 0.14, "decay": 0.35, "sustain": 0.8,
        "release": 0.28, "lfo2_rate": 0.4, "lfo2_depth": 0.06, "volume": 0.36,
    }),
    ("Rising Storm", "FX", "Ruído e ressonância em tempestade.", {
        "osc1_wave": 0.33, "osc1_level": 0.4, "osc2_level": 0.0, "osc3_level": 0.0,
        "noise_level": 0.5, "cutoff": 0.6, "resonance": 0.7, "drive": 0.4,
        "attack": 0.9, "decay": 0.8, "sustain": 0.7, "release": 0.9,
        "lfo_rate": 0.85, "lfo_depth": 0.55, "delay_mix": 0.4, "delay_time": 0.55,
        "delay_feedback": 0.6, "volume": 0.30,
    }),
    ("Robot Voice", "FX", "Pulsos rápidos e graves, efeito robótico.", {
        "osc1_wave": 0.33, "osc2_wave": 0.33, "osc2_octave": 0.25, "osc1_level": 0.6,
        "osc2_level": 0.5, "osc3_level": 0.0, "cutoff": 0.4, "resonance": 0.6,
        "drive": 0.5, "attack": 0.004, "decay": 0.3, "sustain": 0.8,
        "release": 0.15, "lfo_rate": 0.95, "lfo_depth": 0.8, "volume": 0.34,
    }),
)


def fm_voice(**params):
    """Sine operators, OSC1 the carrier modulated by OSC2 (OSC3 -> OSC2 -> OSC1),
    with the analog filter open. Ratios: octave and tune of each oscillator."""
    values = dict(osc1_wave=1.0, osc2_wave=1.0, osc3_wave=1.0, osc1_level=1.0,
                  osc2_level=0.0, osc3_level=0.0, sub_level=0.0, noise_level=0.0,
                  osc1_tune=0.5, osc2_tune=0.5, osc3_tune=0.5, cutoff=1.0, resonance=0.0,
                  drive=0.0, osc1_fm_on=1.0)
    values.update(params)
    return values


# FM (v0.2.19): tune 0.5 + semitones/24, octave 0.75/1.0 = +1/+2 octaves.
FM_PROGRAMS = (
    ("FM E.Piano", "FM", "Piano elétrico FM dos anos 80: ataque brilhante que suaviza.", fm_voice(
        osc1_fm=0.45, osc2_fm_on=1.0, osc2_fm=0.18, osc3_octave=1.0, osc3_tune=1.0,
        mod_attack=0.0, mod_decay=0.45, mod_sustain=0.1, mod_release=0.3,
        attack=0.0, decay=0.7, sustain=0.0, release=0.35, volume=1.00)),
    ("FM Bells", "FM", "Sinos inarmônicos (razão 3,5) com cauda longa.", fm_voice(
        osc1_fm=0.55, osc2_octave=1.0, osc2_tune=0.5 - 2.31 / 24,
        mod_decay=0.7, mod_sustain=0.2, mod_release=0.6,
        attack=0.0, decay=0.9, sustain=0.0, release=0.7, delay_mix=0.2, volume=0.90)),
    ("FM Bass", "FM", "Baixo FM percussivo e definido, ótimo para slap sintético.", fm_voice(
        osc1_fm=0.55, osc1_octave=0.25, osc2_octave=0.25, mod_decay=0.3, mod_sustain=0.15,
        mod_release=0.1, attack=0.0, decay=0.5, sustain=0.6, release=0.1, volume=1.00)),
    ("FM Brass", "FM", "Metais FM: o brilho abre devagar como um sopro.", fm_voice(
        osc1_fm=0.5, osc2_fm_on=1.0, osc2_fm=0.3, osc3_fm_on=1.0, osc3_fm=0.3,
        mod_attack=0.25, mod_decay=0.4, mod_sustain=0.7, mod_release=0.25,
        attack=0.12, decay=0.4, sustain=0.85, release=0.2, lfo2_rate=0.4, lfo2_depth=0.05,
        volume=0.84)),
    ("FM Marimba", "FM", "Marimba de madeira (razão 4), curta e redonda.", fm_voice(
        osc1_fm=0.5, osc2_octave=1.0, mod_decay=0.15, mod_sustain=0.0, mod_release=0.1,
        attack=0.0, decay=0.45, sustain=0.0, release=0.2, volume=1.00)),
    ("FM Glass Pad", "FM", "Pad de vidro que brilha devagar, com vibrato.", fm_voice(
        osc1_fm=0.35, osc2_octave=0.75, osc2_fine=0.52, mod_attack=0.6, mod_decay=0.6,
        mod_sustain=0.5, mod_release=0.6, attack=0.5, decay=0.5, sustain=0.9, release=0.6,
        delay_mix=0.25, delay_time=0.45, lfo2_rate=0.35, lfo2_depth=0.04, volume=0.84)),
    ("FM Feedback Lead", "FM", "Lead de operador com feedback: serrote limpo e cortante.", fm_voice(
        osc1_level=0.0, osc1_fm_on=0.0, osc3_level=1.0, osc3_fm_on=1.0, osc3_fm=0.55,
        cutoff=0.8, attack=0.0, sustain=0.9, release=0.15, lfo2_rate=0.45, volume=0.80)),
    ("FM Clav", "FM", "Clavinet FM (razão 3), ataque estalado e curto.", fm_voice(
        osc1_fm=0.6, osc2_octave=0.75, osc2_tune=0.5 + 7 / 24, mod_decay=0.2,
        mod_sustain=0.0, mod_release=0.1, attack=0.0, decay=0.35, sustain=0.0,
        release=0.08, volume=1.00)),
)
PROGRAMS = PROGRAMS + MORE_PROGRAMS + FM_PROGRAMS


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
