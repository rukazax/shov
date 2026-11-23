#!/usr/bin/env python3
"""Пунктуация и регистр для русского текста без знаков — RUPunct_small на CPU.

Модель: RUPunct/RUPunct_small — ruBERT-tiny2 (3 слоя, hidden 312, 116 МБ),
дообученная на расстановку знаков и восстановление регистра. Работает на CPU,
GPU не нужен. На входе ждёт текст БЕЗ знаков и в нижнем регистре — ровно то,
что отдаёт распознавание речи.

Зачем в конвейере: знаки препинания — это паузы и интонация. edge-tts читает
«,» и «.» по-разному, поэтому текст из распознавания (диктовка, чужой
аудиорип) без пунктуации звучит ровно. Плюс это проверка книги: на
литературном тексте модель показывает, где знака не хватает.

Интерпретатор (нужен torch + transformers):
    /srv/apps/models/venv-teratts/bin/python

Режимы:
    --apply FILE   расставить знаки в сыром тексте (stdout или -o)
    --bench FILES  снять знаки с готовых глав, вернуть моделью и посчитать
                   precision/recall/F1 по каждому знаку — замер на своей книге
    --check FILES  то же, но показать места, где модель спорит с автором
                   (кандидаты «здесь не хватает запятой»), файлы не правит
    --selftest     проверить разбор и счёт на синтетике, без модели

Примеры:
    python punct.py --bench ../BOOK01/ch*.md
    python punct.py --check ../BOOK01/ch01.md --threshold 0.9
    python punct.py --apply /tmp/asr.txt -o /tmp/asr.punct.txt
"""
import argparse
import json
import os
import re
import sys
import time

MODEL = os.environ.get("PUNCT_MODEL", "RUPunct/RUPunct_small")
MAX_WORDS = 400          # кусок на один вызов модели; абзацы короче — целиком

WORD_RE = re.compile(r"[А-Яа-яЁёA-Za-z0-9]+(?:[-'’][А-Яа-яЁёA-Za-z0-9]+)*")
MARK_RE = re.compile(r"\.\.\.|[.,!?…:;—–]")
MARK_MAP = {
    "PERIOD": ".", "COMMA": ",", "QUESTION": "?", "VOSKL": "!",
    "TIRE": "—", "DVOETOCHIE": ":", "PERIODCOMMA": ";", "DEFIS": "—",
    "MNOGOTOCHIE": "…", "QUESTIONVOSKL": "?!", "O": "",
}
DASHES = {"—", "–", "-"}
SENTENCE_END = ".!?…"


def norm_marks(s):
    """Знаки из куска текста в канонический вид: «...» → «…», «–» → «—»."""
    out = []
    for m in MARK_RE.finditer(s):
        m = m.group(0)
        if m == "...":
            m = "…"
        elif m in DASHES:
            m = "—"  # тире: в замер F1 не идёт, но для --check это законный знак
        out.append(m)
    joined = "".join(out)
    return "?!" if joined in ("?!", "!?") else joined


def words_marks(line):
    """Строка → (слова, знак_после_каждого_слова). Знак в начале строки
    (диалоговое тире) отбрасывается: это разметка, а не пунктуация."""
    words, marks, pos = [], [], 0
    for m in WORD_RE.finditer(line):
        if words:
            marks.append(norm_marks(line[pos:m.start()]))
        words.append(m.group(0))
        pos = m.end()
    if words:
        marks.append(norm_marks(line[pos:]))
    return words, marks


def label_mark(label):
    """entity_group → знак. UPPER_*/UPPER_TOTAL_* отличаются только регистром."""
    base = label
    for prefix in ("UPPER_TOTAL_", "UPPER_", "LOWER_"):
        if base.startswith(prefix):
            base = base[len(prefix):]
            break
    if base.startswith("TOTAL_"):
        base = base[6:]
    return MARK_MAP.get(base, "")


def want_case(label):
    """0 — как есть, 1 — с большой, 2 — капсом."""
    if label.startswith("UPPER_TOTAL_"):
        return 2
    if label.startswith("UPPER_"):
        return 1
    return 0


def apply_case(word, mode):
    if mode == 2:
        return word.upper()
    if mode == 1 and word:
        return word[0].upper() + word[1:]
    return word


