import pandas as pd

from legend_data_monitor.save_data import check_level0


def test_check_level0():
    df_with_level0 = pd.DataFrame({"level_0": [1, 2, 3], "data": [4, 5, 6]})

    # df without level_0 column
    df_without_level0 = pd.DataFrame({"data": [4, 5, 6]})

    # is level_0 dropped if present?
    result = check_level0(df_with_level0)
    assert "level_0" not in result.columns
    # are other columns untouched?
    assert "data" in result.columns
    assert len(result) == len(df_with_level0)

    # df is unchanged if level_0 not present
    result = check_level0(df_without_level0)
    assert result.equals(df_without_level0)
