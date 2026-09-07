# Translation & RAG Core (Sub-project B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `translation_core`, a standalone Python package (no UI, no
FastAPI) providing an LLM provider abstraction, a ChromaDB-backed RAG store,
an agent-instructions-file loader, and a `translate_chunk()` function that
combines them — ready for Sub-project C to wrap into graph nodes.

**Architecture:** Four independent modules under `translation_core/`
(`providers/`, `rag/`, `agent_file.py`, `translate.py`), each importable and
testable on its own, composed only by `translate_chunk()` at the top.

**Tech Stack:** Python 3.11+, httpx (already a dependency) for the
OpenAI-compatible provider, ChromaDB + sentence-transformers for the RAG
store, pytest for tests.

**Spec:** [docs/superpowers/specs/2026-09-07-translation-rag-core-design.md](../specs/2026-09-07-translation-rag-core-design.md)

## Global Constraints

- Python 3.11+ only (project-wide constraint carried over from Sub-project A).
- `translation_core` has no dependency on FastAPI, `server/`, or anything
  web/UI-related — it must be importable and testable in complete isolation.
- Provider selection/configuration is entirely external (`base_url`/
  `api_key`/`model`); no vendor-specific logic is hardcoded outside the
  `openai_compatible` provider type.
- RAG entries are per-chapter (no sub-chapter chunking) in this plan.
- The agent file is plain text/markdown with no schema or frontmatter
  parsing — its full content is used verbatim.
- No automatic retry logic at this layer.
- No Anthropic/Gemini provider implementations in this plan (architecture
  supports adding them later; not built now).

---

## File Structure

```
translation_core/
  __init__.py
  providers/
    __init__.py
    base.py                # LLMProvider (ABC) + ProviderError
    openai_compatible.py     # OpenAICompatibleProvider
    factory.py                # ProviderConfig + create_provider()
  rag/
    __init__.py
    store.py                  # RAGStore + RAGExample
  agent_file.py                # load_agent_file() / save_agent_file()
  translate.py                  # translate_chunk()
tests/
  test_providers.py             # Tasks 1-3
  test_agent_file.py             # Task 4
  test_rag_store.py               # Task 5
  test_translate.py                 # Task 6
requirements.txt                   # chromadb + sentence-transformers added in Task 5
```

---

### Task 1: Provider base interface

**Files:**
- Create: `translation_core/__init__.py` (empty)
- Create: `translation_core/providers/__init__.py` (empty)
- Create: `translation_core/providers/base.py`
- Test: `tests/test_providers.py`

**Interfaces:**
- Produces: `class ProviderError(Exception)`; `class LLMProvider(ABC)` with
  abstract method `complete(self, messages: list[dict], **kwargs) -> str`.
  Later tasks (Task 2's `OpenAICompatibleProvider`, Task 6's
  `translate_chunk()`) subclass/consume this exactly.

- [ ] **Step 1: Write the failing tests**

`tests/test_providers.py`:

```python
import pytest

from translation_core.providers.base import LLMProvider, ProviderError


def test_llm_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()


def test_provider_error_is_exception():
    assert issubclass(ProviderError, Exception)


def test_concrete_subclass_can_implement_complete():
    class EchoProvider(LLMProvider):
        def complete(self, messages, **kwargs):
            return messages[-1]["content"]

    provider = EchoProvider()
    result = provider.complete([{"role": "user", "content": "hello"}])

    assert result == "hello"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_providers.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'translation_core'`)

- [ ] **Step 3: Create `translation_core/__init__.py` and `translation_core/providers/__init__.py` (both empty)**

- [ ] **Step 4: Implement `translation_core/providers/base.py`**

```python
from abc import ABC, abstractmethod


class ProviderError(Exception):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[dict], **kwargs) -> str:
        raise NotImplementedError
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_providers.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add translation_core/__init__.py translation_core/providers/__init__.py translation_core/providers/base.py tests/test_providers.py
git commit -m "feat: add LLMProvider base interface and ProviderError"
```

---

### Task 2: OpenAI-compatible provider

**Files:**
- Create: `translation_core/providers/openai_compatible.py`
- Test: `tests/test_providers.py` (extend)

