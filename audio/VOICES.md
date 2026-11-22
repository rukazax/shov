<p align="center"><img src="../assets/banner.svg" alt="Шов — серия на 30 томов" width="100%"></p>

<h1 align="center">Голоса «Шова»</h1>
<p align="center">Как озвучка перестала звучать как робот — и на чём остановились</p>

<p align="center">
  <b>RU</b> · <a href="#english">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/образцов-3-2f6fed?style=flat-square" alt="3 образца">
  <img src="https://img.shields.io/badge/движков_проверено-3-8957e5?style=flat-square" alt="3 движка">
  <img src="https://img.shields.io/badge/русский-родной-3fb950?style=flat-square" alt="русский родной">
  <img src="https://img.shields.io/badge/громкость_−20.5_LUFS-8b949e?style=flat-square" alt="−20.5 LUFS">
  <img src="https://img.shields.io/badge/128_кбит%2Fс-8b949e?style=flat-square" alt="128 кбит/с">
</p>

**Разделы:** [Как слушать](#как-слушать) · [С чего началось](#с-чего-началось) · [Что было не так с эталонами](#что-было-не-так-с-эталонами) · [Движки](#движки) · [Что построено](#что-построено) · [Замеры](#замеры) · [Что дальше](#что-дальше) · [English](#english)

---

## Как слушать

Один и тот же диалог первой главы, три раза, тремя движками. Четырнадцать реплик: описание, вопрос, восклицание, раздражение, крик, казённая речь начальника. Слушать надо не «как звучит тембр», а слышно ли, что человек живой.

| Движок | Образец | Длина | Громкость | Вердикт |
|---|---|---|---|---|
| **F5-TTS_RUSSIAN** | [`tests/f5_cast_demo.mp3`](tests/f5_cast_demo.mp3) | 43,1 с | −20,5 LUFS | **выбран** |
| XTTS v2 | [`tests/xtts_cast_demo.mp3`](tests/xtts_cast_demo.mp3) | 50,2 с | −20,5 LUFS | отклонён: акцент |
| Chatterbox | [`tests/cb_cast_demo.mp3`](tests/cb_cast_demo.mp3) | 51,0 с | −19,7 LUFS | отклонён: акцент |

| F5 | Реплика | Голос | f0 |
|---|---|---|---|
| 0:00 | «Утро началось с бабки и сломанного лифта» | Римский | 130 Гц |
| 0:03 | бабка: «Ты его не рви, ты его гладь!» | Жильцова | 236 Гц |
| 0:05 | герой: «Я и глажу. Только он гладиться не хочет» | Римский | 156 Гц |
| 0:09 | бабка: «Мне в поликлинику к девяти!» | Жильцова | 220 Гц |
| 0:11 | герой: «Успеете. Сейчас поднимем» | Римский | 105 Гц |
| 0:13 | Михалыч: «По факту обращения граждан» | Потеряев | 149 Гц |
| 0:16 | герой: «По какому факту?» | Римский | 178 Гц |
| 0:17 | Михалыч: «В рамках регламента мы обязаны» | Потеряев | 137 Гц |
| 0:21 | герой: «Там лифта нет! Там шахта!» | Римский | 205 Гц |
| 0:23 | Жарова: «Родственница ваша, если я не ошибаюсь» | Чиркова | 233 Гц |
| 0:26 | герой: «На мяуканье?» | Римский | 161 Гц |
| 0:28 | «Двенадцатого августа над Северным Уралом появилась полоса…» | Римский | 124 Гц |
| 0:38 | герой: «А до меня сюда кто-нибудь лазил?» | Римский | 152 Гц |
| 0:40 | бабка: «Сеня, звони Вите, у него ключи!» | Жильцова | 205 Гц |

Все три файла сведены в моно, 48 кГц, 128 кбит/с, громкость выровнена по −20 LUFS — чтобы сравнивать голоса, а не громкость. Пауз длиннее секунды внутри нет: проверено `silencedetect`.

## С чего началось

Черновик тома озвучен на `edge-tts`: семнадцать ролей, тридцать четыре дорожки, подложка, эффекты. Для черновика — отлично. Для «как у 1С-Паблишинг» — нет: голоса читают ровно, эмоций в них ноль, и это слышно с первой фразы.

Брать готовые записи 1С нельзя — по закону. А снять мерки можно: темп, громкость, тембр. Отсюда и весь заход: одиннадцать десятисекундных эталонов из записей Римского, Жильцовой, Чирковой и Потеряева — и клонирование голоса по ним.

Сами записи в репозиторий не выложены: это чужие права. Лежат локально, служат образцом для клонирования и для замеров.

## Что было не так с эталонами

Тут я долго искал виноватого в движке, а виноват был в эталонах. Мерки снимались нарезкой из YouTube-рипов по грубым временным меткам, и три эталона из одиннадцати оказались мусором:

| Эталон | Что в нём было на самом деле |
|---|---|
| `female2` (Жарова) | заставка студии, музыка |
| `male_poteryaev` (Потеряев) | музыка без речи |
| `hero_tense` (Римский, напряжённый) | музыка без речи |

Прогон распознавания по всем эталонам показал это одной таблицей: `[музыка]`, «Издательство 1С-Паблишинг и студия МДМ», «Редактор субтитров А. Синецкая». Клонировать голос с записи, где нет голоса, — и получать потом «русский звучит как чужой». Занавес.

Хуже: первая версия демо (XTTS и Chatterbox в репозитории) сделана на этих же битых эталонах. То есть замечание «русский чужой» было справедливо вдвойне.

Второй капкан — границы нарезки. Эталон для героя заканчивался на половине фразы: «…но далее суд». И F5-TTS честно дочитывал этот хвост в каждую реплику — короткие строки начинались со слова «суд». Пять реплик из шести.

Лечение простое и машинное:

- резать эталон **по границам предложений**, а не по секундомеру — у нас для этого есть SRT от `whisper-cli` по всему рипу;
- текст эталона брать из того же сегмента, а не из вольного пересказа — эталон и его расшифровка обязаны совпадать;
- проверять каждый эталон отдельно: распознать, посмотреть f0, отбросить всё, где нет речи.

После этого разборчивость реплик выросла с 0,11–0,41 до 0,85–1,00 по сходству с исходным текстом.

## Движки

| Кандидат | Что это на самом деле | Влезает в 8 ГБ | Вердикт |
|---|---|---|---|
| «moe» → Fish Audio Drama 3 | 35B mixture-of-experts, 70 ГБ весов | нет | отклонён: железо |
| «strata» → Stra / stra.ai | облако, клон с 30 с, весов нет | — | отклонён: чёрный ящик, оплата за главу |
| ZONOS2 (Zyphra) | MoE, русский нет | — | мимо |
| XTTS v2 (Coqui) | zero-shot клон с 10–12 с | да | **отклонён: акцент** |
| Chatterbox Multilingual | 23 языка, ручка эмоций | да | **отклонён: акцент** |
| **F5-TTS_RUSSIAN** | файнтюн F5-TTS на 5 000 ч русской речи, клон с 10 с | да, 1,35 ГБ | **выбран** |

Почему F5. Он не «понимает русский», он на нём **обучен**: 4 000 часов своего датасета, 400 часов аудиокниг Sova, 240 часов Common Voice, 180 часов LibriHeavy. Управление ударением — символом `+` перед ударной гласной (`молок+о → молокó`). Голос клонируется с эталона, интонация берётся оттуда же: спокойный эталон — ровное чтение, раздражённый — раздражение. Отдельной ручки эмоций, как у Chatterbox, нет; вместо неё **банк эталонов** на каждое настроение.

Что с этим честно: тембр держится, темп держится, «живость» появляется — но крик и шёпот надо приносить своим эталоном. Для героя, который в одном абзаце шутит, а в следующем орёт, это значит два-три эталона на роль, а не один.

## Что построено

Windows-машина рядом: RTX 2080 Max-Q (8 ГБ), Python 3.10, `torch 2.5.1+cu124`, CUDA. Три HTTP-сервера, каждый принимает JSON и отдаёт wav:

```
:8765  XTTS v2                 numpy 2.x      (оставлен для сравнений)
:8766  Chatterbox Multilingual  numpy < 2      (оставлен для сравнений)
:8767  F5-TTS_RUSSIAN v2       24 кГц, vocos   ← рабочий
```

Три, а не один, потому что numpy несовместим: Chatterbox требует старый, XTTS новый. Один venv этого не держит.

Модель и обвязка:

- `Misha24-10/F5-TTS_RUSSIAN`, чекпоинт `F5TTS_v1_Base_v2` (`model_last_inference.safetensors`, 1,35 ГБ), словарь 2 544 символа с кириллицей, вокодер vocos 24 кГц;
- эталоны 24 кГц моно, 6–12 с, каждый со своей расшифровкой в `refs_text.json`;
- отбор дублей: три прогона с разными seed и `cfg_strength` 2,0/2,6/3,2, победитель — по сходству расшифровки с текстом (`difflib` по нормализованным словам) и по попаданию f0 в диапазон роли;
- калибровка тембра по эталону 1С лежит в [`eq_curve.json`](eq_curve.json) — пятнадцать точек от 55 Гц до 12 кГц;
- каждая дорожка нормализуется `loudnorm` до −20 LUFS, −2 dBTP.

Скорость: реплика в 30–40 знаков синтезируется за 2–3 с на 8 ГБ видеопамяти. Глава тома (17–23 тыс. знаков) — это 30–45 минут с отбором дублей.

## Замеры

Не «на слух», а цифрами. Разборчивость — сходство расшифровки `whisper-base` с исходным текстом:

| Реплика | Сходство |
|---|---|
| «Мне в поликлинику к девяти!» | 0,85 |
| «По факту обращения граждан» | 1,00 |
| «Там лифта нет! Там шахта!» | 1,00 |
| «Родственница ваша, если я не ошибаюсь» | 1,00 |
| «Двенадцатого августа над Северным Уралом…» | 0,79 |
| «На мяуканье?» | 0,82 |

Тембр — медиана основного тона по репликам против эталона: 236 и 220 Гц у бабки (эталон 183), 149 и 137 Гц у Михалыча (эталон 161), 130 и 124 Гц у рассказчика (эталон 124). Голос узнаётся, провалов в женский регистр нет.

Слабые места, которые видно в цифрах: очень короткие реплики (меньше 20 знаков) иногда «съезжают» по тону вверх — вопрос «По какому факту?» уехал на 178 Гц при эталоне 124. Лечится отбором дублей и тем, что короткие реплики лучше склеивать с соседними.

## Что дальше

1. Банк эмоциональных эталонов: спокойный, раздражённый, крик, шёпот, ирония — по три на роль. Это то, чего F5 не умеет без эталона.
2. Ударения: подключить `RUAccent` и подавать текст с `+`, иначе «замок» и «замок» читаются как повезёт.
3. Перевести `render.py` с `edge-tts` на `:8767` и перерендерить 34 дорожки тома.
4. Прогнать главу целиком, а не сцену: десять минут показывают то, что скрывают десять секунд.

Выбор владельца записывается здесь, в таблице выше, как только он будет.

---

`#tts #f5-tts #voice-cloning #audiobook #russian #local-ai #vocos`

---

## English

<p align="center">
  <a href="#голоса-шова">Русский</a> · <b>English</b>
</p>

### How to listen

The same first-chapter dialogue, three times, three engines. Fourteen lines: narration, a question, an exclamation, irritation, a shout, bureaucratic speech. The test is not "does the timbre sound nice" but "does this person sound alive".

| Engine | Sample | Length | Loudness | Verdict |
|---|---|---|---|---|
| **F5-TTS_RUSSIAN** | [`tests/f5_cast_demo.mp3`](tests/f5_cast_demo.mp3) | 43.1 s | −20.5 LUFS | **chosen** |
| XTTS v2 | [`tests/xtts_cast_demo.mp3`](tests/xtts_cast_demo.mp3) | 50.2 s | −20.5 LUFS | rejected: accent |
| Chatterbox | [`tests/cb_cast_demo.mp3`](tests/cb_cast_demo.mp3) | 51.0 s | −19.7 LUFS | rejected: accent |

All three are mono, 48 kHz, 128 kbps, normalized to −20 LUFS, so you compare voices rather than loudness. No silence gap over one second inside: checked with `silencedetect`.

### Where it started

The draft volume is voiced with `edge-tts`: seventeen roles, thirty-four tracks, ambient beds, effects. Fine for a draft, useless for "sounds like 1C-Publishing": the voices read evenly, with zero emotion, and you hear it in the first sentence.

Copying the 1C recordings is not an option — legally. Measuring them is: tempo, loudness and timbre were taken from Rimsky, Zhiltsova, Chirkova and Poteryaev as ten-second reference clips. The clips stay local; foreign recordings are not committed.

### What was wrong with the references

I spent hours blaming engines when the references were at fault. Three of eleven clips had no speech in them at all:

| Clip | What it actually contained |
|---|---|
| `female2` (Zharova) | the studio ident, music |
| `male_poteryaev` (Poteryaev) | music, no speech |
| `hero_tense` (Rimsky, tense) | music, no speech |

A recognition pass over every clip showed it in one table: `[music]`, "1C-Publishing and MDM Vision studio present", "Subtitle editor A. Sinetskaya". Cloning a voice from a recording that holds no voice — and then complaining that Russian sounds foreign.

Worse: the first demo (XTTS and Chatterbox, in the repo) was built on those same broken clips. The remark "the Russian sounds foreign" was doubly fair.

The second trap was clip boundaries. The hero's reference ended mid-phrase: "…but then the court". F5-TTS dutifully read that tail into every line — short lines began with the word "court". Five lines out of six.

The fix is mechanical:

- cut the reference **on sentence boundaries**, not by a stopwatch — we have `whisper-cli` SRT for every rip;
- take the reference text from that same segment, so clip and transcript match;
- verify every clip: recognize it, measure f0, discard anything without speech.

Readability went from 0.11–0.41 to 0.85–1.00 against the source text.

### The engines

| Candidate | What it really is | Fits 8 GB | Verdict |
|---|---|---|---|
| "moe" → Fish Audio Drama 3 | 35B mixture-of-experts, 70 GB of weights | no | rejected: hardware |
| "strata" → Stra / stra.ai | cloud clone from 30 s, no weights | — | rejected: black box, paid per chapter |
| ZONOS2 (Zyphra) | MoE, no Russian | — | out |
| XTTS v2 (Coqui) | zero-shot clone from 10–12 s | yes | **rejected: accent** |
| Chatterbox Multilingual | 23 languages, emotion knob | yes | **rejected: accent** |
| **F5-TTS_RUSSIAN** | F5-TTS fine-tuned on 5,000 h of Russian, clone from 10 s | yes, 1.35 GB | **chosen** |

Why F5. It is not "aware of Russian", it is **trained** on it: 4,000 h own dataset, 400 h of Sova audiobooks, 240 h Common Voice, 180 h LibriHeavy. Stress is controlled with a `+` before the stressed vowel (`молок+о → молокó`). The timbre is cloned from the reference and so is the intonation: a calm clip gives even reading, an irritated one gives irritation. There is no emotion knob like Chatterbox's; instead there is a **reference bank** per mood.

Honestly: timbre holds, pace holds, "aliveness" appears — but a shout or a whisper must be brought as a reference of its own. For a hero who jokes in one paragraph and shouts in the next, that means two or three clips per role, not one.

### What was built

A Windows box next door: RTX 2080 Max-Q (8 GB), Python 3.10, `torch 2.5.1+cu124`, CUDA. Three HTTP servers, each taking JSON and returning wav:

```
:8765  XTTS v2                 numpy 2.x      (kept for comparisons)
:8766  Chatterbox Multilingual  numpy < 2      (kept for comparisons)
:8767  F5-TTS_RUSSIAN v2       24 kHz, vocos   ← the working one
```

Three rather than one because numpy does not bend: Chatterbox needs the old one, XTTS the new one. A single venv cannot hold both.

Calibration and checks:

- `Misha24-10/F5-TTS_RUSSIAN`, checkpoint `F5TTS_v1_Base_v2` (1.35 GB), a 2,544-character vocabulary with Cyrillic, vocos vocoder at 24 kHz;
- references 24 kHz mono, 6–12 s each, with its own transcript in `refs_text.json`;
- take selection: three runs with different seeds and `cfg_strength` 2.0/2.6/3.2, the winner picked by transcript similarity (`difflib` over normalized words) and by f0 landing in the role's range;
- a timbre curve against the 1C reference is stored in [`eq_curve.json`](eq_curve.json) — fifteen points from 55 Hz to 12 kHz;
- every take is normalized with `loudnorm` to −20 LUFS, −2 dBTP.

Speed: a 30–40 character line synthesizes in 2–3 s on 8 GB of VRAM. A volume chapter (17–23 thousand characters) is 30–45 minutes with take selection.

### Measurements

Not "by ear", but in numbers. Readability is the similarity of a `whisper-base` transcript to the source text: 0.85 for "Mne v polikliniku k devyati", 1.00 for the bureaucrat's line, 0.79 for the long description, 0.82 for the two-word question.

Timbre is the median fundamental per line against the reference: 236 and 220 Hz for the old woman (reference 183), 149 and 137 Hz for the official (reference 161), 130 and 124 Hz for the narrator (reference 124). The voice is recognizable; no drops into the female register.

Known weak spots, visible in the numbers: very short lines (under 20 characters) sometimes drift upward in pitch — the question "Po kakomu faktu?" landed at 178 Hz against a 124 Hz reference. Take selection helps; merging short lines into neighbours helps more.

### Next

1. An emotion reference bank: calm, irritated, shout, whisper, irony — three per role. This is what F5 cannot do without a reference.
2. Stress marks: wire up `RUAccent` and feed text with `+`, otherwise "zámok" and "zamók" are a coin toss.
3. Move `render.py` from `edge-tts` to `:8767` and re-render the volume's 34 tracks.
4. Render a whole chapter rather than a scene: ten minutes reveal what ten seconds hide.

The owner's choice gets recorded here, in the settings table above, as soon as it exists.

---

`#tts #f5-tts #voice-cloning #audiobook #russian #local-ai #vocos`
