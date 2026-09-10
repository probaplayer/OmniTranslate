import pytest

from translation_core import GlossaryEntry, LLMProvider
from translation_core.chapters import load_chapters
from translation_core.providers.openai_compatible import OpenAICompatibleProvider

from server import workspace
from server.node_registry import get_node_class
from server.nodes import translate  # noqa: F401  (triggers registration)


@pytest.fixture(autouse=True)
def isolated_workspaces_root(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "WORKSPACES_ROOT", tmp_path / "workspaces")


def test_provider_node_creates_openai_compatible_provider():
    node = get_node_class("Provider")()

    result = node.execute(
        base_url="http://localhost:1234/v1", api_key="dummy", model="local-model"
    )

    assert len(result) == 1
    provider = result[0]
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "http://localhost:1234/v1"
    assert provider.model == "local-model"


def test_load_agent_file_node_reads_seeded_file():
    workspace.create_workspace("novel-a")
    node = get_node_class("LoadAgentFile")()

    result = node.execute(workspace_name="novel-a")

    assert "Dịch sang tiếng Việt" in result[0]


def test_load_agent_file_node_raises_when_missing():
    workspace.create_workspace("novel-a")
    workspace.get_workspace_path("novel-a", "agent.md").unlink()
    node = get_node_class("LoadAgentFile")()

    with pytest.raises(FileNotFoundError):
        node.execute(workspace_name="novel-a")


def test_save_agent_file_node_overwrites_content():
    workspace.create_workspace("novel-a")
    node = get_node_class("SaveAgentFile")()

    result = node.execute(workspace_name="novel-a", text="Nội dung mới")

    assert result == ()
    saved = workspace.get_workspace_path("novel-a", "agent.md").read_text(encoding="utf-8")
    assert saved == "Nội dung mới"


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


class _RecordingProvider(LLMProvider):
    def __init__(self):
        self.received_messages = None

    def complete(self, messages, **kwargs):
        self.received_messages = messages
        return "bản dịch giả"


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


def test_translate_node_works_without_rag_examples():
    node = get_node_class("Translate")()
    provider = _RecordingProvider()

    result = node.execute(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt.",
        source_text="Hello world.",
    )

    assert result == ("bản dịch giả",)
    # Verify system prompt is just the agent instructions (no RAG section)
    assert provider.received_messages[0]["role"] == "system"
    assert provider.received_messages[0]["content"] == "Dịch sang tiếng Việt."


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


def test_extract_glossary_skips_unsafe_replacement_when_established_contains_candidate():
    existing = [GlossaryEntry(term="龙王", translation="Hai Long Vuong", note="", chapter_id="ch1")]
    node = get_node_class("ExtractGlossary")()
    provider = _ScriptedProvider(["龙王 | Long Vuong | vua rong", "GIU_CU"])

    updated, corrected, note = node.execute(
        provider=provider,
        glossary_entries=existing,
        source_text="龙王发怒了。龙王下令。",
        translated_text="Hai Long Vuong noi gian. Long Vuong ra lenh.",
        chapter_id="ch2",
    )

    # The already-correct "Hai Long Vuong" occurrence must survive untouched.
    assert corrected == "Hai Long Vuong noi gian. Long Vuong ra lenh."
    assert "không tự sửa được" in note


def test_extract_glossary_skips_unsafe_replacement_on_occurrence_count_mismatch():
    existing = [GlossaryEntry(term="大哥", translation="Dai ca", note="", chapter_id="ch1")]
    node = get_node_class("ExtractGlossary")()
    provider = _ScriptedProvider(["大哥 | Anh | anh trai", "GIU_CU"])

    updated, corrected, note = node.execute(
        provider=provider,
        glossary_entries=existing,
        source_text="大哥走进来。",
        translated_text="Anh buoc vao. Anh Tu va Anh Thu dang cho.",
        chapter_id="ch2",
    )

    # "Anh" occurs 3 times in translated_text but the source term occurs once --
    # count mismatch means this must NOT be auto-replaced (would corrupt "Anh Tu"/"Anh Thu").
    assert corrected == "Anh buoc vao. Anh Tu va Anh Thu dang cho."
    assert "không tự sửa được" in note


def test_extract_glossary_applies_multiple_safe_replacements_in_one_pass_not_sequentially():
    existing = [
        GlossaryEntry(term="A", translation="feline", note="", chapter_id="ch1"),
        GlossaryEntry(term="B", translation="group", note="", chapter_id="ch1"),
    ]
    node = get_node_class("ExtractGlossary")()
    provider = _ScriptedProvider(
        ["A | cat | \nB | category | ", "GIU_CU", "GIU_CU"]
    )

    updated, corrected, note = node.execute(
        provider=provider,
        glossary_entries=existing,
        source_text="I saw an A and another A. It was in a B.",
        translated_text="I saw a cat. It was in a category.",
        chapter_id="ch2",
    )

    # If applied sequentially (old buggy behavior), replacing "cat" -> "feline"
    # first would corrupt "category" (which contains "cat" as a substring)
    # into "felineegory" before the "category" -> "group" replacement ever
    # gets a chance to match. The single-pass regex (longest pattern tried
    # first at each position) must produce the correct result instead.
    #
    # source_text uses "A" twice because "cat" occurs twice in
    # translated_text (once standalone, once as the prefix of "category") --
    # the occurrence-count guard requires those two counts to match, or this
    # pair would be filtered out before ever reaching the single-pass-vs-
    # sequential code path this test exists to exercise.
    assert corrected == "I saw a feline. It was in a group."
    assert "felineegory" not in corrected


def test_evaluate_and_fix_chapters_skips_empty_retranslation_and_leaves_file_unchanged(tmp_path):
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
    provider = _ScriptedProvider(["LỖI: sai nghĩa hoàn toàn", ""])

    result = node.execute(
        workspace_name="novel-a", provider=provider, agent_instructions="Dịch."
    )

    # An empty re-translation must never overwrite the existing (correct) file.
    assert output_path.read_text(encoding="utf-8") == "Sai rồi."
    assert "ch1" in result[0]
    assert "bỏ qua" in result[0]
