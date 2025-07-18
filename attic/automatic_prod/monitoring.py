# Adaptation of William's code to read auto monitoring hdf files for phy data
# and automatically create monitoring plots that'll be later uploaded on the dashboard.
import argparse
import json
import logging
import os
import pickle
import shelve
import sys

import h5py
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from legendmeta import LegendMetadata
from lgdo import lh5
from tqdm.notebook import tqdm

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

plt.rc("font", size=SMALL_SIZE)  # controls default text sizes
plt.rc("axes", titlesize=SMALL_SIZE)  # fontsize of the axes title
plt.rc("axes", labelsize=SMALL_SIZE)  # fontsize of the x and y labels
plt.rc("xtick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
plt.rc("ytick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
plt.rc("legend", fontsize=SMALL_SIZE)  # legend fontsize
plt.rc("figure", titlesize=SMALL_SIZE)  # fontsize of the figure title
plt.rcParams["font.family"] = "serif"

matplotlib.rcParams["mathtext.fontset"] = "stix"

plt.rc("axes", facecolor="white", edgecolor="black", axisbelow=True, grid=True)

ignore_keys = legend_data_monitor.utils.IGNORE_KEYS


def build_new_files(my_path, period, run):
    data_file = os.path.join(
        my_path, "generated/plt/phy", period, run, f"l200-{period}-{run}-phy-geds.hdf"
    )

    if not os.path.exists(data_file):
        logger.debug(f"File not found: {data_file}. Exit here.")
        sys.exit()

    with h5py.File(data_file, "r") as f:
        my_keys = list(f.keys())

    info_dict = {"keys": my_keys}

    resampling_times = ["1min", "5min", "10min", "30min", "60min"]

    for idx, resample_unit in enumerate(resampling_times):
        new_file = os.path.join(
            my_path,
            "generated/plt/phy",
            period,
            run,
            f"l200-{period}-{run}-phy-geds-res_{resample_unit}.hdf",
        )
        # remove it if already exists so we can start again to append resampled data
        if os.path.exists(new_file):
            os.remove(new_file)

        for k in my_keys:
            if "info" in k:
                # do it once
                if idx == 0:
                    original_df = pd.read_hdf(data_file, key=k)
                    info_dict.update(
                        {
                            k: {
                                "subsystem": original_df.loc["subsystem", "Value"],
                                "unit": original_df.loc["unit", "Value"],
                                "label": original_df.loc["label", "Value"],
                                "event_type": original_df.loc["event_type", "Value"],
                                "lower_lim_var": original_df.loc[
                                    "lower_lim_var", "Value"
                                ],
                                "upper_lim_var": original_df.loc[
                                    "upper_lim_var", "Value"
                                ],
                                "lower_lim_abs": original_df.loc[
                                    "lower_lim_abs", "Value"
                                ],
                                "upper_lim_abs": original_df.loc[
                                    "upper_lim_abs", "Value"
                                ],
                            }
                        }
                    )
                continue

            original_df = pd.read_hdf(data_file, key=k)

            # mean dataframe is kept
            if "_mean" in k:
                original_df.to_hdf(new_file, key=k, mode="a")
                continue

            original_df.index = pd.to_datetime(original_df.index)
            # resample
            resampled_df = original_df.resample(resample_unit).mean()
            # substitute the original df with the resampled one
            original_df = resampled_df
            # append resampled data to the new file
            resampled_df.to_hdf(new_file, key=k, mode="a")

        if idx == 0:
            json_output = os.path.join(
                my_path,
                "generated/plt/phy",
                period,
                run,
                f"l200-{period}-{run}-phy-geds-info.yaml",
            )
            with open(json_output, "w") as file:
                json.dump(info_dict, file, indent=4)


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


def get_dfs(phy_mtg_data, period, run_list, parameter):
    geds_df_cuspEmax_abs = pd.DataFrame()
    geds_df_cuspEmax_abs_corr = pd.DataFrame()
    puls_df_cuspEmax_abs = pd.DataFrame()
    geds_df_cuspEmaxCtcCal_abs = pd.DataFrame()

    phy_mtg_data = os.path.join(phy_mtg_data, period)
    runs = os.listdir(phy_mtg_data)
    for r in runs:
        # keep only specified runs
        if r not in run_list:
            continue
        files = os.listdir(os.path.join(phy_mtg_data, r))
        logger.debug(f"Retrieved files: {files}")
        hdf_geds = [
            f
            for f in files
            if "hdf" in f and "geds" in f and "res" not in f and "min" not in f
        ]
        if len(hdf_geds) == 0:
            logger.debug("hdf_geds is empty")
            return None, None, None, None
        else:
            hdf_geds = os.path.join(phy_mtg_data, r, hdf_geds[0])
            geds_abs = pd.read_hdf(hdf_geds, key=f"IsPulser_{parameter}")
            geds_df_cuspEmax_abs = pd.concat(
                [geds_df_cuspEmax_abs, geds_abs], ignore_index=False, axis=0
            )
            # geds_ctc_cal_abs = pd.read_hdf(hdf_geds, key=f'IsPulser_TrapemaxCtcCal')
            # geds_df_cuspEmaxCtcCal_abs = pd.concat([geds_df_cuspEmaxCtcCal_abs, geds_ctc_cal_abs], ignore_index=False, axis=0)
            with pd.HDFStore(hdf_geds, mode="r") as store:
                available_keys = store.keys()
            if f"IsPulser_{parameter}_pulser01anaDiff" in available_keys:
                geds_puls_abs = pd.read_hdf(
                    hdf_geds, key=f"IsPulser_{parameter}_pulser01anaDiff"
                )
                geds_df_cuspEmax_abs_corr = pd.concat(
                    [geds_df_cuspEmax_abs_corr, geds_puls_abs],
                    ignore_index=False,
                    axis=0,
                )

        hdf_puls = [
            f
            for f in files
            if "hdf" in f and "pulser01ana" in f and "res" not in f and "min" not in f
        ]
        if len(hdf_puls) == 0:
            logger.debug("hdf_puls is empty")
        else:
            hdf_puls = os.path.join(phy_mtg_data, r, hdf_puls[0])
            with pd.HDFStore(hdf_puls, mode="r") as store:
                available_keys = store.keys()
            if f"IsPulser_{parameter}" in available_keys:
                puls_abs = pd.read_hdf(hdf_puls, key=f"IsPulser_{parameter}")
                puls_df_cuspEmax_abs = pd.concat(
                    [puls_df_cuspEmax_abs, puls_abs], ignore_index=False, axis=0
                )

    return (
        geds_df_cuspEmax_abs,
        geds_df_cuspEmax_abs_corr,
        puls_df_cuspEmax_abs,
        geds_df_cuspEmaxCtcCal_abs,
    )


def get_traptmax_tp0est(phy_mtg_data, period, run_list):
    geds_df_trapTmax = pd.DataFrame()
    geds_df_tp0est = pd.DataFrame()
    puls_df_trapTmax = pd.DataFrame()
    puls_df_tp0est = pd.DataFrame()

    phy_mtg_data = os.path.join(phy_mtg_data, period)
    runs = os.listdir(phy_mtg_data)
    for r in runs:
        # keep only specified runs
        if r not in run_list:
            continue
        files = os.listdir(os.path.join(phy_mtg_data, r))
        # get only geds files
        hdf_geds = [f for f in files if "hdf" in f and "geds" in f]
        if len(hdf_geds) == 0:
            return None, None, None, None
        hdf_geds = os.path.join(phy_mtg_data, r, hdf_geds[0])  # should be 1
        # get only puls files
        hdf_puls = [f for f in files if "hdf" in f and "pulser01ana" in f]
        if len(hdf_puls) == 0:
            return None, None, None, None
        hdf_puls = os.path.join(phy_mtg_data, r, hdf_puls[0])  # should be 1

        # Geds data
        try:
            geds_trapTmax_abs = pd.read_hdf(hdf_geds, key="IsPulser_TrapTmax")
            geds_df_trapTmax = pd.concat(
                [geds_df_trapTmax, geds_trapTmax_abs], ignore_index=False, axis=0
            )
            geds_tp0est_abs = pd.read_hdf(hdf_geds, key="IsPulser_Tp0Est")
            geds_df_tp0est = pd.concat(
                [geds_df_tp0est, geds_tp0est_abs], ignore_index=False, axis=0
            )
        except (KeyError, OSError, ValueError):
            geds_df_trapTmax = geds_df_tp0est = None

        # Pulser data
        try:
            puls_trapTmax_abs = pd.read_hdf(hdf_puls, key="IsPulser_TrapTmax")
            puls_df_trapTmax = pd.concat(
                [puls_df_trapTmax, puls_trapTmax_abs], ignore_index=False, axis=0
            )
            puls_tp0est_abs = pd.read_hdf(hdf_puls, key="IsPulser_Tp0Est")
            puls_df_tp0est = pd.concat(
                [puls_df_tp0est, puls_tp0est_abs], ignore_index=False, axis=0
            )
        except (KeyError, OSError, ValueError):
            puls_df_trapTmax = puls_df_tp0est = None

    return geds_df_trapTmax, geds_df_tp0est, puls_df_trapTmax, puls_df_tp0est


def filter_series_by_ignore_keys(series_to_filter, ignore_keys, key):
    """Remove keys listed in a dictionary of keys to ignore for each specific period."""
    if key not in ignore_keys:
        return series_to_filter

    start_keys = ignore_keys[key]["start_keys"]
    stop_keys = ignore_keys[key]["stop_keys"]

    for ki, kf in zip(start_keys, stop_keys):
        isolated_ki = pd.to_datetime(ki, format="%Y%m%dT%H%M%S%z")
        isolated_kf = pd.to_datetime(kf, format="%Y%m%dT%H%M%S%z")
        series_to_filter = series_to_filter[
            (series_to_filter.index < isolated_ki)
            | (series_to_filter.index > isolated_kf)
        ]

    return series_to_filter


def get_pulser_data(resampling_time, period, dfs, channel, escale):
    # geds
    ser_ged_cusp = dfs[0][channel].sort_index()
    # if no pulser, set these to None
    pul_cusp_hr_av_ = None
    pul_cusp_hr_std = None
    ser_pul_cusp = None
    ser_pul_cuspdiff = None
    ser_pul_cuspdiff_kev = None
    ged_cusp_cor_hr_av_ = None
    ged_cusp_cor_hr_std = None
    ged_cusp_corr = None
    ged_cusp_corr_kev = None

    logger.debug("...removing cycles to ignore")
    if isinstance(period, list):
        for p in period:
            ser_ged_cusp = filter_series_by_ignore_keys(ser_ged_cusp, ignore_keys, p)
    else:
        ser_ged_cusp = filter_series_by_ignore_keys(ser_ged_cusp, ignore_keys, period)
    ser_ged_cusp = ser_ged_cusp.dropna()

    logger.debug("...getting hour counts")
    hour_counts = ser_ged_cusp.resample(
        resampling_time
    ).count()  # >= 100; before, we were using ser_pul_cusp
    mask = hour_counts > 0

    logger.debug("...getting average")
    # compute how many elements correspond to 10%
    n_elements = int(len(ser_ged_cusp) * 0.10)
    ged_cusp_av = np.average(ser_ged_cusp.values[:n_elements])

    # if first entries of dataframe are NaN
    if np.isnan(ged_cusp_av):
        logger.debug("the average is a nan")
        return None

    logger.debug("...getting geds data")
    # GED part (always computed) ### why 1h times?
    ser_ged_cuspdiff = pd.Series(
        (ser_ged_cusp.values - ged_cusp_av) / ged_cusp_av,
        index=ser_ged_cusp.index.values,
    ).dropna()
    # - same, but at escale ### why 1h times?
    ser_ged_cuspdiff_kev = pd.Series(
        ser_ged_cuspdiff * escale, index=ser_ged_cuspdiff.index.values
    )

    # check if we have any info on the pulser channel
    if not dfs[2].empty:
        ser_pul_cusp = dfs[2][1027203].sort_index()
        # check if these dfs are empty or not - if not, then remove spikes
        if not ser_pul_cusp.all().all() and isinstance(dfs[6], pd.DataFrame):
            ser_pul_tp0est = dfs[6][1027203]

            # remove retriggered events
            condition = (ser_pul_tp0est < 5e4) & (ser_pul_tp0est > 4.8e4)
            len_before = len(ser_pul_tp0est)
            logger.debug(
                "Removed retriggered events:\n",
                ser_pul_tp0est[~condition],
            )
            ser_pul_tp0est_new = ser_pul_tp0est[condition]
            len_after = len(ser_pul_tp0est_new)

            # if not empty, then remove spikes
            if len(ser_pul_tp0est_new) != 0:
                logger.debug(
                    f"!!! Removining {len_before-len_after} global pulser events !!!"
                )
                ser_ged_cusp = ser_ged_cusp.loc[ser_pul_tp0est_new.index]
                ser_pul_cusp = ser_pul_cusp.loc[ser_pul_tp0est_new.index]
        else:
            logger.debug("...tp0est pulser dataframe is empty.")

        logger.debug("...removing cycles to ignore")
        if ser_pul_cusp is not None:
            if isinstance(period, list):
                for p in period:
                    ser_pul_cusp = filter_series_by_ignore_keys(
                        ser_pul_cusp, ignore_keys, p
                    )
            else:
                ser_pul_cusp = filter_series_by_ignore_keys(
                    ser_pul_cusp, ignore_keys, period
                )
        pul_cusp_av = (
            np.average(ser_pul_cusp.values[:n_elements])
            if ser_pul_cusp is not None
            else None
        )

        # Pulser part (only if available or we have an equal number of entries as for geds)
        length_puls = len(ser_pul_cusp[ser_pul_cusp != 0])
        length_geds = len(ser_ged_cusp[ser_ged_cusp != 0])
        if (
            ser_pul_cusp is not None
            and pul_cusp_av is not None
            and length_puls == length_geds
        ):
            logger.debug("...getting pulser and geds-rescaled data")
            ser_pul_cuspdiff = pd.Series(
                (ser_pul_cusp.values - pul_cusp_av) / pul_cusp_av,
                index=ser_pul_cusp.index.values,
            ).dropna()

            ser_pul_cuspdiff_kev = pd.Series(
                ser_pul_cuspdiff * escale, index=ser_pul_cuspdiff.index.values
            )

            pul_cusp_hr_av_ = ser_pul_cuspdiff_kev.resample(resampling_time).mean()
            pul_cusp_hr_av_ = pul_cusp_hr_av_.tz_localize("UTC")  # add UTC timezone
            pul_cusp_hr_av_[~mask] = np.nan

            pul_cusp_hr_std = ser_pul_cuspdiff_kev.resample(resampling_time).std()
            pul_cusp_hr_std = pul_cusp_hr_std.tz_localize("UTC")  # add UTC timezone
            pul_cusp_hr_std[~mask] = np.nan

            # GED - Pulser correction
            common_index = ser_ged_cuspdiff.index.intersection(ser_pul_cuspdiff.index)
            ged_cusp_corr = (
                ser_ged_cuspdiff[common_index] - ser_pul_cuspdiff[common_index]
            )

            ged_cusp_corr_kev = ged_cusp_corr * escale

            ged_cusp_cor_hr_av_ = ged_cusp_corr_kev.resample(resampling_time).mean()
            ged_cusp_cor_hr_av_ = ged_cusp_cor_hr_av_.tz_localize(
                "UTC"
            )  # add UTC timezone
            ged_cusp_cor_hr_av_[~mask] = np.nan

            ged_cusp_cor_hr_std = ged_cusp_corr_kev.resample(resampling_time).std()
            ged_cusp_cor_hr_std = ged_cusp_cor_hr_std.tz_localize(
                "UTC"
            )  # add UTC timezone
            ged_cusp_cor_hr_std[~mask] = np.nan

        else:
            # If no pulser, set these to None or empty series
            pul_cusp_hr_av_ = pul_cusp_hr_std = ser_pul_cuspdiff = (
                ser_pul_cuspdiff_kev
            ) = None
            ged_cusp_cor_hr_av_ = ged_cusp_cor_hr_std = ged_cusp_corr = (
                ged_cusp_corr_kev
            ) = None

    ged_cusp_hr_av_ = ser_ged_cuspdiff_kev.resample(resampling_time).mean()
    ged_cusp_hr_av_ = ged_cusp_hr_av_.tz_localize("UTC")  # add UTC timezone
    ged_cusp_hr_av_[~mask] = np.nan
    ged_cusp_hr_std = ser_ged_cuspdiff_kev.resample(resampling_time).std()
    ged_cusp_hr_std = ged_cusp_hr_std.tz_localize("UTC")  # add UTC timezone
    ged_cusp_hr_std[~mask] = np.nan

    return {
        "ged": {
            "cusp": ser_ged_cusp,
            "cuspdiff": ser_ged_cuspdiff,
            "cuspdiff_kev": ser_ged_cuspdiff_kev,
            "kevdiff_av": ged_cusp_hr_av_,
            "kevdiff_std": ged_cusp_hr_std,
        },
        "pul_cusp": {
            "raw": ser_pul_cusp,
            "rawdiff": ser_pul_cuspdiff,
            "kevdiff": ser_pul_cuspdiff_kev,
            "kevdiff_av": pul_cusp_hr_av_,
            "kevdiff_std": pul_cusp_hr_std,
        },
        "diff": {
            "raw": None,
            "rawdiff": ged_cusp_corr,
            "kevdiff": ged_cusp_corr_kev,
            "kevdiff_av": ged_cusp_cor_hr_av_,
            "kevdiff_std": ged_cusp_cor_hr_std,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Main code for gain monitoring plots.")
    parser.add_argument(
        "--public_data",
        help="Path to tmp-auto public data files (eg /data2/public/prodenv/prod-blind/tmp-auto).",
        default="/data2/public/prodenv/prod-blind/ref-v1.0.1",
    )
    parser.add_argument(
        "--hdf_files",
        help="Path to hdf files (eg see files in /data1/users/calgaro/prod-ref-v2/generated/plt/phy).",
    )
    parser.add_argument(
        "--output", default="removal_new_keys", help="Path to output folder."
    )
    parser.add_argument("--start", help="First timestamp of the inspected range.")
    parser.add_argument("--p", help="Period to inspect.")
    parser.add_argument(
        "--avail_runs",
        nargs="+",
        type=str,
        help="Available runs to inspect for a given period.",
    )
    parser.add_argument("--current_run", type=str, help="Run under inspection.")
    parser.add_argument(
        "--partition",
        default="False",
        help="False if not partition data; default: False",
    )
    parser.add_argument(
        "--zoom", default="False", help="True to zoom over y axis; default: False"
    )
    parser.add_argument(
        "--quad_res",
        default="False",
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
        default="False",
        help="True if you want to save pdf files too; default: False.",
    )
    parser.add_argument(
        "--last_checked",
        help="Timestamp of the last check. ",
    )

    args = parser.parse_args()

    auto_dir_path = args.public_data
    phy_mtg_data = args.hdf_files
    output_folder = args.output
    start_key = args.start
    period = args.p
    runs = args.avail_runs
    current_run = args.current_run
    cluster = args.cluster
    pswd_email = args.pswd_email
    save_pdf = args.pdf
    escale_val = float(args.escale)
    last_checked = args.last_checked

    avail_runs = []
    for entry in runs:
        new_entry = entry.replace(",", "").replace("[", "").replace("]", "")
        avail_runs.append(new_entry)

    dataset = {period: avail_runs}
    logger.debug(f"Available phy data: {dataset}")

    xlim_idx = 1
    partition = False if args.partition == "False" else True
    quadratic = False if args.quad_res == "False" else True
    zoom = False if args.zoom == "False" else True

    fit_flag = "quadratic" if quadratic is True else "linear"

    meta = LegendMetadata(os.path.join(auto_dir_path, "inputs/"))
    # get channel map
    chmap = meta.channelmap(start_key)
    # get string info
    str_chns = {}
    string_numbers = [
        int(item.get("location", {}).get("string"))
        for item in chmap.values()
        if "location" in item and "string" in item["location"]
    ]
    string_numbers = list(dict.fromkeys(string_numbers))  # unique values
    for string in string_numbers:
        channels = [
            f"ch{chmap[ged].daq.rawid}"
            for ged, dic in chmap.items()
            if dic["system"] == "geds"
            and dic["location"]["string"] == string
            and dic["analysis"]["processable"]
            is True  # prevent to load non-processable detectors
        ]
        if len(channels) > 0:
            str_chns[string] = channels

    email_message = []

    # skip detectors with no pulser entries
    no_puls_dets = legend_data_monitor.utils.NO_PULS_DETS
    flag_expr = " or ".join(
        f'(channel == "{channel}" and period in {periods})'
        for channel, periods in no_puls_dets.items()
    )
    period_list = list(dataset.keys())

    # gain over period
    for index_i in tqdm(range(len(period_list))):
        period = period_list[index_i]
        run_list = dataset[period]

        (
            geds_df_cuspEmax_abs,
            geds_df_cuspEmax_abs_corr,
            puls_df_cuspEmax_abs,
            geds_df_cuspEmaxCtcCal_abs,
        ) = get_dfs(phy_mtg_data, period, run_list, "TrapemaxCtcCal")
        geds_df_trapTmax, geds_df_tp0est, puls_df_trapTmax, puls_df_tp0est = (
            get_traptmax_tp0est(phy_mtg_data, period, run_list)
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

        string_list = list(str_chns.keys())
        for index_j in tqdm(range(len(string_list))):
            string = string_list[index_j]

            channel_list = str_chns[string]
            for index_k in range(len(channel_list)):
                channel = channel_list[index_k]
                channel_name = chmap.map("daq.rawid")[int(channel[2:])]["name"]
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
                    escale=escale_val,
                )

                fig, ax = plt.subplots(figsize=(12, 4))
                logger.debug("...getting calibration data")
                pars_data = get_calib_pars(
                    cluster,
                    auto_dir_path,
                    period,
                    run_list,
                    [channel, channel_name],
                    partition,
                    escale=escale_val,
                    fit=fit_flag,
                )

                t0 = pars_data["run_start"]
                if not eval(flag_expr):
                    kevdiff = (
                        pulser_data["ged"]["kevdiff_av"]
                        if pulser_data["diff"]["kevdiff_av"] is None
                        else pulser_data["diff"]["kevdiff_av"]
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
                        if quadratic:
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
                        if quadratic:
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

                    if quadratic:
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
                    f'period: {period} - string: {string} - position: {chmap.map("daq.rawid")[int(channel[2:])]["location"]["position"]} - ged: {channel_name}'
                )
                plt.ylabel(r"Energy diff / keV")
                plt.plot([0, 1], [0, 1], "b", label="Qbb FWHM keV lin.")
                if quadratic:
                    plt.plot([1, 2], [1, 2], "dodgerblue", label="Qbb FWHM keV quadr.")

                if zoom:
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

                mgt_folder = os.path.join(output_folder, period, f"st{string}")
                if not os.path.exists(mgt_folder):
                    os.makedirs(mgt_folder)
                    logger.debug("...created %s", mgt_folder)

                # ~~~~~~~~~~~~~~~~ save pdfs with plots for an easy/quick access ~~~~~~~~~~~~~~~~
                pdf_name = os.path.join(
                    mgt_folder,
                    f"{period}_string{string}_pos{chmap.map('daq.rawid')[int(channel[2:])]['location']['position']}_{channel_name}_gain_shift.pdf",
                )
                if save_pdf:
                    plt.savefig(pdf_name)

                # pickle and save calibration inputs retrieved ots in a shelve file
                # serialize the plot
                serialized_plot = pickle.dumps(plt.gcf())
                plt.close(fig)
                # store the serialized plot in a shelve object under key
                with shelve.open(
                    os.path.join(output_folder, period, f"{period}_gain_shift"),
                    "c",
                    protocol=pickle.HIGHEST_PROTOCOL,
                ) as shelf:
                    shelf[
                        f'{period}_string{string}_pos{chmap.map("daq.rawid")[int(channel[2:])]["location"]["position"]}_{channel_name}'
                    ] = serialized_plot
                plt.close(fig)

                # structure of pickle files:
                #  - p08_string1_pos1_V02160A
                #  - p08_string1_pos2_V02160B
                #  - ...
                #  - p08_string2_pos1_B00035C
                #  - p08_string2_pos2_C000RG1
                #  - ...

    # parameters (bsln, gain, ...) variations over run
    ylabels = {
        "TrapemaxCtcCal": "Energy diff / keV",
        "Baseline": "Baseline % variations",
    }
    colors = {
        "TrapemaxCtcCal": ["dodgerblue", "b"],
        "Baseline": ["r", "firebrick"],
    }
    percentage = {
        "TrapemaxCtcCal": False,
        "Baseline": True,
    }
    titles = {
        "TrapemaxCtcCal": "Gain",
        "Baseline": "FPGA baseline",
    }
    limits = {
        "TrapemaxCtcCal": None,
        "Baseline": 10,
    }
    for inspected_parameter in ["Baseline", "TrapemaxCtcCal"]:
        for index_i in tqdm(range(len(period_list))):
            period = period_list[index_i]

            (
                geds_df_cuspEmax_abs,
                geds_df_cuspEmax_abs_corr,
                puls_df_cuspEmax_abs,
                geds_df_cuspEmaxCtcCal_abs,
            ) = get_dfs(phy_mtg_data, period, [current_run], inspected_parameter)
            geds_df_trapTmax, geds_df_tp0est, puls_df_trapTmax, puls_df_tp0est = (
                get_traptmax_tp0est(phy_mtg_data, period, [current_run])
            )

            if (
                geds_df_cuspEmax_abs is None
                or geds_df_cuspEmax_abs_corr is None
                or puls_df_cuspEmax_abs is None
            ):
                logger.debug("Dataframes are None for %s!", period)
                continue
            if geds_df_cuspEmax_abs.empty:
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

            string_list = list(str_chns.keys())
            for index_j in tqdm(range(len(string_list))):
                string = string_list[index_j]

                channel_list = str_chns[string]
                for index_k in range(len(channel_list)):
                    channel = channel_list[index_k]
                    channel_name = chmap.map("daq.rawid")[int(channel[2:])]["name"]
                    resampling_time = "1h"
                    if int(channel.split("ch")[-1]) not in list(dfs[0].columns):
                        logger.debug(f"{channel} is not present in the dataframe!")
                        continue

                    logger.debug(f"Inspecting {channel_name} for {inspected_parameter}")
                    pulser_data = get_pulser_data(
                        resampling_time,
                        period,
                        dfs,
                        int(channel.split("ch")[-1]),
                        escale=(
                            escale_val if inspected_parameter == "TrapemaxCtcCal" else 1
                        ),
                    )

                    fig, ax = plt.subplots(figsize=(12, 4))
                    logger.debug("...getting calibration data")
                    pars_data = get_calib_pars(
                        cluster,
                        auto_dir_path,
                        period,
                        [current_run],
                        [channel, channel_name],
                        partition,
                        escale=(
                            escale_val if inspected_parameter == "TrapemaxCtcCal" else 1
                        ),
                        fit=fit_flag,
                    )
                    threshold = (
                        pars_data["res"][0]
                        if inspected_parameter == "TrapemaxCtcCal"
                        else 5
                    )

                    t0 = pars_data["run_start"]
                    if not eval(flag_expr):
                        kevdiff = (
                            pulser_data["ged"]["kevdiff_av"]
                            if pulser_data["diff"]["kevdiff_av"] is None
                            else pulser_data["diff"]["kevdiff_av"]
                        )

                        # check threshold and send automatic mail
                        email_message = legend_data_monitor.utils.check_threshold(
                            kevdiff,
                            pswd_email,
                            last_checked,
                            t0,
                            pars_data,
                            threshold,
                            period,
                            current_run,
                            channel_name,
                            string,
                            email_message,
                            titles[inspected_parameter],
                        )

                        # PULS01ANA has a signal - we can correct GEDS energies for it!
                        # only in the case of energy parameters
                        if (
                            pulser_data["pul_cusp"]["kevdiff_av"] is not None
                            and inspected_parameter == "TrapemaxCtcCal"
                        ):
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
                            if percentage[inspected_parameter] is True:
                                pulser_data["ged"]["kevdiff_av"] = (
                                    pulser_data["ged"]["kevdiff_av"] * 100
                                )
                                pulser_data["ged"]["kevdiff_std"] = (
                                    pulser_data["ged"]["kevdiff_std"] * 100
                                )

                            plt.plot(
                                pulser_data["ged"]["kevdiff_av"].sort_index(),
                                color=colors[inspected_parameter][0],
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

                    # plot resolution only for the energy parameters
                    if inspected_parameter == "TrapemaxCtcCal":
                        plt.plot(
                            [t0[0], t0[0] + pd.Timedelta(days=7)],
                            [pars_data["res"][0] / 2, pars_data["res"][0] / 2],
                            color=colors[inspected_parameter][1],
                            ls="-",
                        )
                        plt.plot(
                            [t0[0], t0[0] + pd.Timedelta(days=7)],
                            [-pars_data["res"][0] / 2, -pars_data["res"][0] / 2],
                            color=colors[inspected_parameter][1],
                            ls="-",
                        )

                        if str(pars_data["res"][0] / 2 * 1.1) != "nan" and 0 < len(
                            pars_data["res"]
                        ) - (xlim_idx - 1):
                            plt.text(
                                t0[0],
                                pars_data["res"][0] / 2 * 1.1,
                                "{:.2f}".format(pars_data["res"][0]),
                                color=colors[inspected_parameter][1],
                            )
                        plt.plot(
                            [0, 1],
                            [0, 1],
                            color=colors[inspected_parameter][1],
                            label="Qbb FWHM keV lin.",
                        )
                    else:
                        plt.plot(
                            [t0[0], t0[0] + pd.Timedelta(days=7)],
                            [limits[inspected_parameter], limits[inspected_parameter]],
                            color=colors[inspected_parameter][1],
                            ls="-",
                        )
                        plt.plot(
                            [t0[0], t0[0] + pd.Timedelta(days=7)],
                            [
                                -limits[inspected_parameter],
                                -limits[inspected_parameter],
                            ],
                            color=colors[inspected_parameter][1],
                            ls="-",
                        )

                    plt.ylabel(ylabels[inspected_parameter])
                    fig.suptitle(
                        f'period: {period} - string: {string} - position: {chmap.map("daq.rawid")[int(channel[2:])]["location"]["position"]} - ged: {channel_name}'
                    )

                    if eval(flag_expr) and zoom is False:
                        plt.ylim(-10, 10)
                    else:
                        bound = np.average(pulser_data["ged"]["kevdiff_std"].dropna())
                        plt.ylim(-2.5 * bound, 2.5 * bound)

                    max_date = pulser_data["ged"]["kevdiff_av"].index.max()
                    time_difference = max_date.tz_localize(None) - t0[
                        -xlim_idx
                    ].tz_localize(None)
                    plt.xlim(
                        t0[0] - pd.Timedelta(hours=0.5),
                        t0[-xlim_idx] + time_difference * 1.5,
                    )
                    plt.legend(loc="lower left")
                    plt.tight_layout()

                    end_folder = os.path.join(
                        output_folder,
                        period,
                        current_run,
                        inspected_parameter,
                    )
                    mgt_folder = os.path.join(end_folder, f"st{string}")
                    if not os.path.exists(mgt_folder):
                        os.makedirs(mgt_folder)
                        logger.debug("...created %s", mgt_folder)

                    # ~~~~~~~~~~~~~~~~ save pdfs with plots for an easy/quick access ~~~~~~~~~~~~~~~~
                    pdf_name = os.path.join(
                        mgt_folder,
                        f"{period}_string{string}_pos{chmap.map('daq.rawid')[int(channel[2:])]['location']['position']}_{channel_name}_gain_shift.pdf",
                    )
                    if save_pdf:
                        plt.savefig(pdf_name)

                    # pickle and save calibration inputs retrieved ots in a shelve file
                    # serialize the plot
                    serialized_plot = pickle.dumps(plt.gcf())
                    plt.close(fig)
                    # store the serialized plot in a shelve object under key
                    with shelve.open(
                        os.path.join(end_folder, f"{period}_gain_shift"),
                        "c",
                        protocol=pickle.HIGHEST_PROTOCOL,
                    ) as shelf:
                        shelf[
                            f'{period}_string{string}_pos{chmap.map("daq.rawid")[int(channel[2:])]["location"]["position"]}_{channel_name}'
                        ] = serialized_plot
                    plt.close(fig)

    if len(email_message) > 1 and pswd_email is not None:
        with open("message.txt", "w") as f:
            for line in email_message:
                f.write(line + "\n")
        legend_data_monitor.utils.send_email_alert(
            pswd_email, ["sofia.calgaro@physik.uzh.ch"], "message.txt"
        )


if __name__ == "__main__":
    main()
