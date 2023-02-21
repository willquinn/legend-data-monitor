# needed to open files in settings/
import importlib.resources
import json
import logging
import shelve

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from seaborn import color_palette

from . import analysis_data, plot_styles, status_plot
from .subsystem import Subsystem

# load dictionary with plot info (= units, thresholds, label, ...)
pkg = importlib.resources.files("legend_data_monitor")
with open(pkg / "settings" / "par-settings.json") as f:
    PLOT_INFO = json.load(f)


# -------------------------------------------------------------------------

# global variable to be filled later with colors based on number of channels
COLORS = []

# -------------------------------------------------------------------------
# main plotting function(s)
# -------------------------------------------------------------------------

# plotting function that makes subsystem plots
# feel free to write your own one using Dataset, Subsystem and ParamData objects
# for example, this structure won't work to plot one parameter VS the other


def make_subsystem_plots(subsystem: Subsystem, plots: dict, plt_path: str):
    pdf = PdfPages(plt_path + ".pdf")
    out_dict = {}

    # for param in subsys.parameters:
    for plot_title in plots:
        logging.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        logging.info("~~~ P L O T T I N G  " + plot_title)
        logging.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

        # --- original plot settings provided in json
        # - parameter of interest
        # - event type all/pulser/phy/Klines
        # - variation (bool)
        # - time window (for event rate or vs time plot)
        plot_settings = plots[plot_title]
        # defaults
        if "time_window" not in plot_settings:
            plot_settings["time_window"] = None
        if "variation" not in plot_settings:
            plot_settings["variation"] = False

        # -------------------------------------------------------------------------
        # set up analysis data
        # -------------------------------------------------------------------------

        # --- AnalysisData:
        # - select parameter of interest
        # - subselect type of events (pulser/phy/all/klines)
        # - calculate variation from mean, if asked
        data_analysis = analysis_data.AnalysisData(
            subsystem.data, selection=plot_settings
        )

        # -------------------------------------------------------------------------
        # set up plot info
        # -------------------------------------------------------------------------

        # --- color settings using a pre-defined palette
        # num colors needed = max number of channels per string
        # - find number of unique positions in each string
        # - get maximum occurring
        max_ch_per_string = (
            data_analysis.data.groupby("location")["position"].nunique().max()
        )
        global COLORS
        COLORS = color_palette("hls", max_ch_per_string).as_hex()

        # --- information needed for plot structure
        # ! currently "parameters" is one parameter !
        # subject to change if one day want to plot multiple in one plot
        plot_info = {
            "title": plot_title,
            "subsystem": subsystem.type,
            "locname": {"geds": "string", "spms": "fiber", "pulser": "aux"}[
                subsystem.type
            ],
            "unit": PLOT_INFO[plot_settings["parameters"]]["unit"],
            "plot_style": plot_settings["plot_style"],
        }

        # --- information needed for plot style
        plot_info["parameter"] = plot_settings[
            "parameters"
        ]  # could be multiple in the future!
        plot_info["label"] = PLOT_INFO[plot_info["parameter"]]["label"]
        # unit label should be % if variation was asked
        plot_info["unit_label"] = (
            "%" if plot_settings["variation"] else plot_info["unit"]
        )
        # time window might be needed fort he vs time function
        plot_info["time_window"] = plot_settings["time_window"]
        # threshold values are needed for status map; might be needed for plotting limits on canvas too
        plot_info["limits"] = (
            PLOT_INFO[plot_info["parameter"]]["limits"][subsystem.type]["variation"]
            if plot_settings["variation"]
            else PLOT_INFO[plot_info["parameter"]]["limits"][subsystem.type]["absolute"]
        )

        # -------------------------------------------------------------------------
        # call chosen plot structure
        # -------------------------------------------------------------------------

        # choose plot function based on user requested structure e.g. per channel or all ch together
        plot_structure = plot_styles.PLOT_STRUCTURE[plot_settings["plot_structure"]]

        logging.info("Plot structure: " + plot_settings["plot_structure"])
        par_dict = plot_structure(data_analysis, plot_info, plt_path, pdf)

        # make a special status plot
        if "status" in plot_settings and plot_settings["status"]:
            if subsystem.type == "pulser":
                logging.info(
                    "Thresholds are not enabled for pulser! Use you own eyes to do checks there"
                )
            else:
                status_fig = status_plot.status_plot(
                    subsystem, data_analysis, plot_info, plt_path, pdf
                )
                par_dict[plot_info["subsystem"] + "_map"] = status_fig

        # final saving
        if plot_info["parameter"] not in out_dict.keys():
            out_dict[plot_info["parameter"]] = par_dict

    # save in shelve object
    out_file = shelve.open(plt_path)
    out_file[plot_settings["event_type"]] = out_dict
    out_file.close()
    # save in pdf object
    pdf.close()

    logging.info("- - - - - - - - - - - - - - - - - - - - - - -")
    logging.info("All plots saved in: " + plt_path + ".pdf")
    logging.info("- - - - - - - - - - - - - - - - - - - - - - -")


