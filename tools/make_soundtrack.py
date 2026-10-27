#!/usr/bin/env python3
"""Original soundtrack generator for MMX Zero History.

The brief was "distinta a la original pero parecida": same family of sounds
(two pulse channels, triangle bass, noise percussion, 16-step-style drive,
minor-key heroic melodies), but every melody, progression and tempo here is
new. Nothing is transcribed from the Mega Man X3 soundtrack.

    python3 tools/make_soundtrack.py            # render all tracks
    python3 tools/make_soundtrack.py --track w04_caldor
    python3 tools/make_soundtrack.py --list

Render is deterministic: same file, same bytes. Output is 32 kHz mono s16 PCM
(the SNES DSP's own rate), committed as Ogg Vorbis in assets/audio/ with the
WAVs written to a scratch directory.

Composition model: each track is a hand-written motif plus a chord
progression. The sequencer transposes the motif through the progression,
adds a bassline on the roots, an arpeggio channel, and a drum pattern. That
keeps the writing musical while making every track distinct by construction.
"""

from __future__ import annotations

import argparse
import math
import random
import struct
import subprocess
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "audio"
RATE = 32000

# ---------------------------------------------------------------- note tables

NOTE_BASE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
             "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}

MINOR = (0, 2, 3, 5, 7, 8, 10)
PHRYGIAN = (0, 1, 3, 5, 7, 8, 10)
DORIAN = (0, 2, 3, 5, 7, 9, 10)
MAJOR = (0, 2, 4, 5, 7, 9, 11)


def hz(name: str) -> float:
    """'A4' -> 440.0; 'C#5' -> 554.37."""
    if name == "r":
        return 0.0
    step = name[:-1]
    octave = int(name[-1])
    midi = 12 * (octave + 1) + NOTE_BASE[step]
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


# ---------------------------------------------------------------- oscillators

def osc_pulse(phase: float, duty: float) -> float:
    return 1.0 if (phase % 1.0) < duty else -1.0


def osc_triangle(phase: float) -> float:
    t = phase % 1.0
    return 4.0 * abs(t - 0.5) - 1.0


def osc_saw(phase: float) -> float:
    return 2.0 * (phase % 1.0) - 1.0


@dataclass
class Voice:
    """One monophonic channel with an AD envelope and optional vibrato."""

    waveform: str = "pulse"
    duty: float = 0.5
    attack: float = 0.006
    decay: float = 0.09
    sustain: float = 0.55
    release: float = 0.10
    gain: float = 0.22
    vibrato_hz: float = 0.0
    vibrato_depth: float = 0.0
    detune_cents: float = 0.0
    echo: float = 0.0
    echo_delay: float = 0.115

    def wave(self, phase: float) -> float:
        if self.waveform == "triangle":
            return osc_triangle(phase)
        if self.waveform == "saw":
            return osc_saw(phase)
        return osc_pulse(phase, self.duty)


def env_at(t: float, dur: float, v: Voice) -> float:
    if t < 0.0:
        return 0.0
    if t < v.attack:
        return t / max(v.attack, 1e-6)
    if t < v.attack + v.decay:
        k = (t - v.attack) / max(v.decay, 1e-6)
        return 1.0 + (v.sustain - 1.0) * k
    if t < dur:
        return v.sustain
    r = t - dur
    if r < v.release:
        return v.sustain * (1.0 - r / max(v.release, 1e-6))
    return 0.0


def add_note(buf: list[float], at: float, dur: float, freq: float,
             v: Voice) -> None:
    if freq <= 0.0 or dur <= 0.0:
        return
    start = int(at * RATE)
    length = int((dur + v.release) * RATE)
    if start >= len(buf):
        return
    length = min(length, len(buf) - start)
    if length <= 0:
        return
    phase = 0.0
    detune = 2.0 ** (v.detune_cents / 1200.0)
    echo_buf = None
    if v.echo > 0.0:
        echo_buf = int(v.echo_delay * RATE)
    for i in range(length):
        t = i / RATE
        e = env_at(t, dur, v)
        if e <= 0.0:
            continue
        mod = 1.0
        if v.vibrato_depth > 0.0:
            mod = 1.0 + v.vibrato_depth * math.sin(
                2.0 * math.pi * v.vibrato_hz * t)
        f = freq * mod
        phase += f / RATE
        if detune != 1.0:
            sample = 0.5 * (v.wave(phase) + v.wave(phase * detune))
        else:
            sample = v.wave(phase)
        value = sample * e * v.gain
        buf[start + i] += value
        if echo_buf and start + i + echo_buf < len(buf):
            buf[start + i + echo_buf] += value * v.echo


