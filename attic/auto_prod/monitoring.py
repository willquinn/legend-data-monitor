#
# Big part of the code made by William Quinn - this is an adaptation to read auto monitoring hdf files for phy data
# and automatically create monitoring plots that'll be lared uploaded in the dashboard.
# !!! this is not taking account of global pulser spike tagging
#

import json
import os

import lgdo.lh5_store as lh5
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tqdm.notebook import tqdm

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
# matplotlib.rcParams['font.family'] = 'STIXGeneral'

marker_size = 2
line_width = 0.5
cap_size = 0.5
cap_thick = 0.5

# colors = cycler('color', ['b', 'g', 'r', 'm', 'y', 'k', 'c', '#8c564b'])
plt.rc("axes", facecolor="white", edgecolor="black", axisbelow=True, grid=True)


def get_calib_pars(
    period,
    run_list,
    channel,
    partition,
    escale=2039,
    fit="linear",
    path="/data2/public/prodenv/prod-blind/tmp/auto",
):  #'/data2/public/prodenv/prod-blind/ref/v02.00'):
    sto = lh5.LH5Store()

    calib_data = {
        "fep": [],
        "cal_const": [],
        "run_start": [],
        "run_end": [],
        "res": [],
        "res_quad": [],
    }

    tier = "pht" if partition is True else "hit"
    key_result = "partition_ecal" if partition is True else "ecal"

    for run in run_list:
        prod_ref = path
        timestamp = os.listdir(f"{path}/generated/par/{tier}/cal/{period}/{run}")[
            -1
        ].split("-")[-2]
        if tier == "pht":
            pars = json.load(
                open(
                    f"{path}/generated/par/{tier}/cal/{period}/{run}/l200-{period}-{run}-cal-{timestamp}-par_{tier}.json"
                )
            )
        else:
            pars = json.load(
                open(
                    f"{path}/generated/par/{tier}/cal/{period}/{run}/l200-{period}-{run}-cal-{timestamp}-par_{tier}_results.json"
                )
            )

        # for FEP peak, we want to look at the behaviour over time --> take 'ecal' results (not partition ones!)
        if tier == "pht":
            try:
                fep_peak_pos = pars[channel]["results"]["ecal"]["cuspEmax_ctc_cal"][
                    "pk_fits"
                ]["2614.5"]["parameters_in_ADC"]["mu"]
                fep_gain = fep_peak_pos / 2614.5
            except:
                fep_peak_pos = 0
                fep_gain = 0
        else:
            try:
                fep_peak_pos = pars[channel]["ecal"]["cuspEmax_ctc_cal"][
                    "peak_fit_pars"
                ]["2614.5"][1]
                fep_gain = fep_peak_pos / 2614.5
            except:
                fep_peak_pos = 0
                fep_gain = 0

        if tier == "pht":
            try:
                if fit == "linear":
                    Qbb_fwhm = pars[channel]["results"][key_result]["cuspEmax_ctc_cal"][
                        "eres_linear"
                    ]["Qbb_fwhm(keV)"]
                    Qbb_fwhm_quad = pars[channel]["results"][key_result][
                        "cuspEmax_ctc_cal"
                    ]["eres_quadratic"]["Qbb_fwhm(keV)"]
                else:
                    Qbb_fwhm = pars[channel]["results"][key_result]["cuspEmax_ctc_cal"][
                        "eres_quadratic"
                    ]["Qbb_fwhm(keV)"]
            except:
                Qbb_fwhm = np.nan
        else:
            try:
                Qbb_fwhm = pars[channel][key_result]["cuspEmax_ctc_cal"]["Qbb_fwhm"]
                Qbb_fwhm_quad = np.nan
            except:
                Qbb_fwhm = np.nan
                Qbb_fwhm_quad = np.nan

        pars = json.load(
            open(
                f"{path}/generated/par/{tier}/cal/{period}/{run}/l200-{period}-{run}-cal-{timestamp}-par_{tier}.json"
            )
        )

        if tier == "pht":
            try:
                cal_const_a = pars[channel]["pars"]["operations"]["cuspEmax_ctc_cal"][
                    "parameters"
                ]["a"]
                cal_const_b = pars[channel]["pars"]["operations"]["cuspEmax_ctc_cal"][
                    "parameters"
                ]["b"]
                cal_const_c = pars[channel]["pars"]["operations"]["cuspEmax_ctc_cal"][
                    "parameters"
                ]["c"]
                fep_cal = (
                    cal_const_c
                    + fep_peak_pos * cal_const_b
                    + cal_const_a * fep_peak_pos**2
                )
            except:
                fep_cal = np.nan
        else:
            try:
                cal_const_a = pars[channel]["operations"]["cuspEmax_ctc_cal"][
                    "parameters"
                ]["a"]
                cal_const_b = pars[channel]["operations"]["cuspEmax_ctc_cal"][
                    "parameters"
                ]["b"]
                if period in ["p07"] or (period == "p06" and run == "r005"):
                    cal_const_c = pars[channel]["operations"]["cuspEmax_ctc_cal"][
                        "parameters"
                    ]["c"]
                    fep_cal = (
                        cal_const_c
                        + fep_peak_pos * cal_const_b
                        + cal_const_a * fep_peak_pos**2
                    )
                else:
                    fep_cal = cal_const_b + cal_const_a * fep_peak_pos
            except:
                fep_cal = np.nan

        if run not in os.listdir(f"{prod_ref}/generated/tier/dsp/phy/{period}"):
            # get timestamp for additional-final cal run (only for FEP gain display)
            run_files = sorted(
                os.listdir(f"{prod_ref}/generated/tier/dsp/cal/{period}/{run}/")
            )
            run_end_time = pd.to_datetime(
                sto.read_object(
                    "ch1027201/dsp/timestamp",
                    f"{prod_ref}/generated/tier/dsp/cal/{period}/{run}/"
                    + run_files[-1],
                )[0][-1],
                unit="s",
            )
            run_start_time = run_end_time
            Qbb_fwhm = np.nan
            Qbb_fwhm_quad = np.nan
        else:
            run_files = sorted(
                os.listdir(f"{prod_ref}/generated/tier/dsp/phy/{period}/{run}/")
            )
            run_start_time = pd.to_datetime(
                sto.read_object(
                    "ch1027201/dsp/timestamp",
                    f"{prod_ref}/generated/tier/dsp/phy/{period}/{run}/" + run_files[0],
                )[0][0],
                unit="s",
            )
            run_end_time = pd.to_datetime(
                sto.read_object(
                    "ch1027201/dsp/timestamp",
                    f"{prod_ref}/generated/tier/dsp/phy/{period}/{run}/"
                    + run_files[-1],
                )[0][-1],
                unit="s",
            )

        calib_data["fep"].append(fep_gain)
        calib_data["cal_const"].append(fep_cal)
        calib_data["run_start"].append(run_start_time)
        calib_data["run_end"].append(run_end_time)
        calib_data["res"].append(Qbb_fwhm)
        calib_data["res_quad"].append(Qbb_fwhm_quad)

    print(channel, calib_data["res"])

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
    phy_mtg_data = os.path.join(phy_mtg_data, period)
    runs = os.listdir(phy_mtg_data)
    geds_df_cuspEmax_abs = pd.DataFrame()
    geds_df_cuspEmax_var = pd.DataFrame()
    geds_df_cuspEmax_abs_corr = pd.DataFrame()
    geds_df_cuspEmax_var_corr = pd.DataFrame()
    puls_df_cuspEmax_abs = pd.DataFrame()
    puls_df_cuspEmax_var = pd.DataFrame()

    for r in runs:
        # keep only specified runs
        if r not in run_list:
            continue
        files = os.listdir(os.path.join(phy_mtg_data, r))
        # get only geds files
        hdf_geds = [f for f in files if "hdf" in f and "geds" in f]
        if len(hdf_geds) == 0:
            return None, None, None
        hdf_geds = os.path.join(phy_mtg_data, r, hdf_geds[0])  # should be 1
        # get only puls files
        hdf_puls = [f for f in files if "hdf" in f and "pulser01ana" in f]
        hdf_puls = os.path.join(phy_mtg_data, r, hdf_puls[0])  # should be 1

        # GEDS DATA ========================================================================================================
        geds_abs = pd.read_hdf(hdf_geds, key=f"IsPulser_Cuspemax")
        geds_df_cuspEmax_abs = pd.concat(
            [geds_df_cuspEmax_abs, geds_abs], ignore_index=False, axis=0
        )
        # GEDS PULS-CORRECTED DATA =========================================================================================
        geds_puls_abs = pd.read_hdf(hdf_geds, key=f"IsPulser_Cuspemax_pulser01anaDiff")
        geds_df_cuspEmax_abs_corr = pd.concat(
            [geds_df_cuspEmax_abs_corr, geds_puls_abs], ignore_index=False, axis=0
        )
        # PULS DATA ========================================================================================================
        puls_abs = pd.read_hdf(hdf_puls, key=f"IsPulser_Cuspemax")
        puls_df_cuspEmax_abs = pd.concat(
            [puls_df_cuspEmax_abs, puls_abs], ignore_index=False, axis=0
        )

    return geds_df_cuspEmax_abs, geds_df_cuspEmax_abs_corr, puls_df_cuspEmax_abs


