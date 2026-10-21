"""Erzeugt alle Klangeffekte der App selbst (eigene Synthese, keine fremden Aufnahmen).

Bausteine: Oszillatoren (sine/tri/square/saw, auch verstimmt), FM-Glocken, Rauschen,
Tiefpass, Echo und Hall.  Aufruf:  python tools/make_sounds.py  ->  schreibt sounds/*.wav
"""
import math
import os
import random
import struct
import wave

SR = 32000
TAU = 2 * math.pi
rng = random.Random(11)


# ------------------------------------------------------------- Bausteine ----
def _osc(kind, ph):
    fr = ph % 1.0
    if kind == "sine":
        return math.sin(TAU * ph)
    if kind == "square":
        return 1.0 if fr < 0.5 else -1.0
    if kind == "saw":
        return 2 * fr - 1
    return 4 * abs(fr - 0.5) - 1          # tri


def tone(freq, dur, kind="sine", vol=0.5, attack=0.005, decay=6.0, slide=0.0,
         vib=0.0, vibrate=5.5, detune=0.0, release=0.03):
    n = int(SR * dur)
    voices = [-detune, 0.0, detune] if detune else [0.0]
    ph = [rng.random() for _ in voices]
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        f = freq + slide * t / dur
        if vib:
            f += vib * math.sin(TAU * vibrate * t)
        s = 0.0
        for k, d in enumerate(voices):
            ph[k] += f * (1 + d) / SR
            s += _osc(kind, ph[k])
        s /= len(voices)
        e = min(1.0, t / attack) * math.exp(-decay * t)
        if release:
            e *= min(1.0, (dur - t) / release)
        out[i] = s * vol * e
    return out


def bell(freq, dur, ratio=3.5, index=3.5, decay=4.0, vol=0.4):
    """FM-Glocke: klingt wie Glockenspiel / Muenze."""
    n = int(SR * dur)
    out = []
    for i in range(n):
        t = i / SR
        m = index * math.exp(-decay * t) * math.sin(TAU * freq * ratio * t)
        e = min(1.0, t / 0.002) * math.exp(-decay * 0.75 * t) * min(1.0, (dur - t) / 0.03)
        out.append(math.sin(TAU * freq * t + m) * vol * e)
    return out


def noise(dur, vol=0.4, decay=60.0):
    return [(rng.random() * 2 - 1) * vol * math.exp(-decay * i / SR) for i in range(int(SR * dur))]


def lowpass(x, cutoff):
    a = 1 - math.exp(-TAU * cutoff / SR)
    y, out = 0.0, []
    for v in x:
        y += a * (v - y)
        out.append(y)
    return out


def highpass(x, cutoff):
    lp = lowpass(x, cutoff)
    return [v - l for v, l in zip(x, lp)]


def echo(x, delay, fb=0.45, mixv=0.5, taps=4):
    d = int(delay * SR)
    out = list(x) + [0.0] * (d * taps)
    for k in range(1, taps + 1):
        g = mixv * fb ** (k - 1)
        o = d * k
        for i, v in enumerate(x):
            out[o + i] += v * g
    return out


def reverb(x, wet=0.28, tail=0.9):
    """Einfacher Hall aus vier rueckgekoppelten Kammfiltern."""
    n = len(x) + int(tail * SR)
    src = list(x) + [0.0] * (n - len(x))
    acc = [0.0] * n
    for dl, fb in ((0.0297, 0.62), (0.0371, 0.58), (0.0411, 0.55), (0.0437, 0.52)):
        d = int(dl * SR)
        buf = src[:]
        for i in range(d, n):
            buf[i] += buf[i - d] * fb
        for i in range(n):
            acc[i] += buf[i] * 0.25
    return [s + wet * a for s, a in zip(src, acc)]


def mix(*parts):
    """parts: (Startzeit in s, Samples)"""
    total = max(int(st * SR) + len(s) for st, s in parts)
    buf = [0.0] * total
    for st, s in parts:
        o = int(st * SR)
        for i, v in enumerate(s):
            buf[o + i] += v
    return buf


def scale(x, g):
    return [v * g for v in x]


def save(name, samples, level=0.9):
    peak = max(1e-9, max(abs(v) for v in samples))
    g = level / peak
    os.makedirs("sounds", exist_ok=True)
    with wave.open(os.path.join("sounds", name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(math.tanh(v * g * 1.1) * 32000)) for v in samples))


def brass(freq, dur, vol=0.35):
    return lowpass(tone(freq, dur, "saw", vol, attack=0.04, decay=1.2, detune=0.006,
                        vib=2.5, vibrate=5.2), 2600)


