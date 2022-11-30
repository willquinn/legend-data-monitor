from __future__ import annotations

import os
import pickle as pkl
from datetime import datetime

import ipywidgets as widget
import matplotlib.pyplot as plt

from . import analysis

j_config, _, _ = analysis.read_json_files()
output = j_config[0]["path"]["output"]


def get_day_hour(date: str):
    """
    Get the time interval if a time cut is applied, otherwise return 'no time cuts'.

    Parameters
    ----------
    date
        Selected time interval (if present, the format is of the type '20220922T093400Z_20220922T161000Z':
        the first timestamp corresponds to the start time, the second timestamps corresponds to the stop time)
    """
    if "T" in date:
        start = date.split("_")[0][:-1]
        stop = date.split("_")[1][:-1]
        start_day = datetime.strptime(start, "%Y%m%dT%H%M%S").strftime("%Y/%m/%d %H:%M")
        stop_day = datetime.strptime(stop, "%Y%m%dT%H%M%S").strftime("%Y/%m/%d %H:%M")
        time_interval = start_day + " -> " + stop_day
    else:
        time_interval = "no time cuts"

    return time_interval


def get_dates_pars():
    """Get info for each detector type (geds/spms/ch000) about generated pkl files. Return output folder's path, plus lists containing info about time cuts, parameters, maps."""
    pkl_files = os.listdir(f"{output}pkl-files/par-vs-time/")
    pkl_files = [file for file in pkl_files if "pkl" in file]

    geds_list = [
        file
        for file in pkl_files
        if "S" in file.split("-")[-1]
        if "ch000.pkl" not in file
    ]
    spms_list = [
        file
        for file in pkl_files
        if "S" not in file.split("-")[-1]
        if "ch000.pkl" not in file
    ]
    ch000_list = [file for file in pkl_files if "ch000.pkl" in file]

    # geds
    if geds_list != []:
        # configuration
        geds_map = list(
            dict.fromkeys([file.split("-")[-1].split(".")[0] for file in geds_list])
        )
        # parameters
        geds_par = list(dict.fromkeys([file.split("-")[-2] for file in geds_list]))
        # date
        geds_date = sorted(
            list(dict.fromkeys([file.split("-")[-3] for file in geds_list]))
        )
        # print("\ngeds strings:", geds_map)
        # print("geds parameters:", geds_par)
    else:
        geds_map = geds_par = geds_date = []
        # print("\n-> NO data for geds were found")

    geds_date_formatted = [get_day_hour(date) for date in geds_date]
    geds_time_option = [
        (key, value) for key, value in zip(geds_date_formatted, geds_date)
    ]
    if "no time cuts" in geds_date_formatted:
        geds_time_option = [("all", "no_time_cuts")]
        geds_date = ["no_time_cuts"]
    # print("geds dates:", geds_date)

    # spms
    if spms_list != []:
        # configuration
        spms_map = list(
            dict.fromkeys([file.split("-")[-1].split(".")[0] for file in spms_list])
        )
        # parameters
        spms_par = list(dict.fromkeys([file.split("-")[-2] for file in spms_list]))
        # dates
        spms_date = sorted(
            list(dict.fromkeys([file.split("-")[-3] for file in spms_list]))
        )
        # print("\nspms barrels:", spms_map)
        # print("spms parameters:", spms_par)
    else:
        spms_map = spms_par = spms_date = []
        # print("\n-> NO data for spms were found")

    spms_date_formatted = [get_day_hour(date) for date in spms_date]
    spms_time_option = [
        (key, value) for key, value in zip(spms_date_formatted, spms_date)
    ]
    if "no time cuts" in spms_date_formatted:
        spms_time_option = [("all", "no_time_cuts")]
        spms_date = ["no_time_cuts"]

    # ch000
    if ch000_list != []:
        # parameters
        ch000_par = list(dict.fromkeys([file.split("-")[-2] for file in ch000_list]))
        # date
        ch000_date = sorted(
            list(dict.fromkeys([file.split("-")[-3] for file in ch000_list]))
        )
        # print("\nch000 parameters:", ch000_par)
    else:
        ch000_par = ch000_date = []
        # print("\n-> NO data for ch000 were found")

    ch000_date_formatted = [get_day_hour(date) for date in ch000_date]
    ch000_time_option = [
        (key, value) for key, value in zip(ch000_date_formatted, ch000_date)
    ]
    if "no time cuts" in ch000_date_formatted:
        ch000_time_option = [("all", "no_time_cuts")]
        ch000_date = ["no_time_cuts"]

    geds_info = [geds_date, geds_par, geds_map, geds_time_option]
    spms_info = [spms_date, spms_par, spms_map, spms_time_option]
    ch000_info = [ch000_date, ch000_par, ch000_time_option]

    return output, geds_info, spms_info, ch000_info


