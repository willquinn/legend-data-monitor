import glob
import importlib.resources
import json
import logging
import os
import re
import shelve
import sys

# for getting DataLoader time range
from datetime import datetime, timedelta

import pygama.lgdo.lh5_store as lh5
from pandas import DataFrame, concat

# -------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# stream handler (console)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)

# format
formatter = logging.Formatter("%(asctime)s:  %(message)s")
stream_handler.setFormatter(formatter)

# add to logger
logger.addHandler(stream_handler)

# ------------------------------------------------------------------------- SOME DICTIONARIES LOADING/DEFINITION

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

# load SC params and corresponding flags to get specific parameters from big dfs that are stored in the database
with open(pkg / "settings" / "SC-params.json") as f:
    SC_PARAMETERS = json.load(f)

# load list of columns to load for a dataframe
COLUMNS_TO_LOAD = [
    "name",
    "location",
    "channel",
    "position",
    "cc4_id",
    "cc4_channel",
    "daq_crate",
    "daq_card",
    "HV_card",
    "HV_channel",
    "det_type",
]

# dictionary map (helpful when we want to map channels based on their location/position)
with open(pkg / "settings" / "map-channels.json") as f:
    MAP_DICT = json.load(f)

# dictionary with timestamps to remove for specific channels
with open(pkg / "settings" / "remove-keys.json") as f:
    REMOVE_KEYS = json.load(f)

# dictionary with detectors to remove
with open(pkg / "settings" / "remove-dets.json") as f:
    REMOVE_DETS = json.load(f)

# -------------------------------------------------------------------------
# Subsystem related functions (for getting channel map & status)
# -------------------------------------------------------------------------


