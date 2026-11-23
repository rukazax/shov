#!/usr/bin/env python3
"""Собирает том из глав: единый markdown + статистика в духе «ремесла».

python3 build_book.py            # собрать SHOV-tom1.md и напечатать метрики
"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "SHOV-tom2.md")

TITLE = "Шов"
SUBTITLE = "Книга вторая. Ходок"
EPIGRAPH = (
    "Стучат не для того, чтобы открыли. Стучат, чтобы услышали.\n\n"
    "– из тетради наблюдений, край 4-бис, 2029"
)

SYSTEM_RE = re.compile(
    r"^(Согласование|Метка|Допуск|Ранг|Протечка|Сдвиг|Приказ|Пост|Край|Регистрация|Носитель|Скоба|Тяга|Контакт|Отклонение|Группа)\s*[:.]"
)


def chapter_files():
    files = []
    for f in glob.glob(os.path.join(HERE, "ch*.md")):
        m = re.search(r"ch(\d+)", os.path.basename(f))
        if m:
            files.append((int(m.group(1)), f))
    return [f for _, f in sorted(files)]


def clean(text):
    t = text.replace("\r\n", "\n")
    t = t.replace("—", "–")  # длинное тире в этой серии не используется
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def stats(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    dialogue = sum(1 for l in lines if l.startswith("–"))
    system = sum(1 for l in lines if SYSTEM_RE.match(l))
    scenes = sum(1 for l in lines if re.fullmatch(r"\*\s*\*\s*\*", l))
    sentences = len(re.findall(r"[.!?…]+(?=\s|$)", text))
    words = len(re.findall(r"[А-Яа-яЁёA-Za-z]+", text))
    avg = sum(len(s.split()) for s in re.split(r"(?<=[.!?…])\s+", text) if s.strip())
    sents = [s for s in re.split(r"(?<=[.!?…])\s+", text) if s.strip()]
    return {
        "chars": len(text),
        "chars_ns": len(re.sub(r"\s", "", text)),
        "lines": len(lines),
        "dialogue": dialogue,
        "dialogue_pct": round(dialogue * 100 / max(1, len(lines))),
        "system": system,
        "scenes": scenes,
        "words": words,
        "avg_sentence": round(avg / max(1, len(sents)), 1),
        "sentences": sentences,
    }


def main():
    files = chapter_files()
    parts = []
    toc = []
    body_stats = []

    for f in files:
        raw = clean(open(f, encoding="utf-8").read())
        first = raw.splitlines()[0] if raw else ""
        title = first.lstrip("# ").strip() if first.startswith("#") else os.path.basename(f)
        toc.append(title)
        body_stats.append((title, stats(raw)))
        parts.append(raw)

    body = "\n\n\n".join(parts)
    toc_md = "\n".join(f"{i}. {t}" for i, t in enumerate(toc, start=1))

    head = (
        f"# {TITLE}. {SUBTITLE}\n\n"
        "Текст написан в стилистике Михаила Атаманова (серия «Искажающие реальность»).\n"
        "Это не произведение автора: имена, мир и сюжет — новые.\n\n"
        f"> {EPIGRAPH}\n\n"
        "## Содержание\n\n"
        f"{toc_md}\n\n"
        "---\n\n"
    )
    book = head + body + "\n"
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(book)

    total = stats(body)
    print(f"собрано: {OUT}")
    print(f"глав: {len(files)}  знаков: {total['chars']}  без пробелов: {total['chars_ns']}")
    print(f"слов: {total['words']}  средняя фраза: {total['avg_sentence']} слов")
    print(f"диалог: {total['dialogue_pct']}% строк  сцен: {total['scenes']}  системных строк: {total['system']}")
    print("\nпо главам:")
    for t, s in body_stats:
        print(f"  {s['chars']:7d}  {s['dialogue_pct']:3d}%  {t}")


if __name__ == "__main__":
    main()
