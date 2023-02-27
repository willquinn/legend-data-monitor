import shelve

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pandas import DataFrame
from seaborn import color_palette

from . import analysis_data, plot_styles, status_plot, subsystem, utils

# -------------------------------------------------------------------------

# global variable to be filled later with colors based on number of channels
COLORS = []

# -------------------------------------------------------------------------
# main plotting function(s)
# -------------------------------------------------------------------------

# plotting function that makes subsystem plots
# feel free to write your own one using Dataset, Subsystem and ParamData objects
# for example, this structure won't work to plot one parameter VS the other


def make_subsystem_plots(subsystem: subsystem.Subsystem, plots: dict, plt_path: str):
    pdf = PdfPages(plt_path + "-" + subsystem.type + ".pdf")
    out_dict = {}

    # for param in subsys.parameters:
    for plot_title in plots:
        utils.logger.info(
            "\33[95m~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\33[0m"
        )
        utils.logger.info(f"\33[95m~~~ P L O T T I N G : {plot_title}\33[0m")
        utils.logger.info(
            "\33[95m~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\33[0m"
        )

        # --- original plot settings provided in json
        # - parameter of interest
        # - event type all/pulser/phy/Klines
        # - variation (bool)
        # - time window (for event rate or vs time plot)
        plot_settings = plots[plot_title]

        # --- defaults
        # default time window None if not parameter event rate will be accounted for in AnalysisData,
        # here need to account for plot style vs time (None for all others)
        if "time_window" not in plot_settings:
            plot_settings["time_window"] = None
        # same, here need to account for unit label %
        if "variation" not in plot_settings:
            plot_settings["variation"] = False
        # !? this is not needed because is checked in AnalysisData
        # if "cuts" not in plot_settings:
        #     plot_settings["cuts"] = []

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
        # cuts will be loaded but not applied; for our purposes, need to apply the cuts right away
        # currently only K lines cut is used, and only data after cut is plotted -> just replace
        data_analysis.data = data_analysis.apply_all_cuts()
        utils.logger.debug(data_analysis.data)

        # -------------------------------------------------------------------------
        # set up plot info
        # -------------------------------------------------------------------------

        # --- color settings using a pre-defined palette
        # num colors needed = max number of channels per string
        # - find number of unique positions in each string
        # - get maximum occurring
        if plot_settings["plot_structure"] == "per cc4":
            max_ch_per_string = (
                data_analysis.data.groupby("cc4_id")["cc4_channel"].nunique().max()
            )
        else:
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
            "unit": utils.PLOT_INFO[plot_settings["parameters"]]["unit"],
            "plot_style": plot_settings["plot_style"],
        }

        # --- information needed for plot style
        plot_info["parameter"] = plot_settings[
            "parameters"
        ]  # could be multiple in the future!
        plot_info["label"] = utils.PLOT_INFO[plot_info["parameter"]]["label"]
        # unit label should be % if variation was asked
        plot_info["unit_label"] = (
            "%" if plot_settings["variation"] else plot_info["unit"]
        )
        # time window might be needed fort he vs time function
        plot_info["time_window"] = plot_settings["time_window"]
        # threshold values are needed for status map; might be needed for plotting limits on canvas too
        if subsystem.type != "pulser":
            plot_info["limits"] = (
                utils.PLOT_INFO[plot_info["parameter"]]["limits"][subsystem.type][
                    "variation"
                ]
                if plot_settings["variation"]
                else utils.PLOT_INFO[plot_info["parameter"]]["limits"][subsystem.type][
                    "absolute"
                ]
            )

        # -------------------------------------------------------------------------
        # call chosen plot structure
        # -------------------------------------------------------------------------

        # choose plot function based on user requested structure e.g. per channel or all ch together
        plot_structure = PLOT_STRUCTURE[plot_settings["plot_structure"]]
        utils.logger.debug("Plot structure: " + plot_settings["plot_structure"])

        par_dict_content = plot_structure(data_analysis, plot_info, pdf)

        # make a special status plot
        if "status" in plot_settings and plot_settings["status"]:
            if subsystem.type == "pulser":
                utils.logger.debug(
                    "Thresholds are not enabled for pulser! Use you own eyes to do checks there"
                )
            else:
                # For some reason, after some plotting functions the index is set to "channel".
                # We need to set it back otherwise status_plot.py gets crazy and everything crashes.
                data_analysis.data = data_analysis.data.reset_index()
                status_fig = status_plot.status_plot(
                    subsystem, data_analysis, plot_info, pdf
                )
                par_dict_content[plot_info["subsystem"] + "_map"] = status_fig

        # saving of param dictionary in the global dictionary that will be stored in the shelve object
        if plot_settings["event_type"] in out_dict.keys():
            out_dict[plot_settings["event_type"]] = {
                plot_info["parameter"]: par_dict_content
            }
        else:
            # empty dictionary (not filled yet)
            if len(out_dict.keys()) == 0:
                out_dict = {
                    plot_settings["event_type"]: {
                        plot_info["parameter"]: par_dict_content
                    }
                }
            # the dictionary already contains something (but for another event type selection)
            else:
                out_dict[plot_settings["event_type"]] = {
                    plot_info["parameter"]: par_dict_content
                }

    # save in shelve object
    out_file = shelve.open(plt_path)
    out_file["monitoring"] = out_dict
    out_file.close()

    # save in pdf object
    pdf.close()

    utils.logger.info(
        f"\33[92mAll plots saved in: {plt_path}-{subsystem.type}.pdf\33[0m"
    )