**Interfaces:**
- Consumes: `LLMProvider`, `ProviderError` from `translation_core.providers.base` (Task 1).
- Produces: `class OpenAICompatibleProvider(LLMProvider)` with
  `__init__(self, base_url: str, api_key: str, model: str, client: httpx.Client | None = None)`
  and `complete(self, messages: list[dict], **kwargs) -> str`. The optional
  `client` param exists so tests can inject an `httpx.Client` wired to
  `httpx.MockTransport` instead of hitting a real network endpoint —
  Task 3's factory always constructs it with the default (no `client` arg).

- [ ] **Step 1: Write the failing tests (append to `tests/test_providers.py`)**

```python
import json

import httpx

from translation_core.providers.openai_compatible import OpenAICompatibleProvider


def _client_with_handler(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_complete_returns_message_content():
    def handler(request):
        assert request.url.path == "/chat/completions"
        return httpx.Response(200, json={"choices": [{"message": {"content": "Xin chào"}}]})

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=_client_with_handler(handler),
    )

    result = provider.complete([{"role": "user", "content": "hello"}])

    assert result == "Xin chào"


def test_complete_sends_expected_payload_and_headers():
    captured = {}

    def handler(request):
        captured["headers"] = request.headers
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="secret-key",
        model="local-model",
        client=_client_with_handler(handler),
    )

    provider.complete([{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}])

    assert captured["headers"]["authorization"] == "Bearer secret-key"
    assert captured["json"]["model"] == "local-model"
    assert captured["json"]["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]


def test_complete_raises_provider_error_on_http_status_error():
    def handler(request):
        return httpx.Response(500, text="internal error")

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=_client_with_handler(handler),
    )

    with pytest.raises(ProviderError):
        provider.complete([{"role": "user", "content": "hi"}])


def test_complete_raises_provider_error_on_malformed_response():
    def handler(request):
        return httpx.Response(200, json={"unexpected": "shape"})

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=_client_with_handler(handler),
    )

    with pytest.raises(ProviderError):
        provider.complete([{"role": "user", "content": "hi"}])


def test_complete_raises_provider_error_on_network_failure():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=_client_with_handler(handler),
    )

    with pytest.raises(ProviderError):
        provider.complete([{"role": "user", "content": "hi"}])
```

`ProviderError` and `pytest` are already imported at the top of
`tests/test_providers.py` from Task 1 — add `import json` and `import httpx`
alongside the existing imports.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_providers.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'translation_core.providers.openai_compatible'`)

- [ ] **Step 3: Implement `translation_core/providers/openai_compatible.py`**

```python
import httpx

from translation_core.providers.base import LLMProvider, ProviderError


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client = client or httpx.Client(timeout=60.0)

    def complete(self, messages: list[dict], **kwargs) -> str:
        payload = {"model": self.model, "messages": messages, **kwargs}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"Provider returned HTTP {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Provider request failed: {exc}") from exc

        try:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Provider returned an unexpected response shape: {exc}") from exc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_providers.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add translation_core/providers/openai_compatible.py tests/test_providers.py
git commit -m "feat: add OpenAICompatibleProvider (covers OpenAI/LM Studio/Ollama/etc.)"
```

---

### Task 3: Provider factory

**Files:**
- Create: `translation_core/providers/factory.py`
- Test: `tests/test_providers.py` (extend)

**Interfaces:**
- Consumes: `LLMProvider`, `ProviderError` from `translation_core.providers.base`
  (Task 1); `OpenAICompatibleProvider` from
  `translation_core.providers.openai_compatible` (Task 2).
- Produces: `@dataclass class ProviderConfig` with fields `type: str,
  base_url: str, api_key: str, model: str`; function
  `create_provider(config: ProviderConfig) -> LLMProvider`, raising
  `ProviderError` for an unknown `config.type`.

- [ ] **Step 1: Write the failing tests (append to `tests/test_providers.py`)**

```python
from translation_core.providers.factory import ProviderConfig, create_provider


def test_create_provider_openai_compatible():
    config = ProviderConfig(
        type="openai_compatible",
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
    )

    provider = create_provider(config)

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "http://localhost:1234/v1"
    assert provider.model == "local-model"


