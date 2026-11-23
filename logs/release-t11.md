## Том 11 «Долг» — издание текста

Одиннадцатая книга серии «Шов»: полный текст, EPUB и обложка. Аудио живёт отдельным релизом.

> 🎧 **Аудиоверсия тома 11** — отдельный релиз, когда соберутся все дорожки: 34 дорожки, многоголосый каст, −20 LUFS. Здесь аудиофайлов нет — только книга.

### Что внутри

| | |
|---|---|
| Текст | 608 306 знаков, 102 328 слов, 15,2 а.л. |
| Главы | 34: Введение + 33 главы |
| Сцены | 146 |
| Системные строки | 155 (одна на ~3,9 тыс. знаков) |
| Диалог | 50 % строк |
| Средняя фраза | 8,6 слова |

### О чём том

Он выходит из узла и узнаёт, что вышел не на ту сторону, с которой уходил: у двери стоит девочка, которая узнавала его по голосу, и спрашивает у матери «а кто это?». Дальше начинается не возвращение, а пересчёт.

В паспортном столе ему ставят метку «У-3» — за то, что у него есть вклад времени. Метка даёт три ограничения: работу по допуску, выезд не дольше тридцати суток и графу «основание», в которую нельзя вписать себя. Он человек с вкладом времени, и с него положен пересчёт.

Пересчёт приходит бумагой: вклад девяносто три суток по табелю узла, переходов три, в остатке семьдесят два часа, на явку тридцать суток, внизу приписка «неявка — изъятие вклада». Наружных четырёх месяцев в извещении нет, и это не ошибка: снаружи прошло четыре месяца, а узловая книга считает по табелю, потому что внутри время идёт медленнее. Девяносто три минус девяносто — трое суток, семьдесят два часа. Ровно столько, сколько нельзя ни отработать переходом, ни выкупить.

Он меняет время на время: час смены у стыка стоит суток снаружи, переход гасит месяц вклада. Три перехода он растягивает на полгода, и всё это время живёт по чужой бумаге: в комнате у Свода, ночными сменами без ведомости, субботами по допуску, возражением к чужой опеке, которое принимают к рассмотрению — и это первый раз, когда он что-то смог.

Чем кончается: метку снимают, вклад закрывают штампом ниже метки, и остаток семьдесят два часа остаются в закрытой книге — «списанное можно вернуть, закрытое нельзя». А в книге Свода появляется второй «Лоскутов С. А.» с другим годом рождения, и его просят подойти для сверки личности. Дома, оставшись с ним на минуту, девочка говорит: «Ты не папа. Папа был раньше».

### Чем том отличается от предыдущих

- **Не узел, а бумага.** Десятый том считал часы, одиннадцатый — часы чужие. Сюжет держится не на полотне, а на бланке: талон, карточка, извещение, опись, приписка внизу. Ни одна бумага в томе не злая, и каждая неотменяема.
- **Антагонист — не человек и не регламент, а долг.** У долга нет управляющего: Буш считает, Штиль вручает сведение, Королёва ведёт дело, Гесс даёт переход не по доброте, а потому что у Свода в списке один, кто знает кромку. Спросить не с кого, и это самое тяжёлое.
- **Цена платится не весом и не годами, а правом.** Он не теряет килограммы и не пропускает месяцы: он теряет графу. За трое суток остатка человек становится основанием, а основанием его делает опека — то есть другая бумага.
- **Главный счёт — арифметика, в которой сходится к худшему.** Он считает месяц за тридцать суток, переход кратен месяцу, столбик даёт месяц остатка; ему говорят «считайте по часам»; табель даёт девяносто три суток; двадцать две тысячи триста тридцать два минус две тысячи сто шестьдесят — семьдесят два часа. Сошлось, только не в его пользу: «меня обокрало время, и вора нет».

### Сборка и проверки

- Машинный гейт тома: `BOOK11/gate.sh` — полнота (34 файла), объём главы 16–23 тыс., доля диалога, типографика (только короткое тире, «ёлочки», `…`), атрибуция реплик по именам. Итог: `ГЕЙТЫ: PASS`, безличных ремарок 0, дублей абзацев 0.
- Сборка: `BOOK11/build_book.py` (словарь системных строк расширен под этот том: метка, вклад, переход, извещение, сверка, опека, основание); `BOOK11/build_epub.sh` — EPUB с обложкой `assets/cover-tom11.png`.
- Сведён канон чисел: вклад 93 суток по табелю, переход 720 часов, три перехода 2160, всего 2232, остаток 72 часа; снаружи четыре месяца минус вклад в узловых сутках = 27 суток, «вора нет»; явка 30 суток с вручения; у стыка 1 час смены = 1 сутки снаружи; переход гасит ровно месяц вклада.
- Сведены имена: Лоскутова Ю. П. — и в десятом томе, и в этом (одна фамилия, одна дата рождения, номера 408 и 419 — две ветки, которые Свод различает только по номеру). Инспектор в четырнадцатой главе остаётся безымянным: это не Штиль, Штиль приходит один раз, в двадцать восьмой, со сведением.
- Обложка: бирка с меткой «У-3» на фоне счётной книги, три зачёркнутых месяца и остаток, который не гасится.

