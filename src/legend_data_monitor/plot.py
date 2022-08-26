from __future__ import annotations

import logging
import os
import pickle as pkl
from copy import copy
from datetime import datetime, timezone

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pygama.lgdo.lh5_store as lh5
from matplotlib import dates

from . import analysis, parameters, timecut

plt.rcParams.update({"figure.max_open_warning": 0})
plt.rcParams["figure.figsize"] = (10, 5)
plt.rcParams["font.size"] = 12
plt.rcParams["figure.facecolor"] = "w"
plt.rcParams["grid.color"] = "b0b0b0"
plt.rcParams["axes.facecolor"] = "w"
plt.rcParams["axes.grid"] = True
plt.rcParams["axes.grid.axis"] = "both"
plt.rcParams["axes.grid.which"] = "major"
j_config, j_par, j_plot = analysis.read_json_files()
exp = j_config[0]["exp"]
period = j_config[1]
run = j_config[2]
datatype = j_config[3]


def plot_parameters(
    ax,
    par_array: np.ndarray,
    utime_array: np.ndarray,
    detector: str,
    det_type: str,
    parameter: str,
):
    """
    Plot the parameter VS time and check if parameters are below/above some given thresholds.

    Parameters
    ----------
    ax
                  PLot to be saved in pkl file
    par_array
                  Array with parameter values
    utime_array
                  Array with (shifted+cut) time values
    detector
                  Name of the detector
    det_type
                  Type of detector (geds or spms)
    parameter
                  Parameter to plot
    """
    # evaluate (x,y) points
    #time_slice = j_config[6][det_type]
    """
    if parameter != "event_rate" and parameter != "wf_max":   # <<<---- check it because for wf_max for all ievts gave problems!!!
        times_average, par_average = analysis.par_time_average(
            utime_array, par_array, time_slice
        )
    else:
        times_average = utime_array
        par_average = par_array
    """
    times_average = utime_array
    par_average = par_array

    # function to check if par values are outside some pre-defined limits
    status = analysis.check_par_values(
        times_average, par_average, parameter, detector, det_type
    )
    times = [datetime.fromtimestamp(t) for t in times_average]

    status_flag = j_config[9][det_type]
    if det_type == "spms":
        col = j_plot[2][str(detector)]
    if det_type == "geds":
        col = j_plot[3][detector]
    if det_type == "ch000":
        col = "k"

    # if we want to plot detectors that are only problematic
    if status_flag is True and status == 1:
        ax.plot(
            times, par_average, color=col, linewidth=0, marker=".", markersize=0.5
        )
        plt.plot(
            times, par_average, color=col, linewidth=0, marker=".", markersize=0.5
        )
    # plot everything independently of the detector's status
    else:
        ax.plot(
            times, par_average, color=col, linewidth=0, marker=".", markersize=0.5
        )
        plt.plot(
            times, par_average, color=col, linewidth=0, marker=".", markersize=0.5
        )

    return times[0], times[-1], status, ax


