from legend_data_monitor.save_data import check_existence_and_overwrite


def test_check_existence_and_overwrite(tmp_path):
    tmp_file = tmp_path / "temp_file.txt"
    tmp_file.write_text("temporary content")
    assert tmp_file.exists()

    check_existence_and_overwrite(str(tmp_file))
    # was the filer emoved?
    assert not tmp_file.exists()

    # ensure no error for non-existing file
    check_existence_and_overwrite(str(tmp_file))
