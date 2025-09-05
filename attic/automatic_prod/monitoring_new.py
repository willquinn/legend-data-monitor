# Adaptation of William's code to read auto monitoring hdf files for phy data
# and automatically create monitoring plots that'll be later uploaded on the dashboard.
import argparse
import json
import logging
import os
import pickle
import re
import shelve
import sys

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from legendmeta import LegendMetadata
from lgdo import lh5

import legend_data_monitor

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

# -------------------------------------------------------------------------

IPython_default = plt.rcParams.copy()
SMALL_SIZE = 8
MEDIUM_SIZE = 10
BIGGER_SIZE = 12

figsize = (4.5, 3)

plt.rc("font", size=SMALL_SIZE)  # controls default text sizes
plt.rc("axes", titlesize=SMALL_SIZE)  # fontsize of the axes title
plt.rc("axes", labelsize=SMALL_SIZE)  # fontsize of the x and y labels
plt.rc("xtick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
plt.rc("ytick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
plt.rc("legend", fontsize=SMALL_SIZE)  # legend fontsize
plt.rc("figure", titlesize=SMALL_SIZE)  # fontsize of the figure title
plt.rcParams["font.family"] = "serif"

matplotlib.rcParams["mathtext.fontset"] = "stix"

marker_size = 2
line_width = 0.5
cap_size = 0.5
cap_thick = 0.5

plt.rc("axes", facecolor="white", edgecolor="black", axisbelow=True, grid=True)

ignore_keys = legend_data_monitor.utils.IGNORE_KEYS


def parse_args():
    parser = argparse.ArgumentParser(description="Main code for gain monitoring plots.")
    parser.add_argument(
        "--public_data",
        help="Path to tmp-auto public data files.",
        default="/data2/public/prodenv/prod-blind/tmp-auto",
    )
    parser.add_argument(
        "--hdf_files",
        help="Path to hdf files (eg see files in /data1/users/calgaro/prod-ref-v2/generated/plt/phy).",
    )
    parser.add_argument(
        "--output", default="removal_new_keys", help="Path to output folder."
    )
    parser.add_argument("--start", help="First timestamp of the inspected range.")
    parser.add_argument("--period", help="Period to inspect.")
    parser.add_argument("--runs", nargs="+", type=str, help="Runs to inspect.")
    parser.add_argument(
        "--partition",
        default=False,
        help="False if not partition data; default: False",
    )
    parser.add_argument(
        "--zoom",
        default=False,
        type=bool,
        help="True to zoom over y axis; default: False",
    )
    parser.add_argument(
        "--quadratic",
        default=False,
        type=bool,
        help="True if you want to plot the quadratic resolution too; default: False",
    )
    parser.add_argument(
        "--cluster",
        default="lngs",
        help="Name of the cluster where you are operating; pick among 'lngs' or 'nersc'.",
    )
    parser.add_argument(
        "--pswd_email",
        default=None,
        help="Password to access the legend.data.monitoring@gmail.com account for sending alert messages.",
    )
    parser.add_argument(
        "--escale",
        default=2039,
        type=float,
        help="Energy sccale at which evaluating the gain differences; default: 2039 keV (76Ge Qbb).",
    )
    parser.add_argument(
        "--pdf",
        default=False,
        type=bool,
        help="True if you want to save pdf files too; default: False",
    )

    args = parser.parse_args()
    avail_runs = []
    for entry in args.runs:
        new_entry = entry.replace(",", "").replace("[", "").replace("]", "")
        avail_runs.append(new_entry)
    args.runs = avail_runs

    return parser.parse_args()


def transform_string(input_string):
    """From st1 to String:01."""
    # extract numeric part from the input string using regular expression
    match = re.match(r"\D*(\d+)", input_string)
    numeric_part = match.group(1)
    # Format the numeric part with leading zeros and combine with 'String:'
    result_string = f"String:{int(numeric_part):02}"
    return result_string


def parse_json_or_dict(value):
    """Either load data stored in a JSON file or return the input dictionary."""
    try:
        # Attempt to load value as JSON
        with open(value) as json_file:
            return json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        # Treat value as dictionary
        return eval(value)


def get_energy_key(
    ecal_results: dict,
):
    cut_dict = {}
    for key in ["cuspEmax_ctc_runcal", "cuspEmax_ctc_cal"]:
        if key in ecal_results:
            cut_dict = ecal_results[key]
            break
    else:
        logger.debug("No cuspEmax key")
        return cut_dict

    return cut_dict


# run specific block of retrieving the run information
def get_calib_data_dict(
    calib_data, channel_info, tiers, pars, period, run, tier, key_result, fit
):
    sto = lh5.LH5Store()
    channel = channel_info[0]
    channel_name = channel_info[1]

    folder_tier = (
        os.path.join(tiers[0], "cal", period, run)
        if tier == "hit"
        else os.path.join(tiers[1], "cal", period, run)
    )

    folder_par = (
        os.path.join(pars[2], "cal", period, run)
        if tier == "hit"
        else os.path.join(pars[3], "cal", period, run)
    )
    folder_files = os.listdir(folder_par)
    json_files = [f for f in folder_files if f.endswith(".json")]
    yaml_files = [f for f in folder_files if f.endswith((".yaml", ".yml"))]

    filepath = ""
    if json_files:
        filepath = os.path.join(folder_par, json_files[0])
        with open(filepath) as f:
            pars_dict = json.load(f)
    elif yaml_files:
        filepath = os.path.join(folder_par, yaml_files[0])
        with open(filepath) as f:
            pars_dict = yaml.load(f, Loader=yaml.CLoader)
    else:
        raise FileNotFoundError("No .json or .yaml/.yml file found in the folder.")
        sys.exit()

    ch_keys = all(k.startswith("ch") for k in pars_dict.keys())
    if not ch_keys:
        channel = channel_name

    # for FEP peak, we want to look at the behaviour over time --> take 'ecal' results (not partition ones!)
    if channel not in pars_dict.keys():
        fep_peak_pos = np.nan
        fep_peak_pos_err = np.nan
        fep_gain = np.nan
        fep_gain_err = np.nan
    else:
        ecal_results = pars_dict[channel]["results"]["ecal"]
        pk_fits = get_energy_key(ecal_results)["pk_fits"]
        try:
            fep_energy = [
                p for p in sorted(pk_fits) if float(p) > 2613 and float(p) < 2616
            ][0]
            try:
                fep_peak_pos = pk_fits[fep_energy]["parameters_in_ADC"]["mu"]
                fep_peak_pos_err = pk_fits[fep_energy]["uncertainties_in_ADC"]["mu"]
            except (KeyError, TypeError):
                fep_peak_pos = pk_fits[fep_energy]["parameters"]["mu"]
                fep_peak_pos_err = pk_fits[fep_energy]["uncertainties"]["mu"]
            fep_gain = fep_peak_pos / 2614.5
            fep_gain_err = fep_peak_pos_err / 2614.5

        except (KeyError, TypeError):
            fep_peak_pos = np.nan
            fep_peak_pos_err = np.nan
            fep_gain = np.nan
            fep_gain_err = np.nan

    # load the resolution at Qbb, both linear and quadratic if needed
    if channel not in pars_dict.keys():
        Qbb_fwhm = np.nan
        Qbb_fwhm_quad = np.nan
    else:
        # pay attention to cap of V in keV
        Qbb_fwhm = np.nan
        Qbb_fwhm_quad = np.nan
        exist = (
            True
            if pars_dict[channel]["results"][key_result]["cuspEmax_ctc_cal"]
            else False
        )
        Qbb_key = [
            k
            for k in pars_dict[channel]["results"][key_result]["cuspEmax_ctc_cal"][
                "eres_linear"
            ].keys()
            if "Qbb_fwhm_in_" in k
        ][0]

        if exist:
            try:
                Qbb_fwhm = pars_dict[channel]["results"][key_result][
                    "cuspEmax_ctc_cal"
                ]["eres_linear"][Qbb_key]
            except (KeyError, TypeError):
                Qbb_fwhm = pars_dict[channel]["results"][key_result][
                    "cuspEmax_ctc_cal"
                ]["eres_linear"][Qbb_key]

            if fit != "linear":
                try:
                    Qbb_fwhm_quad = pars_dict[channel]["results"][key_result][
                        "cuspEmax_ctc_cal"
                    ]["eres_quadratic"][Qbb_key]
                except (KeyError, TypeError):
                    Qbb_fwhm_quad = pars_dict[channel]["results"][key_result][
                        "cuspEmax_ctc_cal"
                    ]["eres_quadratic"][Qbb_key]

    # load the calibrated FEP position --> take 'ecal' results (not partition ones!)
    if channel not in pars_dict.keys():
        fep_cal = np.nan
        fep_cal_err = np.nan
    else:
        ecal_results = pars_dict[channel]["pars"]["operations"]
        ecal_results = get_energy_key(ecal_results)
        expr = ecal_results["expression"]
        params = ecal_results["parameters"]
        eval_context = {**params, "cuspEmax_ctc": fep_peak_pos}
        fep_cal = eval(expr, {}, eval_context)
        eval_context = {**params, "cuspEmax_ctc": fep_peak_pos_err}
        fep_cal_err = eval(expr, {}, eval_context)

    # get timestamp for additional-final cal run (only for FEP gain display)
    dir_path = os.path.join(tiers[-1], "phy", period)
    found = False
    if os.path.isdir(dir_path):
        if run not in os.listdir(dir_path):
            run_files = sorted(os.listdir(folder_tier))
            run_end_time = pd.to_datetime(
                sto.read(
                    "ch1027201/dsp/timestamp", os.path.join(folder_tier, run_files[-1])
                )[-1],
                unit="s",
            )
            run_start_time = run_end_time
            found = True
    if not found:
        run_files = sorted(os.listdir(folder_tier))
        run_start_time = pd.to_datetime(
            sto.read(
                "ch1027201/dsp/timestamp", os.path.join(folder_tier, run_files[0])
            )[0],
            unit="s",
        )
        run_end_time = pd.to_datetime(
            sto.read(
                "ch1027201/dsp/timestamp", os.path.join(folder_tier, run_files[-1])
            )[-1],
            unit="s",
        )

    calib_data["fep"].append(fep_gain)
    calib_data["fep_err"].append(fep_gain_err)
    calib_data["cal_const"].append(fep_cal)
    calib_data["cal_const_err"].append(fep_cal_err)
    calib_data["run_start"].append(run_start_time)
    calib_data["run_end"].append(run_end_time)
    calib_data["res"].append(Qbb_fwhm)
    calib_data["res_quad"].append(Qbb_fwhm_quad)

    return calib_data


def get_calib_pars(
    cluster, path, period, run_list, channel_info, partition, escale, fit="linear"
):
    # add special calib runs at the end of a period
    if isinstance(period, list) and isinstance(run_list, dict):
        my_runs = run_list["p09"]
        run_list["p09"] = my_runs + ["r006"]
    else:
        # TODO: fix x-range if this extra run is included
        if period == "p04":
            run_list.append("r004")
        if period == "p07":
            run_list.append("r008")
        if period == "p08":
            run_list.append("r015")
        if period == "p09":
            run_list.append("r006")
        if period == "p10":
            run_list.append("r007")
        if period == "p11":
            run_list.append("r005")

    calib_data = {
        "fep": [],
        "fep_err": [],
        "cal_const": [],
        "cal_const_err": [],
        "run_start": [],
        "run_end": [],
        "res": [],
        "res_quad": [],
    }

    tiers, pars = legend_data_monitor.utils.get_tiers_pars_folders(path)

    tier = "hit"
    key_result = "ecal"
    if os.path.isdir(tiers[1]):
        if os.listdir(tiers[1]) != []:
            tier = "pht"
            key_result = "partition_ecal"

    for run in run_list:
        calib_data = get_calib_data_dict(
            calib_data, channel_info, tiers, pars, period, run, tier, key_result, fit
        )

    for key, item in calib_data.items():
        calib_data[key] = np.array(item)

    init_cal_const, init_fep = 0, 0
    for cal_, fep_ in zip(calib_data["cal_const"], calib_data["fep"]):
        if init_fep == 0 and fep_ != 0:
            init_fep = fep_
        if init_cal_const == 0 and cal_ != 0:
            init_cal_const = cal_

    if init_cal_const == 0:
        calib_data["cal_const_diff"] = np.array(
            [np.nan for i in range(len(calib_data["cal_const"]))]
        )
    else:
        calib_data["cal_const_diff"] = (
            (calib_data["cal_const"] - init_cal_const) / init_cal_const * escale
        )

    if init_fep == 0:
        calib_data["fep_diff"] = np.array(
            [np.nan for i in range(len(calib_data["fep"]))]
        )
    else:
        calib_data["fep_diff"] = (calib_data["fep"] - init_fep) / init_fep * escale

    return calib_data


def custom_resampler(group, min_required_data_points=100):
    if len(group) >= min_required_data_points:
        return group
    else:
        return None


def get_dfs(phy_mtg_data, period, run_list):
    """Load and combine HDF dataframes from geds and pulser files."""
    geds_df_cuspEmax_abs = pd.DataFrame()
    geds_df_cuspEmax_abs_corr = pd.DataFrame()
    puls_df_cuspEmax_abs = pd.DataFrame()
    geds_df_cuspEmaxCtcCal_abs = pd.DataFrame()

    geds_files = get_files(phy_mtg_data, period, run_list, ["hdf", "geds"])
    puls_files = get_files(phy_mtg_data, period, run_list, ["hdf", "pulser01ana"])

    for filepath in geds_files:
        logger.debug(f"Loading geds file: {filepath}")
        geds_abs = load_key_if_exists(filepath, "IsPulser_TrapemaxCtcCal")
        geds_df_cuspEmax_abs = pd.concat([geds_df_cuspEmax_abs, geds_abs])

        corrected = load_key_if_exists(
            filepath, "IsPulser_TrapemaxCtcCal_pulser01anaDiff"
        )
        geds_df_cuspEmax_abs_corr = pd.concat([geds_df_cuspEmax_abs_corr, corrected])

    for filepath in puls_files:
        logger.debug(f"Loading pulser file: {filepath}")
        puls_abs = load_key_if_exists(filepath, "IsPulser_TrapemaxCtcCal")
        puls_df_cuspEmax_abs = pd.concat([puls_df_cuspEmax_abs, puls_abs])

    return (
        geds_df_cuspEmax_abs,
        geds_df_cuspEmax_abs_corr,
        puls_df_cuspEmax_abs,
        geds_df_cuspEmaxCtcCal_abs,
    )


def get_files(phy_mtg_data, period, run_list, match_keywords):
    """Collect matching HDF5 files from run directories."""
    base_path = os.path.join(phy_mtg_data, period)
    matched_files = []

    for run in os.listdir(base_path):
        if run not in run_list:
            continue

        files = os.listdir(os.path.join(base_path, run))
        for f in files:
            if all(k in f for k in match_keywords) and all(
                k not in f for k in ["res", "min"]
            ):
                matched_files.append(os.path.join(base_path, run, f))

    return matched_files


def load_key_if_exists(filepath, key):
    try:
        with pd.HDFStore(filepath, mode="r") as store:
            if key in store:
                return pd.read_hdf(store.filename, key=key)
    except (KeyError, OSError, ValueError):
        pass
    return pd.DataFrame()


def get_traptmax_tp0est(phy_mtg_data, period, run_list):
    """Load Tp0Est and TrapTmax data from geds and pulser HDFs."""
    geds_df_trapTmax = pd.DataFrame()
    geds_df_tp0est = pd.DataFrame()
    puls_df_trapTmax = pd.DataFrame()
    puls_df_tp0est = pd.DataFrame()

    geds_files = get_files(phy_mtg_data, period, run_list, ["hdf", "geds"])
    puls_files = get_files(phy_mtg_data, period, run_list, ["hdf", "pulser01ana"])

    for geds_path in geds_files:
        geds_df_trapTmax = pd.concat(
            [geds_df_trapTmax, load_key_if_exists(geds_path, "IsPulser_TrapTmax")]
        )
        geds_df_tp0est = pd.concat(
            [geds_df_tp0est, load_key_if_exists(geds_path, "IsPulser_Tp0Est")]
        )

    for puls_path in puls_files:
        puls_df_trapTmax = pd.concat(
            [puls_df_trapTmax, load_key_if_exists(puls_path, "IsPulser_TrapTmax")]
        )
        puls_df_tp0est = pd.concat(
            [puls_df_tp0est, load_key_if_exists(puls_path, "IsPulser_Tp0Est")]
        )

    return geds_df_trapTmax, geds_df_tp0est, puls_df_trapTmax, puls_df_tp0est


def filter_series_by_ignore_keys(series, ignore_keys, period_key):
    """Filter out specific time ranges marked for exclusion."""
    if period_key not in ignore_keys:
        return series

    for start, stop in zip(
        ignore_keys[period_key]["start_keys"], ignore_keys[period_key]["stop_keys"]
    ):
        start_time = pd.to_datetime(start, format="%Y%m%dT%H%M%S%z")
        stop_time = pd.to_datetime(stop, format="%Y%m%dT%H%M%S%z")
        series = series[(series.index < start_time) | (series.index > stop_time)]

    return series


def get_pulser_data(phy_mtg_data, period, run_list):

    geds_pulser_amp = pd.DataFrame()
    puls_pulser_amp = pd.DataFrame()
    geds_df_amplitude_diff = pd.DataFrame()
    geds_df_baseline = pd.DataFrame()
    geds_df_energy = pd.DataFrame()

    geds_files = get_files(phy_mtg_data, period, run_list, ["hdf", "geds"])
    puls_files = get_files(phy_mtg_data, period, run_list, ["hdf", "pulser01ana"])

    for filepath in geds_files:
        logger.debug(f"Loading geds pulser data from: {filepath}")
        geds_pulser_amp = pd.concat(
            [
                geds_pulser_amp,
                load_key_if_exists(filepath, "IsPulser_TrapemaxCtcCal"),
            ]
        )
        geds_df_amplitude_diff = pd.concat(
            [
                geds_df_amplitude_diff,
                load_key_if_exists(filepath, "IsPulser_TrapemaxCtcCal_pulser01anaDiff"),
            ]
        )
        geds_df_baseline = pd.concat(
            [
                geds_df_baseline,
                load_key_if_exists(filepath, "IsPulser_Baseline"),
            ]
        )
        geds_df_energy = pd.concat(
            [
                geds_df_energy,
                load_key_if_exists(filepath, "IsPulser_Energy"),
            ]
        )

    for filepath in puls_files:
        logger.debug(f"Loading pulser01ana data from: {filepath}")
        puls_pulser_amp = pd.concat(
            [
                puls_pulser_amp,
                load_key_if_exists(filepath, "IsPulser_TrapemaxCtcCal"),
            ]
        )

    return (
        geds_pulser_amp,
        puls_pulser_amp,
        geds_df_amplitude_diff,
        geds_df_baseline,
        geds_df_energy,
    )


def get_channel_map(meta_data_path, timestamp):
    meta = LegendMetadata(meta_data_path)
    chmap = meta.channelmap(timestamp)

    str_chns = {}
    for ged, item in chmap.items():
        if item["system"] == "geds" and item["analysis"]["processable"]:
            string = int(item["location"]["string"])
            if string not in str_chns.keys():
                str_chns[string] = {"rawid": [], "name": []}
            str_chns[string]["rawid"].append(f"ch{chmap[ged].daq.rawid}")
            str_chns[string]["name"].append(ged)
    return str_chns


def main():

    args = parse_args()

    dataset = {args.period: args.runs}
    logger.debug(f"Available phy data: {dataset}")

    xlim_idx = 1

    fit_flag = "quadratic" if args.quadratic is True else "linear"

    str_chns = get_channel_map(os.path.join(args.public_data, "inputs/"), args.start)

    email_message = ["ALERT: Data monitoring threshold exceeded."]

    # skip detectors with no pulser entries
    no_puls_dets = legend_data_monitor.utils.NO_PULS_DETS
    flag_expr = " or ".join(
        f'(channel == "{channel}" and period in {periods})'
        for channel, periods in no_puls_dets.items()
    )

    # gain over period
    for period, run_list in dataset.items():
        (
            geds_df_cuspEmax_abs,
            geds_df_cuspEmax_abs_corr,
            puls_df_cuspEmax_abs,
            geds_df_cuspEmaxCtcCal_abs,
        ) = get_dfs(args.hdf_files, period, run_list)
        geds_df_trapTmax, geds_df_tp0est, puls_df_trapTmax, puls_df_tp0est = (
            get_traptmax_tp0est(args.hdf_files, period, run_list)
        )

        if (
            geds_df_cuspEmax_abs is None
            or geds_df_cuspEmax_abs_corr is None
            or puls_df_cuspEmax_abs is None
        ):
            logger.debug("Dataframes are None for %s!", period)
            continue
        # check if geds df is empty; if pulser is, means we do not apply any correction
        # (and thus geds_corr is also empty - the code will handle the case)
        if (
            geds_df_cuspEmax_abs.empty
            # or geds_df_cuspEmax_abs_corr.empty
            # or puls_df_cuspEmax_abs.empty
        ):
            logger.debug("Dataframes are empty for %s!", period)
            continue
        dfs = [
            geds_df_cuspEmax_abs,
            geds_df_cuspEmax_abs_corr,
            puls_df_cuspEmax_abs,
            geds_df_trapTmax,
            geds_df_tp0est,
            puls_df_trapTmax,
            puls_df_tp0est,
            geds_df_cuspEmaxCtcCal_abs,
        ]

        for string, channel_list in str_chns.items():
            for channel in channel_list:

                channel_name = str_chns.map("daq.rawid")[int(channel[2:])]["name"]
                resampling_time = "1h"  # if len(runs)>1 else "10T"
                if int(channel.split("ch")[-1]) not in list(dfs[0].columns):
                    logger.debug(f"{channel} is not present in the dataframe!")
                    continue

                logger.debug(f"Inspecting {channel_name}")
                pulser_data = get_pulser_data(
                    resampling_time,
                    period,
                    dfs,
                    int(channel.split("ch")[-1]),
                    len(args.runs),
                    escale=args.escale,
                )

                logger.debug("...getting calibration data")
                pars_data = get_calib_pars(
                    args.cluster,
                    args.public_data,
                    period,
                    run_list,
                    [channel, channel_name],
                    args.partition,
                    escale=args.escale,
                    fit=fit_flag,
                )
                fig, ax = plt.subplots(figsize=(12, 4))

                t0 = pars_data["run_start"]
                if not eval(flag_expr):
                    kevdiff = (
                        pulser_data["ged"]["kevdiff_av"]
                        if pulser_data["diff"]["kevdiff_av"] is None
                        else pulser_data["diff"]["kevdiff_av"]
                    )

                    # check if gain is over threshold
                    if (
                        kevdiff is not None
                        and len(email_message) > 1
                        and args.pswd_email is not None
                    ):
                        timestamps = kevdiff.index
                        for i in range(len(t0)):
                            time_range_start = t0[i]
                            time_range_end = time_range_start + pd.Timedelta(days=7)
                            # convert naive timestamp to UTC-aware
                            time_range_start = pd.Timestamp(time_range_start)
                            time_range_end = pd.Timestamp(time_range_end)

                            if time_range_start.tzinfo is None:
                                time_range_start = time_range_start.tz_localize("UTC")
                            else:
                                time_range_start = time_range_start.tz_convert("UTC")
                            if time_range_end.tzinfo is None:
                                time_range_end = time_range_end.tz_localize("UTC")
                            else:
                                time_range_end = time_range_end.tz_convert("UTC")

                            # filter timestamps/gain within the time range
                            mask_time_range = (timestamps >= time_range_start) & (
                                timestamps < time_range_end
                            )
                            filtered_timestamps = timestamps[mask_time_range]
                            kevdiff_in_range = kevdiff[mask_time_range]

                            threshold = pars_data["res"][i] / 2
                            mask = (kevdiff_in_range > threshold) | (
                                kevdiff_in_range < -threshold
                            )
                            over_threshold_timestamps = filtered_timestamps[mask]

                            if not over_threshold_timestamps.empty:
                                for t in over_threshold_timestamps:
                                    email_message.append(
                                        f"- Gain over threshold at {t} ({period}) for {channel_name} ({channel}) string {string}"
                                    )

                    # PULS01ANA has a signal - we can correct GEDS energies for it!
                    if pulser_data["pul_cusp"]["kevdiff_av"] is not None:
                        plt.plot(
                            pulser_data["pul_cusp"]["kevdiff_av"],
                            "C2",
                            label="PULS01ANA",
                        )
                        plt.plot(
                            pulser_data["diff"]["kevdiff_av"],
                            "C4",
                            label="GED corrected",
                        )
                        plt.fill_between(
                            pulser_data["diff"]["kevdiff_av"].index.values,
                            y1=[
                                float(i) - float(j)
                                for i, j in zip(
                                    pulser_data["diff"]["kevdiff_av"].values,
                                    pulser_data["diff"]["kevdiff_std"].values,
                                )
                            ],
                            y2=[
                                float(i) + float(j)
                                for i, j in zip(
                                    pulser_data["diff"]["kevdiff_av"].values,
                                    pulser_data["diff"]["kevdiff_std"].values,
                                )
                            ],
                            color="k",
                            alpha=0.2,
                            label=r"±1$\sigma$",
                        )
                    # else, no correction is applied
                    else:
                        plt.plot(
                            pulser_data["ged"]["kevdiff_av"].sort_index(),
                            "dodgerblue",
                            label="GED uncorrected",
                        )
                        plt.fill_between(
                            pulser_data["ged"]["kevdiff_av"].index.values,
                            y1=[
                                float(i) - float(j)
                                for i, j in zip(
                                    pulser_data["ged"]["kevdiff_av"].values,
                                    pulser_data["ged"]["kevdiff_std"].values,
                                )
                            ],
                            y2=[
                                float(i) + float(j)
                                for i, j in zip(
                                    pulser_data["ged"]["kevdiff_av"].values,
                                    pulser_data["ged"]["kevdiff_std"].values,
                                )
                            ],
                            color="k",
                            alpha=0.2,
                            label=r"±1$\sigma$",
                        )

                plt.plot(
                    pars_data["run_start"] - pd.Timedelta(hours=5),
                    pars_data["fep_diff"],
                    "kx",
                    label="FEP gain",
                )
                plt.plot(
                    pars_data["run_start"] - pd.Timedelta(hours=5),
                    pars_data["cal_const_diff"],
                    "rx",
                    label="cal. const. diff",
                )

                for ti in pars_data["run_start"]:
                    plt.axvline(ti, color="dimgrey", ls="--")

                for i in range(len(t0)):
                    if i == len(pars_data["run_start"]) - 1:
                        plt.plot(
                            [t0[i], t0[i] + pd.Timedelta(days=7)],
                            [pars_data["res"][i] / 2, pars_data["res"][i] / 2],
                            "b-",
                        )
                        plt.plot(
                            [t0[i], t0[i] + pd.Timedelta(days=7)],
                            [-pars_data["res"][i] / 2, -pars_data["res"][i] / 2],
                            "b-",
                        )
                        if args.quadratic:
                            plt.plot(
                                [t0[i], t0[i] + pd.Timedelta(days=7)],
                                [
                                    pars_data["res_quad"][i] / 2,
                                    pars_data["res_quad"][i] / 2,
                                ],
                                color="dodgerblue",
                                linestyle="-",
                            )
                            plt.plot(
                                [t0[i], t0[i] + pd.Timedelta(days=7)],
                                [
                                    -pars_data["res_quad"][i] / 2,
                                    -pars_data["res_quad"][i] / 2,
                                ],
                                color="dodgerblue",
                                linestyle="-",
                            )
                    else:
                        plt.plot(
                            [t0[i], t0[i + 1]],
                            [pars_data["res"][i] / 2, pars_data["res"][i] / 2],
                            "b-",
                        )
                        plt.plot(
                            [t0[i], t0[i + 1]],
                            [-pars_data["res"][i] / 2, -pars_data["res"][i] / 2],
                            "b-",
                        )
                        if args.quadratic:
                            plt.plot(
                                [t0[i], t0[i + 1]],
                                [
                                    pars_data["res_quad"][i] / 2,
                                    pars_data["res_quad"][i] / 2,
                                ],
                                color="dodgerblue",
                                linestyle="-",
                            )
                            plt.plot(
                                [t0[i], t0[i + 1]],
                                [
                                    -pars_data["res_quad"][i] / 2,
                                    -pars_data["res_quad"][i] / 2,
                                ],
                                color="dodgerblue",
                                linestyle="-",
                            )

                    if str(pars_data["res"][i] / 2 * 1.1) != "nan" and i < len(
                        pars_data["res"]
                    ) - (xlim_idx - 1):
                        plt.text(
                            t0[i],
                            pars_data["res"][i] / 2 * 1.1,
                            "{:.2f}".format(pars_data["res"][i]),
                            color="b",
                        )

                    if args.quadratic:
                        if str(pars_data["res_quad"][i] / 2 * 1.5) != "nan" and i < len(
                            pars_data["res"]
                        ) - (xlim_idx - 1):
                            plt.text(
                                t0[i],
                                pars_data["res_quad"][i] / 2 * 1.5,
                                "{:.2f}".format(pars_data["res_quad"][i]),
                                color="dodgerblue",
                            )

                fig.suptitle(
                    f'period: {period} - string: {string} - position: {str_chns.map("daq.rawid")[int(channel[2:])]["location"]["position"]} - ged: {channel_name}'
                )
                plt.ylabel(r"Energy diff / keV")
                plt.plot([0, 1], [0, 1], "b", label="Qbb FWHM keV lin.")
                if args.quadratic:
                    plt.plot([1, 2], [1, 2], "dodgerblue", label="Qbb FWHM keV quadr.")

                if args.zoom:
                    if flag_expr:
                        plt.ylim(-3, 3)
                    else:
                        bound = np.average(pulser_data["ged"]["cusp_av"].dropna())
                        plt.ylim(-2.5 * bound, 2.5 * bound)
                max_date = pulser_data["ged"]["kevdiff_av"].index.max()
                time_difference = max_date.tz_localize(None) - t0[
                    -xlim_idx
                ].tz_localize(None)
                plt.xlim(
                    t0[0] - pd.Timedelta(hours=8), t0[-xlim_idx] + time_difference * 1.5
                )  # pd.Timedelta(days=7))# --> change me to resize the width of the last run
                plt.legend(loc="lower left")
                plt.tight_layout()

                mgt_folder = os.path.join(args.output, period, f"st{string}")
                if not os.path.exists(mgt_folder):
                    os.makedirs(mgt_folder)
                    logger.debug("...created %s", mgt_folder)

                # ~~~~~~~~~~~~~~~~ save pdfs with plots for an easy/quick access ~~~~~~~~~~~~~~~~
                pdf_name = os.path.join(
                    mgt_folder,
                    f"{period}_string{string}_pos{str_chns.map('daq.rawid')[int(channel[2:])]['location']['position']}_{channel_name}_gain_shift.pdf",
                )
                if args.pdf:
                    logger.info("Saving %s", pdf_name)
                    plt.savefig(pdf_name)

                # pickle and save calibration inputs retrieved ots in a shelve file
                # serialize the plot
                serialized_plot = pickle.dumps(plt.gcf())
                plt.close(fig)
                # store the serialized plot in a shelve object under key
                with shelve.open(
                    os.path.join(args.output, period, f"{period}_gain_shift"),
                    "c",
                    protocol=pickle.HIGHEST_PROTOCOL,
                ) as shelf:
                    shelf[
                        f'{period}_string{string}_pos{str_chns.map("daq.rawid")[int(channel[2:])]["location"]["position"]}_{channel_name}'
                    ] = serialized_plot
                plt.close(fig)

                # structure of pickle files:
                #  - p08_string1_pos1_V02160A
                #  - p08_string1_pos2_V02160B
                #  - ...
                #  - p08_string2_pos1_B00035C
                #  - p08_string2_pos2_C000RG1
                #  - ...

    """if len(email_message) > 1 and args.pswd_email is not None:
        with open("message.txt", "w") as f:
            for line in email_message:
                f.write(line + "\n")
        legend_data_monitor.utils.send_email_alert(
            args.pswd_email, ["sofia.calgaro@physik.uzh.ch"], "message.txt"
        )"""


if __name__ == "__main__":
    main()
