import logging
import os
from datetime import datetime

import numpy as np
import pandas as pd
from legendmeta import LegendMetadata
from pygama.flow import DataLoader

from . import utils

LEGEND_META = LegendMetadata()


# ------------
# specify which lh5 parameters are neede to be loaded from lh5 to calculate them
SPECIAL_PARAMETERS = {
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

    sub_type [str]: geds | spms | pulser

    Options for kwargs

    setup=
        dict with the following keys:
            - 'experiment' [str]: 'L60' or 'L200'
            - 'period' [str]: 'pXX' e.g. p02
    Or input kwargs separately experiment=, period=
    """

    def __init__(self, sub_type: str, **kwargs):
        print(r"\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/")
        print(r"\/\ Setting up " + sub_type)
        print(r"\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/")

        self.type = sub_type

        # -------------------------------------------------------------------------
        # input check
        # -------------------------------------------------------------------------

        # if setup= kwarg was provided, get dict provided
        # otherwise kwargs is itself already the dict we need with experiment= and period=
        setup_info = kwargs["setup"] if "setup" in kwargs else kwargs
        experiments = ["L200", "L60"]
        if (
            not "experiment" in setup_info
            or not setup_info["experiment"] in experiments
        ):
            logging.error("Tell Subsystem valid experiment it belongs to!")
            print(self.__doc__)
            return
        if not "period" in setup_info or not setup_info["period"][0] == "p":
            logging.error("Tell Subsystem valid period it belongs to!")
            print(self.__doc__)
            return

        # -------------------------------------------------------------------------
        # get channel map for this subsystem
        # -------------------------------------------------------------------------

        self.channel_map = self.get_channel_map(setup_info)  # pd.DataFrame

        # add column status to channel map stating On/Off
        self.get_channel_status(setup_info)

        # -------------------------------------------------------------------------
        # K lines
        # -------------------------------------------------------------------------

        # # a bit cumbersome, but we need to know if K_lines was requested to select specified energy parameter
        # self.k_lines = False
        # for plot in self.plots:
        #     # if K lines is asked, set to true
        #     self.k_lines = self.k_lines or (self.plots[plot]['events'] == 'K_lines')

        # -------------------------------------------------------------------------
        # have something before get_data() is called just in case
        self.data = pd.DataFrame()

    def get_data(self, parameters=[], **kwargs):
        """
        parameters [list]: list of parameters to load; if empty, only default parameters will be loaded (channel, timestamp; baseline and wfmax for pulser)

        Available kwargs:

        dataset=
            dict with the following contents:
                - 'type' [str or list of str]: type of data to load e.g. 'phy', 'cal', or ['phy', 'cal']
                - 'path' [str]: path to prod-ref folder (in which is the structure vXX.XX/generated/tier/...) -> needed only for get_data
                - 'version' [str]: version of pygama vXX.XX e.g. 'v06.00'
                - 'selection' [dict]: dict with fields depending on selection options
                    1) 'start' : <start datetime>, 'end': <end datetime> where <datetime> input is of format 'YYYY-MM-DD hh:mm:ss'
                    2) 'window'[str]: time window in the past from current time point, format: 'Xd Xh Xm' for days, hours, minutes
                    2) 'timestamps': str or list of str in format 'YYYYMMDDThhmmssZ'
                    3) 'runs': int or list of ints for run number(s)  e.g. 10 for r010
        Or input kwargs separately type=, path=, version=; start=&end, or timestamp=, or runs=

        Might set default v06.00 for version, but gotta be careful.
        """

        print("... getting data")

        # if dataset= kwarg was provided, get the dict provided
        # otherwise kwargs itself is already the dict we need with type=, path=, version=; start=&end= or timestamps= or runs=
        # we need this dict only for type/path/version (will also contain selection info, but don't care about that)
        data_info = kwargs["dataset"] if "dataset" in kwargs else kwargs

        # -------------------------------------------------------------------------
        # check validity
        # -------------------------------------------------------------------------

        if not "type" in data_info:
            logging.error("Provide data type!")
            print(self.get_data.__doc__)
            return

        # convert to list for convenience
        if isinstance(data_info["type"], str):
            data_info["type"] = [data_info["type"]]

        data_types = ["phy", "cal"]
        for datatype in data_info["type"]:
            if not datatype in data_types:
                logging.error("Invalid data type provided!")
                print(self.get_data.__doc__)
                return

        if not "path" in data_info:
            logging.error("Provide path to data!")
            print(self.get_data.__doc__)
            return
        if not os.path.exists(data_info["path"]):
            logging.error("The data path you provided does not exist!")
            return

        if not "version" in data_info:
            logging.error("Provide pygama version!")
            print(self.get_data.__doc__)
            return

        if not os.path.exists(os.path.join(data_info["path"], data_info["version"])):
            logging.error("Provide valid pygama version!")
            print(self.get_data.__doc__)
            return

        # -------------------------------------------------------------------------
        # Set up DataLoader config
        # -------------------------------------------------------------------------
        print("...... setting up DataLoader")

        # --- construct list of parameters for the data loader
        # depending on special parameters, k lines etc.
        params_for_dataloader = self.get_parameters_for_dataloader(parameters)

        # --- set up DataLoader config
        # needs to know path and version from data_info
        dlconfig, dbconfig = self.construct_dataloader_configs(
            params_for_dataloader, data_info
        )

        # --- set up DataLoader
        dl = DataLoader(dlconfig, dbconfig)

        # -------------------------------------------------------------------------
        # Set up query
        # -------------------------------------------------------------------------

        # --- set up time range

        # needs kwargs dataset={'selection': {...}} or separately start=&end=, or timestamps=, or runs= <- already in kwargs here
        # returns dict {'start: timestamp1, 'end': timestamp2} or list of runs/keys to get
        # it will also check the validity of the selection arguments
        dataloader_timerange = utils.get_dataloader_timerange(**kwargs)
        # get_dataloader_timerange() will return None if there was an error -> exit
        if not dataloader_timerange:
            print(self.get_data.__doc__)
            return

        # if querying by run, need different query word than by timestamp
        # in case of runs, format is 'rXXX', and it will be a list
        time_word = (
            "run"
            if isinstance(dataloader_timerange, list)
            and dataloader_timerange[0][0] == "r"
            else "timestamp"
        )
        if isinstance(dataloader_timerange, dict):
            # query by (timestamp >= ) and (timestamp <=) if format {start: end:}
            query = f"({time_word} >= '{dataloader_timerange['start']}') and ({time_word} <= '{dataloader_timerange['end']}')"
        else:
            # query by (run/timestamp == ) or (run/timestamp == ) if format [list of runs/timestamps]
            query = " or ".join(
                f"({time_word} == '" + run_or_timestamp + "')"
                for run_or_timestamp in dataloader_timerange
            )

        # --- cal or phy data or both
        query += (
            " and ("
            + " or ".join("(type == '" + x + "')" for x in data_info["type"])
            + ")"
        )

        # !!!! QUICKFIX FOR R010
        query += " and (timestamp != '20230125T222013Z')"
        query += " and (timestamp != '20230126T015308Z')"

        print(
            "...... querying DataLoader (includes quickfix-removed faulty files for r010)"
        )
        print(query)

        # -------------------------------------------------------------------------
        # Query DataLoader & load data
        # -------------------------------------------------------------------------

        # --- query data loader
        dl.set_files(query)
        dl.set_output(fmt="pd.DataFrame", columns=params_for_dataloader)

        now = datetime.now()
        self.data = dl.load()
        print(f"Total time to load data: {(datetime.now() - now)}")

        # -------------------------------------------------------------------------
        # polish things up
        # -------------------------------------------------------------------------

        tier = "hit" if "hit" in dbconfig["columns"] else "dsp"
        # remove columns we don't need
        self.data = self.data.drop([f"{tier}_idx", "file"], axis=1)
        # rename channel to channel
        self.data = self.data.rename(columns={f"{tier}_table": "channel"})

        # -------------------------------------------------------------------------
        # create datetime column based on initial key and timestamp
        # -------------------------------------------------------------------------

        # convert UTC timestamp to datetime (unix epoch time)
        self.data["datetime"] = pd.to_datetime(
            self.data["timestamp"], origin="unix", utc=True, unit="s"
        )
        # drop timestamp
        self.data = self.data.drop("timestamp", axis=1)

        # -------------------------------------------------------------------------
        # add detector name, location and position from map
        # -------------------------------------------------------------------------

        print("... mapping to name and string/fiber position")
        self.data = self.data.set_index("channel")
        # expand channel map index to match that of data with repeating channels
        ch_map_reindexed = self.channel_map.set_index("channel").reindex(
            self.data.index
        )
        # append the channel map columns to the data
        self.data = pd.concat([self.data, ch_map_reindexed], axis=1)
        self.data = self.data.reset_index()
        # stupid dataframe, why float
        for col in ["location", "position"]:
            # ignore string values for fibers ('I/OB-XXX-XXX') and positions ('top/bottom') for SiPMs
            if isinstance(self.data[col].iloc[0], float):
                self.data[col] = self.data[col].astype(int)

        # -------------------------------------------------------------------------
        # if this subsystem is pulser, flag pulser timestamps
        # -------------------------------------------------------------------------

        if self.type == "pulser":
            self.flag_pulser_events()

    def flag_pulser_events(self, pulser=None):
        print("... flagging pulser events")

        # --- if a pulser object was provided, flag pulser events in data based on its flag
        if pulser:
            try:
                pulser_timestamps = pulser.data[pulser.data["flag_pulser"]][
                    "datetime"
                ]  # .set_index('datetime').index
                self.data["flag_pulser"] = False
                self.data = self.data.set_index("datetime")
                self.data.loc[pulser_timestamps, "flag_pulser"] = True
            except:
                logging.error(
                    "Warning: cannot flag pulser events, maybe timestamps for some reason don't match, faulty data?"
                )
                logging.error("! Proceeding without pulser flag !")

        else:
            # --- if no object was provided, it's understood that this itself is a pulser
            # find timestamps over threshold
            high_thr = 12500
            self.data = self.data.set_index("datetime")
            wf_max_rel = self.data["wf_max"] - self.data["baseline"]
            pulser_timestamps = self.data[wf_max_rel > high_thr].index
            # flag them
            self.data["flag_pulser"] = False
            self.data.loc[pulser_timestamps, "flag_pulser"] = True

        self.data = self.data.reset_index()

    def get_channel_map(self, setup_info: dict):
        """
        Buld channel map for given subsystem
        location - fiber for SiPMs, string for gedet, dummy for pulser

        setup_info: dict with the keys 'experiment' and 'period'

        Later will probably be changed to get channel map by timestamp (or hopefully run, if possible)
        Planning to add:
            - CC4 name
            - barrel column for SiPMs special case
        """

        print("... getting channel map")

        # -------------------------------------------------------------------------
        # load full channel map of this exp and period
        # -------------------------------------------------------------------------

        ex = "l" + setup_info["experiment"][1:].zfill(3)  # l060 or l200
        json_file = f"{ex}-{setup_info['period']}-r%-T%-all-config.json"
        full_channel_map = LEGEND_META.hardware.configuration.channelmaps[json_file]

        df_map = pd.DataFrame(
            {"name": [], "location": [], "channel": [], "position": []}
        )
        df_map = df_map.set_index("channel")

        # -------------------------------------------------------------------------
        # helper function to determine which channel map entry belongs to this subsystem
        # -------------------------------------------------------------------------

        # dct_key is the subdict corresponding to one chmap entry
        def is_subsystem(dct_key):
            # special case for pulser
            if self.type == "pulser":
                pulser_ch = 0 if setup_info["experiment"] == "L60" else 1
                return (
                    dct_key["system"] == "auxs" and dct_key["daq"]["fcid"] == pulser_ch
                )
            # for geds or spms
            return dct_key["system"] == self.type

        # name of location in the channel map
        loc_code = {"geds": "string", "spms": "fiber"}

        # -------------------------------------------------------------------------
        # loop over entries and find out subsystem
        # -------------------------------------------------------------------------

        # config.channel_map is already a dict read from the channel map json
        for key in full_channel_map:
            # skip 'BF' don't even know what it is
            if "BF" in key:
                continue

            # skip if this is not our system
            if not is_subsystem(full_channel_map[key]):
                continue

            # --- add info for this channel
            # FlashCam channel, unique for geds/spms/pulser
            ch = full_channel_map[key]["daq"]["fcid"]
            df_map.at[ch, "name"] = full_channel_map[key]["name"]
            # number/name of stirng/fiber for geds/spms, dummy for pulser
            df_map.at[ch, "location"] = (
                0
                if self.type == "pulser"
                else full_channel_map[key]["location"][loc_code[self.type]]
            )
            # position in string/fiber for geds/spms, dummy for pulser (works if there is only one pulser channel)
            df_map.at[ch, "position"] = (
                0
                if self.type == "pulser"
                else full_channel_map[key]["location"]["position"]
            )
            # ? add CC4 name goes here

        df_map = df_map.reset_index()

        # -------------------------------------------------------------------------

        # stupid dataframe, can use dtype somehow to fix it?
        for col in ["channel", "location", "position"]:
            if isinstance(df_map[col].loc[0], float):
                df_map[col] = df_map[col].astype(int)

        # sort by channel -> do we really need to?
        df_map = df_map.sort_values("channel")
        return df_map

    def get_channel_status(self, setup_info: dict):
        """
        Add status column to channel map with On/Off for software status

        setup_info: dict with the keys 'experiment' and 'period'

        Later will probably be changed to get channel status by timestamp (or hopefully run, if possible)
        """

        print("... getting channel status")

        # -------------------------------------------------------------------------
        # load full status map of this exp and period
        # -------------------------------------------------------------------------

        run = {"L60": "%", "L200": "010"}[setup_info["experiment"]]
        # L60-pXX-r%-... for L60, L200-pXX-r010-... for L200
        json_file = f"{setup_info['experiment']}-{setup_info['period']}-r{run}-T%-all-config.json"
        full_status_map = LEGEND_META.dataprod.config[json_file][
            "hardware_configuration"
        ]["channel_map"]

        # ----- from Katha
        # chstatmap = self.lmeta.dataprod.config.on(timestamp=timestamp, system='phy')['hardware_configuration']['channel_map']
        # chstat = chstatmap.get('ch'+f"{val.daq.fcid:03d}", {}).get("software_status", "Off")
        # if chstat == "On":
        # ....

        # AUX channels are not in status map, so at least for pulser need default On
        self.channel_map["status"] = "On"
        self.channel_map = self.channel_map.set_index("channel")
        for channel in full_status_map:
            # convert string channel ('ch005') to integer (5)
            ch = int(channel[2:])
            # status map contains all channels, check if this channel is in our subsystem
            if ch in self.channel_map.index:
                self.channel_map.at[ch, "status"] = full_status_map[channel][
                    "software_status"
                ]

        self.channel_map = self.channel_map.reset_index()

    def get_parameters_for_dataloader(self, parameters: list):
        """
        Construct list of parameters to query from the DataLoader
            - parameters that are always loaded (+ pulser special case)
            - parameters that are already in lh5
            - parameters needed for calculation, if special parameter(s) asked
        """

        # --- always read timestamp
        params = ["timestamp"]
        # --- always get wf_max & baseline for pulser for flagging
        if self.type == "pulser":
            params += ["wf_max", "baseline"]

        # --- add user requested parameters
        # change to list for convenience, if input was single
        if isinstance(parameters, str):
            parameters = [parameters]

        global USER_TO_PYGAMA
        for param in parameters:
            if param in SPECIAL_PARAMETERS:
                # for special parameters, look up which parameters are needed to be loaded for their calculation
                # if none, ignore
                params += SPECIAL_PARAMETERS[param] if SPECIAL_PARAMETERS[param] else []
            else:
                # otherwise just add the parameter directly
                params.append(param)

        # add K_lines energy if needed
        # if 'K_lines' in parameters:
        #     params.append(SPECIAL_PARAMETERS['K_lines'][0])

        # some parameters might be repeated twice - remove
        return list(np.unique(params))

    def construct_dataloader_configs(self, params: list, data_info: dict):
        # -------------------------------------------------------------------------
        # which parameters belong to which tiers

        # !! put in a settings json or something!
        PARAM_TIERS = pd.DataFrame(
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
        PARAM_TIERS = PARAM_TIERS[PARAM_TIERS["param"].isin(params)]

        # -------------------------------------------------------------------------
        # set up config templates

        dict_dbconfig = {
            "data_dir": os.path.join(
                data_info["path"], data_info["version"], "generated", "tier"
            ),
            "tier_dirs": {},
            "file_format": {},
            "table_format": {},
            "tables": {},
            "columns": {},
        }
        dict_dlconfig = {"channel_map": {}, "levels": {}}

        # -------------------------------------------------------------------------
        # set up tiers depending on what parameters we need

        # ronly load channels that are On (Off channels will crash DataLoader)
        chlist = list(self.channel_map[self.channel_map["status"] == "On"]["channel"])
        removed_chs = list(
            self.channel_map[self.channel_map["status"] == "Off"]["channel"]
        )
        print(f"...... not loading channels with status Off: {removed_chs}")

        for tier, tier_params in PARAM_TIERS.groupby("tier"):
            dict_dbconfig["tier_dirs"][tier] = f"/{tier}"
            # type not fixed and instead specified in the query
            dict_dbconfig["file_format"][tier] = (
                "/{type}/{period}/{run}/{exp}-{period}-{run}-{type}-{timestamp}-tier_"
                + tier
                + ".lh5"
            )
            dict_dbconfig["table_format"][tier] = "ch{ch:03d}/" + tier

            dict_dbconfig["tables"][tier] = chlist

            dict_dbconfig["columns"][tier] = list(tier_params["param"])

            dict_dlconfig["levels"][tier] = {"tiers": [tier]}

        # special "non-symmetrical" stuff for hit
        if "hit" in dict_dlconfig["levels"]:
            # levels for hit should also include dsp like this {"hit": {"tiers": ["dsp", "hit"]}}
            dict_dlconfig["levels"]["hit"]["tiers"].append("dsp")
            # # dsp should not be in levels separately - if I'm loading hit, I'm always loading dsp too for timestamp
            dict_dlconfig["levels"].pop("dsp")

        return dict_dlconfig, dict_dbconfig
