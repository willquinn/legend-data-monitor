from . import utils

def apply_cut(data, cut):
    utils.logger.info("...... applying cut: " + cut)

    cut_value = 1
    # check if the cut has "not" in it
    if cut[0] == "~":
        cut_value = 0
        cut = cut[1:]

    return data[data[cut] == cut_value]