# -------------------------------------------------------------------------------
# different plot structure functions, defining figures and subplot layouts
# -------------------------------------------------------------------------------

# See mapping user plot structure keywords to corresponding functions in the end of this file


def plot_per_ch(data_analysis, plot_info, pdf):
    # --- choose plot function based on user requested style e.g. vs time or histogram
    plot_style = plot_styles.PLOT_STYLE[plot_info["plot_style"]]
    utils.logger.debug("Plot style: " + plot_info["plot_style"])

    par_dict = {}
    data_analysis.data = data_analysis.data.sort_values(["location", "position"])

    # -------------------------------------------------------------------------------

    # separate figure for each string/fiber ("location")
    for location, data_location in data_analysis.data.groupby("location"):
        utils.logger.debug(f"... {plot_info['locname']} {location}")

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
            utils.logger.debug(f"...... position {position}")

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

            # plot line at 0% for variation
            if plot_info["unit_label"] == "%":
                axes[ax_idx].axhline(y=0, color="gray", linestyle="--")

            ax_idx += 1

        # -------------------------------------------------------------------------------

        fig.suptitle(f"{plot_info['subsystem']} - {plot_info['title']}")
        axes[0].set_title(f"{plot_info['locname']} {location}")

        plt.savefig(pdf, format="pdf", bbox_inches="tight")
        # figures are retained until explicitly closed; close to not consume too much memory
        plt.close()

    return par_dict


