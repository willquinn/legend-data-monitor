from __future__ import annotations

from datetime import datetime

import sys
import numpy as np
import pygama.lgdo.lh5_store as lh5

from . import analysis

j_config, j_par, _ = analysis.read_json_files()
keep_puls = j_config[5]["pulser"]["keep-pulser"]


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
    puls_only_ievt
                Array containing info about pulser event numbers
    """
    par_array = np.array([])
    utime_array = analysis.build_utime_array(dsp_files, detector, det_type)

    if all_ievt!=[] and puls_only_ievt!=[] and not_puls_ievt!=[]:
        det_only_index = np.isin(all_ievt, not_puls_ievt)
        puls_only_index = np.isin(all_ievt, puls_only_ievt)

        if keep_puls is True:
            utime_array = utime_array[puls_only_index]
        if keep_puls is False:
            utime_array = utime_array[det_only_index]

    # cutting time array according to time selection
    utime_array_cut, _ = analysis.time_analysis(utime_array, [], time_cut)

    # to handle particular cases where the timestamp array is outside the time window:
    if len(utime_array_cut) == 0:
        return [], []

    #if parameter == "bl_rms": # <- abbandonata 
    #    par_array = bl_rms(
    #        dsp_files, detector, det_type, puls_only_index
    #    )
    if parameter == "lc":
        par_array = leakage_current(
            dsp_files, detector, det_type
        )
    elif parameter == "event_rate":
        par_array, utime_array_cut = event_rate(
            dsp_files, utime_array_cut, det_type
        )
    elif parameter == "uncal_puls":
        par_array = uncal_pulser(
            dsp_files, detector, puls_only_index
        )
    else:
        par_array = lh5.load_nda(dsp_files, [parameter], detector + "/dsp/")[parameter]

    if all_ievt!=[] and puls_only_ievt!=[] and not_puls_ievt!=[]:
        if keep_puls is True:
            par_array = par_array[puls_only_index]
        if keep_puls is False:
            par_array = par_array[det_only_index]

    # cutting time array according to time selection
    # (we do it here otherwise would arise conflicts with
    # in the above few lines because of cut done with 'puls_only_index')
    _, par_array = analysis.time_analysis(utime_array, par_array, time_cut)

    # Enable following lines to get the delta of a parameter
    #base = lh5.load_nda(dsp_files, ["baseline"], detector + "/dsp/")["baseline"]
    par_array_mean = np.mean(par_array[:1000]) # mean over first X data
    par_array = np.subtract(par_array, par_array_mean)

    # check if there are 'nan' values in par_array
    par_array, utime_array_cut = analysis.remove_nan_values(
        par_array, utime_array_cut
    )

    return par_array, utime_array_cut

"""
def bl_rms(
    raw_files: list[str],
    detector: str,
    det_type: str,
    puls_only_index: np.ndarray,
):
    #Return the RMS of the normalized baseline.
    if det_type == "spms":
        wf_det = lh5.load_nda(raw_files, ["values"], detector + "/raw/waveform/")[
            "values"
        ]
    if det_type == "geds":
        wf_det = lh5.load_nda(raw_files, ["values"], detector + "/raw/waveform/")[
            "values"
        ]

    wf_puls = wf_det[puls_only_index][:100]
    wf_samples = 1000
    array_rms = [np.sqrt(np.mean(waveform[:wf_samples] ** 2)) for waveform in wf_det]
    pulser_rms = [np.sqrt(np.mean(waveform[:wf_samples] ** 2)) for waveform in wf_puls]
    puls_mean = np.mean(pulser_rms)
    bl_norm = [ged_rms / puls_mean for ged_rms in array_rms]

    return np.array(bl_norm)
"""

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


def uncal_pulser(dsp_files: list[str], detector: str, puls_only_index: np.ndarray):
    """
    Return the uncalibrated pulser value.

    Parameters
    ----------
    dsp_files
                      lh5 dsp files
    detector
                      Channel of the detector
    puls_only_index
                      Index for pulser only entries
    """
    if "trapEmax" not in lh5.ls(dsp_files, f"{detector}/dsp/"):
        return []
    puls_energy = lh5.load_nda(dsp_files, ["trapEmax"], detector + "/data")["trapEmax"]

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
