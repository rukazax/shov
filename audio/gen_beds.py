#!/usr/bin/env python3
"""Генерирует музыкальные подложки и звуковые эффекты для аудиоверсии «Шова».

Ничего не скачивает: всё синтезируется из синусов, шума и огибающих.
44.1 кГц, моно, 16 бит. Запуск: python3 gen_beds.py
"""
import os
import wave

import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "beds")
rng = np.random.default_rng(4)


def env_ad(n, attack, decay, sr=SR):
    a = max(1, int(attack * sr))
    d = max(1, int(decay * sr))
    e = np.ones(n, dtype=np.float32)
    e[:a] = np.linspace(0.0, 1.0, a, dtype=np.float32)
    if d < n - a:
        e[a + d:] = 0.0
        e[a:a + d] = np.linspace(1.0, 0.0, d, dtype=np.float32) ** 1.6
    else:
        e[a:] = np.linspace(1.0, 0.0, n - a, dtype=np.float32) ** 1.6
    return e


def note(freq, dur, amp=0.3, attack=0.05, decay=None, harmonics=(1.0, 0.3, 0.12), detune=0.0):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    sig = np.zeros(n, dtype=np.float32)
    for i, h in enumerate(harmonics, start=1):
        f = freq * i * (1.0 + detune)
        sig += h * np.sin(2 * np.pi * f * t, dtype=np.float32)
    sig *= env_ad(n, attack, decay if decay is not None else dur, )
    return amp * sig / max(1.0, sum(harmonics))


def noise(dur, amp=0.2, lowpass=0.2):
    n = int(dur * SR)
    x = rng.standard_normal(n).astype(np.float32)
    # однополюсный ФНЧ: сглаживание
    a = float(lowpass)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(n):
        acc = acc * (1.0 - a) + x[i] * a
        y[i] = acc
    return amp * y


def reverb(x, mix=0.25, delays=(0.031, 0.067, 0.113), feedback=0.35):
    out = x.copy()
    for d in delays:
        k = int(d * SR)
        tail = np.zeros_like(x)
        tail[k:] = x[:-k] * feedback
        tail[k:] += np.roll(tail, k)[k:] * feedback
        out += tail * mix
    return out


def fade(x, sec=0.5):
    n = int(sec * SR)
    if n * 2 >= len(x):
        return x
    x[:n] *= np.linspace(0, 1, n, dtype=np.float32)
    x[-n:] *= np.linspace(1, 0, n, dtype=np.float32)
    return x


def write_wav(name, data, sr=SR):
    os.makedirs(OUT, exist_ok=True)
    peak = float(np.max(np.abs(data))) or 1.0
    data = np.clip(data / peak * 0.85, -1, 1)
    pcm = (data * 32767).astype("<i2")
    with wave.open(os.path.join(OUT, name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"{name:16s} {len(data)/sr:6.1f}s")


# --- подложки -------------------------------------------------------------

def bed_calm(dur=75.0):
    """Спокойная: малая терция, медленное дыхание, редкий колокольчик."""
    n = int(dur * SR)
    out = np.zeros(n, dtype=np.float32)
    chords = [(110.0, 132.0, 164.8), (98.0, 123.5, 146.8), (110.0, 138.6, 164.8)]
    seg = dur / len(chords)
    for i, ch in enumerate(chords):
        start = int(i * seg * SR)
        pad_n = int(seg * 1.3 * SR)
        pad = np.zeros(pad_n, dtype=np.float32)
        t = np.arange(pad_n, dtype=np.float32) / SR
        lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t)
        for f in ch:
            pad += (0.2 * np.sin(2 * np.pi * f * t) + 0.1 * np.sin(2 * np.pi * f * 1.004 * t)).astype(np.float32) * lfo
        pad *= env_ad(pad_n, 2.0, seg * 1.25)
        out[start:start + pad_n] += pad[: n - start]
    for k in range(1, 5):
        start = int(dur * k / 5 * SR)
        bell = note(880.0 * (1.0 if k % 2 else 0.5), 2.5, amp=0.05, attack=0.002, decay=2.5)
        out[start:start + len(bell)] += bell[: n - start]
    return fade(reverb(out, mix=0.3), 1.5)


def bed_tense(dur=75.0):
    """Напряжение: низкий гул, сердцебиение, диссонанс."""
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    hum = 0.16 * np.sin(2 * np.pi * 55.0 * t) + 0.09 * np.sin(2 * np.pi * 55.4 * t)
    hum += 0.05 * np.sin(2 * np.pi * 116.5 * t)
    hum *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.08 * t)
    out = hum.astype(np.float32)
    beat_period = 60.0 / 68.0
    k = 0.0
    while k < dur:
        start = int(k * SR)
        thud = note(48.0, 0.5, amp=0.28, attack=0.004, decay=0.5, harmonics=(1.0, 0.4, 0.0))
        out[start:start + len(thud)] += thud[: n - start]
        k += beat_period
    return fade(reverb(out, mix=0.18), 1.5)