def plot_per_cc4(data_analysis, plot_info, pdf):
    # --- choose plot function based on user requested style e.g. vs time or histogram
    plot_style = plot_styles.PLOT_STYLE[plot_info["plot_style"]]
    utils.logger.debug("Plot style: " + plot_info["plot_style"])

    par_dict = {}

    # --- create plot structure
    # number of cc4s
    no_cc4_id = len(data_analysis.data["cc4_id"].unique())
    # set constrained layout to accommodate figure suptitle
    fig, axes = plt.subplots(
        no_cc4_id,
        figsize=(10, no_cc4_id * 3),
        sharex=True,
        sharey=True,
        constrained_layout=True,
    )

    # -------------------------------------------------------------------------------
    # create label of format hardcoded for geds sXX-pX-chXXX-name-CC4channel
    # -------------------------------------------------------------------------------
    labels = data_analysis.data.groupby("channel").first()[
        ["name", "position", "location", "cc4_channel", "cc4_id"]
    ]
    labels["channel"] = labels.index
    labels["label"] = labels[
        ["location", "position", "channel", "name", "cc4_channel"]
    ].apply(lambda x: f"s{x[0]}-p{x[1]}-ch{str(x[2]).zfill(3)}-{x[3]}-{x[4]}", axis=1)
    # put it in the table
    data_analysis.data = data_analysis.data.set_index("channel")
    data_analysis.data["label"] = labels["label"]

    # -------------------------------------------------------------------------------
    # plot
    # -------------------------------------------------------------------------------

    data_analysis.data = data_analysis.data.sort_values(
        ["cc4_id", "cc4_channel", "label"]
    )
    # new subplot for each string
    ax_idx = 0
    for cc4_id, data_cc4_id in data_analysis.data.groupby("cc4_id"):
        utils.logger.debug(f"... CC4 {cc4_id}")

        # new color for each channel
        col_idx = 0
        labels = []
        for label, data_channel in data_cc4_id.groupby("label"):
            cc4_channel = (label.split("-"))[-1]
            utils.logger.debug(f"...... channel {cc4_channel}")
            ch_dict = plot_style(
                data_channel, fig, axes[ax_idx], plot_info, COLORS[col_idx]
            )
            labels.append(label)
            col_idx += 1

            channel = ((label.split("-")[2]).split("ch")[-1]).lstrip("0")
            if channel not in par_dict.keys():
                par_dict[channel] = ch_dict

        # add grid
        axes[ax_idx].grid("major", linestyle="--")
        # beautification
        axes[ax_idx].set_title(f"{plot_info['locname']} {cc4_id}")
        axes[ax_idx].set_ylabel("")
        axes[ax_idx].legend(labels=labels, loc="center left", bbox_to_anchor=(1, 0.5))

        # plot the position of the two K lines
        if plot_info["title"] == "K lines":
            axes[ax_idx].axhline(y=1460.822, color="gray", linestyle="--")
            axes[ax_idx].axhline(y=1524.6, color="gray", linestyle="--")

        # plot line at 0% for variation
        if plot_info["unit_label"] == "%":
            axes[ax_idx].axhline(y=0, color="gray", linestyle="--")
        ax_idx += 1

    # -------------------------------------------------------------------------------
    fig.suptitle(f"{plot_info['subsystem']} - {plot_info['title']}")
    # fig.supylabel(f'{plotdata.param.label} [{plotdata.param.unit_label}]') # --> plot style
    plt.savefig(pdf, format="pdf", bbox_inches="tight")
    # figures are retained until explicitly closed; close to not consume too much memory
    plt.close()

    return par_dict


# technically per location
def plot_per_string(data_analysis, plot_info, pdf):
    # --- choose plot function based on user requested style e.g. vs time or histogram
    plot_style = plot_styles.PLOT_STYLE[plot_info["plot_style"]]
    utils.logger.debug("Plot style: " + plot_info["plot_style"])

    par_dict = {}

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
    # create label of format hardcoded for geds pX-chXXX-name
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
        utils.logger.debug(f"... {plot_info['locname']} {location}")

        # new color for each channel
        col_idx = 0
        labels = []
        for label, data_channel in data_location.groupby("label"):
            ch_dict = plot_style(
                data_channel, fig, axes[ax_idx], plot_info, COLORS[col_idx]
            )
            labels.append(label)
            col_idx += 1

            channel = ((label.split("-")[1]).split("ch")[-1]).lstrip("0")
            if channel not in par_dict.keys():
                par_dict[channel] = ch_dict

        # add grid
        axes[ax_idx].grid("major", linestyle="--")
        # beautification
        axes[ax_idx].set_title(f"{plot_info['locname']} {location}")
        axes[ax_idx].set_ylabel("")
        axes[ax_idx].legend(labels=labels, loc="center left", bbox_to_anchor=(1, 0.5))

        # plot the position of the two K lines
        if plot_info["title"] == "K lines":
            axes[ax_idx].axhline(y=1460.822, color="gray", linestyle="--")
            axes[ax_idx].axhline(y=1524.6, color="gray", linestyle="--")

        # plot line at 0% for variation
        if plot_info["unit_label"] == "%":
            axes[ax_idx].axhline(y=0, color="gray", linestyle="--")
        ax_idx += 1

    # -------------------------------------------------------------------------------
    fig.suptitle(f"{plot_info['subsystem']} - {plot_info['title']}")
    # fig.supylabel(f'{plotdata.param.label} [{plotdata.param.unit_label}]') # --> plot style
    plt.savefig(pdf, format="pdf", bbox_inches="tight")
    # figures are retained until explicitly closed; close to not consume too much memory
    plt.close()

    return par_dict


