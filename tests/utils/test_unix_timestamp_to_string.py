import calendar
from datetime import datetime

from legend_data_monitor.utils import unix_timestamp_to_string


def test_unix_timestamp_to_string():
    dt = datetime(2023, 7, 14, 12, 34, 56)
    # convert to unix timestamp
    unix_ts = calendar.timegm(dt.timetuple())
    expected = "20230714T123456Z"

    result = unix_timestamp_to_string(unix_ts)
    assert result == expected
