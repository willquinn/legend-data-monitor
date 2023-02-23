import json

from . import plotting, subsystem, utils


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

    # -------------------------------------------------------------------------
    # Define PDF file basename
    # -------------------------------------------------------------------------

    # Format: l200-p02-{run}-{data_type} or l200-p02-timestamp1_timestamp2-{data_type}
    # One file for all subsystems

    try:
        data_types = (
            [config["dataset"]["type"]]
            if isinstance(config["dataset"]["type"], str)
            else config["dataset"]["type"]
        )

        plt_basename = "{}-{}-".format(
            config["dataset"]["experiment"].lower(),
            config["dataset"]["period"],
        )
    except (KeyError, TypeError):
        # means something about dataset is wrong -> print Subsystem.get_data doc
        utils.logger.error(
            "\033[91mSomething is missing or wrong in your 'dataset' field of the config. You can see the format here under 'dataset=':\033[0m"
        )
        utils.logger.info("\033[91m%s\033[0m", subsystem.Subsystem.get_data.__doc__)
        return

    user_time_range = utils.get_query_timerange(dataset=config["dataset"])
    # will be returned as None if something is wrong, and print an error message
    if not user_time_range:
        return

    # create output folders for plots
    output_paths = utils.make_output_paths(config, user_time_range)
    if not output_paths:
        return

    # we don't care here about the time keyword timestamp/run -> just get the value
    plt_basename += utils.get_time_name(user_time_range)
    plt_path = output_paths + plt_basename
    plt_path += "-{}".format("_".join(data_types))

    # -------------------------------------------------------------------------
    # Get pulser first - needed to flag pulser events
    # -------------------------------------------------------------------------

    # put it in a dict, so that later, if pulser is also wanted to be plotted, we don't have to load it twice
    subsystems = {"pulser": subsystem.Subsystem("pulser", dataset=config["dataset"])}
    # get list of all parameters needed for all requested plots, if any
    parameters = utils.get_all_plot_parameters("pulser", config)
    # get data for these parameters and time range given in the dataset
    # (if no parameters given to plot, baseline and wfmax will always be loaded to flag pulser events anyway)
    subsystems["pulser"].get_data(parameters)
    utils.logger.debug(subsystems["pulser"].data)

    # -------------------------------------------------------------------------

    # What subsystems do we want to plot?
    subsystems_to_plot = list(config["subsystems"].keys())

    for system in subsystems_to_plot:
        # -------------------------------------------------------------------------
        # set up subsystem
        # -------------------------------------------------------------------------

        # set up if wasn't already set up (meaning, not pulser, previously already set up)
        if system not in subsystems:
            # Subsystem: knows its channel map & software status (On/Off channels)
            subsystems[system] = subsystem.Subsystem(system, dataset=config["dataset"])
            # get list of parameters needed for all requested plots, if any
            parameters = utils.get_all_plot_parameters(system, config)
            # get data for these parameters and dataset range
            subsystems[system].get_data(parameters)
            utils.logger.debug(subsystems[system].data)
            # flag pulser events for future parameter data selection
            subsystems[system].flag_pulser_events(subsystems["pulser"])

        # -------------------------------------------------------------------------
        # make subsystem plots
        # -------------------------------------------------------------------------

        # - set up log file for each system
        # file handler
        file_handler = utils.logging.FileHandler(plt_path + "_" + system + ".log")
        file_handler.setLevel(utils.logging.DEBUG)
        # add to logger
        utils.logger.addHandler(file_handler)

        plotting.make_subsystem_plots(
            subsystems[system], config["subsystems"][system], plt_path
        )

    utils.logger.info("D O N E")
