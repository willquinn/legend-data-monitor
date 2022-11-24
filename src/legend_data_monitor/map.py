from __future__ import annotations

import pickle as pkl

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from . import analysis, timecut

j_config, j_par, j_plot = analysis.read_json_files()
exp = j_config[0]["exp"]
period = j_config[1]
run = j_config[2]
datatype = j_config[3]


def pkl_name(time_cut: list[str], parameter: str, start_code: str):
    """
    Define the name of output pkl file.

    Parameters
    ----------
    time_cut
                     List with info about time cuts
    parameter
                     Parameter to plot
    start_code
                     Starting time of the code
    """
    run_name = ""
    if isinstance(run, str):
        run_name = run
    elif isinstance(run, list):
        for r in run:
            run_name = run_name + r + "-"
        run_name = run_name[:-1]
    if run:
        if len(time_cut) != 0:
            start, end = timecut.time_dates(time_cut, start_code)
            pkl_filename = (
                exp
                + "-"
                + period
                + "-"
                + run
                + "-"
                + datatype
                + "-"
                + start
                + "_"
                + end
                + "-"
                + parameter
            )
        else:
            pkl_filename = (
                exp + "-" + period + "-" + run_name + "-" + datatype + "-" + parameter
            )
    else:
        if len(time_cut) != 0:
            start, end = timecut.time_dates(time_cut, start_code)
            pkl_filename = (
                exp
                + "-"
                + period
                + "-"
                + datatype
                + "-"
                + start
                + "_"
                + end
                + "-"
                + parameter
            )
        else:
            pkl_filename = exp + "-" + period + "-" + datatype + "-" + parameter

    return pkl_filename


def place_dets(det_dict: dict, string_entries: list[str]):
    """
    Fill strings keeping in mind the real position of detectors.

    Parameters
    ----------
    det_dict
                     Contains info (crate, card, ch_orca) for geds/spms/other
    string_entries
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


def check_det(cmap_dict: dict, det_dict: dict):
    """
    Check if all detectors of det_dict are present in cmap_dict. If not, they are added with status=OFF.

    Parameters
    ----------
    det_dict
                Contains info (crate, card, ch_orca) for geds/spms/other
    cmap_dict
                Dictionary with info for building the heatmap
    """
    for k1 in det_dict.keys():
        if k1 not in cmap_dict:
            cmap_dict[k1] = 3

    return cmap_dict


def geds_map(
    parameter: str,
    det_dict: dict,
    string_entries: list,
    string_name: list[str],
    cmap_dict: dict,
    time_cut: list[str],
    map_path: str,
    start_code: str,
    pdf,
):
    """
    Create a heatmap for germanium detectors.

    Parameters
    ----------
    parameter
                     Parameter to plot
    det_dict
                     Contains info (crate, card, ch_orca) for geds/spms/other
    string_entries
                     List of strings
    string_name
                     List of name of strings
    cmap_dict
                     Dictionary with info for building the heatmap
    time_cut
                     List with info about time cuts
    map_path
                     Path where to save output heatmaps
    start_code
                     Starting time of the code
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

    x_axis_labels = [f"S{no}" for no in string_name]
    y_axis_labels = ["" for idx in range(0, len(df))]

    fig = plt.figure(num=None, figsize=(8, 12), dpi=80, facecolor="w", edgecolor="k")
    sns.set(font_scale=1.2)

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
    plt.title(f"geds ({parameter})")

    pkl_file = pkl_name(time_cut, parameter, start_code)
    pkl.dump(fig, open(f"out/pkl-files/heatmaps/{pkl_file}.pkl", "wb"))
    pdf.savefig(bbox_inches="tight")
    plt.close()

    return


def spms_map(
    parameter: str,
    det_dict: dict,
    string_entries: list,
    string_name: list[str],
    cmap_dict: dict,
    time_cut: list[str],
    map_path: str,
    start_code: str,
    pdf,
):
    """
    Create a heatmap for spms detectors.

    Parameters
    ----------
    parameter
                     Parameter to plot
    det_dict
                     Contains info (crate, card, ch_orca) for geds/spms/other
    string_entries
                     List of strings
    string_name
                     List of name of strings
    cmap_dict
                     Dictionary with info for building the heatmap
    time_cut
                     List with info about time cuts
    map_path
                     Path where to save output heatmaps
    start_code
                     Starting time of the code
    """
    cmap_dict = check_det(cmap_dict, det_dict)

    df_ob = pd.DataFrame(data=list(string_entries[:2]))
    df_ib = pd.DataFrame(data=list(string_entries[2:]))

    spms_ob_dict = {}
    spms_ib_dict = {}

    # If you want to put SiPM name in spms label
    for k1, v1 in det_dict.items():
        for k2, v2 in v1.items():
            if k2 == "det":
                det_name = v2
            if k2 == "daq":
                for k3, v3 in v2.items():
                    if k3 == "card":
                        if k1 in string_entries[0] or k1 in string_entries[1]:
                            spms_ob_dict[k1] = f"\n{det_name}\n{v3}-"
                        else:
                            spms_ib_dict[k1] = f"\n{det_name}\n{v3}-"
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
    fig_ob = plt.figure(num=None, figsize=(38, 5), dpi=80, facecolor="w", edgecolor="k")
    sns.set(font_scale=1.2)

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
        square=True,
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
    plt.title(f"spms - outer barrel ({parameter})")

    pkl_file = pkl_name(time_cut, parameter, start_code)
    pkl.dump(fig_ob, open(f"out/pkl-files/heatmaps/{pkl_file}-OB.pkl", "wb"))
    pdf.savefig(bbox_inches="tight")

    # inner barrel
    fig_ib = plt.figure(num=None, figsize=(18, 5), dpi=80, facecolor="w", edgecolor="k")
    sns.set(font_scale=1.2)

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
        square=True,
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
    plt.title(f"spms - inner barrel ({parameter})")
    pkl.dump(fig_ib, open(f"out/pkl-files/heatmaps/{pkl_file}-IB.pkl", "wb"))
    pdf.savefig(bbox_inches="tight")

    plt.close()

    return
