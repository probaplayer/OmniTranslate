# Evaluate & Fix Chapters — Design

## Bối cảnh

Once a novel has many chapters translated, mistakes made early (a
character name translated inconsistently, a recurring mistranslation, a
tone drift) stay wrong forever — nothing in this app ever looks back at
already-translated chapters. `RAGStore` can store and semantically search
chapters (`add_chapter`/`query`), but it has no notion of chronological
order (Chroma does not guarantee insertion order on arbitrary reads) and
no link from a stored chapter back to the output file it was written to
— `chapter_id` (used by `SaveToRAG`) and the output file path (used
separately by `SaveTextFile`) are two independently-typed strings today,
confirmed by reading the shipped `vi-du-lm-studio` example workflow, which
doesn't even wire `SaveToRAG` into its graph.

The user wants a way to periodically look back at the most recently
translated chapters, detect ones that were mistranslated, fix them in
place (both the output file and the RAG entry), and — separately —
surface a proposed revision to `agent.md`'s instructions when the same
kind of mistake recurs, without ever auto-applying that revision (agent.md
stays hand-edited via the existing `LoadAgentFile`/`SaveAgentFile` nodes,
same as today; this feature only proposes).

## Mục tiêu

1. `SaveToRAG` records which output file a chapter was written to, and
   when it was saved — the missing link needed for anything to look back
   at "what did I translate recently, and where did it go."
2. `RAGStore.get_recent(n)` returns the `n` most recently saved chapters,
   newest first — a new capability; `query` only does semantic search.
3. A new node, `EvaluateAndFixChapters`, reviews the last N chapters
   (N a per-run setting) against the current `agent_instructions`,
   re-translates and overwrites (file + RAG entry) any it judges
   mistranslated, and separately proposes a revised `agent_instructions`
   text when it finds a recurring problem (unchanged if it finds none).
   Neither the fixed chapters nor the revised instructions are silently
   applied beyond what the node itself does — the *proposed instructions*
   output is just a `STRING` the user chooses whether to wire into
   `SaveAgentFile`.

## Kiến trúc tổng quan

```
translation_core/
  rag/
    store.py         (Modify: add_chapter gains output_path; a
                       ChapterRecord dataclass; RAGStore.get_recent(n))
server/
  nodes/
    translate.py      (Modify: SaveToRAG gains a required output_path
                        input; new EvaluateAndFixChapters node)
web/
  js/
    nodegen.js          (Modify: NODE_TYPE_META entry for
                          EvaluateAndFixChapters)
    i18n.js              (Modify: node label/description + any new UI
                           strings)
```

No frontend behavior changes beyond the new node's icon/label/description
— like `TextInput`, its inputs are plain typed values the inspector
already knows how to render (`PROVIDER`/`STRING`), and its two `STRING`
outputs need no special UI.

### `RAGStore` changes

```python
@dataclass
class ChapterRecord:
    chapter_id: str
    source_text: str
    translated_text: str
    output_path: str
    saved_at: float
```

