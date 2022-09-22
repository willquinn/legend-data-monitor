from __future__ import annotations

import logging
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

plt.rcParams["agg.path.chunksize"] = 10000000000000000
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
no_variation_pars = j_config[5]["plot_values"]["no_variation_pars"]


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
    # function to check if par values are outside some pre-defined limits
    status = analysis.check_par_values(
        utime_array, par_array, parameter, detector, det_type
    )
    times = [datetime.fromtimestamp(t) for t in utime_array]

    status_flag = j_config[9][det_type]
    if det_type == "spms":
        col = j_plot[2][str(detector)]
    if det_type == "geds":
        col = j_plot[3][detector]
    if det_type == "ch000":
        col = "r"

    # if we want to plot detectors that are only problematic
    if status_flag is True and status == 1:
        ax.plot(times, par_array, color=col, linewidth=0, marker=".", markersize=0.5)
        plt.plot(times, par_array, color=col, linewidth=0, marker=".", markersize=0.5)
    # plot everything independently of the detector's status
    else:
        if det_type == "ch000" or parameter == "K_lines":
            ax.plot(times, par_array, color=col, linewidth=0, marker=".", markersize=6)
            plt.plot(times, par_array, color=col, linewidth=0, marker=".", markersize=6)
        else:
            ax.plot(times, par_array, color=col, linewidth=1)
            plt.plot(times, par_array, color=col, linewidth=1)

    return times[0], times[-1], status, ax


def plot_par_vs_time(
    dsp_files: list[str],
    det_list: list[str],
    parameter: str,
    time_cut: list[str],
    det_type: str,
    string_number: str,
    det_dict: dict,
    pdf=None,
) -> dict:
    """
    Plot time evolution of given parameter for geds/spms.

    Parameters
    ----------
    dsp_all
                    lh5 dsp files
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

    # exit if no dsp files are found
    if len(dsp_files) == 0:
        logging.warning("Dsp files do not exist")
        return None

    # search for pulser events
    all_ievt, puls_only_ievt, not_puls_ievt = analysis.get_puls_ievt(dsp_files)

    for _, detector in enumerate(det_list):
        if parameter == "cal_puls" or parameter == "K_lines":
            if detector == "ch010" or detector == "ch024":
                continue

        # if detector==det_list[1]: # <<-- for quick tests

        # skip detectors that are not geds/spms
        if det_dict[detector]["system"] == "--":
            continue

        # add entries for the legend
        card = det_dict[detector]["daq"]["card"]
        ch_orca = det_dict[detector]["daq"]["ch_orca"]
        if det_type == "geds":
            name = det_dict[detector]["det"]
            lab = f"{name} - {detector} - {card},{ch_orca}"
        if det_type == "spms":
            lab = f"{detector} - {card},{ch_orca}"
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
            dsp_files,
            detector,
            det_type,
            time_cut,
            all_ievt,
            puls_only_ievt,
            not_puls_ievt,
        )

        # offset = 1000 * (0 + index)
        # par_np_array = np.add(par_np_array, offset)

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

        # skip those detectors that are not within the time window
        if start_time == 0 and end_time == 0:
            continue
        start_times.append(start_time)
        end_times.append(end_time)

    # no data were found at all
    if len(start_times) == 0 and len(end_times) == 0:
        return None

    # 1D-plot
    local_timezone = datetime.now(timezone.utc).astimezone().tzinfo
    locs = np.linspace(
        dates.date2num(min(start_times)), dates.date2num(max(end_times)), 10
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
    if parameter in no_variation_pars:
        if j_par[0][parameter]["units"] != "null":
            ylab += " [" + j_par[0][parameter]["units"] + "]"
        if parameter == "event_rate":
            units = j_config[5]["Available-par"]["Other-par"]["event_rate"]["units"][
                det_type
            ]
            ylab += " [" + units + "]"
    else:
        ylab += ", %"
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

    # define horiziontal lines
    low_lim = j_par[0][parameter]["limit"][det_type][0]
    upp_lim = j_par[0][parameter]["limit"][det_type][1]
    if low_lim != "null":
        ax.axhline(y=low_lim, color="r", linestyle="--", linewidth=2)
        plt.axhline(y=low_lim, color="r", linestyle="--", linewidth=2)
    if upp_lim != "null":
        ax.axhline(y=upp_lim, color="r", linestyle="--", linewidth=2)
        plt.axhline(y=upp_lim, color="r", linestyle="--", linewidth=2)
    # plt.ylim(low_lim*(1-0.01), upp_lim*(1+0.01)) # y-axis zoom
    if parameter == "K_lines":
        ax.axhline(y=1460.8, color="r", linestyle="--", linewidth=1)
        plt.axhline(y=1460.8, color="r", linestyle="--", linewidth=1)
        ax.axhline(y=1524.6, color="r", linestyle="--", linewidth=1)
        plt.axhline(y=1524.6, color="r", linestyle="--", linewidth=1)

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

    logging.info(f"{parameter} is plotted from {start_times[0]} to {end_times[-1]}")

    return map_dict


def plot_par_vs_time_ch000(
    dsp_files: list[str],
    parameter: str,
    time_cut: list[str],
    det_type: str,
    pdf=None,
) -> dict:
    """
    Plot time evolution of given parameter for ch000.

    Parameters
    ----------
    dsp_files
                    Strings of lh5 dsp files
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

    # exit if no dsp files are found
    if len(dsp_files) == 0:
        logging.warning("Dsp files do not exist")
        return None

    # search for pulser events
    all_ievt, puls_only_ievt, not_puls_ievt = analysis.get_puls_ievt(dsp_files)

    # remove the dsp file if the channel is not there
    # for dsp_file in dsp_files:
    #    if "ch000" not in lh5.ls(dsp_file, ""):
    #        dsp_files.remove(dsp_file)
    #        logging.warning(f"No ch000 in {dsp_file}: removed")

    # remove the dsp file if the parameter for the channel under study is not there
    # for dsp_file in dsp_files:
    #    if "ch000/dsp/"+parameter not in lh5.ls(dsp_file, "ch000/dsp/"):
    #        dsp_files.remove(dsp_file)
    #        logging.warning(f"No {parameter} in {dsp_file}: removed")

    # add entries for the legend
    handle_list.append(
        mpatches.Patch(
            color="k",
            label="ch000 - 0,0",  # channel - card, ch_orca (FC)
        )
    )

    # det parameter and time arrays for a given detector
    par_np_array, utime_array = parameters.load_parameter(
        parameter,
        dsp_files,
        "ch000",
        det_type,
        time_cut,
        all_ievt,
        puls_only_ievt,
        not_puls_ievt,
    )

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
    xlab = j_config[10]["frmt"]
    ylab = j_par[0][parameter]["label"]
    if parameter in no_variation_pars:
        if j_par[0][parameter]["units"] != "null":
            ylab += " [" + j_par[0][parameter]["units"] + "]"
        if parameter == "event_rate":
            units = j_config[5]["Available-par"]["Other-par"]["event_rate"]["units"][
                det_type
            ]
            ylab += " [" + units + "]"
    else:
        ylab += ", %"
    ax.set_ylabel(ylab)
    ax.set_xlabel(f"{xlab} (UTC)")
    plt.ylabel(ylab)
    plt.xlabel(f"{xlab} (UTC)")

    # set title
    ax.set_title("pulser - ch000")
    plt.title("pulser - ch000")

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

    logging.info(f"{parameter} is plotted from {start_times[0]} to {end_times[-1]}")

    return map_dict


