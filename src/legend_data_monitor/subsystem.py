import logging

import numpy as np
import pandas as pd
from pygama.flow import DataLoader

# ------------

# specify which lh5 parameters are neede to be loaded from lh5 to calculate them
SPECIAL_PARAMETERS = {
    # 'uncal_puls': 'trapTmax',
    # 'cal_puls': 'cuspEmax_ctc_cal',
    "K_lines": "cuspEmax_ctc_cal",
    "wf_max_rel": ["wf_max", "baseline"],
    "event_rate": None,  # for event rate, don't need to load any parameter, just count events
}

# convert all to lists for convenience
for param in SPECIAL_PARAMETERS:
    if isinstance(SPECIAL_PARAMETERS[param], str):
        SPECIAL_PARAMETERS[param] = [SPECIAL_PARAMETERS[param]]

# ------------


class Subsystem:
    """
    Object containing information for a given subsystem
    such as chanel map, removed channels etc.
    """

    def __init__(self, config, sub_type):
        """
        conf: config.Config object with user providedsettings
        sub_type [str]: geds | spms | pulser
        """
        logging.error(r"\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/")
        logging.error(r"\/\ Setting up " + sub_type)
        logging.error(r"\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/")

        self.type = sub_type

        # channels to be removed from channel map (have no hit data)
        # !! why needed? DataLoader crashes if channels missing are there?
        self.removed_chs = []
        if (
            sub_type in config.subsystems
            and "removed_channels" in config.subsystems[sub_type]
        ):
            self.removed_chs = config.subsystems[sub_type]["removed_channels"]

        self.ch_map = self.get_channel_map(config)  # pd.DataFrame

        # list parameters of interest
        self.parameters = (
            config.subsystems[sub_type]["parameters"]
            if sub_type in config.subsystems
            else []
        )

        # a bit cumbersome, but we need to know if K_lines was requested to select specified energy parameter
        self.k_lines = False
        for param in self.parameters:
            self.k_lines = self.k_lines or (
                config.plotting.parameters[param]["events"] == "K_lines"
            )

        # !! quality cut bool
        # per parameter or per subsystem?
        self.qc = (
            config.subsystems[sub_type]["quality_cut"]
            if sub_type in config.subsystems
            else False
        )

        self.data = pd.DataFrame()

    def get_data(self, dataset):
        """
        plt_set [dict]: plot settings for this subsystem
            (params to plot, QC bool, ...)
        """

        logging.error("... getting data")

        # -------------------------------
        # prepare parameter list for DataLoader()

        # always read timestamp
        params = ["timestamp"]
        # always get wf_max & baseline for pulser for flagging
        if self.type == "pulser":
            params += ["wf_max", "baseline"]

        # add QC method to parameters to be read from the DataLoader
        if self.qc:
            params.append(dataset.qc_name)

        # add user requested parameters
        global USER_TO_PYGAMA
        for param in self.parameters:
            if param in SPECIAL_PARAMETERS:
                # for special parameters, look up which parameters are needed to be loaded for their calculation
                # if none, ignore
                params += SPECIAL_PARAMETERS[param] if SPECIAL_PARAMETERS[param] else []
            else:
                # otherwise just add the parameter directly
                params.append(param)

        # add K_lines energy if needed
        if self.k_lines:
            params.append(SPECIAL_PARAMETERS["K_lines"][0])

        # some parameters might be repeated twice - remove (maybe not needed?)
        params = list(np.unique(params))

        # -------------------------------
        # get data from DataLoader
        dlconfig, dbconfig = self.construct_dataloader_configs(dataset, params)
        logging.error("...... calling data loader")
        dl = DataLoader(dlconfig, dbconfig)
        # if querying by run, need different query word
        time_word = "run" if dataset.time_range["start"][0] == "r" else "timestamp"
        query = f"({time_word} >= '{dataset.time_range['start']}') and ({time_word} <= '{dataset.time_range['end']}')"
        # cal or phy data or both
        query += (
            " and (" + " or ".join("(type == '" + x + "')" for x in dataset.type) + ")"
        )

        # !!!! QUICKFIX FOR R010
        query += " and (timestamp != '20230125T222013Z')"
        query += " and (timestamp != '20230126T015308Z')"

        logging.error(query)
        dl.set_files(query)
        dl.set_output(fmt="pd.DataFrame", columns=params)
        self.data = dl.load()

        # -------------------------------
        # polish things up

        tier = "hit" if "hit" in dbconfig["columns"] else "dsp"
        # remove columns we don't need
        self.data = self.data.drop([f"{tier}_idx", "file"], axis=1)
        # rename channel to channel
        self.data = self.data.rename(columns={f"{tier}_table": "channel"})

        # rename columns back to user params
        # remove Nones
        # USER_TO_PYGAMA = {key: USER_TO_PYGAMA[key] for key in USER_TO_PYGAMA if USER_TO_PYGAMA[key]}
        # self.data = self.data.rename(columns = dict(zip(USER_TO_PYGAMA.values(), USER_TO_PYGAMA.keys())))

        # -------------------------------
        # create datetime column based on initial key and timestamp

        # convert UTC timestamp to datetime (unix epoch time)
        self.data["datetime"] = pd.to_datetime(
            self.data["timestamp"], origin="unix", utc=True, unit="s"
        )
        # drop timestamp
        self.data = self.data.drop("timestamp", axis=1)

        # -------------------------------
        # add detector name, location and position from map

        # !! don't need to do yet, takes time?
        # logging.error('......mapping to name and string/fiber position')
        # self.ch_map = self.ch_map.set_index('channel')
        # self.data = self.data.set_index('channel')
        # for col in self.ch_map:
        #     self.data[col] = self.ch_map.loc[self.data.index][col]
        # self.data = self.data.reset_index()

        # -------------------------------

        # apply QC*
        # !! right now set up to be per subsystem, not per parameter
        if self.qc:
            logging.error("...... applying quality cut")
            self.data = self.data[self.data[dataset.qc_name]]

        logging.error(self.data)

    def flag_pulser_events(self, pulser):
        # flag pulser events
        logging.error("... flagging pulser events")
        # find timestamps where goes over threshold
        high_thr = 12500
        pulser.data["wf_max_rel"] = pulser.data["wf_max"] - pulser.data["baseline"]
        # !! use datetime instead of timestamp, drop timestamp?
        pulser_timestamps = pulser.data[pulser.data["wf_max_rel"] > high_thr][
            "datetime"
        ]
        # flag data
        self.data["flag_pulser"] = False
        try:
            self.data = self.data.set_index("datetime")
            self.data.loc[pulser_timestamps, "flag_pulser"] = True
        except:
            logging.error(
                "Warning: probably calibration has faulty pulser data and timestamps not found. Proceeding with all events flagged as False for pulser."
            )

        self.data = self.data.reset_index()

    def get_channel_map(self, config):
        """
        Buld channel map for given subsystem
        location - fiber for SiPMs, string for gedet, dummy for pulser
        """
        logging.error("... getting channel map")

        df_map = pd.DataFrame(
            {"name": [], "location": [], "channel": [], "position": []}
        )
        df_map = df_map.set_index("channel")

        # selection depending on subsystem, dct_key is the part corresponding to one chmap entry
        def is_subsystem(dct_key):
            # special case for pulser
            if self.type == "pulser":
                pulser_ch = 0 if config.dataset.exp == "l60" else 1
                return (
                    dct_key["system"] == "auxs" and dct_key["daq"]["fcid"] == pulser_ch
                )
            # for geds or spms
            return dct_key["system"] == self.type

        # key_code = {'geds': ['V', 'B', 'P', 'C'], 'pulser': ['A'], 'spms': ['S']}
        # name of location
        loc_code = {"geds": "string", "spms": "fiber"}

        # config.channel_map is already a dict read from the channel map json
        for key in config.channel_map:
            # skip 'BF' don't even know what it is
            if "BF" in key:
                continue

            # skip if this is not our system
            if not is_subsystem(config.channel_map[key]):
                continue

            # add info for this channel
            # FlashCam channel, unique for geds/spms/pulser
            ch = config.channel_map[key]["daq"]["fcid"]
            df_map.at[ch, "name"] = config.channel_map[key]["name"]
            # number/name of stirng/fiber for geds/spms, dummy for pulser
            df_map.at[ch, "location"] = (
                0
                if self.type == "pulser"
                else config.channel_map[key]["location"][loc_code[self.type]]
            )
            # position in string/fiber for geds/spms, dummy for pulser (works if there is only one pulser channel)
            df_map.at[ch, "position"] = (
                0
                if self.type == "pulser"
                else config.channel_map[key]["location"]["position"]
            )

        df_map = df_map.reset_index()
        # stupid dataframe
        # !! change to using dtype!
        for col in ["channel", "location", "position"]:
            if isinstance(df_map[col].loc[0], float):
                df_map[col] = df_map[col].astype(int)

        # ?? sort by channel -> do we really need to?
        df_map = df_map.sort_values("channel")
        return df_map

    def construct_dataloader_configs(self, dataset, params):
        """ """

        # which parameters belong to which tiers
        # !! put in a settings json or something!
        param_tiers = pd.DataFrame(
            {
                "param": [
                    "baseline",
                    "wf_max",
                    "timestamp",
                    "cuspEmax_ctc_cal",
                    "AoE_Corrected",
                    "zacEmax_ctc_cal",
                    "cuspEmax",
                ],
                "tier": ["dsp", "dsp", "dsp", "hit", "hit", "hit", "dsp"],
            }
        )

        # which of these are requested by user
        param_tiers = param_tiers[param_tiers["param"].isin(params)]

        # set up config templates
        dict_dbconfig = {
            "data_dir": dataset.path,
            "tier_dirs": {},
            "file_format": {},
            "table_format": {},
            "tables": {},
            "columns": {},
        }
        dict_dlconfig = {"channel_map": {}, "levels": {}}

        # set up tiers depending on what parameters we need
        logging.error(f"......removing channels with no data: {self.removed_chs}")
        for tier, tier_params in param_tiers.groupby("tier"):
            dict_dbconfig["tier_dirs"][tier] = f"/{tier}"
            # type not fixed and instead specified in the query
            dict_dbconfig["file_format"][tier] = (
                "/{type}/{period}/{run}/{exp}-{period}-{run}-{type}-{timestamp}-tier_"
                + tier
                + ".lh5"
            )
            dict_dbconfig["table_format"][tier] = "ch{ch:03d}/" + tier

            # remove channels requested by user if hit level
            chlist = self.ch_map["channel"]
            # if tier == 'hit':
            chlist = chlist[~self.ch_map["channel"].isin(self.removed_chs)]
            dict_dbconfig["tables"][tier] = list(chlist)

            dict_dbconfig["columns"][tier] = list(tier_params["param"])

            dict_dlconfig["levels"][tier] = {"tiers": [tier]}

        # special "non-symmetrical" stuff for hit
        if "hit" in dict_dlconfig["levels"]:
            # levels for hit should also include dsp like this {"hit": {"tiers": ["dsp", "hit"]}}
            dict_dlconfig["levels"]["hit"]["tiers"].append("dsp")
            # # dsp should not be in levels separately - if I'm loading hit, I'm always loading dsp too for timestamp
            dict_dlconfig["levels"].pop("dsp")

        return dict_dlconfig, dict_dbconfig
