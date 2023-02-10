from . import parameter_data as paramdata

from pandas import pivot_table

import matplotlib.pyplot as plt
from matplotlib.dates import MinuteLocator, DateFormatter
from matplotlib import dates, rcParams, cycler
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import FormatStrFormatter
from seaborn import color_palette

import os

# from __future__ import annotations

# See mapping user plot style keywords to corresponding functions in the end of this file

# ---- main plotting function
def make_subsystem_plots(subsys, plot_settings):         

    # !! this is wrong here - not all plots in the loop may be par_vs_time
    # there could be 2 subsystems in config, e.g. baseline vs time for geds, and some param histo or so
    # in this case, pdf should be not per subsystem, but per parameter
    # in principle, i think one DataMonitor run will have one PDF with everything in it - geds, spms, all the plots
    # so that after it launches automatically, produces one pdf per run, and RunTeam or someone can analyse the run behavior
    # -> TBD
    out_name = os.path.join(plot_settings.output_paths['pdf_files'], 'par_vs_time',
                                    plot_settings.basename + '_' + subsys.type + '.pdf')
    pdf = PdfPages(out_name)        
    
    for param in subsys.parameters:
        # select data from subsystem data for given parameter based on parameter settings
        pardata = paramdata.ParamData(subsys, param, plot_settings)
            
        # decide plot function based on user requested style (see dict below)            
        plot_parameter = PLOT_STYLE[pardata.plot_settings['plot_style']]            
            
        #print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        #print('~~~ P L O T T I N G')
        #print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        plot_parameter(pardata, pdf)
          
    pdf.close()
    #print('All plots saved in: ' + out_name)
            

# -------------------------------------------------------------------------------
# different plot style functions called from the main one depending on parameter
# -------------------------------------------------------------------------------

        
def plot_ch_par_vs_time(pardata, pdf):
    data = pardata.data.sort_values(['location', 'position'])
    
    # separate figure for each string/fiber ("location")
    for location, data_location in data.groupby('location'):
        #print(f'... {pardata.locname} {location}')
        
        # ---------------------------------------------
        #  global channel mean
        # det name, channel in each position (position will be index after groupby)
        channel_mean = data_location.groupby('position').first()[['name', 'channel']]
        # get mean
        channel_mean['mean'] = data_location.groupby('position').mean(numeric_only=True)[pardata.param]

        # ---------------------------------------------
        # calculate variation if asked by user

        # set y label now already, add % if variation
        ylabel = pardata.param_info.label + f" [{pardata.param_info.units}]"
        if pardata.plot_settings['some_name'] == "variation":
            #print('... calculating variation from the mean')
            # set index to position to correspond to channel_mean
            data_location = data_location.set_index('position')
            # subtract mean from value for each position (i.e. channel)
            data_location[pardata.param] = (-data_location[pardata.param] / channel_mean['mean'] + 1) * 100 # %
            data_location = data_location.reset_index()   
            ylabel += ' - %'   
    
        # ---------------------------------------------
        # plot

        numch = len(data_location['channel'].unique())
        fig, axes = plt.subplots(numch, figsize=(10,numch*3), sharex=True)#, sharey=True)
        # in case of pulser, axes will be not a list but one axis -> convert to list
        if numch == 1:
            axes = [axes]

        #print('... plotting')
        ax_idx = 0
        # groupby takes 4 seconds while pd.pivot_table - 20 -> changed to for loop with groupby
        for position, data_position in data_location.groupby('position'):
            # need to plot this way, and not data_position.plot(...) because the datetime column is of type Timestamp
            # plotting this way, to_pydatetime() converts it to type datetime which is needed for DateFormatter
            # changing the type of the column itself with the table does not work
            axes[ax_idx].plot(data_position['datetime'].dt.to_pydatetime(), data_position[pardata.param], color='darkgray')
            ax_idx += 1


        # ---------------------------------------------
        # plot resampled average, unless it's event rate - already resampled and counted for the same time window

        if pardata.param != 'event_rate':
            #print('...... resampling for every ' + pardata.sampling)
            # after groupby->resample will have multi index in (position, datetime)
            resampled = data_location.set_index('datetime').groupby('position').resample(pardata.sampling).mean(numeric_only=True)
            # drop position, will be re-inserted with reset_index
            resampled = resampled.drop('position', axis=1)
            resampled = resampled.reset_index()

            #print('...... plotting resampled')
            # color settings using a pre-defined palette
            rcParams['axes.prop_cycle'] = cycler(color=color_palette("hls", len(resampled.position.unique()))) 
            # here pivot is quite quick even with 3minute sampling
            pivot_table(resampled, index='datetime', columns='position', values=pardata.param).plot(
                subplots=True, legend=False, ax = axes) 
            
        # !! with very short ranges, x-axis with datetime might behave weird
        # might not need a solution for this because usually the range is > 2 keys

        # ---------------------------------------------
        # beautification

        #print('... making the plot pretty for you')

        # summary annotations
        channel_mean = channel_mean.reset_index()
        channel_mean['text'] = channel_mean[['name', 'channel', 'position', 'mean']].apply(lambda x:
            '{}\nchannel {}\nposition {}\nmean = {}'.format(x[0], x[1], x[2], round(x[3],2)) + f' {pardata.param_info.units}', axis=1)

        # time ticks/labels on x-axis
        # !! does not work for very small or non uniform data
        # index step width for taking every 10th time point
        every_10th_index_step = int( len(data_location) / 10. )
        # get corresponding timedelta in minutes to be safe for any plotting range
        time_step = int( (pardata.data.iloc[every_10th_index_step]['datetime'] - pardata.data.iloc[0]['datetime']).total_seconds() / 60. )
        # locator - locates the ticks for given interval
        locator = MinuteLocator(interval = time_step)
        # formatter - formats the x label
        formatter = DateFormatter('%Y\n%m/%d\n%H:%M') 

            
        # now add this stuff to axes
        for idx in range(len(axes)):
            # text
            axes[idx].text(1.01, 0.5, channel_mean.iloc[idx]['text'], transform=axes[idx].transAxes)
            # grid
            axes[idx].grid('major', linestyle='--')
            # locate ticks
            axes[idx].xaxis.set_major_locator(locator)

        # set date format
        axes[-1].xaxis.set_major_formatter(formatter)

        # ---- fix plot info
        axes[0].set_title(f"{pardata.subsys} - {pardata.locname} {location}")
        axes[-1].set_xlabel('') # remove 'datatime' authomatic entry
        fig.supxlabel('UTC Time') 
        fig.supylabel(ylabel)


        fig.tight_layout()
        plt.savefig(pdf, format='pdf')#, bbox_inches='tight')     
        # pdf.savefig()      
                

