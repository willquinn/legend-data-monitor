import pandas as pd
import numpy as np
from datetime import datetime

from pygama.flow import DataLoader


# ------------
# specify which lh5 parameters are neede to be loaded from lh5 to calculate them
SPECIAL_PARAMETERS = {
    "K_lines": 'cuspEmax_ctc_cal',
    'wf_max_rel': ['wf_max', 'baseline'],
    'event_rate': None  # for event rate, don't need to load any parameter, just count events
}

# convert all to lists for convenience
for param in SPECIAL_PARAMETERS:
    if isinstance(SPECIAL_PARAMETERS[param], str):
        SPECIAL_PARAMETERS[param] = [ SPECIAL_PARAMETERS[param] ]

# ------------

class Subsystem():
    '''
    Object containing information for a given subsystem
    such as chanel map, removed channels etc.
    '''
    def __init__(self, config, sub_type):
        '''
        conf: config.Config object with user providedsettings
        sub_type [str]: geds | spms | pulser
        '''
        print('\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/')
        print('\/\ Setting up ' + sub_type)
        print('\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/')
        
        self.type = sub_type

        # --- list of plots to make for this subsystem
        # if subtype is not in config, means probably it's pulser being set up for flagging not for plotting
        self.plots = config.subsystems[sub_type]['plots'] if sub_type in config.subsystems else []
        # total parameters of interest for all plots to load from DataLoader (can have repetitions)
        self.parameters = []
        for plot in self.plots:
            self.parameters.append(self.plots[plot]['parameter'])

        # -------------------------------------------------------------------------
        # get channel map for this subsystem
        # -------------------------------------------------------------------------

        self.ch_map = self.get_channel_map(config) # pd.DataFrame

        # add column status to channel map stating On/Off
        self.get_channel_status(config)

        # -------------------------------------------------------------------------
        # K lines
        # -------------------------------------------------------------------------
 
        # a bit cumbersome, but we need to know if K_lines was requested to select specified energy parameter
        self.k_lines = False
        for plot in self.plots:
            # if K lines is asked, set to true
            self.k_lines = self.k_lines or (self.plots[plot]['events'] == 'K_lines')

        # -------------------------------------------------------------------------
        # quality cut*
        # -------------------------------------------------------------------------

        # !! per parameter or per subsystem?
        self.qc = config.subsystems[sub_type]['quality_cut'] if sub_type in config.subsystems else False

        # -------------------------------------------------------------------------
        # have something before get_data() is called just in case
        self.data = pd.DataFrame()


    def get_data(self, dataset):
        '''
        plt_set [dict]: plot settings for this subsystem
            (params to plot, QC bool, ...)
        '''
        
        print('... getting data')
        
        # -------------------------------------------------------------------------
        # Data Loader
        # -------------------------------------------------------------------------
        
        # --- construct list of parameters for the data loader
        # depending on special parameters, k lines etc.
        params = self.params_for_dataloader(dataset)

        # --- set up DataLoader
        dlconfig, dbconfig = self.construct_dataloader_configs(dataset, params)
        print('...... calling data loader')        
        dl = DataLoader(dlconfig, dbconfig)
        # if querying by run, need different query word
        time_word = 'run' if dataset.time_range['start'][0] == 'r' else 'timestamp'
        query = f"({time_word} >= '{dataset.time_range['start']}') and ({time_word} <= '{dataset.time_range['end']}')"
        # cal or phy data or both
        query += ' and (' + ' or '.join("(type == '" + x + "')" for x in dataset.type) + ')'

        # !!!! QUICKFIX FOR R010
        query += " and (timestamp != '20230125T222013Z')"
        query += " and (timestamp != '20230126T015308Z')"
        
        print(query)

        # --- query data loader
        dl.set_files(query)
        dl.set_output(fmt="pd.DataFrame", columns=params)           
        now = datetime.now()
        self.data = dl.load() 
        print(f'Total time to load data: {(datetime.now() - now)}')

        # -------------------------------------------------------------------------
        # apply QC*
        # -------------------------------------------------------------------------
        # !! right now set up to be per subsystem, not per parameter

        if self.qc:
            print('...... applying quality cut')
            self.data = self.data[ self.data[dataset.qc_name] ]        

        # -------------------------------------------------------------------------
        # polish things up
        # -------------------------------------------------------------------------

        tier = 'hit' if 'hit' in dbconfig['columns'] else 'dsp'
        # remove columns we don't need
        self.data = self.data.drop([f"{tier}_idx", 'file'], axis=1)
        # rename channel to channel
        self.data = self.data.rename(columns={f'{tier}_table': 'channel'})    

        # -------------------------------------------------------------------------
        # create datetime column based on initial key and timestamp
        # -------------------------------------------------------------------------

        # convert UTC timestamp to datetime (unix epoch time)
        self.data['datetime'] = pd.to_datetime(self.data['timestamp'], origin='unix', utc=True, unit='s')
        # drop timestamp
        self.data = self.data.drop('timestamp', axis=1)  
                    
        # -------------------------------------------------------------------------
        # add detector name, location and position from map
        # -------------------------------------------------------------------------

        print('... mapping to name and string/fiber position')
        self.data = self.data.set_index('channel')
        ch_map_reindexed = self.ch_map.set_index('channel').reindex(self.data.index)
        self.data = pd.concat([ self.data, ch_map_reindexed[['name', 'location', 'position']] ], axis=1)        
        self.data = self.data.reset_index()     
        # stupid dataframe, why float
        for col in ['location', 'position']:
            self.data[col] = self.data[col].astype(int)

        # -------------------------------------------------------------------------
        # if this subsystem is pulser, flag pulser timestamps
        # -------------------------------------------------------------------------      

        if(self.type == 'pulser'):
            self.flag_pulser_events()

        print(self.data)
        
    
    def flag_pulser_events(self, pulser=None):
        print('... flagging pulser events')

        # --- if a pulser object was provided, flag pulser events in data based on its flag
        if(pulser):
            try:
                pulser_timestamps = pulser.data[ pulser.data['flag_pulser'] ]['datetime']#.set_index('datetime').index
                self.data['flag_pulser'] = False
                self.data = self.data.set_index('datetime')
                self.data.loc[pulser_timestamps, 'flag_pulser'] = True
            except:
                print("Warning: cannot flag pulser events, maybe timestamps for some reason don't match, faulty data?")
                print("! Proceeding without pulser flag !")

            print(self.data)     

        else:
            # --- if no object was provided, it's understood that this itself is a pulser
            # find timestamps over threshold
            high_thr = 12500
            self.data = self.data.set_index('datetime')   
            wf_max_rel = self.data['wf_max'] - self.data['baseline'] 
            pulser_timestamps = self.data[ wf_max_rel > high_thr ].index
            # flag them
            self.data['flag_pulser'] = False
            self.data.loc[pulser_timestamps, 'flag_pulser'] = True                    

        self.data = self.data.reset_index()  


    def get_channel_map(self, config):
        """
        Buld channel map for given subsystem
        location - fiber for SiPMs, string for gedet, dummy for pulser
        """
        
        print('... getting channel map')
        
        df_map = pd.DataFrame({'name':[], 'location': [], 'channel':[], 'position':[]})
        df_map = df_map.set_index('channel')
        
        # -------------------------------------------------------------------------      

        # selection depending on subsystem, dct_key is the part corresponding to one chmap entry
        def is_subsystem(dct_key):
            # special case for pulser
            if self.type == 'pulser':
                pulser_ch = 0 if config.dataset.exp == 'l60' else 1
                return dct_key['system'] == 'auxs' and dct_key['daq']['fcid'] == pulser_ch
            # for geds or spms
            return dct_key['system'] == self.type

        # name of location
        loc_code = {'geds': 'string', 'spms': 'fiber'}

        # -------------------------------------------------------------------------      
        # loop over entries and find out subsystem
        # -------------------------------------------------------------------------      

        # config.channel_map is already a dict read from the channel map json
        for key in config.channel_map:
            # skip 'BF' don't even know what it is
            if 'BF' in key:
                continue

            # skip if this is not our system
            if not is_subsystem(config.channel_map[key]):
                continue
                        
            # --- add info for this channel
            # FlashCam channel, unique for geds/spms/pulser            
            ch = config.channel_map[key]['daq']['fcid']
            df_map.at[ch, 'name'] = config.channel_map[key]['name']
            # number/name of stirng/fiber for geds/spms, dummy for pulser
            df_map.at[ch, 'location'] = 0 if self.type == 'pulser' else config.channel_map[key]['location'][loc_code[self.type]]
            # position in string/fiber for geds/spms, dummy for pulser (works if there is only one pulser channel)
            df_map.at[ch, 'position'] = 0 if self.type == 'pulser' else config.channel_map[key]['location']['position']
            # ? add CC4 name goes here?
                                
        df_map = df_map.reset_index()

        # -------------------------------------------------------------------------      

        # stupid dataframe, can use dtype somehow to fix it?
        for col in ['channel', 'location', 'position']:
            if isinstance(df_map[col].loc[0], float):
                df_map[col] = df_map[col].astype(int)
                
        # sort by channel -> do we really need to?
        df_map = df_map.sort_values('channel')
        return df_map
    

    def get_channel_status(self, config):
        # AUX channels are not in status map, so at least for pulser need default On        
        self.ch_map['status'] = 'On'
        self.ch_map = self.ch_map.set_index('channel')
        for ch in config.status_map:
            # status map contains all channels, check if this channel is in our subsystem
            if ch in self.ch_map:
                self.ch_map.at[int(ch[2:]), 'status'] = config.status_map[ch]['software_status']
                
        self.ch_map = self.ch_map.reset_index()


    def params_for_dataloader(self, dataset):
        # --- always read timestamp
        params = ['timestamp']
        # --- always get wf_max & baseline for pulser for flagging
        if self.type == 'pulser':
            params += ['wf_max', 'baseline']
        
        # --- add QC method to parameters to be read from the DataLoader
        if self.qc:
            params.append(dataset.qc_name)
            
        # --- add user requested parameters
        global USER_TO_PYGAMA
        for param in self.parameters:
            if param in SPECIAL_PARAMETERS:
                # for special parameters, look up which parameters are needed to be loaded for their calculation
                # if none, ignore
                params += (SPECIAL_PARAMETERS[param] if SPECIAL_PARAMETERS[param] else [])
            else:
                # otherwise just add the parameter directly
                params.append(param)
        
        # add K_lines energy if needed
        if self.k_lines:
            params.append(SPECIAL_PARAMETERS['K_lines'][0])

        # some parameters might be repeated twice - remove
        return list(np.unique(params))        
    

    def construct_dataloader_configs(self, dataset, params):

        # -------------------------------------------------------------------------      
        # which parameters belong to which tiers

        # !! put in a settings json or something!
        PARAM_TIERS = pd.DataFrame({
            'param': ['baseline', 'wf_max', 'timestamp', 'cuspEmax_ctc_cal', 'AoE_Corrected', 'zacEmax_ctc_cal', 'cuspEmax'],
            'tier': ['dsp', 'dsp', 'dsp', 'hit', 'hit', 'hit', 'dsp']
        })

        # which of these are requested by user
        PARAM_TIERS = PARAM_TIERS[ PARAM_TIERS['param'].isin(params) ]

        # -------------------------------------------------------------------------      
        # set up config templates

        dict_dbconfig = {
            "data_dir": dataset.path,
            "tier_dirs": {},
            "file_format": {},        
            "table_format": {},
            "tables": {},
            "columns": {}
        }
        dict_dlconfig = {
            'channel_map': {},
            'levels': {}
        }

        # -------------------------------------------------------------------------      
        # set up tiers depending on what parameters we need

        # ronly load channels that are On (Off channels will crash DataLoader)
        chlist = list(self.ch_map[ self.ch_map['status'] == 'On']['channel'])
        removed_chs = list(self.ch_map[ self.ch_map['status'] == 'Off']['channel'])
        print('...... not loading channels with status Off: {}'.format(removed_chs))  

        for tier, tier_params in PARAM_TIERS.groupby('tier'):
            dict_dbconfig['tier_dirs'][tier] = f'/{tier}'
            # type not fixed and instead specified in the query
            dict_dbconfig['file_format'][tier] = "/{type}/{period}/{run}/{exp}-{period}-{run}-{type}-{timestamp}-tier_" + tier + '.lh5'
            dict_dbconfig['table_format'][tier] = "ch{ch:03d}/" + tier
                         
            dict_dbconfig['tables'][tier] = chlist

            dict_dbconfig['columns'][tier] = list(tier_params['param'])

            dict_dlconfig['levels'][tier] = {'tiers': [tier]}

        # special "non-symmetrical" stuff for hit
        if 'hit' in dict_dlconfig['levels']:
            # levels for hit should also include dsp like this {"hit": {"tiers": ["dsp", "hit"]}}
            dict_dlconfig['levels']['hit']['tiers'].append('dsp')
            # # dsp should not be in levels separately - if I'm loading hit, I'm always loading dsp too for timestamp
            dict_dlconfig['levels'].pop('dsp')

        return dict_dlconfig, dict_dbconfig    
