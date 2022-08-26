from __future__ import annotations

from datetime import datetime

import numpy as np
import pygama.lgdo.lh5_store as lh5

from . import analysis

j_config, j_par, _ = analysis.read_json_files()


def load_parameter(
    parameter: str,
    raw_file: str,
    dsp_file: str,
    detector: str,
    det_type: str,
    time_cut: list[str],
    raw_files: list,
    puls_only_ievt: np.ndarray,
    not_puls_ievt: np.ndarray,
):
    """
    Load parameters from files.

    Parameters
    ----------
    parameter
                Parameter to plot
    raw_file
                Single lh5 raw file
    dsp_file
                Single lh5 dsp file
    detector
                Name of the detector
    det_type
                Type of detector (geds or spms)
    time_cut
                List with info about time cuts
    puls_only_ievt
                Array containing info about pulser event numbers
    """
    par_array = np.array([])
    utime_array = analysis.build_utime_array(raw_file, detector, det_type)

    det_and_puls_ievt = lh5.load_nda(raw_file, ["eventnumber"], f"{detector}/raw")[
        "eventnumber"
    ]
    det_only_index = np.isin(det_and_puls_ievt, not_puls_ievt)
    puls_only_index = np.isin(det_and_puls_ievt, puls_only_ievt)

    keep_puls = j_config[5]["pulser"]["keep-pulser"]
    if parameter != "uncal_puls":
        if keep_puls is True:
            utime_array = utime_array[puls_only_index]
        if keep_puls is False:
            utime_array = utime_array[det_only_index]

    # cutting time array according to time selection
    utime_array_cut, _ = analysis.time_analysis(utime_array, [], time_cut)

    # to handle particular cases where the timestamp array is outside the time window:
    if len(utime_array_cut) == 0:
        return [], []

    if parameter == "bl_rms":
        par_array = bl_rms(raw_file, detector, det_type, puls_only_index, raw_files)
    elif parameter == "delta_bl_std":
        par_array = delta_bl_std(
            raw_file, detector, det_type, puls_only_index, raw_files
        )
    elif parameter == "lc":
        par_array = leakage_current(raw_file, detector, det_type, raw_files)
    elif parameter == "delta_bl_mean":
        par_array = delta_bl_mean(raw_file, detector, det_type, raw_files)
    elif parameter == "event_rate":
        par_array, utime_array_cut = event_rate(raw_file, utime_array_cut, det_type)
    elif parameter == "uncal_puls":
        par_array = uncal_pulser(dsp_file, detector, puls_only_index)
    else:
        par_array = analysis.build_par_array(
            raw_file, dsp_file, parameter, detector, det_type, raw_files
        )

    if parameter != "uncal_puls" and parameter != "event_rate":
        if keep_puls is True:
            par_array = par_array[puls_only_index]
        if keep_puls is False:
            par_array = par_array[det_only_index]

        # cutting time array according to time selection
        # (we do it here otherwise would arise conflicts with
        # in the above few lines because of cut done with 'puls_only_index')
        _, par_array = analysis.time_analysis(utime_array, par_array, time_cut)

    # check if there are 'nan' values in par_array (only for dsp parameters)
    if j_par[0][parameter]["tier"] == 2:
        par_array, utime_array_cut = analysis.remove_nan_values(
            par_array, utime_array_cut
        )

    return par_array, utime_array_cut


def bl_rms(
    raw_file: str,
    detector: str,
    det_type: str,
    puls_only_index: np.ndarray,
    raw_files: list[str],
):
    """
    Return the RMS of the normalized baseline.

    Parameters
    ----------
    raw_file
                      String of lh5 raw file
    detector
                      Channel of the detector
    det_type
                      Type of detector (geds or spms)
    puls_only_index
                      Index for pulser only entries
    """
    if det_type == "spms":
        wf_det = lh5.load_nda(raw_file, ["values"], detector + "/raw/waveform/")[
            "values"
        ]
    if det_type == "geds":
        wf_det = lh5.load_nda(raw_file, ["values"], detector + "/raw/waveform/")[
            "values"
        ]

    wf_puls = wf_det[puls_only_index][:100]
    wf_samples = 1000
    array_rms = [np.sqrt(np.mean(waveform[:wf_samples] ** 2)) for waveform in wf_det]
    pulser_rms = [np.sqrt(np.mean(waveform[:wf_samples] ** 2)) for waveform in wf_puls]
    puls_mean = np.mean(pulser_rms)
    bl_norm = [ged_rms / puls_mean for ged_rms in array_rms]
    return np.array(bl_norm)


