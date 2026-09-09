from server.node_registry import get_node_class
from server.nodes import utility  # noqa: F401  (triggers registration)


def test_load_text_file_reads_content(tmp_path):
    file_path = tmp_path / "chapter1.txt"
    file_path.write_text("hello novel", encoding="utf-8")

    node = get_node_class("LoadTextFile")()
    result = node.execute(path=str(file_path))

    assert result == ("hello novel",)


def test_save_text_file_creates_parent_dirs_and_writes(tmp_path):
    file_path = tmp_path / "out" / "chapter1.txt"

    node = get_node_class("SaveTextFile")()
    result = node.execute(text="translated text", path=str(file_path))

    assert result == ()
    assert file_path.read_text(encoding="utf-8") == "translated text"


def test_text_preview_does_not_raise():
    node = get_node_class("TextPreview")()
    assert node.execute(text="anything") == ()


def test_note_does_not_raise():
    node = get_node_class("Note")()
    assert node.execute(text="a note") == ()


def test_text_input_returns_the_pasted_text():
    node = get_node_class("TextInput")()
    result = node.execute(text="toàn bộ nội dung chương")
    assert result == ("toàn bộ nội dung chương",)