(A distinct dataclass from `RAGExample`, not a reuse: `RAGExample` carries
a similarity `distance`, which has no meaning for a chronological fetch,
and doesn't carry `output_path`, which `RAGExample`'s existing consumer —
`Translate`'s few-shot prompt — has no use for.)

`add_chapter(self, chapter_id, source_text, translated_text, output_path="") -> None`:
adds `output_path` (default `""` so any not-yet-updated caller keeps
working, though `SaveToRAG` will always pass a real value once this ships)
and stamps `metadata["saved_at"] = time.time()`. `time.time()` is
monotonic-enough for this purpose — chapters are saved seconds-to-minutes
apart by a human/graph-run workflow, never sub-millisecond — so no
separate persistent counter is needed. The existing
`isinstance(translated_text, str)` guard (protecting against chromadb
silently dropping the whole metadata dict on a non-primitive value) stays
exactly as-is; `output_path` and `saved_at` go through the same
`metadatas=[...]` dict and are equally exposed to that failure mode, so
the guard's docstring should be updated to say so.

`get_recent(self, n: int) -> list[ChapterRecord]`: chromadb's `Collection.get()`
(not `.query()`) fetches by criteria without embedding search — confirm
its exact keyword shape (`include=[...]`, whether metadatas are returned
by default) against the installed chromadb version while implementing,
the same verify-before-committing discipline this project already applies
to litegraph.js. Fetch all documents (`self._collection.get(include=["documents", "metadatas"])`),
sort the returned rows by `metadata["saved_at"]` descending, take the
first `n`, map into `ChapterRecord`s. `n <= 0` or an empty collection both
return `[]`, mirroring `query`'s existing `top_k <= 0` / `count() == 0`
early returns.

### `SaveToRAG` changes

`INPUT_TYPES` moves `output_path` into `required` (not optional — a
chapter this feature can't later find on disk to fix is not useful to
this feature, and there is no reasonable default path to fall back to):

```python
"required": {
    "chapter_id": ("STRING", {"default": ""}),
    "source_text": ("STRING", {"default": ""}),
    "translated_text": ("STRING", {"default": ""}),
    "output_path": ("STRING", {"default": "", "widget": "path"}),
},
```

(The `widget: "path"` flag depends on Sub-project A's inspector-panel
change; if this sub-project ships first, add the flag now and it simply
has no visible effect — a plain textarea — until Sub-project A lands, per
that spec's "must ship sequentially" note. If this ships second, the
Browse… button just works.)

`execute` passes `output_path` straight through to `store.add_chapter(...)`.
This is a **required-input addition to an existing node** — any saved
graph that already wires `SaveToRAG` without this input will fail
`server/executor.py`'s `validate_required_inputs` the next time it runs.
Confirmed via the shipped example workspace that no graph currently wires
`SaveToRAG` at all, so this has zero real-world breakage today, but the
plan should still add a one-line note to whatever user-facing changelog
this project keeps (if any) — check during planning whether one exists.

### `EvaluateAndFixChapters` node

```python
@register_node("EvaluateAndFixChapters")
class EvaluateAndFixChapters(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("report", "revised_agent_instructions")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": ("PROVIDER", {}),
                "agent_instructions": ("STRING", {"default": ""}),
            },
            "optional": {"chapter_count": ("STRING", {"default": "5"})},
        }

    def execute(self, workspace_name, provider, agent_instructions, chapter_count="5"):
        ...
```

`execute`'s algorithm:

1. `store = RAGStore(workspace.get_workspace_path(workspace_name, "rag_index"))`
   — if Sub-project A has shipped, this node has no `embedding_provider`
   input of its own; it only needs to *read* the existing index (via
   `get_recent`, which does not touch the embedding function at all —
   `Collection.get()` needs no query embedding), so the mismatch-detection
   from Sub-project A only matters here in that a genuinely mismatched
   index still raises from `RAGStore.__init__` before `get_recent` runs,
   which is the correct, consistent behavior (this node can't safely
   trust a chapter record from an index built with a different embedding
   config either, even though it isn't the thing being validated).
2. `chapters = store.get_recent(int(chapter_count))`. Empty →
   `return (f"Không có chương nào để đánh giá.", agent_instructions)`, no
   LLM calls.
3. For each chapter, newest → oldest, build a critique prompt:
   - System message: `agent_instructions` plus a fixed instruction block
     asking the model to answer in exactly one of two forms: the literal
     line `OK`, or a line starting `LỖI: ` followed by a short description
     of the problem.
   - User message: the chapter's `source_text` and current
     `translated_text`, clearly labeled.
   - Call `provider.complete(messages)` directly (the same `LLMProvider`
     interface `Translate` already uses — no new provider method needed).
4. Parse the response: if it starts with `LỖI` (case-sensitive match on
   the fixed prefix this node itself asked for — a model that doesn't
   follow the format is treated as "no error found" rather than crashing
   the node; log this leniency in a code comment, don't silently pretend
   it's a real verdict), call
   `translate_chunk(provider, agent_instructions, [], chapter.source_text)`
   for a corrected translation, then:
   - Overwrite the file: `Path(chapter.output_path).parent.mkdir(parents=True, exist_ok=True); Path(chapter.output_path).write_text(corrected, encoding="utf-8")` — the exact same two lines `SaveTextFile.execute` already uses, kept inline here rather than extracted into a shared helper (two call sites, three lines, not worth a new indirection per this project's YAGNI norm — revisit only if a third caller shows up).
   - `store.add_chapter(chapter.chapter_id, chapter.source_text, corrected, chapter.output_path)` — `upsert` under the same id overwrites in place, and `add_chapter`'s new `saved_at` stamp naturally advances, so a chapter that gets fixed also becomes "more recent" for the *next* run of this same node — an accepted, not fought, side effect (a chapter just fixed doesn't need re-checking again immediately).
   - Append `(chapter.chapter_id, error_description)` to a `findings` list.
5. After the loop: if `findings` is non-empty, one more `provider.complete(...)`
   call — system message asks the model to act as a translation editor and
   propose a revised `agent_instructions` given the current instructions
   and the list of recurring problems found; the findings are formatted
   into the user message. If `findings` is empty, `revised = agent_instructions`
   unchanged (no LLM call — nothing to revise).
6. `report` is a plain-text summary: how many chapters were checked, and
   for each one that was fixed, its `chapter_id` and the error description.
7. `return (report, revised)`.

**Explicitly accepted limitation, not solved by this plan:** this is one
`execute()` call making up to `2N + 1` sequential LLM completions (1
critique + up to 1 re-translation per chapter, + 1 final revision call).
`server/executor.py`'s `run_graph` only emits `node_started`/`node_completed`
around the *whole* node — there is no per-chapter progress event, so for a
large `chapter_count` against a local model, the UI shows this node as one
long-running step with no incremental feedback. Splitting this into
separate "evaluate" and "fix" nodes with real per-chapter progress would
solve that, but is a bigger redesign than what was asked for here — noted
as a future enhancement, not part of this plan.

## Xử lý lỗi

- `int(chapter_count)` on a non-numeric value raises `ValueError` and
  propagates — no bespoke validation, matching `RAGQuery.execute`'s
  existing identical `int(top_k)` behavior (same file, same precedent).
- A chapter whose `output_path` no longer exists on disk (deleted or moved
  since it was saved) — `Path(...).parent.mkdir(parents=True, exist_ok=True)`
  before writing means a missing *directory* self-heals, but note this
  explicitly recreates a deleted directory structure the user may have
  intentionally removed; this mirrors `SaveTextFile`'s existing behavior
  exactly (no new risk introduced, just inherited).
- An `EmbeddingMismatchError` from `RAGStore.__init__` (Sub-project A) is
  not caught here — it propagates as a normal node exception, exactly like
  every other exception in this codebase's node `execute()` methods.

## Testing

- `tests/test_rag_store.py`: `add_chapter` stores `output_path` and a
  `saved_at` that increases across calls; `get_recent(n)` returns the
  correct count/order (newest-first) and truncates when fewer than `n`
  chapters exist; `get_recent` on an empty store returns `[]`.
- `tests/test_translate_nodes.py`: `SaveToRAG` now requires `output_path`
  (update the existing test(s) that call it); a new `_ScriptedProvider`
  test double (same shape as the file's existing `_RecordingProvider`,
  but returning canned responses from a list in call order) exercises
  `EvaluateAndFixChapters`: all-chapters-`OK` (no file/RAG writes, `revised
  == agent_instructions`), one-flawed-chapter (file overwritten, RAG entry
  updated, `revised != agent_instructions`, `report` names the fixed
  chapter), and the empty-store path (no LLM calls made at all — assert
  the scripted provider was never invoked).

## Phụ thuộc & thứ tự triển khai

Shares `translation_core/rag/store.py` with the Embedding Provider design
— see that spec's "Phụ thuộc & thứ tự triển khai" section. Build this one
second, after Embedding Provider has merged, and rebase `get_recent`/`add_chapter`'s
changes on top of that file's post-merge state rather than developing both
in parallel worktrees.

## Ngoài phạm vi

- Updating `agent.md` automatically — `revised_agent_instructions` is
  always just an output the user chooses to wire into `SaveAgentFile` or
  not (explicit brainstorm decision).
- Any automatic/background trigger for this node (e.g. "run this after
  every N chapters translated") — it is a node like any other, run when
  the user chooses to run it (explicit brainstorm decision).
- Per-chapter progress reporting during a single run (see "Explicitly
  accepted limitation" above).
- Re-evaluating chapters by any means other than "the N most recently
  saved" (e.g. a user-supplied explicit chapter-id list) — explicit
  brainstorm decision.