def delta_bl_std(
    raw_file: str,
    detector: str,
    det_type: str,
    puls_only_index: np.ndarray,
    raw_files: list[str],
):
    """
    Returns the difference with respect to the average value evaluated over the whole time window.
    """
    # mean over the whole time window
    dsp_files = [raw.replace("raw", "dsp") for raw in raw_files]
    bl_std_all = lh5.load_nda(dsp_files, ["bl_std"], detector + "/dsp")["bl_std"]
    # bl_std_mean = np.mean(bl_std_all)

    # dsp values for a given file
    dsp_file = raw_file.replace("raw", "dsp")
    bl_std = lh5.load_nda(dsp_file, ["bl_std"], detector + "/dsp")["bl_std"]
    bl_std_mean = np.mean(bl_std)

    # baseline difference
    diff = bl_std - bl_std_mean

    return np.array(diff)


def leakage_current(raw_file: str, detector: str, det_type: str, raw_files: list[str]):
    """
    Return the leakage current.

    Parameters
    ----------
    raw_file
               String of lh5 raw file
    detector
               Channel of the detector
    det_type
               Type of detector (geds or spms)
    """
    bl_det = lh5.load_nda(raw_file, ["baseline"], detector + "/raw")["baseline"]
    bl_puls = lh5.load_nda(raw_file, ["baseline"], "ch000/raw")["baseline"][:100]
    bl_puls_mean = np.mean(bl_puls)
    lc = bl_det - bl_puls_mean

    return (
        lc * 2.5 / 500 / 3 / (2**16)
    )  # using old GERDA (baseline -> lc) conversion factor


def delta_bl_mean(raw_file: str, detector: str, det_type: str, raw_files: list[str]):
    """
    Return the difference with respect to the average value evaluated over the whole time window.
    """
    # mean over the whole time window
    dsp_files = [raw.replace("raw", "dsp") for raw in raw_files]
    bl_mean_all = lh5.load_nda(dsp_files, ["bl_mean"], detector + "/dsp")["bl_mean"]
    # bl_puls_mean = np.mean(bl_mean_all)

    # dsp values for a given file
    dsp_file = raw_file.replace("raw", "dsp")
    bl_mean = lh5.load_nda(dsp_file, ["bl_mean"], detector + "/dsp")["bl_mean"]
    bl_puls_mean = np.mean(bl_mean)

    # baseline difference
    diff = bl_mean - bl_puls_mean

    return diff


def event_rate(raw_run: str, timestamp: list, det_type: str):
    """
    Return the event rate (as cts/dt).

    Parameters
    ----------
    raw_run
                String of lh5 raw file
    timestamp
                List of shifted UTC timestamps
    det_type
                Type of detector (geds or spms)
    """
    rate = []
    times = []

    date_time = (((raw_run.split("/")[-1]).split("-")[4]).split("Z")[0]).split("T")
    run_start = datetime.strptime(date_time[0] + date_time[1], "%Y%m%d%H%M%S")
    run_start = datetime.timestamp(run_start)

    i = 0
    j = run_start
    dt = j_config[5]["Available-par"]["Other-par"]["event_rate"]["dt"][det_type]

    while j + dt <= timestamp[-1]:
        num = 0
        while timestamp[i] < (j + dt):
            num += 1
            i += 1
        if j != run_start:
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


def uncal_pulser(dsp_file: str, detector: str, puls_only_index: np.ndarray):
    """
    Return the uncalibrated pulser value.

    Parameters
    ----------
    dsp_file
                      String of lh5 dsp file
    detector
                      Channel of the detector
    puls_only_index
                      Index for pulser only entries
    """
    if "trapEmax" not in lh5.ls(dsp_file, f"{detector}/dsp/"):
        return []
    puls_energy = lh5.load_nda(dsp_file, ["trapEmax"], detector + "/data")["trapEmax"]

    if len(puls_energy) == 2 * len(puls_only_index):
        puls_energy = puls_energy[: len(puls_only_index)]
    puls_energy = puls_energy[puls_only_index]

    puls_mean = np.mean(puls_energy[:100])
    puls_energy_sub = np.array([en - puls_mean for en in puls_energy])

    return puls_energy_sub


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