def predict(clf, words):
    """Слова без знаков → [(слово, знак, уверенность, регистр)] по позициям."""
    text = " ".join(words).lower()
    out = []
    for e in clf(text):
        parts = e["word"].strip().split()
        if not parts:
            continue
        mark, score, mode = label_mark(e["entity_group"]), float(e["score"]), \
            want_case(e["entity_group"])
        out.extend((w, "", score, mode) for w in parts[:-1])
        out.append((parts[-1], mark, score, mode))
    return out


def chunk(words, n=MAX_WORDS):
    for i in range(0, len(words), n):
        yield words[i:i + n]


def read_paragraphs(path):
    """Абзацы: непустые строки без заголовков, разделителей сцен и прочей разметки."""
    paras = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if re.fullmatch(r"\*\s*\*\s*\*", line) or re.fullmatch(r"[-—–_*\s]{3,}", line):
                continue
            paras.append((lineno, line))
    return paras


def score(gold_marks, pred_marks):
    """Счёт по позициям: {знак: [tp, fp, fn]}."""
    res = {}
    for g, p in zip(gold_marks, pred_marks):
        if g == p:
            if g:
                res.setdefault(g, [0, 0, 0])[0] += 1
            continue
        if g:
            res.setdefault(g, [0, 0, 0])[2] += 1
        if p:
            res.setdefault(p, [0, 0, 0])[1] += 1
    return res


def micro(res):
    tp = sum(v[0] for v in res.values())
    fp = sum(v[1] for v in res.values())
    fn = sum(v[2] for v in res.values())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def render(pred):
    """(слово, знак, уверенность, регистр) → строка. Начало предложения —
    всегда с большой буквы, даже если модель ошиблась с меткой. Дефис
    приклеивается к соседям: токенизатор отдаёт «чью-то» тремя кусками."""
    out, sentence_start, glue = [], True, False
    for w, mark, _score, mode in pred:
        if w in {"-", "'", "’"}:          # дефис/апостроф внутри слова
            if out:
                out[-1] += w
                glue = True
            continue
        piece = apply_case(w, max(mode, 1) if sentence_start else mode)
        if glue and out:
            out[-1] += piece
        else:
            out.append(piece)
        glue = False
        sentence_start = bool(mark) and mark[0] in SENTENCE_END
        out[-1] += (" " + mark) if "—" in mark else mark   # тире отделяют пробелами
    return " ".join(out)


def run_bench(clf, files):
    total, chars, words_total, skipped = {}, 0, 0, 0
    t0 = time.time()
    for path in files:
        for lineno, para in read_paragraphs(path):
            gold_w, gold_m = words_marks(para)
            if len(gold_w) < 3:
                continue
            pred = [p for part in chunk(gold_w) for p in predict(clf, part)]
            if [p[0] for p in pred] != [w.lower() for w in gold_w]:
                skipped += 1
                continue
            pred_m = [p[1].replace("—", "") for p in pred]
            gold_m = [x.replace("—", "") for x in gold_m]
            for k, v in score(gold_m, pred_m).items():
                cur = total.setdefault(k, [0, 0, 0])
                for i in range(3):
                    cur[i] += v[i]
            chars += len(para)
            words_total += len(gold_w)
    dt = time.time() - t0
    p, r, f = micro(total)
    print(f"файлов {len(files)} · слов {words_total} · абзацев пропущено {skipped} "
          f"(слова не сошлись)")
    print(f"микро: P {p:.3f}  R {r:.3f}  F1 {f:.3f} · "
          f"{chars / dt:.0f} зн/с · {dt:.1f} с на {chars} знаков")
    print(f"{'знак':<6}{'gold':>7}{'pred':>7}{'tp':>7}{'P':>7}{'R':>7}{'F1':>7}")
    for k in sorted(total, key=lambda x: -sum(total[x])):
        tp, fp, fn = total[k]
        pp = tp / (tp + fp) if tp + fp else 0
        rr = tp / (tp + fn) if tp + fn else 0
        ff = 2 * pp * rr / (pp + rr) if pp + rr else 0
        print(f"{k:<6}{tp + fn:>7}{tp + fp:>7}{tp:>7}{pp:>7.3f}{rr:>7.3f}{ff:>7.3f}")
    return total


