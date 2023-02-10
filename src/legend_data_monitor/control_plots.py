from . import config, dataset, subsystem, plotting

import sys

# import logging

def control_plots(user_config):

    # Read user settings
    # - read all json
    # - mark code start time
    # - read channel map as dict (for now from path)
    conf = config.Config(user_config)

    # Note: is a nested attribute dict so that one can do dct.a.b instead of dct['a']['b']
    # simplifies stuff but maybe not needed if takes too much memory
    
    # Load dataset based on user provided config
    # - construct paths to data
    # - obtain name of QC flag column for given version
    # - obtain time range based on user given selection type and resulting one based on dsp file keys (may be narrower)
    dset = dataset.Dataset(conf)    

    # Get plot settings from user provided config + calculated time range
    # - sampling for averages
    # - output paths
    # - parameter plot settings (phy/puls/all to plot, which plot style, plot absolute or variation in % etc.)
    plot_settings = config.PlotSettings(conf, dset)

    # Get pulser first - needed to flag pulser events
    # - get data for time range given in the dataset
    # - put it in a dict, so that later, if pulser is also wanted to be plotted, we don't have to load it twice
    subsystems = { 'pulser': subsystem.Subsystem(conf, 'pulser') }
    subsystems['pulser'].get_data(dset)
    
    # What subsystems do we want to plot?
    subsys_to_plot = list(conf.subsystems.keys())

    for syst in subsys_to_plot:
        # set up subsystem
        # - channel map
        # - removed channels
        # - parameters of interest
        if not syst in subsystems:
            subsystems[syst] = subsystem.Subsystem(conf, syst)
            subsystems[syst].get_data(dset)
        
        # flag pulser events for future parameter data selection
        # ?? do this at get_data() level, constructing "own pulser" inside subsystem?
        subsystems[syst].flag_pulser_events(subsystems['pulser'])

        # make subsystem plots
        # ?? one plot for all? one plot per subsystem? -> currently per subsystem
        # ToDo: K_lines
        plotting.make_subsystem_plots(subsystems[syst], plot_settings)
    
    print('D O N E')


if __name__ == '__main__':
    control_plots(sys.argv[1])