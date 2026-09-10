# Embedding Provider & Path Picker — Design

## Bối cảnh

`RAGStore` (`translation_core/rag/store.py`) hard-codes its embedding
backend: `chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")`,
downloaded from the HuggingFace Hub the first time it's used, with no way
to point at a different model, a different backend, or a local cache
folder. There is also no configurable embedding per workspace/graph — the
model is the same for every workspace, always.

The user wants to be able to choose, per graph, between:
1. **LM Studio** — an already-running local LLM server that also exposes
   an OpenAI-compatible `/v1/embeddings` endpoint when an embedding model
   is loaded in it.
2. **Local (cached) model** — a sentence-transformers model identified by
   its HuggingFace id, downloaded once into a user-chosen folder and
   loaded from there on every subsequent run (fully offline after the
   first download).

Separately, every path-shaped input in this app (`LoadTextFile.path`,
`SaveTextFile.path`, and the new local-model cache folder) is a plain text
box today — the user has to type or paste an absolute path by hand. The
user wants a "Browse…" popup to pick a folder instead.

**Important browser constraint, established during brainstorming:** a
browser cannot open a native OS folder-picker dialog and hand back a real
absolute filesystem path (`<input type="file">` deliberately withholds the
full path for security; the File System Access API returns opaque handles,
not path strings). Since every path in this app is a path *on the machine
running the FastAPI backend* (this is a local, single-user tool — the
backend and the browser are the same machine in normal use), the only way
to give the user a real "browse and pick a path" experience is a small,
custom, backend-driven directory browser: an API that lists a directory's
subfolders, and a modal in the canvas UI that walks it.

## Mục tiêu

1. A new node, `EmbeddingProvider` (category `Translation`, mirroring the
   existing `Provider` node), lets a graph choose an embedding backend —
   LM Studio or local — and configure it.
2. `RAGQuery` and `SaveToRAG` accept this configuration through a new
   **optional** `embedding_provider` input. Unwired (the case for every
   graph that predates this feature, including the shipped
   `vi-du-lm-studio` example), they keep today's exact behavior: the
   hard-coded local MiniLM model, no cache-folder override. This feature
   must not break any existing saved workspace.
3. Switching embedding backend on a workspace that already has a non-empty
   `rag_index` is a real hazard (different backend ⇒ different vector
   space; even a coincidentally-matching dimension gives silently wrong
   nearest-neighbour results). Detect this and fail loudly rather than
   returning bad results.
4. A general-purpose "Browse…" folder picker, usable on any path-shaped
   node input — not just the new embedding cache folder. Applied to
   `LoadTextFile.path`, `SaveTextFile.path`, and `EmbeddingProvider`'s
   local-cache-folder field.

## Kiến trúc tổng quan

```
translation_core/
  rag/
    embeddings.py        (Create: EmbeddingBackendConfig, the LM Studio
                           embedding function, and the factory that turns
                           a config into a chromadb-compatible embedding
                           function)
    store.py              (Modify: RAGStore accepts an optional
                            EmbeddingBackendConfig; records/validates an
                            embedding-identity signature on the collection)
  __init__.py              (Modify: export EmbeddingBackendConfig)
server/
  main.py                  (Modify: add `GET /api/browse-directory`)
  nodes/
    translate.py           (Modify: EmbeddingProvider node; RAGQuery and
                             SaveToRAG gain the optional
                             embedding_provider input)
    utility.py             (Modify: mark LoadTextFile.path and
                             SaveTextFile.path as path-widget fields)
web/
  canvas.html              (Modify: load path_picker.js, modal CSS)
  js/
    path_picker.js         (Create: openPathPicker(initialPath, onSelect)
                             — fetches /api/browse-directory, renders a
                             breadcrumb + folder-list modal)
    inspector_panel.js      (Modify: a STRING field whose spec carries
                             `widget: "path"` gets a "Browse…" button)
    nodegen.js               (Modify: NODE_TYPE_META entry for
                               EmbeddingProvider)
    i18n.js                  (Modify: new UI strings + EmbeddingProvider's
                               node label/description)
```

### `EmbeddingBackendConfig` and the embedding function factory

```python
@dataclass
class EmbeddingBackendConfig:
    backend: str            # "lm_studio" | "local"
    base_url: str = ""      # lm_studio
    api_key: str = ""       # lm_studio
    model: str = ""         # lm_studio — the loaded embedding model's name
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"   # local
    cache_folder: str = ""  # local — "" lets sentence-transformers use its
                             # own default cache location

    @property
    def signature(self) -> str:
        """A short identity string used to detect a backend/model switch
        on an existing collection. Deliberately excludes base_url/api_key/
        cache_folder: those can change (a different port, a moved cache
        folder) without changing what the vectors actually mean."""
        if self.backend == "lm_studio":
            return f"lm_studio:{self.model}"
        return f"local:{self.model_name}"
```