def widgets(
    geds_info: list[list[str]], spms_info: list[list[str]], ch000_info: list[list[str]]
):
    """
    Create widget buttons for each detector type (geds/spms/ch000).

    Parameters
    ----------
    geds_info
        Time/parameters/map info for geds
    spms_info
        Time/parameters/map info for spms
    ch000_info
        Time/parameters info for ch000
    """
    # select widget for selecting the date (for geds)
    if geds_info[0] != []:
        geds_time_select = widget.Select(
            options=geds_info[3],
            value=geds_info[0][0],
            description="Time:",
            disabled=False,
            layout={"width": "max-content"},
        )
    else:
        geds_time_select = []
    # select widget for selecting the date (for spms)
    if spms_info[0] != []:
        spms_time_select = widget.Select(
            options=spms_info[3],
            value=spms_info[0][0],
            description="Time:",
            disabled=False,
            layout={"width": "max-content"},
        )
    else:
        spms_time_select = []
    # select widget for selecting the date (for ch000)
    if ch000_info[0] != []:
        ch000_time_select = widget.Select(
            options=ch000_info[2],
            value=ch000_info[0][0],
            description="Time:",
            disabled=False,
            layout={"width": "max-content"},
        )
    else:
        ch000_time_select = []

    # tab for selecting parameters to plot (for geds)
    par_geds_buttons = widget.ToggleButtons(
        options=geds_info[1],
        description="Parameter:",
        disabled=False,
        button_style="",
        tooltips=[],
    )
    # tab for selecting parameters to plot (for spms)
    par_spms_buttons = widget.ToggleButtons(
        options=spms_info[1],
        description="Parameter:",
        disabled=False,
        button_style="",
        tooltips=[],
    )
    # tab for selecting parameters to plot (for ch000)
    par_ch000_buttons = widget.ToggleButtons(
        options=ch000_info[1],
        description="Parameter:",
        disabled=False,
        button_style="",
        tooltips=[],
    )

    # par-vs-time
    geds_map_buttons = widget.ToggleButtons(
        options=geds_info[2],
        description="String:",
        disabled=False,
        button_style="",
        tooltips=[],
    )
    spms_map_buttons = widget.ToggleButtons(
        options=spms_info[2],
        description="Position:",
        disabled=False,
        button_style="",
        tooltips=[],
    )

    geds_buttons = [geds_time_select, par_geds_buttons, geds_map_buttons]
    spms_buttons = [spms_time_select, par_spms_buttons, spms_map_buttons]
    ch000_buttons = [ch000_time_select, par_ch000_buttons]

    return geds_buttons, spms_buttons, ch000_buttons


def widgets_3dim():
    """Create a widget button for z-axis range and rotation angles."""
    # minimum value for z-axis range
    z_min = widget.FloatText(value=-10, description="z min:", disabled=False)
    # maximum value for z-axis range
    z_max = widget.FloatText(value=10, description="z max:", disabled=False)

    # slider for 3D angle view
    elevation_slider = widget.IntSlider(
        min=-360,
        max=360,
        step=5,
        value=20,
        description="Elevation angle [°]:",
        style={"description_width": "initial"},
    )

    azimuth_slider = widget.IntSlider(
        min=-360,
        max=360,
        step=5,
        value=-60,
        description="Azimuth angle [°]:",
        style={"description_width": "initial"},
    )

    widg_3dim = [z_min, z_max, elevation_slider, azimuth_slider]
    return widg_3dim


def plot_geds(
    pkl_name: str,
    output: str,
    geds_info: list[list[str]],
    geds_buttons,
):
    """
    Plot geds and return a function for widgets.

    Parameters
    ----------
    pkl_name
        String that contains info for reading pkl files. The format is: exp-period-datatype (ex. 'l60-p01-phy')
    geds_info
        Time/parameters/map info for geds
    geds_buttons
        Widget buttons for geds
    """
    if geds_info[0] == []:
        return None

    def get_geds(time_select: str, parameter: str, string: str):
        if time_select == "no_time_cuts":
            pkl.load(
                open(
                    f"{output}pkl-files/par-vs-time/{pkl_name}-{parameter}-{string}.pkl",
                    "rb",
                )
            )
        else:
            pkl.load(
                open(
                    f"{output}pkl-files/par-vs-time/{pkl_name}-{time_select}-{parameter}-{string}.pkl",
                    "rb",
                )
            )
        plt.show()

    out_geds = widget.interactive_output(
        get_geds,
        {
            "time_select": geds_buttons[0],
            "parameter": geds_buttons[1],
            "string": geds_buttons[2],
        },
    )

    return out_geds


