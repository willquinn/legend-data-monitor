import os
import shelve

from pandas import DataFrame, concat

from . import utils

# -------------------------------------------------------------------------
# Saving related functions
# -------------------------------------------------------------------------


def save_df_and_info(df: DataFrame, plot_info: dict) -> dict:
    """Return a dictionary containing a dataframe for the parameter(s) under study for a given subsystem. The plotting info are saved too."""
    par_dict_content = {
        "df_" + plot_info["subsystem"]: df,  # saving dataframe
        "plot_info": plot_info,  # saving plotting info
    }

    return par_dict_content


def build_out_dict(
    plot_settings: list,
    par_dict_content: dict,
    out_dict: dict,
):
    """
    Build the output dictionary based on the input 'saving' option.

    Parameters
    ----------
    plot_settings
        Dictionary with settings for plotting. It contains the following keys: 'parameters', 'event_type', 'plot_structure', 'resampled', 'plot_style', 'variation', 'time_window', 'range', 'saving', 'plt_path'
    par_dict_content
        Dictionary containing, for a given parameter, the dataframe with data and a dictionary with info for plotting (e.g. plot style, title, units, labels, ...)
    out_dict
        Dictionary that is returned, containing the objects that need to be saved.
    """
    saving = plot_settings["saving"] if "saving" in plot_settings.keys() else None
    plt_path = plot_settings["plt_path"] if "plt_path" in plot_settings.keys() else None
    plot_info = par_dict_content["plot_info"]

    # we overwrite the object with a new one
    if saving == "overwrite":
        out_dict = build_dict(plot_settings, plot_info, par_dict_content, out_dict)

    # we retrieve the already existing shelve object, and we append new things to it; the parameter here is fixed
    if saving == "append":
        # the file does not exist, so we create it
        if not os.path.exists(plt_path + "-" + plot_info["subsystem"] + ".dat"):
            out_dict = build_dict(plot_settings, plot_info, par_dict_content, out_dict)

        # the file exists, so we are going to append data
        else:
            utils.logger.info(
                "There is already a file containing output data. Appending new data to it right now..."
            )
            # open already existing shelve file
            with shelve.open(plt_path + "-" + plot_info["subsystem"], "r") as shelf:
                old_dict = dict(shelf)

            # one parameter case
            if (
                isinstance(plot_settings["parameters"], list)
                and len(plot_settings["parameters"]) == 1
            ) or isinstance(plot_settings["parameters"], str):
                utils.logger.debug("... appending new data for the one-parameter case")
                out_dict = append_new_data(
                    plot_settings["parameters"][0]
                    if isinstance(plot_settings["parameters"], list)
                    else plot_settings["parameters"],
                    plot_settings,
                    plot_info,
                    old_dict,
                    par_dict_content,
                    plt_path,
                )
            # multi-parameters case
            if (
                isinstance(plot_settings["parameters"], list)
                and len(plot_settings["parameters"]) > 1
            ):
                utils.logger.debug(
                    "... appending new data for the multi-parameters case"
                )
                for param in plot_settings["parameters"]:
                    out_dict = append_new_data(
                        param,
                        plot_settings,
                        plot_info,
                        old_dict,
                        par_dict_content,
                        plt_path,
                    )

    return out_dict


