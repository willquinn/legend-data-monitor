import pandas as pd

from legend_data_monitor.save_data import save_df_and_info


def test_save_df_and_info():
    data = {
        "name": [1, 2],
        "location": [3, 4],
        "value": [10, 20],
        "other_col": [5, 6],
    }
    df = pd.DataFrame(data)

    plot_info = {"subsystem": "testvalue"}

    result = save_df_and_info(df, plot_info)

    assert f"df_{plot_info['subsystem']}" in result
    assert "plot_info" in result

    df_result = result[f"df_{plot_info['subsystem']}"]
    for col in ["name", "location"]:
        assert col not in df_result.columns

    for col in ["value", "other_col"]:
        assert col in df_result.columns

    # plot_info unchanged
    assert result["plot_info"] == plot_info
