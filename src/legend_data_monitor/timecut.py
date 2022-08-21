import logging
import sys
from datetime import datetime, timedelta

import numpy as np


def build_timecut_list(time_window: list, last_hours: list):
    """
    Build list with time cut values.

    Description
    -----------
    If a time cut is enabled, the function returns
    a list with info (dates/times) about the time cut.

    Parameters
    ----------
    time_window
                  List with info about the 'time_window' cut
    last_hours
                  List with info about the 'last_hours' cut
    """
    time_cut = []
    if time_window["enabled"] is True:
        time_cut.append(time_window["start_date"])  # start date
        time_cut.append(time_window["start_hour"])  # start hour
        time_cut.append(time_window["end_date"])  # end date
        time_cut.append(time_window["end_hour"])  # end hour
    else:
        if last_hours["enabled"] is True:
            time_cut.append(last_hours["prod_time"]["days"])  # days
            time_cut.append(last_hours["prod_time"]["hours"])  # hours
            time_cut.append(last_hours["prod_time"]["minutes"])  # minutes

    if time_window["enabled"] is True and last_hours["enabled"] is True:
        logging.info(
            'Both "time_window" and "last_hours" are enabled. You must enable just one of the two analysis!'
        )
        sys.exit(1)

    return time_cut


def time_dates(time_cut: list):
    """
    Return start/end time of cuts in UTC+00:00 format.

    Parameters
    ----------
    time_cut
               List with info about time cuts
    """
    if len(time_cut) == 4:
        start_date = time_cut[0].split("/")
        start_time = time_cut[1].split(":")
        end_date = time_cut[2].split("/")
        end_time = time_cut[3].split(":")
        start = (
            start_date[2]
            + start_date[1]
            + start_date[0]
            + "T"
            + start_time[0]
            + start_time[1]
            + start_time[2]
            + "Z"
        )
        end = (
            end_date[2]
            + end_date[1]
            + end_date[0]
            + "T"
            + end_time[0]
            + end_time[1]
            + end_time[2]
            + "Z"
        )
    if len(time_cut) == 3:
        end = datetime.now().strftime("%Y%m%dT&H%M%SZ")
        start = (
            datetime.now()
            - timedelta(days=time_cut[0], hours=time_cut[1], minutes=time_cut[2])
        ).strftime("%Y%m%dT%H%M%SZ")

    return start, end


def min_timestamp_thr(timestamp: list, prod_time: list):
    """
    Return the first timestamp within the selected time window after the time cut.

    Parameters
    ----------
    timestamp
                Timestamps evaluated in seconds
    prod_time
                List with info about time cuts
    """
    thr_timestamp = (
        datetime.now()
        - timedelta(days=prod_time[0], hours=prod_time[1], minutes=prod_time[2])
    ).timestamp()
    start_t = 0
    for t in timestamp:
        if t < thr_timestamp:
            continue
        if t > thr_timestamp:
            start_t = t
            break
    return timestamp.index(start_t)


def cut_array_below_min(val_array: np.ndarray, start_index: int):
    """
    Cut an array above a given index.

    Parameters
    ----------
    val_array
                 Array filled with values of a given parameter
    start_index
                 Starting index
    """
    val_list = val_array.tolist()
    val_list = val_list[start_index:]
    val_array = []
    val_array = np.array(val_list)
    return val_array


def date_string_formatting(date):
    date = date.split("/")[2] + date.split("/")[1] + date.split("/")[0]
    return date


def hour_string_formatting(hour):
    hour = hour.split(":")[0] + hour.split(":")[1] + hour.split(":")[2]
    return hour