def riser(dur, f0=180.0, f1=1700.0):
    """Aufsteigender Spannungs-Sound: Sweep + Rauschen + immer schnelleres Tremolo."""
    n = int(SR * dur)
    ph, y, out = 0.0, 0.0, []
    for i in range(n):
        t = i / SR
        p = t / dur
        f = f0 * (f1 / f0) ** p
        ph += f / SR
        saw = 2 * (ph % 1.0) - 1
        c = 300 + 6500 * p * p
        a = 1 - math.exp(-TAU * c / SR)
        y += a * ((rng.random() * 2 - 1) - y)
        trem = 0.55 + 0.45 * math.sin(TAU * (3 + 18 * p * p) * t)
        amp = (0.12 + 0.88 * p ** 1.6) * trem
        out.append((0.45 * saw * 0.5 + 0.9 * y) * amp * min(1.0, (dur - t) / 0.04))
    return out


# ----------------------------------------------------------------- Klaenge ----
def build():
    # Bedienung
    save("click", mix((0, highpass(noise(0.014, 0.6, 260), 1500)),
                      (0, tone(2400, 0.03, "square", 0.2, decay=120))))
    save("hold", mix((0, highpass(noise(0.012, 0.5, 300), 1200)),
                     (0.01, bell(1320, 0.3, 2.0, 2.0, 12, 0.35))))
    # Walzen
    save("tick", mix((0, tone(900, 0.03, "tri", 0.35, decay=110)), (0, noise(0.01, 0.3, 400))))
    save("stop", mix((0, tone(140, 0.2, "sine", 0.9, decay=20, slide=-70)),
                     (0, lowpass(noise(0.05, 0.6, 70), 900)),
                     (0, tone(1900, 0.012, "square", 0.15, decay=200))))
    # Gewinne
    notes = [523.25, 659.25, 783.99, 1046.5, 1318.5]
    small = [(0.085 * i, bell(f, 0.9, 3.5, 3.0, 5.0, 0.38)) for i, f in enumerate(notes)]
    small.append((0, tone(261.6, 0.9, "tri", 0.18, decay=3)))
    small.append((0, tone(329.6, 0.9, "tri", 0.14, decay=3)))
    save("win_small", reverb(mix(*small), 0.3, 0.7))

    big = [(0.00, brass(261.6, 0.55)), (0.00, brass(329.6, 0.55)), (0.00, brass(392.0, 0.55)),
           (0.55, brass(293.7, 0.45)), (0.55, brass(392.0, 0.45)), (0.55, brass(493.9, 0.45)),
           (1.05, brass(523.25, 1.9, 0.4)), (1.05, brass(659.25, 1.9, 0.35)),
           (1.05, brass(784.0, 1.9, 0.35)), (1.05, brass(1046.5, 1.9, 0.25)),
           (1.05, highpass(noise(1.4, 0.35, 2.6), 5000))]
    pent = [523.25, 587.3, 659.25, 783.99, 880.0, 1046.5, 1174.7, 1318.5, 1568.0, 1760.0, 2093.0]
    for i, f in enumerate(pent):
        big.append((0.15 + 0.1 * i, bell(f, 0.8, 3.5, 3.0, 5.0, 0.28)))
    for i in range(16):
        big.append((1.2 + 0.07 * i, bell(rng.randint(2100, 3300), 0.25, 2.2, 1.5, 14, 0.22)))
    save("win_big", reverb(mix(*big), 0.32, 1.0))

    # Verlust: traurige Posaune
    sad = []
    t0 = 0.0
    for f, d in ((233.1, 0.32), (220.0, 0.32), (207.7, 0.32), (196.0, 0.9)):
        sad.append((t0, lowpass(tone(f, d, "saw", 0.5, attack=0.03, decay=1.5, detune=0.007,
                                     vib=4 if d > 0.5 else 0, vibrate=5.5), 1100)))
        t0 += d
    save("lose", reverb(mix(*sad), 0.2, 0.6))

    save("coins", echo(mix(*[(0.065 * i, bell(rng.randint(1800, 3200), 0.3, 2.4, 1.8, 11, 0.4))
                             for i in range(14)]), 0.11, 0.4, 0.4, 3))

    # Risiko
    save("risk_start", reverb(mix(
        (0, tone(75, 0.7, "sine", 0.95, decay=6, slide=-35)),
        (0, lowpass(noise(0.25, 0.7, 14), 500)),
        (0.02, lowpass(tone(220, 1.0, "saw", 0.3, decay=2.2, detune=0.008), 1400)),
        (0.02, lowpass(tone(261.6, 1.0, "saw", 0.28, decay=2.2, detune=0.008), 1400)),
        (0.02, lowpass(tone(311.1, 1.0, "saw", 0.26, decay=2.2, detune=0.008), 1400)),
        (0.02, lowpass(tone(370.0, 1.0, "saw", 0.24, decay=2.2, detune=0.008), 1400)),
    ), 0.3, 0.8))

    # Spannungsschleife (2 s, nahtlos): dunkler Brummton, Herzschlag, flirrende Hoehen
    L = 2.0
    n = int(SR * L)
    drone = [0.0] * n
    for f, v in ((55.0, 0.55), (82.5, 0.40), (110.5, 0.25)):
        for i in range(n):
            t = i / SR
            lfo = 0.65 + 0.35 * math.sin(TAU * 2.0 * t)       # 2 ganze Schwingungen in 2 s
            drone[i] += math.sin(TAU * f * t) * v * lfo
    shimmer = [0.0] * n
    for f in (880.0, 1318.5, 1760.0):
        for i in range(n):
            t = i / SR
            shimmer[i] += math.sin(TAU * f * t) * 0.045 * (0.5 + 0.5 * math.sin(TAU * 8.0 * t)) ** 2
    beats = []
    for b0 in (0.0, 1.0):
        beats.append((b0, tone(58, 0.22, "sine", 1.0, decay=17)))
        beats.append((b0 + 0.20, tone(50, 0.26, "sine", 0.8, decay=15)))
    for k in range(8):
        beats.append((0.25 * k, mix((0, tone(300, 0.03, "tri", 0.12, decay=90)))))
    loop = mix((0, drone), (0, shimmer), *beats)[:n]
    save("risk_loop", loop)
    # Stopp-Schlag
    save("risk_stop", reverb(mix(
        (0, tone(120, 0.35, "sine", 1.0, decay=11, slide=-70)),
        (0, lowpass(noise(0.08, 0.8, 45), 2500)),
        (0, tone(880, 0.12, "square", 0.18, decay=60)),
    ), 0.22, 0.6))
    # Wartespannung nach dem Auslaufen: tiefes Anschwellen mit Flirren
    hold = []
    for i in range(int(SR * 1.7)):
        t = i / SR
        p = t / 1.7
        hold.append((math.sin(TAU * (70 + 40 * p) * t) * 0.6 +
                     math.sin(TAU * (700 + 900 * p) * t) * 0.10 * p) * (0.15 + 0.85 * p ** 1.5) *
                    (0.7 + 0.3 * math.sin(TAU * (4 + 10 * p) * t)))
    save("risk_hold", hold)
    save("risk_tick_lo", mix((0, tone(430, 0.06, "sine", 0.7, decay=55)), (0, noise(0.008, 0.35, 500))))
    save("risk_tick_hi", mix((0, tone(1180, 0.06, "sine", 0.55, decay=60)),
                             (0, tone(1770, 0.05, "tri", 0.2, decay=70)), (0, noise(0.008, 0.3, 500))))
    save("heart", mix((0, tone(62, 0.18, "sine", 0.9, decay=22)),
                      (0.19, tone(55, 0.22, "sine", 0.75, decay=20))))
    win = [(0, tone(300, 0.35, "sine", 0.5, decay=2.0, slide=1900))]
    for i, f in enumerate([1046.5, 1318.5, 1568.0, 2093.0]):
        win.append((0.33 + 0.04 * i, bell(f, 1.5, 3.5, 3.0, 3.5, 0.34)))
    for i in range(10):
        win.append((0.45 + 0.06 * i, bell(rng.randint(2200, 3400), 0.25, 2.2, 1.5, 14, 0.2)))
    win.append((0.33, highpass(noise(0.9, 0.3, 4), 4500)))
    save("risk_win", reverb(mix(*win), 0.3, 1.0))
    save("risk_lose", reverb(mix(
        (0, tone(95, 1.5, "sine", 0.95, decay=2.6, slide=-55)),
        (0, lowpass(noise(0.9, 0.7, 4), 220)),
        (0.05, lowpass(tone(420, 1.3, "saw", 0.45, decay=1.8, detune=0.012, slide=-330), 800)),
        (0.05, lowpass(tone(315, 1.3, "saw", 0.4, decay=1.8, detune=0.012, slide=-250), 700)),
    ), 0.28, 0.9))


if __name__ == "__main__":
    build()
    for f in sorted(os.listdir("sounds")):
        w = wave.open(os.path.join("sounds", f))
        print("%-18s %.2fs" % (f, w.getnframes() / w.getframerate()))