def get_pulser_data(period, dfs, channel, escale):

    ser_pul_cusp = dfs[2][1027203]  # selection of pulser channel
    ser_ged_cusp = dfs[0][channel]  # selection of ged channel

    ser_ged_cusp = ser_ged_cusp.dropna()
    ser_pul_cusp = ser_pul_cusp.loc[ser_ged_cusp.index]
    hour_counts = ser_pul_cusp.resample("H").count() >= 100

    ged_cusp_av = np.average(
        ser_ged_cusp.values[:360]
    )  # switch to first 10% of available time interval?
    pul_cusp_av = np.average(ser_pul_cusp.values[:360])
    # first entries of dataframe are NaN ... how to solve it?
    if np.isnan(ged_cusp_av):
        print("the average is a nan")
        print(ser_pul_cusp_without_nan)
        return None

    ser_ged_cuspdiff = pd.Series(
        (ser_ged_cusp.values - ged_cusp_av) / ged_cusp_av,
        index=ser_ged_cusp.index.values,
    ).dropna()
    ser_pul_cuspdiff = pd.Series(
        (ser_pul_cusp.values - pul_cusp_av) / pul_cusp_av,
        index=ser_pul_cusp.index.values,
    ).dropna()
    ser_ged_cuspdiff_kev = pd.Series(
        ser_ged_cuspdiff * escale, index=ser_ged_cuspdiff.index.values
    )
    ser_pul_cuspdiff_kev = pd.Series(
        ser_pul_cuspdiff * escale, index=ser_pul_cuspdiff.index.values
    )

    # is_valid = (df_ged.tp_0_est < 5e4) & (df_ged.tp_0_est > 4.8e4) & (df_ged.trapTmax > 200) # global pulser removal (these columns are not present in our dfs)

    ged_cusp_hr_av_ = ser_ged_cuspdiff_kev.resample("H").mean()
    ged_cusp_hr_av_[~hour_counts.values] = np.nan
    ged_cusp_hr_std = ser_ged_cuspdiff_kev.resample("H").std()
    ged_cusp_hr_std[~hour_counts.values] = np.nan
    pul_cusp_hr_av_ = ser_pul_cuspdiff_kev.resample("H").mean()
    pul_cusp_hr_av_[~hour_counts.values] = np.nan
    pul_cusp_hr_std = ser_pul_cuspdiff_kev.resample("H").std()
    pul_cusp_hr_std[~hour_counts.values] = np.nan

    ged_cusp_corr = ser_ged_cuspdiff - ser_pul_cuspdiff
    ged_cusp_corr = pd.Series(ged_cusp_corr[ser_ged_cuspdiff.index.values])
    ged_cusp_corr_kev = ged_cusp_corr * escale
    ged_cusp_corr_kev = pd.Series(ged_cusp_corr_kev[ged_cusp_corr.index.values])
    ged_cusp_cor_hr_av_ = ged_cusp_corr_kev.resample("H").mean()
    ged_cusp_cor_hr_av_[~hour_counts.values] = np.nan
    ged_cusp_cor_hr_std = ged_cusp_corr_kev.resample("H").std()
    ged_cusp_cor_hr_std[~hour_counts.values] = np.nan

    return {
        "ged": {
            "cusp": ser_ged_cusp,
            "cuspdiff": ser_ged_cuspdiff,
            "cuspdiff_kev": ser_ged_cuspdiff_kev,
            "cusp_av": ged_cusp_hr_av_,
            "cusp_std": ged_cusp_hr_std,
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


def stability(
    phy_mtg_data,
    output_folder,
    dataset,
    chmap,
    str_chns,
    xlim_idx,
    partition=False,
    quadratic=False,
    zoom=True,
):

    period_list = list(dataset.keys())
    for index_i in tqdm(range(len(period_list))):
        period = period_list[index_i]
        run_list = dataset[period]

        geds_df_cuspEmax_abs, geds_df_cuspEmax_abs_corr, puls_df_cuspEmax_abs = get_dfs(
            phy_mtg_data, period, run_list
        )
        if (
            geds_df_cuspEmax_abs is None
            or geds_df_cuspEmax_abs_corr is None
            or puls_df_cuspEmax_abs is None
        ):
            continue
        dfs = [geds_df_cuspEmax_abs, geds_df_cuspEmax_abs_corr, puls_df_cuspEmax_abs]

        string_list = list(str_chns.keys())
        for index_j in tqdm(range(len(string_list))):
            string = string_list[index_j]

            channel_list = str_chns[string]
            do_channel = True
            for index_k in range(len(channel_list)):
                channel = channel_list[index_k]
                pulser_data = get_pulser_data(
                    period, dfs, int(channel.split("ch")[-1]), escale=2039
                )
                if pulser_data is None:
                    continue

                fig, ax = plt.subplots(figsize=(12, 4))

                pars_data = get_calib_pars(
                    period, run_list, channel, partition, escale=2039
                )

                if channel != "ch1120004":

                    # plt.plot(pulser_data['ged']['cusp_av'], 'C0', label='GED')
                    plt.plot(
                        pulser_data["pul_cusp"]["kevdiff_av"], "C2", label="PULS01"
                    )
                    plt.plot(
                        pulser_data["diff"]["kevdiff_av"], "C4", label="GED corrected"
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
                    plt.axvline(ti, color="k")

                t0 = pars_data["run_start"]
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
                                "y-",
                            )
                            plt.plot(
                                [t0[i], t0[i] + pd.Timedelta(days=7)],
                                [
                                    -pars_data["res_quad"][i] / 2,
                                    -pars_data["res_quad"][i] / 2,
                                ],
                                "y-",
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
                                "y-",
                            )
                            plt.plot(
                                [t0[i], t0[i + 1]],
                                [
                                    -pars_data["res_quad"][i] / 2,
                                    -pars_data["res_quad"][i] / 2,
                                ],
                                "y-",
                            )
                    if str(pars_data["res"][i] / 2 * 1.1) != "nan" and i < len(
                        pars_data["res"]
                    ) - (xlim_idx - 1):
                        plt.text(
                            t0[i],
                            pars_data["res"][i] / 2 * 1.1,
                            "{:.2f}".format(pars_data["res"][i]),
                        )

                    if quadratic:
                        if str(pars_data["res_quad"][i] / 2 * 1.5) != "nan" and i < len(
                            pars_data["res"]
                        ) - (xlim_idx - 1):
                            plt.text(
                                t0[i],
                                pars_data["res_quad"][i] / 2 * 1.5,
                                "{:.2f} (Q)".format(pars_data["res_quad"][i]),
                            )

                fig.suptitle(
                    f'period: {period} string: {string} ged: {chmap.map("daq.rawid")[int(channel[2:])]["name"]}'
                )
                plt.ylabel(r"Energy diff / keV")
                plt.plot([0, 1], [0, 1], "b", label="Qbb FWHM keV (linear)")
                my_det = chmap.map("daq.rawid")[int(channel[2:])]["name"]
                if quadratic:
                    plt.plot([1, 2], [1, 2], "y", label="Qbb FWHM keV (quadratic)")

                if zoom:
                    bound = np.average(pulser_data["diff"]["kevdiff_std"].dropna())
                    if chmap.map("daq.rawid")[int(channel[2:])]["name"] == "B00089D":
                        plt.ylim(-3, 3)
                    else:
                        plt.ylim(-2.5 * bound, 2.5 * bound)
                plt.xlim(
                    t0[0] - pd.Timedelta(hours=20), t0[-xlim_idx] + pd.Timedelta(days=7)
                )
                plt.legend(loc="lower left")
                plt.tight_layout()
                if not os.path.exists(f"{output_folder}/{period}/st{string}"):
                    os.makedirs(f"{output_folder}/{period}/st{string}")
                    print(f"...created {output_folder}/{period}/st{string}")
                plt.savefig(
                    f'{output_folder}/{period}/st{string}/{period}_string{string}_pos{chmap.map("daq.rawid")[int(channel[2:])]["location"]["position"]}_{chmap.map("daq.rawid")[int(channel[2:])]["name"]}_gain_shift.pdf'
                )
                plt.close(fig)
