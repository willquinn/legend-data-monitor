import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def place_dets(det_dict, string_entries):
    """
    Fill strings keeping in mind the real position of detectors.

    Parameters
    ----------
    det_dict       : dictionary
                     Contains info (crate, card, ch_orca) for geds/spms/other
    string_entries : list
                     List of strings
    """
    new_string_entries = []

    # get the meaximum length of the whole system
    max_length = 1
    for v1 in det_dict.values():
        for k2, v2 in v1.items():
            if k2 == "string":
                for k3, v3 in v2.items():
                    if k3 == "position" and v3 != "--":
                        if int(v3) > max_length:
                            max_length = int(v3)

    # let's order detectors (and add gaps)
    for entry in range(0, len(string_entries)):
        string = []
        idx = 1
        j = 0
        while idx <= max_length and j < len(string_entries[entry]):
            det = string_entries[entry][j]
            pos = det_dict[string_entries[entry][j]]["string"]["position"]
            if str(idx) == pos:
                string.append(det)
                j += 1
            else:
                string.append("")
            idx += 1

        while len(string) < max_length:
            string.append("")

        new_string_entries.append(string)

    return new_string_entries


def check_det(cmap_dict, det_dict):
    """
    Check if all detectors of det_dict are present in cmap_dict. If not, they are added with status=OFF.

    Parameters
    ----------
    det_dict  : dictionary
                Contains info (crate, card, ch_orca) for geds/spms/other
    cmap_dict : dictionary
                Dictionary with info for building the heatmap
    """
    for k1 in det_dict.keys():
        if k1 not in cmap_dict:
            cmap_dict[k1] = 3

    return cmap_dict


def geds_map(det_dict, string_entries, string_name, cmap_dict, map_path, pdf):
    """
    Create a heatmap for germanium detectors.

    Parameters
    ----------
    det_dict       : dictionary
                     Contains info (crate, card, ch_orca) for geds/spms/other
    string_entries : list
                     List of strings
    string_name    : list
                     List of name of strings
    cmap_dict      : dictionary
                     Dictionary with info for building the heatmap
    map_path       : string
                     Path where to save output heatmaps
    """
    string_entries = place_dets(det_dict, string_entries)
    df = pd.DataFrame(data=list(string_entries))
    df = df.T

    geds_name_dict = {}
    for k1, v1 in det_dict.items():
        for k2, v2 in v1.items():
            if k2 == "det":
                geds_name_dict[k1] = v2 + f"\n{k1}\n"
            if k2 == "daq":
                for k3, v3 in v2.items():
                    if k3 == "card":
                        geds_name_dict[k1] += f"{v3}-"
                    if k3 == "ch_orca":
                        geds_name_dict[k1] += f"{v3}"

    labels = df.replace(geds_name_dict)
    # replace None entries with empty strings
    mask = labels.applymap(lambda x: x is None)
    cols = labels.columns[(mask).any()]
    for col in labels[cols]:
        labels.loc[mask[col], col] = ""

    # check if cmap_dict contains all det that are in det_dict
    cmap_dict = check_det(cmap_dict, det_dict)

    dataframe = df.replace(cmap_dict)
    dataframe = dataframe.replace(np.nan, 4)
    dataframe = dataframe.replace("", 4)

    x_axis_labels = [f"String {no}" for no in string_name]
    y_axis_labels = ["" for idx in range(0, len(df))]

    plt.figure(num=None, figsize=(17, 15), dpi=80, facecolor="w", edgecolor="k")
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


def spms_map(det_dict, string_entries, string_name, cmap_dict, map_path, pdf):
    """
    Create a heatmap for spms detectors.

    Parameters
    ----------
    det_dict       : dictionary
                     Contains info (crate, card, ch_orca) for geds/spms/other
    string_entries : list
                     List of strings
    string_name    : list
                     List of name of strings
    cmap_dict      : dictionary
                     Dictionary with info for building the heatmap
    map_path       : string
                     Path where to save output heatmaps
    """
    cmap_dict = check_det(cmap_dict, det_dict)

    df_ob = pd.DataFrame(data=list(string_entries[:2]))
    df_ib = pd.DataFrame(data=list(string_entries[2:]))

    spms_ob_dict = {}
    spms_ib_dict = {}
    for k1, v1 in det_dict.items():
        for k2, v2 in v1.items():
            if k2 == "daq":
                for k3, v3 in v2.items():
                    if k3 == "card":
                        if k1 in string_entries[0] or k1 in string_entries[1]:
                            spms_ob_dict[k1] = f"\n{k1}\n{v3}-"
                        else:
                            spms_ib_dict[k1] = f"\n{k1}\n{v3}-"
                    if k3 == "ch_orca":
                        if k1 in string_entries[0] or k1 in string_entries[1]:
                            spms_ob_dict[k1] += f"{v3}"
                        else:
                            spms_ib_dict[k1] += f"{v3}"

    labels_ob = df_ob.replace(spms_ob_dict)
    labels_ib = df_ib.replace(spms_ib_dict)
    # replace None entries with empty strings
    mask = labels_ob.applymap(lambda x: x is None)
    cols = labels_ob.columns[(mask).any()]
    for col in labels_ob[cols]:
        labels_ob.loc[mask[col], col] = ""
    mask = labels_ib.applymap(lambda x: x is None)
    cols = labels_ib.columns[(mask).any()]
    for col in labels_ib[cols]:
        labels_ib.loc[mask[col], col] = ""

    df_ob = df_ob.replace(cmap_dict)
    df_ob = df_ob.replace(np.nan, 4)
    df_ob = df_ob.replace("", 4)
    df_ib = df_ib.replace(cmap_dict)
    df_ib = df_ib.replace(np.nan, 4)
    df_ib = df_ib.replace("", 4)

    x_lab_ob = ["" for idx in range(0, df_ob.shape[1])]
    x_lab_ib = ["" for idx in range(0, df_ib.shape[1])]
    y_lab = ["top", "bottom"]

    # outer barrel
    plt.figure(num=None, figsize=(40, 10), dpi=80, facecolor="w", edgecolor="k")
    sns.set(font_scale=1.5)

    #                blue        red        grey       white
    custom_cmap = ["#318CE7", "#CC0000", "#A9A9A9"]
    status_map = sns.heatmap(
        data=df_ob,
        annot=labels_ob,
        vmin=0,
        vmax=len(custom_cmap),
        yticklabels=y_lab,
        xticklabels=x_lab_ob,
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
    plt.title("spms - outer barrel")
    pdf.savefig(bbox_inches="tight")

    # inner barrel
    plt.figure(num=None, figsize=(40, 10), dpi=80, facecolor="w", edgecolor="k")
    sns.set(font_scale=1.5)

    #                blue        red        grey       white
    custom_cmap = ["#318CE7", "#CC0000", "#A9A9A9"]
    status_map = sns.heatmap(
        data=df_ib,
        annot=labels_ib,
        vmin=0,
        vmax=len(custom_cmap),
        yticklabels=y_lab,
        xticklabels=x_lab_ib,
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
    plt.title("spms - inner barrel")
    pdf.savefig(bbox_inches="tight")

    plt.close()

    return
