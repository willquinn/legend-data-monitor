from legend_data_monitor.utils import make_dir


def test_make_dir_creates_directory(tmp_path, caplog):
    # create a new path that does not exist yet
    new_dir = tmp_path / "test_output"
    assert not new_dir.exists()
    make_dir(str(new_dir))
    assert new_dir.exists()
    assert new_dir.is_dir()

    assert "Output directory" in caplog.text
    assert "created" in caplog.text


def test_make_dir_when_directory_exists(tmp_path, caplog):
    existing_dir = tmp_path / "already_exists"
    existing_dir.mkdir()
    assert existing_dir.exists()
    make_dir(str(existing_dir))

    assert existing_dir.exists()
    assert "Output directory" in caplog.text
    assert "created" not in caplog.text  # Should not log "created"
