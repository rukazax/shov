#!/usr/bin/env python3
"""Проверка разметки ролей (cast/*.cast.txt) и правка её патчем.

    python3 cast_audit.py                     # сводка по всем главам
    python3 cast_audit.py cast/ch01.cast.txt  # одна глава, с примерами
    python3 cast_audit.py cast/ch01.cast.txt --apply patch.txt

Патч — строки «номер<TAB>роль» (то, что присылает разметчик). Роль вне
VOICES не применяется, чтобы опечатка не убила голос молча.
"""
import collections
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASTDIR = os.path.join(HERE, "cast")

MALE = {"hero", "bocman", "vitya", "muhin", "grisha", "mihalych", "leytenant",
        "tehnik", "narrator", "system"}
FEMALE = {"ganna", "dasha", "lida", "pozharskaya", "agrafena", "female", "babka"}

# имя -> роль. Нужно только для сверки разметки, голоса берутся из render.py
NAMES = [
    (r"Боцман", "bocman"), (r"Вит(?:я|ю|и|е|ей)\b", "vitya"), (r"Мухин", "muhin"),
    (r"Гриш(?:а|у|и|е|ей)\b", "grisha"), (r"Кожин", "grisha"),
    (r"(?:Геннадий Михалыч|Михалыч)", "mihalych"), (r"лейтенант", "leytenant"),
    (r"техник", "tehnik"), (r"(?:Ганна|Ганн)\b", "ganna"), (r"Ткач\b", "ganna"),
    (r"Даш(?:а|у|и|е|ей)\b", "dasha"), (r"девчонк", "dasha"),
    (r"Лид(?:а|у|ы|е)\b", "lida"), (r"Пожарск", "pozharskaya"),
    (r"Аграфен", "agrafena"), (r"бабк|бабул|старух", "babka"),
]

FEM_VERB = re.compile(r"\b(сказала|ответила|спросила|проговорила|произнесла|добавила|"
                      r"заметила|уточнила|подтвердила|буркнула|пробормотала|крикнула|"
                      r"позвала|попросила|предложила|возразила|усмехнулась|улыбнулась|"
                      r"кивнула|вздохнула|помолчала|махнула|посмотрела|повторила|"
                      r"продолжила|засмеялась|фыркнула|огрызнулась|прошептала|шепнула|"
                      r"объяснила|рассказала|подумала|испугалась|обрадовалась|"
                      r"согласилась|поправила|показала|вышла|вошла)\b", re.I)
MALE_VERB = re.compile(r"\b(сказал|ответил|спросил|проговорил|произнёс|произнес|добавил|"
                       r"заметил|уточнил|подтвердил|буркнул|пробормотал|крикнул|позвал|"
                       r"попросил|предложил|возразил|усмехнулся|улыбнулся|кивнул|"
                       r"вздохнул|помолчал|махнул|посмотрел|повторил|продолжил|"
                       r"засмеялся|фыркнул|огрызнулся|прошептал|шепнул|объяснил|"
                       r"рассказал|подумал|испугался|обрадовался|согласился|"
                       r"поправил|показал|вышел|вошёл|вошел)\b", re.I)


ATTRIB = (r"(?:сказал|ответил|спросил|проговорил|произнёс|произнес|добавил|заметил|"
          r"уточнил|подтвердил|буркнул|пробормотал|крикнул|позвал|попросил|предложил|"
          r"возразил|усмехнулся|улыбнулся|кивнул|вздохнул|помолчал|махнул|посмотрел|"
          r"повторил|продолжил|засмеялся|фыркнул|огрызнулся|прошептал|шепнул|объяснил|"
          r"рассказал|согласился|поправил|показал)")
# рассказчик — первое лицо: «сказал он» в его реплике значит, что говорил не он,
# а «сказал я» у чужой роли значит, что говорил герой. Это главная причина
# перепутанных hero/vitya: имена и род глагола такую инверсию не ловят.
SAID_HE = re.compile(r"\b" + ATTRIB + r"\s+он[аы]?\b", re.I)
SAID_I = re.compile(r"\b" + ATTRIB + r"\s+я\b", re.I)


ATTR_RE = re.compile(r"\\b" + ATTRIB + r"\\b", re.I)