def plot_geds_3dim(
    pkl_name: str,
    output: str,
    geds_info: list[list[str]],
    geds_buttons,
    range_button,
):
    """
    Plot geds in 3D and return a function for widgets.

    Parameters
    ----------
    pkl_name
        String that contains info for reading pkl files. The format is: exp-period-datatype (ex. 'l60-p01-phy')
    geds_info
        Time/parameters/map info for geds
    geds_buttons
        Widget buttons for geds
    range_button
        Widget button for z-axis range and rotation angles
    """
    if geds_info[0] == []:
        return None

    def get_geds_3dim(
        zmin: float,
        zmax: float,
        elevation: int,
        azimuth: int,
        time_select: str,
        parameter: str,
        string: str,
    ):
        if time_select == "no_time_cuts":
            ax = pkl.load(
                open(
                    f"{output}pkl-files/par-vs-time/{pkl_name}-{parameter}-{string}.pkl",
                    "rb",
                )
            )
        else:
            ax = pkl.load(
                open(
                    f"{output}pkl-files/par-vs-time/{pkl_name}-{time_select}-{parameter}-{string}.pkl",
                    "rb",
                )
            )
        ax.set_zlim3d(zmin, zmax)
        plt.subplots_adjust(top=1.2, right=1.1)
        # plt.subplots_adjust(top=1.2, right=1.2, bottom = -0.1)
        ax.view_init(elevation, azimuth)
        plt.show()

    out_geds = widget.interactive_output(
        get_geds_3dim,
        {
            "zmin": range_button[0],
            "zmax": range_button[1],
            "elevation": range_button[2],
            "azimuth": range_button[3],
            "time_select": geds_buttons[0],
            "parameter": geds_buttons[1],
            "string": geds_buttons[2],
        },
    )

    return out_geds


def plot_spms(
    pkl_name: str,
    output: str,
    spms_info: list[list[str]],
    spms_buttons,
):
    """
    Plot spms and return a function for widgets.

    Parameters
    ----------
    pkl_name
        String that contains info for reading pkl files. The format is: exp-period-datatype (ex. 'l60-p01-phy')
    spms_info
        Time/parameters/map info for spms
    spms_buttons
        Widget buttons for spms
    """
    if spms_info[0] == []:
        return None

    def get_spms(time_select: str, parameter: str, string: str):
        if time_select == "no_time_cuts":
            pkl.load(
                open(
                    f"{output}pkl-files/par-vs-time/{pkl_name}-{parameter}-{string}.pkl",
                    "rb",
                )
            )
        else:
            pkl.load(
                open(
                    f"{output}pkl-files/par-vs-time/{pkl_name}-{time_select}-{parameter}-{string}.pkl",
                    "rb",
                )
            )
        plt.show()

    out_spms = widget.interactive_output(
        get_spms,
        {
            "time_select": spms_buttons[0],
            "parameter": spms_buttons[1],
            "string": spms_buttons[2],
        },
    )

    return out_spms


def plot_ch000(
    pkl_name: str,
    output: str,
    ch000_info: list[list[str]],
    ch000_buttons,
):
    """
    Plot ch000 and return a function for widgets.

    Parameters
    ----------
    pkl_name
        String that contains info for reading pkl files. The format is: exp-period-datatype (ex. 'l60-p01-phy')
    ch000_info
        Time/parameters/map info for ch000
    ch000_buttons
        Widget buttons for ch000
    """
    if ch000_info[0] == []:
        return None

    def get_ch000(time_select: str, parameter: str):
        if time_select == "no_time_cuts":
            pkl.load(
                open(
                    f"{output}pkl-files/par-vs-time/{pkl_name}-{parameter}-ch000.pkl",
                    "rb",
                )
            )
        else:
            pkl.load(
                open(
                    f"{output}pkl-files/par-vs-time/{pkl_name}-{time_select}-{parameter}-ch000.pkl",
                    "rb",
                )
            )
        plt.show()

    out_ch000 = widget.interactive_output(
        get_ch000,
        {
            "time_select": ch000_buttons[0],
            "parameter": ch000_buttons[1],
        },
    )

    return out_ch000
