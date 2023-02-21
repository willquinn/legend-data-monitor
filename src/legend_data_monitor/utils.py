import logging
import os
import re

# for getting DataLoader time range
from datetime import datetime, timedelta

from .plot_styles import PLOT_STYLE
from .plotting import PLOT_STRUCTURE


def get_dataloader_timerange(**kwargs):
    """
    Get the time range for the specified interval.

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
            except Exception:
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
        except Exception:
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
    options = {
        "plot_structure": PLOT_STRUCTURE.keys(),
        "plot_style": PLOT_STYLE.keys(),
    }

    for subsys in conf["subsystems"]:
        for plot in conf["subsystems"][subsys]:
            # settings for this plot
            plot_settings = conf["subsystems"][subsys][plot]

            # check if all necessary fields for param settings were provided
            for field in options:
                # if this field is not provided by user, tell them to provide it
                # (if optional to provided, will have been set with defaults before calling set_defaults())
                if field not in plot_settings:
                    logging.error(
                        f"Provide {field} in plot settings of '{plot}' for {subsys}!"
                    )
                    logging.error(
                        "Available options: {}".format(",".join(options[field]))
                    )
                    return False

                # check if the provided option is valid
                opt = plot_settings[field]

                if opt not in options[field]:
                    logging.error(
                        f"Option {opt} provided for {field} in plot settings of '{plot}' for {subsys} does not exist!"
                    )
                    logging.error(
                        "Available options: {}".format(",".join(options[field]))
                    )
                    return False

            # if vs time was provided, need time window
            if (
                plot_settings["plot_style"] == "vs time"
                and "time_window" not in plot_settings
            ):
                logging.error(
                    "You chose plot style 'vs time' and did not provide 'time_window'!"
                )
                return False

    return True


def make_output_paths(config: dict):
    """
    Get a dict and return a dict. The function defines output paths and create directories accordingly.

    To use when you want a specific output structure of the following type: [...]/prod-ref/{version}/generated/plt/phy/{period}/{run}
    This does not work if you select more types (eg. both cal and phy) or timestamp intervals (but just runs).
    It can be used for run summary plots, eg during stable data taking.
    """
    logging.info("----------------------------------------------------")
    logging.info("--- Setting up plotting")
    logging.info("----------------------------------------------------")

    if "output" not in config:
        logging.error('Provide output folder path in your config field "output"!')
        return

    # general output path
    try:
        make_dir(config["output"])
    except Exception:
        logging.error(f"Cannot make output folder {config['output']}")
        logging.error("Maybe you don't have rights to create this path?")
        return

    # output subfolders
    output_paths = {}

    # create subfolders for the fixed path
    logging.info("config[output]:", config["output"])
    version_dir = config["output"] + config["dataset"]["version"] + "/"
    generated_dir = version_dir + "generated/"
    plt_dir = generated_dir + "plt/"
    # 'phy' or 'cal' if one of the two is specified; if both are specified, store data in 'cal_phy/'
    if isinstance(config["dataset"]["type"], list):
        type_dir = plt_dir + "cal_phy" + "/"
    else:
        type_dir = plt_dir + config["dataset"]["type"] + "/"
    period_dir = type_dir + config["dataset"]["period"] + "/"
    output_paths = (
        period_dir + "r" + str(config["dataset"]["selection"]["runs"]).zfill(3) + "/"
    )

    make_dir(version_dir)
    make_dir(generated_dir)
    make_dir(plt_dir)
    make_dir(type_dir)
    make_dir(period_dir)
    make_dir(output_paths)

    logging.info("output_paths:", output_paths)
    return output_paths


def make_dir(dir_path):
    """Check if directory exists, and if not, make it."""
    message = "Output directory " + dir_path
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)
        message += " (created)"
    logging.info(message)


def get_all_plot_parameters(subsystem: str, config: dict):
    """Get list of all parameters needed for all plots for given subsystem."""
    all_parameters = []
    if subsystem in config["subsystems"]:
        for plot in config["subsystems"][subsystem]:
            parameters = config["subsystems"][subsystem][plot]["parameters"]
            if isinstance(parameters, str):
                all_parameters.append(parameters)
            else:
                all_parameters += parameters

    return all_parameters
