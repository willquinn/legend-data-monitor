from __future__ import annotations

from datetime import datetime

import numpy as np
import pygama.lgdo.lh5_store as lh5

from . import analysis

j_config, j_par, _ = analysis.read_json_files()
keep_puls_pars = j_config[5]["pulser"]["keep_puls_pars"]
keep_phys_pars = j_config[5]["pulser"]["keep_phys_pars"]
no_variation_pars = j_config[5]["plot_values"]["no_variation_pars"]


def load_parameter(
    parameter: str,
    dsp_files: list[str],
    detector: str,
    det_type: str,
    time_cut: list[str],
    all_ievt: np.ndarray,
    puls_only_ievt: np.ndarray,
    not_puls_ievt: np.ndarray,
):
    """
    Load parameters from files.

    Parameters
    ----------
    parameter
                    Parameter to plot
    dsp_files
                    lh5 dsp files
    detector
                    Name of the detector
    det_type
                    Type of detector (geds or spms)
    time_cut
                    List with info about time cuts
    all_ievt
                    Event number for all events
    puls_only_ievt
                    Event number for high energy pulser events
    not_puls_ievt
                    Event number for physical events
    """
    par_array = np.array([])
    utime_array = analysis.build_utime_array(dsp_files, detector, det_type)
    hit_files = [dsp_file.replace("dsp", "hit") for dsp_file in dsp_files]

    if all_ievt != [] and puls_only_ievt != [] and not_puls_ievt != []:
        det_only_index = np.isin(all_ievt, not_puls_ievt)
        puls_only_index = np.isin(all_ievt, puls_only_ievt)

        if parameter in keep_puls_pars:
            utime_array = utime_array[puls_only_index]
        if parameter in keep_phys_pars:
            utime_array = utime_array[det_only_index]

    # cutting time array according to time selection
    utime_array_cut, _ = analysis.time_analysis(utime_array, [], time_cut)

    # to handle particular cases where the timestamp array is outside the time window:
    if len(utime_array_cut) == 0:
        return [], []

    if parameter == "lc":
        par_array = leakage_current(dsp_files, detector, det_type)
    elif parameter == "event_rate":
        par_array, utime_array_cut = event_rate(dsp_files, utime_array_cut, det_type)
    elif parameter == "uncal_puls":
        par_array = lh5.load_nda(dsp_files, ["trapTmax"], detector + "/dsp")["trapTmax"]
    elif parameter == "cal_puls":
        par_array = lh5.load_nda(hit_files, ["cuspEmax_ctc_cal"], detector + "/hit")[
            "cuspEmax_ctc_cal"
        ]
    elif parameter == "bl_difference":
        par_array = bl_difference(dsp_files, detector)
    elif parameter == "AoE":
        par_array = aoe(dsp_files, detector)
    elif parameter == "K_lines":
        par_array = np.array(
            lh5.load_nda(hit_files, ["cuspEmax_ctc_cal"], detector + "/hit")[
                "cuspEmax_ctc_cal"
            ]
        )
        # keep physical events
        if all_ievt != [] and puls_only_ievt != [] and not_puls_ievt != []:
            par_array = par_array[det_only_index]
        # temporal cut
        _, par_array = analysis.time_analysis(utime_array, par_array, time_cut)
        par_array, utime_array_cut = energy_potassium_lines(par_array, utime_array_cut)
    else:
        par_array = lh5.load_nda(dsp_files, [parameter], detector + "/dsp")[parameter]

    if all_ievt != [] and puls_only_ievt != [] and not_puls_ievt != []:
        if parameter in keep_puls_pars:
            if parameter != "K_lines" and parameter != "event_rate":
                par_array = par_array[puls_only_index]
        if parameter in keep_phys_pars:
            if parameter != "K_lines":
                par_array = par_array[det_only_index]

    # Applying Quality Cuts, removing ch010 and ch024 because they are missing in hit tier (why?) 
    # if detector not in ['ch010', 'ch024']:
    #     par_array, utime_array_cut = analysis.apply_quality_cut(hit_files, par_array, utime_array_cut, detector, puls_only_index)

    # cutting time array according to time selection
    no_timecut_pars = ["event_rate", "K_lines"]
    if parameter not in no_timecut_pars:
        _, par_array = analysis.time_analysis(utime_array, par_array, time_cut)

    # check if there are 'nan' values in par_array; if 'yes', remove them
    if np.isnan(par_array).any():
        par_array, utime_array_cut = analysis.remove_nan(par_array, utime_array_cut)    

    # Enable following lines to get the delta of a parameter
    if (parameter not in no_variation_pars) and (det_type != "ch000"):
        cut = int(0.05 * len(par_array))
        par_array_mean = np.mean(par_array[:cut])
        par_array = np.subtract(par_array, par_array_mean)
        par_array = np.divide(par_array, par_array_mean) * 100

    return par_array, utime_array_cut


