import numpy as np
import pandas as pd

from . import subsystem


# !! should inherit from dataframe!
class ParamData:
    # should maybe inherit from pd.DataFrame directly?
    def __init__(self, subsys, param, plot_settings):

        #print('============================================')
        #print('=== Setting up ' + param)
        #print('============================================')

        # !! can be gotten from non (datetime, channel, pulser flag columns)
        self.param = param

        # !! should not need? -> need for plotting title -> move locname there as well?
        self.subsys = subsys.type

        # for plotting, whether 'location' is string or fiber for given subsystem
        self.locname = {"geds": "string", "spms": "fiber", "pulser": "pulser"}[
            subsys.type
        ]

        # plot settings for this param
        # what events to keep (phy/puls/all), plot style, variation or absolute
        # note: results in a UserWarning about columns as attributes
        self.plot_settings = plot_settings.param_settings[param]
        # color, range, etc. (not user defined)
        self.param_info = plot_settings.param_info[param]
        # pass on avg sampling from plot settings
        self.sampling = plot_settings.sampling

        # -------------------------------
        # subselect data to load for only this parameter

        # always get channel and datetime
        params_to_get = ["channel", "datetime"]
        # pulser flag is present only if subsystem.flag_pulser_events() was called
        if "flag_pulser" in subsys.data:
            params_to_get.append("flag_pulser")

        if self.param in subsystem.SPECIAL_PARAMETERS:
            # if special parameter, get columns needed to calculate it
            # ignore if none are needed
            params_to_get += (
                subsystem.SPECIAL_PARAMETERS[param]
                if subsystem.SPECIAL_PARAMETERS[param]
                else []
            )
        else:
            # otherwise just load it
            params_to_get.append(param)

        # avoid repetition
        params_to_get = list(np.unique(params_to_get))
        self.data = subsys.data[params_to_get].copy()

        # -------------------------------

        # selec phy/puls/all events
        self.select_events()

        # -------------------------------
        # calculate special parameters

        if param == "wf_max_rel":
            # calculate wf max relative to baseline
            # !! why "copy of a slice" warning? it's the same dataframe...
            self.data["wf_max_rel"] = self.data["wf_max"] - self.data["baseline"]
            # drop the original columns not to drag them around
            self.data = self.data.drop(["wf_max", "baseline"], axis=1)
        elif param == "event_rate":
            # count number of events in given time windows
            # (count() returns count for each column, just want one column 'event_rate' -> pick 'channel' since it's never NaN so correct count, rename)
            self.data = (
                self.data.set_index("datetime")
                .groupby("channel")
                .resample(self.sampling)
                .count()["channel"]
                .to_frame(name="event_rate")
                .reset_index()
            )
            # divide event count by time window in seconds to get Hz
            dt_seconds = get_seconds(self.sampling)
            self.data["event_rate"] = self.data["event_rate"] / dt_seconds

        # ----------------

        # map to det name and string
        self.map_channels(subsys)

        #print(self.data)

    def select_events(self):
        # do we want to keep all, phy or pulser events?
        if self.plot_settings['events'] == 'pulser':
            #print('... keeping only pulser events')
            self.data = self.data[ self.data['flag_pulser'] ]
        elif self.plot_settings['events'] == 'phy':
            #print('... keeping only physical (non-pulser) events')
            self.data = self.data[ ~self.data['flag_pulser'] ]
        elif self.plot_settings['events'] == 'K_lines':
            #print('... selecting K lines in physical (non-pulser) events')
            self.data = self.data[ ~self.data['flag_pulser'] ]
            energy = subsystem.SPECIAL_PARAMETERS['K_lines'][0]
            self.data = self.data[ (self.data[energy] > 1430) & (self.data[energy] < 1575)]
        else:
            #print('... keeping all (pulser + non-pulser) events')



    def map_channels(self, subsys):
        #print(f'... mapping channel name, location, and position')
        ch_map = subsys.ch_map.set_index('channel')
        self.data = self.data.set_index('channel')
        self.data = pd.concat([self.data, ch_map.loc[self.data.index]], axis=1)
        self.data = self.data.reset_index()


# ------------ helper functions


def get_seconds(sampling):
    """
    Convert sampling format used for DataFrame.resample() to int representing seconds.

    >>> get_seconds('30T')
    1800
    """
    # correspondence of symbol to seconds, T = minutes
    sampling_to_seconds = {"S": 1, "T": 60, "D": 24 * 60 * 60}

    for key in sampling_to_seconds:
        if key in sampling:
            return int(sampling.rstrip(key)) * sampling_to_seconds[key]
