import matplotlib.pyplot as plt
import sys
import numpy as np
import pandas as pd
import seaborn as sns
from datetime import datetime, timezone
from matplotlib.backends.backend_pdf import PdfPages
from pandas import DataFrame, Timedelta, concat

from legendmeta import LegendSlowControlDB
scdb = LegendSlowControlDB()
scdb.connect(password="...")  # ????????????????????

from . import utils

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# SLOW CONTROL LOADING/PLOTTING FUNCTIONS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Necessary to perform the SSH tunnel to the databse
def get_sc_df(param="PT118"):
    """
    def ssh_tunnel():
        import subprocess
        #ssh_tunnel_cmd = 'ssh -t ugnet-proxy' 
        #full_ssh_cmd = ssh_tunnel_cmd
        #subprocess.run(full_ssh_cmd, shell=True)
        #subprocess.Popen(["ssh", "-t", "ugnet-proxy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    """

    # load info from settings/SC-params.json
    sc_params = utils.SC_PARAMETERS

    # check if parameter is within the one listed in settings/SC-params.json
    if param not in sc_params['SC_DB_params'].keys():
        utils.logger.error(f"\033[91mThe parameter {param} is not present in 'settings/SC-params.json'. Try again with another parameter or update the json file!\033[0m")
        sys.exit()

    # get data
    df_param = load_table_and_apply_flags(param, sc_params)
    unit, lower_lim, upper_lim = get_plotting_info(param, sc_params)


    exit()


def load_table_and_apply_flags(param: str, sc_params: dict) -> DataFrame:
    """Load the corresponding table from SC database for the process of interest and apply already the flags for the parameter under study."""
    # getting the process and flags of interest from 'settings/SC-params.json' for the provided parameter
    table_param = sc_params['SC_DB_params'][param]['table']
    flags_param = sc_params['SC_DB_params'][param]['flags']

    # check if the selected table is present in the SC database. If not, arise an error and exit
    if table_param not in scdb.get_tables():
        utils.logger.error("\033[91mThis is not present in the SC database! Try again.\033[0m")
        sys.exit()
    
    # Assuming T1 and T2 are datetime objects or strings in the format 'YYYY-MM-DD HH:MM:SS' (we'll apply a time query to shorten the df loading time)
    T1 = '2023-01-09 00:00:00'
    T2 = '2023-01-09 06:00:00'

    # get the dataframe for the process of interest
    utils.logger.debug(f"... getting the dataframe for '{table_param}' in the time range of interest")
    # SQL query to filter the dataframe based on the time range
    query = f"SELECT * FROM {table_param} WHERE tstamp >= '{T1}' AND tstamp <= '{T2}'"
    get_table_df = scdb.dataframe(query)
    # order by timestamp (not automatically done)
    get_table_df = get_table_df.sort_values(by="tstamp")

    utils.logger.debug(get_table_df)

    # let's apply the flags for keeping only the parameter of interest
    utils.logger.debug(f"... applying flags to get the parameter '{param}'")
    get_table_df = apply_flags(get_table_df, sc_params, flags_param)
    utils.logger.debug("... after flagging the events:", get_table_df)

    return get_table_df



def get_plotting_info(param: str, sc_params: dict): # -> str, float, float:
    """Return units and low/high limits of a given parameter."""
    table_param = sc_params['SC_DB_params'][param]['table']
    flags_param = sc_params['SC_DB_params'][param]['flags']
    
    # get info dataframe of the corresponding process under study (do I need to specify the param????)
    get_table_info = scdb.dataframe(table_param.replace("snap", "info"))

    # let's apply the flags for keeping only the parameter of interest
    get_table_info = apply_flags(get_table_info, sc_params, flags_param)
    utils.logger.debug("... units and thresholds will be retrieved from the following object: %s", get_table_info)

    # To get units and limits, consider they might change over time
    # This means we have to query the dataframe get the correct values based on the inspected time interval
    T1 = '2023-04-01 00:00:00'
    T2 = '2023-04-01 15:00:00'

    # Convert T1 and T2 to datetime objects in the UTC timezone
    T1 = datetime.strptime(T1, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    T2 = datetime.strptime(T2, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

    # Filter the DataFrame based on the time interval, starting to look from the latest entry ('reversed(...)')
    times = list(get_table_info['tstamp'].unique()) 
    for time in reversed(times):
        if T1 < time < T2:
            unit = list(get_table_info['unit'].unique())[0] 
            lower_lim = upper_lim = None
            utils.logger.warning(f"\033[93mParameter {param} has no valid range in the time period you selected. Upper and lower thresholds are set to None, while units={unit}\033[0m")
            return unit, lower_lim, upper_lim

        if time < T1 and time < T2:
            unit = list(get_table_info[get_table_info['tstamp'] == time]['unit'].unique())[0] 
            lower_lim = get_table_info[get_table_info['tstamp'] == time]['ltol'].tolist()[-1]
            upper_lim = get_table_info[get_table_info['tstamp'] == time]['utol'].tolist()[-1]
            utils.logger.debug(f"... parameter {param} must be within [{lower_lim};{upper_lim}] {unit}")
            return unit, lower_lim, upper_lim

        if time > T1 and time > T2:
            utils.logger.error("\033[91mYou're travelling too far in the past, there were no SC data in the time period you selected. Try again!\033[0m")
            sys.exit()

    return unit, lower_lim, upper_lim


def apply_flags(df: DataFrame, sc_params: dict, flags_param: list) -> DataFrame:
    """Apply the flags read from 'settings/SC-params.json' to the input dataframe."""
    for flag in flags_param:
        column = sc_params['expressions'][flag]['column']
        entry = sc_params['expressions'][flag]['entry']
        df = df[df[column] == entry]

    return df