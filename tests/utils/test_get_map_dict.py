import pandas as pd

from legend_data_monitor.utils import get_map_dict


def test_get_map_dict():
    # fake location and position
    data = {"location": ["A", "A", "B", "B", "B", "C"], "position": [1, 2, 1, 3, 2, 1]}
    df = pd.DataFrame(data)

    expected = {"A": {"1": 0, "2": 1}, "B": {"1": 2, "2": 3, "3": 4}, "C": {"1": 5}}

    result = get_map_dict(df)

    assert result == expected
