# -------------------------------------------------------------------------------
# different plot style functions called from the main one depending on parameter
# -------------------------------------------------------------------------------

# See mapping user plot structure keywords to corresponding functions in the end of this file

from math import ceil

from matplotlib.dates import DateFormatter, date2num
from matplotlib.ticker import FixedLocator
from pandas import Timedelta


def plot_vs_time(data_channel, fig, ax, plot_info, color=None):
    # -------------------------------------------------------------------------
    # plot this data vs time
    # -------------------------------------------------------------------------

    # need to plot this way, and not data_position.plot(...) because the datetime column is of type Timestamp
    # plotting this way, to_pydatetime() converts it to type datetime which is needed for DateFormatter
    # changing the type of the column itself with the table does not work
    data_channel = data_channel.sort_values("datetime")
    ax.plot(
        data_channel["datetime"].dt.to_pydatetime(),
        data_channel[plot_info["parameter"]],
        zorder=0,
        color=color if plot_info["parameter"] == "event_rate" else "darkgray",
    )

    # -------------------------------------------------------------------------
    # plot resampled average
    # -------------------------------------------------------------------------

    # unless event rate - already resampled and counted in some time window
    if not plot_info["parameter"] == "event_rate":
        # resample in given time window, as start pick the first timestamp in table
        resampled = (
            data_channel.set_index("datetime")
            .resample(plot_info["time_window"], origin="start")
            .mean(numeric_only=True)
        )
        # will have datetime as index after resampling -> put back
        resampled = resampled.reset_index()
        # the timestamps in the resampled table will start from the first timestamp, and go with sampling intervals
        # I want to shift them by half sampling window, so that the resampled value is plotted in the middle time window in which it was calculated
        resampled["datetime"] = (
            resampled["datetime"] + Timedelta(plot_info["time_window"]) / 2
        )

        ax.plot(
            resampled["datetime"].dt.to_pydatetime(),
            resampled[plot_info["parameter"]],
            color=color,
            zorder=1,
            marker="o",
            linestyle="-",
        )

    # -------------------------------------------------------------------------
    # beautification
    # -------------------------------------------------------------------------

    # --- time ticks/labels on x-axis
    # index step width for taking every 10th time point
    every_10th_index_step = ceil(len(data_channel) / 10.0)
    # get corresponding time points
    # if there are less than 10 points in total in the frame, the step will be 0 -> take all points
    timepoints = (
        data_channel.iloc[::every_10th_index_step]["datetime"]
        if every_10th_index_step
        else data_channel["datetime"]
    )

    # set ticks and date format
    ax.xaxis.set_major_locator(
        FixedLocator([date2num(x) for x in timepoints.dt.to_pydatetime()])
    )
    ax.xaxis.set_major_formatter(DateFormatter("%Y\n%m/%d\n%H:%M"))

    # --- set labels
    fig.supxlabel("UTC Time")
    fig.supylabel(f"{plot_info['label']} [{plot_info['unit_label']}]")


def plot_histo(data_channel, fig, ax, plot_info, color=None):
    # --- histo range
    # !! in the future take from par-settings
    # needed for cuspEmax because with geant outliers not possible to view normal histo
    hrange = {"keV": [0, 2500]}
    # take full range if not specified
    x_min = (
        hrange[plot_info["unit"]][0]
        if plot_info["unit"] in hrange
        else data_channel[plot_info["parameter"]].min()
    )
    x_max = (
        hrange[plot_info["unit"]][1]
        if plot_info["unit"] in hrange
        else data_channel[plot_info["parameter"]].max()
    )

    # --- bin width
    bwidth = {"keV": 2.5}  # what to do with binning???
    bin_width = bwidth[plot_info["unit"]] if plot_info["unit"] in bwidth else None
    no_bins = int((x_max - x_min) / bin_width) if bin_width else 50

    # -------------------------------------------------------------------------

    data_channel[plot_info["parameter"]].plot.hist(
        bins=no_bins,
        range=[x_min, x_max],
        histtype="step",
        linewidth=1.5,
        ax=ax,
        color=color,
    )

    # -------------------------------------------------------------------------

    ax.set_yscale("log")
    fig.supxlabel(f"{plot_info['label']} [{plot_info['unit_label']}]")


def plot_scatter(data_channel, fig, ax, plot_info, color=None):
    ax.scatter(
        data_channel["datetime"].dt.to_pydatetime(),
        data_channel[plot_info["parameter"]],
        color=color,
    )

    ax.xaxis.set_major_formatter(DateFormatter("%Y\n%m/%d\n%H:%M"))
    fig.supxlabel("UTC Time")


def plot_heatmap(data_channel, fig, ax, plot_info, color=None):
    # here will be a function to plot a SiPM heatmap
    pass


# -------------------------------------------------------------------------------
# mapping user keywords to plot style functions
# -------------------------------------------------------------------------------

PLOT_STYLE = {
    "vs time": plot_vs_time,
    "histogram": plot_histo,
    "scatter": plot_scatter,
    "heatmap": plot_heatmap,
}
