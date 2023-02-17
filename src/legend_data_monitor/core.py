from . import utils, subsystem, plotting

import logging
import os
import json

log = logging.getLogger(__name__)
# set up logging to console
console = logging.StreamHandler()
console.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s:  %(message)s")
console.setFormatter(formatter)
logging.getLogger("").addHandler(console)

def control_plots(user_config_path: str):

    # -------------------------------------------------------------------------
    # Read user settings
    # -------------------------------------------------------------------------

    with open(user_config_path) as f:
        config = json.load(f)

    # check validity
    valid = utils.check_plot_settings(config)
    if not valid:
        return  

    # create output folders for plots
    output_paths = utils.make_output_paths(config)
    if not output_paths:
        return

    # -------------------------------------------------------------------------
    # Define PDF file basename
    # -------------------------------------------------------------------------
    
    # Format: l200_p02_phy_timestamp1_timestamp2
    # later subsystem name will be added e.g. l200-p02-phy-timestamp1_timestamp2_geds.pdf

    try:
        data_types = [ config['dataset']['type'] ] if isinstance(config['dataset']['type'], str) else config['dataset']['type']
        pdf_basename = "{}_{}_{}_".format(
                config['dataset']['experiment'],
                config['dataset']['period'],
                '_'.join(data_types)
        )
    except:
        # means something about dataset is wrong -> print Subsystem.get_data doc
        logging.error("Something is missing or wrong in your 'dataset' field of the config. You can see the format here under 'dataset=':")
        print(subsystem.Subsystem.get_data.__doc__)
        return

    user_time_range = utils.get_dataloader_timerange(dataset=config['dataset'])
    # will be returned as None if something is wrong, and print an error message
    if not user_time_range:
        return

    name_time = [ user_time_range['start'], user_time_range['end'] ] if 'start' in user_time_range else user_time_range        
    pdf_basename += '-'.join(name_time)
 

    # --- define PDF base path
    # path/to/output/pdf_files/par_vs_time/l200-p02-...
    # ! currently using par_vs_time path even though saving full subsystem plots there
    pdf_basepath = os.path.join(output_paths['pdf_files'], 'par_vs_time', pdf_basename)

    # -------------------------------------------------------------------------
    # Get pulser first - needed to flag pulser events
    # -------------------------------------------------------------------------
    
    # put it in a dict, so that later, if pulser is also wanted to be plotted, we don't have to load it twice
    subsystems = { 'pulser': subsystem.Subsystem('pulser', setup=config['dataset']) }
    # get list of all parameters needed for all requested plots, if any
    parameters = utils.get_all_plot_parameters('pulser', config)
    # get data for these parameters and time range given in the dataset
    # (if no parameters given to plot, baseline and wfmax will always be loaded to flag pulser events anyway)
    subsystems['pulser'].get_data(parameters, dataset=config['dataset'])
    
    # -------------------------------------------------------------------------

    # What subsystems do we want to plot?
    subsystems_to_plot = list(config['subsystems'].keys())

    for system in subsystems_to_plot:
        # -------------------------------------------------------------------------
        # set up subsystem
        # -------------------------------------------------------------------------

        # set up if wasn't already set up (meaning, not pulser, previously already set up)
        if not system in subsystems:
            # Subsystem: knows its channel map & sofware status (On/Off channels)
            subsystems[system] = subsystem.Subsystem(system, setup=config['dataset'])
            # get list of parameters needed for all requested plots, if any
            parameters = utils.get_all_plot_parameters(system, config)
            # get data for these parameters and dataset range
            subsystems[system].get_data(parameters, dataset=config['dataset'])
            print(subsystems[system].data)
            # flag pulser events for future parameter data selection
            subsystems[system].flag_pulser_events(subsystems['pulser'])

        # -------------------------------------------------------------------------
        # make subsystem plots
        # -------------------------------------------------------------------------

        # - currently one PDF file per subsystem, even though path to par_vs_time
        pdf_path = pdf_basepath + '_' + subsystems[system].type + '.pdf'
 
        plotting.make_subsystem_plots(subsystems[system], config['subsystems'][system], pdf_path)
    
    print('D O N E')