def test_create_provider_unknown_type_raises():
    config = ProviderConfig(type="unknown", base_url="", api_key="", model="")

    with pytest.raises(ProviderError):
        create_provider(config)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_providers.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'translation_core.providers.factory'`)

- [ ] **Step 3: Implement `translation_core/providers/factory.py`**

```python
from dataclasses import dataclass

from translation_core.providers.base import LLMProvider, ProviderError
from translation_core.providers.openai_compatible import OpenAICompatibleProvider


@dataclass
class ProviderConfig:
    type: str
    base_url: str
    api_key: str
    model: str


def create_provider(config: ProviderConfig) -> LLMProvider:
    if config.type == "openai_compatible":
        return OpenAICompatibleProvider(
            base_url=config.base_url, api_key=config.api_key, model=config.model
        )
    raise ProviderError(f"Unknown provider type: {config.type}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_providers.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add translation_core/providers/factory.py tests/test_providers.py
git commit -m "feat: add ProviderConfig + create_provider factory"
```

---

### Task 4: Agent file loader

**Files:**
- Create: `translation_core/agent_file.py`
- Test: `tests/test_agent_file.py`

**Interfaces:**
- Produces: `load_agent_file(path: str | Path) -> str` (raises
  `FileNotFoundError` if the file doesn't exist); `save_agent_file(path: str
  | Path, content: str) -> None`. Task 6's tests use these names directly
  (though `translate_chunk()` itself takes the already-loaded string, not a
  path — see Task 6).

- [ ] **Step 1: Write the failing tests**

`tests/test_agent_file.py`:

```python
import pytest

from translation_core.agent_file import load_agent_file, save_agent_file


def test_save_then_load_round_trips_content(tmp_path):
    path = tmp_path / "agent.md"

    save_agent_file(path, "Dịch sang tiếng Việt, giữ văn phong trang trọng.")

    assert load_agent_file(path) == "Dịch sang tiếng Việt, giữ văn phong trang trọng."


def test_load_missing_file_raises_file_not_found_error(tmp_path):
    missing = tmp_path / "does-not-exist.md"

    with pytest.raises(FileNotFoundError):
        load_agent_file(missing)


def test_save_overwrites_existing_content(tmp_path):
    path = tmp_path / "agent.md"
    save_agent_file(path, "first version")

    save_agent_file(path, "second version")

    assert load_agent_file(path) == "second version"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_agent_file.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'translation_core.agent_file'`)

- [ ] **Step 3: Implement `translation_core/agent_file.py`**

```python
from pathlib import Path


def load_agent_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def save_agent_file(path: str | Path, content: str) -> None:
    Path(path).write_text(content, encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_agent_file.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add translation_core/agent_file.py tests/test_agent_file.py
git commit -m "feat: add agent file load/save helpers"
```

---

### Task 5: RAG store

**Files:**
- Create: `translation_core/rag/__init__.py` (empty)
- Create: `translation_core/rag/store.py`
- Modify: `requirements.txt` (add `chromadb` and `sentence-transformers`)
- Test: `tests/test_rag_store.py`

**Interfaces:**
- Produces: `@dataclass class RAGExample` with fields `chapter_id: str,
  source_text: str, translated_text: str, distance: float`; `class
  RAGStore` with `__init__(self, persist_directory: str | Path)`,
  `add_chapter(self, chapter_id: str, source_text: str, translated_text:
  str) -> None`, `query(self, text: str, top_k: int = 3) -> list[RAGExample]`.
  Task 6 consumes `RAGExample` and passes a `list[RAGExample]` (from
  `RAGStore.query()`) into `translate_chunk()`.

This task's tests use a real ChromaDB instance and a real
sentence-transformers model (`paraphrase-multilingual-MiniLM-L12-v2`) — no
mocking. **The first run downloads the model (~470MB) and needs internet
access; subsequent runs use the local cache and are fast.** Each test
constructing a `RAGStore` takes a few seconds (model load) — this is
expected, not a bug; don't try to "fix" the test speed.

- [ ] **Step 1: Add new dependencies to `requirements.txt`**

Append to the existing file (keep the 4 existing lines unchanged):

```
chromadb==0.5.20
sentence-transformers==3.3.1
```

Run: `pip install -r requirements.txt` and confirm it completes without
error (this step alone can take several minutes and a large download —
that's expected for these two packages).

- [ ] **Step 2: Write the failing tests**

`tests/test_rag_store.py`:

```python
from translation_core.rag.store import RAGStore


def test_add_and_query_returns_similar_chapter_first(tmp_path):
    store = RAGStore(persist_directory=tmp_path / "rag_index")

    store.add_chapter(
        chapter_id="ch1",
        source_text="The dragon knight Long Khe traveled to the misty mountain village.",
        translated_text="Long Khê du hành đến ngôi làng núi mù sương.",
    )
    store.add_chapter(
        chapter_id="ch2",
        source_text="The stock market crashed and traders panicked on Wall Street.",
        translated_text="Thị trường chứng khoán sụp đổ, các nhà giao dịch hoảng loạn.",
    )

    results = store.query("A knight rides toward a mountain village shrouded in fog.", top_k=1)

    assert len(results) == 1
    assert results[0].chapter_id == "ch1"
    assert results[0].translated_text == "Long Khê du hành đến ngôi làng núi mù sương."


def test_query_on_empty_store_returns_empty_list(tmp_path):
    store = RAGStore(persist_directory=tmp_path / "rag_index")

    results = store.query("anything", top_k=3)

    assert results == []


def test_add_chapter_upserts_existing_id(tmp_path):
    store = RAGStore(persist_directory=tmp_path / "rag_index")

    store.add_chapter(chapter_id="ch1", source_text="first version", translated_text="bản đầu")
    store.add_chapter(chapter_id="ch1", source_text="second version", translated_text="bản hai")

    results = store.query("second version", top_k=1)

    assert len(results) == 1
    assert results[0].translated_text == "bản hai"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_rag_store.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'translation_core.rag'`)

- [ ] **Step 4: Create `translation_core/rag/__init__.py` (empty) and implement `translation_core/rag/store.py`**

```python
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions


@dataclass
class RAGExample:
    chapter_id: str
    source_text: str
    translated_text: str
    distance: float


class RAGStore:
    _COLLECTION_NAME = "chapters"
    _EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, persist_directory: str | Path):
        self._client = chromadb.PersistentClient(path=str(persist_directory))
        self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self._EMBEDDING_MODEL_NAME
        )
        self._collection = self._client.get_or_create_collection(
            name=self._COLLECTION_NAME,
            embedding_function=self._embedding_function,
        )

    def add_chapter(self, chapter_id: str, source_text: str, translated_text: str) -> None:
        self._collection.upsert(
            ids=[chapter_id],
            documents=[source_text],
            metadatas=[{"translated_text": translated_text}],
        )

    def query(self, text: str, top_k: int = 3) -> list[RAGExample]:
        if self._collection.count() == 0:
            return []

        result = self._collection.query(
            query_texts=[text],
            n_results=min(top_k, self._collection.count()),
        )

        examples = []
        for chapter_id, source_text, metadata, distance in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            examples.append(
                RAGExample(
                    chapter_id=chapter_id,
                    source_text=source_text,
                    translated_text=metadata["translated_text"],
                    distance=distance,
                )
            )
        return examples
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_rag_store.py -v`
Expected: PASS (3 passed) — allow extra time for the first run's model
download.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt translation_core/rag/__init__.py translation_core/rag/store.py tests/test_rag_store.py
git commit -m "feat: add ChromaDB-backed RAGStore keyed per chapter"
```

