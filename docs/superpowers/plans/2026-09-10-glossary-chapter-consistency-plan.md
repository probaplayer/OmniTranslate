# Glossary & Chapter Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Chroma-backed RAG subsystem (`RAGStore`, `RAGExample`,
`RAGQuery`, `SaveToRAG`) with a flat-JSON glossary (`glossary.json`, term
consistency via substring matching) and a chapter manifest
(`chapters.json`, chapter_id → source/output file paths), plus new nodes
that keep glossary terms consistent across chapters and re-review recent
translations for quality.

**Architecture:** Two new, dependency-free `translation_core` modules
(`glossary.py`, `chapters.py`) replace the whole `translation_core/rag/`
package. `Translate` reads glossary context instead of past-chapter
few-shot examples. Five nodes cover the workflow: `LoadGlossary`/
`SaveGlossary` (explicit file I/O, matching `LoadAgentFile`/`SaveAgentFile`'s
convention), `LookupGlossary` (pure substring-match, replaces `RAGQuery`),
`RecordChapter` (replaces `SaveToRAG`, now records file paths instead of
content), `ExtractGlossary` (new — the one AI-driven step, detects and
resolves term conflicts), and `EvaluateAndFixChapters` (new — reviews
recent chapters for general quality, independent of glossary conflicts).

**Tech Stack:** Plain `json`/`pathlib` (no new dependency); removes
`chromadb` and `sentence-transformers` from `requirements.txt` entirely.

**Spec:** `docs/superpowers/specs/2026-09-10-glossary-chapter-consistency-design.md`

## Global Constraints

- No embedding/vector search anywhere in this feature — `find_relevant_entries`
  is a literal substring match (`entry.term in text`), by design, not a
  stopgap.
- `glossary.json`/`chapters.json` are seeded empty (`{"entries": []}` /
  `{"chapters": []}`) by `create_workspace`, but `load_glossary`/
  `load_chapters` also tolerate a missing file by returning `[]` (unlike
  `load_agent_file`, which raises `FileNotFoundError` on missing) — an
  empty glossary/chapter-history is a normal starting state, not an error
  condition.
