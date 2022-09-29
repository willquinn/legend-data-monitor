from __future__ import annotations

import importlib.resources
import json
import logging
import os
from datetime import datetime

import numpy as np
import pygama.lgdo.lh5_store as lh5
from pygama.lgdo import LH5Store
from pygama.raw.orca import orca_streamer

from . import timecut

pkg = importlib.resources.files("legend_data_monitor")


def read_json_files():
    """Read json files of 'settings/' folder and return three lists."""
    with open(pkg / ".." / ".." / "config.json") as f:
        data_config = json.load(f)
    with open(pkg / "settings" / "par-settings.json") as g:
        data_par = json.load(g)
    with open(pkg / "settings" / "plot-settings.json") as h:
        data_plot = json.load(h)
    j_config = []
    j_par = []
    j_plot = []

    j_config.append(data_config["run_info"])  # 0
    j_config.append(data_config["period"])  # 1
    j_config.append(data_config["run"])  # 2
    j_config.append(data_config["datatype"])  # 3
    j_config.append(data_config["det_type"])  # 4
    j_config.append(data_config["par_to_plot"])  # 5
    j_config.append(data_config["plot_style"])  # 6
    j_config.append(data_config["time_window"])  # 7
    j_config.append(data_config["last_hours"])  # 8
    j_config.append(data_config["status"])  # 9
    j_config.append(data_config["time-format"])  # 10
    j_config.append(data_config["verbose"])  # 11

    j_par.append(data_par["par_to_plot"])  # 0

    j_plot.append(data_plot["spms_name_dict"])  # 0
    j_plot.append(data_plot["geds_name_dict"])  # 1
    j_plot.append(data_plot["spms_col_dict"])  # 2
    j_plot.append(data_plot["geds_col_dict"])  # 3

    return j_config, j_par, j_plot


j_config, j_par, j_plot = read_json_files()


def load_channels(raw_files: list[str]):
    """
    Load channel map.

    Parameters
    ----------
    raw_files
                Strings of lh5 raw files
    """
    channels = lh5.ls(raw_files[0], "")
    filename = os.path.basename(raw_files[0])
    fn_split = filename.split("-")
    orca_name = (
        f"{fn_split[0]}-{fn_split[1]}-{fn_split[2]}-{fn_split[3]}-{fn_split[4]}.orca"
    )
    data_type = fn_split[3]
    orca_path = j_config[0]["path"]["orca-files"]
    period = j_config[1]
    run = j_config[2]
    orca_file = f"{orca_path}{data_type}/{period}/{run}/{orca_name}"
    orstr = orca_streamer.OrcaStreamer()
    orstr.open_stream(orca_file)
    channel_map = json.loads(orstr.header["ObjectInfo"]["ORL200Model"]["DetectorMap"])
    store = LH5Store()

    geds_dict = {}
    spms_dict = {}
    other_dict = {}

    for ch in channels:
        crate = store.read_object(f"{ch}/raw/crate", raw_files[0])[0].nda[0]
        card = store.read_object(f"{ch}/raw/card", raw_files[0])[0].nda[0]
        ch_orca = store.read_object(f"{ch}/raw/ch_orca", raw_files[0])[0].nda[0]
        daq_dict = {}
        daq_dict["crate"] = crate
        daq_dict["card"] = card
        daq_dict["ch_orca"] = ch_orca

        if crate == 0:
            for det, entry in channel_map.items():
                if (
                    entry["daq"]["crate"] == f"{crate}"
                    and entry["daq"]["board_slot"] == f"{card}"
                    and entry["daq"]["board_ch"] == f"{ch_orca}"
                ):
                    string_dict = {}
                    hv_dict = {}
                    string_dict["number"] = entry["string"]["number"]
                    string_dict["position"] = entry["string"]["position"]
                    hv_dict["board_chan"] = entry["high_voltage"]["board_chan"]
                    hv_dict["flange_id"] = entry["high_voltage"]["flange_id"]

                    geds_dict[ch] = {
                        "system": "ged",
                        "det": det,
                        "string": string_dict,
                        "daq": daq_dict,
                        "high_voltage": hv_dict,
                    }

        if crate == 1:
            other_dict[ch] = {"system": "--", "daq": daq_dict}
        if crate == 2:
            spms_dict[ch] = {"system": "spm", "daq": daq_dict}

    return geds_dict, spms_dict, other_dict


def read_geds(geds_dict: dict):
    """
    Build an array of germanium strings.

    Parameters
    ----------
    geds_dict
               Contains info (crate, card, ch_orca) for geds
    """
    string_tot = []
    string_name = []

    # no of strings
    str_no = [
        v["string"]["number"]
        for k, v in geds_dict.items()
        if v["string"]["number"] != "--"
    ]
    min_str = int(min(str_no))
    max_str = int(max(str_no))
    idx = min_str

    # fill lists with strings of channels ('while' loop over no of string)
    while idx <= max_str:
        string = [k for k, v in geds_dict.items() if v["string"]["number"] == str(idx)]
        pos = []
        for v1 in geds_dict.values():
            for k2, v2 in v1.items():
                if k2 == "string":
                    for k3, v3 in v2.items():
                        if k3 == "position" and v1["string"]["number"] == str(idx):
                            pos.append(v3)

        if len(string) == 0:
            idx += 1
        else:
            # order channels within a string
            pos, string = (list(t) for t in zip(*sorted(zip(pos, string))))
            string_tot.append(string)
            string_name.append(f"{idx}")
            idx += 1

    return string_tot, string_name


