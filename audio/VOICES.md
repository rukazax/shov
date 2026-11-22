<p align="center"><img src="../assets/banner.svg" alt="Шов — серия на 30 томов" width="100%"></p>

<h1 align="center">Голоса «Шова»</h1>
<p align="center">Семнадцать персонажей, два тембра — и как из этого получился каст</p>

<p align="center">
  <b>RU</b> · <a href="#english">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/ролей-17-2f6fed?style=flat-square" alt="17 ролей">
  <img src="https://img.shields.io/badge/глав-34-8957e5?style=flat-square" alt="34 главы">
  <img src="https://img.shields.io/badge/громкость_−20_LUFS-3fb950?style=flat-square" alt="−20 LUFS">
  <img src="https://img.shields.io/badge/96_кбит%2Fс-8b949e?style=flat-square" alt="96 кбит/с">
</p>

**Разделы:** [Как слушать](#как-слушать) · [Что выбрано](#что-выбрано) · [Каст](#каст) · [Почему два голоса](#почему-два-голоса) · [Замеры](#замеры) · [Подводные камни](#подводные-камни) · [Как переозвучить](#как-переозвучить) · [English](#english)

---

## Как слушать

| Образец | Что внутри | Длина |
|---|---|---|
| [`tests/female-3.mp3`](tests/female-3.mp3) | рассказчик, затем три варианта женского голоса | 32 с |
| [`tests/female-A.mp3`](tests/female-A.mp3) | принятый вариант: рассказчик и четыре женские реплики | 27 с |

Оба файла — моно, 48 кГц, 128 кбит/с, приведены к −20 LUFS, чтобы сравнивать голоса, а не громкость.

Рядом лежат образцы отвергнутых движков — того же диалога первой главы: [`tests/xtts_cast_demo.mp3`](tests/xtts_cast_demo.mp3), [`tests/cb_cast_demo.mp3`](tests/cb_cast_demo.mp3), [`tests/f5_cast_demo.mp3`](tests/f5_cast_demo.mp3). Они нужны только для сравнения тембров и в каст не пошли.

## Что выбрано

Синтез речи `edge-tts`, два родных русских голоса: `ru-RU-DmitryNeural` для рассказа и мужских ролей, `ru-RU-SvetlanaNeural` для женских. Остальные голоса каталога говорят по-русски с акцентом — проверено на слух, в каст не пошли.

Женская база принята владельцем как **вариант А**: Svetlana, темп +3 %, тон +2 Гц. Остальные женские роли сдвинуты вокруг неё. Мужские остались как были: Dmitry, рассказчик −2 % / −2 Гц.

| Движок | Что показал | Вердикт |
|---|---|---|
| XTTS v2 | клонирует голос по десятисекундному эталону, но на русском слышен акцент; эталоны `male_petrov` и `male_poteryaev` к тому же зацикливают текст (0,20–0,48 с на знак против нормы 0,13) | отклонён |
| Chatterbox | то же, плюс рассинхрон с numpy | отклонён |
| F5-TTS_RUSSIAN | лучший клон, но требует 24-кГц эталонов на каждое настроение и внешней машины с видеопамятью | отложен |
| **`edge-tts`** | два родных голоса, ровный темп, быстрый синтез, кэш по блокам | **выбран** |

## Каст

Семнадцать ролей. Различие персонажей держится на темпе и тоне: 2 % и 4–5 Гц — тот шаг, на котором два голоса ещё слышны как разные люди и уже не звучат пародией.

| Роль | Кто это | Голос | Темп | Тон | Громкость |
|---|---|---|---|---|---|
| `hero` | Сеня, рассказчик от первого лица | Dmitry | +1 % | +2 Гц | +1 % |
| `narrator` | повествование от третьего лица | Dmitry | −2 % | −2 Гц | 0 |
| `bocman` | Боцман | Dmitry | −15 % | −16 Гц | +1 % |
| `mihalych` | Михалыч, начальник участка | Dmitry | −11 % | −11 Гц | 0 |
| `grisha` | Гриша, кладовщик | Dmitry | −8 % | −8 Гц | 0 |
| `muhin` | Мухин, Аркадий Львович | Dmitry | −5 % | −5 Гц | 0 |
| `leytenant` | лейтенант | Dmitry | +5 % | +4 Гц | +1 % |
| `tehnik` | техник и любой безымянный мужчина | Dmitry | +9 % | +9 Гц | −1 % |
| `vitya` | Витя | Dmitry | +14 % | +14 Гц | +1 % |
| `system` | системные строки Согласования | Dmitry | −25 % | −18 Гц | 0 |
| `agrafena` | Аграфена Тихоновна, старуха автолавки | Svetlana | −13 % | −13 Гц | 0 |
| `babka` | бабка, Нина Петровна | Svetlana | −8 % | −9 Гц | +1 % |
| `ganna` | Ганна Фёдоровна | Svetlana | −4 % | −5 Гц | 0 |
| `pozharskaya` | Пожарская, Ольга Тимуровна | Svetlana | 0 | −1 Гц | 0 |
| `female` | безымянная женщина, Юля | Svetlana | +3 % | +2 Гц | 0 |
| `lida` | Лида | Svetlana | +8 % | +7 Гц | 0 |
| `dasha` | Даша, дочь | Svetlana | +12 % | +11 Гц | +1 % |

Кто есть кто и кто что говорит — в `cast/chNN.cast.txt`, по файлу на главу. Правится только колонка роли; текст, тип и номер блока — для контекста.

Поверх тембра работает просодия от знака и ремарки:

- вопрос — выше на 6 Гц и быстрее на 3 %;
- `!` — громче на 6 %, выше на 5 Гц;
- `…` дважды — медленнее на 8 %, ниже на 3 Гц;
- короткая рубленая реплика — суше и ниже;
- длинный абзац описания — ровнее и медленнее;
- «заорал», «крикнул», капс — крик, «прошептал», «вполголоса» — шёпот.

Плюс микроразброс ±2 % и ±2 Гц, посчитанный от текста блока: без него каждая реплика одного персонажа звучит одним и тем же пресетом, и это слышится как механика.

## Почему два голоса

Родных русских голосов в каталоге ровно два. Взять «ещё голос» можно только из мультиязычных — и они читают по-русски с акцентом; на первом же прослушивании это слышно и убивает всю работу. Поэтому персонажей различает не тембр движка, а согласованный сдвиг по темпу и тону.

Что это даёт на практике: в сцене, где разговаривают бабка, Ганна и Даша, разница 9 Гц и 16 % темпа слышна уверенно. В сцене, где двое мужчин с разницей 4 Гц и 3 %, — уже нет; такие пары я развожу по тону сильнее. Список выше собран именно так, чтобы соседи по сценам не сходились.

Безымянные прохожие, вахтёрши и дежурные делят `tehnik` и `female`. Это приём, а не недосмотр, — но при разметке надо смотреть, чтобы два таких человека не оказались в одной сцене.

## Замеры

Тембр проверяется не на слух, а медианой основного тона по блоку. Замер снимается скриптом `voice_probe.py`: он берёт по одной реплике на роль, синтезирует её и считает медиану основного тона по автокорреляции.

| Группа | Что проверено | Итог |
|---|---|---|
| Мужские роли | основной тон по ролям | от 106 до 138 Гц, шаг 3–5 Гц |
| Женские роли | основной тон по ролям | от 157 до 181 Гц, шаг 4–5 Гц |
| Образец каста | громкость, тишина по краям | −20,3 LUFS, пауз длиннее секунды внутри реплик нет |
| Глава | громкость, пик | −20,5 LUFS, пик −3,4 dBTP |

Слабые места, которые видно в цифрах и слышно на длинных абзацах: короткие реплики (меньше 20 знаков) иногда съезжают по тону на 5–8 Гц вверх — вопрос «По какому факту?» у героя звучит выше обычного. Лечится тем, что короткие реплики лучше склеивать с соседними, а не читать отдельным блоком.

## Подводные камни

Синтез речи — внешний сервис, и он ведёт себя неровно. Всё, что ниже, стоит денег времени, если не знать заранее.

| Симптом | Что на самом деле | Что делать |
|---|---|---|
| `NoAudioReceived: No audio was received` | сервис отбивает запрос; текст, темп и тон ни при чём | повторять: отказ приходит за 2–4 с, успех — за 1–2 с |
| один и тот же текст проходит 6/6, а десять новых — 2/10 | у сервиса кэш своих синтезов, «новое» упирается в деградацию | повторять, пока не попадёт в окно; не верить единичному замеру |
| процесс жив, CPU 0 %, кэш не растёт | запрос повис без ответа | таймаут 25 с на запрос (`render.py`) |
| глава не собралась после всех повторов | волна отказов длиннее пяти минут | `render_book.sh` делает до шести заходов на главу с паузой 2 минуты |
| рендер идёт 4 блока в минуту | один поток против волн отказов | восемь параллельных потоков дают 36 блоков в минуту |
| мужские реплики отбиваются, женские проходят | голоса деградируют **по отдельности**: в один замер Dmitry дал 1/6, Svetlana 5/6 | ждать своё окно по каждому голосу; замерять их раздельно, а не «синтез вообще» |

Ещё два правила, добытых опытом:

- паузы между повторами — 0,15–0,5 с, а не 8 с: долгие паузы съедают время, отказ всё равно приходит быстро;
- блок, который «не синтезируется», почти всегда синтезируется с четвёртой попытки: это не битый текст, а потерянный запрос.

## Как переозвучить

```bash
cd audio

python3 gen_beds.py                    # подложки и эффекты, один раз
python3 cast_audit.py                  # что в разметке ролей вызывает вопросы
python3 voice_probe.py                 # таблица ролей с замером основного тона

# одна глава
python3 render.py ../BOOK01/ch01.md

# вся книга: четыре потока по диапазонам глав
FORCE=1 JOBS=2 ./render_book.sh 0 8    &
FORCE=1 JOBS=2 ./render_book.sh 9 16   &
FORCE=1 JOBS=2 ./render_book.sh 17 24  &
FORCE=1 JOBS=2 ./render_book.sh 25 33  &

python3 check_out.py                   # длительность, громкость, пик, битрейт
```

Что важно знать перед запуском:

- `cache/` хранит блоки по ключу «голос, темп, тон, громкость, текст». Любая правка этих полей убивает кэш — синтез пойдёт заново на весь том, это ожидаемо и закладывается временем.
- `FORCE=1` нужен, если файлы в `out/` новее текста глав, а переозвучить всё равно надо.
- `JOBS` — число одновременных запросов внутри главы. Выше трёх бесполезно, а на волнах отказов даже вредно: узкое место не в нас.
- Каждая глава пишется под `flock`, поэтому несколько `render_book.sh` можно гонять параллельно по непересекающимся диапазонам.
- Рендер всей книги — это часы, а не минуты. Кэш делает повторный запуск почти бесплатным: синтезируется только недостающее.

Выход: `out/chNN.mp3`, моно, 44,1 кГц, 96 кбит/с, −20 LUFS, каждый файл проверяется `check_out.py` по длительности, громкости и битрейту.

---

`#tts #audiobook #russian #voice-casting #edge-tts`

---

## English

<p align="center">
  <a href="#голоса-шова">Русский</a> · <b>English</b>
</p>

### How to listen

| Sample | What is inside | Length |
|---|---|---|
| [`tests/female-3.mp3`](tests/female-3.mp3) | the narrator, then three female voice options | 32 s |
| [`tests/female-A.mp3`](tests/female-A.mp3) | the accepted option: narrator and four female lines | 27 s |

Both are mono, 48 kHz, 128 kbps, normalized to −20 LUFS, so you compare voices rather than loudness.

Next to them sit samples of the rejected engines on the same first-chapter dialogue: [`tests/xtts_cast_demo.mp3`](tests/xtts_cast_demo.mp3), [`tests/cb_cast_demo.mp3`](tests/cb_cast_demo.mp3), [`tests/f5_cast_demo.mp3`](tests/f5_cast_demo.mp3). They exist for timbre comparison only and never entered the cast.

### What was chosen

`edge-tts` with the two native Russian voices: `ru-RU-DmitryNeural` for narration and male roles, `ru-RU-SvetlanaNeural` for female ones. Every other voice in the catalogue speaks Russian with an accent — checked by ear, none made the cast.

The female base is what the owner accepted as **option A**: Svetlana at +3 % rate, +2 Hz pitch. The other female roles sit around it. Male roles stayed as they were: Dmitry, narrator at −2 % / −2 Hz.

| Engine | What it showed | Verdict |
|---|---|---|
| XTTS v2 | clones a voice from a ten-second reference, but the Russian carries an accent; the `male_petrov` and `male_poteryaev` references also loop the text (0.20–0.48 s per character against a 0.13 norm) | rejected |
| Chatterbox | the same accent, plus a numpy conflict | rejected |
| F5-TTS_RUSSIAN | the best clone, but it needs 24 kHz references per mood and a separate machine with video memory | deferred |
| **`edge-tts`** | two native voices, even pace, fast synthesis, per-block cache | **chosen** |

### The cast

Seventeen roles. Character separation rests on pace and pitch: 2 % and 4–5 Hz is the step where two voices still read as different people and do not yet sound like a parody.

| Role | Who this is | Voice | Rate | Pitch | Volume |
|---|---|---|---|---|---|
| `hero` | Senya, first-person narrator | Dmitry | +1 % | +2 Hz | +1 % |
| `narrator` | third-person narration | Dmitry | −2 % | −2 Hz | 0 |
| `bocman` | the boatswain | Dmitry | −15 % | −16 Hz | +1 % |
| `mihalych` | Mikhaylych, the site foreman | Dmitry | −11 % | −11 Hz | 0 |
| `grisha` | Grisha, the storekeeper | Dmitry | −8 % | −8 Hz | 0 |
| `muhin` | Mukhin, Arkady Lvovich | Dmitry | −5 % | −5 Hz | 0 |
| `leytenant` | the lieutenant | Dmitry | +5 % | +4 Hz | +1 % |
| `tehnik` | the technician and any unnamed man | Dmitry | +9 % | +9 Hz | −1 % |
| `vitya` | Vitya | Dmitry | +14 % | +14 Hz | +1 % |
| `system` | the Concordance system lines | Dmitry | −25 % | −18 Hz | 0 |
| `agrafena` | Agrafena Tikhonovna, the old woman of the shop truck | Svetlana | −13 % | −13 Hz | 0 |
| `babka` | the old woman, Nina Petrovna | Svetlana | −8 % | −9 Hz | +1 % |
| `ganna` | Ganna Fyodorovna | Svetlana | −4 % | −5 Hz | 0 |
| `pozharskaya` | Pozharskaya, Olga Timurovna | Svetlana | 0 | −1 Hz | 0 |
| `female` | any unnamed woman, Yulya | Svetlana | +3 % | +2 Hz | 0 |
| `lida` | Lida | Svetlana | +8 % | +7 Hz | 0 |
| `dasha` | Dasha, the daughter | Svetlana | +12 % | +11 Hz | +1 % |

Who is who and who says what lives in `cast/chNN.cast.txt`, one file per chapter. Only the role column is edited; block number, type and text are there for context.

Prosody rides on top of the timbre:

- a question — 6 Hz higher, 3 % faster;
- `!` — 6 % louder, 5 Hz higher;
- two `…` — 8 % slower, 3 Hz lower;
- a short clipped line — drier and lower;
- a long description paragraph — more even and slower;
- "shouted", "yelled", all caps — a shout; "whispered", "under his breath" — a whisper.

Plus a micro-jitter of ±2 % and ±2 Hz derived from the block text: without it every line of one character reads with the same preset, and that is heard as machinery.

### Why two voices

The catalogue has exactly two native Russian voices. Any "extra voice" can only come from the multilingual set, and those read Russian with an accent — audible on the first listen, and it ruins the work. So characters are separated by a deliberate shift in pace and pitch, not by the engine's timbre.

In practice: in a scene with the old woman, Ganna and Dasha, 9 Hz and 16 % of pace are unmistakable. In a scene with two men 4 Hz and 3 % apart, they are not — such pairs get a wider pitch gap. The table above is built so that scene neighbours never collapse into each other.

Unnamed passers-by, caretakers and couriers share `tehnik` and `female`. That is a device, not an oversight — but when marking up a chapter, check that two such people never land in one scene.

### Measurements

Timbre is checked by the median fundamental per block, not by ear. `voice_probe.py` takes one line per role, synthesizes it and measures the median fundamental by autocorrelation.

| Group | What was checked | Result |
|---|---|---|
| Male roles | fundamental per role | 106 to 138 Hz, 3–5 Hz steps |
| Female roles | fundamental per role | 157 to 181 Hz, 4–5 Hz steps |
| Cast sample | loudness, edge silence | −20.3 LUFS, no gap over a second inside a line |
| A chapter | loudness, peak | −20.5 LUFS, peak −3.4 dBTP |

Known weak spots, visible in the numbers and audible on long paragraphs: short lines (under 20 characters) sometimes drift 5–8 Hz upward — the hero's "Po kakomu faktu?" reads higher than usual. The fix is to merge short lines into their neighbours instead of reading them as separate blocks.

### Pitfalls

Speech synthesis is an external service and it behaves unevenly. Everything below costs hours if unknown.

| Symptom | What is really happening | What to do |
|---|---|---|
| `NoAudioReceived: No audio was received` | the service drops the request; text, rate and pitch are not to blame | retry: a failure comes back in 2–4 s, a success in 1–2 s |
| the same text passes 6/6 while ten new ones pass 2/10 | the service caches its own synthesis; "new" hits degradation | retry until it lands in a good window; never trust a single measurement |
| the process is alive, CPU 0 %, the cache stops growing | a request hung with no answer | a 25 s timeout per request (`render.py`) |
| a chapter will not assemble after all retries | the failure wave outlasts five minutes | `render_book.sh` makes up to six passes per chapter with a 2-minute pause |
| the render runs at 4 blocks a minute | one stream against failure waves | eight parallel streams give 36 blocks a minute |
| male lines are dropped while female ones pass | voices degrade **individually**: in one measurement Dmitry gave 1/6, Svetlana 5/6 | wait for each voice's own window; measure them separately, not "synthesis in general" |

Two more rules learned the hard way:

- the pause between retries is 0.15–0.5 s, not 8 s: long pauses only burn time, a failure returns fast anyway;
- a block that "will not synthesize" almost always synthesizes on the fourth attempt: it is a lost request, not broken text.

### How to re-render

```bash
cd audio

python3 gen_beds.py                    # beds and effects, once
python3 cast_audit.py                  # what looks wrong in the role markup
python3 voice_probe.py                 # the role table with measured fundamentals

# one chapter
python3 render.py ../BOOK01/ch01.md

# the whole book: four streams over chapter ranges
FORCE=1 JOBS=2 ./render_book.sh 0 8    &
FORCE=1 JOBS=2 ./render_book.sh 9 16   &
FORCE=1 JOBS=2 ./render_book.sh 17 24  &
FORCE=1 JOBS=2 ./render_book.sh 25 33  &

python3 check_out.py                   # duration, loudness, peak, bitrate
```

Worth knowing before launching:

- `cache/` keys blocks by "voice, rate, pitch, volume, text". Any edit to those fields wipes the cache — synthesis restarts for the whole volume, expected and budgeted in time.
- `FORCE=1` is needed when `out/` is newer than the chapter text and you still want to re-voice.
- `JOBS` is the number of concurrent requests inside a chapter. Above three it is useless, and during failure waves it is actively counter-productive: the bottleneck is not on our side.
- Every chapter is written under `flock`, so several `render_book.sh` runs can work disjoint ranges in parallel.
- A full-book render is hours, not minutes. The cache makes a re-run nearly free: only what is missing gets synthesized.

Output: `out/chNN.mp3`, mono, 44.1 kHz, 96 kbps, −20 LUFS, each file verified by `check_out.py` for duration, loudness and bitrate.

---

`#tts #audiobook #russian #voice-casting #edge-tts`