def build_dict(
    plot_settings: list, plot_info: list, par_dict_content: dict, out_dict: dict
) -> dict:
    """Create a dictionary with the correct format for being saved in the final shelve object."""
    # get the parameters under study (can be one, can be more for 'par vs par' plot style)
    params = (
        plot_info["parameters"]
        if "parameters" in plot_info.keys()
        else plot_info["parameter"]
    )

    # one parameter
    if (isinstance(params, list) and len(params) == 1) or isinstance(params, str):
        utils.logger.debug(
            "... building the output dictionary in the one-parameter case"
        )
        if isinstance(params, list):
            param = params[0]
        if isinstance(params, str):
            param = params
        parameter = param.split("_var")[0] if "_var" in param else param
        par_dict_content["plot_info"] = get_param_info(
            param, par_dict_content["plot_info"]
        )
        # --- building up the output dictionary
        # event type key is already there
        if plot_settings["event_type"] in out_dict.keys():
            out_dict[plot_settings["event_type"]][parameter] = par_dict_content
        # event type key is NOT there
        else:
            # empty dictionary (not filled yet)
            if len(out_dict.keys()) == 0:
                out_dict = {plot_settings["event_type"]: {parameter: par_dict_content}}
            # the dictionary already contains something (but for another event type selection)
            else:
                out_dict[plot_settings["event_type"]] = {parameter: par_dict_content}
    # more than one parameter
    if isinstance(params, list) and len(params) > 1:
        utils.logger.debug(
            "... building the output dictionary in the multi-parameters case"
        )
        # we have to polish our dataframe and plot_info dictionary from other parameters...
        # --- original plot info
        # ::::::::::::::::::::::::::::::::::::::::::: example 'plot_info_all' :::::::::::::::::::::::::::::::::::::::::::
        # {'title': 'Plotting cuspEmax vs baseline', 'subsystem': 'geds', 'locname': 'string',
        #  'plot_style': 'par vs par', 'time_window': '10T', 'resampled': 'no', 'range': [None, None], 'std': False,
        #  'unit': {'cuspEmax_var': 'ADC', 'baseline_var': 'ADC'},
        #  'label': {'cuspEmax_var': 'cuspEmax', 'baseline_var': 'FPGA baseline'},
        #  'unit_label': {'cuspEmax_var': '%', 'baseline_var': '%'},
        #  'limits': {'cuspEmax_var': [-0.025, 0.025], 'baseline_var': [-5, 5]},
        #  'parameters': ['cuspEmax_var', 'baseline_var'],
        #  'param_mean': ['cuspEmax_mean', 'baseline_mean']}
        plot_info_all = par_dict_content["plot_info"]

        # --- original dataframes coming from the analysis
        df_all = par_dict_content["df_" + plot_info_all["subsystem"]]

        for param in params:
            parameter = param.split("_var")[0] if "_var" in param else param

            # --- cleaned plot info
            # ::::::::::::::::::::::::::::::::::::::::::: example 'plot_info_param' :::::::::::::::::::::::::::::::::::::::::::
            # {'title': 'Prove in corso', 'subsystem': 'geds', 'locname': 'string', 'plot_style': 'par vs par', 'time_window': '10T',
            #  'resampled': 'no', 'range': [None, None], 'std': False, 'unit': 'ADC', 'label': 'cuspEmax', 'unit_label': '%',
            #  'limits': [-0.025, 0.025], 'param_mean': 'cuspEmax_mean', 'parameter': 'cuspEmax_var', 'variation': True}
            plot_info_param = get_param_info(param, plot_info_all)

            # --- cleaned df
            df_param = get_param_df(parameter, df_all)

            # --- rebuilding the 'par_dict_content' for the parameter under study
            par_dict_content = save_df_and_info(df_param, plot_info_param)

            # --- building up the output dictionary
            # event type key is already there
            if plot_settings["event_type"] in out_dict.keys():
                out_dict[plot_settings["event_type"]][parameter] = par_dict_content
            # event type key is NOT there
            else:
                # empty dictionary (not filled yet)
                if len(out_dict.keys()) == 0:
                    out_dict = {
                        plot_settings["event_type"]: {parameter: par_dict_content}
                    }
                # the dictionary already contains something (but for another event type selection)
                else:
                    out_dict[plot_settings["event_type"]] = {
                        parameter: par_dict_content
                    }

    return out_dict


def append_new_data(
    param: str,
    plot_settings: dict,
    plot_info: dict,
    old_dict: dict,
    par_dict_content: dict,
    plt_path: str,
) -> dict:
    # the parameter is there
    parameter = param.split("_var")[0] if "_var" in param else param
    event_type = plot_settings["event_type"]

    if old_dict["monitoring"][event_type][parameter]:
        # get already present df
        old_df = old_dict["monitoring"][event_type][parameter][
            "df_" + plot_info["subsystem"]
        ].copy()
        old_df = check_level0(old_df)

        # get new df (plot_info object is the same as before, no need to get it and update it)
        new_df = par_dict_content["df_" + plot_info["subsystem"]].copy()
        # --- cleaned df
        new_df = get_param_df(parameter, new_df)

        # --- we have to copy the new means in the old one, otherwise we end up with two values (consider they have different lengths!)
        # Create a dictionary mapping 'channel' values to 'parameter_mean' values from new_df
        mean_dict = new_df.set_index("channel")[parameter + "_mean"].to_dict()
        # Update 'parameter_mean' values in old_df based on the dictionary mapping
        old_df[parameter + "_mean"] = (
            old_df["channel"].map(mean_dict).fillna(old_df[parameter + "_mean"])
        )

        # concatenate the two dfs (channels are no more grouped; not a problem)
        merged_df = DataFrame.empty
        merged_df = concat([old_df, new_df], ignore_index=True, axis=0)
        merged_df = merged_df.reset_index()
        merged_df = check_level0(merged_df)
        # re-order content in order of channels/timestamps
        merged_df = merged_df.sort_values(["channel", "datetime"])

        # redefine the dict containing the df and plot_info
        par_dict_content = {}
        par_dict_content["df_" + plot_info["subsystem"]] = merged_df
        par_dict_content["plot_info"] = plot_info

        # saved the merged df as usual (but for the given parameter)
        plot_info = get_param_info(param, plot_info)
        out_dict = build_dict(
            plot_settings, plot_info, par_dict_content, old_dict["monitoring"]
        )

        # we need to save it, otherwise when looping over the next parameter we lose the appended info for the already inspected parameter
        out_file = shelve.open(plt_path + "-" + plot_info["subsystem"])
        out_file["monitoring"] = out_dict
        out_file.close()

    return out_dict


