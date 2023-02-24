from . import utils

def cut_k_lines(data):
    energy = utils.SPECIAL_PARAMETERS['K lines'][0]
    return data[ (data[energy] > 1430) & (data[energy] < 1575)]
    
def apply_cut(data, cut):
    cut_function = CUTS[cut]
    utils.logger.info("...... applying cut: " + cut)
    return cut_function(data)


CUTS = {
    "K lines": cut_k_lines
}