def plot_par_vs_time_2d(
    dsp_files: list[str],
    det_list: list[str],
    time_cut: list[str],
    det_type: str,
    string_number: str,
    det_dict: dict,
    pdf=None,
) -> None:
    """
    Plot for gain parameter.

    Parameters
    ----------
    dsp_files
                    lh5 dsp files
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

        wf_array = lh5.load_nda(dsp_files, ["wf_max"], detector + "/dsp/")["wf_max"]

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
            dsp_files, detector, "spms"
        )  # shifted timestamps (pulser events are not removed)
        utime_array, wf_array = analysis.time_analysis(utime_array, wf_array, time_cut)
        par_array = parameters.spms_gain(wf_array)

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
        x_lab = j_config[10]["frmt"]
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
                ax_list[ax_idx].set(xlabel=f"{x_lab} (UTC)")
        if "IB" in string_number:
            ax_list[ax_idx].set_title(
                f"{detector} - {card},{ch_orca}", fontsize=7, y=0.95
            )
            if ax_idx == 0 or ax_idx == 3 or ax_idx == 6:
                ax_list[ax_idx].set(ylabel="Gain [ADC]")
            if ax_idx == 6 or ax_idx == 7 or ax_idx == 8:
                ax_list[ax_idx].set(xlabel=f"{x_lab} (UTC)")
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


def plot_wtrfll(
    dsp_all: list[str],
    det_list: list[str],
    parameter: str,
    time_cut: list[str],
    det_type: str,
    string_number: str,
    det_dict: dict,
    pdf=None,
) -> dict:
    """
    Plot time evolution of given parameter for geds/spms as a waterfall plot.

    Parameters
    ----------
    dsp_all
                    lh5 dsp files
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
    # fig = plt.subplot(projection='3d')
    fig = plt.figure(figsize=(20, 16))
    ax = fig.add_subplot(111, projection="3d")
    y_values = []
    start_times = []
    end_times = []
    map_dict = {}

    # exit if no dsp files are found
    if len(dsp_all) == 0:
        logging.warning("Dsp files do not exist")
        return None

    # search for pulser events
    all_ievt, puls_only_ievt, not_puls_ievt = analysis.get_puls_ievt(dsp_all)

    for index, detector in enumerate(det_list):
        if parameter == "cal_puls" or parameter == "K_lines":
            if detector == "ch010" or detector == "ch024":
                continue
        # if detector==det_list[1]: # <<-- for quick tests

        # need to define a variable for dsp files for every ch (due to the "remove")
        dsp_files = dsp_all

        # skip detectors that are not geds/spms
        if det_dict[detector]["system"] == "--":
            continue

        # add entries for the legend
        if det_type == "geds":
            name = det_dict[detector]["det"]
            if "V0" in name:
                name = name[2:]
            string_no = det_dict[detector]["string"]["number"]
            string_pos = det_dict[detector]["string"]["position"]
            new_label = f"s{string_no}-p{string_pos}-{detector}-{name}"
        else:
            name = f"{detector}"
        if det_type == "spms":
            col = j_plot[2][str(detector)]
        if det_type == "geds":
            col = j_plot[3][detector]
        y_values.append(new_label)

        # det parameter and time arrays for a given detector
        par_np_array, utime_array = parameters.load_parameter(
            parameter,
            dsp_files,
            detector,
            det_type,
            time_cut,
            all_ievt,
            puls_only_ievt,
            not_puls_ievt,
        )

        # function to check if par values are outside some pre-defined limits
        status = analysis.check_par_values(
            utime_array, par_np_array, parameter, detector, det_type
        )
        times = [datetime.fromtimestamp(t) for t in utime_array]
        start_time = times[0]
        end_time = times[-1]

        utime_list = utime_array.tolist()
        par_np_list = par_np_array.tolist()
        y_list = [index for i in range(0, len(utime_list))]
        ax.plot3D(utime_list, y_list, par_np_list, color=col, zorder=-index, alpha=0.9)
        ax.set_xlim3d(utime_list[0], utime_list[-1])

        # fill the map with status flags
        if det_type == "spms":
            detector = str(detector)
        if detector not in map_dict:
            map_dict[detector] = status
        else:
            if map_dict[detector] == 0:
                map_dict[detector] = status

        # skip those detectors that are not within the time window
        if start_time == 0 and end_time == 0:
            continue
        start_times.append(start_time)
        end_times.append(end_time)

    """
    # x-axis in dates (not working...)
    local_timezone = datetime.now(timezone.utc).astimezone().tzinfo
    locs = np.linspace(
        dates.date2num(start_time), dates.date2num(end_time), 5
    )
    labels = [dates.num2date(loc, tz=local_timezone).strftime("%d/%m\n%H:%M") for loc in locs]
    ax.set_xticks(locs)
    ax.set_xticklabels(labels)
    """

    # plot features
    ax.set_box_aspect(aspect=(1, 1, 0.5))  # aspect ratio for axes

    ax.set_xlabel("Time (UTC)", labelpad=15)  # axes labels
    zlab = j_par[0][parameter]["label"]
    if parameter in no_variation_pars:
        if j_par[0][parameter]["units"] != "null":
            zlab = zlab + " [" + j_par[0][parameter]["units"] + "]"
        if parameter == "event_rate":
            units = j_config[5]["Available-par"]["Other-par"]["event_rate"]["units"][
                det_type
            ]
            zlab = zlab + " [" + units + "]"
    else:
        zlab += ", %"
    ax.set_zlabel(zlab)

    # define new y-axis values
    yticks_loc = [i for i in range(0, len(y_values))]
    ax.set_yticks(yticks_loc)
    ax.set_yticklabels(y_values, ha="left")  # change number into name

    # ax.set_xlim3d(dates.date2num(start_times[0]), dates.date2num(end_times[-1]))
    ax.set_ylim3d(0, len(det_list))
    fig.subplots_adjust(left=-0.21)  # to move the plot towards the left

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

    return map_dict
