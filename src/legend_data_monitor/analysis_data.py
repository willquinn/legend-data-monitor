import pandas as pd
import numpy as np

# needed to know which parameters are not in DataLoader
# but need to be calculated, such as event rate
# ! maybe belongs as json in settings
# ! maybe needs to be loaded in some sort of utils.py
from .subsystem import SPECIAL_PARAMETERS

## -------------------------------------------------------------------------

class AnalysisData():
    '''
    sub_data [DataFrame]: subsystem data
    [parameters] [str|list]: parameter(s) of interest
    evt_type [str]: event type (pulser/phy/all/Klines)
    variation [bool]: keep absolute value of parameter (False) or calculate % variation from mean (True)
    window [str]: time window in which to calculate event rate, in case that's the parameter of interest (default None)
    '''

    def __init__(self, sub_data, parameters, event_type, variation=False, time_window=None):

        print('============================================')
        print('=== Setting up Analysis Data')
        print('============================================')

        # -------------------------------------------------------------------------      
        # validity checks
        # -------------------------------------------------------------------------      
        
        # convert single parameter input to list for convenience
        if isinstance(parameters, str):
            parameters = [parameters]

        # cannot do event rate and another parameter at the same time
        # since event rate is calculated in windows
        if 'event_rate' in parameters and len(parameters) > 1:
            print('Cannot get event rate and another parameter at the same time!')
            print('Event rate has to be calculated based on time windows, so the other parameter has to be thrown away.')
            print('Contact Mariia if you want, for example, to keep that parameter, but look at mean in the windows of event rate.')
            return

        # time window must be provided for event rate
        if parameters[0] == 'event_rate' and not time_window:
            print('Provide time window in which to take the event rate!')
            print('Format: NA, where N is integer, and A is M for months, D for days, T for minutes, and S for seconds')
            return

        self.parameters = parameters
        self.evt_type = event_type
        self.time_window = time_window
        self.variation = variation

        # -------------------------------------------------------------------------      
        # subselect data
        # -------------------------------------------------------------------------      

        # always get basic parameters
        params_to_get = ['datetime', 'channel', 'name', 'location', 'position']
        # pulser flag is present only if subsystem.flag_pulser_events() was called
        # needed to subselect phy/pulser events
        if 'flag_pulser' in sub_data:
            params_to_get.append('flag_pulser')

        # if special parameter, get columns needed to calculate it
        for param in self.parameters:
            if param in SPECIAL_PARAMETERS:
                # ignore if none are needed
                params_to_get += (SPECIAL_PARAMETERS[param] if SPECIAL_PARAMETERS[param] else [])
            else:
                # otherwise just load it
                params_to_get.append(param)
        
        # avoid repetition
        params_to_get = list(np.unique(params_to_get))
        
        self.data = sub_data[params_to_get].copy()

        # -------------------------------------------------------------------------      

        # selec phy/puls/all events
        self.select_events()

        # calculate if special parameter
        self.special_parameter()          

        # calculate channel mean
        self.channel_mean()

        # calculate variation if needed - only works after channel mean
        self.calculate_variation()           

        # -------------------------------------------------------------------------      

        self.data = self.data.sort_values(['channel', 'datetime'])       

        print(self.data)

        
    def select_events(self):
        # do we want to keep all, phy or pulser events?
        if self.evt_type == 'pulser':
            print('... keeping only pulser events')
            self.data = self.data[ self.data['flag_pulser'] ]
        elif self.evt_type == 'phy':
            print('... keeping only physical (non-pulser) events')
            self.data = self.data[ ~self.data['flag_pulser'] ]
        elif self.evt_type == 'K_lines':
            print('... selecting K lines in physical (non-pulser) events')
            self.data = self.data[ ~self.data['flag_pulser'] ]
            energy = SPECIAL_PARAMETERS['K_lines'][0]
            self.data = self.data[ (self.data[energy] > 1430) & (self.data[energy] < 1575)] 
        else:
            print('... keeping all (pulser + non-pulser) events')
              
        
    def special_parameter(self):
        for param in self.parameters:
            if param== 'wf_max_rel':
                # calculate wf max relative to baseline
                self.data['wf_max_rel'] = self.data['wf_max'] - self.data['baseline']
            elif param == 'event_rate':
                # ! sorry need to jump through a lot of hoops here ! bare with me....

                # --- count number of events in given time windows
                # - count() returns count of rows for each column - redundant, same value in each (unless we have NaN)
                # just want one column 'event_rate' -> pick 'channel' since it's never NaN, so correct count; rename to event rate
                # - this is now a resampled dataframe with column event rate, and multiindex channel, datetime -> put them back as columns with reset index
                event_rate = self.data.set_index('datetime').groupby('channel').resample(self.time_window, origin='start').count()['channel'].to_frame(name = 'event_rate').reset_index()
                
                # divide event count in each time window by sampling window in seconds to get Hz
                dt_seconds = get_seconds(self.time_window)
                event_rate['event_rate'] = event_rate['event_rate'] / dt_seconds    

                # --- get rid of last value
                # as the data range does not equally divide by the time window, the count in the last "window" will be smaller
                # as it corresponds to, in reality, smaller window
                # since we divided by the window, the rate then will appear as smaller
                # it's too complicated to fix that, so I will just get rid of the last row
                event_rate = event_rate.iloc[:-1]
                
                # --- shift timestamp
                # the resulting table will start with the first timestamp of the original table
                # I want to shift the time values by the half the time window, so that the event rate value corresponds to the middle of the time window
                event_rate['datetime'] = event_rate['datetime'] + pd.Timedelta(self.time_window) / 2

                # --- now have to jump through hoops to put back in location position and name
                # - group original table by channel and pick first occurence to get the channel map (ignore other columns)
                # - reindex to match event rate table index
                # - put the columns in with concat
                event_rate = event_rate.set_index('channel')
                self.data = pd.concat([ event_rate, self.data.groupby('channel').first().reindex(event_rate.index)[['name', 'location', 'position']] ], axis=1)
                # put the channel back as column
                self.data = self.data.reset_index()


    def channel_mean(self):
        print('... getting channel mean')
        # series with index channel, columns of parameters containing mean of each channel
        channel_mean = self.data.groupby('channel').mean(numeric_only=True)[self.parameters]
        # rename columns to be param_mean
        channel_mean = channel_mean.rename(columns={param: param+'_mean' for param in self.parameters})
        # add it as column for convenience - repeating redundant information, but convenient
        self.data = self.data.set_index('channel')
        # print(channel_mean.reindex(self.data.index))
        # self.data['mean'] = channel_mean.reindex(self.data.index)
        self.data = pd.concat([self.data, channel_mean.reindex(self.data.index)], axis=1)
        # put channel back in
        self.data = self.data.reset_index()        


    def calculate_variation(self):
        if self.variation:
            print('... calculating % variation from the mean')
            for param in self.parameters:
                # subtract mean from value for each channel
                self.data[param] = ( self.data[param] / self.data[param+'_mean'] - 1) * 100 # %


# -------------------------------------------------------------------------      
# helper function
# -------------------------------------------------------------------------

def get_seconds(time_window):
    '''
    Convert sampling format used for DataFrame.resample() to int representing seconds.
    Needed for event rate calculation.

    >>> get_seconds('30T')
    1800
    '''
    # correspondence of symbol to seconds, T = minutes
    str_to_seconds = {'S': 1, 'T': 60, 'H': 60*60, 'D': 24*60*60}
    # unit of this time window
    time_unit = time_window[-1]

    return int(time_window.rstrip(time_unit)) * str_to_seconds[time_unit]

