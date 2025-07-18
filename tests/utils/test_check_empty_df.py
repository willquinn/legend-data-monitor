import pandas as pd

from legend_data_monitor.utils import check_empty_df


# mock/import the AnalysisData class
class MockAnalysisData:
    def __init__(self, data):
        self.data = data


def test_check_empty_df():
    # pandas DataFrame
    empty_df = pd.DataFrame()
    non_empty_df = pd.DataFrame({"a": [1, 2]})
    assert check_empty_df(empty_df) is True
    assert check_empty_df(non_empty_df) is False

    # AnalysisData object
    empty_analysis = MockAnalysisData(pd.DataFrame())
    non_empty_analysis = MockAnalysisData(pd.DataFrame({"a": [1]}))
    assert check_empty_df(empty_analysis) is True
    assert check_empty_df(non_empty_analysis) is False