def bl_difference(dsp_files: list[str], detector: str):
    """
    Return the difference between offline reconstructed baseline (dsp/bl_mean) and baseline from FPGA (dsp/baseline).

    Parameters
    ----------
    dsp_files
               lh5 dsp files
    detector
               Channel of the detector
    """
    fpga_baseline = lh5.load_nda(dsp_files, ["baseline"], detector + "/dsp")["baseline"]
    reconstructed_bl = lh5.load_nda(dsp_files, ["bl_mean"], detector + "/dsp")[
        "bl_mean"
    ]

    return reconstructed_bl - fpga_baseline


def aoe(dsp_files: list[str], detector: str):
    """
    Return the A/E ratio (dsp/A_max divided by dsp/cuspEmax).

    Parameters
    ----------
    dsp_files
               lh5 dsp files
    detector
               Channel of the detector
    """
    a_max = lh5.load_nda(dsp_files, ["A_max"], detector + "/dsp")["A_max"]
    cusp_e_max = lh5.load_nda(dsp_files, ["cuspEmax"], detector + "/dsp")["cuspEmax"]
    aoe = np.divide(a_max, cusp_e_max)

    return aoe


def leakage_current(dsp_files: list[str], detector: str, det_type: str):
    """
    Return the leakage current.

    Parameters
    ----------
    dsp_files
               lh5 dsp files
    detector
               Channel of the detector
    det_type
               Type of detector (geds or spms)
    """
    bl_det = lh5.load_nda(dsp_files, ["baseline"], detector + "/dsp")["baseline"]
    bl_puls = lh5.load_nda(dsp_files, ["baseline"], "ch000/dsp")["baseline"][:100]
    bl_puls_mean = np.mean(bl_puls)
    lc = bl_det - bl_puls_mean

    return (
        lc * 2.5 / 500 / 3 / (2**16)
    )  # using old GERDA (baseline -> lc) conversion factor


def event_rate(dsp_files: list[str], timestamp: list, det_type: str):
    """
    Return the event rate (as cts/dt).

    Parameters
    ----------
    dsp_files
                lh5 dsp files
    timestamp
                List of shifted UTC timestamps
    det_type
                Type of detector (geds or spms)
    """
    rate = []
    times = []

    for dsp_file in dsp_files:
        date_time = (((dsp_file.split("/")[-1]).split("-")[4]).split("Z")[0]).split("T")
        run_start = datetime.strptime(date_time[0] + date_time[1], "%Y%m%d%H%M%S")
        run_start = datetime.timestamp(
            run_start
        )  # in the future, this will be replaced by timestamp[0]

        i = 0
        j = run_start
        dt = j_config[5]["Available-par"]["Other-par"]["event_rate"]["dt"][det_type]

        while j + dt <= timestamp[-1]:
            num = 0
            while timestamp[i] < (j + dt):
                num += 1
                i += 1
            if j != run_start and num != 0:
                rate.append(num / dt)
                times.append(j)
            j += dt

    units = j_config[5]["Available-par"]["Other-par"]["event_rate"]["units"][det_type]
    if units == "mHz":
        fact = 1000
    if units == "Hz":
        fact = 1
    if units == "kHz":
        fact = 0.001

    return np.array(rate) * fact, np.array(times)


def spms_gain(wf_array: np.ndarray):
    """
    Return the spms gain.

    Parameters
    ----------
    wf_array
               Array of arrays, i.e. waveforms
    """
    bl_mean = np.array([np.mean(wf[:100]) for wf in wf_array])
    bl_removed_wf = [wf - bl for (wf, bl) in zip(wf_array, bl_mean)]
    gain = np.array([np.max(wf) for wf in bl_removed_wf])

    return gain


def energy_potassium_lines(par_array: list, timestamp: list):
    """
    Return the energy for events in around K-40 and K-42 lines.

    Parameters
    ----------
    par_array
                Energies (trapEmax) of events
    timestamp
                List of shifted UTC timestamps
    """
    par_list = []
    time_list = []

    for idx, entry in enumerate(par_array):
        if entry > 1430 and entry < 1575:
            par_list.append(entry)
            time_list.append(timestamp[idx])

    return np.array(par_list), np.array(time_list)
