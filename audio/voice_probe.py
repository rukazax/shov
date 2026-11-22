#!/usr/bin/env python3
"""Таблица голосов с замером: темп, тон и медиана основного тона по роли.

    python3 voice_probe.py             # синтезировать по реплике на роль и замерить
    python3 voice_probe.py --table     # только настройки, без синтеза

Нужен, чтобы «у каждого персонажа свой голос» было не обещанием, а цифрой:
если две роли сели на один основной тон, их не различить в диалоге.
Пробные реплики кэшируются в cache/probe/, повторный запуск бесплатный.
"""
import argparse
import asyncio
import os
import subprocess
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render  # noqa: E402

PROBE = "Проверка голоса. Сейчас будет короткая фраза, чтобы снять тембр."
PROBE_DIR = os.path.join(render.CACHE, "probe")


def f0_of(path):
    """Медиана основного тона по автокорреляции, 60–400 Гц."""
    w = wave.open(path, "rb")
    sr, n = w.getframerate(), w.getnframes()
    a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    w.close()
    win, hop = int(sr * 0.04), int(sr * 0.02)
    lo, hi = int(sr / 400), int(sr / 60)
    vals = []
    for st in range(0, len(a) - win, hop):
        fr = a[st:st + win]
        if np.sqrt((fr ** 2).mean()) < 0.02:
            continue
        fr = fr - fr.mean()
        ac = np.correlate(fr, fr, "full")[win - 1:]
        if ac[0] <= 0 or ac[lo:hi].size == 0:
            continue
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] / ac[0] > 0.3:
            vals.append(sr / lag)
    return float(np.median(vals)) if vals else 0.0


async def synth(role, spec, path):
    import edge_tts
    for _ in range(20):
        try:
            await asyncio.wait_for(
                edge_tts.Communicate(PROBE, spec["voice"], rate=spec["rate"],
                                     pitch=spec["pitch"], volume=spec["volume"]).save(path),
                timeout=25)
            if os.path.getsize(path) > 500:
                return True
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(0.3)
    return False


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", action="store_true", help="только настройки, без синтеза")
    args = ap.parse_args()

    os.makedirs(PROBE_DIR, exist_ok=True)
    print(f"{'роль':12s} {'голос':10s} {'темп':>5s} {'тон':>6s} {'громк':>6s} {'f0,Гц':>6s} {'с/знак':>7s}")
    for role, spec in render.VOICES.items():
        voice = spec["voice"].split("-")[2].replace("Neural", "")
        row = (f"{role:12s} {voice:10s} {spec['rate']:>5s} {spec['pitch']:>6s} "
               f"{spec['volume']:>6s}")
        if args.table:
            print(row)
            continue
        mp3 = os.path.join(PROBE_DIR, role + ".mp3")
        wav = os.path.join(PROBE_DIR, role + ".wav")
        if not (os.path.exists(mp3) and os.path.getsize(mp3) > 500):
            if not await synth(role, spec, mp3):
                print(row + "  ОТКАЗ (сервис не отдал звук, повтори позже)")
                continue
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp3, "-ar", "24000",
                        "-ac", "1", wav], check=True)
        d = duration(mp3)
        print(row + f" {f0_of(wav):6.0f} {d / len(PROBE):7.3f}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