def name_roles(text):
    """Роли, чьё имя стоит при глаголе речи — то есть кто говорит.

    Просто упомянутое имя ничего не значит: «Михалыч же её поставил» говорит
    Витя, а не Михалыч. Поэтому имя засчитывается только рядом с глаголом речи.
    Звательные в начале реплики («Михалыч, ну...») не в счёт.
    """
    out = []
    for pat, role in NAMES:
        for m in re.finditer(pat, text, re.I):
            rest = text[m.end():].lstrip()
            if m.start() <= 2 and (rest[:1] in ",.!?–-" or not rest):
                continue
            win = text[max(0, m.start() - 35):m.end() + 35]
            if not ATTR_RE.search(win):
                continue
            out.append(role)
    return out


def read_cast(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        p = line.rstrip("\n").split("\t")
        if len(p) >= 4:
            rows.append((int(p[0]), p[1], p[2], p[3]))
    return rows


def audit(rows):
    bad = []
    for idx, kind, role, text in rows:
        if kind != "dialogue":
            continue
        if role == "hero":
            m = SAID_HE.search(text)
            if m:
                bad.append((idx, role, "герой, а сказано «%s»" % m.group(0), text))
                continue
        elif role not in ("narrator", "system"):
            m = SAID_I.search(text)
            if m:
                bad.append((idx, role, "чужая роль, а сказано «%s»" % m.group(0), text))
                continue
        nr = name_roles(text)
        if nr and role not in nr and role not in ("hero", "narrator", "system"):
            bad.append((idx, role, "имя " + "/".join(sorted(set(nr))), text))
            continue
        if role in MALE:
            m = FEM_VERB.search(text)
            if m and not MALE_VERB.search(text):
                bad.append((idx, role, "женский глагол «%s»" % m.group(1), text))
        elif role in FEMALE:
            m = MALE_VERB.search(text)
            if m and not FEM_VERB.search(text):
                bad.append((idx, role, "мужской глагол «%s»" % m.group(1), text))
    return bad


def apply_patch(rows, patch_path, voices):
    patch = {}
    for line in open(patch_path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"[\t ]+", line)
        if len(parts) < 2 or not parts[0].isdigit():
            continue
        role = parts[1].strip()
        if role not in voices:
            print("  нет роли «%s» в строке: %s" % (role, line), file=sys.stderr)
            continue
        patch[int(parts[0])] = role
    seen, out, changed = set(), [], 0
    for idx, kind, role, text in rows:
        want = patch.get(idx)
        if want:
            seen.add(idx)
            if want != role:
                print("  #%d: %s → %s   %s" % (idx, role, want, text[:60]))
                role, changed = want, changed + 1
        out.append((idx, kind, role, text))
    lost = set(patch) - seen
    if lost:
        print("  в главе нет блоков: %s" % sorted(lost), file=sys.stderr)
    return out, changed


def main():
    args = [a for a in sys.argv[1:]]
    patch = None
    if "--apply" in args:
        i = args.index("--apply")
        patch = args[i + 1]
        del args[i:i + 2]
    paths = args or sorted(glob.glob(os.path.join(CASTDIR, "ch*.cast.txt")))

    voices = set()
    try:
        sys.path.insert(0, HERE)
        from render import VOICES
        voices = set(VOICES)
    except Exception:
        voices = MALE | FEMALE

    total = flagged = 0
    per_chapter = []
    for path in paths:
        rows = read_cast(path)
        if patch:
            rows, changed = apply_patch(rows, patch, voices)
            stem = os.path.basename(path)
            with open(path, "w", encoding="utf-8") as f:
                f.write("# %s — кто говорит. Колонки: номер, тип, роль, текст.\n" % stem)
                f.write("# Правится только роль. Строки на # игнорируются.\n")
                f.write("# Роли: " + " ".join(sorted(voices)) + "\n")
                for idx, kind, role, text in rows:
                    f.write("%d\t%s\t%s\t%s\n" % (idx, kind, role, text))
            print("%s: исправлено %d из %d" % (stem, changed, len(rows)))
        bad = audit(rows)
        total += len(rows)
        flagged += len(bad)
        per_chapter.append((len(bad), os.path.basename(path).split(".")[0], len(rows)))
        if len(paths) == 1:
            for idx, role, why, text in bad:
                print("  %4d %-11s %-24s %s" % (idx, role, why, text[:70]))

    if len(paths) > 1:
        print("блоков: %d, под вопросом: %d" % (total, flagged))
        for n, ch, cnt in sorted(per_chapter, reverse=True):
            print("  %-14s %4d из %4d" % (ch, n, cnt))


if __name__ == "__main__":
    main()
