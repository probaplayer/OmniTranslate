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