def add_noise(buf: list[float], at: float, dur: float, gain: float,
              tone: float = 0.5, decay: float = 0.03) -> None:
    """Percussion: filtered noise burst. tone 0 = kick-ish, 1 = hat-ish."""
    start = int(at * RATE)
    length = int(dur * RATE)
    if start >= len(buf):
        return
    length = min(length, len(buf) - start)
    rng = random.Random(start * 2654435761 % (2 ** 32))
    prev = 0.0
    coef = 0.92 - 0.85 * tone
    for i in range(length):
        t = i / RATE
        e = math.exp(-t / max(decay, 1e-4))
        n = rng.uniform(-1.0, 1.0)
        prev = coef * prev + (1.0 - coef) * n
        body = prev
        if tone < 0.2:  # add a pitched thump for kicks
            body += 0.7 * math.sin(2 * math.pi * (52.0 - 18.0 * t) * t)
        buf[start + i] += body * e * gain


# ---------------------------------------------------------------- composition

@dataclass
class Track:
    key: str                 # tonic pitch class name
    scale: tuple[int, ...]
    bpm: float
    bars: int
    beats_per_bar: int
    motif: list[str]         # one bar of melody, step = eighth note
    progression: list[int]   # scale-degree roots, one per bar
    drums: str               # 'four', 'backbeat', 'march', 'none', 'shuffle'
    lead: Voice
    bass: Voice
    arp: Voice
    arp_step: float = 0.125
    title: str = ""
    mood: str = ""
    octave: int = 4


def scale_note(key: str, scale: tuple[int, ...], degree: int,
               octave: int) -> str:
    """Scale degree -> note name. degree may walk past the octave."""
    steps = len(scale)
    oct_shift, idx = divmod(degree, steps)
    semis = NOTE_BASE[key] + scale[idx] + 12 * oct_shift
    octave += semis // 12
    semis %= 12
    names = {v: k for k, v in NOTE_BASE.items()}
    return f"{names[semis]}{octave}"


