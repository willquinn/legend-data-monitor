import glob
import importlib.resources
import json
import logging
import os
import re

# for getting DataLoader time range
from datetime import datetime, timedelta

# -------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# stream handler (console)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)

# format
formatter = logging.Formatter("%(asctime)s:  %(message)s")
stream_handler.setFormatter(formatter)
# file_handler.setFormatter(formatter)

# add to logger
logger.addHandler(stream_handler)

# -------------------------------------------------------------------------

pkg = importlib.resources.files("legend_data_monitor")

# load dictionary with plot info (= units, thresholds, label, ...)
with open(pkg / "settings" / "par-settings.json") as f:
    PLOT_INFO = json.load(f)

# which parameter belongs to which tier
with open(pkg / "settings" / "parameter-tiers.json") as f:
    PARAMETER_TIERS = json.load(f)

# which lh5 parameters are needed to be loaded from lh5 to calculate them
with open(pkg / "settings" / "special-parameters.json") as f:
    SPECIAL_PARAMETERS = json.load(f)

# convert all to lists for convenience
for param in SPECIAL_PARAMETERS:
    if isinstance(SPECIAL_PARAMETERS[param], str):
        SPECIAL_PARAMETERS[param] = [SPECIAL_PARAMETERS[param]]

# -------------------------------------------------------------------------
# Subsystem related functions (for getting channel map & status)
# -------------------------------------------------------------------------


def get_query_times(**kwargs):
    """
    Get time ranges for DataLoader query from user input, as well as first timestamp for channel map/status query.

    Available kwargs:

    Available kwargs:
    dataset=
        dict with the following keys:
            - 'path' [str]: < move description here from get_data() >
            - 'version' [str]: < move description here from get_data() >
            - 'type' [str]: < move description here > ! not possible for multiple types now!
            - the following keys depending in time selection mode (choose one)
                1) 'start' : <start datetime>, 'end': <end datetime> where <datetime> input is of format 'YYYY-MM-DD hh:mm:ss'
                2) 'window'[str]: time window in the past from current time point, format: 'Xd Xh Xm' for days, hours, minutes
                2) 'timestamps': str or list of str in format 'YYYYMMDDThhmmssZ'
                3) 'runs': int or list of ints for run number(s)  e.g. 10 for r010
    Or input kwargs separately path=, ...; start=&end=, or window=, or timestamps=, or runs=

    Designed in such a way to accommodate Subsystem init kwargs. A bit cumbersome and can probably be done better.

    Path, version, and type only needed because channel map and status cannot be queried by run directly,
        so we need these to look up first timestamp in data path to run.

    >>> get_query_times(..., start='2022-09-28 08:00:00', end='2022-09-28 09:30:00')
    {'timestamp': {'start': '20220928T080000Z', 'end': '20220928T093000Z'}}, '20220928T080000Z'

    >> get_query_times(..., runs=27)
    ({'run': ['r027']}, '20220928T091135Z')
    """
    # get time range query for DataLoader
    timerange = get_query_timerange(**kwargs)

    first_timestamp = ""
    # get first timestamp in case keyword is timestamp
    if "timestamp" in timerange:
        if "start" in timerange["timestamp"]:
            first_timestamp = timerange["timestamp"]["start"]
        else:
            first_timestamp = min(timerange["timestamp"])
    # look in path to find first timestamp if keyword is run
    else:
        # currently only list of runs and not 'start' and 'end', so always list
        # find earliest run, format rXXX
        first_run = min(timerange["run"])

        # --- get dsp filelist of this run
        # if setup= keyword was used, get dict; otherwise kwargs is already the dict we need
        path_info = kwargs["dataset"] if "dataset" in kwargs else kwargs

        # format to search /path/to/prod-ref/v06.00/generated/tier/**/phy/**/r027
        glob_path = os.path.join(
            path_info["path"],
            path_info["version"],
            "generated",
            "tier",
            "**",
            path_info["type"],
            "**",
            first_run,
            "*.lh5",
        )
        dsp_files = glob.glob(glob_path)
        # find earliest
        dsp_files.sort()
        first_file = dsp_files[0]
        # extract timestamp
        first_timestamp = get_key(first_file)

    return timerange, first_timestamp