def plot_par_vs_time(
    raw_files: list[str],
    det_list: list[str],
    parameter: str,
    time_cut: list[str],
    det_type: str,
    string_number: str,
    det_dict: dict,
    pdf=None,
) -> dict:
    """
    Plot time evolution of given parameter.

    Parameters
    ----------
    raw_files
                    Strings of lh5 dsp files
    det_list
                    List of detectors present in a string
    parameter
                    Parameter to plot
    time_cut
                    List with info about time cuts
    det_type
                    Type of detector (geds or spms)
    string_number
                    Number of the string under study
    det_dict    
                    Contains info (crate, card, ch_orca) for geds/spms/other
    """
    fig, ax = plt.subplots(1, 1)
    ax.set_facecolor("w")
    ax.grid(axis="both", which="major")
    plt.grid(axis="both", which="major")
    plt.figure().patch.set_facecolor(j_par[0][parameter]["facecol"])
    start_times = []
    end_times = []
    handle_list = []
    map_dict = {}

    for raw_file in raw_files:
        dsp_file = raw_file.replace("raw", "dsp")

        # search for pulser events
        puls_only_ievt, not_puls_ievt = analysis.get_puls_ievt(raw_file, dsp_file)

        # skip the file if it does not exist the dsp one (just for dsp-related parameters)
        if os.path.exists(dsp_file) is False:
            logging.warning(f"File {dsp_file} does not exist")
            if parameter in ["uncal_puls"] or j_par[0][parameter]["tier"] == 2:
                continue

        for detector in det_list:
            # skip detectors that are not geds/spms
            if det_dict[detector]["system"] == "--":
                continue

            # skip the file if dsp-parameter is not present in the dsp file
            if j_par[0][parameter]["tier"] == 2:
                if f"{detector}/dsp/{parameter}" not in lh5.ls(
                    dsp_file, f"{detector}/dsp/"
                ):
                    continue

            # skip the detector if not in raw file
            if detector not in lh5.ls(raw_file, ""):
                logging.warning(f"No {detector} branch in file {raw_file}")
                continue

            # skip the detector if not in dsp file (just for dsp-related parameters)
            if parameter in ["uncal_puls"] or j_par[0][parameter]["tier"] == 2:
                if detector not in lh5.ls(dsp_file, ""):
                    logging.warning(f"No {detector} branch in file {dsp_file}")
                    continue

            # add entries for the legend
            card = det_dict[detector]["daq"]["card"]
            ch_orca = det_dict[detector]["daq"]["ch_orca"]
            if det_type=="geds": 
                name = det_dict[detector]["det"]
                lab = f"{name} - {detector} - {card},{ch_orca}"
            if det_type == "spms":
                lab = f"{detector} - {card},{ch_orca}"
            if raw_file == raw_files[0]:
                if det_type == "spms":
                    col = j_plot[2][str(detector)]
                if det_type == "geds":
                    col = j_plot[3][detector]
                handle_list.append(
                    mpatches.Patch(
                        color=col,
                        label=lab,
                    )
                )

            # det parameter and time arrays for a given detector
            par_np_array, utime_array = parameters.load_parameter(
                parameter,
                raw_file,
                dsp_file,
                detector,
                det_type,
                time_cut,
                raw_files,
                puls_only_ievt,
                not_puls_ievt,
            )

            # to handle particular cases where the timestamp array is outside the time window:
            if len(par_np_array) == 0 and len(utime_array) == 0:
                continue

            # plot detector and get its status
            start_time, end_time, status, ax = plot_parameters(
                ax, par_np_array, utime_array, detector, det_type, parameter
            )

            # fill the map with status flags
            if det_type == "spms":
                detector = str(detector)
            if detector not in map_dict:
                map_dict[detector] = status
            else:
                if map_dict[detector] == 0:
                    map_dict[detector] = status

            # skip those events that are not within the time window
            if start_time == 0 and end_time == 0:
                if raw_file != raw_files[-1]:
                    continue
                else:
                    break
            start_times.append(start_time)
            end_times.append(end_time)

    # no data were found at all
    if len(start_times) == 0 and len(end_times) == 0:
        return None

    # 1D-plot
    local_timezone = datetime.now(timezone.utc).astimezone().tzinfo
    locs = np.linspace(
        dates.date2num(start_times[0]), dates.date2num(end_times[-1]), 10
    )
    xlab = "%d/%m"
    if j_config[10]["frmt"] == "day/month-time":
        xlab = "%d/%m\n%H:%M"
    if j_config[10]["frmt"] == "time":
        xlab = "%H:%M"
    labels = [dates.num2date(loc, tz=local_timezone).strftime(xlab) for loc in locs]
    ax.set_xticks(locs)
    ax.set_xticklabels(labels)
    plt.xticks(locs, labels)
    ax.legend(
        loc=(1.04, 0.0),
        ncol=1,
        frameon=True,
        facecolor="white",
        framealpha=0,
        handles=handle_list,
    )
    plt.legend(
        loc=(1.04, 0.0),
        ncol=1,
        frameon=True,
        facecolor="white",
        framealpha=0,
        handles=handle_list,
    )
    ylab = j_par[0][parameter]["label"]
    if j_par[0][parameter]["units"] != "null":
        ylab = ylab + " [" + j_par[0][parameter]["units"] + "]"
    if parameter == "event_rate":
        units = j_config[5]["Available-par"]["Other-par"]["event_rate"]["units"][
            det_type
        ]
        ylab = ylab + " [" + units + "]"
    ax.set_ylabel(ylab)
    ax.set_xlabel(f'{j_config[10]["frmt"]} (UTC)')
    plt.ylabel(ylab)
    plt.xlabel(f'{j_config[10]["frmt"]} (UTC)')

    # set title
    if det_type == "spms":
        ax.set_title(f"spms - {string_number}")
        plt.title(f"spms - {string_number}")
    if det_type == "geds":
        ax.set_title(f"geds - string #{string_number}")
        plt.title(f"geds - string #{string_number}")

    # set y-label
    low_lim = j_par[0][parameter]["limit"][det_type][0]
    upp_lim = j_par[0][parameter]["limit"][det_type][1]
    if low_lim != "null":
        ax.axhline(y=low_lim, color="r", linestyle="--", linewidth=2)
        plt.axhline(y=low_lim, color="r", linestyle="--", linewidth=2)
    if upp_lim != "null":
        ax.axhline(y=upp_lim, color="r", linestyle="--", linewidth=2)
        plt.axhline(y=upp_lim, color="r", linestyle="--", linewidth=2)
    # plt.ylim(low_lim*(1-0.01), upp_lim*(1+0.01)) # y-axis zoom

    # define name of pkl file (with info about time cut if present)
    if len(time_cut) != 0:
        start, end = timecut.time_dates(time_cut)
        if det_type == "geds":
            pkl_name = (
                exp
                + "-"
                + period
                + "-"
                + run
                + "-"
                + datatype
                + "-"
                + start
                + "_"
                + end
                + "-"
                + parameter
                + "-string"
                + string_number
                + ".pkl"
            )
        if det_type == "spms":
            pkl_name = (
                exp
                + "-"
                + period
                + "-"
                + run
                + "-"
                + datatype
                + "-"
                + start
                + "_"
                + end
                + "-"
                + parameter
                + "-"
                + string_number
                + ".pkl"
            )
    else:
        if det_type == "geds":
            pkl_name = (
                exp
                + "-"
                + period
                + "-"
                + run
                + "-"
                + datatype
                + "-"
                + parameter
                + "-string"
                + string_number
                + ".pkl"
            )
        if det_type == "spms":
            pkl_name = (
                exp
                + "-"
                + period
                + "-"
                + run
                + "-"
                + datatype
                + "-"
                + parameter
                + "-"
                + string_number
                + ".pkl"
            )

    pkl.dump(ax, open(f"out/pkl-files/par-vs-time/{pkl_name}", "wb"))
    pdf.savefig(bbox_inches="tight")
    plt.close()

    logging.info(f'{parameter} is plotted from {start_times[0]} to {end_times[-1]}')

    return map_dict