def read_spms(spms_dict: dict):
    """
    Build two lists for IN and OUT spms.

    Parameters
    ----------
    spms_dict
               Contains info (crate, card, ch_orca) for spms
    """
    spms_map = json.load(open(pkg / "settings" / "spms_map.json"))
    top_ob = []
    bot_ob = []
    top_ib = []
    bot_ib = []

    # loop over spms channels (i.e. channels w/ crate=2)
    for ch in list(spms_dict.keys()):
        card = spms_dict[ch]["daq"]["card"]
        ch_orca = spms_dict[ch]["daq"]["ch_orca"]

        idx = "0"
        for serial in list(spms_map.keys()):
            if (
                spms_map[serial]["card"] == card
                and spms_map[serial]["ch_orca"] == ch_orca
            ):
                idx = str(serial)
        if idx == "0":
            continue

        spms_type = spms_map[idx]["type"]
        spms_pos = spms_map[idx]["pos"]
        if spms_type == "OB" and spms_pos == "top":
            top_ob.append(ch)
        if spms_type == "OB" and spms_pos == "bot":
            bot_ob.append(ch)
        if spms_type == "IB" and spms_pos == "top":
            top_ib.append(ch)
        if spms_type == "IB" and spms_pos == "bot":
            bot_ib.append(ch)

    half_len_top_ob = int(len(top_ob) / 2)
    half_len_bot_ob = int(len(bot_ob) / 2)
    top_ob_1 = top_ob[half_len_top_ob:]
    top_ob_2 = top_ob[:half_len_top_ob]
    bot_ob_1 = bot_ob[half_len_bot_ob:]
    bot_ob_2 = bot_ob[:half_len_bot_ob]

    string_tot_div = [top_ob_1, top_ob_2, bot_ob_1, bot_ob_2, top_ib, bot_ib]
    string_name_div = [
        "top_OB-1",
        "top_OB-2",
        "bot_OB-1",
        "bot_OB-2",
        "top_IB",
        "bot_IB",
    ]

    string_tot = [top_ob, bot_ob, top_ib, bot_ib]
    string_name = ["top_OB", "bot_OB", "top_IB", "bot_IB"]

    return string_tot, string_name, string_tot_div, string_name_div


def check_par_values(
    times_average: np.ndarray,
    par_average: np.ndarray,
    parameter: str,
    detector: str,
    det_type: str,
):
    """
    Check parameter values.

    Parameters
    ----------
    times_average
                   Array with x-axis time average values
    par_average
                   Array with y-axis parameter average values
    parameter
                   Name of the parameter to plot
    detector
                   Channel of the detector
    det_type
                   Type of detector (geds or spms)
    """
    low_lim = j_par[0][parameter]["limit"][det_type][0]
    upp_lim = j_par[0][parameter]["limit"][det_type][1]
    units = j_par[0][parameter]["units"]
    thr_flag = 0

    idx = 0
    while idx + 1 < len(par_average):
        # value below the threshold
        if low_lim != "null":
            if par_average[idx] < low_lim:
                thr_flag = 1  # problems!
                j = 0
                time1 = datetime.fromtimestamp(times_average[idx]).strftime(
                    "%d/%m %H:%M:%S"
                )
                while par_average[idx + j] < low_lim and idx + j + 1 < len(par_average):
                    j = j + 1
                idx = idx + j - 1
                time2 = datetime.fromtimestamp(times_average[idx]).strftime(
                    "%d/%m %H:%M:%S"
                )
                if time1 == time2:
                    logging.debug(
                        f' "{parameter}"<{low_lim} {units} (at {time1}) for ch={detector}'
                    )
                else:
                    logging.debug(
                        f' "{parameter}"<{low_lim} {units} ({time1} -> {time2}) for ch={detector}'
                    )
            idx = idx + 1
        # value above the threshold
        if upp_lim != "null":
            if par_average[idx] > upp_lim:
                thr_flag = 1  # problems!
                j = 0
                time1 = datetime.fromtimestamp(times_average[idx]).strftime(
                    "%d/%m %H:%M:%S"
                )
                while par_average[idx + j] > upp_lim and idx + j + 1 < len(par_average):
                    j = j + 1
                idx = idx + j - 1
                time2 = datetime.fromtimestamp(times_average[idx]).strftime(
                    "%d/%m %H:%M:%S"
                )
                if time1 == time2:
                    logging.debug(
                        f' "{parameter}">{upp_lim} {units} (at {time1}) for ch={detector}'
                    )
                else:
                    logging.debug(
                        f' "{parameter}">{upp_lim} {units} ({time1} -> {time2}) for ch={detector}'
                    )
            idx = idx + 1
        # value within the limits
        else:
            idx = idx + 1

    return thr_flag


