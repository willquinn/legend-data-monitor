# -------------------------------------------------------------------------------
# different plot style functions called from the main one depending on parameter
# -------------------------------------------------------------------------------                

# See mapping user plot structure keywords to corresponding functions in the end of this file

from math import ceil
from pandas import Timedelta
from matplotlib.dates import DateFormatter, date2num
from matplotlib.ticker import FixedLocator


def plot_vs_time(data_channel, param, fig, ax, color=None):
    # -------------------------------------------------------------------------
    # plot this data vs time
    # -------------------------------------------------------------------------
    
    # need to plot this way, and not data_position.plot(...) because the datetime column is of type Timestamp
    # plotting this way, to_pydatetime() converts it to type datetime which is needed for DateFormatter
    # changing the type of the column itself with the table does not work  
    data_channel = data_channel.sort_values('datetime')  
    ax.plot(data_channel['datetime'].dt.to_pydatetime(), data_channel[param.name], zorder = 0,
        color=color if param.name == 'event_rate' else 'darkgray')

    # -------------------------------------------------------------------------
    # plot resampled average
    # -------------------------------------------------------------------------
    
    # unless event rate - already resampled and counted in some time window
    if not param.name == 'event_rate':
        # resample in given time window, as start pick the first timestamp in table
        resampled = data_channel.set_index('datetime').resample(param.sampling, origin='start').mean(numeric_only=True)
        # will have datetime as index after resampling -> put back
        resampled = resampled.reset_index()
        # the timestamps in the resampled table will start from the first timestamp, and go with sampling intervals
        # I want to shift them by sampling window, so that the resampled value is plotted for the end of the time window in which it was calculated
        resampled['datetime'] = resampled['datetime'] + Timedelta(param.sampling)

        ax.plot(resampled['datetime'].dt.to_pydatetime(), resampled[param.name], color=color, zorder=1, marker='o', linestyle='-')

    # -------------------------------------------------------------------------
    # beautification
    # -------------------------------------------------------------------------

    # --- time ticks/labels on x-axis
    # index step width for taking every 10th time point
    every_10th_index_step = ceil( len(data_channel) / 10. )
    # get corresponding time points
    # if there are less than 10 points in total in the frame, the step will be 0 -> take all points
    timepoints = data_channel.iloc[::every_10th_index_step]['datetime'] if every_10th_index_step else data_channel['datetime']

    # set ticks and date format
    ax.xaxis.set_major_locator(FixedLocator([ date2num(x) for x in timepoints.dt.to_pydatetime() ]))
    ax.xaxis.set_major_formatter(DateFormatter('%Y\n%m/%d\n%H:%M'))

    # --- set labels
    fig.supxlabel('UTC Time')
    fig.supylabel(f'{param.label} [{param.unit_label}]')


def plot_histo(data_channel, param, fig, ax, color=None):
  
    # --- histo range
    # !! in the future take from par-settings
    # needed for cuspEmax because with geant outliers not possible to view normal histo
    hrange = {'keV': [0, 2500]}
    # take full range if not specified
    x_min = hrange[param.unit][0] if param.unit in hrange else data_channel[param.name].min()
    x_max = hrange[param.unit][1] if param.unit in hrange else data_channel[param.name].max()

    # --- bin width
    bwidth = {'keV': 2.5} # what to do with binning???
    bin_width = bwidth[param.unit] if param.unit in bwidth else None
    no_bins = int( (x_max - x_min) / bin_width) if bin_width else 50

    # -------------------------------------------------------------------------

    data_channel[param.name].plot.hist(bins=no_bins, range=[x_min, x_max], histtype='step', linewidth=1.5, ax = ax, color=color)

    # -------------------------------------------------------------------------

    ax.set_yscale('log')
    fig.supxlabel(f'{param.label} [{param.unit_label}]') 


def plot_scatter(data_channel, param, fig, ax, color=None):
    ax.scatter(data_channel['datetime'].dt.to_pydatetime(), data_channel[param.name], color=color)

    ax.xaxis.set_major_formatter(DateFormatter('%Y\n%m/%d\n%H:%M'))
    fig.supxlabel('UTC Time')


def plot_heatmap(data_channel, param, fig, ax, color=None):
    # here will be a function to plot a SiPM heatmap
    pass

def plot_status(data_channel, param, fig, ax, color=None):
    # here i will transfer Sofia's heatmaps.py function
    pass

# -------------------------------------------------------------------------------                
# mapping user keywords to plot style functions
# -------------------------------------------------------------------------------                

PLOT_STYLE = {
    'vs time': plot_vs_time,
    'histogram': plot_histo,
    'scatter': plot_scatter,
    'heatmap': plot_heatmap,
    'status': plot_status
}