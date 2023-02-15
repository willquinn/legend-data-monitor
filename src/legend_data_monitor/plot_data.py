import pandas as pd
import numpy as np

# needed to know which parameters are not in DataLoader
# but need to be calculated, such as event rate
# ! maybe belongs as json in settings
# ! maybe needs to be loaded in some sort of utils.py
from .subsystem import SPECIAL_PARAMETERS

import json
# ? not nice that need to load in multiple files? e.g. config.py and here
from legendmeta.jsondb import AttrsDict

# needed to open files in settings/
import importlib.resources
# load dictionary with plot info (= units, thresholds, label, ...)
pkg = importlib.resources.files("legend_data_monitor")
with open(pkg / "settings" / "par-settings.json") as f:
    PLOT_INFO = AttrsDict(json.load(f))

## -------------------------------------------------------------------------

class PlotData():
    def __init__(self, subsys, plot):

        print('============================================')
        print('=== Setting up data for plot ' + plot)
        print('============================================')

        # name of this plot - will be a suptitle of the figure
        self.plot_title = plot
        # which subsystem this plot belongs to
        self.subsys = subsys.type
        # for plotting, whether 'location' is string or fiber for given subsystem
        self.locname = {'geds': 'string', 'spms': 'fiber', 'pulser': 'aux'}[subsys.type]        

        # -------------------------------------------------------------------------      
        # settings and info
        
        # --- plot and data settings for this plot
        # - what parameter we are plotting
        # - plotting variation in % or absolute value
        # - what events to keep (phy/puls/all)
        # - plot structure and style
        # - sampling in cases it's needed
        self.plot_settings = subsys.plots[plot]   

        # --- parameter of interest in this plot and info related to it
        # - label, unit; later also limits if needed, facecolor, any other settings
        # - name
        # - sampling - might be needed for plotting data resampled in a time window, so need to pass on this info to use later
        param_name = self.plot_settings.parameter
        self.param = PLOT_INFO[param_name]
        self.param['name'] = param_name
        # unit label can be % if variation
        self.param['unit_label'] = '%' if self.plot_settings['some_name'] == 'variation' else self.param['unit']
                  
        self.param['sampling'] = self.plot_settings['sampling'] if 'sampling' in self.plot_settings else None

        # make attrs dict for convenience
        self.param = AttrsDict(self.param)  

        # -------------------------------------------------------------------------      
        # subselect data to load for only this parameter

        # always get basic parameters
        params_to_get = ['datetime', 'channel', 'name', 'location', 'position']
        # pulser flag is present only if subsystem.flag_pulser_events() was called
        # needed to subselect phy/pulser events
        if 'flag_pulser' in subsys.data:
            params_to_get.append('flag_pulser')

        # if special parameter, get columns needed to calculate it
        if self.param.name in SPECIAL_PARAMETERS:
            # ignore if none are needed
            params_to_get += (SPECIAL_PARAMETERS[self.param.name] if SPECIAL_PARAMETERS[self.param.name] else [])
        else:
            # otherwise just load it
            params_to_get.append(self.param.name)
        
        # avoid repetition
        params_to_get = list(np.unique(params_to_get))
        
        self.data = subsys.data[params_to_get].copy()

        # -------------------------------------------------------------------------      

        # selec phy/puls/all events
        self.select_events()

        # calculate if special parameter
        self.special_parameter()          

        # -------------------------------------------------------------------------              
        # calculate channel mean

        print('... getting channel mean')
        # series with index channel containing mean values (no column name)
        channel_mean = self.data.groupby('channel').mean(numeric_only=True)[self.param.name]
        # add it as column for convenience - repeating redundant information, but convenient
        self.data = self.data.set_index('channel')
        # print(channel_mean.reindex(self.data.index))
        self.data['mean'] = channel_mean.reindex(self.data.index)
        # put channel back in
        self.data = self.data.reset_index()

        # -------------------------------------------------------------------------      
        # calculate variation if needed - only works after channel mean
        self.calculate_variation()           

        # -------------------------------------------------------------------------      

        self.data = self.data.sort_values(['channel', 'datetime'])       

        print(self.data)

        
    def select_events(self):
        # do we want to keep all, phy or pulser events?
        if self.plot_settings['events'] == 'pulser':
            print('... keeping only pulser events')
            self.data = self.data[ self.data['flag_pulser'] ]
        elif self.plot_settings['events'] == 'phy':
            print('... keeping only physical (non-pulser) events')
            self.data = self.data[ ~self.data['flag_pulser'] ]
        elif self.plot_settings['events'] == 'K_lines':
            print('... selecting K lines in physical (non-pulser) events')
            self.data = self.data[ ~self.data['flag_pulser'] ]
            energy = SPECIAL_PARAMETERS['K_lines'][0]
            self.data = self.data[ (self.data[energy] > 1430) & (self.data[energy] < 1575)] 
        else:
            print('... keeping all (pulser + non-pulser) events')
              
        
    def special_parameter(self):
        if self.param.name == 'wf_max_rel':
            # calculate wf max relative to baseline
            self.data['wf_max_rel'] = self.data['wf_max'] - self.data['baseline']
            # drop the original columns not to drag them around
            self.data = self.data.drop(['wf_max', 'baseline'], axis=1)
        elif self.param.name == 'event_rate':
            # ! sorry need to jump through a lot of hoops here ! bare with me....

            # --- count number of events in given time windows
            # - count() returns count of rows for each column - redundant, same value in each (unless we have NaN)
            # just want one column 'event_rate' -> pick 'channel' since it's never NaN, so correct count; rename to event rate
            # - this is now a resampled dataframe with column event rate, and multiindex channel, datetime -> put them back as columns with reset index
            event_rate = self.data.set_index('datetime').groupby('channel').resample(self.param.sampling, origin='start').count()['channel'].to_frame(name = 'event_rate').reset_index()
            
            # divide event count in each time window by sampling window in seconds to get Hz
            dt_seconds = get_seconds(self.param.sampling)
            event_rate['event_rate'] = event_rate['event_rate'] / dt_seconds    

            # --- get rid of last value
            # as the data range does not equally divide by the sampling window, the count in the last "window" will be smaller
            # as it corresponds to, in reality, smaller window
            # since we divided by the window, the rate then will appear as smaller
            # it's too complicated to fix that, so I will just get rid of the last row
            event_rate = event_rate.iloc[:-1]
            
            # --- shift timestamp
            # the resulting table will start with the first timestamp of the original table
            # I want to shift the time values by the sampling window, so that the event rate value corresponds to the end of the sampling window
            event_rate['datetime'] = event_rate['datetime'] + pd.Timedelta(self.param.sampling)

            # --- now have to jump through hoops to put back in location position and name
            # - group original table by channel and pick first occurence to get the channel map (ignore other columns)
            # - reindex to match event rate table index
            # - put the columns in with concat
            event_rate = event_rate.set_index('channel')
            self.data = pd.concat([ event_rate, self.data.groupby('channel').first().reindex(event_rate.index)[['name', 'location', 'position']] ], axis=1)
            # put the channel back as column
            self.data = self.data.reset_index()


    def calculate_variation(self):
        if self.plot_settings['some_name'] == "variation":
            print('... calculating % variation from the mean')
            # subtract mean from value for each channel
            self.data[self.param.name] = ( self.data[self.param.name] / self.data['mean'] - 1) * 100 # %


# -------------------------------------------------------------------------      
# helper function
# -------------------------------------------------------------------------

def get_seconds(sampling):
    '''
    Convert sampling format used for DataFrame.resample() to int representing seconds.
    Needed for event rate calculation.

    >>> get_seconds('30T')
    1800
    '''
    # correspondence of symbol to seconds, T = minutes
    sampling_to_seconds = {'S': 1, 'T': 60, 'H': 60*60, 'D': 24*60*60}

    for key in sampling_to_seconds:
        if key in sampling:
            return int(sampling.rstrip(key)) * sampling_to_seconds[key]

