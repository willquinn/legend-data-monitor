from . import utils


def cut_k_lines(data):
    # if we are not plotting "K_events", then there is still the case were the user might want to plot a given parameter (eg. baseline)
    # in correspondence ok K line entries. To do this, we go and look at the corresponding energy column. In particular, the energy is decided a priori in 'special-parameters.json'
    if utils.SPECIAL_PARAMETERS["K_events"][0] in data.columns:
        energy = utils.SPECIAL_PARAMETERS["K_events"][0]
    # when we are plotting "K_events", then we already re-named the energy column with the parameter's name (due to how the code was built)
    if "K_events" in data.columns:
        energy = "K_events"
    # if something is not properly working, exit from the code
    else:
        utils.logger.error(
            "\033[91mThe cut over K lines entries is not working. Check again your subsystem options!\033[0m"
        )
        exit()

    return data[(data[energy] > 1430) & (data[energy] < 1575)]


def apply_cut(data, cut):
    cut_function = CUTS[cut]
    utils.logger.info("...... applying cut: " + cut)
    return cut_function(data)


CUTS = {"K lines": cut_k_lines}
