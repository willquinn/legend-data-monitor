from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pygama.lgdo.lh5_store as lh5

from . import analysis

j_config, j_par, _ = analysis.read_json_files()
keep_puls_pars = j_config[5]["pulser"]["keep_puls_pars"]
keep_phys_pars = j_config[5]["pulser"]["keep_phys_pars"]
no_variation_pars = j_config[5]["plot_values"]["no_variation_pars"]
qc_flag = j_config[5]["quality_cuts"]


def load_parameter(
    parameter: str,
    dsp_files: list[str],
    detector: str,
    det_type: str,
    time_cut: list[str],
    all_ievt: np.ndarray,
    puls_only_ievt: np.ndarray,
    not_puls_ievt: np.ndarray,
    start_code: str,
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
                    Name of the aoe
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
    start_code
                    Starting time of the code
    """
    no_cut_pars = ["event_rate", "K_lines"]
    par_array = np.array([])
    utime_array = lh5.load_nda(dsp_files, ["timestamp"], detector + "/dsp")["timestamp"]
    hit_files = [dsp_file.replace("dsp", "hit") for dsp_file in dsp_files]

    if all_ievt != [] and puls_only_ievt != [] and not_puls_ievt != []:
        det_only_index = np.isin(all_ievt, not_puls_ievt)
        puls_only_index = np.isin(all_ievt, puls_only_ievt)
        if parameter in keep_puls_pars:
            utime_array = utime_array[puls_only_index]
        if parameter in keep_phys_pars:
            utime_array = utime_array[det_only_index]

    # apply quality cuts to the time array
    if qc_flag[det_type] is True:
        if parameter in keep_puls_pars:
            keep_evt_index = puls_only_index
        elif parameter in keep_phys_pars:
            keep_evt_index = det_only_index
        else:
            keep_evt_index = []
        quality_index = analysis.get_qc_ievt(hit_files, detector, keep_evt_index)
        utime_array = utime_array[quality_index]

    # cutting time array according to time selection
    utime_array_cut, _ = analysis.time_analysis(utime_array, [], time_cut, start_code)

    # to handle particular cases where the timestamp array is outside the time window:
    if len(utime_array_cut) == 0:
        return [], [], []

    if parameter == "lc":
        par_array = leakage_current(dsp_files, detector, det_type)
    elif parameter == "event_rate":
        par_array, utime_array_cut = event_rate(dsp_files, utime_array, utime_array_cut, detector, det_type, all_ievt, puls_only_ievt, not_puls_ievt, time_cut, start_code)
    elif parameter == "uncal_puls":
        par_array = lh5.load_nda(dsp_files, ["trapTmax"], detector + "/dsp")["trapTmax"]
    elif parameter == "cal_puls":
        par_array = lh5.load_nda(hit_files, ["cuspEmax_ctc_cal"], detector + "/hit")[
            "cuspEmax_ctc_cal"
        ]
    elif parameter == "AoE_Classifier":
        par_array = lh5.load_nda(hit_files, ["AoE_Classifier"], detector + "/hit")[
            "AoE_Classifier"
        ]
    elif parameter == "AoE_Corrected":
        par_array = np.array(
            lh5.load_nda(hit_files, ["AoE_Corrected"], detector + "/hit")[
                "AoE_Corrected"
            ]
        )
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
        _, par_array = analysis.time_analysis(
            utime_array, par_array, time_cut, start_code
        )
        par_array, utime_array_cut = energy_potassium_lines(par_array, utime_array_cut)
    elif parameter == "AoE_Classifier":
        par_array = np.array(
            lh5.load_nda(hit_files, ["AoE_Classifier"], detector + "/hit")[
                "AoE_Classifier"
            ]
        )
    else:
        par_array = lh5.load_nda(dsp_files, [parameter], detector + "/dsp")[parameter]
        if parameter == "wf_max":
            baseline = lh5.load_nda(dsp_files, ["baseline"], "ch000/dsp")["baseline"]
            par_array = np.subtract(par_array, baseline)

    if all_ievt != [] and puls_only_ievt != [] and not_puls_ievt != []:
        if parameter in keep_puls_pars:
            if parameter not in no_cut_pars:
                par_array = par_array[puls_only_index]
        if parameter in keep_phys_pars:
            if parameter not in no_cut_pars:
                par_array = par_array[det_only_index]

    # apply quality cuts to the parameter array
    if qc_flag[det_type] is True and parameter not in no_cut_pars:
        par_array = par_array[quality_index]

    # cutting parameter array according to time selection
    if parameter not in no_cut_pars:
        _, par_array = analysis.time_analysis(
            utime_array, par_array, time_cut, start_code
        )

    # check if there are 'nan' values in par_array; if yes, remove them
    if np.isnan(par_array).any():
        par_array, utime_array_cut = analysis.remove_nan(par_array, utime_array_cut)

    # Enable following lines to get the % variation of a parameter wrt to its mean value
    if parameter not in no_variation_pars and det_type not in ["spms", "ch000"]:
        par_array_mean = np.mean(par_array[: int(0.05 * len(par_array))])
        # par_array_mean = analysis.get_mean(parameter, detector)
        par_array = np.subtract(par_array, par_array_mean)
        par_array = np.divide(par_array, par_array_mean) * 100
    else:
        par_array_mean = []

    return par_array_mean, par_array, utime_array_cut


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


def event_rate(dsp_files: list[str], utime_array: list, timestamp: list, detector: str, det_type: str, all_ievt: np.ndarray, puls_only_ievt: np.ndarray, not_puls_ievt: np.ndarray, time_cut: list[str], start_code: str):
    """
    Return the event rate (as cts/dt).

    Parameters
    ----------
    dsp_files
                lh5 dsp files
    utime_array
                List of shifted UTC timestamps - no time cut applied
    timestamp
                List of shifted UTC timestamps
    detector
                Channel of the detector
    det_type
                Type of detector (geds or spms)
    all_ievt
                Event number for all events
    puls_only_ievt
                Event number for high energy pulser events
    not_puls_ievt
                Event number for physical events
    time_cut
                List with info about time cuts    
    start_code
                Starting time of the code
    """
    rate = []
    times = []

    # for spms, we keep timestamp entries only if there's a non-null energy release 
    if det_type=="spms":
        energies = lh5.load_nda(dsp_files, ["energies"], detector+"/dsp")["energies"]

        # remove nan entries
        energies = [entry[~np.isnan(entry)] for entry in energies] 
        new_energies=[]
        for entry in energies:
            if np.size(entry)==0:
                new_energies.append(False)
            else:
                new_energies.append(True)
        energies = np.array(new_energies)
        if len(energies)==0:
            return np.zeros(len(timestamp)), np.array(timestamp)

        # apply pulser cut
        if all_ievt != [] and puls_only_ievt != [] and not_puls_ievt != []:
            det_only_index = np.isin(all_ievt, not_puls_ievt)
            puls_only_index = np.isin(all_ievt, puls_only_ievt)
            if "event_rate" in keep_puls_pars:
                energies = energies[puls_only_index]
            if "event_rate" in keep_phys_pars:
                energies = energies[det_only_index]
        if len(energies)==0:
            return np.zeros(len(timestamp)), np.array(timestamp)

        # apply quality cuts
        if qc_flag[det_type] is True:
            if "event_rate" in keep_puls_pars:
                keep_evt_index = puls_only_index
            elif "event_rate" in keep_phys_pars:
                keep_evt_index = det_only_index
            else:
                keep_evt_index = []
            hit_files = [dsp_file.replace("dsp", "hit") for dsp_file in dsp_files]
            quality_index = analysis.get_qc_ievt(hit_files, detector, keep_evt_index)
            energies = energies[quality_index]
            if len(energies)==0:
                return np.zeros(len(timestamp)), np.array(timestamp)

        # apply time cut
        timestamp, energies = analysis.time_analysis(utime_array, energies, time_cut, start_code)
        if len(energies)==0:
            return np.zeros(len(timestamp)), np.array(timestamp)
        
        timestamp = timestamp[energies]
        if len(timestamp)==0:
            return np.array([]), np.array([])

    date_time = (((dsp_files[0].split("/")[-1]).split("-")[4]).split("Z")[0]).split("T")
    run_start = datetime.strptime(date_time[0] + date_time[1], "%Y%m%d%H%M%S")
    run_start = datetime.strptime(str(run_start), "%Y-%m-%d %H:%M:%S")

    i = 0
    j = datetime.timestamp(run_start + timedelta(days=0, hours=2, minutes=0))
    dt = j_config[5]["Available-par"]["Other-par"]["event_rate"]["dt"]

    while j + dt <= timestamp[-1]:
        num = 0
        while timestamp[i] < (j + dt):
            num += 1
            i += 1
        if j != run_start:
            rate.append(num / dt)
            times.append(j)
        j += dt

    units = j_config[5]["Available-par"]["Other-par"]["event_rate"]["units"]
    if units == "mHz":
        fact = 1000
    if units == "Hz":
        fact = 1
    if units == "kHz":
        fact = 0.001

    return np.array(rate) * fact, np.array(times)


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