def get_query_times(**kwargs):
    """
    Get time ranges for DataLoader query from user input, as well as first/last timestamp for channel map / status / SC query.

    Available kwargs:

    Available kwargs:
    dataset=
        dict with the following keys:
            - 'path' [str]: < move description here from get_data() >
            - 'version' [str]: < move description here from get_data() >
            - 'type' [str]: < move description here > ! not possible for multiple types now!
            - the following keys depending in time selection mode (choose one)
                1. 'start' : <start datetime>, 'end': <end datetime> where <datetime> input is of format 'YYYY-MM-DD hh:mm:ss'
                2. 'window'[str]: time window in the past from current time point, format: 'Xd Xh Xm' for days, hours, minutes
                2. 'timestamps': str or list of str in format 'YYYYMMDDThhmmssZ'
                3. 'runs': int or list of ints for run number(s)  e.g. 10 for r010
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
    # get first/last timestamp in case keyword is timestamp
    if "timestamp" in timerange:
        if "start" in timerange["timestamp"]:
            first_timestamp = timerange["timestamp"]["start"]
        if "end" in timerange["timestamp"]:
            last_timestamp = timerange["timestamp"]["end"]
        if (
            "start" not in timerange["timestamp"]
            and "end" not in timerange["timestamp"]
        ):
            first_timestamp = min(timerange["timestamp"])
            last_timestamp = max(timerange["timestamp"])
    # look in path to find first timestamp if keyword is run
    else:
        # currently only list of runs and not 'start' and 'end', so always list
        # find earliest/latest run, format rXXX
        first_run = min(timerange["run"])
        last_run = max(timerange["run"])

        # --- get dsp filelist of this run
        # if setup= keyword was used, get dict; otherwise kwargs is already the dict we need
        path_info = kwargs["dataset"] if "dataset" in kwargs else kwargs

        # format to search /path_to_prod-ref[/vXX.XX]/generated/tier/dsp/phy/pXX/rXXX (version 'vXX.XX' might not be there).
        # NOTICE that we fixed the tier, otherwise it picks the last one it finds (eg tcm).
        # NOTICE that this is PERIOD SPECIFIC (unlikely we're gonna inspect two periods together, so we fix it)
        first_glob_path = os.path.join(
            path_info["path"],
            path_info["version"],
            "generated",
            "tier",
            "dsp",
            path_info["type"],
            path_info["period"],
            first_run,
            "*.lh5",
        )
        last_glob_path = os.path.join(
            path_info["path"],
            path_info["version"],
            "generated",
            "tier",
            "dsp",
            path_info["type"],
            path_info["period"],
            last_run,
            "*.lh5",
        )
        first_dsp_files = glob.glob(first_glob_path)
        last_dsp_files = glob.glob(last_glob_path)
        # find earliest
        first_dsp_files.sort()
        first_file = first_dsp_files[0]
        # find latest
        last_dsp_files.sort()
        last_file = last_dsp_files[-1]
        # extract timestamps
        first_timestamp = get_key(first_file)
        # last timestamp is not the key of last file: it's the last timestamp saved in the last file
        last_timestamp = get_last_timestamp(
            last_file
        )

    return timerange, first_timestamp, last_timestamp


def get_query_timerange(**kwargs):
    """
    Get DataLoader compatible time range.

    Available kwargs:

    dataset=
        dict with the following keys depending in time selection mode (choose one)
            1. 'start' : <start datetime>, 'end': <end datetime> where <datetime> input is of format 'YYYY-MM-DD hh:mm:ss'
            2. 'window'[str]: time window in the past from current time point, format: 'Xd Xh Xm' for days, hours, minutes
            2. 'timestamps': str or list of str in format 'YYYYMMDDThhmmssZ'
            3. 'runs': int or list of ints for run number(s)  e.g. 10 for r010
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
        logger.error(
            "\033[91mInvalid time selection. Choose among: runs, timestamps, window, start+end - try again!\033[0m"
        )
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

            # ----------------------------------------------------------------------------------------------
            # general check
            # ----------------------------------------------------------------------------------------------
            # check if all necessary fields for param settings were provided
            for field in options:
                # when plot_structure is summary, plot_style is not needed...
                # ToDo: neater way to skip the whole loop but still do special checks; break? ugly...
                # future ToDo: exposure can be plotted in various plot styles e.g. string viz, or plot array, will change
                if plot_settings["parameters"] == "exposure":
                    continue

                # ...otherwise, it is required
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

            # ----------------------------------------------------------------------------------------------
            # special checks
            # ----------------------------------------------------------------------------------------------

            # exposure check
            if plot_settings["parameters"] == "exposure" and (
                plot_settings["event_type"] not in ["pulser", "all"]
            ):
                logger.error(
                    "\033[91mPulser events are needed to calculate livetime/exposure; choose 'pulser' or 'all' event type\033[0m"
                )
                return False

            # ToDo: neater way to skip the whole loop but still do special checks; break? ugly...
            if plot_settings["parameters"] == "exposure":
                continue

            # other non-exposure checks

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

    # create subfolders for the fixed path
    logger.info("config[output]:" + config["output"])
    version_dir = os.path.join(config["output"], config["dataset"]["version"])
    generated_dir = os.path.join(version_dir, "generated")
    plt_dir = os.path.join(generated_dir, "plt")
    # 'phy' or 'cal' if one of the two is specified; if both are specified, store data in 'cal_phy/'
    if isinstance(config["dataset"]["type"], list):
        type_dir = os.path.join(plt_dir, "cal_phy")
    else:
        type_dir = os.path.join(plt_dir, config["dataset"]["type"])
    # period info
    period_dir = os.path.join(type_dir, config["dataset"]["period"]) + "/"

    # output subfolders
    make_dir(version_dir)
    make_dir(generated_dir)
    make_dir(plt_dir)
    make_dir(type_dir)
    make_dir(period_dir)

    return period_dir


def make_dir(dir_path):
    """Check if directory exists, and if not, make it."""
    message = "Output directory " + dir_path
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)
        message += " (created)"
    logger.info(message)


def get_multiple_run_id(user_time_range: dict) -> str:
    time_range = list(user_time_range.values())[0]
    name_time = "{}".format("_".join(time_range))
    return name_time


def get_time_name(user_time_range: dict) -> str:
    """Get a name for each available time selection.

    careful handling of folder name depending on the selected time range. The possibilities are:
      1. user_time_range = {'timestamp': {'start': '20220928T080000Z', 'end': '20220928T093000Z'}} => start + end
              -> folder: 20220928T080000Z_20220928T093000Z/
      2. user_time_range = {'timestamp': ['20230207T103123Z']} => one key
              -> folder: 20230207T103123Z/
      3. user_time_range = {'timestamp': ['20230207T103123Z', '20230207T141123Z', '20230207T083323Z']} => multiple keys
              -> get min/max and use in the folder name
              -> folder: 20230207T083323Z_20230207T141123Z/
      4. user_time_range = {'run': ['r010']} => one run
              -> folder: r010/
      5. user_time_range = {'run': ['r010', 'r014']} => multiple runs
              -> folder: r010_r014/
    """
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
        name_time = get_multiple_run_id(user_time_range)

    else:
        logger.error("\033[91mInvalid time selection!\033[0m")
        return

    return name_time