def plot_par_vs_time_ch000(
    raw_files: list[str],
    parameter: str,
    time_cut: list[str],
    det_type: str,
    pdf=None,
) -> dict:
    """
    Plot time evolution of given parameter.

    Parameters
    ----------
    raw_files
                    Strings of lh5 raw files
    parameter
                    Parameter to plot
    det_type
                    Type of detector (pulser)
    time_cut
                    List with info about time cuts
    """
    fig, ax = plt.subplots(1, 1)
    ax.set_facecolor("w")
    ax.grid(axis="both", which="major")
    plt.grid(axis="both", which="major")
    plt.figure().patch.set_facecolor(j_par[0][parameter]["facecol"])
    start_times = []
    end_times = []
    handle_list = []
    map_dict = {}

    for raw_file in raw_files:
        dsp_file = raw_file.replace("raw", "dsp")

        # search for pulser events
        puls_only_ievt, not_puls_ievt = analysis.get_puls_ievt(raw_file, dsp_file)

        # skip the file if it does not exist the dsp one (just for dsp-related parameters)
        if os.path.exists(dsp_file) is False:
            logging.warning(f"File {dsp_file} does not exist")
            if parameter in ["uncal_puls"] or j_par[0][parameter]["tier"] == 2:
                continue

        # skip the file if dsp-parameter is not present in the dsp file
        if j_par[0][parameter]["tier"] == 2:
            if f"ch000/dsp/{parameter}" not in lh5.ls(dsp_file, f"ch000/dsp/"):
                continue

        # skip the detector if not in raw file
        if "ch000" not in lh5.ls(raw_file, ""):
            logging.warning(f'No "ch000" in file {raw_file}')
            continue

        # skip the detector if not in dsp file (just for dsp-related parameters)
        if parameter in ["uncal_puls"] or j_par[0][parameter]["tier"] == 2:
            if "ch000" not in lh5.ls(dsp_file, ""):
                logging.warning(f'No "ch000" in file {dsp_file}')
                continue

        # add entries for the legend
        if raw_file == raw_files[0]:
            handle_list.append(
                mpatches.Patch(
                    color="k",
                    label="ch000 - 0,0",  # channel - card, ch_orca (FC)
                )
            )

        # det parameter and time arrays for a given detector
        par_np_array, utime_array = parameters.load_parameter(
            parameter,
            raw_file,
            dsp_file,
            "ch000",
            det_type,
            time_cut,
            raw_files,
            puls_only_ievt,
            not_puls_ievt,
        )

        # to handle particular cases where the timestamp array is outside the time window:
        if len(par_np_array) == 0 and len(utime_array) == 0:
            continue

        # plot detector and get its status
        start_time, end_time, status, ax = plot_parameters(
            ax, par_np_array, utime_array, "ch000", det_type, parameter
        )

        # fill the map with status flags
        if "ch000" not in map_dict:
            map_dict["ch000"] = status
        else:
            if map_dict["ch000"] == 0:
                map_dict["ch000"] = status

        # skip those events that are not within the time window
        if start_time == 0 and end_time == 0:
            if raw_file != raw_files[-1]:
                continue
            else:
                break
        start_times.append(start_time)
        end_times.append(end_time)

    # no data were found at all
    if len(start_times) == 0 and len(end_times) == 0:
        return None

    # 1D-plot
    local_timezone = datetime.now(timezone.utc).astimezone().tzinfo
    locs = np.linspace(
        dates.date2num(start_times[0]), dates.date2num(end_times[-1]), 10
    )
    xlab = "%d/%m"
    if j_config[10]["frmt"] == "day/month-time":
        xlab = "%d/%m\n%H:%M"
    if j_config[10]["frmt"] == "time":
        xlab = "%H:%M"
    labels = [dates.num2date(loc, tz=local_timezone).strftime(xlab) for loc in locs]
    ax.set_xticks(locs)
    ax.set_xticklabels(labels)
    plt.xticks(locs, labels)
    ax.legend(
        loc=(1.04, 0.0),
        ncol=1,
        frameon=True,
        facecolor="white",
        framealpha=0,
        handles=handle_list,
    )
    plt.legend(
        loc=(1.04, 0.0),
        ncol=1,
        frameon=True,
        facecolor="white",
        framealpha=0,
        handles=handle_list,
    )
    ylab = j_par[0][parameter]["label"]
    if j_par[0][parameter]["units"] != "null":
        ylab = ylab + " [" + j_par[0][parameter]["units"] + "]"
    if parameter == "event_rate":
        units = j_config[5]["Available-par"]["Other-par"]["event_rate"]["units"][
            det_type
        ]
        ylab = ylab + " [" + units + "]"
    ax.set_ylabel(ylab)
    ax.set_xlabel(f'{j_config[10]["frmt"]} (UTC)')
    plt.ylabel(ylab)
    plt.xlabel(f'{j_config[10]["frmt"]} (UTC)')

    # set title
    ax.set_title(f"pulser - ch000")
    plt.title(f"pulser - ch000")

    # set y-label
    low_lim = j_par[0][parameter]["limit"][det_type][0]
    upp_lim = j_par[0][parameter]["limit"][det_type][1]
    if low_lim != "null":
        ax.axhline(y=low_lim, color="r", linestyle="--", linewidth=2)
        plt.axhline(y=low_lim, color="r", linestyle="--", linewidth=2)
    if upp_lim != "null":
        ax.axhline(y=upp_lim, color="r", linestyle="--", linewidth=2)
        plt.axhline(y=upp_lim, color="r", linestyle="--", linewidth=2)

    # define name of pkl file (with info about time cut if present)
    if len(time_cut) != 0:
        start, end = timecut.time_dates(time_cut)
        pkl_name = (
            exp
            + "-"
            + period
            + "-"
            + run
            + "-"
            + datatype
            + "-"
            + start
            + "_"
            + end
            + "-"
            + parameter
            + "-pulser.pkl"
        )
    else:
        pkl_name = (
            exp
            + "-"
            + period
            + "-"
            + run
            + "-"
            + datatype
            + "-"
            + parameter
            + "-pulser.pkl"
        )

    pkl.dump(ax, open(f"out/pkl-files/par-vs-time/{pkl_name}", "wb"))
    pdf.savefig(bbox_inches="tight")
    plt.close()

    logging.info(f'{parameter} is plotted from {start_times[0]} to {end_times[-1]}')

    return map_dict


