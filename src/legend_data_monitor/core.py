from . import config, dataset, subsystem, plotting

import logging
import os

log = logging.getLogger(__name__)
# set up logging to console
console = logging.StreamHandler()
console.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s:  %(message)s")
console.setFormatter(formatter)
logging.getLogger("").addHandler(console)

def control_plots(user_config):

    ## Read user settings
    # - read user config
    # - convert single inputs to lists for convenience e.g. "runs": 27 -> "runs": [27]
    # - check settings validity
    # - construct plot output paths and create if needed
    # - mark code start time
    # - read channel map from legendmeta
    conf = config.config_build(user_config)
    
    ## Load dataset based on user provided config
    # - construct paths to data
    # - obtain name of QC flag column for given version
    # - obtain time range based on user given selection type and resulting one based on dsp file keys (may be narrower)
    dset = dataset.Dataset(conf)    

    ## -------------------------------------------------------------------------

    ## define PDF file basename
    # e.g. l200-p02-phy-timestamp1_timestamp2
    # later subsystem name will be added e.g. l200-p02-phy-timestamp1_timestamp2_geds.pdf
    pdf_basename = "{}-{}-{}-{}_{}".format(
            dset.exp,
            dset.period,
            '_'.join(dset.type),
            dset.user_time_range['start'],
            dset.user_time_range['end']
    )       

    ## define PDF base path
    # path/to/par_vs_time/l200-p02-...
    # ! currently using par_vs_time path even though saving full subsystem plots there
    pdf_basepath = os.path.join(conf.output_paths['pdf_files'], 'par_vs_time', pdf_basename)

    ## -------------------------------------------------------------------------

    ## Get pulser first - needed to flag pulser events
    # - put it in a dict, so that later, if pulser is also wanted to be plotted, we don't have to load it twice
    subsystems = { 'pulser': subsystem.Subsystem(conf, 'pulser') }
    # - get data for time range given in the dataset
    subsystems['pulser'].get_data(dset)
    
    ## -------------------------------------------------------------------------

    # What subsystems do we want to plot?
    subsys_to_plot = list(conf.subsystems.keys())

    for syst in subsys_to_plot:
        ## set up subsystem if wasn't already set up (meaning, not pulser)
        # - channel map
        # - removed channels
        # - parameters of interest
        # - plot settings for each parameter
        if not syst in subsystems:
            subsystems[syst] = subsystem.Subsystem(conf, syst)
            subsystems[syst].get_data(dset)
        
            ## flag pulser events for future parameter data selection
            subsystems[syst].flag_pulser_events(subsystems['pulser'])
     
        ## make subsystem plots
        # - currently one PDF file per subsystem, even though path to par_vs_time
        pdf_path = pdf_basepath + '_' + subsystems[syst].type + '.pdf'
 
        plotting.make_subsystem_plots(subsystems[syst], pdf_path)
    
    print('D O N E')