def plot_histo(pardata, pdf):
    # bins and range definition
    data = pardata.data[pardata.param]
    x_min = data.min()
    x_max = data.max()
    no_bins = int(x_max-x_min)

    #print('Plotting...')
    data.plot.hist(bins=no_bins, range=[x_min, x_max], histtype='step', linewidth=1.5)

    xlabel = pardata.param_info.label + f" [{pardata.param_info.units}]"
    plt.xlabel(xlabel) 
    plt.ylabel('Counts')
    plt.yscale('log')
    pdf.savefig(bbox_inches='tight')


def plot_all_par_vs_time(pardata, pdf):
    labels = pardata.data.groupby('channel').first()[['name', 'location', 'position']]
    labels['channel'] = labels.index
    labels['label'] = labels[['location', 'position', 'channel', 'name']].apply( lambda x: f's{x[0]}-p{x[1]}-ch{str(x[2]).zfill(3)}-{x[3]}', axis=1 )

    pardata.data = pardata.data.set_index('channel')
    pardata.data['label'] = labels['label']

    fig, ax = plt.subplots()

    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    for label, group in pardata.data.groupby('label'):
        plt.scatter(group['datetime'].dt.to_pydatetime(), group[pardata.param],
            label=label, color = colors[group['location'].iloc[0]])


    ax.set_xlabel('Time (UTC)')
    ax.xaxis.set_major_formatter(DateFormatter('%Y\n%m/%d\n%H:%M'))
    ax.set_ylabel(f'{pardata.param} [{pardata.param_info.units}]')
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))

    plt.legend()

    fig.tight_layout()
    pdf.savefig()


# mapping user keywords to plot style functions
PLOT_STYLE = {
    'per channel': plot_ch_par_vs_time,
    'all channels': plot_all_par_vs_time,
    'histogram': plot_histo
}  