def bed_action(dur=75.0):
    """Действие: пульс восьмыми, шумовые тарелки, подъём."""
    n = int(dur * SR)
    out = np.zeros(n, dtype=np.float32)
    bpm = 132.0
    step = 60.0 / bpm / 2.0
    k = 0.0
    i = 0
    while k < dur:
        start = int(k * SR)
        bass = note(55.0 if i % 4 < 2 else 49.0, step * 0.9, amp=0.22, attack=0.004, decay=step * 0.9,
                    harmonics=(1.0, 0.35, 0.1))
        out[start:start + len(bass)] += bass[: n - start]
        if i % 2 == 1:
            hat = noise(0.05, amp=0.10, lowpass=0.5)
            out[start:start + len(hat)] += hat[: n - start]
        i += 1
        k += step
    t = np.arange(n, dtype=np.float32) / SR
    pad = 0.07 * np.sin(2 * np.pi * 220.0 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.03 * t))
    out += pad.astype(np.float32)
    return fade(reverb(out, mix=0.12), 1.5)


def bed_seam(dur=60.0):
    """Шов: гул, дрожь, шипение чужой геометрии."""
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    base = 0.18 * np.sin(2 * np.pi * 41.0 * t) + 0.1 * np.sin(2 * np.pi * 41.7 * t)
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * 0.35 * t)
    hiss = noise(dur, amp=0.06, lowpass=0.35)
    out = (base * trem).astype(np.float32) + hiss
    return fade(reverb(out, mix=0.35), 2.0)


# --- эффекты --------------------------------------------------------------

def sfx_chime():
    """Системная строка: два тона и хвост."""
    a = note(1174.7, 0.9, amp=0.35, attack=0.003, decay=0.9, harmonics=(1.0, 0.2, 0.05))
    b = note(880.0, 1.4, amp=0.3, attack=0.003, decay=1.4, harmonics=(1.0, 0.25, 0.08))
    out = np.zeros(len(a) + int(0.18 * SR), dtype=np.float32)
    out[: len(a)] += a
    out[int(0.18 * SR): int(0.18 * SR) + len(b)] += b[: len(out) - int(0.18 * SR)]
    return reverb(out, mix=0.4)


def sfx_static(dur=0.7):
    x = noise(dur, amp=0.35, lowpass=0.75)
    e = env_ad(len(x), 0.01, dur)
    return x * e


def sfx_thud():
    return note(44.0, 0.7, amp=0.5, attack=0.002, decay=0.7, harmonics=(1.0, 0.45, 0.15))


def sfx_whoosh(dur=1.0):
    n = int(dur * SR)
    x = rng.standard_normal(n).astype(np.float32)
    # грубый низкочастотный фильтр с меняющейся полосой: прореживание через усреднение окнами
    k = np.linspace(4, 60, n).astype(np.int32)
    y = np.zeros(n, dtype=np.float32)
    acc = 0.0
    for i in range(n):
        a = 1.0 / float(max(2, k[i]))
        acc = acc * (1 - a) + x[i] * a
        y[i] = acc
    e = np.sin(np.pi * np.linspace(0, 1, n, dtype=np.float32)) ** 2
    return y * e * 1.4


def sfx_click():
    return note(2200.0, 0.06, amp=0.3, attack=0.001, decay=0.06, harmonics=(1.0,))


def sfx_door():
    """Скрип клети: шум + низкий тон."""
    n = int(1.2 * SR)
    x = noise(1.2, amp=0.18, lowpass=0.1)
    t = np.arange(n, dtype=np.float32) / SR
    tone = 0.12 * np.sin(2 * np.pi * (90 - 40 * t) * t)
    e = env_ad(n, 0.05, 1.2)
    return (x * 0.6 + tone.astype(np.float32)) * e


if __name__ == "__main__":
    write_wav("calm.wav", bed_calm())
    write_wav("tense.wav", bed_tense())
    write_wav("action.wav", bed_action())
    write_wav("seam.wav", bed_seam())
    write_wav("chime.wav", sfx_chime())
    write_wav("static.wav", sfx_static())
    write_wav("thud.wav", sfx_thud())
    write_wav("whoosh.wav", sfx_whoosh())
    write_wav("click.wav", sfx_click())
    write_wav("door.wav", sfx_door())