def get_timestamp(filename):
    """Get the timestamp from a filename. For instance, if file='l200-p04-r000-phy-20230421T055556Z-tier_dsp.lh5', then it returns '20230421T055556Z'."""
    # Assumes that the timestamp is in the format YYYYMMDDTHHMMSSZ
    return filename.split("-")[-2]


def get_run_name(config, user_time_range: dict) -> str:
    """Get the run ID given start/end timestamps."""
    # this is the root directory to search in the timestamps
    main_folder = os.path.join(
        config["dataset"]["path"], config["dataset"]["version"], "generated/tier"
    )

    # start/end timestamps of the selected time range of interest
    # if range was given, will have keywords "start" and "end"
    if "start" in user_time_range["timestamp"]:
        start_timestamp = user_time_range["timestamp"]["start"]
        end_timestamp = user_time_range["timestamp"]["end"]
    # if list of timestamps was given (may be not consecutive or in order), it's just a list
    else:
        start_timestamp = min(user_time_range["timestamp"])
        end_timestamp = max(user_time_range["timestamp"])

    run_list = []  # this will be updated with the run ID

    # start to look for timestamps inside subfolders
    def search_for_timestamp(folder):
        run_id = ""
        for subfolder in os.listdir(folder):
            subfolder_path = os.path.join(folder, subfolder)
            if os.path.isdir(subfolder_path):
                files = sorted(glob.glob(os.path.join(subfolder_path, "*")))
                for i, file in enumerate(files):
                    if (
                        get_timestamp(files[i - 1])
                        <= start_timestamp
                        <= get_timestamp(file)
                    ) or (
                        get_timestamp(files[i - 1])
                        <= end_timestamp
                        <= get_timestamp(file)
                    ):
                        run_id = file.split("/")[-2]
                        run_list.append(run_id)
                        break

                if len(run_list) == 0:
                    search_for_timestamp(subfolder_path)
                else:
                    break
        return

    search_for_timestamp(main_folder)

    if len(run_list) == 0:
        logger.error(
            "\033[91mThe selected timestamps were not find anywhere. Try again with another time range!\033[0m"
        )
        sys.exit()
    if len(run_list) > 1:
        return get_multiple_run_id(user_time_range)

    return run_list[0]


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

            # check if event type asked needs a special parameter (K lines need energy)
            event_type = config["subsystems"][subsystem][plot]["event_type"]
            if event_type in SPECIAL_PARAMETERS:
                all_parameters += SPECIAL_PARAMETERS[event_type]

            # check if there is any QC entry; if so, add it to the list of parameters to load
            if "cuts" in config["subsystems"][subsystem][plot]:
                cuts = config["subsystems"][subsystem][plot]["cuts"]
                # convert to list for convenience
                if isinstance(cuts, str):
                    cuts = [cuts]
                for cut in cuts:
                    # append original name of the cut to load (remove the "not" ~ symbol if present)
                    if cut[0] == "~":
                        cut = cut[1:]
                    all_parameters.append(cut)

    return all_parameters


def get_key(dsp_fname: str) -> str:
    """Extract key from lh5 filename."""
    return re.search(r"-\d{8}T\d{6}Z", dsp_fname).group(0)[1:]


def unix_timestamp_to_string(unix_timestamp):
    """Convert a Unix timestamp to a string in the format 'YYYYMMDDTHHMMSSZ' with the timezone indicating UTC+00."""
    utc_datetime = datetime.utcfromtimestamp(unix_timestamp)
    formatted_string = utc_datetime.strftime("%Y%m%dT%H%M%SZ")
    return formatted_string


def get_last_timestamp(dsp_fname: str) -> str:
    """Read a lh5 file and return the last timestamp saved in the file. This works only in case of a global trigger where the whole array is entirely recorded for a given timestamp."""
    # pick a random channel
    first_channel = lh5.ls(dsp_fname, "")[0]
    # get array of timestamps stored in the lh5 file
    timestamp = lh5.load_nda(dsp_fname, ["timestamp"], f"{first_channel}/dsp/")[
        "timestamp"
    ]
    # get the last entry
    last_timestamp = timestamp[-1]
    # convert from UNIX tstamp to string tstmp of format YYYYMMDDTHHMMSSZ
    last_timestamp = unix_timestamp_to_string(last_timestamp)

    return last_timestamp


# -------------------------------------------------------------------------
# Config file related functions (for building files)
# -------------------------------------------------------------------------