def run_check(clf, files, threshold, limit):
    cand = []
    t0 = time.time()
    for path in files:
        for n, para in read_paragraphs(path):
            gold_w, gold_m = words_marks(para)
            if len(gold_w) < 3:
                continue
            pred = [p for part in chunk(gold_w) for p in predict(clf, part)]
            if [p[0] for p in pred] != [w.lower() for w in gold_w]:
                continue
            # ищем только ПРОПУЩЕННЫЕ знаки; двоеточие перед репликой,
            # многоточие и обрывки в кавычках — стиль, а не ошибка
            tail = para.rstrip()
            if tail.endswith((":", "…", "«", "–")):
                continue
            for i, ((_, pm, sc, _), gm) in enumerate(zip(pred, gold_m)):
                if "—" in gm or "—" in pm:
                    continue          # автор поставил тире — это не пропуск
                if pm and sc >= threshold and not gm and pm in (",", ".", "?"):
                    cand.append({
                        "file": os.path.basename(path), "line": n, "pos": i,
                        "gold": gm, "model": pm, "score": round(sc, 3),
                        "text": " ".join(gold_w[max(0, i - 6):i + 7]),
                    })
    cand.sort(key=lambda c: -c["score"])
    print(f"кандидатов {len(cand)} за {time.time() - t0:.0f} с "
          f"(порог {threshold}); показаны {min(limit, len(cand))}")
    for c in cand[:limit]:
        kind = "нет знака" if not c["gold"] else f"{c['gold']} → {c['model']}"
        print(f"\n{c['file']}:{c['line']} · {kind} · {c['score']}")
        print(f"  …{c['text']}…")
    return cand


def run_apply(clf, path, out):
    text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    t0, res, words_n = time.time(), [], 0
    for para in paras:
        words = WORD_RE.findall(para)
        if words:
            res.append(render([p for part in chunk(words) for p in predict(clf, part)]))
            words_n += len(words)
    joined = "\n\n".join(res)
    dt = time.time() - t0
    if out:
        open(out, "w", encoding="utf-8").write(joined + "\n")
        print(f"→ {out}: {len(res)} абзацев, {words_n} слов, {dt:.1f} с")
    else:
        print(joined)
    return joined


def selftest():
    w, m = words_marks("– Я и глажу, – сказал я. – Только он гладиться не хочет.")
    assert w[:3] == ["Я", "и", "глажу"], w
    assert m[0] == "" and m[2] == ",—", m
    assert norm_marks("...") == "…" and norm_marks("–") == "—"
    assert norm_marks("?!") == "?!"
    res = score(["", ",", ""], ["", ",", "."])
    assert res[","] == [1, 0, 0] and res["."] == [0, 1, 0], res
    p, r, f = micro(res)
    assert abs(p - 0.5) < 1e-9 and abs(r - 1.0) < 1e-9, (p, r, f)
    assert label_mark("UPPER_COMMA") == "," and label_mark("LOWER_TOTAL_PERIOD") == "."
    assert want_case("UPPER_TOTAL_O") == 2 and want_case("LOWER_O") == 0
    pred = [("привет", "", 1.0, 0), ("как", ",", 1.0, 0), ("дела", ".", 1.0, 2)]
    assert render(pred) == "Привет как, ДЕЛА.", render(pred)
    pred = [("чью", "", 1.0, 1), ("-", "", 1.0, 0), ("то", ".", 1.0, 0)]
    assert render(pred) == "Чью-то.", render(pred)
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", metavar="FILE", help="файл с сырым текстом или - для stdin")
    ap.add_argument("--bench", nargs="+", metavar="FILES", help="главы для замера (со знаками)")
    ap.add_argument("--check", nargs="+", metavar="FILES", help="главы для поиска спорных мест")
    ap.add_argument("--threshold", type=float, default=0.9, help="порог уверенности для --check")
    ap.add_argument("--limit", type=int, default=20, help="сколько кандидатов печатать")
    ap.add_argument("-o", "--out", help="куда писать результат/кандидатов")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return
    if not (args.apply or args.bench or args.check):
        ap.error("нужен один из режимов: --apply, --bench, --check")

    from transformers import AutoTokenizer, pipeline

    tk = AutoTokenizer.from_pretrained(MODEL, strip_accents=False, add_prefix_space=True)
    clf = pipeline("ner", model=MODEL, tokenizer=tk,
                   aggregation_strategy="first", device=-1)

    if args.check:
        cand = run_check(clf, args.check, args.threshold, args.limit)
        if args.out:
            json.dump(cand, open(args.out, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            print(f"→ {args.out}")
        return
    if args.bench:
        run_bench(clf, args.bench)
        return
    run_apply(clf, args.apply, args.out)


if __name__ == "__main__":
    main()
