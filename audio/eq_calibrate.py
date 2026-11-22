#!/usr/bin/env python3
"""Подгонка кривой тембра под эталон по замеру полос.

    python3 eq_calibrate.py [наша_дорожка] [--apply]

Сравнивает спектр нашей дорожки со спектром эталона 1С-Паблишинг по 14 полосам
и правит eq_curve.json на 0.7 от разницы (полный шаг перелетает: доли полос
не складываются линейно). Дальше render.py берёт кривую из файла.
"""
import json
import subprocess
import sys

import numpy as np

SR = 24000
BANDS = [(50, 80), (80, 120), (120, 180), (180, 280), (280, 450), (450, 700),
         (700, 1100), (1100, 1700), (1700, 2500), (2500, 3500), (3500, 4500),
         (4500, 6000), (6000, 8000), (8000, 11000)]
DAMP = 0.7


def spec(p):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", p, "-f", "f32le",
                          "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    w = int(0.04 * SR)
    acc = np.zeros(len(BANDS))
    cnt = 0
    for i in range(0, len(x) - w, w):
        seg = x[i:i + w].astype(np.float64)
        if np.sqrt((seg ** 2).mean()) < 0.02:
            continue
        sp = np.abs(np.fft.rfft(seg * np.hanning(w)))
        fr = np.fft.rfftfreq(w, 1 / SR)
        tot = sp.sum() + 1e-9
        for j, (lo, hi) in enumerate(BANDS):
            acc[j] += sp[(fr >= lo) & (fr < hi)].sum() / tot
        cnt += 1
    return acc / max(cnt, 1)


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    args = [a for a in args if a != "--apply"]
    ours = args[0] if args else "out/ch00_vvedenie.mp3"

    curve = json.load(open("eq_curve.json", encoding="utf-8"))
    ref = spec(curve["reference"])
    cur = spec(ours)
    pts = curve["points"]

    deltas = []
    for (lo, hi), r, o in zip(BANDS, ref, cur):
        d = 20 * np.log10(max(o, 1e-9) / max(r, 1e-9))
        deltas.append(d)
        print(f"{lo:5d}-{hi:5d}  1С {100*r:5.2f}%  наш {100*o:5.2f}%  {d:+6.1f} дБ")

    # дельта каждой полосы переносится на ближайшую точку кривой
    for (lo, hi), d in zip(BANDS, deltas):
        mid = (lo * hi) ** 0.5
        j = min(range(len(pts)), key=lambda k: abs(np.log2(pts[k][0] / mid)))
        pts[j][1] = round(pts[j][1] - DAMP * d, 2)
    rms = float(np.sqrt(np.mean(np.square(deltas))))
    print(f"расхождение по полосам: {rms:.1f} дБ"
          f"{' (цель < 1.5)' if rms >= 1.5 else ' — в норме'}")
    print("новая кривая: " + " ".join(f"{f:.0f}:{g:+.1f}" for f, g in pts))
    if apply:
        curve["points"] = pts
        json.dump(curve, open("eq_curve.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("eq_curve.json обновлён")


if __name__ == "__main__":
    main()