def build_utime_array(dsp_files: list[str], detector: str, det_type: str):
    """
    Return an array with shifted time arrays for spms detectors.

    Parameters
    ----------
    dsp_files
                   lh5 dsp files
    detector
                   Name of the detector
    det_type
                   Type of detector (geds/spms/pulser)
    """
    utime_array = lh5.load_nda(dsp_files, ["timestamp"], detector + "/dsp")["timestamp"]

    return utime_array


def add_offset_to_timestamp(tmp_array: np.ndarray, dsp_file: list[str]):
    """
    Add a time shift to the filename given by the time shown in 'runtime'.

    Parameters
    ----------
    tmp_array
                Time since beginning of file
    dsp_file
                lh5 dsp file
    """
    date_time = (((dsp_file.split("/")[-1]).split("-")[4]).split("Z")[0]).split("T")
    date = date_time[0]
    time = date_time[1]
    run_start = datetime.strptime(date + time, "%Y%m%d%H%M%S")
    utime_array = tmp_array + np.full(tmp_array.size, run_start.timestamp())

    return utime_array


def time_analysis(utime_array: np.ndarray, par_array: np.ndarray, time_cut: list[str]):
    """
    Return the timestamp & parameter lists after the time cuts.

    Parameters
    ----------
    utime_array
                  Array of (already shifted) timestamps
    par_array
                  Array with parameter values
    time_cut
                  List with info about time cuts
    """
    # time window analysis
    if len(time_cut) == 4:
        start_index, end_index = timecut.min_max_timestamp_thr(
            utime_array.tolist(),
            time_cut[0] + " " + time_cut[1],
            time_cut[2] + " " + time_cut[3],
        )
        # to handle particular cases where the timestamp array is outside the time window:
        if end_index != end_index or start_index != start_index:
            return [], []
        if len(utime_array) != 0:
            utime_array = timecut.cut_array_in_min_max(
                utime_array, start_index, end_index
            )
        if len(par_array) != 0:
            par_array = timecut.cut_array_in_min_max(par_array, start_index, end_index)
    # last X hours analysis
    if len(time_cut) == 3:
        start_index = timecut.min_timestamp_thr(utime_array.tolist(), time_cut)
        if len(utime_array) != 0:
            utime_array = timecut.cut_array_below_min(utime_array, start_index)
        if len(par_array) != 0:
            par_array = timecut.cut_array_below_min(par_array, start_index)

    return utime_array, par_array


def get_puls_ievt(dsp_files: list[str]):
    """
    Select pulser events.

    Parameters
    ----------
    dsp_files
               lh5 dsp file
    """
    wf_max = lh5.load_nda(dsp_files, ["wf_max"], "ch000/dsp/")["wf_max"]
    baseline = lh5.load_nda(dsp_files, ["baseline"], "ch000/dsp")["baseline"]
    wf_max = np.subtract(wf_max, baseline)
    puls_ievt = []
    baseline_entry = []
    pulser_highen_entry = []
    not_pulser_entry = []

    for idx, entry in enumerate(wf_max):
        puls_ievt.append(idx)
        if entry > 12500: # high energy
        #if entry > 17500:
            pulser_highen_entry.append(idx)
        if entry < 2500: # low energy
            not_pulser_entry.append(idx)
        else: # intermediate energy
            baseline_entry.append(idx)

    # pulser+physical events
    puls_ievt = np.array(puls_ievt)
    # pulser entries (high E)
    puls_only_ievt = puls_ievt[np.isin(puls_ievt, pulser_highen_entry)]
    # physical entries
    not_puls_ievt = puls_ievt[np.isin(puls_ievt, not_pulser_entry)]

    return puls_ievt, puls_only_ievt, not_puls_ievt


def remove_nan(par_array: np.ndarray, time_array: np.ndarray):
    """
    Remove NaN values from arrays.

    Parameters
    ----------
    par_array
                 Array with parameter values
    time_array
                 Array with time values
    """
    par_array_no_nan = par_array[~np.isnan(par_array)]
    time_array_no_nan = time_array[~np.isnan(par_array)]

    return np.asarray(par_array_no_nan), np.asarray(time_array_no_nan)



def par_average(par_array: np.ndarray, time_array: np.ndarray):
    """
    Evaluate the average of entries in arrays.

    Parameters
    ----------
    par_array
                 Array with parameter values
    time_array
                 Array with time values
    """
    par_avg = []
    time_avg = []

    step = j_config[6]["par_average"]["step"]
    i = 0

    while (i+1)*step<len(par_array):
        total = 0
        tot_time = 0
        for entry in range(i*step, (i+1)*step):
            total = total + par_array[entry]
            tot_time = tot_time + time_array[entry]
        par_avg.append(total/step)
        time_avg.append(tot_time/step)
        i += 1

    return par_avg, time_avg
