# Agent Template Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a workspace start from a pre-written, genre-specific
translation-instruction template instead of writing `agent.md` from
scratch every time, without giving up the ability to customize it per
workspace afterward.

**Architecture:** A checked-in `agents/<lang>/<genre>.md` library (14
files: 7 genres × 2 languages), a small `server/agent_templates.py`
module to list and resolve them safely, a new backend endpoint, and one
new optional field on the existing `LoadAgentFile` node — `"workspace"`
(the default, today's exact behavior) or `"<lang>/<genre>"` (a shared
template). `SaveAgentFile` is untouched.

**Tech Stack:** Plain `pathlib`/`re` (no new dependency); vanilla JS for
the picker modal, matching every other frontend module in `web/js/`.

**Spec:** `docs/superpowers/specs/2026-09-10-agent-template-library-design.md`

## Global Constraints

- This plan is independent of the other two sub-projects from the same
  brainstorm (Path Picker; Glossary & Chapter Consistency) — it touches
  only `LoadAgentFile`, never `SaveAgentFile`, and shares no file with
  either of the other two plans' code changes. It does not assume either
  of those plans has already been executed — its own frontend task
  defines its own, self-contained CSS classes rather than reusing
  anything from the Path Picker plan, since that plan may not have run
  yet.
- `LoadAgentFile.execute`'s `template` parameter defaults to `"workspace"`
  at the Python level (not just in `INPUT_TYPES`'s declared default) —
  the existing tests call `node.execute(workspace_name="novel-a")` with
  no `template` argument at all and must keep passing unchanged.
- Template ids are validated against the same allowlist-regex approach
  `server/workspace.py`'s `_NAME_PATTERN` already establishes for
  workspace names — reject anything outside `[a-z0-9_-]+` per path
  segment, so a crafted `template` value can never escape `AGENTS_ROOT`.
- The 14 template files are real, complete, genre-specific content,
  checked into git as ordinary developer-authored files (not user data,
  not workspace-scoped).

---

### Task 1: The 14 agent template files

**Files:**
- Create: `agents/vn/tien-hiep.md`
- Create: `agents/vn/ngon-tinh.md`
- Create: `agents/vn/kiem-hiep.md`
- Create: `agents/vn/hoc-duong.md`
- Create: `agents/vn/hai-huoc.md`
- Create: `agents/vn/fantasy.md`
- Create: `agents/vn/general.md`
- Create: `agents/en/tien-hiep.md`
- Create: `agents/en/ngon-tinh.md`
- Create: `agents/en/kiem-hiep.md`
- Create: `agents/en/hoc-duong.md`
- Create: `agents/en/hai-huoc.md`
- Create: `agents/en/fantasy.md`
- Create: `agents/en/general.md`

**Interfaces:**
- Produces: the on-disk content Task 3's `resolve_template_path` and
  Task 4's `LoadAgentFile` read verbatim. No code interface — this task
  is pure content authoring.

Every file uses the same four sections, in this order: **Văn phong**,
**Xưng hô**, **Thuật ngữ đặc trưng**, **Lưu ý khác** (per the spec's
"Nội dung 14 template" section). Each file states its own target
language explicitly in its opening line — this is the one place target
language is recorded anywhere in this feature (see spec's Mục tiêu §5).

- [ ] **Step 1: `agents/vn/tien-hiep.md`**

This is the spec's own worked example, reproduced verbatim:

```markdown
# Hướng dẫn dịch — Tiên hiệp / Huyền huyễn / Dị giới

Dịch sang tiếng Việt. Thể loại tiên hiệp/huyền huyễn/dị giới (tu tiên,
pháp thuật, dị thế giới) — giữ đúng các quy ước sau.

## Văn phong

- Giọng văn trang trọng, cổ trang vừa phải — không dùng từ lóng/teencode,
  không hiện đại hóa lời thoại.
- Câu văn có thể dài, nhiều tính từ miêu tả cảnh vật/tu vi — không cắt
  ngắn thô bạo, giữ nhịp điệu và không khí của nguyên tác.
- Thuật ngữ tu luyện dịch nhất quán xuyên suốt — nếu workspace có
  glossary.json, luôn ưu tiên thuật ngữ đã có trong đó.

## Xưng hô

- Sư đồ (thầy trò): đệ tử xưng "đệ tử"/"con", gọi thầy là
  "sư phụ"/"sư tôn"; không dùng "thầy/em" trung tính.
- Đồng môn: xưng hô theo thứ bậc nhập môn — "sư huynh/sư tỷ/sư đệ/sư
  muội", không dùng "anh/chị/em" hiện đại.
- Trưởng bối/vãn bối không cùng môn phái: "tiền bối"/"vãn bối", tránh
  "ông/bà/cháu".
- Kẻ thù/địch nhân: xưng hô lạnh lùng, cộc lốc — "ngươi/ta", không dùng
  "bạn/tôi".

## Thuật ngữ đặc trưng

- Giữ nguyên hệ thống cảnh giới tu luyện của tác phẩm (ví dụ: Luyện Khí,
  Trúc Cơ, Kim Đan, Nguyên Anh, Hóa Thần...) — không tự ý đổi tên hay
  dịch nghĩa đen sang tiếng Anh/tiếng khác.
- Tên công pháp, pháp bảo, linh thú: giữ Hán Việt nếu bản gốc dùng Hán
  tự, trừ khi cái tên mang ý nghĩa quan trọng với cốt truyện và cần dịch
  nghĩa để người đọc hiểu được dụng ý.
- Đơn vị đo tu vi/thời gian tu luyện (năm, kiếp, tuổi thọ...) giữ nguyên
  logic của nguyên tác, không quy đổi sang đơn vị hiện đại.

## Lưu ý khác

- Không thêm chú thích/giải thích ngoài lề kiểu "(ND: ...)" trong bản
  dịch — nếu cần giải thích, đó là việc của agent.md/glossary, không
  phải của bản dịch.
- Giữ nguyên các thán từ, khẩu quyết, tên chiêu thức khi nhân vật hô lớn
  lúc thi triển — dịch sát nghĩa nhưng không thoát ý làm mất khí thế.
```

- [ ] **Step 2: `agents/en/tien-hiep.md`**

```markdown
# Translation Guide — Xianxia / Cultivation / Alt-World

Translate into English. Genre: xianxia/cultivation/isekai-adjacent
fantasy (cultivation systems, immortal arts, alternate worlds) — follow
these conventions.

## Style

- Register is elevated but readable — avoid modern slang or internet
  speak in narration or dialogue; the prose can be somewhat formal
  without becoming stiff or archaic ("thee/thou" is wrong for this genre).
- Sentences may run long with heavy scene/cultivation-state description —
  do not chop them into short, choppy fragments; preserve the original's
  pacing and atmosphere.
- Use terminology consistently across the whole work — if the workspace
  has a glossary.json, always defer to what's already established there
  over inventing a new rendering.

## Forms of address

- Master–disciple: a disciple refers to themselves as "this disciple" or
  by name, and addresses their teacher as "Master" or "Master So-and-so" —
  not a neutral "teacher".
- Fellow disciples: address by cultivation-entry rank — "Senior
  Brother/Sister", "Junior Brother/Sister" — not generic "brother/sister"
  or first names alone unless the original explicitly uses a given name.
- Seniors/juniors outside one's own sect: "Senior" / "Junior" (as a form
  of address, capitalized), avoid "sir/miss".
- Enemies: cold, curt address — "you" is fine, but avoid warmth-implying
  contractions or friendliness markers a hostile exchange wouldn't have.

## Genre-specific terminology

- Keep the work's own cultivation-realm system intact (e.g. Qi
  Condensation, Foundation Establishment, Core Formation, Nascent Soul,
  Deity Transformation) — do not invent a different English convention
  than what the work itself implies, and do not collapse distinct realms
  into one.
- Technique/treasure/spirit-beast names: prefer keeping the original's
  proper-noun flavor (transliterated or a direct English rendering used
  consistently) over ad hoc re-translation each time it appears — pick
  one rendering per name and keep it, unless the name's meaning is
  plot-relevant and needs to read as meaningful in English.
- Cultivation-time units (years of seclusion, lifespan figures) follow
  the source's own internal logic — do not convert to a real-world
  calendar sense that doesn't match the work's scale.

## Other notes

- No inline translator notes/parentheticals in the translated text itself.
- Keep shouted technique names/incantations largely intact when a
  character calls them out — translate for meaning, but don't flatten
  them into a bland description that loses the dramatic weight.
```

- [ ] **Step 3: `agents/vn/ngon-tinh.md`**

```markdown
# Hướng dẫn dịch — Ngôn tình / Đô thị

Dịch sang tiếng Việt. Thể loại ngôn tình/đô thị hiện đại (tình cảm, đời
sống thành thị, công sở) — giữ đúng các quy ước sau.

## Văn phong

- Giọng văn tự nhiên, gần với lời ăn tiếng nói đời thường — tránh câu cú
  quá trang trọng/cổ trang; đối thoại nên đọc như người thật đang nói
  chuyện.
- Cảm xúc nội tâm nhân vật (đặc biệt các đoạn miêu tả tâm lý) cần dịch
  mượt, giữ được sắc thái tinh tế thay vì dịch thô cứng từng câu.
- Có thể dùng câu ngắn, câu cảm thán để giữ nhịp điệu tình cảm — không
  cần giữ cấu trúc câu dài như văn phong tiên hiệp.

## Xưng hô

- Cặp đôi/người yêu: "anh/em" là mặc định cho quan hệ nam nữ lãng mạn;
  chuyển đổi linh hoạt theo diễn biến quan hệ (từ trang trọng "anh/tôi"
  sang thân mật "anh/em" khi tình cảm phát triển).
- Gia đình: giữ đúng thứ bậc thân tộc Việt hóa tự nhiên — "ba/mẹ",
  "anh/chị/em", "cô/chú/dì/cậu" — không giữ nguyên cách gọi kiểu Trung
  văn (không dùng "phụ thân/mẫu thân" trừ khi có chủ đích hài/giễu).
- Công sở: "sếp", "anh/chị" theo cấp bậc, tên riêng khi thân thiết — quan
  hệ đồng nghiệp nên tự nhiên như văn phòng Việt Nam hiện đại.
- Biệt danh/tên gọi âu yếm: dịch thoát ý sang cách gọi âu yếm tự nhiên
  trong tiếng Việt thay vì dịch sát nghĩa đen (ví dụ tên gọi kiểu "tiểu
  X" nên chuyển thành biệt danh tự nhiên, không giữ "tiểu" nếu nghe gượng).

## Thuật ngữ đặc trưng

- Chức danh công sở, tên công ty/nhãn hàng: dịch hoặc giữ nguyên tùy ngữ
  cảnh, miễn nhất quán xuyên suốt.
- Địa danh/tên đường đô thị: có thể giữ nguyên tên gốc hoặc Việt hóa nhẹ,
  không cần Hán Việt hóa như thể loại cổ trang.

## Lưu ý khác

- Tránh dịch quá sát nghĩa đen các thành ngữ/tục ngữ tình cảm — ưu tiên
  tìm cách diễn đạt tương đương tự nhiên trong tiếng Việt.
- Giữ độ "ngọt"/lãng mạn của nguyên tác — không làm lời thoại tình cảm
  trở nên khô khan, máy móc.
```

- [ ] **Step 4: `agents/en/ngon-tinh.md`**

```markdown
# Translation Guide — Romance / Contemporary Urban

Translate into English. Genre: contemporary romance/urban fiction
(relationships, city life, office settings) — follow these conventions.

## Style

- Natural, conversational register — avoid stiff or archaic phrasing;
  dialogue should read like real people talking, not a formal document.
- Interior emotional narration should read smoothly and idiomatically —
  prioritize how the feeling lands in English over a literal clause-by-
  clause rendering.
- Short sentences and exclamations are fine and often better here than
  in more formal genres — don't pad them out to sound more "literary".

## Forms of address

- Convert kinship- or title-based address terms into what English
  readers actually expect: a couple calls each other by name or a pet
  name, not a literal rendering of an honorific system that doesn't
  exist in English. Do not carry over source-language address particles
  as English nouns.
- Family: use natural English kinship terms (Mom/Dad, older
  brother/sister as a name or "my brother", not a literal title used as
  a form of direct address the way some source languages do).
- Workplace: "boss", first names among peers, title + last name for more
  formal relationships — mirror how an English-language office actually
  talks, not the source hierarchy's literal address terms.
- Pet names/endearments: localize to a natural English endearment
  ("babe", "sweetheart", a nickname) rather than transliterating or
  literally translating a source-language diminutive that would sound
  odd in English.

## Genre-specific terminology

- Job titles, company/brand names: translate or keep as appropriate to
  context, but stay consistent for the same entity throughout.
- Place names/streets: either keep the original name or a natural
  English rendering — no special formal-register terminology system is
  needed here (contrast with a period/fantasy setting).

## Other notes

- Avoid literal translation of romantic idioms/proverbs — find the
  natural English equivalent feeling instead.
- Preserve the warmth/sweetness of the original — don't let romantic
  dialogue read as flat or mechanical.
```

- [ ] **Step 5: `agents/vn/kiem-hiep.md`**

```markdown
# Hướng dẫn dịch — Kiếm hiệp / Võ hiệp

Dịch sang tiếng Việt. Thể loại kiếm hiệp/võ hiệp (giang hồ, võ công, môn
phái, ân oán) — không có yếu tố tu luyện siêu nhiên như tiên hiệp, giữ
đúng các quy ước sau.

## Văn phong

- Giọng văn cổ trang, hào sảng, đậm chất giang hồ — câu văn có thể ngắn
  gọn, dứt khoát khi miêu tả cảnh giao đấu, nhưng vẫn trang trọng khi
  miêu tả tình huống/nhân vật.
- Không dùng thuật ngữ tu tiên (cảnh giới, đan dược thần kỳ) — thế giới
  kiếm hiệp thiên về con người thật, võ công luyện tập được chứ không
  phải phép thuật.

## Xưng hô

- Đồng môn: "sư huynh/sư tỷ/sư đệ/sư muội" theo môn phái, "sư phụ/sư
  nương" với người dạy võ.
- Giang hồ đồng đạo: "huynh đài", "các hạ", "tại hạ" khi xưng hô lịch sự
  giữa những người không quen biết; "huynh/đệ" khi đã thân thiết.
- Người có địa vị/tuổi tác cao: "tiền bối", "đại hiệp" (kính trọng người
  có võ công/danh tiếng); "vãn bối" khi tự xưng với bậc trên.
- Kẻ thù/địch nhân: "ngươi/ta", có thể kèm khinh miệt tùy ngữ cảnh
  ("tên/thằng" nếu nguyên tác có sắc thái tương tự).

## Thuật ngữ đặc trưng

- Tên môn phái, chiêu thức, bí kíp võ công: giữ Hán Việt nhất quán, không
  dịch nghĩa đen sang tiếng thuần Việt trừ khi tên có dụng ý đặc biệt.
- Binh khí: giữ tên gọi Hán Việt quen thuộc (trường kiếm, đao, thương...)
  thay vì dịch chung chung "kiếm/dao".
- Nội công/khí công: phân biệt rõ với "tu vi" của tiên hiệp — đây là kết
  quả khổ luyện, không phải "đột phá cảnh giới" kiểu thần thánh hóa.

## Lưu ý khác

- Không lẫn thuật ngữ tiên hiệp (đan điền, kim đan, phi thăng...) vào
  văn bản kiếm hiệp trừ khi nguyên tác chủ động pha trộn hai thể loại.
- Giữ không khí "ân oán giang hồ" — đối thoại nên có chất hào hùng/bi
  tráng đặc trưng của thể loại, không hiện đại hóa lời thoại.
```

- [ ] **Step 6: `agents/en/kiem-hiep.md`**

```markdown
# Translation Guide — Wuxia

Translate into English. Genre: wuxia (jianghu, martial arts schools,
rivalries and debts of honor) — no supernatural cultivation system like
xianxia; follow these conventions.

## Style

- Period-flavored but readable register, with a heroic/dramatic tone —
  sentences can be terse and clipped during combat scenes, more formal
  when describing character and circumstance.
- Do not borrow xianxia terminology (cultivation realms, magical pills) —
  wuxia's world is grounded in trained human skill, not magic.

## Forms of address

- Fellow disciples: "Senior/Junior Brother/Sister" by sect rank; "Master"
  for one's martial arts teacher.
- Jianghu peers: "Young Hero"/formal address between strangers who
  respect each other's standing; first names or "Brother" once familiar.
- Higher-status or senior figures: "Senior", "Great Hero" (for a
  respected/famous martial artist); a junior refers to themselves humbly
  when addressing such a figure.
- Enemies: plain "you", with contempt conveyed through word choice rather
  than an invented honorific.

## Genre-specific terminology

- Sect names, techniques, martial arts manuals: keep proper-noun flavor
  consistent (a transliterated or fixed English rendering used the same
  way every time) rather than re-translating loosely each occurrence.
- Weapons: use specific English weapon terms (longsword, saber, spear)
  rather than a generic "sword/blade" that loses the distinction the
  original makes.
- Internal energy/qi-as-trained-skill: keep this distinct from a xianxia
  "cultivation realm" framing — it's the product of hard training, not a
  mystical breakthrough.

## Other notes

- Don't let xianxia vocabulary (dantian, golden core, ascension) leak
  into a wuxia text unless the source itself deliberately blends genres.
- Preserve the "jianghu code of honor" atmosphere — dialogue should carry
  the genre's heroic/tragic weight, not read as modern-day speech.
```

- [ ] **Step 7: `agents/vn/hoc-duong.md`**

```markdown
# Hướng dẫn dịch — Học đường

Dịch sang tiếng Việt. Thể loại học đường (trung học/đại học, tuổi mới
lớn, đời sống lớp học) — giữ đúng các quy ước sau.

## Văn phong

- Giọng văn trẻ trung, hiện đại, gần với cách nói chuyện thật của học
  sinh/sinh viên — có thể dùng khẩu ngữ nhẹ nhàng, không cần trang trọng.
- Đối thoại giữa bạn bè nên tự nhiên, ngắn gọn, đúng chất tuổi teen —
  tránh câu văn quá "người lớn"/văn viết.

## Xưng hô

- Bạn bè cùng lớp/cùng tuổi: "cậu/tớ" hoặc "mày/tao" (tùy mức độ thân
  thiết và văn phong nguyên tác) hoặc "bạn/tôi" nếu trang trọng hơn.
- Học sinh với giáo viên: "em/thầy" hoặc "em/cô", giữ đúng phép tắc lễ
  phép học đường Việt Nam.
- Đàn anh/đàn em khác khóa: "anh/chị" (khóa trên), "em" (khóa dưới) —
  tương tự cách xưng hô ở trường học Việt Nam thực tế, không dùng
  "senpai/kohai" trừ khi bản gốc có bối cảnh Nhật rõ ràng và cố ý giữ.
- Lớp trưởng/ban cán sự lớp: gọi theo chức danh khi trang trọng ("lớp
  trưởng ơi"), gọi tên khi thân mật.

## Thuật ngữ đặc trưng

- Chức danh/tổ chức học đường: "lớp trưởng", "bí thư chi đoàn", "câu lạc
  bộ", "hội học sinh" — dùng đúng thuật ngữ trường học Việt Nam thay vì
  dịch nguyên văn hệ thống trường học nước ngoài.
- Môn học/kỳ thi: có thể Việt hóa tên môn học, kỳ thi cho gần gũi với học
  sinh Việt Nam, trừ khi bối cảnh nguyên tác rõ ràng ở nước khác và cần
  giữ nguyên để không sai bối cảnh.

## Lưu ý khác

- Có thể dùng tiếng lóng học đường nhẹ nhàng, đúng thời điểm nguyên tác
  hướng đến (không dùng slang quá cũ hoặc quá mới gây lệch bối cảnh).
- Giữ được không khí hồn nhiên/tinh nghịch đặc trưng tuổi học trò, tránh
  dịch quá nghiêm túc/người lớn hóa nhân vật.
```

- [ ] **Step 8: `agents/en/hoc-duong.md`**

```markdown
# Translation Guide — School / Campus

Translate into English. Genre: school/campus life (secondary school or
college, teen life, classroom dynamics) — follow these conventions.

## Style

- Young, contemporary register close to how actual students talk —
  casual phrasing is fine; this genre does not need a formal voice.
- Dialogue between friends should be natural and clipped, true to teen
  speech patterns — avoid overly "adult"/literary sentence construction.

## Forms of address

- Classmates/peers: first names, nicknames — casual and familiar, the
  way real classmates talk to each other.
- Student to teacher: "Mr./Ms./Mrs. [Last Name]", or "Teacher" only if
  the source setting specifically calls for that convention (e.g. an
  East Asian school setting kept deliberately) — otherwise use the
  English-school convention.
- Upperclassmen/underclassmen: by name, with "senior"/"freshman" etc. as
  descriptive terms rather than direct address — English school culture
  doesn't have a direct honorific for grade seniority the way some
  source languages do; don't invent one.
- Class officers/student council: refer to them by role when formal
  ("class president"), by name when casual.

## Genre-specific terminology

- School organizations/titles: "class president", "student council",
  "club" — use real English school-system terms rather than a literal
  translation of a foreign school system's structure.
- Subjects/exams: localize naturally for an English-reading audience
  unless the source setting is explicitly and importantly set in a
  specific country's school system that should be preserved.

## Other notes

- Light, appropriately-dated slang is fine if it matches the story's
  intended time period — don't use slang that's jarringly too old or
  too current for the setting.
- Preserve the innocent/playful energy typical of this genre — avoid
  making characters sound more serious or adult than intended.
```

- [ ] **Step 9: `agents/vn/hai-huoc.md`**

```markdown
# Hướng dẫn dịch — Hài hước

Dịch sang tiếng Việt. Thể loại hài hước (dí dỏm, chơi chữ, tình huống
oái oăm) — giữ đúng các quy ước sau.

## Văn phong

- Ưu tiên giữ được tiếng cười hơn là bám sát câu chữ — đây là thể loại
  DUY NHẤT trong bộ hướng dẫn này được phép thoát ý mạnh khi cần, miễn
  giữ được hiệu ứng hài hước tương đương.
- Nhịp điệu câu văn cần nhanh, dí d�ỏm — tránh câu dài dòng làm loãng
  điểm hài.

## Xưng hô

- Linh hoạt theo quan hệ nhân vật như thể loại tương ứng (đô thị, học
  đường...) — nhưng có thể phóng đại/chơi chữ trong cách xưng hô nếu
  nguyên tác cố ý làm vậy để gây cười.

## Thuật ngữ đặc trưng

- Chơi chữ/thành ngữ dân gian: khi một câu đùa dựa trên chơi chữ của
  ngôn ngữ gốc không thể dịch nguyên nghĩa, hãy tìm một câu chơi chữ
  tương đương trong tiếng Việt tạo hiệu ứng hài tương tự, thay vì dịch
  sát nghĩa khiến câu đùa mất tác dụng.
- Tên nhân vật/địa danh mang tính hài (chơi chữ có chủ đích): có thể Việt
  hóa/đặt lại tên để giữ được điểm hài, ghi chú lại trong glossary.json
  nếu tên đó xuất hiện lặp lại.

## Lưu ý khác

- Nếu một câu đùa thực sự không thể chuyển ngữ mà giữ được hiệu ứng, ưu
  tiên giữ được tiếng cười ở vị trí đó bằng một câu đùa khác phù hợp ngữ
  cảnh, hơn là dịch sát nghĩa nhưng làm câu văn trở nên vô nghĩa/không
  buồn cười.
- Tránh lạm dụng thoát ý ở những đoạn không mang tính hài — chỉ áp dụng
  quyền tự do này cho đúng đoạn cần gây cười.
```

- [ ] **Step 10: `agents/en/hai-huoc.md`**

```markdown
# Translation Guide — Comedy

Translate into English. Genre: comedy (wit, wordplay, absurd situations)
— follow these conventions.

## Style

- Prioritize preserving the laugh over literal wording — this is the
  ONE genre in this library where strong localization/adaptation is
  explicitly allowed, as long as the comedic effect lands.
- Keep sentence rhythm quick and punchy — a joke buried in a long,
  meandering sentence loses its timing.

## Forms of address

- Follow the conventions of whatever underlying setting the story uses
  (urban, school, etc.) — but exaggeration or wordplay in how characters
  address each other is fine to preserve if the original does it on
  purpose for comedic effect.

## Genre-specific terminology

- Wordplay/puns: when a joke depends on wordplay in the source language
  that has no direct English equivalent, find an English pun or joke
  that produces a similar comedic effect in that spot, rather than a
  literal translation that kills the joke.
- Comedic character/place names (deliberately punny in the original):
  it's acceptable to localize or re-coin the name to preserve the joke —
  note it in glossary.json if the name recurs, so later chapters stay
  consistent.

## Other notes

- When a joke genuinely cannot be carried over with its exact effect
  intact, prioritize landing a joke of similar spirit at that same beat
  over a literal-but-unfunny translation.
- Don't over-apply this adaptation freedom to non-comedic passages —
  only the parts meant to be funny get this latitude.
```

- [ ] **Step 11: `agents/vn/fantasy.md`**

```markdown
# Hướng dẫn dịch — Fantasy (phương Tây)

Dịch sang tiếng Việt. Thể loại fantasy kiểu phương Tây (pháp sư, hiệp
sĩ, rồng, vương quốc giả tưởng) — khác hẳn tiên hiệp về hệ thống thuật
ngữ, giữ đúng các quy ước sau.

## Văn phong

- Giọng văn trang trọng kiểu sử thi phương Tây — không dùng thuật ngữ
  Hán Việt kiểu tiên hiệp/kiếm hiệp (không "tu vi", "cảnh giới", "sư
  huynh").
- Miêu tả phép thuật/chiến đấu có thể giàu hình ảnh, nhịp điệu gần với
  văn phong dịch tiểu thuyết fantasy phương Tây quen thuộc với độc giả
  Việt (kiểu Harry Potter, Lord of the Rings đã được dịch).

## Xưng hô

- Quý tộc/hoàng gia: "ngài", "bệ hạ", "điện hạ", "huân tước/phu nhân" —
  theo hệ thống tước vị phương Tây, không dùng "tiền bối/vãn bối" kiểu
  Á Đông.
- Hiệp sĩ/quân đội: "ngài hiệp sĩ", "chỉ huy", "binh nhì" theo cấp bậc
  quân sự phương Tây.
- Pháp sư/học viện phép thuật: "thầy/trò" kiểu học viện (giống "giáo sư/
  sinh viên" hơn là "sư phụ/đệ tử" kiểu tu tiên).
- Thường dân với quý tộc: "thưa ngài/thưa quý cô" — giữ khoảng cách xã
  hội kiểu phong kiến châu Âu.

## Thuật ngữ đặc trưng

- Tên riêng phương Tây (nhân vật, địa danh): phiên âm hoặc giữ nguyên
  chữ Latin tùy quy ước đã chọn cho tác phẩm — nhất quán xuyên suốt,
  không Hán Việt hóa.
- Hệ thống phép thuật: dùng thuật ngữ kiểu "pháp sư", "phù thủy", "thần
  chú", "ma pháp" — khác biệt rõ với "tu luyện/pháp thuật tiên gia" của
  tiên hiệp.
- Chủng tộc giả tưởng (yêu tinh, người lùn, rồng...): dùng tên gọi quen
  thuộc với độc giả Việt qua các bản dịch fantasy phổ biến, trừ khi tác
  phẩm có tên gọi riêng cần giữ nguyên.

## Lưu ý khác

- Không để thuật ngữ tiên hiệp/kiếm hiệp lẫn vào bản dịch fantasy — hai
  hệ thống thế giới quan khác nhau hoàn toàn.
- Tên riêng phương Tây dài/khó đọc: giữ nguyên cách viết, không tự ý rút
  gọn trừ khi nguyên tác cũng dùng dạng rút gọn đó.
```

- [ ] **Step 12: `agents/en/fantasy.md`**

```markdown
# Translation Guide — Western Fantasy

Translate into English. Genre: Western-style high/low fantasy (mages,
knights, dragons, invented kingdoms) — follow these conventions.

## Style

- Elevated, epic-fantasy register in the vein of well-known translated
  Western fantasy — not the xianxia/wuxia cultivation-genre voice.
- Combat and magic description can be vivid and rhythmic, matching the
  pacing conventions readers expect from this genre.

## Forms of address

- Nobility/royalty: "my lord/lady", "Your Majesty", "Your Highness",
  formal titles ("Lord/Lady So-and-so") — a Western feudal address
  system, not an Eastern master/disciple one.
- Knights/military: rank-based address ("Sir Knight", "Commander",
  "Private") following a Western military hierarchy.
- Mages/magic academies: an academic teacher/student relationship
  ("Professor"/student), not a cultivation-style master/disciple bond.
- Commoners to nobility: "my lord/my lady" — preserve the social
  distance of a European-feudal-flavored setting.

## Genre-specific terminology

- Proper nouns (characters, places): keep them in their original
  Latin-alphabet form or a consistent transliteration already
  established for the work — never render them with Sino-Vietnamese-
  style naming conventions.
- Magic system: use terms like "mage", "sorcerer", "spell", "arcane
  magic" — clearly distinct from a xianxia cultivation framing.
- Fantasy races (elves, dwarves, dragons, etc.): use the names already
  familiar to genre readers unless the work has coined its own specific
  terms that need preserving.

## Other notes

- Do not let xianxia/wuxia vocabulary bleed into a Western fantasy
  translation — these are different worldbuilding systems entirely.
- Keep long/unusual Western proper nouns spelled exactly as given —
  don't shorten them unless the source itself uses a shortened form.
```

- [ ] **Step 13: `agents/vn/general.md`**

```markdown
# Hướng dẫn dịch — Chung (không xác định thể loại)

Dịch sang tiếng Việt. Dùng khi chưa xác định rõ thể loại tác phẩm, hoặc
tác phẩm không thuộc hẳn một thể loại cụ thể nào trong thư viện này.

## Văn phong

- Dịch trung thực, tự nhiên, giữ đúng văn phong và giọng điệu của nguyên
  tác — không thêm/bớt sắc thái riêng của người dịch.
- Khi không chắc chắn về mức độ trang trọng/thân mật phù hợp, ưu tiên
  bám sát mức độ mà nguyên tác thể hiện thay vì tự suy đoán.

## Xưng hô

- Giữ đúng quan hệ xưng hô như nguyên tác thể hiện (tuổi tác, địa vị,
  mức độ thân thiết) — dịch theo ngữ cảnh cụ thể của từng đoạn hội thoại
  thay vì áp dụng một khuôn mẫu cố định.
- Khi nguyên tác dùng đại từ trung tính không rõ sắc thái, chọn cách
  xưng hô tiếng Việt tự nhiên và trung tính tương ứng, tránh suy diễn
  quá xa.

## Thuật ngữ đặc trưng

- Với tên riêng/thuật ngữ chuyên môn xuất hiện lặp lại, ghi nhận lại
  cách dịch đã chọn (glossary.json nếu workspace có) và giữ nhất quán
  cho các lần xuất hiện sau.
- Khi gặp thuật ngữ mơ hồ về thể loại, ưu tiên cách dịch phổ thông, dễ
  hiểu nhất thay vì áp dụng quy ước đặc trưng của một thể loại cụ thể
  (tiên hiệp, kiếm hiệp...) mà tác phẩm chưa chắc thuộc về.

## Lưu ý khác

- Khi không chắc chắn, ưu tiên dịch sát nghĩa và rõ ràng — tránh thoát ý
  quá xa nếu không có cơ sở chắc chắn về ý đồ của tác giả.
- Nếu trong quá trình dịch nhận ra tác phẩm thực chất thuộc một thể loại
  cụ thể trong thư viện (tiên hiệp, ngôn tình...), cân nhắc chuyển sang
  dùng template phù hợp hơn cho các chương sau.
```

- [ ] **Step 14: `agents/en/general.md`**

```markdown
# Translation Guide — General (genre unspecified)

Translate into English. Use this when the work's genre isn't yet clear,
or when it doesn't cleanly fit any specific genre in this library.

## Style

- Translate faithfully and naturally, preserving the source's own style
  and tone — don't impose a translator's personal voice on top of it.
- When the right level of formality/familiarity is unclear, default to
  matching whatever level the source text itself demonstrates rather
  than guessing at a convention.

## Forms of address

- Preserve whatever address relationships the source shows (age, status,
  closeness) — decide per passage from context rather than applying one
  fixed template throughout.
- When the source uses a neutral pronoun/address term with unclear
  connotation, choose the most natural neutral English equivalent rather
  than over-interpreting.

## Genre-specific terminology

- For recurring proper nouns/specialized terms, record the translation
  choice made (in glossary.json, if the workspace has one) and stay
  consistent for every later occurrence.
- For genre-ambiguous terminology, prefer the plain, most broadly
  understandable rendering over applying a specific genre's convention
  (xianxia, wuxia, etc.) the work may not actually belong to.

## Other notes

- When uncertain, favor a literal and clear translation over strong
  adaptation — don't take large liberties without solid grounding in the
  author's evident intent.
- If it becomes clear partway through that the work does fit a specific
  genre in this library (xianxia, romance, etc.), consider switching to
  that more specific template for later chapters.
```

- [ ] **Step 15: Commit**

```bash
git add agents/
git commit -m "feat: add the 14-file agent template library (7 genres x 2 languages)"
```

---

### Task 2: `server/agent_templates.py`

**Files:**
- Create: `server/agent_templates.py`
- Test: `tests/test_agent_templates.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (Task 1's files exist on disk, but
  this task's tests use a monkeypatched, isolated `AGENTS_ROOT`, matching
  `tests/test_workspace.py`'s `isolated_workspaces_root` convention).
- Produces: `AGENTS_ROOT: Path`; `list_templates() -> dict[str, list[str]]`;
  `resolve_template_path(template: str) -> Path` (raises `ValueError` for
  a malformed template string, `FileNotFoundError` for a well-formed one
  naming a file that doesn't exist).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_agent_templates.py`:

```python
import pytest

from server import agent_templates


@pytest.fixture(autouse=True)
def isolated_agents_root(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_templates, "AGENTS_ROOT", tmp_path / "agents")


def _seed(lang, genre, content="nội dung"):
    path = agent_templates.AGENTS_ROOT / lang / f"{genre}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_list_templates_on_missing_root_returns_empty_dict():
    assert agent_templates.list_templates() == {}


def test_list_templates_groups_by_language():
    _seed("vn", "tien-hiep")
    _seed("vn", "ngon-tinh")
    _seed("en", "tien-hiep")

    result = agent_templates.list_templates()

    assert result == {"vn": ["ngon-tinh", "tien-hiep"], "en": ["tien-hiep"]}


def test_resolve_template_path_returns_existing_file():
    path = _seed("vn", "tien-hiep", "nội dung mẫu")

    resolved = agent_templates.resolve_template_path("vn/tien-hiep")

    assert resolved == path
    assert resolved.read_text(encoding="utf-8") == "nội dung mẫu"


def test_resolve_template_path_rejects_malformed_string_no_slash():
    with pytest.raises(ValueError):
        agent_templates.resolve_template_path("tien-hiep")


def test_resolve_template_path_rejects_too_many_parts():
    with pytest.raises(ValueError):
        agent_templates.resolve_template_path("vn/tien-hiep/extra")


def test_resolve_template_path_rejects_path_traversal_payload():
    with pytest.raises(ValueError):
        agent_templates.resolve_template_path("../etc")


def test_resolve_template_path_rejects_invalid_characters():
    with pytest.raises(ValueError):
        agent_templates.resolve_template_path("vn/tien hiep")


def test_resolve_template_path_raises_file_not_found_for_missing_file():
    with pytest.raises(FileNotFoundError):
        agent_templates.resolve_template_path("vn/does-not-exist")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_agent_templates.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'server.agent_templates'`.

- [ ] **Step 3: Write the implementation**

Create `server/agent_templates.py`:

```python
import re
from pathlib import Path

AGENTS_ROOT = Path(__file__).resolve().parent.parent / "agents"
_SLUG_PATTERN = re.compile(r"[a-z0-9_-]+")


def _is_valid_slug(value: str) -> bool:
    return isinstance(value, str) and _SLUG_PATTERN.fullmatch(value) is not None


def list_templates() -> dict[str, list[str]]:
    if not AGENTS_ROOT.exists():
        return {}
    result = {}
    for lang_dir in sorted(AGENTS_ROOT.iterdir()):
        if not lang_dir.is_dir():
            continue
        genres = sorted(p.stem for p in lang_dir.glob("*.md"))
        result[lang_dir.name] = genres
    return result


def resolve_template_path(template: str) -> Path:
    parts = template.split("/")
    if len(parts) != 2:
        raise ValueError(f"Malformed template id: '{template}' (expected '<lang>/<genre>')")
    lang, genre = parts
    if not _is_valid_slug(lang) or not _is_valid_slug(genre):
        raise ValueError(f"Malformed template id: '{template}'")
    path = AGENTS_ROOT / lang / f"{genre}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Agent template not found: '{template}'")
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_agent_templates.py -v`
Expected: all 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add server/agent_templates.py tests/test_agent_templates.py
git commit -m "feat: add agent_templates.py — list and safely resolve shared agent templates"
```

---

### Task 3: `GET /api/agent-templates`

**Files:**
- Modify: `server/main.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `agent_templates.list_templates()` (Task 2).
- Produces: `GET /api/agent-templates` → `{"<lang>": ["<genre>", ...], ...}`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_api.py`:

```python
def test_get_agent_templates_returns_grouped_list(tmp_path, monkeypatch):
    (tmp_path / "vn").mkdir()
    (tmp_path / "vn" / "tien-hiep.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(agent_templates, "AGENTS_ROOT", tmp_path)

    client = TestClient(app)
    response = client.get("/api/agent-templates")

    assert response.status_code == 200
    assert response.json() == {"vn": ["tien-hiep"]}
```

Add `from server import agent_templates` to `tests/test_api.py`'s
existing import block (alongside `from server import main as server_main`
and `from server import workspace`).

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_api.py -k agent_templates -v`
Expected: FAIL with 404 (the route doesn't exist yet).

- [ ] **Step 3: Add the route**

In `server/main.py`, add the import alongside the existing `from server import workspace`:

```python
from server import agent_templates
```

Add the route (anywhere among the other `@app.get(...)` routes, e.g.
right after `get_nodes`):

```python
@app.get("/api/agent-templates")
def get_agent_templates():
    return agent_templates.list_templates()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_api.py -k agent_templates -v`
Expected: PASS.

- [ ] **Step 5: Run the full API test file**

Run: `pytest tests/test_api.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add server/main.py tests/test_api.py
git commit -m "feat: add GET /api/agent-templates"
```

---

### Task 4: `LoadAgentFile`'s `template` field

**Files:**
- Modify: `server/nodes/translate.py:30-43` (the `LoadAgentFile` class)
- Test: `tests/test_translate_nodes.py`

**Interfaces:**
- Consumes: `agent_templates.resolve_template_path` (Task 2).
- Produces: `LoadAgentFile.execute(workspace_name, template="workspace") -> (str,)`.
  `SaveAgentFile` is untouched by this task — it already writes to the
  workspace's own `agent.md`, which is exactly what a customized save
  should do.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_translate_nodes.py`:

```python
def test_load_agent_file_node_loads_a_shared_template(tmp_path, monkeypatch):
    workspace.create_workspace("novel-a")
    monkeypatch.setattr(agent_templates, "AGENTS_ROOT", tmp_path)
    template_dir = tmp_path / "vn"
    template_dir.mkdir()
    (template_dir / "tien-hiep.md").write_text("Nội dung mẫu tiên hiệp", encoding="utf-8")
    node = get_node_class("LoadAgentFile")()

    result = node.execute(workspace_name="novel-a", template="vn/tien-hiep")

    assert result == ("Nội dung mẫu tiên hiệp",)


def test_load_agent_file_node_still_defaults_to_the_workspace_file():
    """Confirms the pre-existing behavior survives unchanged: calling
    execute() exactly like every test written before this feature existed
    (no `template` argument at all) must keep reading workspace/agent.md."""
    workspace.create_workspace("novel-a")
    node = get_node_class("LoadAgentFile")()

    result = node.execute(workspace_name="novel-a")

    assert "Dịch sang tiếng Việt" in result[0]
```

Add `from server import agent_templates` to this file's existing imports.

(The second test duplicates what `test_load_agent_file_node_reads_seeded_file`
already covers, but states explicitly what property is being protected —
both must pass unchanged after this task's edit.)

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `pytest tests/test_translate_nodes.py -k load_agent_file -v`
Expected: `test_load_agent_file_node_loads_a_shared_template` FAILs with
`TypeError: execute() got an unexpected keyword argument 'template'`; the
other two (`test_load_agent_file_node_reads_seeded_file` and the new
`_still_defaults_` one) already PASS against the current code.

- [ ] **Step 3: Update `LoadAgentFile`**

Currently:

```python
@register_node("LoadAgentFile")
class LoadAgentFile(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    def execute(self, workspace_name: str) -> tuple:
        path = workspace.get_workspace_path(workspace_name, "agent.md")
        return (load_agent_file(path),)
```

Change to:

```python
@register_node("LoadAgentFile")
class LoadAgentFile(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {"template": ("STRING", {"default": "workspace", "widget": "agent_template"})},
        }

    def execute(self, workspace_name: str, template: str = "workspace") -> tuple:
        if template == "workspace":
            path = workspace.get_workspace_path(workspace_name, "agent.md")
        else:
            path = agent_templates.resolve_template_path(template)
        return (load_agent_file(path),)
```

Add `from server import agent_templates` to `server/nodes/translate.py`'s
existing imports, alongside `from server import workspace`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_translate_nodes.py -k load_agent_file -v`
Expected: all 3 PASS.

- [ ] **Step 5: Run the full node test file**

Run: `pytest tests/test_translate_nodes.py -v`
Expected: all PASS — every pre-existing test, including
`test_load_agent_file_node_raises_when_missing`, is unaffected.

- [ ] **Step 6: Commit**

```bash
git add server/nodes/translate.py tests/test_translate_nodes.py
git commit -m "feat: let LoadAgentFile load a shared agent template, default unchanged"
```

---

### Task 5: The "Chọn agent…" picker modal

**Files:**
- Create: `web/js/agent_template_picker.js`
- Modify: `web/canvas.html`
- Modify: `web/js/inspector_panel.js:89-103` (the STRING-field render loop)
- Modify: `web/js/i18n.js`

**Interfaces:**
- Consumes: `GET /api/agent-templates` (Task 3).
- Produces: `openAgentTemplatePicker(onSelect)` — a global function.
  `onSelect` is called with either `"workspace"` or `"<lang>/<genre>"`.

This task defines its **own**, self-contained CSS classes
(`agent-template-picker-*`) rather than assuming the Path Picker
sub-project's `path-picker-*` classes already exist in the live
`canvas.html` — the two sub-projects are independent and may land in
either order (see Global Constraints).

- [ ] **Step 1: Add the i18n keys**

In `web/js/i18n.js`, add to the `vi` object:

```js
    agentTemplateButton: "Chọn agent...",
    agentTemplateWorkspaceOption: "Tùy chỉnh riêng cho workspace này",
    agentTemplateCancel: "Hủy",
```

And to the `en` object:

```js
    agentTemplateButton: "Choose agent...",
    agentTemplateWorkspaceOption: "Custom for this workspace",
    agentTemplateCancel: "Cancel",
```

- [ ] **Step 2: Write `web/js/agent_template_picker.js`**

```js
let agentTemplatePickerState = null;

function openAgentTemplatePicker(onSelect) {
  closeAgentTemplatePicker();

  const overlay = document.createElement("div");
  overlay.id = "agent-template-picker-overlay";
  overlay.className = "agent-template-picker-overlay";

  const modal = document.createElement("div");
  modal.className = "agent-template-picker-modal";

  const workspaceOption = document.createElement("div");
  workspaceOption.className = "agent-template-picker-item";
  workspaceOption.textContent = t("agentTemplateWorkspaceOption");
  workspaceOption.addEventListener("click", () => {
    onSelect("workspace");
    closeAgentTemplatePicker();
  });
  modal.appendChild(workspaceOption);

  const tabs = document.createElement("div");
  tabs.className = "agent-template-picker-tabs";
  modal.appendChild(tabs);

  const list = document.createElement("div");
  list.className = "agent-template-picker-list";
  modal.appendChild(list);

  const actions = document.createElement("div");
  actions.className = "agent-template-picker-actions";
  const cancelButton = document.createElement("button");
  cancelButton.textContent = t("agentTemplateCancel");
  cancelButton.addEventListener("click", closeAgentTemplatePicker);
  actions.appendChild(cancelButton);
  modal.appendChild(actions);

  overlay.appendChild(modal);
  document.body.appendChild(overlay);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) closeAgentTemplatePicker();
  });

  agentTemplatePickerState = { onSelect, data: {}, activeLang: null };

  fetch("/api/agent-templates")
    .then((response) => response.json())
    .then((data) => {
      if (!agentTemplatePickerState) return;
      agentTemplatePickerState.data = data;
      agentTemplatePickerState.activeLang = Object.keys(data)[0] || null;
      renderAgentTemplateTabs();
      renderAgentTemplateList();
    });
}

function closeAgentTemplatePicker() {
  const overlay = document.getElementById("agent-template-picker-overlay");
  if (overlay) overlay.remove();
  agentTemplatePickerState = null;
}

function renderAgentTemplateTabs() {
  const overlay = document.getElementById("agent-template-picker-overlay");
  if (!overlay || !agentTemplatePickerState) return;
  const tabs = overlay.querySelector(".agent-template-picker-tabs");
  tabs.innerHTML = "";

  for (const lang of Object.keys(agentTemplatePickerState.data)) {
    const tab = document.createElement("button");
    tab.className =
      "agent-template-picker-tab" + (lang === agentTemplatePickerState.activeLang ? " active" : "");
    tab.textContent = lang.toUpperCase();
    tab.addEventListener("click", () => {
      agentTemplatePickerState.activeLang = lang;
      renderAgentTemplateTabs();
      renderAgentTemplateList();
    });
    tabs.appendChild(tab);
  }
}

function renderAgentTemplateList() {
  const overlay = document.getElementById("agent-template-picker-overlay");
  if (!overlay || !agentTemplatePickerState) return;
  const list = overlay.querySelector(".agent-template-picker-list");
  list.innerHTML = "";

  const lang = agentTemplatePickerState.activeLang;
  const genres = (lang && agentTemplatePickerState.data[lang]) || [];

  for (const genre of genres) {
    const item = document.createElement("div");
    item.className = "agent-template-picker-item";
    item.textContent = genre;
    item.addEventListener("click", () => {
      agentTemplatePickerState.onSelect(`${lang}/${genre}`);
      closeAgentTemplatePicker();
    });
    list.appendChild(item);
  }
}
```

- [ ] **Step 3: Add the modal CSS and script tag to `web/canvas.html`**

Add this block to the `<style>` section:

```css
    .agent-template-picker-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 100;
    }
    .agent-template-picker-modal {
      width: 420px;
      max-height: 70vh;
      display: flex;
      flex-direction: column;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 9px;
      padding: 14px;
      box-sizing: border-box;
    }
    .agent-template-picker-tabs {
      display: flex;
      gap: 6px;
      margin: 8px 0;
    }
    .agent-template-picker-tab {
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text-faint);
      font-size: 11.5px;
      padding: 5px 10px;
      border-radius: 6px;
      cursor: pointer;
    }
    .agent-template-picker-tab.active,
    .agent-template-picker-tab:hover { border-color: var(--accent); color: var(--accent); }
    .agent-template-picker-list {
      flex: 1;
      overflow-y: auto;
      border: 1px solid var(--border);
      border-radius: 6px;
      margin-bottom: 10px;
    }
    .agent-template-picker-item {
      padding: 7px 10px;
      font-size: 12.5px;
      color: var(--text);
      cursor: pointer;
    }
    .agent-template-picker-item:hover { background: var(--bg-hover); }
    .agent-template-picker-actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }
    .agent-template-picker-actions button {
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 12px;
      padding: 8px 14px;
      border-radius: 6px;
      cursor: pointer;
    }
    .agent-template-picker-actions button:hover { border-color: var(--accent); color: var(--accent); }
```

Add the script tag right before `inspector_panel.js`'s own tag:

```html
  <script src="/js/agent_template_picker.js"></script>
  <script src="/js/inspector_panel.js"></script>
```

- [ ] **Step 4: Wire the button in `web/js/inspector_panel.js`**

The current STRING-field loop is:

```js
  for (const [name, spec] of Object.entries(allInputs)) {
    const inputType = spec[0];
    if (inputType !== "STRING" || linked.has(name)) continue;

    appendInspectorLabel(panel, name);
    const field = document.createElement("textarea");
    field.className = "inspector-input";
    field.rows = 3;
    field.value = node.properties[name] || "";
    field.addEventListener("input", () => {
      node.properties[name] = field.value;
      markActiveDirty();
    });
    panel.appendChild(field);
  }
```

Change it to:

```js
  for (const [name, spec] of Object.entries(allInputs)) {
    const inputType = spec[0];
    if (inputType !== "STRING" || linked.has(name)) continue;

    appendInspectorLabel(panel, name);
    const field = document.createElement("textarea");
    field.className = "inspector-input";
    field.rows = 3;
    field.value = node.properties[name] || "";
    field.addEventListener("input", () => {
      node.properties[name] = field.value;
      markActiveDirty();
    });
    panel.appendChild(field);

    const config = spec[1] || {};
    if (config.widget === "agent_template") {
      const chooseButton = document.createElement("button");
      chooseButton.className = "inspector-browse-button";
      chooseButton.textContent = t("agentTemplateButton");
      chooseButton.addEventListener("click", () => {
        openAgentTemplatePicker((chosen) => {
          field.value = chosen;
          node.properties[name] = chosen;
          markActiveDirty();
        });
      });
      panel.appendChild(chooseButton);
    }
  }
```

If the Path Picker sub-project has already landed in this codebase by
the time this task runs, `.inspector-browse-button` already exists (its
own plan defines it) and this reuses it as-is — a shared, generic
"small button under a textarea" style, not specific to either feature.
If it has **not** landed yet, add this task's own copy of that one CSS
rule to `web/canvas.html`'s `<style>` section (next to the
`.inspector-input:focus` rule), so this task is correct standing alone:

```css
    .inspector-browse-button {
      width: 100%;
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text-faint);
      font-size: 11.5px;
      padding: 6px 8px;
      border-radius: 6px;
      cursor: pointer;
      margin-top: 4px;
      box-sizing: border-box;
    }
    .inspector-browse-button:hover { border-color: var(--accent); color: var(--accent); }
```

Adding this rule twice (once from each independent plan) is harmless —
CSS rules with identical selectors and identical declarations simply
apply the same style redundantly, with no visual or functional
difference; whichever plan lands second should skip re-adding it once
it notices the rule already present, but is not required to check.

- [ ] **Step 5: Manual verification**

Start the server, open the canvas page. Drag a `LoadAgentFile` node onto
the canvas, select it — confirm its (optional) `template` field renders
with a "Chọn agent..." button. Click it — confirm the modal shows
"Tùy chỉnh riêng cho workspace này" at the top, language tabs below it
(from the real `agents/` directory populated in Task 1), and clicking a
genre fills the field with `"<lang>/<genre>"` and closes the modal.
Clicking "Tùy chỉnh riêng cho workspace này" fills the field with
`"workspace"`. Run the node (via the inspector's "Chạy node này" button,
against a real workspace) with a chosen template and confirm its output
text matches the chosen template file's real content.

- [ ] **Step 6: Commit**

```bash
git add web/js/agent_template_picker.js web/canvas.html web/js/inspector_panel.js web/js/i18n.js
git commit -m "feat: add the agent template picker modal"
```

---

### Task 6: End-to-end verification

**Files:**
- None created/modified — verification only.

- [ ] **Step 1: Full walkthrough**

- Run the full pytest suite: `pytest -q` — expect every test passing,
  including the new `tests/test_agent_templates.py` and the additions to
  `tests/test_api.py`/`tests/test_translate_nodes.py`.
- Confirm all 14 files under `agents/` are present, each non-empty, and
  each contains all four required section headings (`## Văn phong`,
  `## Xưng hô`, `## Thuật ngữ đặc trưng`, `## Lưu ý khác` for the `vn`
  files; `## Style`, `## Forms of address`, `## Genre-specific
  terminology`, `## Other notes` for the `en` files).
- In the browser: create a new workspace, drag `LoadAgentFile`, leave
  `template` at its default — confirm it still loads that workspace's
  own `agent.md` (today's exact behavior, unchanged).
- Change `template` to `vn/tien-hiep` via the picker, run the node,
  confirm the output text is the real xianxia template content (not the
  workspace's own file).
- Confirm `SaveAgentFile` still only ever writes to the workspace's own
  `agent.md` regardless of what `LoadAgentFile.template` was set to —
  it has no `template` field at all and was never modified by this plan.
- Switch language (VI/EN) in the app — confirm "Chọn agent..." and the
  modal's other strings update correctly.

- [ ] **Step 2: Report results**

No commit for this task. Note anything that didn't work as described
above.