def cut_min_max_filelist(runs: list[str], time_cut: list[str]):
    """
    Select files for analysis in a specified time interval using file name.

    Parameters
    ----------
    runs
                list of all files for a given run
    time_cut
                list with day and hour for timecut as strings
    """
    day = np.array([((run.split("-")[4]).split("Z")[0]).split("T")[0] for run in runs])
    hour = np.array([((run.split("-")[4]).split("Z")[0]).split("T")[1] for run in runs])
    day = np.core.defchararray.add(day, hour)
    day = np.array([int(single_day) for single_day in day])

    timecut_low = int(
        date_string_formatting(time_cut[0]) + hour_string_formatting(time_cut[1])
    )
    timecut_high = int(
        date_string_formatting(time_cut[2]) + hour_string_formatting(time_cut[3])
    )

    lowcut_list = np.where(day > timecut_low)[0]
    highcut_list = np.where(day < timecut_high)[0]

    if len(lowcut_list) == 0 or len(highcut_list) == 0:
        logging.info("No entries in the selected time window, retry!")
        sys.exit(1)

    files_index = np.arange(lowcut_list[0], highcut_list[-1] + 1, 1)
    runs = np.array(runs)

    return runs[files_index]


def cut_below_threshold_filelist(runs: list[str], time_cut: list[str]):
    """
    Select files for analysis below time threshold using file name.

    Parameters
    ----------
    runs
                list of all files for a given run
    time_cut
                list with day and hour for timecut as strings
    """
    day = np.array([((run.split("-")[4]).split("Z")[0]).split("T")[0] for run in runs])
    hour = np.array([((run.split("-")[4]).split("Z")[0]).split("T")[1] for run in runs])
    day = np.core.defchararray.add(day, hour)
    day = np.array([int(single_day) for single_day in day])

    time_difference = datetime.now() - timedelta(
        days=time_cut[0], hours=time_cut[1], minutes=time_cut[2]
    )
    threshold_lowcut = int(
        time_difference.date().strftime("%Y%m%d")
        + time_difference.time().strftime("%H%M%S")
    )
    threshold_highcut = int(
        datetime.now().date().strftime("%Y%m%d")
        + datetime.now().time().strftime("%H%M%S")
    )

    lowcut_list = np.where(day > threshold_lowcut)[0]
    highcut_list = np.where(day < threshold_highcut)[0]

    if len(lowcut_list) == 0:
        logging.info("No entries in the selected time window, retry!")
        sys.exit(1)

    files_index = np.arange(lowcut_list[0] - 1, highcut_list[-1], 1)
    runs = np.array(runs)

    return runs[files_index]


def min_max_timestamp_thr(timestamp: list, start_time: str, end_time: str):
    """
    Return the first and last timestamps within the selected time window after the time cut.

    Parameters
    ----------
    timestamp
                Timestamps evaluated in seconds
    start_time
                Start time to include events (in %d/%m/%Y %H:%M:%S format)
    end_time
                End time to include events (in %d/%m/%Y %H:%M:%S format)
    """
    start_timestamp = (datetime.strptime(start_time, "%d/%m/%Y %H:%M:%S")).timestamp()
    end_timestamp = (datetime.strptime(end_time, "%d/%m/%Y %H:%M:%S")).timestamp()

    start_t = 0
    for t in timestamp:
        if t < start_timestamp or t > end_timestamp:
            continue
        if t > start_timestamp:
            start_t = t
            break
    end_t = 0
    for t in timestamp:
        if t > start_timestamp:
            if timestamp[-1] < end_timestamp:
                end_t = timestamp[-1]
            if timestamp[-1] > end_timestamp:
                if t > end_timestamp:
                    end_t = t
                    break

    start_index = np.nan
    end_index = np.nan
    if start_t in timestamp:
        start_index = timestamp.index(start_t)
    if end_t in timestamp:
        end_index = timestamp.index(end_t)
    return start_index, end_index


def cut_array_in_min_max(
    val_array: np.ndarray, start_index: int, end_index: int
) -> np.ndarray:
    """
    Cut an array within two indices.

    Parameters
    ----------
    val_array
                 Array filled with values of a given parameter
    start_index
                 Starting index
    end_index
                 Ending index
    """
    val_list = val_array.tolist()
    if end_index == len(val_array) - 1:
        val_list = val_list[start_index:]
    else:
        val_list = val_list[start_index:end_index]
    val_array = []
    val_array = np.array(val_list)

    return val_array
