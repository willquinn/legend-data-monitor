import analysis
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

j_config, j_par, j_plot = analysis.read_json_files()
spms_name_dict = j_plot[0]
geds_name_dict = j_plot[1]

# geds (need an automatic loading of detectors)
S1 = ["ch024", "ch025", "ch026", "ch036", ""]
S2 = ["ch027", "ch028", "ch029", "ch030", "ch031"]
S3 = ["ch032", "ch033", "ch034", "ch035", ""]
S4 = ["ch037", "ch038", "ch039", "ch040", ""]
"""
Comment: strings need to be of the same length; if no detectors
         are present, then '' is sufficient (but must be put!)
"""

# spms (need an automatic loading of detectors)
spms_S1 = ["0", "10", "20"]
spms_S2 = ["1", "11", "21"]
spms_S3 = ["2", "12", "22"]
spms_S4 = ["3", "13", "23"]
spms_S5 = ["4", "14", "24"]
spms_S6 = ["5", "15", "25"]
spms_S7 = ["6", "16", "26"]
spms_S8 = ["7", "17", "27"]
spms_S9 = ["8", "18", "28"]
spms_S10 = ["9", "19", "29"]


def check_det(cmap_dict, det_type):
    """
    Description
    -----------
    It creates a heatmap for germanium detectors.

    Parameters
    ----------
    cmap_dict : dictionary
                Dictionary with info for building the heatmap
    det_type  : string
                Type of detector (geds or spms)
    """

    # to check if all detectors are inside it, otherwise put =white
    # (future: load channels from maps)
    if det_type == "spms":
        all_det = [str(i) for i in range(0, 30, 1)]
    if det_type == "geds":
        all_det = ["ch0" + str(i) for i in range(26, 40, 1)]

    for det in all_det:
        if det not in cmap_dict:
            cmap_dict[det] = 3

    return cmap_dict


def geds_map(cmap_dict, map_path, pdf):
    """
    Description
    -----------
    It creates a heatmap for germanium detectors.

    Parameters
    ----------
    cmap_dict : dictionary
                Dictionary with info for building the heatmap
    map_path  : string
                Path where to save ouput heatmaps
    """

    cmap_dict = check_det(cmap_dict, "geds")
    cmap_dict[""] = 4

    df = pd.DataFrame(data=list(zip(S1, S2, S3, S4)))

    labels = df.replace(geds_name_dict)
    dataframe = df.replace(cmap_dict)

    x_axis_labels = ["String 1", "String 2", "String 3", "String 4"]
    y_axis_labels = ["", "", "", "", ""]

    fig = plt.figure(num=None, figsize=(14, 10), dpi=80, facecolor="w", edgecolor="k")
    sns.set(font_scale=1.5)

    custom_cmap = ["#318CE7", "#CC0000", "#F7AB60", "#D0D0D0", "#FFFFFF"]
    status_map = sns.heatmap(
        data=dataframe,
        annot=labels,
        vmin=0,
        vmax=len(custom_cmap),
        yticklabels=y_axis_labels,
        xticklabels=x_axis_labels,
        fmt="s",
        cmap=custom_cmap,
        cbar=True,
        linewidths=1,
        linecolor="white",
        square=True,
        rasterized=True,
    )

    """
    status_map.add_patch(Rectangle((0,0), 1, 1, fill=False, edgecolor='#3F5AC9', lw=3, clip_on=False))
    status_map.add_patch(Rectangle((0,1), 1, 1, fill=False, edgecolor='#3F5AC9', lw=3, clip_on=False))
    status_map.add_patch(Rectangle((0,2), 1, 1, fill=False, edgecolor='#3F5AC9', lw=3, clip_on=False))
    status_map.add_patch(Rectangle((1,1), 1, 1, fill=False, edgecolor='#000000', lw=3, clip_on=False))
    status_map.add_patch(Rectangle((1,2), 1, 1, fill=False, edgecolor='#FFD721', lw=3, clip_on=False))
    status_map.add_patch(Rectangle((1,3), 1, 1, fill=False, edgecolor='#DD3CF7', lw=3, clip_on=False))
    """

    colorbar = status_map.collections[0].colorbar
    colorbar.set_ticks([1 / 2, 3 / 2, 5 / 2, 7 / 2, 0])
    colorbar.set_ticklabels(["OK", "X", "AC", "OFF", ""])

    plt.tick_params(
        axis="both",
        which="major",
        labelsize=20,
        labelbottom=False,
        bottom=False,
        top=False,
        labeltop=True,
    )
    plt.title("geds")
    pdf.savefig(bbox_inches="tight")
    plt.close()

    return


def spms_map(cmap_dict, map_path, pdf):
    """
    Description
    -----------
    It creates a heatmap for spms detectors.

    Parameters
    ----------
    cmap_dict : dictionary
                Dictionary with info for building the heatmap
    map_path  : string
                Path where to save ouput heatmaps
    """

    cmap_dict = check_det(cmap_dict, "spms")

    df = pd.DataFrame(
        data=list(
            zip(
                spms_S1,
                spms_S2,
                spms_S3,
                spms_S4,
                spms_S5,
                spms_S6,
                spms_S7,
                spms_S8,
                spms_S9,
                spms_S10,
            )
        )
    )

    labels = df.replace(spms_name_dict)
    dataframe = df.replace(cmap_dict)

    x_axis_labels = ["", "", "", "", "", "", "", "", "", ""]
    y_axis_labels = ["", "", ""]

    fig = plt.figure(num=None, figsize=(14, 10), dpi=80, facecolor="w", edgecolor="k")
    sns.set(font_scale=1.5)

    #                blue        red        grey       white
    custom_cmap = ["#318CE7", "#CC0000", "#A9A9A9"]
    status_map = sns.heatmap(
        data=dataframe,
        annot=labels,
        vmin=0,
        vmax=len(custom_cmap),
        yticklabels=y_axis_labels,
        xticklabels=x_axis_labels,
        fmt="s",
        cmap=custom_cmap,
        cbar=True,
        linewidths=10,
        linecolor="white",
        square=False,
    )

    colorbar = status_map.collections[0].colorbar
    colorbar.set_ticks([1 / 2, 3 / 2, 5 / 2, 7 / 2])
    colorbar.set_ticklabels(["OK", "X", "OFF"])

    plt.tick_params(
        axis="both",
        which="major",
        labelsize=20,
        labelbottom=False,
        bottom=False,
        top=False,
        labeltop=True,
    )
    plt.title("spms")
    pdf.savefig(bbox_inches="tight")
    plt.close()

    return