def add_config_entries(
    config: dict,
    file_keys: str,
    prod_path: str,
    prod_config: dict,
) -> dict:
    """Add missing information (output, dataset) to the configuration file. This function is generally used during automathic data production, where the initiali config file has only the 'subsystem' entry."""
    # Get the keys
    with open(file_keys) as f:
        keys = f.readlines()
    # Remove newline characters from each line using strip()
    keys = [key.strip() for key in keys]
    # get only keys of timestamps
    timestamp = [key.split("-")[-1] for key in keys]

    # Get the experiment
    experiment = (keys[0].split("-"))[0].upper()

    # Get the period
    period = (keys[0].split("-"))[1]

    # Get the run
    run = (keys[0].split("-"))[2]

    # Get the version
    if "dataset" in config.keys():
        if "version" in config["dataset"].keys():
            version = config["dataset"]["version"]
        else:
            version = (
                (prod_path.split("/"))[-2]
                if prod_path.endswith("/")
                else (prod_path.split("/"))[-1]
            )
        if "type" in config["dataset"].keys():
            type = config["dataset"]["type"]
        else:
            logger.error("\033[91mYou need to provide data type! Try again.\033[0m")
            sys.exit()
        if "path" in config["dataset"].keys():
            path = config["dataset"]["path"]
        else:
            logger.error(
                "\033[91mYou need to provide path to lh5 files! Try again.\033[0m"
            )
            sys.exit()
    else:
        # get phy/cal lists
        phy_keys = [key for key in keys if "phy" in key]
        cal_keys = [key for key in keys if "cal" in key]
        if len(phy_keys) == 0 and len(cal_keys) == 0:
            logger.error("\033[91mNo keys to load. Try again.\033[0m")
            return
        if len(phy_keys) != 0 and len(cal_keys) == 0:
            type = "phy"
        if len(phy_keys) == 0 and len(cal_keys) != 0:
            type = "cal"
            logger.error("\033[91mcal is still under development! Try again.\033[0m")
            return
        if len(phy_keys) != 0 and len(cal_keys) != 0:
            type = ["cal", "phy"]
            logger.error(
                "\033[91mBoth cal and phy are still under development! Try again.\033[0m"
            )
            return
        # Get the production path
        path = (
            prod_path.split("prod-ref")[0] + "prod-ref"
            if prod_path.split("prod-ref")[0].endswith("/")
            else prod_path.split("prod-ref")[0] + "/prod-ref"
        )

    if "output" in config.keys():
        prod_path = config["output"]

    # create the dataset dictionary
    dataset_dict = {
        "experiment": experiment,
        "period": period,
        "version": version,
        "path": path,
        "type": type,
        "run": run,
        "timestamps": timestamp,
    }

    more_info = {"output": prod_path, "dataset": dataset_dict}

    # 'saving' and 'subsystem' info must be already there
    config.update(more_info)

    # let's make a check that everything we need is inside the config, otherwise exit
    if not all(key in config for key in ["output", "dataset", "saving", "subsystems"]):
        logger.error(
            '\033[91mThere are missing entries among ["output", "dataset", "saving", "subsystems"] in the config file (found keys: %s). Try again and check you start with "output" and "dataset" info!\033[0m',
            config.keys(),
        )
        sys.exit()

    return config





# -------------------------------------------------------------------------
# Other functions
# -------------------------------------------------------------------------


def get_livetime(tot_livetime: float):
    """Get the livetime in a human readable format, starting from livetime in seconds.

    If tot_livetime is more than 0.1 yr, convert it to years.
    If tot_livetime is less than 0.1 yr but more than 1 day, convert it to days.
    If tot_livetime is less than 1 day but more than 1 hour, convert it to hours.
    If tot_livetime is less than 1 hour but more than 1 minute, convert it to minutes.
    """
    if tot_livetime > 60 * 60 * 24 * 365.25:
        tot_livetime = tot_livetime / 60 / 60 / 24 / 365.25
        unit = " yr"
    elif tot_livetime > 60 * 60 * 24:
        tot_livetime = tot_livetime / 60 / 60 / 24
        unit = " days"
    elif tot_livetime > 60 * 60:
        tot_livetime = tot_livetime / 60 / 60
        unit = " hrs"
    elif tot_livetime > 60:
        tot_livetime = tot_livetime / 60
        unit = " min"
    else:
        unit = " sec"
    logger.info(f"Total livetime: {tot_livetime:.2f}{unit}")

    return tot_livetime, unit


def is_empty(df: DataFrame):
    """Check if a dataframe is empty. If so, we exit from the code."""
    if df.empty:
        logger.warning(
            "\033[93mThe dataframe is empty. Plotting the next entry (if present, otherwise exiting from the code).\033[0m"
        )
        return True