def compose(track: Track, seconds_hint: float = 26.0) -> list[float]:
    rng = random.Random(f"zero-history:{track.title}")
    beat = 60.0 / track.bpm
    eighth = beat / 2.0
    bar_len = beat * track.beats_per_bar
    total_bars = track.bars
    total = bar_len * total_bars
    # Round the loop up to a whole bar so the seam is clean.
    frames = int(round(total * RATE))
    buf = [0.0] * frames

    for bar in range(total_bars):
        bar_at = bar * bar_len
        root = track.progression[bar % len(track.progression)]

        # --- bass: root on the downbeat, fifth on the back half
        add_note(buf, bar_at, beat * 1.6,
                 hz(scale_note(track.key, track.scale, root - 7, 2)),
                 track.bass)
        add_note(buf, bar_at + beat * 1.75, beat * 0.4,
                 hz(scale_note(track.key, track.scale, root - 7, 2)),
                 track.bass)
        add_note(buf, bar_at + beat * 2.0, beat * 1.5,
                 hz(scale_note(track.key, track.scale, root - 4, 2)),
                 track.bass)

        # --- arpeggio: triad, up and down, on the arp voice
        triad = (root, root + 2, root + 4)
        steps = int(round(bar_len / track.arp_step))
        for s in range(steps):
            deg = triad[s % len(triad)] + (7 if (s // len(triad)) % 2 else 0)
            add_note(buf, bar_at + s * track.arp_step, track.arp_step * 0.92,
                     hz(scale_note(track.key, track.scale, deg, track.octave)),
                     track.arp)

        # --- lead: motif transposed to the bar's chord, with a small
        #     variation on every second pass through the progression
        var = (bar // len(track.progression)) % 3
        for i, token in enumerate(track.motif):
            if token == "r":
                continue
            if var == 1 and i % 3 == 2:
                continue                      # rhythmic thinning
            deg = int(token) + root
            octave = track.octave
            if var == 2 and i % 4 == 3:
                deg += 2
            add_note(buf, bar_at + i * eighth, eighth * 0.92,
                     hz(scale_note(track.key, track.scale, deg, octave)),
                     track.lead)

        # --- drums
        d = track.drums
        if d == "four":
            for b in range(track.beats_per_bar):
                add_noise(buf, bar_at + b * beat, 0.10, 0.30, 0.1, 0.05)
                add_noise(buf, bar_at + b * beat + beat * 0.5, 0.06, 0.13,
                          0.85, 0.02)
        elif d == "backbeat":
            add_noise(buf, bar_at, 0.10, 0.30, 0.1, 0.05)
            add_noise(buf, bar_at + beat * 2, 0.10, 0.28, 0.1, 0.05)
            for b in (1, 3):
                add_noise(buf, bar_at + b * beat, 0.14, 0.14, 0.85, 0.05)
            for s in range(0, 8, 2):
                add_noise(buf, bar_at + s * eighth, 0.04, 0.07, 0.9, 0.015)
        elif d == "march":
            for b in range(track.beats_per_bar):
                add_noise(buf, bar_at + b * beat, 0.09, 0.24, 0.15, 0.04)
                add_noise(buf, bar_at + b * beat + beat * 0.5, 0.05, 0.10,
                          0.8, 0.02)
        elif d == "shuffle":
            for b in range(track.beats_per_bar):
                add_noise(buf, bar_at + b * beat, 0.08, 0.20, 0.1, 0.04)
            add_noise(buf, bar_at + beat * 1.33, 0.06, 0.12, 0.85, 0.02)
            add_noise(buf, bar_at + beat * 3.33, 0.06, 0.12, 0.85, 0.02)

    _ = rng
    return finish(buf, track)


def finish(buf: list[float], track: Track) -> list[float]:
    """Soft-clip, normalise to -1 dBFS, and add a short loop-friendly tail."""
    peak = max(1e-9, max(abs(x) for x in buf))
    norm = 0.89 / peak
    out = [math.tanh(x * norm * 1.15) * 0.92 for x in buf]
    # 8 ms fade at both ends so the loop point does not click.
    fade = int(0.008 * RATE)
    for i in range(min(fade, len(out))):
        k = i / fade
        out[i] *= k
        out[-1 - i] *= k
    return out


# ---------------------------------------------------------------- the record

def _v(**kw) -> Voice:
    return Voice(**kw)


LEAD = _v(waveform="pulse", duty=0.25, gain=0.19, decay=0.08, sustain=0.6,
          vibrato_hz=5.6, vibrato_depth=0.005, echo=0.16)
LEAD_SOFT = _v(waveform="pulse", duty=0.5, gain=0.15, attack=0.02,
               decay=0.14, sustain=0.55, vibrato_hz=5.0,
               vibrato_depth=0.004, echo=0.20)
BASS = _v(waveform="triangle", gain=0.30, attack=0.004, decay=0.06,
          sustain=0.72, release=0.06)
ARP = _v(waveform="pulse", duty=0.125, gain=0.085, attack=0.003,
         decay=0.05, sustain=0.35, release=0.05, echo=0.12)


TRACKS: dict[str, Track] = {
    "title_boveda": Track(
        title="title_boveda", key="A", scale=MINOR, bpm=76, bars=16,
        beats_per_bar=4, octave=4, drums="none",
        motif=["0", "r", "2", "r", "4", "r", "2", "r"],
        progression=[0, 5, 3, 4, 0, 5, 6, 4, 0, 5, 3, 4, 0, 6, 5, 4],
        lead=_v(waveform="pulse", duty=0.5, gain=0.16, attack=0.03,
                decay=0.20, sustain=0.5, vibrato_hz=4.4,
                vibrato_depth=0.004, echo=0.26, echo_delay=0.24),
        bass=_v(waveform="triangle", gain=0.20, attack=0.02, sustain=0.6),
        arp=_v(waveform="pulse", duty=0.125, gain=0.055, attack=0.01,
               sustain=0.3, echo=0.28, echo_delay=0.24),
        arp_step=0.25,
        mood="Archivo abriéndose. Lento, grave, con eco largo."),

    "stage_select": Track(
        title="stage_select", key="E", scale=MINOR, bpm=132, bars=16,
        beats_per_bar=4, octave=5, drums="four",
        motif=["0", "0", "4", "2", "0", "r", "2", "4"],
        progression=[0, 4, 5, 3, 0, 4, 6, 5, 0, 4, 5, 3, 6, 4, 5, 5],
        lead=LEAD, bass=BASS, arp=ARP,
        mood="Decisión. Pulso firme, arpegio constante."),

    "w01_condor_cobalto": Track(
        title="w01_condor_cobalto", key="D", scale=MINOR, bpm=150, bars=16,
        beats_per_bar=4, octave=5, drums="four",
        motif=["4", "2", "0", "2", "4", "6", "4", "2"],
        progression=[0, 0, 5, 5, 3, 3, 4, 4, 0, 0, 5, 5, 6, 4, 5, 5],
        lead=LEAD, bass=BASS, arp=ARP, arp_step=0.0833,
        mood="Viento de altura. Rápido, con arpegios de tresillos."),

    "w02_salitre_sierpe": Track(
        title="w02_salitre_sierpe", key="C", scale=PHRYGIAN, bpm=124,
        bars=16, beats_per_bar=4, octave=4, drums="backbeat",
        motif=["0", "1", "0", "4", "0", "1", "3", "r"],
        progression=[0, 1, 0, 4, 0, 1, 3, 4, 0, 1, 0, 4, 3, 1, 0, 4],
        lead=_v(waveform="pulse", duty=0.25, gain=0.18, decay=0.10,
                sustain=0.58, vibrato_hz=6.2, vibrato_depth=0.007,
                echo=0.14),
        bass=BASS, arp=ARP,
        mood="Desierto. Frigio, seco, sin resolución cómoda."),

    "w03_glaciar_grifo": Track(
        title="w03_glaciar_grifo", key="F#", scale=MINOR, bpm=118, bars=16,
        beats_per_bar=4, octave=5, drums="backbeat",
        motif=["4", "r", "6", "r", "4", "2", "0", "r"],
        progression=[0, 3, 5, 4, 0, 3, 5, 4, 0, 3, 6, 4, 5, 3, 4, 4],
        lead=_v(waveform="pulse", duty=0.125, gain=0.17, attack=0.01,
                decay=0.12, sustain=0.5, vibrato_hz=5.2,
                vibrato_depth=0.006, echo=0.22, echo_delay=0.19),
        bass=_v(waveform="triangle", gain=0.26, sustain=0.7),
        arp=_v(waveform="pulse", duty=0.125, gain=0.07, sustain=0.3,
               echo=0.22, echo_delay=0.19),
        mood="Hielo. Timbre delgado, silencios largos, eco corto."),

    "w04_vibora_caldor": Track(
        title="w04_vibora_caldor", key="G", scale=MINOR, bpm=168, bars=16,
        beats_per_bar=4, octave=4, drums="four",
        motif=["0", "0", "3", "0", "4", "3", "0", "r"],
        progression=[0, 0, 3, 3, 5, 5, 4, 4, 0, 0, 3, 3, 6, 6, 4, 4],
        lead=_v(waveform="saw", duty=0.5, gain=0.13, decay=0.09,
                sustain=0.6, vibrato_hz=6.8, vibrato_depth=0.008,
                echo=0.10),
        bass=_v(waveform="triangle", gain=0.32, attack=0.003,
                decay=0.05, sustain=0.8),
        arp=ARP, arp_step=0.0833,
        mood="Lava. Agresivo, sierra, batería a toda."),

    "w05_marea_mantis": Track(
        title="w05_marea_mantis", key="A", scale=DORIAN, bpm=108, bars=16,
        beats_per_bar=3, octave=4, drums="shuffle",
        motif=["0", "2", "4", "r", "2", "4", "6", "r"],
        progression=[0, 4, 3, 0, 0, 4, 5, 3, 0, 4, 3, 0, 5, 4, 3, 0],
        lead=LEAD_SOFT, bass=BASS, arp=ARP, arp_step=0.1667,
        mood="Marea. Compás de 3, vaivén, sin apuro."),

    "w06_jabali_alerce": Track(
        title="w06_jabali_alerce", key="B", scale=MINOR, bpm=142, bars=16,
        beats_per_bar=4, octave=4, drums="backbeat",
        motif=["0", "4", "2", "4", "0", "r", "6", "4"],
        progression=[0, 0, 6, 6, 4, 4, 5, 5, 0, 0, 6, 6, 4, 5, 6, 6],
        lead=LEAD, bass=BASS, arp=ARP,
        mood="Selva. Síncopa, tambor de madera, peso en el contratiempo."),

    "w07_buho_reloj": Track(
        title="w07_buho_reloj", key="D", scale=MINOR, bpm=126, bars=16,
        beats_per_bar=4, octave=5, drums="march",
        motif=["0", "r", "0", "4", "0", "r", "2", "r"],
        progression=[0, 3, 0, 3, 5, 3, 0, 3, 0, 3, 0, 3, 4, 5, 3, 0],
        lead=_v(waveform="pulse", duty=0.5, gain=0.17, attack=0.004,
                decay=0.06, sustain=0.5, echo=0.18, echo_delay=0.25),
        bass=BASS,
        arp=_v(waveform="pulse", duty=0.25, gain=0.06, attack=0.002,
               decay=0.03, sustain=0.2, release=0.02),
        arp_step=0.0833,
        mood="Relojería. Tictac en el arpegio, todo cuadrado."),

    "w08_puma_chatarra": Track(
        title="w08_puma_chatarra", key="E", scale=PHRYGIAN, bpm=156, bars=16,
        beats_per_bar=4, octave=4, drums="four",
        motif=["0", "1", "4", "1", "0", "3", "1", "r"],
        progression=[0, 0, 1, 1, 4, 4, 3, 3, 0, 0, 1, 1, 6, 6, 4, 4],
        lead=_v(waveform="saw", duty=0.5, gain=0.14, decay=0.07,
                sustain=0.65, vibrato_hz=7.0, vibrato_depth=0.009),
        bass=_v(waveform="triangle", gain=0.33, sustain=0.82),
        arp=ARP, arp_step=0.0833,
        mood="Chatarra. Industrial, desafinado a propósito, con golpes."),

    "omega": Track(
        title="omega", key="C", scale=MINOR, bpm=96, bars=16,
        beats_per_bar=4, octave=4, drums="march",
        motif=["0", "0", "6", "4", "0", "0", "3", "4"],
        progression=[0, 6, 5, 4, 0, 6, 5, 4, 0, 6, 3, 4, 5, 6, 4, 4],
        lead=_v(waveform="pulse", duty=0.25, gain=0.18, attack=0.01,
                decay=0.12, sustain=0.62, vibrato_hz=4.8,
                vibrato_depth=0.006, echo=0.20, echo_delay=0.21),
        bass=_v(waveform="triangle", gain=0.32, sustain=0.8),
        arp=ARP,
        mood="Bóveda Ω. Marcial, lento, inevitable."),

    "zero_history": Track(
        title="zero_history", key="A", scale=MINOR, bpm=88, bars=16,
        beats_per_bar=4, octave=5, drums="none",
        motif=["4", "r", "3", "2", "0", "r", "2", "r"],
        progression=[0, 5, 2, 4, 0, 5, 2, 4, 0, 5, 2, 4, 3, 2, 5, 5],
        lead=_v(waveform="pulse", duty=0.5, gain=0.16, attack=0.04,
                decay=0.24, sustain=0.5, vibrato_hz=4.6,
                vibrato_depth=0.005, echo=0.28, echo_delay=0.28),
        bass=_v(waveform="triangle", gain=0.18, attack=0.03, sustain=0.6),
        arp=_v(waveform="pulse", duty=0.125, gain=0.05, attack=0.02,
               sustain=0.28, echo=0.30, echo_delay=0.28),
        arp_step=0.25,
        mood="Créditos. Tema de Zero: el mismo motivo del título, resuelto."),
}


def write_wav(path: Path, samples: list[float]) -> None:
    frames = bytearray()
    for s in samples:
        v = max(-1.0, min(1.0, s))
        frames += struct.pack("<h", int(round(v * 32767.0)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))


def encode_ogg(wav: Path, ogg: Path) -> bool:
    if not subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0:
        return False
    proc = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
         "-c:a", "libvorbis", "-q:a", "4", str(ogg)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  ffmpeg failed: {proc.stderr.strip()[:200]}", file=sys.stderr)
        return False
    return True


def render_one(name: str, scratch: Path) -> None:
    track = TRACKS[name]
    samples = compose(track)
    scratch.mkdir(parents=True, exist_ok=True)
    wav = scratch / f"{name}.wav"
    write_wav(wav, samples)
    OUT.mkdir(parents=True, exist_ok=True)
    ogg = OUT / f"{name}.ogg"
    if encode_ogg(wav, ogg):
        print(f"  {name:<24} {ogg.stat().st_size // 1024:>5} KiB ogg")
    else:
        keep = OUT / f"{name}.wav"
        keep.write_bytes(wav.read_bytes())
        print(f"  {name:<24} {keep.stat().st_size // 1024:>5} KiB wav (no ffmpeg)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--track", action="append", default=None,
                    help="render only this track (repeatable)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--scratch", default="/tmp/zero-history-wav")
    args = ap.parse_args(argv)

    if args.list:
        for name, t in TRACKS.items():
            print(f"{name:<24} {t.bpm:>5.0f} bpm  {t.beats_per_bar}/4  "
                  f"{t.bars:>2} bars  {t.mood}")
        return 0

    names = args.track or list(TRACKS)
    for name in names:
        if name not in TRACKS:
            print(f"unknown track {name!r}; see --list", file=sys.stderr)
            return 2
    scratch = Path(args.scratch)
    print(f"rendering {len(names)} track(s) at {RATE} Hz")
    for name in names:
        render_one(name, scratch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