- `ExtractGlossary` never touches `chapters.json` or any file at all — it
  is a pure function (no `NEEDS_WORKSPACE`). It is the only node in this
  feature permitted to be a "smart" AI step; every other node either does
  plain file I/O or plain substring matching, never both, and never LLM
  calls mixed with file I/O in the same node (`EvaluateAndFixChapters` is
  the one exception, matching how `Translate` already mixes an LLM call
  with no file I/O — see spec's "Xử lý lỗi" for the reasoning).
- `EvaluateAndFixChapters` never proposes an `agent.md` revision — it has
  exactly one output, `report` (STRING). `agent.md` stays a manual edit
  via the existing `LoadAgentFile`/`SaveAgentFile` nodes.
- A conflict `ExtractGlossary` cannot parse defaults to keeping the
  established glossary entry (`GIU_CU`), never to silently accepting the
  new one — an unparseable model response must never churn the glossary.
- A per-chapter failure inside a batch operation (a missing file in
  `EvaluateAndFixChapters`, a permission error browsing a directory
  elsewhere in this app) is a skip-and-note, never a whole-request
  failure — matches this project's established `list_workspaces`/
  `browse-directory` precedent.

---

### Task 1: `translation_core/glossary.py`

**Files:**
- Create: `translation_core/glossary.py`
- Test: `tests/test_glossary.py`

**Interfaces:**
- Produces: `GlossaryEntry(term, translation, note, chapter_id)` dataclass;
  `load_glossary(path) -> list[GlossaryEntry]`;
  `save_glossary(path, entries: list[GlossaryEntry]) -> None`;
  `find_relevant_entries(entries: list[GlossaryEntry], text: str) -> list[GlossaryEntry]`.
  Every later task that touches glossary data uses these exact names.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_glossary.py`:

```python
from translation_core.glossary import (
    GlossaryEntry,
    find_relevant_entries,
    load_glossary,
    save_glossary,
)


def test_load_glossary_on_missing_file_returns_empty_list(tmp_path):
    assert load_glossary(tmp_path / "glossary.json") == []


def test_save_then_load_round_trips_entries(tmp_path):
    path = tmp_path / "glossary.json"
    entries = [
        GlossaryEntry(term="龙王", translation="Long Vương", note="vua rồng", chapter_id="ch3"),
        GlossaryEntry(term="李明", translation="Lý Minh", note="", chapter_id="ch1"),
    ]

    save_glossary(path, entries)
    loaded = load_glossary(path)

    assert loaded == entries


def test_find_relevant_entries_matches_literal_substring():
    entries = [
        GlossaryEntry(term="龙王", translation="Long Vương", note="", chapter_id="ch3"),
        GlossaryEntry(term="李明", translation="Lý Minh", note="", chapter_id="ch1"),
    ]

    result = find_relevant_entries(entries, "龙王今天很生气，李明害怕地跑开了。")

    assert result == entries


def test_find_relevant_entries_excludes_non_matching_terms():
    entries = [GlossaryEntry(term="龙王", translation="Long Vương", note="", chapter_id="ch3")]

    result = find_relevant_entries(entries, "今天天气很好。")

    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_glossary.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'translation_core.glossary'`.

- [ ] **Step 3: Write the implementation**

Create `translation_core/glossary.py`:

```python
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class GlossaryEntry:
    term: str
    translation: str
    note: str
    chapter_id: str


def load_glossary(path: str | Path) -> list[GlossaryEntry]:
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [GlossaryEntry(**entry) for entry in data.get("entries", [])]


def save_glossary(path: str | Path, entries: list[GlossaryEntry]) -> None:
    path = Path(path)
    path.write_text(
        json.dumps({"entries": [asdict(e) for e in entries]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def find_relevant_entries(entries: list[GlossaryEntry], text: str) -> list[GlossaryEntry]:
    return [e for e in entries if e.term in text]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_glossary.py -v`
Expected: all 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add translation_core/glossary.py tests/test_glossary.py
git commit -m "feat: add glossary.py — flat-file term store with substring lookup"
```

---

### Task 2: `translation_core/chapters.py`

**Files:**
- Create: `translation_core/chapters.py`
- Test: `tests/test_chapters.py`

**Interfaces:**
- Produces: `ChapterRecord(chapter_id, source_path, output_path, saved_at)`
  dataclass; `load_chapters(path) -> list[ChapterRecord]`;
  `save_chapters(path, records: list[ChapterRecord]) -> None`;
  `record_chapter(path, chapter_id, source_path, output_path) -> None`
  (upserts by `chapter_id`, stamps `saved_at=time.time()`);
  `get_recent(records: list[ChapterRecord], n: int) -> list[ChapterRecord]`
  (newest first, `n <= 0` or an empty list both return `[]`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_chapters.py`:

```python
import time

from translation_core.chapters import (
    ChapterRecord,
    get_recent,
    load_chapters,
    record_chapter,
    save_chapters,
)


def test_load_chapters_on_missing_file_returns_empty_list(tmp_path):
    assert load_chapters(tmp_path / "chapters.json") == []


def test_record_chapter_appends_new_chapter(tmp_path):
    path = tmp_path / "chapters.json"

    record_chapter(path, "ch1", "src/ch1.txt", "out/ch1-vi.txt")

    records = load_chapters(path)
    assert len(records) == 1
    assert records[0].chapter_id == "ch1"
    assert records[0].source_path == "src/ch1.txt"
    assert records[0].output_path == "out/ch1-vi.txt"


def test_record_chapter_updates_existing_chapter_instead_of_duplicating(tmp_path):
    path = tmp_path / "chapters.json"

    record_chapter(path, "ch1", "src/ch1.txt", "out/ch1-vi.txt")
    record_chapter(path, "ch1", "src/ch1.txt", "out/ch1-vi-fixed.txt")

    records = load_chapters(path)
    assert len(records) == 1
    assert records[0].output_path == "out/ch1-vi-fixed.txt"


def test_record_chapter_stamps_an_advancing_saved_at(tmp_path):
    path = tmp_path / "chapters.json"

    record_chapter(path, "ch1", "src/ch1.txt", "out/ch1.txt")
    first_saved_at = load_chapters(path)[0].saved_at
    time.sleep(0.01)
    record_chapter(path, "ch2", "src/ch2.txt", "out/ch2.txt")

    ch2 = next(r for r in load_chapters(path) if r.chapter_id == "ch2")
    assert ch2.saved_at > first_saved_at


def test_get_recent_returns_newest_first():
    records = [
        ChapterRecord(chapter_id="ch1", source_path="s1", output_path="o1", saved_at=100.0),
        ChapterRecord(chapter_id="ch2", source_path="s2", output_path="o2", saved_at=300.0),
        ChapterRecord(chapter_id="ch3", source_path="s3", output_path="o3", saved_at=200.0),
    ]

    result = get_recent(records, 2)

    assert [r.chapter_id for r in result] == ["ch2", "ch3"]


def test_get_recent_truncates_when_fewer_than_n_exist():
    records = [ChapterRecord(chapter_id="ch1", source_path="s1", output_path="o1", saved_at=1.0)]

    assert len(get_recent(records, 5)) == 1


def test_get_recent_on_empty_list_returns_empty():
    assert get_recent([], 5) == []


def test_get_recent_non_positive_n_returns_empty():
    records = [ChapterRecord(chapter_id="ch1", source_path="s1", output_path="o1", saved_at=1.0)]

    assert get_recent(records, 0) == []
    assert get_recent(records, -1) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_chapters.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'translation_core.chapters'`.

- [ ] **Step 3: Write the implementation**

Create `translation_core/chapters.py`:

```python
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ChapterRecord:
    chapter_id: str
    source_path: str
    output_path: str
    saved_at: float


def load_chapters(path: str | Path) -> list[ChapterRecord]:
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ChapterRecord(**record) for record in data.get("chapters", [])]


def save_chapters(path: str | Path, records: list[ChapterRecord]) -> None:
    path = Path(path)
    path.write_text(
        json.dumps({"chapters": [asdict(r) for r in records]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def record_chapter(path: str | Path, chapter_id: str, source_path: str, output_path: str) -> None:
    records = [r for r in load_chapters(path) if r.chapter_id != chapter_id]
    records.append(
        ChapterRecord(
            chapter_id=chapter_id,
            source_path=source_path,
            output_path=output_path,
            saved_at=time.time(),
        )
    )
    save_chapters(path, records)


def get_recent(records: list[ChapterRecord], n: int) -> list[ChapterRecord]:
    if n <= 0:
        return []
    return sorted(records, key=lambda r: r.saved_at, reverse=True)[:n]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_chapters.py -v`
Expected: all 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add translation_core/chapters.py tests/test_chapters.py
git commit -m "feat: add chapters.py — per-chapter file-path manifest"
```

---

### Task 3: Rewrite `translate_chunk` and the `Translate` node for glossary entries

**Files:**
- Modify: `translation_core/translate.py`
- Modify: `server/nodes/translate.py:108-129` (the `Translate` class only)
- Modify: `tests/test_translate.py` (full rewrite)
- Modify: `tests/test_translate_nodes.py` (the one `Translate`-node test)
- Modify: `tests/test_api.py` (delete the one RAG-based websocket test —
  see Step 6 below; a replacement is added in Task 4 once
  `LookupGlossary`/`LoadGlossary` exist)

**Interfaces:**
- Consumes: `GlossaryEntry` (Task 1).
- Produces: `translate_chunk(provider, agent_instructions, glossary_entries: list[GlossaryEntry], source_text) -> str`
  — the `rag_examples`/`max_example_chars` parameters and all truncation
  logic are gone entirely, not deprecated-but-kept. `Translate`'s
  `optional.rag_examples: RAG_EXAMPLES` input becomes
  `optional.glossary_entries: GLOSSARY_ENTRIES`.

This task deliberately does **not** touch `RAGQuery`/`SaveToRAG` yet —
they still import/use `RAGStore` unchanged, and their own tests are
unaffected by this task. Only `Translate` and `translate_chunk` change
here.

- [ ] **Step 1: Rewrite `tests/test_translate.py`**

Replace the entire file:

```python
import pytest

from translation_core.glossary import GlossaryEntry
from translation_core.providers.base import LLMProvider
from translation_core.translate import translate_chunk


class RecordingProvider(LLMProvider):
    def __init__(self):
        self.received_messages = None

    def complete(self, messages, **kwargs):
        self.received_messages = messages
        return "bản dịch giả"


def test_translate_chunk_builds_system_prompt_with_glossary_entries():
    provider = RecordingProvider()
    entries = [
        GlossaryEntry(term="Long Khê", translation="Long Khê", note="hiệp sĩ rồng", chapter_id="ch1"),
    ]

    result = translate_chunk(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt, văn phong trang trọng.",
        glossary_entries=entries,
        source_text="Long Khê drew his sword.",
    )

    assert result == "bản dịch giả"
    system_prompt = provider.received_messages[0]["content"]
    assert provider.received_messages[0]["role"] == "system"
    assert "Dịch sang tiếng Việt" in system_prompt
    assert "Long Khê → Long Khê (hiệp sĩ rồng)" in system_prompt
    assert provider.received_messages[1] == {"role": "user", "content": "Long Khê drew his sword."}


def test_translate_chunk_without_glossary_entries_omits_the_section():
    provider = RecordingProvider()

    translate_chunk(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt.",
        glossary_entries=[],
        source_text="Hello world.",
    )

    assert "đã xác lập" not in provider.received_messages[0]["content"]


def test_translate_chunk_omits_note_parens_when_note_is_empty():
    provider = RecordingProvider()
    entries = [GlossaryEntry(term="龙王", translation="Long Vương", note="", chapter_id="ch1")]

    translate_chunk(
        provider=provider,
        agent_instructions="Dịch.",
        glossary_entries=entries,
        source_text="src",
    )

    system_prompt = provider.received_messages[0]["content"]
    assert "龙王 → Long Vương" in system_prompt
    assert "()" not in system_prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_translate.py -v`
Expected: FAIL — `translate_chunk` still has the old `rag_examples`
signature, so calling with `glossary_entries=` raises `TypeError`.

- [ ] **Step 3: Rewrite `translation_core/translate.py`**

Replace the entire file:

```python
from translation_core.glossary import GlossaryEntry
from translation_core.providers.base import LLMProvider


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

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_translate.py -v`
Expected: all 3 PASS.

- [ ] **Step 5: Update the `Translate` node**

In `server/nodes/translate.py`, the `Translate` class's `INPUT_TYPES`
currently has:

```python
            "optional": {"rag_examples": ("RAG_EXAMPLES", {})},
```

Change to:

```python
            "optional": {"glossary_entries": ("GLOSSARY_ENTRIES", {})},
```

And `execute` currently is:

```python
    def execute(
        self, provider, agent_instructions: str, source_text: str, rag_examples=None
    ) -> tuple:
        result = translate_chunk(provider, agent_instructions, rag_examples or [], source_text)
        return (result,)
```

Change to:

```python
    def execute(
        self, provider, agent_instructions: str, source_text: str, glossary_entries=None
    ) -> tuple:
        result = translate_chunk(provider, agent_instructions, glossary_entries or [], source_text)
        return (result,)
```

- [ ] **Step 6: Update `tests/test_translate_nodes.py`'s `Translate`-node test**

The existing test imports `RAGExample` at the top of the file and uses it
in `test_translate_node_calls_translate_chunk_with_composed_inputs`:

```python
from translation_core import LLMProvider, RAGExample
```

Change to:

```python
from translation_core import GlossaryEntry, LLMProvider
```

(`RAGExample` stays needed nowhere else in this file at this point — the
`RAGQuery`/`SaveToRAG` tests further down still exist untouched until
Task 4, and they do not import `RAGExample` themselves, only construct
`RAGStore` indirectly through the node.)

The test itself currently is:

```python
def test_translate_node_calls_translate_chunk_with_composed_inputs():
    node = get_node_class("Translate")()
    provider = _RecordingProvider()
    rag_examples = [
        RAGExample(
            chapter_id="ch1",
            source_text="A knight traveled to the village.",
            translated_text="Một hiệp sĩ đã đến ngôi làng.",
            distance=0.1,
        )
    ]

    result = node.execute(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt.",
        source_text="The knight drew his sword.",
        rag_examples=rag_examples,
    )

    assert result == ("bản dịch giả",)
```

Change to:

```python
def test_translate_node_calls_translate_chunk_with_composed_inputs():
    node = get_node_class("Translate")()
    provider = _RecordingProvider()
    glossary_entries = [
        GlossaryEntry(term="hiệp sĩ", translation="hiệp sĩ", note="", chapter_id="ch1"),
    ]

    result = node.execute(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt.",
        source_text="The knight drew his sword.",
        glossary_entries=glossary_entries,
    )

    assert result == ("bản dịch giả",)
```

- [ ] **Step 7: Delete the now-broken RAG websocket test from `tests/test_api.py`**

Delete `test_websocket_run_with_rag_nodes_streams_serializable_events` in
full (its graph wires `RAGQuery.rag_examples → Translate.rag_examples`,
and `Translate` no longer has a `rag_examples` input at all after Step 5
— this is not fixable in this task since its replacement needs
`LookupGlossary`/`LoadGlossary`, which don't exist until Task 4). A
replacement, `test_websocket_run_with_glossary_nodes_streams_serializable_events`,
is added in Task 4, Step 6 — this is a deliberate, temporary test
relocation across two tasks in the same plan, not a dropped test.

- [ ] **Step 8: Run the tests this task actually changed**

Run: `pytest tests/test_translate.py tests/test_translate_nodes.py -v`
Expected: all PASS. (`tests/test_api.py`'s full suite is expected to
still have the RAG-nodes test's coverage gap until Task 4 — do not run
`pytest -q` yet expecting a fully green suite; the other `test_api.py`
tests are unaffected and still pass individually if you want to spot-check.)

- [ ] **Step 9: Commit**

```bash
git add translation_core/translate.py server/nodes/translate.py tests/test_translate.py tests/test_translate_nodes.py tests/test_api.py
git commit -m "feat: rewrite translate_chunk and Translate to use glossary entries instead of RAG examples"
```

---

### Task 4: `LoadGlossary`, `SaveGlossary`, `LookupGlossary` (replaces `RAGQuery`), `RecordChapter` (replaces `SaveToRAG`)

**Files:**
- Modify: `server/nodes/translate.py` (replace the `RAGQuery`/`SaveToRAG`
  classes; add `LoadGlossary`/`SaveGlossary`; update the top import line)
- Modify: `tests/test_translate_nodes.py` (replace
  `test_save_to_rag_and_query_returns_saved_chapter` with tests for the
  four new/renamed nodes)
- Modify: `tests/test_api.py` (re-add the glossary-nodes websocket test,
  fix the missing-workspace test)

**Interfaces:**
- Consumes: `load_glossary`/`save_glossary`/`find_relevant_entries`/
  `GlossaryEntry` (Task 1), `record_chapter` (Task 2).
- Produces: `LoadGlossary.execute(workspace_name) -> (list[GlossaryEntry],)`;
  `SaveGlossary.execute(workspace_name, glossary_entries) -> ()`;
  `LookupGlossary.execute(glossary_entries, text) -> (list[GlossaryEntry],)`
  (no `NEEDS_WORKSPACE` — a pure function, unlike the `RAGQuery` it
  replaces); `RecordChapter.execute(workspace_name, chapter_id, source_path, output_path) -> ()`.

- [ ] **Step 1: Update the top import line in `server/nodes/translate.py`**

Currently:

```python
from translation_core import ProviderConfig, RAGStore, create_provider, load_agent_file, save_agent_file, translate_chunk
```

Change to:

```python
from translation_core import (
    GlossaryEntry,
    ProviderConfig,
    create_provider,
    find_relevant_entries,
    load_agent_file,
    load_glossary,
    record_chapter,
    save_agent_file,
    save_glossary,
    translate_chunk,
)
```

(`RAGStore` is dropped here — nothing in this file needs it after this
task. `GlossaryEntry` is imported for type clarity even though this
task's nodes don't directly construct one — Task 5's `ExtractGlossary`,
added to this same file next, does.)

- [ ] **Step 2: Replace `RAGQuery` and `SaveToRAG`**

Delete the current `RAGQuery` class:

```python
@register_node("RAGQuery")
class RAGQuery(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("RAG_EXAMPLES",)
    RETURN_NAMES = ("rag_examples",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"text": ("STRING", {"default": ""})},
            "optional": {"top_k": ("STRING", {"default": "3"})},
        }

    def execute(self, workspace_name: str, text: str, top_k: str = "3") -> tuple:
        store = RAGStore(workspace.get_workspace_path(workspace_name, "rag_index"))
        examples = store.query(text, top_k=int(top_k))
        return (examples,)
```

and the current `SaveToRAG` class:

```python
@register_node("SaveToRAG")
class SaveToRAG(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "chapter_id": ("STRING", {"default": ""}),
                "source_text": ("STRING", {"default": ""}),
                "translated_text": ("STRING", {"default": ""}),
            }
        }

    def execute(
        self, workspace_name: str, chapter_id: str, source_text: str, translated_text: str
    ) -> tuple:
        store = RAGStore(workspace.get_workspace_path(workspace_name, "rag_index"))
        store.add_chapter(chapter_id, source_text, translated_text)
        return ()
```

Replace both with:

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

    def execute(self, workspace_name: str) -> tuple:
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

    def execute(self, workspace_name: str, glossary_entries) -> tuple:
        path = workspace.get_workspace_path(workspace_name, "glossary.json")
        save_glossary(path, glossary_entries)
        return ()


@register_node("LookupGlossary")
class LookupGlossary(NodeBase):
    CATEGORY = "Translation"
    RETURN_TYPES = ("GLOSSARY_ENTRIES",)
    RETURN_NAMES = ("relevant_entries",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "glossary_entries": ("GLOSSARY_ENTRIES", {}),
                "text": ("STRING", {"default": ""}),
            }
        }

    def execute(self, glossary_entries, text: str) -> tuple:
        return (find_relevant_entries(glossary_entries, text),)


@register_node("RecordChapter")
class RecordChapter(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "chapter_id": ("STRING", {"default": ""}),
                "source_path": ("STRING", {"default": "", "widget": "path"}),
                "output_path": ("STRING", {"default": "", "widget": "path"}),
            }
        }

    def execute(self, workspace_name: str, chapter_id: str, source_path: str, output_path: str) -> tuple:
        path = workspace.get_workspace_path(workspace_name, "chapters.json")
        record_chapter(path, chapter_id, source_path, output_path)
        return ()
```

`LookupGlossary` has no `NEEDS_WORKSPACE = True` — unlike every other
node in this file, it takes its glossary as a plain input rather than
reading a file itself, since it's a pure function (see Global
Constraints).

- [ ] **Step 3: Replace the RAGQuery/SaveToRAG test in `tests/test_translate_nodes.py`**

Delete `test_save_to_rag_and_query_returns_saved_chapter` in full. Add
these in its place:

```python
def test_load_glossary_node_reads_empty_by_default():
    workspace.create_workspace("novel-a")
    node = get_node_class("LoadGlossary")()

    result = node.execute(workspace_name="novel-a")

    assert result == ([],)


def test_save_and_load_glossary_round_trip_through_the_nodes():
    workspace.create_workspace("novel-a")
    entries = [GlossaryEntry(term="龙王", translation="Long Vương", note="", chapter_id="ch1")]

    save_node = get_node_class("SaveGlossary")()
    save_node.execute(workspace_name="novel-a", glossary_entries=entries)

    load_node = get_node_class("LoadGlossary")()
    result = load_node.execute(workspace_name="novel-a")

    assert result == (entries,)


def test_lookup_glossary_returns_only_matching_entries():
    entries = [
        GlossaryEntry(term="龙王", translation="Long Vương", note="", chapter_id="ch1"),
        GlossaryEntry(term="李明", translation="Lý Minh", note="", chapter_id="ch1"),
    ]
    node = get_node_class("LookupGlossary")()

    result = node.execute(glossary_entries=entries, text="龙王今天很高兴。")

    assert result == ([entries[0]],)


def test_record_chapter_writes_to_the_chapters_manifest():
    workspace.create_workspace("novel-a")
    node = get_node_class("RecordChapter")()

    result = node.execute(
        workspace_name="novel-a",
        chapter_id="ch1",
        source_path="chapters/ch1.txt",
        output_path="output/ch1-vi.txt",
    )

    assert result == ()
    records = load_chapters(workspace.get_workspace_path("novel-a", "chapters.json"))
    assert len(records) == 1
    assert records[0].chapter_id == "ch1"
    assert records[0].output_path == "output/ch1-vi.txt"
```

Add the needed imports at the top of `tests/test_translate_nodes.py`:

```python
from translation_core.chapters import load_chapters
```

(`GlossaryEntry` is already imported from Task 3, Step 6.)

- [ ] **Step 4: Run the node tests**

Run: `pytest tests/test_translate_nodes.py -v`
Expected: all PASS (the old RAGQuery/SaveToRAG tests are gone; the new
four are present and green).

- [ ] **Step 5: Fix `tests/test_api.py`'s missing-workspace test**

Currently:

```python
def test_websocket_run_against_missing_workspace_errors_and_creates_nothing():
    """A typo'd workspace name must not materialise a phantom directory.

    chromadb.PersistentClient auto-creates its parents, so a RAG node running
    against a nonexistent workspace would leave behind a
    workspaces/<name>/rag_index/ with no config.json or graph.json -- which
    then lists in the workspace picker and 422s when clicked.
    """
    client = TestClient(app)
    graph = {
        "nodes": [
            {
                "id": "1",
                "type": "RAGQuery",
                "inputs": {"text": "anything", "top_k": "3"},
            }
        ],
        "links": [],
    }

    with client.websocket_connect("/ws/run/typo-workspace") as websocket:
        websocket.send_json({"graph": graph})
        events = _drain(websocket)

    assert [e["event"] for e in events] == ["validation_error"]
    assert "does not exist" in events[0]["message"]
    assert not (workspace.WORKSPACES_ROOT / "typo-workspace").exists()
```

Change to:

```python
def test_websocket_run_against_missing_workspace_errors_and_creates_nothing():
    """A typo'd workspace name must not materialise a phantom directory.

    Any NEEDS_WORKSPACE node's file I/O (LoadGlossary here) must never run
    against a workspace name that was never validated to exist -- ws_run's
    upfront existence check must reject the run before any node's execute()
    does anything.
    """
    client = TestClient(app)
    graph = {
        "nodes": [{"id": "1", "type": "LoadGlossary", "inputs": {}}],
        "links": [],
    }

    with client.websocket_connect("/ws/run/typo-workspace") as websocket:
        websocket.send_json({"graph": graph})
        events = _drain(websocket)

    assert [e["event"] for e in events] == ["validation_error"]
    assert "does not exist" in events[0]["message"]
    assert not (workspace.WORKSPACES_ROOT / "typo-workspace").exists()
```

- [ ] **Step 6: Re-add the glossary-nodes websocket serialization test**

Add this to `tests/test_api.py`, in the same place the old
`test_websocket_run_with_rag_nodes_streams_serializable_events` used to
be (deleted in Task 3, Step 7):

```python
def test_websocket_run_with_glossary_nodes_streams_serializable_events(ws_workspace):
    """Regression guard for the GLOSSARY_ENTRIES path.

    LookupGlossary returns `list[GlossaryEntry]` -- a list of dataclass
    instances, unserializable as-is -- the same shape of bug this guarded
    against for RAG_EXAMPLES before RAGQuery/SaveToRAG were replaced.
    """
    save_glossary(
        workspace.get_workspace_path(ws_workspace, "glossary.json"),
        [GlossaryEntry(term="世界", translation="thế giới", note="", chapter_id="ch0")],
    )

    client = TestClient(app)
    graph = {
        "nodes": [
            {"id": "1", "type": "LoadGlossary", "inputs": {}},
            {
                "id": "2",
                "type": "Provider",
                "inputs": {
                    "base_url": "http://127.0.0.1:1/v1",
                    "api_key": "sk-not-a-real-key",
                    "model": "test-model",
                },
            },
            {
                "id": "3",
                "type": "LookupGlossary",
                "inputs": {"text": "こんにちは世界"},
            },
            {
                "id": "4",
                "type": "Translate",
                "inputs": {
                    "agent_instructions": "Translate to Vietnamese.",
                    "source_text": "こんにちは世界",
                },
            },
        ],
        "links": [
            {
                "from_node": "1",
                "from_output": "glossary_entries",
                "to_node": "3",
                "to_input": "glossary_entries",
            },
            {
                "from_node": "2",
                "from_output": "provider",
                "to_node": "4",
                "to_input": "provider",
            },
            {
                "from_node": "3",
                "from_output": "relevant_entries",
                "to_node": "4",
                "to_input": "glossary_entries",
            },
        ],
    }

    with client.websocket_connect(f"/ws/run/{ws_workspace}") as websocket:
        websocket.send_json({"graph": graph})
        events = _drain(websocket)

    assert json.dumps(events)

    lookup_completed = next(
        e for e in events if e["event"] == "node_completed" and e["node_id"] == "3"
    )
    assert lookup_completed["outputs"] == ["<list>"]

    assert any(e["event"] == "node_error" and e["node_id"] == "4" for e in events)
    assert events[-1]["event"] == "run_finished"
```

Add the needed imports at the top of `tests/test_api.py` (alongside its
existing `from server import workspace`):

```python
from translation_core.glossary import GlossaryEntry, save_glossary
```

- [ ] **Step 7: Run the full API test file**

Run: `pytest tests/test_api.py -v`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add server/nodes/translate.py tests/test_translate_nodes.py tests/test_api.py
git commit -m "feat: replace RAGQuery/SaveToRAG with LoadGlossary/SaveGlossary/LookupGlossary/RecordChapter"
```

---

### Task 5: `ExtractGlossary`

**Files:**
- Modify: `server/nodes/translate.py` (add the `ExtractGlossary` class)
- Modify: `tests/test_translate_nodes.py` (add its tests)

**Interfaces:**
- Consumes: `GlossaryEntry` (Task 1).
- Produces: `ExtractGlossary.execute(provider, glossary_entries, source_text, translated_text, chapter_id) -> (list[GlossaryEntry], str, str)`
  — `(updated_glossary_entries, corrected_translated_text, revision_note)`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_translate_nodes.py`:

```python
class _ScriptedProvider(LLMProvider):
    """Returns canned responses in call order -- for tests that need the
    provider to answer differently across ExtractGlossary's multiple
    internal LLM calls (extraction, then zero or more conflict checks)."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def complete(self, messages, **kwargs):
        self.calls.append(messages)
        return self._responses.pop(0)


def test_extract_glossary_adds_a_brand_new_term():
    node = get_node_class("ExtractGlossary")()
    provider = _ScriptedProvider(["龙王 | Long Vương | vua rồng"])

    updated, corrected, note = node.execute(
        provider=provider,
        glossary_entries=[],
        source_text="龙王发怒了。",
        translated_text="Long Vương nổi giận.",
        chapter_id="ch1",
    )

    assert updated == [
        GlossaryEntry(term="龙王", translation="Long Vương", note="vua rồng", chapter_id="ch1")
    ]
    assert corrected == "Long Vương nổi giận."
    assert "Thuật ngữ mới" in note
    assert len(provider.calls) == 1  # no conflict -> no second call


def test_extract_glossary_no_op_when_translation_already_matches():
    existing = [GlossaryEntry(term="龙王", translation="Long Vương", note="vua rồng", chapter_id="ch1")]
    node = get_node_class("ExtractGlossary")()
    provider = _ScriptedProvider(["龙王 | Long Vương | vua rồng"])

    updated, corrected, note = node.execute(
        provider=provider,
        glossary_entries=existing,
        source_text="龙王发怒了。",
        translated_text="Long Vương nổi giận.",
        chapter_id="ch2",
    )

    assert updated == existing
    assert corrected == "Long Vương nổi giận."
    assert len(provider.calls) == 1  # matching translation -> no conflict call


def test_extract_glossary_conflict_keeps_established_term():
    existing = [GlossaryEntry(term="龙王", translation="Long Vương", note="vua rồng", chapter_id="ch1")]
    node = get_node_class("ExtractGlossary")()
    provider = _ScriptedProvider(
        ["龙王 | Vua Rồng | vua rồng", "GIU_CU"]
    )

    updated, corrected, note = node.execute(
        provider=provider,
        glossary_entries=existing,
        source_text="龙王发怒了。",
        translated_text="Vua Rồng nổi giận.",
        chapter_id="ch2",
    )

    assert updated == existing  # glossary unchanged
    assert corrected == "Long Vương nổi giận."  # chapter's own text fixed
    assert len(provider.calls) == 2


def test_extract_glossary_conflict_adopts_the_new_term():
    existing = [GlossaryEntry(term="龙王", translation="Long Vương", note="vua rồng", chapter_id="ch1")]
    node = get_node_class("ExtractGlossary")()
    provider = _ScriptedProvider(
        ["龙王 | Vua Rồng | vua rồng, tân danh xưng", "DUNG_MOI: tên mới chuẩn hơn"]
    )

    updated, corrected, note = node.execute(
        provider=provider,
        glossary_entries=existing,
        source_text="龙王发怒了。",
        translated_text="Vua Rồng nổi giận.",
        chapter_id="ch2",
    )

    assert updated == [
        GlossaryEntry(term="龙王", translation="Vua Rồng", note="vua rồng, tân danh xưng", chapter_id="ch2")
    ]
    assert corrected == "Vua Rồng nổi giận."  # this chapter's text already used the new term
    assert "đổi từ 'Long Vương' sang 'Vua Rồng'" in note


def test_extract_glossary_unparseable_conflict_response_defaults_to_keeping_established():
    existing = [GlossaryEntry(term="龙王", translation="Long Vương", note="vua rồng", chapter_id="ch1")]
    node = get_node_class("ExtractGlossary")()
    provider = _ScriptedProvider(["龙王 | Vua Rồng | vua rồng", "không rõ ràng"])

    updated, corrected, note = node.execute(
        provider=provider,
        glossary_entries=existing,
        source_text="龙王发怒了。",
        translated_text="Vua Rồng nổi giận.",
        chapter_id="ch2",
    )

    assert updated == existing
    assert corrected == "Long Vương nổi giận."
```

Add `from translation_core import LLMProvider` if not already imported
at the top of the file (it already is, per Task 3, Step 6's edit to this
file's import line).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_translate_nodes.py -k extract_glossary -v`
Expected: FAIL — `get_node_class("ExtractGlossary")` raises `KeyError`.

- [ ] **Step 3: Add the `ExtractGlossary` node**

Add to `server/nodes/translate.py`:

```python
_CONFLICT_KEEP_OLD = "GIU_CU"
_CONFLICT_USE_NEW = "DUNG_MOI"


@register_node("ExtractGlossary")
class ExtractGlossary(NodeBase):
    CATEGORY = "Translation"
    RETURN_TYPES = ("GLOSSARY_ENTRIES", "STRING", "STRING")
    RETURN_NAMES = ("updated_glossary_entries", "corrected_translated_text", "revision_note")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": ("PROVIDER", {}),
                "glossary_entries": ("GLOSSARY_ENTRIES", {}),
                "source_text": ("STRING", {"default": ""}),
                "translated_text": ("STRING", {"default": ""}),
                "chapter_id": ("STRING", {"default": ""}),
            }
        }

    def execute(self, provider, glossary_entries, source_text, translated_text, chapter_id) -> tuple:
        candidates = self._extract_candidates(provider, source_text, translated_text)

        working = list(glossary_entries)
        by_term = {e.term: e for e in working}
        replacements = []
        added = []
        notes = []

        for term, translation, note in candidates:
            existing = by_term.get(term)
            if existing is None:
                entry = GlossaryEntry(term=term, translation=translation, note=note, chapter_id=chapter_id)
                working.append(entry)
                by_term[term] = entry
                added.append(term)
                continue
            if existing.translation == translation:
                continue

            verdict = self._resolve_conflict(provider, existing, term, translation, note)
            if verdict == _CONFLICT_USE_NEW:
                working = [e for e in working if e.term != term]
                new_entry = GlossaryEntry(term=term, translation=translation, note=note, chapter_id=chapter_id)
                working.append(new_entry)
                by_term[term] = new_entry
                notes.append(
                    f"'{term}': đổi từ '{existing.translation}' sang '{translation}' — "
                    "các chương khác dùng bản dịch cũ nên được rà soát lại bằng EvaluateAndFixChapters."
                )
            else:
                replacements.append((translation, existing.translation))

        corrected_translated_text = translated_text
        for wrong, correct in replacements:
            corrected_translated_text = corrected_translated_text.replace(wrong, correct)

        summary_lines = []
        if added:
            summary_lines.append("Thuật ngữ mới: " + ", ".join(added))
        summary_lines.extend(notes)
        if not summary_lines:
            summary_lines.append("Không có thuật ngữ mới hoặc xung đột nào.")

        return (working, corrected_translated_text, "\n".join(summary_lines))

    def _extract_candidates(self, provider, source_text, translated_text):
        messages = [
            {
                "role": "system",
                "content": (
                    "Đọc đoạn văn gốc và bản dịch dưới đây. Liệt kê các thuật ngữ/tên riêng/"
                    "quan hệ nhân vật đáng nhớ để giữ nhất quán về sau, mỗi dòng một mục theo "
                    "đúng định dạng: TERM | TRANSLATION | NOTE (NOTE có thể để trống). "
                    "Nếu không có gì đáng nhớ, trả lời một dòng trống."
                ),
            },
            {
                "role": "user",
                "content": f"Văn bản gốc:\n{source_text}\n\nBản dịch:\n{translated_text}",
            },
        ]
        response = provider.complete(messages)
        candidates = []
        for line in response.splitlines():
            parts = line.split("|")
            if len(parts) != 3:
                continue
            term, translation, note = (p.strip() for p in parts)
            if not term or not translation:
                continue
            candidates.append((term, translation, note))
        return candidates

    def _resolve_conflict(self, provider, existing, term, new_translation, new_note):
        messages = [
            {
                "role": "system",
                "content": (
                    "Có một xung đột thuật ngữ dịch thuật. Thuật ngữ đã xác lập trước đó và "
                    "cách dùng mới trong chương hiện tại khác nhau. Trả lời đúng một trong hai: "
                    f"'{_CONFLICT_KEEP_OLD}' (giữ bản đã xác lập) hoặc "
                    f"'{_CONFLICT_USE_NEW}: <lý do>' (dùng bản mới)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Thuật ngữ: {term}\n"
                    f"Đã xác lập trước đó: {existing.translation} ({existing.note})\n"
                    f"Cách dùng mới trong chương này: {new_translation} ({new_note})"
                ),
            },
        ]
        response = provider.complete(messages).strip()
        if response.upper().startswith(_CONFLICT_USE_NEW):
            return _CONFLICT_USE_NEW
        return _CONFLICT_KEEP_OLD
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_translate_nodes.py -k extract_glossary -v`
Expected: all 5 PASS.

- [ ] **Step 5: Run the full node test file**

Run: `pytest tests/test_translate_nodes.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add server/nodes/translate.py tests/test_translate_nodes.py
git commit -m "feat: add ExtractGlossary — detects and resolves term conflicts after translating"
```

---

### Task 6: `EvaluateAndFixChapters`

**Files:**
- Modify: `server/nodes/translate.py` (add `Path` import if not already
  present, add `get_recent`/`load_chapters` to the `translation_core`
  import, add the `EvaluateAndFixChapters` class)
- Modify: `tests/test_translate_nodes.py` (add its tests)

**Interfaces:**
- Consumes: `get_recent`/`load_chapters`/`ChapterRecord` (Task 2),
  `find_relevant_entries`/`GlossaryEntry` (Task 1), `translate_chunk`
  (Task 3).
- Produces: `EvaluateAndFixChapters.execute(workspace_name, provider, agent_instructions, glossary_entries=None, chapter_count="5") -> (str,)`
  — a single `report` string, no second output.

- [ ] **Step 1: Add the needed imports**

`server/nodes/translate.py` needs `from pathlib import Path` at the top
(not currently imported in this file) and `get_recent`/`load_chapters`
added to the existing `from translation_core import (...)` block from
Task 4, Step 1:

```python
from pathlib import Path

from translation_core import (
    GlossaryEntry,
    ProviderConfig,
    create_provider,
    find_relevant_entries,
    get_recent,
    load_agent_file,
    load_chapters,
    load_glossary,
    record_chapter,
    save_agent_file,
    save_glossary,
    translate_chunk,
)
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_translate_nodes.py`:

```python
from translation_core.chapters import record_chapter


def test_evaluate_and_fix_chapters_on_empty_manifest_makes_no_llm_calls():
    workspace.create_workspace("novel-a")
    node = get_node_class("EvaluateAndFixChapters")()
    provider = _ScriptedProvider([])

    result = node.execute(
        workspace_name="novel-a", provider=provider, agent_instructions="Dịch."
    )

    assert result == ("Không có chương nào để đánh giá.",)
    assert provider.calls == []


def test_evaluate_and_fix_chapters_all_ok_makes_no_file_changes(tmp_path):
    workspace.create_workspace("novel-a")
    source_path = tmp_path / "ch1.txt"
    output_path = tmp_path / "ch1-vi.txt"
    source_path.write_text("Hello.", encoding="utf-8")
    output_path.write_text("Xin chào.", encoding="utf-8")
    record_chapter(
        workspace.get_workspace_path("novel-a", "chapters.json"),
        "ch1", str(source_path), str(output_path),
    )
    node = get_node_class("EvaluateAndFixChapters")()
    provider = _ScriptedProvider(["OK"])

    result = node.execute(
        workspace_name="novel-a", provider=provider, agent_instructions="Dịch."
    )

    assert "Đã kiểm tra 1 chương" in result[0]
    assert output_path.read_text(encoding="utf-8") == "Xin chào."


def test_evaluate_and_fix_chapters_fixes_a_flawed_chapter(tmp_path):
    workspace.create_workspace("novel-a")
    source_path = tmp_path / "ch1.txt"
    output_path = tmp_path / "ch1-vi.txt"
    source_path.write_text("Hello.", encoding="utf-8")
    output_path.write_text("Sai rồi.", encoding="utf-8")
    record_chapter(
        workspace.get_workspace_path("novel-a", "chapters.json"),
        "ch1", str(source_path), str(output_path),
    )
    node = get_node_class("EvaluateAndFixChapters")()
    provider = _ScriptedProvider(["LỖI: sai nghĩa hoàn toàn", "Xin chào."])

    result = node.execute(
        workspace_name="novel-a", provider=provider, agent_instructions="Dịch."
    )

    assert "ch1" in result[0]
    assert "sai nghĩa hoàn toàn" in result[0]
    assert output_path.read_text(encoding="utf-8") == "Xin chào."


def test_evaluate_and_fix_chapters_skips_a_chapter_with_a_missing_file(tmp_path):
    workspace.create_workspace("novel-a")
    missing_source = tmp_path / "does-not-exist.txt"
    output_path = tmp_path / "ch1-vi.txt"
    output_path.write_text("Xin chào.", encoding="utf-8")
    record_chapter(
        workspace.get_workspace_path("novel-a", "chapters.json"),
        "ch1", str(missing_source), str(output_path),
    )
    node = get_node_class("EvaluateAndFixChapters")()
    provider = _ScriptedProvider([])

    result = node.execute(
        workspace_name="novel-a", provider=provider, agent_instructions="Dịch."
    )

    assert "ch1" in result[0]
    assert "bỏ qua" in result[0]
    assert provider.calls == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_translate_nodes.py -k evaluate_and_fix -v`
Expected: FAIL — `get_node_class("EvaluateAndFixChapters")` raises `KeyError`.

- [ ] **Step 4: Add the `EvaluateAndFixChapters` node**

Add to `server/nodes/translate.py`:

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

    def execute(
        self, workspace_name, provider, agent_instructions, glossary_entries=None, chapter_count="5"
    ) -> tuple:
        chapters_path = workspace.get_workspace_path(workspace_name, "chapters.json")
        records = get_recent(load_chapters(chapters_path), int(chapter_count))

        if not records:
            return ("Không có chương nào để đánh giá.",)

        glossary_entries = glossary_entries or []
        fixed = []
        skipped = []

        for record in records:
            try:
                source_text = Path(record.source_path).read_text(encoding="utf-8")
                translated_text = Path(record.output_path).read_text(encoding="utf-8")
            except OSError as exc:
                skipped.append(f"{record.chapter_id}: bỏ qua (không đọc được file: {exc})")
                continue

            relevant = find_relevant_entries(glossary_entries, source_text)
            verdict, description = self._critique(
                provider, agent_instructions, relevant, source_text, translated_text
            )

            if verdict == "LỖI":
                corrected = translate_chunk(provider, agent_instructions, relevant, source_text)
                Path(record.output_path).write_text(corrected, encoding="utf-8")
                fixed.append(f"{record.chapter_id}: {description}")

        lines = [f"Đã kiểm tra {len(records)} chương."]
        lines.extend(f"Sửa {entry}" for entry in fixed)
        lines.extend(skipped)
        return ("\n".join(lines),)

    def _critique(self, provider, agent_instructions, relevant_entries, source_text, translated_text):
        system_prompt = agent_instructions
        if relevant_entries:
            entries_text = "\n".join(
                f"- {e.term} → {e.translation}" + (f" ({e.note})" if e.note else "")
                for e in relevant_entries
            )
            system_prompt += "\n\n## Thuật ngữ/quan hệ đã xác lập (giữ nhất quán):\n" + entries_text
        system_prompt += (
            "\n\nSo sánh bản gốc và bản dịch dưới đây. Nếu bản dịch đúng, trả lời đúng "
            "một dòng 'OK'. Nếu có lỗi, trả lời 'LỖI: <mô tả ngắn>'."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Bản gốc:\n{source_text}\n\nBản dịch:\n{translated_text}"},
        ]
        response = provider.complete(messages).strip()
        if response.upper().startswith("LỖI"):
            description = response.split(":", 1)[1].strip() if ":" in response else response
            return ("LỖI", description)
        return ("OK", "")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_translate_nodes.py -k evaluate_and_fix -v`
Expected: all 4 PASS.

- [ ] **Step 6: Run the full node test file**

Run: `pytest tests/test_translate_nodes.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add server/nodes/translate.py tests/test_translate_nodes.py
git commit -m "feat: add EvaluateAndFixChapters — re-review recent chapters, fix flawed ones"
```

---

### Task 7: Seed `glossary.json`/`chapters.json` on workspace creation

**Files:**
- Modify: `server/workspace.py:89-105` (`create_workspace`)
- Test: `tests/test_workspace.py`

**Interfaces:**
- No new function signatures — `create_workspace`'s own signature is
  unchanged.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_workspace.py`, right after the existing
`test_create_workspace_seeds_agent_file`:

```python
def test_create_workspace_seeds_empty_glossary_file():
    workspace.create_workspace("novel-a")

    glossary_path = workspace.get_workspace_path("novel-a", "glossary.json")

    assert glossary_path.exists()
    assert json.loads(glossary_path.read_text(encoding="utf-8")) == {"entries": []}


def test_create_workspace_seeds_empty_chapters_file():
    workspace.create_workspace("novel-a")

    chapters_path = workspace.get_workspace_path("novel-a", "chapters.json")

    assert chapters_path.exists()
    assert json.loads(chapters_path.read_text(encoding="utf-8")) == {"chapters": []}
```

(`json` is already imported at the top of `tests/test_workspace.py`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_workspace.py -k "seeds_empty" -v`
Expected: FAIL — the files don't exist yet.

- [ ] **Step 3: Update `create_workspace`**

Currently:

```python
def create_workspace(name: str, source_lang: str = "", target_lang: str = "") -> None:
    ws_dir = _workspace_dir(name)
    if ws_dir.exists():
        raise WorkspaceError(f"Workspace '{name}' already exists")
    ws_dir.mkdir(parents=True)
    (ws_dir / "chapters").mkdir()
    (ws_dir / "output").mkdir()
    (ws_dir / "config.json").write_text(
        json.dumps(
            {"name": name, "source_lang": source_lang, "target_lang": target_lang},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (ws_dir / "graph.json").write_text(json.dumps(_DEFAULT_GRAPH), encoding="utf-8")
    (ws_dir / "agent.md").write_text(_DEFAULT_AGENT_FILE, encoding="utf-8")
```

Change the last line to:

```python
    (ws_dir / "graph.json").write_text(json.dumps(_DEFAULT_GRAPH), encoding="utf-8")
    (ws_dir / "agent.md").write_text(_DEFAULT_AGENT_FILE, encoding="utf-8")
    (ws_dir / "glossary.json").write_text(json.dumps({"entries": []}), encoding="utf-8")
    (ws_dir / "chapters.json").write_text(json.dumps({"chapters": []}), encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_workspace.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add server/workspace.py tests/test_workspace.py
git commit -m "feat: seed empty glossary.json/chapters.json when a workspace is created"
```

---

### Task 8: Migrate the shipped example workflow

**Files:**
- Modify: `workspaces/vi-du-lm-studio/graph.json`

**Interfaces:**
- None — this task only edits a saved graph, no code.

- [ ] **Step 1: Confirm the file's current exact content**

Re-read `workspaces/vi-du-lm-studio/graph.json` before editing — this
plan's Task authoring already read it once, but re-confirm no other task
or a concurrent process has touched it since. Its `RAGQuery` node (id 5)
currently reads:

```json
    {
      "id": 5,
      "type": "Translation/RAGQuery",
      "pos": [240, 518],
      "size": {"0": 200, "1": 88},
      "flags": {},
      "order": 4,
      "mode": 0,
      "inputs": [
        {"name": "text", "type": "STRING", "link": 1},
        {"name": "top_k", "type": "STRING", "link": null}
      ],
      "outputs": [
        {"name": "rag_examples", "type": "RAG_EXAMPLES", "links": [5]}
      ],
      "properties": {"text": "", "top_k": "3"},
      "boxcolor": "#c98a7e"
    },
```

and the `Translate` node (id 6) has this input among its four:

```json
        {"name": "rag_examples", "type": "RAG_EXAMPLES", "link": 5},
```

and link 5 is:

```json
    [5, 5, 0, 6, 3, "RAG_EXAMPLES"],
```

- [ ] **Step 2: Replace the whole file**

`Translation/RAGQuery` is renamed to `Translation/LookupGlossary`, its
`top_k` input is removed (no longer applicable), and it gains a
`glossary_entries` input fed by a new `Translation/LoadGlossary` node
(id 8, since `last_node_id` was 7). `Translate`'s `rag_examples` input
becomes `glossary_entries`. `last_node_id` becomes 8 and `last_link_id`
becomes 7 (the new LoadGlossary→LookupGlossary link).

Replace the entire file with:

```json
{
  "last_node_id": 8,
  "last_link_id": 7,
  "nodes": [
    {
      "id": 3,
      "type": "Utility/Note",
      "pos": [380, -160],
      "size": {"0": 200, "1": 68},
      "flags": {},
      "order": 2,
      "mode": 0,
      "inputs": [{"name": "text", "type": "STRING", "link": null}],
      "properties": {
        "text": "Đổi 'model' ở node Provider thành đúng tên model bạn đã load trong LM Studio, nếu LM Studio yêu cầu tên chính xác."
      },
      "boxcolor": "#8d949e"
    },
    {
      "id": 1,
      "type": "Utility/LoadTextFile",
      "pos": [-15, 181],
      "size": {"0": 200, "1": 68},
      "flags": {},
      "order": 0,
      "mode": 0,
      "inputs": [{"name": "path", "type": "STRING", "link": null}],
      "outputs": [{"name": "text", "type": "STRING", "links": [1, 2]}],
      "properties": {
        "path": "D:/VsCode/MCPToolTranslaterNovel/workspaces/vi-du-lm-studio/chapters/chuong-1.txt"
      },
      "boxcolor": "#7ea6c9"
    },
    {
      "id": 4,
      "type": "Translation/LoadAgentFile",
      "pos": [270, 324],
      "size": {"0": 200, "1": 68},
      "flags": {},
      "order": 3,
      "mode": 0,
      "outputs": [{"name": "text", "type": "STRING", "links": [4]}],
      "properties": {},
      "boxcolor": "#d9a44c"
    },
    {
      "id": 8,
      "type": "Translation/LoadGlossary",
      "pos": [-15, 518],
      "size": {"0": 200, "1": 68},
      "flags": {},
      "order": 1,
      "mode": 0,
      "outputs": [{"name": "glossary_entries", "type": "GLOSSARY_ENTRIES", "links": [7]}],
      "properties": {},
      "boxcolor": "#c98a7e"
    },
    {
      "id": 5,
      "type": "Translation/LookupGlossary",
      "pos": [240, 518],
      "size": {"0": 200, "1": 88},
      "flags": {},
      "order": 5,
      "mode": 0,
      "inputs": [
        {"name": "glossary_entries", "type": "GLOSSARY_ENTRIES", "link": 7},
        {"name": "text", "type": "STRING", "link": 1}
      ],
      "outputs": [{"name": "relevant_entries", "type": "GLOSSARY_ENTRIES", "links": [5]}],
      "properties": {},
      "boxcolor": "#c98a7e"
    },
    {
      "id": 7,
      "type": "Utility/SaveTextFile",
      "pos": [1032, 186],
      "size": {"0": 200, "1": 88},
      "flags": {},
      "order": 6,
      "mode": 0,
      "inputs": [
        {"name": "text", "type": "STRING", "link": 6},
        {"name": "path", "type": "STRING", "link": null}
      ],
      "properties": {
        "text": "",
        "path": "D:/VsCode/MCPToolTranslaterNovel/workspaces/vi-du-lm-studio/output/chuong-1-vi.txt"
      },
      "boxcolor": "#9b8fc4"
    },
    {
      "id": 6,
      "type": "Translation/Translate",
      "pos": [700, 200],
      "size": {"0": 287.20001220703125, "1": 128},
      "flags": {},
      "order": 6,
      "mode": 0,
      "inputs": [
        {"name": "provider", "type": "PROVIDER", "link": 3},
        {"name": "agent_instructions", "type": "STRING", "link": 4},
        {"name": "source_text", "type": "STRING", "link": 2},
        {"name": "glossary_entries", "type": "GLOSSARY_ENTRIES", "link": 5}
      ],
      "outputs": [{"name": "translated_text", "type": "STRING", "links": [6]}],
      "properties": {"provider": "", "agent_instructions": "", "source_text": "", "glossary_entries": ""},
      "boxcolor": "#7fb98a"
    },
    {
      "id": 2,
      "type": "Translation/Provider",
      "pos": [370, 30],
      "size": {"0": 200, "1": 108},
      "flags": {},
      "order": 1,
      "mode": 0,
      "inputs": [
        {"name": "base_url", "type": "STRING", "link": null},
        {"name": "api_key", "type": "STRING", "link": null},
        {"name": "model", "type": "STRING", "link": null}
      ],
      "outputs": [{"name": "provider", "type": "PROVIDER", "links": [3]}],
      "properties": {
        "base_url": "http://localhost:1234/v1",
        "api_key": "lm-studio",
        "model": "local-model"
      },
      "boxcolor": "#7fb98a"
    }
  ],
  "links": [
    [1, 1, 0, 5, 1, "STRING"],
    [2, 1, 0, 6, 2, "STRING"],
    [3, 2, 0, 6, 0, "PROVIDER"],
    [4, 4, 0, 6, 1, "STRING"],
    [5, 5, 0, 6, 3, "GLOSSARY_ENTRIES"],
    [6, 6, 0, 7, 0, "STRING"],
    [7, 8, 0, 5, 0, "GLOSSARY_ENTRIES"]
  ],
  "groups": [],
  "config": {},
  "extra": {},
  "version": 0.4
}
```

Link array entries are `[link_id, from_node, from_slot, to_node, to_slot, type]`.
Link 1 (`LoadTextFile.text → LookupGlossary.text`) now targets slot 1 of
node 5 (its second input, after the new `glossary_entries` slot 0) — this
is the one existing link whose target *slot index* shifts because of the
new input being inserted before it on the same node; every other
existing link is untouched.

- [ ] **Step 2: Manual verification**

Start the server, open this workspace in the canvas UI (`?workspace=vi-du-lm-studio`
or via "Mở workspace..."), confirm the graph loads without console errors,
all nodes render with their correct current input/output names, and no
node shows a broken/dangling link visually.

- [ ] **Step 3: Commit**

```bash
git add workspaces/vi-du-lm-studio/graph.json
git commit -m "chore: migrate the example workflow from RAGQuery/rag_examples to LookupGlossary/glossary_entries"
```

---

### Task 9: Delete the old RAG package, dependency, and tests

**Files:**
- Delete: `translation_core/rag/` (the whole package: `store.py`, `__init__.py` if present)
- Delete: `tests/test_rag_store.py`
- Modify: `translation_core/__init__.py`
- Modify: `tests/test_integration.py`
- Modify: `requirements.txt`

**Interfaces:**
- None produced — this is the final cleanup task for this plan.

- [ ] **Step 1: Confirm nothing else references the old names**

```bash
grep -rn "chromadb\|sentence-transformers\|sentence_transformers\|RAGStore\|RAGExample\|translation_core\.rag\|translation_core/rag" --include="*.py" .
```

Expected at this point: only `translation_core/rag/store.py` itself,
`translation_core/__init__.py` (still re-exporting the old names), and
`tests/test_rag_store.py`/`tests/test_integration.py` (not yet rewritten).
If anything else turns up, stop and investigate before deleting — do not
delete blindly.

- [ ] **Step 2: Delete the old package and its dedicated test file**

```bash
git rm -r translation_core/rag
git rm tests/test_rag_store.py
```

- [ ] **Step 3: Update `translation_core/__init__.py`**

Replace the entire file:

```python
"""Translation & RAG core.

Public API — consumers (e.g. server/nodes) import from here:

    from translation_core import create_provider, ProviderConfig, GlossaryEntry, ...

``OpenAICompatibleProvider`` is deliberately not re-exported: it is one
concrete backend, while ``create_provider``/``ProviderConfig`` are the
intended generic entry point for constructing a provider.
"""

from translation_core.agent_file import load_agent_file, save_agent_file
from translation_core.chapters import ChapterRecord, get_recent, load_chapters, record_chapter, save_chapters
from translation_core.glossary import GlossaryEntry, find_relevant_entries, load_glossary, save_glossary
from translation_core.providers.base import LLMProvider, ProviderError
from translation_core.providers.factory import ProviderConfig, create_provider
from translation_core.translate import translate_chunk

__all__ = [
    "ChapterRecord",
    "GlossaryEntry",
    "LLMProvider",
    "ProviderConfig",
    "ProviderError",
    "create_provider",
    "find_relevant_entries",
    "get_recent",
    "load_agent_file",
    "load_chapters",
    "load_glossary",
    "record_chapter",
    "save_agent_file",
    "save_chapters",
    "save_glossary",
    "translate_chunk",
]
```

- [ ] **Step 4: Rewrite `tests/test_integration.py`**

Replace the entire file:

```python
"""End-to-end composition tests: real glossary.py -> translate_chunk -> real provider.

Every other test file exercises one piece in isolation; these wire the real
objects together, the seam where a non-str provider response used to slip
through uncaught.
"""

import json

import httpx
import pytest

from translation_core import (
    GlossaryEntry,
    LLMProvider,
    ProviderConfig,
    ProviderError,
    create_provider,
    find_relevant_entries,
    load_agent_file,
    save_agent_file,
    translate_chunk,
)
from translation_core.providers.openai_compatible import OpenAICompatibleProvider

AGENT_INSTRUCTIONS = "Dịch sang tiếng Việt, giữ văn phong trang trọng."
SOURCE_TEXT = "Long Khê rode on through the fog toward the village gate."


def _relevant_glossary_entries():
    entries = [
        GlossaryEntry(term="Long Khê", translation="Long Khê", note="hiệp sĩ rồng", chapter_id="ch1"),
    ]
    return find_relevant_entries(entries, SOURCE_TEXT)


def test_full_composition_real_glossary_lookup_real_provider():
    glossary_entries = _relevant_glossary_entries()
    assert len(glossary_entries) == 1

    captured = {}

    def handler(request):
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Bản dịch thật"}}]})

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with provider:
        result = translate_chunk(
            provider=provider,
            agent_instructions=AGENT_INSTRUCTIONS,
            glossary_entries=glossary_entries,
            source_text=SOURCE_TEXT,
        )

    assert result == "Bản dịch thật"

    system_prompt = captured["json"]["messages"][0]["content"]
    assert captured["json"]["messages"][0]["role"] == "system"
    assert AGENT_INSTRUCTIONS in system_prompt
    assert "Long Khê → Long Khê (hiệp sĩ rồng)" in system_prompt
    assert captured["json"]["messages"][1] == {"role": "user", "content": SOURCE_TEXT}


def test_full_composition_null_content_raises_provider_error():
    """A server sending JSON `"content": null` must fail loudly, not return None."""

    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": None}}]})

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with provider, pytest.raises(ProviderError) as excinfo:
        translate_chunk(
            provider=provider,
            agent_instructions=AGENT_INSTRUCTIONS,
            glossary_entries=_relevant_glossary_entries(),
            source_text=SOURCE_TEXT,
        )

    assert "content must be a str" in str(excinfo.value)


def test_public_api_exports_the_sixteen_documented_names():
    import translation_core

    expected = {
        "ChapterRecord",
        "GlossaryEntry",
        "LLMProvider",
        "ProviderConfig",
        "ProviderError",
        "create_provider",
        "find_relevant_entries",
        "get_recent",
        "load_agent_file",
        "load_chapters",
        "load_glossary",
        "record_chapter",
        "save_agent_file",
        "save_chapters",
        "save_glossary",
        "translate_chunk",
    }

    assert set(translation_core.__all__) == expected
    for name in expected:
        assert getattr(translation_core, name) is not None

    assert issubclass(ProviderError, Exception)
    assert callable(create_provider)
    assert callable(translate_chunk)
    assert callable(load_agent_file)
    assert callable(save_agent_file)
    assert ProviderConfig.__name__ == "ProviderConfig"
    assert LLMProvider.__name__ == "LLMProvider"
    assert GlossaryEntry.__name__ == "GlossaryEntry"


def test_create_provider_from_top_level_import_works():
    provider = create_provider(
        ProviderConfig(
            type="openai_compatible",
            base_url="http://localhost:1234/v1",
            api_key="dummy",
            model="local-model",
        )
    )

    with provider:
        assert isinstance(provider, OpenAICompatibleProvider)
```

`test_full_composition_null_content_raises_provider_error`'s old
second half — reproducing the assertion via `store.add_chapter(...,
translated_text=None)` — is dropped, not replaced with an equivalent: it
guarded against a chromadb-specific silent-metadata-drop bug for a value
that flowed unchecked from a raw provider response into
`RAGStore.add_chapter`. In this design, `translate_chunk`'s output only
ever reaches `save_glossary`/`record_chapter` after already passing
through `OpenAICompatibleProvider.complete`'s own `content must be a str`
guard (exercised by the assertion kept above) — there is no remaining
code path where a `None` could reach glossary/chapter storage unchecked,
so there is nothing left for an equivalent test to guard.

- [ ] **Step 5: Update `requirements.txt`**

Remove these two lines (confirmed at lines 5-6 as of this plan being
written — re-check the exact lines before editing, in case an unrelated
earlier edit shifted them):

```
chromadb==1.5.9
sentence-transformers==5.6.0
```

- [ ] **Step 6: Run the full test suite**

Run: `pytest -q`
Expected: all tests pass, with no `chromadb`/`sentence-transformers`
import anywhere in the run (a passing suite here already proves this,
since nothing left imports them).

- [ ] **Step 7: Commit**

```bash
git add translation_core/__init__.py tests/test_integration.py requirements.txt
git commit -m "chore: remove the Chroma-backed RAG package and its dependencies"
```

---

### Task 10: End-to-end verification

**Files:**
- None created/modified — verification only.

- [ ] **Step 1: Full walkthrough**

- Run the full pytest suite: `pytest -q` — expect every test passing,
  and confirm no `chromadb`/`sentence-transformers` import remains
  anywhere (`pip show chromadb` after `pip uninstall chromadb
  sentence-transformers -y` in a scratch venv is one way to confirm
  nothing silently still depends on them, but is not required if the
  grep from Task 9 Step 1 and a clean pytest run already establish it).
- In the browser: create a new workspace, confirm `glossary.json` and
  `chapters.json` both exist on disk immediately with empty
  `{"entries": []}`/`{"chapters": []}` content.
- Build a small graph: `LoadTextFile` (a short source chapter) →
  `Provider` → `Translate` → `SaveTextFile`, then separately
  `Translate.translated_text` + `LoadTextFile.text` (as `source_text`) →
  `ExtractGlossary` (with `LoadGlossary` feeding its `glossary_entries`
  input and `chapter_id` set to something like `"ch1"`) →
  `ExtractGlossary.updated_glossary_entries` → `SaveGlossary`,
  `ExtractGlossary.corrected_translated_text` → a second `SaveTextFile`,
  `ExtractGlossary.revision_note` → `TextPreview`. Run it against a real
  LM Studio (or any OpenAI-compatible) endpoint, confirm `glossary.json`
  gains at least one entry.
- Also wire `RecordChapter` (with the same source/output paths used
  above) into the same run, confirm `chapters.json` gains a matching entry.
- Run `EvaluateAndFixChapters` against that same workspace (provider +
  `agent_instructions` + the just-saved `glossary_entries`), confirm its
  `report` output mentions the one recorded chapter.
- Open the migrated `vi-du-lm-studio` example workspace, confirm it still
  loads and its graph runs end-to-end against a real LM Studio instance
  (this reproduces Task 8's manual check with an actual run, not just a
  visual load).

- [ ] **Step 2: Report results**

No commit for this task. Note anything that didn't work as described
above.