---

### Task 6: `translate_chunk()`

**Files:**
- Create: `translation_core/translate.py`
- Test: `tests/test_translate.py`

**Interfaces:**
- Consumes: `LLMProvider` from `translation_core.providers.base` (Task 1);
  `RAGExample` from `translation_core.rag.store` (Task 5).
- Produces: `translate_chunk(provider: LLMProvider, agent_instructions: str,
  rag_examples: list[RAGExample], source_text: str) -> str`. This is the
  function Sub-project C's "Translate" node will call directly.

- [ ] **Step 1: Write the failing tests**

`tests/test_translate.py`:

```python
from translation_core.providers.base import LLMProvider
from translation_core.rag.store import RAGExample
from translation_core.translate import translate_chunk


class RecordingProvider(LLMProvider):
    def __init__(self):
        self.received_messages = None

    def complete(self, messages, **kwargs):
        self.received_messages = messages
        return "bản dịch giả"


def test_translate_chunk_builds_system_prompt_with_rag_examples_and_calls_provider():
    provider = RecordingProvider()
    rag_examples = [
        RAGExample(
            chapter_id="ch1",
            source_text="A knight traveled to the village.",
            translated_text="Một hiệp sĩ đã đến ngôi làng.",
            distance=0.1,
        )
    ]

    result = translate_chunk(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt, văn phong trang trọng.",
        rag_examples=rag_examples,
        source_text="The knight drew his sword.",
    )

    assert result == "bản dịch giả"
    assert provider.received_messages[0]["role"] == "system"
    assert "Dịch sang tiếng Việt" in provider.received_messages[0]["content"]
    assert "A knight traveled to the village." in provider.received_messages[0]["content"]
    assert "Một hiệp sĩ đã đến ngôi làng." in provider.received_messages[0]["content"]
    assert provider.received_messages[1] == {"role": "user", "content": "The knight drew his sword."}


def test_translate_chunk_without_rag_examples_omits_examples_section():
    provider = RecordingProvider()

    translate_chunk(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt.",
        rag_examples=[],
        source_text="Hello world.",
    )

    assert "Ví dụ dịch trước đó" not in provider.received_messages[0]["content"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_translate.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'translation_core.translate'`)