### English

## Volume 11 «Debt» — text edition

The eleventh book of the «Seam» series: full text, EPUB and cover. Audio ships as a separate release.

> 🎧 **Audiobook of volume 11** — a separate release once all tracks are ready: 34 tracks, multi-voice cast, −20 LUFS. No audio files here, only the book.

### What is inside

| | |
|---|---|
| Text | 608,306 characters, 102,328 words, 15.2 author sheets |
| Chapters | 34: Introduction + 33 chapters |
| Scenes | 146 |
| System lines | 155 (one per ~3,900 characters) |
| Dialogue | 50 % of lines |
| Average sentence | 8.6 words |

### What the volume is about

He comes out of the knot and learns he did not come out on the side he left: a girl stands at the door, the girl who used to know him by his voice, and asks her mother "who is that?". What begins next is not a return but a recount.

At the passport office he is given the tag «U-3» — because he owns a deposit of time. The tag carries three limits: work by permit, travel no longer than thirty days, and the column "grounds", into which he cannot write himself. He is a man with a deposit of time, and a recount is due from him.

The recount arrives as paper: the deposit is ninety-three days by the knot's ledger, three transitions, seventy-two hours left, thirty days to appear, and at the bottom the note "failure to appear — forfeiture of the deposit". The four outside months are not in the notice, and that is no mistake: four months passed outside, while the knot's book counts by the ledger, because inside time runs slower. Ninety-three minus ninety is three days, seventy-two hours. Exactly as much as can be neither worked off by a transition nor bought out.

He trades time for time: an hour of shift at the joint costs a day outside, a transition cancels a month of deposit. He stretches three transitions over half a year, and all that time he lives on someone else's paper: in a room by the Junction, night shifts without a payroll sheet, Saturdays by permit, an objection to another's guardianship that is accepted for consideration — and that is the first time he has managed anything.

How it ends: the tag is removed, the deposit is closed with a stamp below the tag, and the remaining seventy-two hours stay in the closed book — "what is written off can be returned; what is closed cannot". And in the Junction's book a second «Loskutov S. A.» appears, with a different year of birth, and he is asked to come in for an identity check. At home, left with him for a minute, the girl says: "You're not papa. Papa was before."

### How it differs

- **Not a knot but paper.** The tenth volume counted hours, the eleventh counts other people's hours. The plot rests not on cloth but on a form: a ticket, a card, a notice, an inventory, a note at the bottom. Not one paper in the volume is malicious, and every one of them is irrevocable.
- **The antagonist is neither a person nor a regulation but a debt.** The debt has no manager: Bush counts, Shtil serves the notice, Korolyova keeps the file, Gess grants a transition not out of kindness but because the Junction's list has one man who knows the edge. There is no one to blame, and that is the hardest part.
- **The price is paid neither in weight nor in years but in right.** He loses no kilograms and misses no months: he loses a column. For three remaining days a man becomes grounds, and guardianship is what makes him grounds — that is, another paper.
- **The main account is arithmetic that converges on the worst outcome.** He counts a month as thirty days, a transition as a multiple of a month, and his column gives a month left; he is told "count in hours"; the ledger gives ninety-three days; twenty-two thousand three hundred and thirty-two minus two thousand one hundred and sixty is seventy-two hours. It adds up, only not in his favour: "time robbed me, and there is no thief".

### Build and checks

- Volume machine gate: `BOOK11/gate.sh` — completeness (34 files), per-chapter length 16–23 thousand characters, dialogue share, typography (short dash only, «ёлочки» quotes, `…`), speaker attribution by name. Result: `ГЕЙТЫ: PASS`, zero impersonal attributions, zero duplicated paragraphs.
- Build: `BOOK11/build_book.py` (the system-line vocabulary extended for this volume: tag, deposit, transition, notice, audit, guardianship, grounds); `BOOK11/build_epub.sh` — EPUB with `assets/cover-tom11.png`.
- Numbers reconciled: deposit 93 days by the ledger, a transition 720 hours, three transitions 2160, total 2232, remainder 72 hours; four outside months minus the deposit in knot days = 27 days, "no thief"; thirty days to appear from delivery; at the joint one shift hour = one day outside; a transition cancels exactly one month of deposit.
- Names reconciled: Loskutova Yu. P. in the tenth volume and in this one (one surname, one date of birth, numbers 408 and 419 — two branches the Junction tells apart only by number). The inspector in chapter fourteen stays unnamed: that is not Shtil, Shtil comes once, in chapter twenty-eight, with a notice.
- Cover: a tag with «U-3» over an account book, three crossed-out months and a remainder that cannot be cancelled.