# -------------------------------------------------------------------------------
# different plot structure functions, defining figures and subplot layouts
# -------------------------------------------------------------------------------

# See mapping user plot structure keywords to corresponding functions in the end of this file


def plot_per_ch(data_analysis, plot_info, plt_path, pdf):
    # --- choose plot function based on user requested style e.g. vs time or histogram
    plot_style = plot_styles.PLOT_STYLE[plot_info["plot_style"]]
    logging.info("Plot style: " + plot_info["plot_style"])

    par_dict = {}
    data_analysis.data = data_analysis.data.sort_values(["location", "position"])

    # -------------------------------------------------------------------------------

    # separate figure for each string/fiber ("location")
    for location, data_location in data_analysis.data.groupby("location"):
        logging.info(f"... {plot_info['locname']} {location}")

        # -------------------------------------------------------------------------------
        # create plot structure: 1 column, N rows with subplot for each channel
        # -------------------------------------------------------------------------------

        # number of channels in this string/fiber
        numch = len(data_location["channel"].unique())
        # create corresponding number of subplots for each channel, set constrained layout to accommodate figure suptitle
        fig, axes = plt.subplots(
            nrows=numch,
            ncols=1,
            figsize=(10, numch * 3),
            sharex=True,
            constrained_layout=True,
        )  # , sharey=True)
        # in case of pulser, axes will be not a list but one axis -> convert to list
        if numch == 1:
            axes = [axes]

        # -------------------------------------------------------------------------------
        # plot
        # -------------------------------------------------------------------------------

        ax_idx = 0
        # plot one channel on each axis, ordered by position
        for position, data_channel in data_location.groupby("position"):
            logging.info(f"...... position {position}")

            # plot selected style on this axis
            ch_dict = plot_style(
                data_channel, fig, axes[ax_idx], plot_info, color=COLORS[ax_idx]
            )

            # --- add summary to axis
            # name, position and mean are unique for each channel - take first value
            t = data_channel.iloc[0][
                ["channel", "position", "name", plot_info["parameter"] + "_mean"]
            ]
            if t["channel"] not in par_dict.keys():
                par_dict[str(t["channel"])] = ch_dict

            text = (
                t["name"]
                + "\n"
                + f"channel {t['channel']}\n"
                + f"position {t['position']}\n"
                + f"mean {round(t[plot_info['parameter']+'_mean'],3)} [{plot_info['unit']}]"
            )
            axes[ax_idx].text(1.01, 0.5, text, transform=axes[ax_idx].transAxes)

            # add grid
            axes[ax_idx].grid("major", linestyle="--")
            # remove automatic y label since there will be a shared one
            axes[ax_idx].set_ylabel("")

            ax_idx += 1

        # -------------------------------------------------------------------------------

        fig.suptitle(f"{plot_info['subsystem']} - {plot_info['title']}")
        axes[0].set_title(f"{plot_info['locname']} {location}")

        plt.savefig(pdf, format="pdf")
        # figures are retained until explicitly closed; close to not consume too much memory
        plt.close()

    return par_dict