- [ ] **Step 3: Implement `translation_core/translate.py`**

```python
from translation_core.providers.base import LLMProvider
from translation_core.rag.store import RAGExample


def translate_chunk(
    provider: LLMProvider,
    agent_instructions: str,
    rag_examples: list[RAGExample],
    source_text: str,
) -> str:
    system_prompt = agent_instructions

    if rag_examples:
        examples_text = "\n\n".join(
            f"Nguồn: {example.source_text}\nBản dịch: {example.translated_text}"
            for example in rag_examples
        )
        system_prompt += (
            "\n\n## Ví dụ dịch trước đó (tham khảo văn phong/thuật ngữ):\n" + examples_text
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": source_text},
    ]
    return provider.complete(messages)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_translate.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full test suite once to confirm no regressions**

Run: `pytest -v`
Expected: all tests pass (existing A1 backend tests + this plan's new tests).

- [ ] **Step 6: Commit**

```bash
git add translation_core/translate.py tests/test_translate.py
git commit -m "feat: add translate_chunk combining provider + RAG + agent instructions"
```

---

## Self-Review Notes

- **Spec coverage:** Provider abstraction (#1) → Tasks 1-3; RAG store (#2)
  → Task 5; Agent file loader (#3) → Task 4; `translate_chunk()` core
  function → Task 6; error handling (ProviderError, FileNotFoundError) →
  Tasks 1/2/4 tests; testing section (httpx.MockTransport for provider, real
  ChromaDB+embedding for RAG, real file I/O for agent file, fake provider
  for translate_chunk) → matches each task's test approach exactly. Out of
  scope items (Anthropic/Gemini providers, sub-chapter chunking, auto
  glossary extraction, UI/MCP) are correctly absent from every task.
- **Type consistency:** `LLMProvider`/`ProviderError` (Task 1) used
  identically in Tasks 2, 3, 6. `OpenAICompatibleProvider` (Task 2)
  constructor signature matches its use in Task 3's factory. `RAGExample`
  (Task 5) field names (`chapter_id`, `source_text`, `translated_text`,
  `distance`) match exactly how Task 6's tests construct and how
  `translate_chunk()` reads them.
- **Placeholder scan:** no TBD/TODO; every step has runnable code and an
  expected test-run outcome.

---

Plan complete and saved to `docs/superpowers/plans/2026-09-07-translation-rag-core-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