def plot_par_vs_time_2d(
    raw_files: list[str],
    det_list: list[str],
    time_cut: list[str],
    det_type: str,
    string_number: str,
    det_dict: dict,
    pdf=None,
) -> None:
    """
    No map is provided as an output.

    Parameters
    ----------
    raw_files
                    Strings of lh5 raw files
    det_list
                    List of detectors present in a string
    det_list
                    Detector channel numbers
    time_cut
                    List with info about time cuts
    string_number
                    Number of the string under study
    det_type
                    Type of detector (geds or spms)
    det_dict
                    Contains info (crate, card, ch_orca) for geds/spms/other
    """
    parameter = "gain"
    handle_list = []
    plt.rcParams["font.size"] = 6
    if "OB" in string_number:
        fig, (
            (ax1, ax2, ax3, ax4, ax5),
            (ax6, ax7, ax8, ax9, ax10),
            (ax11, ax12, ax13, ax14, ax15),
            (ax16, ax17, ax18, ax19, ax20),
        ) = plt.subplots(4, 5, sharex=True, sharey=True)
        ax_list = [
            ax1,
            ax2,
            ax3,
            ax4,
            ax5,
            ax6,
            ax7,
            ax8,
            ax9,
            ax10,
            ax11,
            ax12,
            ax13,
            ax14,
            ax15,
            ax16,
            ax17,
            ax18,
            ax19,
            ax20,
        ]
    if "IB" in string_number:
        fig, ((ax1, ax2, ax3), (ax4, ax5, ax6), (ax7, ax8, ax9)) = plt.subplots(
            3, 3, sharex=True, sharey=True
        )
        ax_list = [ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9]

    ax_idx = 0
    fig.patch.set_facecolor(j_par[0][parameter]["facecol"])
    fig.suptitle(f"spms - {string_number}", fontsize=8)

    for detector in det_list:
        if det_dict[detector]["system"] == "--":
            continue

        wf_array = lh5.load_nda(raw_files, ["values"], detector + "/raw/waveform")[
            "values"
        ]

        # add entries for the legend
        card = det_dict[detector]["daq"]["card"]
        ch_orca = det_dict[detector]["daq"]["ch_orca"]
        if det_type == "spms":
            handle_list.append(
                mpatches.Patch(
                    color=j_plot[2][str(detector)],
                    label=f"{detector} - {card},{ch_orca}",
                )
            )
        if det_type == "geds":
            handle_list.append(
                mpatches.Patch(
                    color=j_plot[3][detector],
                    label=f"{detector} - {card},{ch_orca}",
                )
            )

        # select the channel
        utime_array = analysis.build_utime_array(
            raw_files, detector, "spms"
        )  # shifted timestamps (pulser events are not removed)
        utime_array, wf_array = analysis.time_analysis(utime_array, wf_array, time_cut)

        # calculate the gain
        if parameter == "gain":
            par_array = parameters.spms_gain(wf_array)
        if len(par_array) == 0 and len(utime_array) == 0:
            continue

        # define x-axis
        start_time = datetime.fromtimestamp(utime_array[0])
        end_time = datetime.fromtimestamp(utime_array[-1])
        local_timezone = datetime.now(timezone.utc).astimezone().tzinfo
        locs = np.linspace(dates.date2num(start_time), dates.date2num(end_time), 3)
        xlab = "%d/%m"
        if j_config[10]["frmt"] == "day/month-time":
            xlab = "%d/%m\n%H:%M"
        if j_config[10]["frmt"] == "time":
            xlab = "%H:%M"
        labels = [dates.num2date(loc, tz=local_timezone).strftime(xlab) for loc in locs]

        # 2D-plot
        h, xedges, yedges = np.histogram2d(
            utime_array,
            par_array,
            bins=[200, 200],
            range=[[utime_array[0], utime_array[-1]], [0, 300]],
        )
        to_datetime = np.vectorize(datetime.fromtimestamp)
        xedges_datetime = to_datetime(xedges)
        cmap = copy(plt.get_cmap("hot"))
        cmap.set_bad(cmap(0))

        ylab = j_par[0][parameter]["label"]
        if j_par[0][parameter]["units"] != "null":
            ylab = ylab + " [" + j_par[0][parameter]["units"] + "]"

        ax_list[ax_idx].pcolor(
            xedges_datetime, yedges, h.T, norm=mpl.colors.LogNorm(), cmap="magma"
        )
        if "OB" in string_number:
            ax_list[ax_idx].set_title(
                f"{detector} - {card},{ch_orca}", fontsize=7, y=0.93
            )
            if ax_idx == 0 or ax_idx == 5 or ax_idx == 10 or ax_idx == 15:
                ax_list[ax_idx].set(ylabel="Gain [ADC]")
            if (
                ax_idx == 15
                or ax_idx == 16
                or ax_idx == 17
                or ax_idx == 18
                or ax_idx == 19
            ):
                ax_list[ax_idx].set(xlabel=f'{j_config[10]["frmt"]} (UTC)')
        if "IB" in string_number:
            ax_list[ax_idx].set_title(
                f"{detector} - {card},{ch_orca}", fontsize=7, y=0.95
            )
            if ax_idx == 0 or ax_idx == 3 or ax_idx == 6:
                ax_list[ax_idx].set(ylabel="Gain [ADC]")
            if ax_idx == 6 or ax_idx == 7 or ax_idx == 8:
                ax_list[ax_idx].set(xlabel=f'{j_config[10]["frmt"]} (UTC)')
        ax_list[ax_idx].set_xticks(locs)
        ax_list[ax_idx].set_xticklabels(labels)
        plt.setp(ax_list[ax_idx].get_xticklabels(), rotation=0, ha="center")

        ax_idx += 1
        handle_list = []
        start_time = end_time = 0

    # define name of pkl file (with info about time cut if present)
    if len(time_cut) != 0:
        start, end = timecut.time_dates(time_cut)
        if det_type == "geds":
            pkl_name = (
                exp
                + "-"
                + period
                + "-"
                + run
                + "-"
                + datatype
                + "-"
                + start
                + "_"
                + end
                + "-"
                + parameter
                + "-string"
                + string_number
                + ".pkl"
            )
        if det_type == "spms":
            pkl_name = (
                exp
                + "-"
                + period
                + "-"
                + run
                + "-"
                + datatype
                + "-"
                + start
                + "_"
                + end
                + "-"
                + parameter
                + "-"
                + string_number
                + ".pkl"
            )
    else:
        if det_type == "geds":
            pkl_name = (
                exp
                + "-"
                + period
                + "-"
                + run
                + "-"
                + datatype
                + "-"
                + parameter
                + "-string"
                + string_number
                + ".pkl"
            )
        if det_type == "spms":
            pkl_name = (
                exp
                + "-"
                + period
                + "-"
                + run
                + "-"
                + datatype
                + "-"
                + parameter
                + "-"
                + string_number
                + ".pkl"
            )

    pkl.dump(ax_list, open(f"out/pkl-files/par-vs-time/{pkl_name}", "wb"))
    pdf.savefig(bbox_inches="tight")
    plt.close()

    return