`create_embedding_function(config: EmbeddingBackendConfig | None)` returns
a chromadb-compatible embedding function (any callable
`__call__(self, input: list[str]) -> list[list[float]]` satisfies
chromadb's `EmbeddingFunction` protocol):

- `config is None` → today's exact call:
  `SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")`.
- `config.backend == "local"` → same class, plus
  `cache_folder=config.cache_folder or None` and
  `model_name=config.model_name`.
- `config.backend == "lm_studio"` → a new `LMStudioEmbeddingFunction`
  class in the same file: `POST {base_url}/embeddings` with
  `{"input": texts, "model": config.model}`, headers
  `{"Authorization": f"Bearer {config.api_key}"}` (LM Studio ignores the
  key but the header costs nothing to send, and it keeps this consistent
  with `OpenAICompatibleProvider`'s pattern), parses the OpenAI-shaped
  response `{"data": [{"embedding": [...]}, ...]}` back into a plain list
  of vectors, in the same order as the input. HTTP/shape errors raise a
  `ProviderError`-style exception (reuse `translation_core.providers.base.ProviderError`
  — an embedding backend failing is the same *kind* of failure as an LLM
  backend failing) with the response body sanitized/truncated the same
  way `OpenAICompatibleProvider._sanitize_error_body` does (mirror that
  logic; a wrong `api_key` should never end up in a raised exception's
  string).

### `RAGStore` changes

`__init__(self, persist_directory, embedding_config: EmbeddingBackendConfig | None = None)`:

1. Build the embedding function via `create_embedding_function(embedding_config)`.
2. Compute `signature = (embedding_config.signature if embedding_config else _DEFAULT_SIGNATURE)`, where `_DEFAULT_SIGNATURE = "local:paraphrase-multilingual-MiniLM-L12-v2"` (identical to what `EmbeddingBackendConfig(backend="local").signature` would produce, so `None` and "explicitly the default local config" are indistinguishable — intentional).
3. `get_or_create_collection(name=..., embedding_function=..., metadata={"embedding_signature": signature})`. chromadb's `get_or_create` does **not** overwrite metadata on an already-existing collection with different metadata passed in — verify this against the installed chromadb version while implementing; if it turns out `get_or_create_collection` **does** clobber existing metadata, the create-then-read-back order must change (create only via `get_collection`, falling back to `create_collection` on a `NotFoundError`, so an existing collection's stored metadata is never re-written by a later open).
4. After obtaining the collection, read back `collection.metadata.get("embedding_signature")`. A collection created before this feature existed has no such key at all — treat a **missing** key as `_DEFAULT_SIGNATURE` (an old collection is assumed to have been built with the old hard-coded model, which is true for every collection that exists before this ships). If the stored signature (real or assumed-default) does not equal the current `signature`, raise a new `EmbeddingMismatchError(WorkspaceError-style exception, but specific to RAG)` naming the workspace's stored signature, the requested signature, and pointing at the two ways out: switch `EmbeddingProvider` back, or delete the workspace's `rag_index/` folder to start a fresh index (a full re-embed is out of scope for this plan — see "Ngoài phạm vi").

This is a **read-time** check (raised from `__init__`, so it fires before
either `query` or `add_chapter` can run) — the plan's error-handling
constraint from Sub-project B ("`int(chapter_count)` invalid → let it
raise naturally") sets the same precedent here: a mismatch is a hard
failure surfaced to the graph-run's `node_error` event, not a silent
fallback.

### `EmbeddingProvider` node

```python
@register_node("EmbeddingProvider")
class EmbeddingProvider(NodeBase):
    CATEGORY = "Translation"
    RETURN_TYPES = ("EMBEDDING_PROVIDER",)
    RETURN_NAMES = ("embedding_provider",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"backend": ("STRING", {"default": "local"})},
            "optional": {
                "base_url": ("STRING", {"default": "http://localhost:1234/v1"}),
                "api_key": ("STRING", {"default": "lm-studio"}),
                "model": ("STRING", {"default": ""}),
                "model_name": ("STRING", {"default": "paraphrase-multilingual-MiniLM-L12-v2"}),
                "cache_folder": ("STRING", {"default": "", "widget": "path"}),
            },
        }

    def execute(self, backend, base_url="http://localhost:1234/v1",
                api_key="lm-studio", model="", model_name="paraphrase-multilingual-MiniLM-L12-v2",
                cache_folder=""):
        return (EmbeddingBackendConfig(
            backend=backend, base_url=base_url, api_key=api_key, model=model,
            model_name=model_name, cache_folder=cache_folder,
        ),)
```

Like `Provider`, all fields are always visible regardless of `backend`'s
value — this app's node UI has no conditional-field-visibility mechanism,
and `Provider` already establishes the "flat fields, some unused
depending on a mode field" convention. Not introducing conditional
rendering here is consistent, not a shortcut.

### `RAGQuery` / `SaveToRAG` changes

Both gain `"optional": {"embedding_provider": ("EMBEDDING_PROVIDER", {})}`
(added to `RAGQuery`'s existing `optional` dict alongside `top_k`). Both
pass it straight through: `RAGStore(path, embedding_config=embedding_provider)`.
`embedding_provider` defaults to `None` in `execute`'s signature, matching
every other optional-typed input in this codebase (e.g. `Translate.rag_examples=None`).

### Path picker

**Backend — `GET /api/browse-directory`** (`server/main.py`):

- Query param `path` (optional). Empty/omitted → return the Windows drive
  list as pseudo-entries (`os.listdrives()` on Python ≥ 3.12, else probe
  `A:` through `Z:` with `Path(f"{letter}:/").exists()` — confirm the
  running Python's version during planning and pick accordingly), with
  `parent: null`.
- Non-empty `path` → `Path(path)` must exist and be a directory, else
  `HTTPException(400, "Path does not exist or is not a directory")`
  (mirrors `_workspace_http_error`'s "clear detail message" convention).
  List only subdirectories (this is a folder picker, not a file picker),
  sorted by name. A subdirectory that raises `PermissionError` on stat is
  skipped, not fatal to the whole listing (mirrors `list_workspaces`'
  "skip what fails validation" precedent). Response:
  `{"path": "<normalized path>", "parent": "<parent path or null>", "entries": [{"name": "...", "path": "..."}]}`.
- **Security note, stated explicitly for review, not silently assumed:**
  this endpoint lets any client that can reach the server enumerate the
  entire filesystem the server process can read. This is *not* a new
  trust boundary — `LoadTextFile`/`SaveTextFile` already accept and act on
  arbitrary absolute paths with zero restriction, consistent with this
  app's established local single-user trust model — but it makes
  filesystem structure discoverable through a UI affordance rather than
  requiring the caller to already know a path, which is worth a deliberate
  sign-off rather than an implicit one.

**Frontend — `web/js/path_picker.js`** (new):
`openPathPicker(initialPath, onSelect)` opens a modal, fetches
`/api/browse-directory?path=...` starting from `initialPath` (or the
drive list if blank/nonexistent), renders a breadcrumb and the folder
list, double-click navigates in, an "Up" action (when `parent` is
non-null) goes up, a "Chọn thư mục này" button calls
`onSelect(currentPath)` and closes the modal, "Hủy" just closes it.

**`inspector_panel.js` change:** in the existing STRING-field render loop
(`renderInspector`, the one that currently only checks
`inputType !== "STRING"`), also read `spec[1]?.widget`. When it is
`"path"`, append a small "Browse…" button next to the textarea:
`openPathPicker(field.value, (chosen) => { field.value = chosen; node.properties[name] = chosen; markActiveDirty(); })`.
This is additive to the existing textarea, not a replacement — the user
can still type/paste a path by hand.

**Marking the existing path fields:** `LoadTextFile.path` and
`SaveTextFile.path` (`server/nodes/utility.py`) both get
`{"default": "", "widget": "path"}` instead of `{"default": ""}`. This is
the only change to those two nodes.

## Xử lý lỗi & tương thích ngược

- No `EmbeddingProvider` wired into a graph (every graph that exists
  today) → `embedding_provider=None` reaches `RAGStore` exactly as before
  this feature shipped. Verified against the `vi-du-lm-studio` example
  workspace's `graph.json`, which does not use `SaveToRAG`/`RAGQuery` at
  all today and is therefore unaffected either way.
- An existing non-empty `rag_index/` with a different (or assumed-default)
  signature than the current graph's `EmbeddingProvider` → `RAGStore.__init__`
  raises `EmbeddingMismatchError` before any query/add happens. Surfaces to
  the graph run as a normal `node_error` event (the same path every other
  node exception already takes in `server/executor.py`'s `run_graph` — no
  executor change needed).
- LM Studio embedding endpoint unreachable/erroring → `ProviderError`,
  same surfacing path.

## Phụ thuộc & thứ tự triển khai

Both this sub-project and "Evaluate & Fix Chapters" touch
`translation_core/rag/store.py` (this one changes `__init__`'s signature
and adds the signature-check; the other changes `add_chapter`'s signature
and adds `get_recent`). They are independent in intent but **must be
implemented and merged sequentially, not in parallel worktrees**, to avoid
a merge conflict on the same file. Recommended order: this sub-project
first (it's the smaller, more self-contained of the two), then Evaluate &
Fix Chapters rebases on top of it.

## Ngoài phạm vi

- Automatic re-embedding of an existing `rag_index` when the backend
  changes (the brainstorm's "báo lỗi rõ ràng, không tự động" choice
  explicitly defers this — a user who wants to switch backends on a
  non-empty index deletes `rag_index/` and starts fresh).
- Any restriction/sandboxing of `GET /api/browse-directory` beyond what
  `LoadTextFile`/`SaveTextFile` already imply about this app's trust model.
- Conditional field visibility on `EmbeddingProvider` (showing only the
  fields relevant to the selected `backend`) — matches `Provider`'s
  existing flat-fields convention instead.
