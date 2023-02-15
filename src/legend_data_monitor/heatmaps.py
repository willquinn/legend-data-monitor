import logging
import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

from . import parameter_data as paramdata


# ---- main plotting function
def make_subsystem_heatmaps(subsys, plot_settings):
    # !! this is wrong here
    # there could be 2 subsystems in config: pdf should be not per subsystem, but per parameter
    # in principle, i think one DataMonitor run will have one PDF with everything in it - geds, spms, all the plots
    # so that after it launches automatically, produces one pdf per run, and RunTeam or someone can analyse the run behavior
    # -> TBD
    out_name = os.path.join(
        plot_settings.output_paths["pdf_files"],
        "heatmaps",
        plot_settings.basename + "_" + subsys.type + ".pdf",
    )
    pdf = PdfPages(out_name)

    for param in subsys.parameters:
        # select data from subsystem data for given parameter based on parameter settings
        pardata = paramdata.ParamData(subsys, param, plot_settings)

        # decide plot function based on user requested style (see dict below)
        generate_heatmap = plot_style[pardata.subsys]

        logging.error("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        logging.error("~~~ H E A T M A P S")
        logging.error("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        generate_heatmap(pardata, pdf)

    pdf.close()
    logging.error("All plots saved in: " + out_name)


def geds_map(pardata, pdf):
    """Create a heatmap for germanium detectors."""
    data = pardata.data.sort_values(["location", "position"])

    low_thr = pardata.param_info.limit[pardata.subsys][0]
    high_thr = pardata.param_info.limit[pardata.subsys][1]

    logging.error("...low threshold for " + pardata.param + " set at: " + str(low_thr))
    logging.error(
        "...high threshold for " + pardata.param + " set at: " + str(high_thr)
    )

    plot_title = f"{pardata.subsys} - "
    if low_thr is not None or high_thr is not None:
        if low_thr is None and high_thr is not None:
            plot_title += f"{pardata.param} > {high_thr}"
        if low_thr is not None and high_thr is None:
            plot_title += f"{pardata.param} < {low_thr}"
        if low_thr is not None and high_thr is not None:
            plot_title += f"{pardata.param} < {low_thr} || {pardata.param} > {high_thr}"
    if low_thr is None and high_thr is None:
        plot_title += f"{pardata.param} (no checks)"

    new_dataframe = pd.DataFrame()
    # loop over individual channels (otherwise, the problematic timestamps apply to all detectors, even the OK ones) and create a summary dataframe
    for channel in data["channel"].unique():
        # select one block of DataFrame
        data_per_ch = data.loc[data["channel"] == channel]

        status = 0  # -> OK detector
        if low_thr is not None or high_thr is not None:
            if low_thr is None and high_thr is not None:
                if (data_per_ch[pardata.param] > high_thr).any():
                    status = 1  # -> problematic detector
            if low_thr is not None and high_thr is None:
                if (data_per_ch[pardata.param] < low_thr).any():
                    status = 1  # -> problematic detector
                    plot_title += f"{pardata.param} < {low_thr}"
            if low_thr is not None and high_thr is not None:
                if (data_per_ch[pardata.param] < low_thr).any() or (
                    data_per_ch[pardata.param] > high_thr
                ).any():
                    status = 1  # -> problematic detector
                    plot_title += (
                        f"{pardata.param} < {low_thr} || {pardata.param} > {high_thr}"
                    )

        # create a new row in the new dataframe with essential info (ie: channel, name, location, position, status)
        name = (data_per_ch["name"].unique())[0]
        location = (data_per_ch["location"].unique())[0]
        position = (data_per_ch["position"].unique())[0]
        new_row = [[channel, name, location, position, status]]
        new_df = pd.DataFrame(
            new_row, columns=["channel", "name", "location", "position", "status"]
        )
        new_dataframe = pd.concat([new_dataframe, new_df], ignore_index=True, axis=0)

    # --------------------------------------------------------------------------------------------------------------------------
    # include OFF channels and see what is their status
    for channel in pardata.status_map.keys():
        det = int(channel.split("ch")[-1])

        # check if the channel is already in the status dataframe; if not, add a new row for it
        if det not in new_dataframe["channel"].values:
            # get status info
            if (pardata.status_map[channel]).software_status == "Off":
                status = 3
            if (pardata.status_map[channel]).software_status == "AC":
                status = 2  # is at "AC"? CHECK IT!

            # get position within the array + other necessary info
            name = (pardata.channel_map[det]).name
            location = (pardata.channel_map[det]).location.string
            position = (pardata.channel_map[det]).location.position

            # define new row for not-ON detectors
            new_row = [[det, name, location, position, status]]
            new_df = pd.DataFrame(
                new_row, columns=["channel", "name", "location", "position", "status"]
            )
            # add the new row to the dataframe (order?)
            new_dataframe = pd.concat(
                [new_dataframe, new_df], ignore_index=True, axis=0
            )

    # --------------------------------------------------------------------------------------------------------------------------
    # sort the dataframe according to channel ID number
    new_dataframe = new_dataframe.sort_values("channel")
    new_dataframe = new_dataframe.reset_index()
    new_dataframe = new_dataframe.drop(
        columns=["index"]
    )  # somehow, an index column appears: remove it

    # create a pivot with necessary info
    result = new_dataframe.pivot(index="position", columns="location", values="status")

    # --------------------------------------------------------------------------------------------------------------------------
    # create the figure
    plt.figure(num=None, figsize=(8, 12), dpi=80, facecolor="w", edgecolor="k")
    sns.set(font_scale=1)

    # create labels for dets
    labels = new_dataframe.pivot(index="position", columns="location", values="name")

    # labels definition (AFTER having included OFF detectors too)
    # LOCATION:
    x_axis_labels = [f"S{no}" for no in new_dataframe["location"].unique()]
    # POSITION:
    y_axis_labels = [
        no
        for no in range(
            min(new_dataframe["position"].unique()),
            max(new_dataframe["position"].unique() + 1),
        )
    ]

    # to account for empty strings: not a good idea actually...
    # In L60, there are S1,S2,S7,S8: do we really want to display 4 empty strings, i.e. S3-S6? There is no need!
    # x_axis_labels = [f"S{no}" for no in range(min(new_dataframe["location"].unique()), max(new_dataframe["location"].unique()+1))]

    # status map (0=OK, 1=X, 2=AC, 3=OFF)
    custom_cmap = ["#318CE7", "#CC0000", "#F7AB60", "#D0D0D0", "#FFFFFF"]

    # create the heatmap
    status_map = sns.heatmap(
        data=result,
        annot=labels,
        annot_kws={"size": 6},
        vmin=0,
        vmax=len(custom_cmap),
        yticklabels=y_axis_labels,
        xticklabels=x_axis_labels,
        fmt="s",
        cmap=custom_cmap,
        cbar=True,
        cbar_kws={"shrink": 0.5},
        linewidths=1,
        linecolor="white",
        square=True,
        rasterized=True,
    )

    # set user defined heatmap colours
    colorbar = status_map.collections[0].colorbar
    colorbar.set_ticks([1 / 2, 3 / 2, 5 / 2, 7 / 2])
    colorbar.set_ticklabels(["OK", "X", "AC", "OFF"])

    plt.tick_params(
        axis="both",
        which="major",
        # labelsize=20,
        labelbottom=False,
        bottom=False,
        top=False,
        labeltop=True,
    )
    plt.yticks(rotation=0)
    plt.title(plot_title)
    pdf.savefig(bbox_inches="tight")


def spms_map(pardata, pdf):
    """Create a heatmap for SiPMs."""
    logging.error("Spms heatmap has not yet been implemented!")


# mapping user keywords to heatmap style functions
plot_style = {
    "geds": geds_map,
    "spms": spms_map,
}