def get_query_timerange(**kwargs):
    """
    Get DataLoader compatible time range.

    Available kwargs:

    dataset=
        dict with the following keys depending in time selection mode (choose one)
            1) 'start' : <start datetime>, 'end': <end datetime> where <datetime> input is of format 'YYYY-MM-DD hh:mm:ss'
            2) 'window'[str]: time window in the past from current time point, format: 'Xd Xh Xm' for days, hours, minutes
            2) 'timestamps': str or list of str in format 'YYYYMMDDThhmmssZ'
            3) 'runs': int or list of ints for run number(s)  e.g. 10 for r010
    Or enter kwargs separately start=&end=, or window=, or timestamp=, or runs=

    Designed in such a way to accommodate Subsystem init kwargs. A bit cumbersome and can probably be done better.

    >>> get_query_timerange(start='2022-09-28 08:00:00', end='2022-09-28 09:30:00')
    {'timestamp': {'start': '20220928T080000Z', 'end': '20220928T093000Z'}}

    >>> get_query_timerange(window='1d 5h 0m')
    {'timestamp': {'end': '20230220T114337Z', 'start': '20230219T064337Z'}}

    >>> get_query_timerange(timestamps=['20220928T080000Z', '20220928093000Z'])
    {'timestamp': ['20220928T080000Z', '20220928093000Z']}
    >>> get_query_timerange(timestamps='20220928T080000Z')
    {'timestamp': ['20220928T080000Z']}

    >> get_query_timerange(runs=[9,10])
    {'run': ['r009', 'r010']}
    >>> get_query_timerange(runs=10)
    {'run': ['r010']}

    >>> get_query_timerange(dataset={'start': '2022-09-28 08:00:00', 'end':'2022-09-28 09:30:00'})
    {'timestamp': {'start': '20220928T080000Z', 'end': '20220928T093000Z'}}
    """
    # if dataset= kwarg was provided, get the 'selection' part
    # otherwise kwargs itself is already the dict we need with start= & end=; or timestamp= etc
    user_selection = kwargs["dataset"] if "dataset" in kwargs else kwargs

    # -------------------------------------------------------------------------
    #  in these cases, DataLoader will be called with (timestamp >= ...) and (timestamp <= ...)
    # -------------------------------------------------------------------------
    if "start" in user_selection:
        time_range = {"timestamp": {}}
        for point in ["start", "end"]:
            try:
                time_range["timestamp"][point] = datetime.strptime(
                    user_selection[point], "%Y-%m-%d %H:%M:%S"
                ).strftime("%Y%m%dT%H%M%SZ")
            except ValueError:
                logger.error("\033[91mInvalid date format!\033[0m")
                return

    elif "window" in user_selection:
        time_range = {"timestamp": {}}
        time_range["timestamp"]["end"] = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        try:
            days, hours, minutes = re.split(r"d|h|m", user_selection["window"])[
                :-1
            ]  # -1 for trailing ''
        except ValueError:
            logger.error("\033[91mInvalid window format!\033[0m")
            return

        dt = timedelta(days=int(days), hours=int(hours), minutes=int(minutes))
        time_range["timestamp"]["start"] = (
            datetime.strptime(time_range["timestamp"]["end"], "%Y%m%dT%H%M%SZ") - dt
        ).strftime("%Y%m%dT%H%M%SZ")

    # -------------------------------------------------------------------------
    #  in these cases, DataLoader will be called with (timestamp/run == ...) or (timestamp/run == ...)
    # -------------------------------------------------------------------------
    elif "timestamps" in user_selection:
        time_range = {"timestamp": []}
        time_range["timestamp"] = (
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
                logger.error("\033[91mInvalid run format!\033[0m")
                return

        # format rXXX for DataLoader
        time_range = {"run": []}
        time_range["run"] = ["r" + str(run).zfill(3) for run in runs]

    else:
        logger.error("\033[91mInvalid time selection!\033[0m")
        return

    return time_range


# -------------------------------------------------------------------------
# Plotting related functions
# -------------------------------------------------------------------------


def check_plot_settings(conf: dict):
    from . import plot_styles, plotting

    options = {
        "plot_structure": plotting.PLOT_STRUCTURE.keys(),
        "plot_style": plot_styles.PLOT_STYLE.keys(),
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
                    logger.error(
                        f"\033[91mProvide {field} in plot settings of '{plot}' for {subsys}!\033[0m"
                    )
                    logger.error(
                        "\033[91mAvailable options: {}\033[0m".format(
                            ",".join(options[field])
                        )
                    )
                    return False

                # check if the provided option is valid
                opt = plot_settings[field]

                if opt not in options[field]:
                    logger.error(
                        f"\033[91mOption {opt} provided for {field} in plot settings of '{plot}' for {subsys} does not exist!\033[0m"
                    )
                    logger.error(
                        "\033[91mAvailable options: {}\033[0m".format(
                            ",".join(options[field])
                        )
                    )
                    return False

            # if vs time was provided, need time window
            if (
                plot_settings["plot_style"] == "vs time"
                and "time_window" not in plot_settings
            ):
                logger.error(
                    "\033[91mYou chose plot style 'vs time' and did not provide 'time_window'!\033[0m"
                )
                return False

    return True


def make_output_paths(config: dict, user_time_range: dict) -> str:
    """
    Get a dict and return a dict. The function defines output paths and create directories accordingly.

    To use when you want a specific output structure of the following type: [...]/prod-ref/{version}/generated/plt/phy/{period}/{run}
    This does not work if you select more types (eg. both cal and phy) or timestamp intervals (but just runs).
    It can be used for run summary plots, eg during stable data taking.
    """
    logger.info("Setting up plotting...")

    if "output" not in config:
        logger.error(
            "\033[91mProvide output folder path in your config field 'output'!\033[0m"
        )
        return

    # general output path
    try:
        make_dir(config["output"])
    except Exception:
        logger.error(f"\033[91mCannot make output folder {config['output']}\033[0m")
        logger.error("\033[91mMaybe you don't have rights to create this path?\033[0m")
        return

    # output subfolders
    output_paths = {}

    # create subfolders for the fixed path
    logger.info("config[output]:" + config["output"])
    version_dir = config["output"] + "/" + config["dataset"]["version"] + "/"
    generated_dir = version_dir + "generated/"
    plt_dir = generated_dir + "plt/"
    # 'phy' or 'cal' if one of the two is specified; if both are specified, store data in 'cal_phy/'
    if isinstance(config["dataset"]["type"], list):
        type_dir = plt_dir + "cal_phy" + "/"
    else:
        type_dir = plt_dir + config["dataset"]["type"] + "/"
    # period info
    period_dir = type_dir + config["dataset"]["period"] + "/"

    # careful handling of folder name depending on the selected time range. The possibilities are:
    #   1) user_time_range = {'timestamp': {'start': '20220928T080000Z', 'end': '20220928T093000Z'}} => start + end
    #           -> folder: 20220928T080000Z_20220928T093000Z/
    #   2) user_time_range = {'timestamp': ['20230207T103123Z']} => one key
    #           -> folder: 20230207T103123Z/
    #   3) user_time_range = {'timestamp': ['20230207T103123Z', '20230207T141123Z', '20230207T083323Z']} => multiple keys
    #           -> get min/max and use in the folder name
    #           -> folder: 20230207T083323Z_20230207T141123Z/
    #   4) user_time_range = {'run': ['r010']} => one run
    #           -> folder: r010/
    #   5) user_time_range = {'run': ['r010', 'r014']} => multiple runs
    #           -> folder: r010_r014/
    name_time = get_time_name(user_time_range)

    output_paths = period_dir + name_time + "/"

    make_dir(version_dir)
    make_dir(generated_dir)
    make_dir(plt_dir)
    make_dir(type_dir)
    make_dir(period_dir)
    make_dir(output_paths)

    return output_paths


def make_dir(dir_path):
    """Check if directory exists, and if not, make it."""
    message = "Output directory " + dir_path
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)
        message += " (created)"
    logger.info(message)


def get_time_name(user_time_range: dict) -> str:
    """Get a name for each available time selection."""
    name_time = ""
    if "timestamp" in user_time_range.keys():
        time_range = list(user_time_range.values())[0]
        if "start" in time_range:
            name_time += time_range["start"] + "_" + time_range["end"]
        else:
            if len(time_range) == 1:
                name_time += time_range[0]
            else:
                timestamp_range = [
                    datetime.strptime(string, "%Y%m%dT%H%M%SZ").timestamp()
                    for string in time_range
                ]
                min_idx = timestamp_range.index(min(timestamp_range))
                max_idx = timestamp_range.index(max(timestamp_range))
                name_time += time_range[min_idx] + "_" + time_range[max_idx]

    elif "run" in user_time_range.keys():
        time_range = list(user_time_range.values())[0]
        name_time += "{}".format("_".join(time_range))

    else:
        logger.error("\033[91mInvalid time selection!\033[0m")
        return

    return name_time


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

            # check if there is any QC entry; if so, add it to the list of parameters to load
            if "quality_cuts" in config["subsystems"][subsystem][plot]:
                all_parameters.append(
                    config["subsystems"][subsystem][plot]["quality_cuts"]
                )

    return all_parameters


def get_key(dsp_fname: str) -> str:
    """Extract key from lh5 filename."""
    return re.search(r"-\d{8}T\d{6}Z", dsp_fname).group(0)[1:]
