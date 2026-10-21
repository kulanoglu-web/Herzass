"""Erzeugt die Klangeffekte der App selbst (eigene Synthese, keine fremden Aufnahmen).
Aufruf: python tools/make_sounds.py  ->  schreibt sounds/*.wav"""
import math
import os
import random
import struct
import wave

SR = 22050
rng = random.Random(7)


def tone(freq, dur, kind="sine", vol=0.5, attack=0.004, decay=8.0, slide=0.0, vibrato=0.0):
    out, phase = [], 0.0
    for i in range(int(SR * dur)):
        t = i / SR
        f = freq + slide * t / dur
        if vibrato:
            f += vibrato * math.sin(2 * math.pi * 6 * t)
        phase += 2 * math.pi * f / SR
        frac = (phase / (2 * math.pi)) % 1.0
        if kind == "sine":
            s = math.sin(phase)
        elif kind == "square":
            s = 1.0 if frac < 0.5 else -1.0
        elif kind == "saw":
            s = 2 * frac - 1
        else:  # tri
            s = 4 * abs(frac - 0.5) - 1
        out.append(s * vol * min(1.0, t / attack) * math.exp(-decay * t))
    return out


def noise(dur, vol=0.4, decay=60.0):
    return [(rng.random() * 2 - 1) * vol * math.exp(-decay * i / SR) for i in range(int(SR * dur))]


def mix(*parts):
    """parts: (Startzeit in s, Samples)"""
    total = max(int(st * SR) + len(s) for st, s in parts)
    buf = [0.0] * total
    for st, s in parts:
        o = int(st * SR)
        for i, v in enumerate(s):
            buf[o + i] += v
    return buf


def save(name, samples):
    peak = max(1e-9, max(abs(v) for v in samples))
    scale = min(1.0, 0.9 / peak)
    os.makedirs("sounds", exist_ok=True)
    with wave.open(os.path.join("sounds", name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v * scale)) * 32767))
                               for v in samples))


def arp(notes, step, kind="square", vol=0.3, last=0.5, decay=7.0):
    parts = []
    for i, f in enumerate(notes):
        d = last if i == len(notes) - 1 else step * 1.6
        parts.append((i * step, tone(f, d, kind, vol, decay=decay)))
    return mix(*parts)


save("click", tone(1400, 0.04, "square", 0.3, decay=70))
save("tick", mix((0, noise(0.02, 0.5, 120)), (0, tone(700, 0.03, "square", 0.25, decay=90))))
save("stop", mix((0, tone(150, 0.14, "sine", 0.9, decay=24, slide=-70)), (0, noise(0.03, 0.5, 100))))
save("hold", mix((0, tone(880, 0.07, "tri", 0.5, decay=30)), (0.045, tone(1320, 0.08, "tri", 0.5, decay=30))))
save("win_small", arp([523, 659, 784, 1047], 0.10))
save("win_big", mix(
    (0, arp([523, 659, 784, 1047, 784, 1047, 1319, 1568], 0.09, last=0.7, decay=5)),
    (0.2, arp([262, 330, 392, 523], 0.18, "tri", 0.3, last=0.6, decay=4))))
save("lose", tone(300, 0.55, "saw", 0.4, decay=3.5, slide=-190))
save("risk_start", tone(200, 0.5, "tri", 0.5, decay=1.5, slide=650))
save("risk_tick", mix((0, tone(1900, 0.03, "square", 0.3, decay=110)), (0, tone(950, 0.04, "sine", 0.4, decay=80))))
save("risk_win", mix((0, tone(784, 0.18, "tri", 0.5, decay=9)), (0.13, tone(1175, 0.5, "tri", 0.5, decay=5)),
                      (0.13, tone(2350, 0.4, "sine", 0.15, decay=7))))
save("risk_lose", mix((0, tone(330, 0.9, "saw", 0.4, decay=2.5, slide=-230, vibrato=8)),
                       (0.05, tone(70, 0.5, "sine", 0.8, decay=6))))
save("coins", mix(*[(0.055 * i, tone(rng.randint(1800, 2700), 0.09, "sine", 0.4, decay=25)) for i in range(7)]))
print("fertig:", sorted(os.listdir("sounds")))
