from . import plot_data
from .plot_styles import *

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from seaborn import color_palette

# -------------------------------------------------------------------------

# global variable to be filled later with colors based on number of channels
COLORS = []

# -------------------------------------------------------------------------
# main plotting function(s)
# -------------------------------------------------------------------------

# plotting function that makes subsystem plots
# feel free to write your own one using Dataset, Subsystem and ParamData objects
# for example, this structure won't work to plot one parameter VS the other

def make_subsystem_plots(subsys, pdf_path):         

    pdf = PdfPages(pdf_path)        
    
    # for param in subsys.parameters:
    for plot in subsys.plots:
        # --- set up plot data
        # - set up plot settings and info
        # - subselect data from this plot from subsystem data for given parameter based on given selection etc.
        plotdata = plot_data.PlotData(subsys, plot)
            
        # choose plot function based on user requested structure e.g. per channel or all ch together            
        plot_structure = PLOT_STRUCTURE[plotdata.plot_settings['plot_structure']]            

        # --- color settings using a pre-defined palette
        # num colors needed = max number of channels per string
        # - find number of unique positions in each string
        # - get maximum occuring
        max_ch_per_string = plotdata.data.groupby('location')['position'].nunique().max()
        global COLORS
        COLORS = color_palette("hls", max_ch_per_string).as_hex()
            
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        print('~~~ P L O T T I N G')
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        print('Plot structure: ' + plotdata.plot_settings['plot_structure'])
        plot_structure(plotdata, pdf)
          
    pdf.close()
    print('- - - - - - - - - - - - - - - - - - - - - - -')
    print('All plots saved in: ' + pdf_path)
    print('- - - - - - - - - - - - - - - - - - - - - - -')
            

# -------------------------------------------------------------------------------
# different plot structure functions, how the figure should look like
# -------------------------------------------------------------------------------

# See mapping user plot structure keywords to corresponding functions in the end of this file
        
def plot_per_ch(plotdata, pdf):
    # --- choose plot function based on user requested style e.g. vs time or histogram
    plot_style =  PLOT_STYLE[plotdata.plot_settings['plot_style']]
    print('Plot style: ' + plotdata.plot_settings['plot_style'])

    plotdata.data = plotdata.data.sort_values(['location', 'position'])   

    # -------------------------------------------------------------------------------

    # separate figure for each string/fiber ("location")
    for location, data_location in plotdata.data.groupby('location'):
        print(f'... {plotdata.locname} {location}')

        # -------------------------------------------------------------------------------
        # create plot structure: 1 column, N rows with subplot for each channel
        # -------------------------------------------------------------------------------

        # number of channels in this string/fiber
        numch = len(data_location['channel'].unique())
        # create corresponding number of subplots for each channel, set constrained layout to accommodate figure suptitle
        fig, axes = plt.subplots(nrows=numch, ncols=1, figsize=(10,numch*3), sharex = True, constrained_layout=True)#, sharey=True)
        # in case of pulser, axes will be not a list but one axis -> convert to list
        if numch == 1:
            axes = [axes]

        # -------------------------------------------------------------------------------
        # plot
        # -------------------------------------------------------------------------------

        ax_idx = 0
        # plot one channel on each axis, ordered by position
        for position, data_channel in data_location.groupby('position'):
            print(f'...... position {position}')

            # plot selected style on this axis
            plot_style(data_channel, plotdata.param, fig, axes[ax_idx], color=COLORS[ax_idx])

            # --- add summary to axis
            # name, position and mean are unique for each channel - take first value
            t = data_channel.iloc[0][['channel', 'position', 'name', 'mean']]
            text =  t['name']  +  '\n'  +\
                    f"channel {t['channel']}\n" +\
                    f"position {t['position']}\n"  +\
                    f"mean {round(t['mean'],3)} [{plotdata.param.unit}]"
            axes[ax_idx].text(1.01, 0.5, text, transform=axes[ax_idx].transAxes)  

            # add grid
            axes[ax_idx].grid('major', linestyle='--')
            # remove automatic y label since there will be a shared one
            axes[ax_idx].set_ylabel('')

            ax_idx += 1

        # -------------------------------------------------------------------------------

        fig.suptitle(f'{plotdata.subsys} - {plotdata.plot_title}')
        axes[0].set_title(f"{plotdata.locname} {location}")

        plt.savefig(pdf, format='pdf')
        # figures are retained until explicitly closed; close to not consume too much memory
        plt.close()


def plot_per_string(plotdata, pdf):
    # --- choose plot function based on user requested style e.g. vs time or histogram
    plot_style =  PLOT_STYLE[plotdata.plot_settings['plot_style']]
    print('Plot style: ' + plotdata.plot_settings['plot_style'])

    # --- create plot structure
    # number of strings/fibers
    no_location = len(plotdata.data['location'].unique())
    # set constrained layout to accommodate figure suptitle
    fig, axes = plt.subplots(no_location, figsize=(10,no_location*3), sharex=True, sharey=True, constrained_layout=True)

    # -------------------------------------------------------------------------------
    # create label of format hardcoded for geds sXX-pX-chXXX-name
    # -------------------------------------------------------------------------------

    labels = plotdata.data.groupby('channel').first()[['name', 'position']]
    labels['channel'] = labels.index
    labels['label'] = labels[['position', 'channel', 'name']].apply( lambda x: f'p{x[0]}-ch{str(x[1]).zfill(3)}-{x[2]}', axis=1 )
    # put it in the table
    plotdata.data = plotdata.data.set_index('channel')
    plotdata.data['label'] = labels['label']
    plotdata.data = plotdata.data.sort_values('label')    

    # -------------------------------------------------------------------------------
    # plot
    # -------------------------------------------------------------------------------

    plotdata.data = plotdata.data.sort_values(['location', 'label'])
    # new subplot for each string
    ax_idx = 0
    for location, data_location in plotdata.data.groupby('location'):
        print(f'... {plotdata.locname} {location}')

        # new color for each channel
        col_idx = 0
        labels = []
        for label, data_channel in data_location.groupby('label'):
            plot_style(data_channel, plotdata.param, fig, axes[ax_idx], COLORS[col_idx])
            labels.append(label)
            col_idx += 1

        axes[ax_idx].set_title(f"{plotdata.locname} {location}")
        axes[ax_idx].set_ylabel('')
        axes[ax_idx].legend(labels = labels, loc='center left', bbox_to_anchor=(1, 0.5))
        ax_idx += 1

    # -------------------------------------------------------------------------------

    fig.suptitle(f'{plotdata.subsys} - {plotdata.plot_title}')
    fig.supylabel(f'{plotdata.param.label} [{plotdata.param.unit_label}]')
    plt.savefig(pdf, format='pdf')
    # figures are retained until explicitly closed; close to not consume too much memory
    plt.close()
        

def plot_top_bottom(plotdata, pdf):
    # here will be the SiPM function plotting one figure for top and one for bottom SiPMs, arranged in grid
    pass

# -------------------------------------------------------------------------------
# mapping user keywords to plot style functions
# -------------------------------------------------------------------------------

PLOT_STRUCTURE = {
    'per channel': plot_per_ch,
    'per string': plot_per_string,
    'top bottom': plot_top_bottom
}  
