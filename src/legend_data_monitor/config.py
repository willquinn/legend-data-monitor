import json
import logging
import os
import sys
from datetime import datetime

from legendmeta import LegendMetadata
from legendmeta.jsondb import AttrsDict

# needed to check available plot structures
from .plotting import PLOT_STRUCTURE
# needed to check available plot styles
from .plot_styles import PLOT_STYLE

SINGLE_TO_LIST = {"dataset": {"type": 0, "selection": {"runs": 0}}}


def config_build(user_config):
    """
    user_config: str - name of json, dict/AttrsDict - already in dict format given directly

    Returns nested AttrsDict designed in legendmeta

    >>> config = config_build({'a': {'c':1, 'd':3}, 'b': 2})
    >>> config.a.c
    1
    """

    # if path to json is provided, open json
    if isinstance(user_config, str):
        logging.error("Reading settings from " + str(user_config) + "...")
        with open(user_config) as f:
            conf = json.load(f)
    # if dict is provided, take directly
    elif isinstance(user_config, dict):
        conf = AttrsDict(user_config)
    else:
        logging.error('Input to build_config() should be a dict, AttrsDict or json filename!')
        sys.exit(1)

    # convert to AttrsDict for convenience
    conf = AttrsDict(conf)


    # update single to list with subsystem for single to list conversion
    for subsys in conf.subsystems:
        SINGLE_TO_LIST["subsystems"] = {
            subsys: {"parameters": 0, "removed_channels": 0}
        }

    # convert strings to lists for single input
    conf = single_to_list(conf)

    # check if something wrong was entered
    check_settings(conf)

    # create output paths
    conf.output_paths = make_output_paths(conf)

    # start time of code - needed if data selection type is "last hours"
    conf.start_code = datetime.now().strftime("%Y%m%dT%H%M%SZ")

    # load channel map
    # l060 instead of l60 for exp
    ex = "l" + conf.dataset.exp.split("l")[1].zfill(3)
    json_file = f"{ex}-{conf.dataset.period}-r%-T%-all-config.json"

    lmeta = LegendMetadata()
    conf.channel_map = lmeta.hardware.configuration.channelmaps[json_file]

    # load status map
    if conf.dataset.exp == "60":
        ex = conf.dataset.exp
    json_file = f"{ex.upper()}-{conf.dataset.period}-r%-T%-all-config.json"  # "L200-p02-r010-T%-all-config.json"
    if conf.dataset.exp == "l200":
        json_file = json_file.replace("r%", "r010")
    conf.status_map = lmeta.dataprod.config[json_file]

    return conf


    

    # ------ logging -> should go to dataset? settings? separate?
    # set up logging to file
    # log name
    # log_name = os.path.join(setup.output_paths['log-files'], dataset.basename + '.log')

    # logging.basicConfig(
    #     filename=log_name,
    #     level=logging.error,
    #     filemode="w",
    #     format="%(levelname)s: %(message)s",
    # )
    # ------ logging


# -------------------------------------------------------------------------
# Config related functions
# -------------------------------------------------------------------------

def check_settings(conf):

    # time selection types
    for key in conf.dataset.selection:
        if not key in ['start','end', 'timestamps', 'runs']:
            logging.error('Invalid dataset time selection!')
            logging.error('Available selection: start & end, timestamps, or runs')
            sys.exit(1)

    # param settings
    OPTIONS = {
        'events': ['phy', 'pulser', 'all', 'K_lines'],
        'plot_structure': PLOT_STRUCTURE.keys(),
        'plot_style': PLOT_STYLE.keys(),
        'some_name': ['variation', 'absolute']
    }
        
    # for each plot, check provided plot settings
    for subsys in conf.subsystems:
        for plot in conf.subsystems[subsys]["plots"]:
            # settings for this plot
            plot_settings = conf.subsystems[subsys]['plots'][plot]

            # check if all necessary fields for param settings were provided
            for field in OPTIONS:
                # if this field is not provided by user, tell them to provide it
                if not field in plot_settings:
                    logging.error(f"Provide {field} for plot '{plot}' in {subsys}!")
                    logging.error('Available options: {}'.format(','.join(OPTIONS[field])))
                    sys.exit(1)

                # check if the provided option is valid
                opt = plot_settings[field]

                if not opt in OPTIONS[field]:
                    logging.error(f"Option {opt} provided for {field} in plot '{plot}' does not exist!")
                    logging.error('Available options: {}'.format(','.join(OPTIONS[field])))
                    sys.exit(1)            

            # sampling is needed if
            # - plot style vs time is asked
            # - event rate is asked as parameter
            # parameter in this plot
            param = plot_settings['parameter']
            if not 'sampling' in plot_settings:
                if param == 'event_rate':
                    logging.error(f"You chose parameter event_rate for plot '{plot}' in {subsys} and did not provide sampling window.")
                    sys.exit(1)
                
                elif plot_settings['plot_style'] == 'vs time':
                    logging.error(f"You chose plot style vs time for plot '{plot}' in {sybsys} and did not provide sampling window.")
                    sys.exit(1)            


def make_output_paths(conf):
    ''' define output paths and create directories accordingly '''

    print('----------------------------------------------------')
    print('--- Setting up plotting')    
    print('----------------------------------------------------')

    # general output path
    make_dir(conf.output)

    # output subfolders
    output_paths = {}

    # sub directories
    for out_dir in ["log_files", "pdf_files", "pkl_files", "json_files"]:
        out_dir_path = os.path.join(conf.output, out_dir)
        make_dir(out_dir_path)
        # remember for later for convenience
        output_paths[out_dir] = out_dir_path

    # sub sub directories
    for out_dir in ["pdf_files", "pkl_files"]:
        for out_subdir in ["par_vs_time", "heatmaps"]:
            out_dir_path = os.path.join(conf.output, out_dir, out_subdir)
            # make dir but no need to remember
            make_dir(out_dir_path)
            
    return AttrsDict(output_paths)   

# ------------------------------------------------------------------------- 
# helper functions
# -------------------------------------------------------------------------

def single_to_list(conf, dct=SINGLE_TO_LIST):
    """Recursively convert single entries to lists."""
    for field in dct:
        if isinstance(dct[field], dict):
            conf[field] = single_to_list(conf[field], dct[field])

        elif field in conf and not isinstance(conf[field], list):
            conf[field] = [conf[field]]

    return conf


def make_dir(dir_path):
    """Check if directory exists, and if not, make it."""
    message = "Output directory " + dir_path
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)
        message += " (created)"
    logging.error(message)
