from legend_data_monitor.utils import get_multiple_run_id


def test_get_multiple_run_id_with_run_range():
    user_time_range = {"run": ["r010", "r014"]}
    expected = "r010_r014"

    result = get_multiple_run_id(user_time_range)
    assert result == expected


def test_get_multiple_run_id_single_value():
    user_time_range = {"run": ["r010"]}
    result = get_multiple_run_id(user_time_range)
    assert result == "r010"
