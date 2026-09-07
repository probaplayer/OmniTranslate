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
