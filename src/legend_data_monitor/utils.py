import logging
import os
import re

# for getting DataLoader time range
from datetime import datetime, timedelta

from .plotting import PLOT_STRUCTURE, PLOT_STYLE


def get_dataloader_timerange(**kwargs):
    """
    Available kwargs:

    dataset=
    dict with the following single field
        - 'selection' [dict]: dict with fields depending on selection options
            1) 'start': <start datetime>, 'end': <end datetime> where <datetime> input is of format 'YYYY-MM-DD [hh:mm:ss]' (everything starting from hour is optional)
            2) 'timestamps': str or list of str in format 'YYYYMMDDThhmmssZ'
            3) 'runs': int or list of ints for run number(s)
    Or enter kwargs separately start=&end=, or timestamp=, or runs=

    >>> get_dataloader_timerange(start='2022-09-28 08:00', end='2022-09-28 09:30')
    {'start': '20220928T080000Z','end': '20220928093000Z'}

    >>> get_dataloader_timerange(window='1d 5h 0m')
    {'end': '20230216T182358Z', 'start': '20230215T132358Z'}

    >>> get_dataloader_timerange(timestamps=['20220928T080000Z', '20220928093000Z'])
    ['20220928T080000Z', '20220928093000Z']
    >>> get_dataloader_timerange(timestamps='20220928T080000Z')
    ['20220928T080000Z']

    >> get_dataloader_timerange(runs=[9,10])
    ['r009', 'r010']
    >>> get_dataloader_timerange(runs=10)
    ['r010']

    >>> get_dataloader_timerange(dataset={'selection': {'start': '2022-09-28 08:00:00', 'end':'2022-09-28 09:30:00'}})
    {'start': '20220909T080000Z', 'end': '20220909T093000Z'}
    """

    # if dataset= kwarg was used, kwargs['selection'] is the dict we need
    # otherwise have start&end= or timestamps= or runs=

    # if dataset= kwarg was provided, get the 'selection' part
    # otherwise kwargs itself is already the dict we need with start= & end=; or timestamp= etc
    user_selection = kwargs["dataset"]["selection"] if "dataset" in kwargs else kwargs

    message = "Time selection mode: "

    # -------------------------------------------------------------------------
    #  in these cases, DataLoader will be called with (timestamp >= ...) and (timestamp <= ...)
    # -------------------------------------------------------------------------
    if "start" in user_selection:
        message += "time range"
        time_range = {}
        for point in ["start", "end"]:
            try:
                time_range[point] = datetime.strptime(
                    user_selection[point], "%Y-%m-%d %H:%M:%S"
                ).strftime("%Y%m%dT%H%M%SZ")
            except:
                logging.error("Invalid date format!'")
                return

    elif "window" in user_selection:
        message += "time window"
        time_range = {}
        time_range["end"] = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        try:
            days, hours, minutes = re.split(r"d|h|m", user_selection["window"])[
                :-1
            ]  # -1 for trailing ''
        except:
            logging.error("Invalid window format!")
            return

        dt = timedelta(days=int(days), hours=int(hours), minutes=int(minutes))
        time_range["start"] = (
            datetime.strptime(time_range["end"], "%Y%m%dT%H%M%SZ") - dt
        ).strftime("%Y%m%dT%H%M%SZ")

    # -------------------------------------------------------------------------
    #  in these cases, DataLoader will be called with (timestamp/run = ...) or (timestamp/run= ...)
    # -------------------------------------------------------------------------
    elif "timestamps" in user_selection:
        time_range = (
            user_selection["timestamps"]
            if isinstance(user_selection["timestamps"], list)
            else [user_selection["timestamps"]]
        )

    elif "runs" in user_selection:
        runs = (
            user_selection["runs"]
            if isinstance(user_selection["runs"], list)
            else [user_selection["runs"]]
        )
        # check validity
        for run in runs:
            if not isinstance(run, int):
                logging.error("Invalid run format!")
                return

        # format rXXX for DataLoader
        time_range = ["r" + str(run).zfill(3) for run in runs]

    else:
        logging.error("Invalid time selection!")

    return time_range


def check_plot_settings(conf: dict):
    OPTIONS = {
        "plot_structure": PLOT_STRUCTURE.keys(),
        "plot_style": PLOT_STYLE.keys(),
    }

    for subsys in conf["subsystems"]:
        for plot in conf["subsystems"][subsys]:
            # settings for this plot
            plot_settings = conf["subsystems"][subsys][plot]

            # check if all necessary fields for param settings were provided
            for field in OPTIONS:
                # if this field is not provided by user, tell them to provide it
                # (if optional to provided, will have been set with defaults before calling set_defaults())
                if not field in plot_settings:
                    logging.error(
                        f"Provide {field} in plot settings of '{plot}' for {subsys}!"
                    )
                    logging.error(
                        "Available options: {}".format(",".join(OPTIONS[field]))
                    )
                    return False

                # check if the provided option is valid
                opt = plot_settings[field]

                if not opt in OPTIONS[field]:
                    logging.error(
                        f"Option {opt} provided for {field} in plot settings of '{plot}' for {subsys} does not exist!"
                    )
                    logging.error(
                        "Available options: {}".format(",".join(OPTIONS[field]))
                    )
                    return False

            # if vs time was provided, need time window
            if (
                plot_settings["plot_style"] == "vs time"
                and not "time_window" in plot_settings
            ):
                logging.error(
                    f"You chose plot style 'vs time' and did not provide 'time_window'!"
                )
                return False

    return True


def make_output_paths(config: dict):
    """
    dict -> dict

    define output paths and create directories accordingly
    """

    print("----------------------------------------------------")
    print("--- Setting up plotting")
    print("----------------------------------------------------")

    if not "output" in config:
        logging.error('Provide output folder path in your config field "output"!')
        return

    # general output path
    try:
        make_dir(config["output"])
    except:
        logging.error(f"Cannot make output folder {config['output']}")
        logging.error("Maybe you don't have rights to create this path?")
        return

    # output subfolders
    output_paths = {}

    # sub directories
    for out_dir in ["log_files", "pdf_files", "pkl_files", "json_files"]:
        out_dir_path = os.path.join(config["output"], out_dir)
        make_dir(out_dir_path)
        # remember for later for convenience
        output_paths[out_dir] = out_dir_path

    # sub sub directories
    for out_dir in ["pdf_files", "pkl_files"]:
        for out_subdir in ["par_vs_time", "heatmaps"]:
            out_dir_path = os.path.join(config["output"], out_dir, out_subdir)
            # make dir but no need to remember
            make_dir(out_dir_path)

    return output_paths


def make_dir(dir_path):
    """Check if directory exists, and if not, make it."""
    message = "Output directory " + dir_path
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)
        message += " (created)"
    print(message)


def get_all_plot_parameters(subsystem: str, config: dict):
    """
    Get list of all parameters needed for all plots for given subsystem
    """
    all_parameters = []
    if subsystem in config["subsystems"]:
        for plot in config["subsystems"][subsystem]:
            parameters = config["subsystems"][subsystem][plot]["parameters"]
            if isinstance(parameters, str):
                all_parameters.append(parameters)
            else:
                all_parameters += parameters

    return all_parameters
