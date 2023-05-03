from . import utils


def cut_k_lines(data):
    """Keep only events that are in the K lines region (i.e., in (1430;1575) keV)."""
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


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# QUALITY CUTS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def is_valid_0vbb(data):
    """Keep only events that are valid for 0vbb analysis."""
    return data[data["is_valid_0vbb"] == 1]


def is_valid_cal(data):
    return data[data["is_valid_cal"] == 1]


def is_negative(data):
    return data[data["is_negative"] == 1]


def is_saturated(data):
    return data[data["is_saturated"] == 1]


def is_valid_rt(data):
    return data[data["is_valid_rt"] == 1]


def is_valid_t0(data):
    return data[data["is_valid_t0"] == 1]


def is_valid_tmax(data):
    return data[data["is_valid_tmax"] == 1]


def is_valid_dteff(data):
    return data[data["is_valid_dteff"] == 1]


def is_valid_ediff(data):
    return data[data["is_valid_ediff"] == 1]


def is_valid_ediff(data):
    return data[data["is_valid_ediff"] == 1]


def is_valid_efrac(data):
    return data[data["is_valid_efrac"] == 1]


def is_negative_crosstalk(data):
    return data[data["is_negative_crosstalk"] == 1]


def is_discharge(data):
    return data[data["is_discharge"] == 1]


def is_neg_energy(data):
    return data[data["is_neg_energy"] == 1]


def is_valid_tail(data):
    return data[data["is_valid_tail"] == 1]


def is_downgoing_baseline(data):
    return data[data["is_downgoing_baseline"] == 1]


def is_upgoing_baseline(data):
    return data[data["is_upgoing_baseline"] == 1]


def is_upgoing_baseline(data):
    return data[data["is_upgoing_baseline"] == 1]


def is_noise_burst(data):
    return data[data["is_noise_burst"] == 1]


def is_valid_baseline(data):
    return data[data["is_valid_baseline"] == 1]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ANTI - QUALITY CUTS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def is_not_valid_0vbb(data):
    """Keep only events that are valid for 0vbb analysis."""
    return data[data["is_valid_0vbb"] == 0]


def is_not_valid_cal(data):
    return data[data["is_valid_cal"] == 0]


def is_not_negative(data):
    return data[data["is_negative"] == 0]


def is_not_saturated(data):
    return data[data["is_saturated"] == 0]


def is_not_valid_rt(data):
    return data[data["is_valid_rt"] == 0]


def is_not_valid_t0(data):
    return data[data["is_valid_t0"] == 0]


def is_not_valid_tmax(data):
    return data[data["is_valid_tmax"] == 0]


def is_not_valid_dteff(data):
    return data[data["is_valid_dteff"] == 0]


def is_not_valid_ediff(data):
    return data[data["is_valid_ediff"] == 0]


def is_not_valid_ediff(data):
    return data[data["is_valid_ediff"] == 0]


def is_not_valid_efrac(data):
    return data[data["is_valid_efrac"] == 0]


def is_not_negative_crosstalk(data):
    return data[data["is_negative_crosstalk"] == 0]


def is_not_discharge(data):
    return data[data["is_discharge"] == 0]


def is_not_neg_energy(data):
    return data[data["is_neg_energy"] == 0]


def is_not_valid_tail(data):
    return data[data["is_valid_tail"] == 0]


def is_not_downgoing_baseline(data):
    return data[data["is_downgoing_baseline"] == 0]


def is_not_upgoing_baseline(data):
    return data[data["is_upgoing_baseline"] == 0]


def is_not_upgoing_baseline(data):
    return data[data["is_upgoing_baseline"] == 0]


def is_not_noise_burst(data):
    return data[data["is_noise_burst"] == 0]


def is_not_valid_baseline(data):
    return data[data["is_valid_baseline"] == 0]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Apply cut
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def apply_cut(data, cut):
    cut_function = CUTS[cut]
    utils.logger.info("...... applying cut: " + cut)
    return cut_function(data)


# temporary list - all QCs will be merged in a more clean way
CUTS = {
    "K lines": cut_k_lines,
    "is_valid_0vbb": is_valid_0vbb,
    "is_valid_cal": is_valid_cal,
    "is_negative": is_negative,
    "is_saturated": is_saturated,
    "is_valid_rt": is_valid_rt,
    "is_valid_t0": is_valid_t0,
    "is_valid_tmax": is_valid_tmax,
    "is_valid_dteff": is_valid_dteff,
    "is_valid_ediff": is_valid_ediff,
    "is_valid_efrac": is_valid_efrac,
    "is_negative_crosstalk": is_negative_crosstalk,
    "is_discharge": is_discharge,
    "is_neg_energy": is_neg_energy,
    "is_valid_tail": is_valid_tail,
    "is_downgoing_baseline": is_downgoing_baseline,
    "is_upgoing_baseline": is_upgoing_baseline,
    "is_noise_burst": is_noise_burst,
    "is_valid_baseline": is_valid_baseline,
    "~is_valid_0vbb": is_not_valid_0vbb,
    "~is_valid_cal": is_not_valid_cal,
    "~is_negative": is_not_negative,
    "~is_saturated": is_not_saturated,
    "~is_valid_rt": is_not_valid_rt,
    "~is_valid_t0": is_not_valid_t0,
    "~is_valid_tmax": is_not_valid_tmax,
    "~is_valid_dteff": is_not_valid_dteff,
    "~is_valid_ediff": is_not_valid_ediff,
    "~is_valid_efrac": is_not_valid_efrac,
    "~is_negative_crosstalk": is_not_negative_crosstalk,
    "~is_discharge": is_not_discharge,
    "~is_neg_energy": is_not_neg_energy,
    "~is_valid_tail": is_not_valid_tail,
    "~is_downgoing_baseline": is_not_downgoing_baseline,
    "~is_upgoing_baseline": is_not_upgoing_baseline,
    "~is_noise_burst": is_not_noise_burst,
    "~is_valid_baseline": is_not_valid_baseline,
}