# technically per location
def plot_per_string(data_analysis, plot_info, plt_path, pdf):
    # --- choose plot function based on user requested style e.g. vs time or histogram
    plot_style = plot_styles.PLOT_STYLE[plot_info["plot_style"]]
    logging.info("Plot style: " + plot_info["plot_style"])

    par_dict = {}  # not actually filled

    # --- create plot structure
    # number of strings/fibers
    no_location = len(data_analysis.data["location"].unique())
    # set constrained layout to accommodate figure suptitle
    fig, axes = plt.subplots(
        no_location,
        figsize=(10, no_location * 3),
        sharex=True,
        sharey=True,
        constrained_layout=True,
    )

    # -------------------------------------------------------------------------------
    # create label of format hardcoded for geds sXX-pX-chXXX-name
    # -------------------------------------------------------------------------------

    labels = data_analysis.data.groupby("channel").first()[["name", "position"]]
    labels["channel"] = labels.index
    labels["label"] = labels[["position", "channel", "name"]].apply(
        lambda x: f"p{x[0]}-ch{str(x[1]).zfill(3)}-{x[2]}", axis=1
    )
    # put it in the table
    data_analysis.data = data_analysis.data.set_index("channel")
    data_analysis.data["label"] = labels["label"]
    data_analysis.data = data_analysis.data.sort_values("label")

    # -------------------------------------------------------------------------------
    # plot
    # -------------------------------------------------------------------------------

    data_analysis.data = data_analysis.data.sort_values(["location", "label"])
    # new subplot for each string
    ax_idx = 0
    for location, data_location in data_analysis.data.groupby("location"):
        logging.info(f"... {plot_info['locname']} {location}")

        # new color for each channel
        col_idx = 0
        labels = []
        for label, data_channel in data_location.groupby("label"):
            plot_style(data_channel, fig, axes[ax_idx], plot_info, COLORS[col_idx])
            labels.append(label)
            col_idx += 1

        axes[ax_idx].set_title(f"{plot_info['locname']} {location}")
        axes[ax_idx].set_ylabel("")
        axes[ax_idx].legend(labels=labels, loc="center left", bbox_to_anchor=(1, 0.5))
        ax_idx += 1

    # -------------------------------------------------------------------------------

    fig.suptitle(f"{plot_info['subsystem']} - {plot_info['title']}")
    # fig.supylabel(f'{plotdata.param.label} [{plotdata.param.unit_label}]') # --> plot style
    plt.savefig(pdf, format="pdf")
    # figures are retained until explicitly closed; close to not consume too much memory
    plt.close()

    return par_dict


# -------------------------------------------------------------------------------
# SiPM specific structures
# -------------------------------------------------------------------------------


def plot_per_barrel(data_analysis, plot_info, pdf):
    # here will be a function plotting SiPMs with:
    # - one figure for top and one for bottom SiPMs
    # - each figure has subplots with N columns and M rows where N is the number of fibers, and M is the number of positions (top/bottom -> 2)
    # this function will only work for SiPMs requiring a columns 'barrel' in the channel map
    # add a check in config settings check to make sure geds are not called with this structure to avoid crash
    pass


def plot_per_barrel_and_position(data_analysis, plot_info, pdf):
    # here will be a function plotting SiPMs with:
    # - one figure for each barrel-position combination (IB-top, IB-bottom, OB-top, OB-bottom; pr IB-top, OB-top, IB-bottom, OB-bottom)
    # - subplots for each fiber
    pass


# -------------------------------------------------------------------------------
# mapping user keywords to plot style functions
# -------------------------------------------------------------------------------

PLOT_STRUCTURE = {
    "per channel": plot_per_ch,
    "per string": plot_per_string,
    "per barrel": plot_per_barrel,
    "top bottom": plot_per_barrel_and_position,
}