# -------------------------------------------------------------------------------
# SiPM specific structures
# -------------------------------------------------------------------------------


def plot_per_fiber_and_barrel(data_analysis: DataFrame, plot_info: dict, pdf: PdfPages):
    # here will be a function plotting SiPMs with:
    # - one figure for top and one for bottom SiPMs
    # - each figure has subplots with N columns and M rows where N is the number of fibers, and M is the number of positions (top/bottom -> 2)
    # this function will only work for SiPMs requiring a columns 'barrel' in the channel map
    # add a check in config settings check to make sure geds are not called with this structure to avoid crash
    pass


def plot_per_barrel_and_position(
    data_analysis: DataFrame, plot_info: dict, pdf: PdfPages
):
    # here will be a function plotting SiPMs with:
    # - one figure for each barrel-position combination (IB-top, IB-bottom, OB-top, OB-bottom) = 4 figures in total

    plot_style = plot_styles.PLOT_STYLE[plot_info["plot_style"]]
    utils.logger.debug("Plot style: " + plot_info["plot_style"])

    par_dict = {}
    import sys

    sys.exit(1)

    # UNDER CONSTRUCTION!!!

    # re-arrange dataframe to separate location: from location=[IB-015-016] to location=[IB] & fiber=[015-016]
    data_analysis.data["fiber"] = (
        data_analysis.data["location"].str.split().str[:-7].str.join("")
    )
    data_analysis.data["location"] = (
        data_analysis.data["location"].str.split().str[2:].str.join("")
    )

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
    # create label of format hardcoded for geds pX-chXXX-name
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
        utils.logger.debug(f"... {plot_info['locname']} {location}")

        # new color for each channel
        col_idx = 0
        labels = []
        for label, data_channel in data_location.groupby("label"):
            ch_dict = plot_style(
                data_channel, fig, axes[ax_idx], plot_info, COLORS[col_idx]
            )
            labels.append(label)
            col_idx += 1

            channel = ((label.split("-")[1]).split("ch")[-1]).lstrip("0")
            if channel not in par_dict.keys():
                par_dict[channel] = ch_dict

        # add grid
        axes[ax_idx].grid("major", linestyle="--")
        # beautification
        axes[ax_idx].set_title(f"{plot_info['locname']} {location}")
        axes[ax_idx].set_ylabel("")
        axes[ax_idx].legend(labels=labels, loc="center left", bbox_to_anchor=(1, 0.5))

        # plot the position of the two K lines
        if plot_info["title"] == "K lines":
            axes[ax_idx].axhline(y=1460.822, color="gray", linestyle="--")
            axes[ax_idx].axhline(y=1524.6, color="gray", linestyle="--")

        # plot line at 0% for variation
        if plot_info["unit_label"] == "%":
            axes[ax_idx].axhline(y=0, color="gray", linestyle="--")
        ax_idx += 1

    # -------------------------------------------------------------------------------
    fig.suptitle(f"{plot_info['subsystem']} - {plot_info['title']}")
    # fig.supylabel(f'{plotdata.param.label} [{plotdata.param.unit_label}]') # --> plot style
    plt.savefig(pdf, format="pdf", bbox_inches="tight")
    # figures are retained until explicitly closed; close to not consume too much memory
    plt.close()
    return par_dict


# -------------------------------------------------------------------------------
# mapping user keywords to plot style functions
# -------------------------------------------------------------------------------

PLOT_STRUCTURE = {
    "per channel": plot_per_ch,
    "per cc4": plot_per_cc4,
    "per string": plot_per_string,
    "per fiber": plot_per_fiber_and_barrel,
    "per barrel": plot_per_barrel_and_position,
}