def check_level0(dataframe: DataFrame) -> DataFrame:
    """Check if a dataframe contains the 'level_0' column. If so, remove it."""
    if "level_0" in dataframe.columns:
        return dataframe.drop(columns=["level_0"])
    else:
        return dataframe


def get_param_info(param: str, plot_info: dict) -> dict:
    """Subselect from 'plot_info' the plotting info for the specified parameter ```param```. This is needed for the multi-parameters case."""
    # get the *naked* parameter name and apply some if statements to avoid problems
    param = param + "_var" if "_var" not in param else param
    parameter = param.split("_var")[0]

    # but what if there is no % variation? We don't want any "_var" in our parameters!
    if (
        isinstance(plot_info["unit_label"], dict)
        and param not in plot_info["unit_label"].keys()
    ):
        if plot_info["unit_label"][parameter] != "%":
            param = parameter
    if isinstance(plot_info["unit_label"], str):
        if plot_info["unit_label"] != "%":
            param = parameter

    # re-shape the plot_info dictionary for the given parameter under study
    plot_info_param = plot_info.copy()
    plot_info_param["title"] = f"Plotting {param}"
    plot_info_param["unit"] = (
        plot_info["unit"][param]
        if isinstance(plot_info["unit"], dict)
        else plot_info["unit"]
    )
    plot_info_param["label"] = (
        plot_info["label"][param]
        if isinstance(plot_info["label"], dict)
        else plot_info["label"]
    )
    plot_info_param["unit_label"] = (
        plot_info["unit_label"][param]
        if isinstance(plot_info["unit_label"], dict)
        else plot_info["unit_label"]
    )
    plot_info_param["limits"] = (
        plot_info["limits"][param]
        if isinstance(plot_info["limits"], dict)
        else plot_info["limits"]
    )
    plot_info_param["K_events"] = (
        plot_info["K_events"][param]
        if isinstance(plot_info["K_events"], dict)
        else plot_info["K_events"]
    )
    plot_info_param["param_mean"] = parameter + "_mean"
    plot_info_param["variation"] = (
        True if plot_info_param["unit_label"] == "%" else False
    )
    plot_info_param["parameters"] = (
        param if plot_info_param["variation"] is True else parameter
    )

    # ... need to go back to the one parameter case ...
    # if "parameters" in plot_info_param.keys():
    #    plot_info_param["parameter"] = plot_info_param.pop("parameters")

    return plot_info_param


def get_param_df(parameter: str, df: DataFrame) -> DataFrame:
    """Subselect from 'df' only the dataframe columns that refer to a given parameter. The case of 'parameter' being a special parameter is carefully handled."""
    # list needed to better divide the parameters stored in the dataframe...
    keep_cols = [
        "index",
        "channel",
        "HV_card",
        "HV_channel",
        "cc4_channel",
        "cc4_id",
        "daq_card",
        "daq_crate",
        "datetime",
        "det_type",
        "flag_fc_bsln",
        "flag_muon",
        "flag_pulser",
        "location",
        "name",
        "position",
        "status",
    ]
    df_param = df.copy().drop(columns={x for x in df.columns if parameter not in x})
    df_cols = df.copy().drop(columns={x for x in df.columns if x not in keep_cols})

    # check if the parameter belongs to a special one
    if parameter in utils.SPECIAL_PARAMETERS:
        # get the other columns to keep in the new dataframe
        other_cols_to_keep = utils.SPECIAL_PARAMETERS[parameter]
        # initialize an empty dataframe
        df_other_cols = DataFrame()
        # we might want to load one or more special columns
        # (of course, avoid to load columns if the special parameter does not request any special parameter,
        # eg event rate or exposure are not build on the basis of any other parameter)

        # + one column only
        if isinstance(other_cols_to_keep, str) and other_cols_to_keep is not None:
            df_other_cols = df.copy().drop(
                columns={x for x in df.columns if x != other_cols_to_keep}
            )
        # + more than one column
        if isinstance(other_cols_to_keep, list):
            for col in other_cols_to_keep:
                if col is not None:
                    # this is the first column we are putting in 'df_other_cols'
                    if df_other_cols.empty:
                        df_other_cols = df.copy().drop(
                            columns={x for x in df.columns if x != col}
                        )
                    # there are already column(s) in 'df_other_cols'
                    else:
                        new_col = df.copy().drop(
                            columns={x for x in df.columns if x != col}
                        )
                        df_other_cols = concat([df_other_cols, new_col], axis=1)
    else:
        df_other_cols = DataFrame()

    # concatenate everything
    df_param = concat([df_param, df_cols, df_other_cols], axis=1)

    return df_param
