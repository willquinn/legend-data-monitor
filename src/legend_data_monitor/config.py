# needed to open files in settings/
import importlib.resources
import json
import logging
import os
import sys
from datetime import datetime

from legendmeta import LegendMetadata
from legendmeta.jsondb import AttrsDict

# needed to check plot settings
from . import plotting

pkg = importlib.resources.files("legend_data_monitor")

SINGLE_TO_LIST = {"dataset": {"type": 0, "selection": {"runs": 0}}}


def Config(json_name: str):
    """
    json_name: path to user config json file.

    Returns NestedAttrDict. Can't use inheritance because of conflicting kwargs
    in __init__ when passing self. Mascking this function to look like a class.

    >>> config = Config({'a': {'c':1, 'd':3}, 'b': 2})
    >>> config.a.c
    1
    """
    logging.error('Reading settings from ' + str(json_name) + '...')    
    
    with open(pkg / "settings" / json_name) as f:    
        conf = AttrsDict(json.load(f))    

    # update single to list with subsystem for single to list conversion
    for subsys in conf.subsystems:
        SINGLE_TO_LIST["subsystems"] = {
            subsys: {"parameters": 0, "removed_channels": 0}
        }

    # convert strings to lists for single input
    conf = single_to_list(conf)

    # check if something wrong was entered
    check_settings(conf)

    # start time of code - needed if data selection type is "last hours"
    conf.start_code = datetime.now().strftime("%Y%m%dT%H%M%SZ")

    # load channel map
    # l060 instead of l60 for exp
    ex = "l" + conf.dataset.exp.split("l")[1].zfill(3)
    json_file = f"{ex}-{conf.dataset.period}-r%-T%-all-config.json"

    lmeta = LegendMetadata()
    conf.channel_map = lmeta.hardware.configuration.channelmaps[json_file]

    # load dicitonary with plot info (= units, thresholds, label, ...)
    with open(pkg / "settings" / "par-settings.json") as f:
        plot_info_json = AttrsDict(json.load(f))
    conf.plot_info = plot_info_json

    return conf


class PlotSettings:
    def __init__(self, conf: Config, dset):
        logging.error('----------------------------------------------------')
        logging.error('--- Setting up plotting')    
        logging.error('----------------------------------------------------')
        
        # sampling for averages
        # e.g. "30T"
        # minute - T, second - S, month - M
        self.sampling = conf.plotting.sampling

        # output paths, make folders if needed
        self.output_paths = self.make_output_paths(conf)

        # settings for each parameter
        # (keep phy or pulser events, plot style)
        self.param_settings = conf.plotting.parameters
        #
        self.param_info = conf.plot_info

        # check if something is missing or not valid
        self.check_settings()

        # base name for log and PDF files
        self.basename = "{}-{}-{}-{}_{}".format(
            conf.dataset.exp,
            conf.dataset.period,
            "_".join(conf.dataset.type),
            dset.user_time_range["start"],
            dset.user_time_range["end"],
        )

    def make_output_paths(self, conf):
        """define output paths and create directories accordingly"""
        # general output path
        make_dir(conf.plotting.output)

        # output subfolders
        output_paths = {"path": conf.plotting.output}

        # sub directories
        for out_dir in ["log_files", "pdf_files", "pkl_files", "json_files"]:
            out_dir_path = os.path.join(conf.plotting.output, out_dir)
            make_dir(out_dir_path)
            output_paths[out_dir] = out_dir_path

        # sub sub directories
        for out_dir in ["pdf_files", "pkl_files"]:
            # "plot path" and "map path"
            for out_subdir in ["par_vs_time", "heatmaps"]:
                out_dir_path = os.path.join(conf.plotting.output, out_dir, out_subdir)
                make_dir(out_dir_path)
                # !! oops
                output_paths[out_subdir] = out_dir_path

        return AttrsDict(output_paths)

    def check_settings(self):
        options = {
            'events': ['phy', 'pulser', 'all', 'K_lines'],
            'plot_style': plotting.plot_style.keys(),
            'some_name': ['variation', 'absolute']
        }

        # for each parameter, check provided plot settings
        for param in self.param_settings:
            # look at every option available in plot settings
            for field in options:
                # if this field is not provided by user, tell them to provide it
                if field not in self.param_settings[param]:
                    logging.error(f"Provide {field} settings for {param}!")
                    logging.error(
                        "Available options: {}".format(",".join(options[field]))
                    )
                    sys.exit(1)

                opt = self.param_settings[param][field]

                if opt not in options[field]:
                    logging.error(f"Option {opt} provided for {param} does not exist!")
                    logging.error(
                        "Available options: {}".format(",".join(options[field]))
                    )
                    sys.exit(1)

    # ------ logging -> should go to dataset? settings? separate?
    # set up logging to file
    # log name
    # log_name = os.path.join(setup.output_paths['log-files'], dataset.basename + '.log')

    # logging.basicConfig(
    #     filename=log_name,
    #     level=logging.INFO,
    #     filemode="w",
    #     format="%(levelname)s: %(message)s",
    # )

    # # set up logging to console
    # console = logging.StreamHandler()
    # console.setLevel(logging.ERROR)
    # formatter = logging.Formatter("%(asctime)s:  %(message)s")
    # console.setFormatter(formatter)
    # logging.getLogger("").addHandler(console)
    # ------ logging


# ------- Config related functions
def check_settings(conf):
    # if parameter is under subsystem to be plotted, must be in plot settings
    for subsys in conf.subsystems:
        for param in conf.subsystems[subsys].parameters:
            if param not in conf.plotting.parameters:
                logging.error(
                    f"Parameter {param} is asked to be plotted for subsystem {subsys} but no plot settings are provided!"
                )
                sys.exit(1)

    # time selection types
    for key in conf.dataset.selection:
        if key not in ["start", "end", "timestamps", "runs"]:
            logging.error("Invalid dataset time selection!")
            logging.error("Available selection: start & end, timestamps, or runs")
            sys.exit(1)


def single_to_list(conf, dct=SINGLE_TO_LIST):
    """Recursively convert single entries to lists."""
    for field in dct:
        if isinstance(dct[field], dict):
            conf[field] = single_to_list(conf[field], dct[field])

        elif field in conf and not isinstance(conf[field], list):
            conf[field] = [conf[field]]

    return conf


# ----------- helper function
def make_dir(dir_path):
    """Check if directory exists, and if not, make it."""
    message = "Output directory " + dir_path
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)
        message += ' (created)'
    logging.error(message)    
