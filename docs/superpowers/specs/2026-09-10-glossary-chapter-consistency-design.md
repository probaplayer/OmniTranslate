# Glossary & Chapter Consistency — Design

## Bối cảnh

This replaces an earlier draft of this spec (originally titled "Evaluate &
Fix Chapters", built on top of the existing Chroma-backed `RAGStore`).
During brainstorming, the actual purpose of "RAG" in this app turned out to
be narrower and simpler than semantic chapter search: the user wants a way
to remember **terminology and relationship decisions** already made (a
character's name, a title, how two characters address each other) so that
later chapters translate them the same way, and so a chapter that gets a
term "wrong" relative to what's already established can be corrected — in
either direction: fix the new chapter to match the old, established
translation, or, when the new chapter's usage is judged more correct, fix
the old chapters instead.

This does **not** require semantic embedding search over full chapter
text. A glossary entry is short (a term, its translation, a short note) —
short enough that finding which entries are relevant to an upcoming
chapter is reliably done by scanning for the term's literal occurrence in
the source text, not by comparing vector embeddings. This sidesteps two
real problems the embedding-based design had: an embedding model
truncating a multi-thousand-character chapter to its first ~128–256
tokens (so "semantic similarity" was only ever comparing chapter
*openings*), and the `chromadb`/`sentence-transformers` dependency weight
that came with it. Both are moot once nothing this feature does needs an
embedding at all.

This spec **replaces** `RAGStore`, `RAGExample`, `RAGQuery`, `SaveToRAG`,
and the `translation_core/rag/` package entirely — none of it survives.
The earlier "Embedding Provider" spec (LM Studio / local embedding
backend selection) is dropped in full; see this project's
`2026-09-10-path-picker-design.md` for the one piece of that earlier
design that still stands on its own (the general-purpose folder picker),
independent of everything below.

## Mục tiêu

1. A per-workspace **glossary** (`glossary.json`): a flat list of
   `{term, translation, note, chapter_id}` entries — the established
   translation for a term/relationship, and which chapter last
   confirmed it.
2. A per-workspace **chapter manifest** (`chapters.json`): a record of
   every chapter ever translated — `{chapter_id, source_path, output_path, saved_at}`
   — pointing at the real files on disk, not a copy of their content.
3. `Translate` looks up glossary entries relevant to the chapter it's
   about to translate and includes them in its prompt, replacing the
   existing "past chapters as few-shot examples" mechanism entirely.
4. After translating a chapter, an AI step reads the glossary, notices new
   or conflicting terms, decides (autonomously, but always with a clear,
   readable explanation) which version is correct, updates the glossary
   accordingly, and corrects the *current* chapter's translation if the
   established version wins.
5. A separate, on-demand tool re-reviews the last N chapters (N a
   per-run setting) for translation quality in general — not just
   terminology — and fixes any it judges flawed, in place (both the
   output file and the manifest). It does **not** touch `agent.md`; any
   general style/instruction change a user decides to make stays a manual
   edit via the existing `LoadAgentFile`/`SaveAgentFile` nodes, exactly as
   today (an earlier draft of this idea also proposed the tool suggesting
   `agent.md` revisions — dropped: the line between "a term inconsistency"
   and "a style problem" is blurry enough that an AI self-critiquing its
   own system prompt produces weak, generic suggestions more often than
   useful ones; a human reading the tool's report and deciding whether to
   touch `agent.md` is more reliable).

## Kiến trúc tổng quan

```
translation_core/
  rag/                      (Delete: the whole package — store.py,
                             RAGStore, RAGExample, the chromadb/
                             sentence-transformers dependency)
  glossary.py               (Create: GlossaryEntry, load_glossary,
                             save_glossary, find_relevant_entries)
  chapters.py                (Create: ChapterRecord, load_chapters,
                              save_chapters, record_chapter, get_recent)
  translate.py                (Modify: translate_chunk takes
                               glossary_entries instead of rag_examples,
                               and drops the few-shot truncation logic —
                               entries are short enough to never need it)
  __init__.py                  (Modify: export the new names, drop
                                RAGStore/RAGExample)
server/
  workspace.py                 (Modify: create_workspace also seeds
                                empty glossary.json/chapters.json)
  nodes/
    translate.py                (Modify: RAGQuery → LookupGlossary,
                                 SaveToRAG → RecordChapter (drops
                                 source_text/translated_text, gains
                                 source_path); Translate's rag_examples
                                 input → glossary_entries; EvaluateAndFixChapters
                                 rewritten against chapters.json/glossary.py
                                 instead of RAGStore, single STRING output.
                                 New: LoadGlossary, SaveGlossary,
                                 ExtractGlossary)
tests/
  test_rag_store.py             (Delete)
  test_glossary.py               (Create)
  test_chapters.py                (Create)
  test_translate_nodes.py          (Modify: rewrite the RAGQuery/SaveToRAG
                                    tests for the new nodes)
  test_translate.py                 (Modify: translate_chunk's
                                     rag_examples-based tests rewritten
                                     for glossary_entries)
workspaces/
  vi-du-lm-studio/graph.json         (Modify: the shipped example wires
                                      RAGQuery.rag_examples →
                                      Translate.rag_examples — both node
                                      type and field name are gone, so
                                      this graph must be updated to use
                                      LoadGlossary → LookupGlossary →
                                      Translate.glossary_entries or it
                                      will fail validate_required_inputs
                                      the next time someone runs it)
```

### Data shapes

```python
@dataclass
class GlossaryEntry:
    term: str
    translation: str
    note: str
    chapter_id: str          # the chapter that most recently confirmed this entry
```

`glossary.json`:
```json
{"entries": [
  {"term": "龙王", "translation": "Long Vương", "note": "vua rồng, cai quản biển đông", "chapter_id": "ch3"}
]}
```

```python
@dataclass
class ChapterRecord:
    chapter_id: str
    source_path: str
    output_path: str
    saved_at: float          # time.time() at the moment RecordChapter ran
```

`chapters.json`:
```json
{"chapters": [
  {"chapter_id": "ch3", "source_path": "D:/.../chapters/ch3.txt", "output_path": "D:/.../output/ch3-vi.txt", "saved_at": 1757500000.0}
]}
```

Both files are seeded empty (`{"entries": []}` / `{"chapters": []}`) by
`create_workspace`, the same way `graph.json`/`agent.md` already are — but
`load_glossary`/`load_chapters` also tolerate a **missing** file by
returning `[]` rather than raising, so a workspace created before this
ships (and therefore missing both files) self-heals on first read instead
of needing manual repair. (This is a deliberate exception to
`load_agent_file`'s "raise `FileNotFoundError` on missing" precedent — an
empty glossary/chapter-history is a normal, common starting state, unlike
a missing `agent.md`, which always exists by construction and whose
absence signals something actually wrong.)

### `translation_core/glossary.py`

```python
def load_glossary(path: str | Path) -> list[GlossaryEntry]: ...
def save_glossary(path: str | Path, entries: list[GlossaryEntry]) -> None: ...

def find_relevant_entries(entries: list[GlossaryEntry], text: str) -> list[GlossaryEntry]:
    """Entries whose `term` occurs literally (substring match) in `text`."""
    return [e for e in entries if e.term in text]
```

`find_relevant_entries` is the one piece of retrieval logic in this whole
feature, and it is shared by two call sites: `LookupGlossary` (below) and
`EvaluateAndFixChapters`'s internal re-translation step — one
implementation, not duplicated.

### `translation_core/chapters.py`

```python
def load_chapters(path: str | Path) -> list[ChapterRecord]: ...
def save_chapters(path: str | Path, records: list[ChapterRecord]) -> None: ...

def record_chapter(path: str | Path, chapter_id: str, source_path: str, output_path: str) -> None:
    """Upsert by chapter_id (replace if present, append if new), stamping saved_at=time.time()."""
    ...

def get_recent(records: list[ChapterRecord], n: int) -> list[ChapterRecord]:
    """The n records with the largest saved_at, newest first. n <= 0 or an empty list both return []."""
    ...
```

### `translate_chunk` (rewritten)

```python
def translate_chunk(
    provider: LLMProvider,
    agent_instructions: str,
    glossary_entries: list[GlossaryEntry],
    source_text: str,
) -> str:
    system_prompt = agent_instructions
    if glossary_entries:
        entries_text = "\n".join(
            f"- {e.term} → {e.translation}" + (f" ({e.note})" if e.note else "")
            for e in glossary_entries
        )
        system_prompt += "\n\n## Thuật ngữ/quan hệ đã xác lập (giữ nhất quán):\n" + entries_text
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": source_text},
    ]
    return provider.complete(messages)
```

The old `_truncate`/`max_example_chars=800` machinery is deleted, not kept
unused: a glossary entry is a term plus a short note, never a multi-KB
blob, so there is nothing left to truncate.

### Node changes (`server/nodes/translate.py`)

**`Translate`** — `optional.rag_examples: RAG_EXAMPLES` becomes
`optional.glossary_entries: GLOSSARY_ENTRIES`; `execute` passes it through
to the rewritten `translate_chunk` unchanged in spirit
(`glossary_entries or []`, matching the existing `rag_examples or []`
pattern exactly).

**`LookupGlossary`** (replaces `RAGQuery`) — a pure function, no
`NEEDS_WORKSPACE`:
```python
@register_node("LookupGlossary")
class LookupGlossary(NodeBase):
    CATEGORY = "Translation"
    RETURN_TYPES = ("GLOSSARY_ENTRIES",)
    RETURN_NAMES = ("relevant_entries",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "glossary_entries": ("GLOSSARY_ENTRIES", {}),
            "text": ("STRING", {"default": ""}),
        }}

    def execute(self, glossary_entries, text):
        return (find_relevant_entries(glossary_entries, text),)
```
No `top_k`: substring matching returns exactly the entries that actually
occur in `text`, not a ranked top-K — there is nothing to rank.

**`LoadGlossary`** / **`SaveGlossary`** (new) — the explicit load/save
pair, matching `LoadAgentFile`/`SaveAgentFile`'s existing convention of
never hiding file I/O inside another node:
```python
@register_node("LoadGlossary")
class LoadGlossary(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("GLOSSARY_ENTRIES",)
    RETURN_NAMES = ("glossary_entries",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    def execute(self, workspace_name):
        path = workspace.get_workspace_path(workspace_name, "glossary.json")
        return (load_glossary(path),)


@register_node("SaveGlossary")
class SaveGlossary(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"glossary_entries": ("GLOSSARY_ENTRIES", {})}}

    def execute(self, workspace_name, glossary_entries):
        path = workspace.get_workspace_path(workspace_name, "glossary.json")
        save_glossary(path, glossary_entries)
        return ()
```

**`RecordChapter`** (replaces `SaveToRAG`) — drops `source_text`/
`translated_text` entirely (this feature no longer stores chapter
content anywhere), gains `source_path`:
```python
@register_node("RecordChapter")
class RecordChapter(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "chapter_id": ("STRING", {"default": ""}),
            "source_path": ("STRING", {"default": "", "widget": "path"}),
            "output_path": ("STRING", {"default": "", "widget": "path"}),
        }}

    def execute(self, workspace_name, chapter_id, source_path, output_path):
        path = workspace.get_workspace_path(workspace_name, "chapters.json")
        record_chapter(path, chapter_id, source_path, output_path)
        return ()
```
(The `widget: "path"` flag depends on the path-picker sub-project; see
that spec's own note about shipping order — the flag is inert, a plain
textarea, until that lands.)

**`ExtractGlossary`** (new) — the one genuinely AI-driven step in this
whole feature. A pure function: takes the current glossary as input
(from `LoadGlossary`), does not touch any file itself.

```python
@register_node("ExtractGlossary")
class ExtractGlossary(NodeBase):
    CATEGORY = "Translation"
    RETURN_TYPES = ("GLOSSARY_ENTRIES", "STRING", "STRING")
    RETURN_NAMES = ("updated_glossary_entries", "corrected_translated_text", "revision_note")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "provider": ("PROVIDER", {}),
            "glossary_entries": ("GLOSSARY_ENTRIES", {}),
            "source_text": ("STRING", {"default": ""}),
            "translated_text": ("STRING", {"default": ""}),
            "chapter_id": ("STRING", {"default": ""}),
        }}

    def execute(self, provider, glossary_entries, source_text, translated_text, chapter_id):
        ...
```

Algorithm:

1. One `provider.complete(...)` call: system prompt asks the model to
   read `source_text`/`translated_text` and list any term/relationship
   worth remembering, one per line, in the fixed format
   `TERM | TRANSLATION | NOTE` (`NOTE` may be empty). Parse leniently —
   a line that doesn't split into exactly three `|`-separated parts is
   skipped, not fatal (matches this project's established leniency
   precedent for a model that doesn't follow a requested format, e.g.
   `EvaluateAndFixChapters`'s `OK`/`LỖI` parsing).
2. For each parsed `(term, translation, note)`:
   - No existing entry with this `term` → add
     `GlossaryEntry(term, translation, note, chapter_id)` to a working
     copy of `glossary_entries`.
   - An existing entry has the same `translation` → no-op (already
     consistent).
   - An existing entry has a **different** `translation` — a real
     conflict: one more `provider.complete(...)` call (one per
     conflicting term, not batched — each conflict gets its own
     focused judgment), giving the model both the established entry
     (translation + note) and this chapter's usage, asking it to answer
     `GIU_CU` or `DUNG_MOI: <lý do>`. An unparseable answer defaults to
     `GIU_CU` — keeping the established term is the conservative choice;
     silently churning the glossary on a response the code couldn't even
     parse would be worse.
     - `GIU_CU`: this chapter's `translated_text` used the wrong term.
       Record `(candidate_translation, established_translation)` in a
       replacements list — a plain string substitution, not a second
       full re-translation call (the exact wrong substring and its
       correct replacement are both already known).
     - `DUNG_MOI`: update the working glossary copy's entry for this
       term to the new translation/note/chapter_id; append a line to the
       revision note naming the term, the old and new translation, and
       that chapters other than `chapter_id` may now be inconsistent —
       phrased as guidance to go run `EvaluateAndFixChapters`, not as a
       specific chapter_id list (this node has no access to
       `chapters.json` and shouldn't reach for it — see "Xử lý lỗi").
3. `corrected_translated_text` = `translated_text` with every
   `(wrong, correct)` pair from step 2 substituted in (unchanged if the
   replacements list is empty).
4. `revision_note` = a plain-text summary: new terms added, terms
   confirmed unchanged (may be omitted for brevity — a plan detail, not
   a spec requirement), and every `DUNG_MOI` override with its
   old→new wording.
5. Return `(working_glossary_copy, corrected_translated_text, revision_note)`.

Typical wiring: `Translate → ExtractGlossary.translated_text`,
`LoadGlossary → ExtractGlossary.glossary_entries`,
`ExtractGlossary.updated_glossary_entries → SaveGlossary`,
`ExtractGlossary.corrected_translated_text → SaveTextFile` (instead of
wiring `Translate`'s raw output there directly — this is what guarantees
the file actually saved reflects any glossary-driven correction),
`ExtractGlossary.revision_note → TextPreview` (or `Note`) so the user
sees it.

**`EvaluateAndFixChapters`** (rewritten against the new data model):

```python
@register_node("EvaluateAndFixChapters")
class EvaluateAndFixChapters(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("report",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": ("PROVIDER", {}),
                "agent_instructions": ("STRING", {"default": ""}),
            },
            "optional": {
                "glossary_entries": ("GLOSSARY_ENTRIES", {}),
                "chapter_count": ("STRING", {"default": "5"}),
            },
        }

    def execute(self, workspace_name, provider, agent_instructions,
                glossary_entries=None, chapter_count="5"):
        ...
```

Algorithm:

1. `records = get_recent(load_chapters(workspace.get_workspace_path(workspace_name, "chapters.json")), int(chapter_count))`.
   Empty → return `("Không có chương nào để đánh giá.",)`, no LLM calls.
2. For each record, newest → oldest:
   - Read `Path(record.source_path).read_text(encoding="utf-8")` and
     `Path(record.output_path).read_text(encoding="utf-8")`. Either file
     missing/unreadable → skip this chapter, note it in the report
     (`"{chapter_id}: bỏ qua (không đọc được file: {lý do})"`) — matches
     this project's established "one bad item doesn't abort the whole
     batch" precedent (`list_workspaces`, `browse-directory`).
   - Critique via one `provider.complete(...)` call — same `OK` /
     `LỖI: <mô tả>` fixed-format contract as before, system prompt built
     from `agent_instructions` plus, if `glossary_entries` was supplied,
     the entries relevant to this chapter
     (`find_relevant_entries(glossary_entries, source_text)`) formatted
     the same way `translate_chunk` does, so the critique is aware of
     established terms too.
   - `LỖI` → re-translate:
     `translate_chunk(provider, agent_instructions, find_relevant_entries(glossary_entries or [], source_text), source_text)`
     — the fix stays consistent with the current glossary, not just the
     chapter's own prior wording. Overwrite `record.output_path` with the
     corrected text. Append `(chapter_id, error_description)` to a
     findings list.
   - `OK` → no action.
3. `report` = how many chapters were checked, and for each fixed one, its
   `chapter_id` and the error description. No second output — no
   `agent.md` revision proposal (dropped; see "Mục tiêu" §5).

## Xử lý lỗi

- `int(chapter_count)` on a non-numeric value raises `ValueError` and
  propagates — matches the removed `RAGQuery`'s identical `int(top_k)`
  precedent.
- `ExtractGlossary` never reads `chapters.json` and therefore never names
  specific old chapters in its `revision_note` — only "chapters may need
  re-checking, run `EvaluateAndFixChapters`". This is a deliberate
  boundary, not an oversight: keeping `ExtractGlossary` a pure function
  (no workspace access at all) means it cannot itself go patch arbitrary
  files, which keeps "which node can silently rewrite old chapters" to
  exactly one place in the whole system —
  `EvaluateAndFixChapters` — for anyone auditing this codebase later.
- A `source_path`/`output_path` in `chapters.json` that no longer resolves
  (moved or deleted since it was recorded) is a per-chapter skip inside
  `EvaluateAndFixChapters`, never a whole-node failure.
- `find_relevant_entries`'s substring match is case-sensitive and does
  exact literal matching only — a term rendered with different
  punctuation/spacing than what's stored won't be found. This is an
  accepted trade-off for the reliability substring matching gives over
  embeddings for proper nouns (see "Bối cảnh"); not solved here.

## Testing

- `tests/test_glossary.py`: `find_relevant_entries` matches only entries
  whose `term` literally occurs in the given text (including a
  no-match-at-all case); `load_glossary` on a missing file returns `[]`;
  `save_glossary` then `load_glossary` round-trips a list of entries
  exactly.
- `tests/test_chapters.py`: `record_chapter` appends a new chapter_id and
  updates (not duplicates) an existing one, stamping an advancing
  `saved_at`; `get_recent` returns the correct count/order (newest
  first) and truncates when fewer than `n` chapters exist; both on an
  empty/missing file return `[]`.
- `tests/test_translate.py`: `translate_chunk` with glossary entries
  builds the "Thuật ngữ/quan hệ đã xác lập" block correctly; with none,
  omits it entirely (matches the removed `rag_examples`-empty behavior).
- `tests/test_translate_nodes.py`: rewrite the `RAGQuery`/`SaveToRAG`
  tests for `LookupGlossary`/`RecordChapter`/`LoadGlossary`/`SaveGlossary`;
  add `ExtractGlossary` tests using a `_ScriptedProvider` test double
  (same shape as the file's existing `_RecordingProvider`, returning
  canned responses in call order) covering: a brand-new term (added, no
  conflict call made), a matching-translation re-occurrence (no-op, no
  conflict call made), a conflicting term resolved `GIU_CU` (glossary
  entry unchanged, `corrected_translated_text` differs from the input),
  a conflicting term resolved `DUNG_MOI` (glossary entry updated,
  `revision_note` names the change); add `EvaluateAndFixChapters` tests
  for the all-OK path, the one-flawed-chapter path (file overwritten,
  report names it), the empty-manifest path (no LLM calls), and a
  missing-source-file path (chapter skipped, noted in `report`, other
  chapters still processed).

## Phụ thuộc & thứ tự triển khai

Independent of the path-picker and agent-template-library sub-projects at
the file level (only `RecordChapter`'s two `widget: "path"` flags read
that mechanism, and the flag is inert until it ships — see that spec).
No forced ordering between this spec and the other two.

## Ngoài phạm vi

- Semantic/embedding-based glossary lookup — substring matching is the
  chosen, final mechanism (see "Bối cảnh"), not a stopgap.
- Automatic `agent.md` revision from `EvaluateAndFixChapters` — dropped
  (see "Mục tiêu" §5).
- `ExtractGlossary` locating and patching specific old chapters itself —
  that is `EvaluateAndFixChapters`'s job, run separately by the user when
  a `revision_note` suggests it's warranted (see "Xử lý lỗi").
- Any conflict-resolution UI requiring human confirmation before a
  glossary override or an old-chapter fix — the user's explicit choice
  during brainstorming was "AI tự quyết định, báo cáo rõ", not a
  confirm-before-acting flow.
