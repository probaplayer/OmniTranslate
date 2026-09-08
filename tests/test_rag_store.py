import pytest

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


@pytest.mark.parametrize("bad_value", [None, 123, ["a"]])
def test_add_chapter_rejects_non_string_translated_text(tmp_path, bad_value):
    store = RAGStore(persist_directory=tmp_path / "rag_index")

    with pytest.raises(TypeError, match="translated_text must be a str"):
        store.add_chapter(chapter_id="ch1", source_text="src", translated_text=bad_value)

    # Nothing was written.
    assert store.query("src", top_k=1) == []


def test_query_tolerates_preexisting_row_with_dropped_metadata(tmp_path):
    """A row written before the add_chapter guard existed must not break the query.

    chromadb silently drops the whole metadata dict when a value is not a
    primitive, so such a row reads back with metadata None. It must degrade to
    an empty translated_text rather than crash every chapter in the result set.
    """
    store = RAGStore(persist_directory=tmp_path / "rag_index")

    # Bypass add_chapter's guard to reproduce the legacy corrupted row exactly.
    store._collection.upsert(
        ids=["corrupt"],
        documents=["a corrupted chapter about knights and dragons"],
        metadatas=[{"translated_text": None}],
    )
    store.add_chapter(
        chapter_id="healthy",
        source_text="a healthy chapter about knights and dragons",
        translated_text="bản dịch lành",
    )

    results = store.query("knights and dragons", top_k=2)

    by_id = {example.chapter_id: example for example in results}
    assert by_id["corrupt"].translated_text == ""
    # The healthy chapter ranking alongside it is unaffected.
    assert by_id["healthy"].translated_text == "bản dịch lành"


@pytest.mark.parametrize("top_k", [0, -1])
def test_query_with_non_positive_top_k_returns_empty_list(tmp_path, top_k):
    store = RAGStore(persist_directory=tmp_path / "rag_index")
    store.add_chapter(chapter_id="ch1", source_text="some source", translated_text="bản dịch")

    assert store.query("some source", top_k=top_k) == []
