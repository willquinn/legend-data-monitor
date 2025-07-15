from legend_data_monitor.utils import get_timestamp


def test_get_timestamp_valid_filename():
    filename = "l200-p04-r000-phy-20230421T055556Z-tier_dsp.lh5"
    expected = "20230421T055556Z"

    result = get_timestamp(filename)
    assert result == expected
