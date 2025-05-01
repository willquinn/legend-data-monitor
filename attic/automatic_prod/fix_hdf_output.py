import os
import pandas as pd 
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import math, sys
import seaborn as sns
import pandas as pd
from datetime import datetime
import logging
import pandas as pd
import os
import fnmatch
import shelve
import pickle as pkl
import json
import h5py

def build_new_files(my_path, period, run):
    data_file = os.path.join(my_path, f'generated/plt/phy/{period}/{run}/l200-{period}-{run}-phy-geds.hdf')
    with h5py.File(data_file, 'r') as f:
        my_keys = list(f.keys())

    info_dict = {
        "keys": my_keys
    }

    resampling_times = ["1min", "5min", "10min", "30min", "60min"] 

    for idx,resample_unit in enumerate(resampling_times):
        new_file = f'{my_path}/generated/plt/phy/{period}/{run}/l200-{period}-{run}-phy-geds-res_{resample_unit}.hdf'
        # remove it if already exists so we can start again to append resampled data
        if os.path.exists(new_file):
            os.remove(new_file)
            print(new_file, 'was removed!')

        for k in my_keys:
            if "info" in k: 
                # do it once
                if idx==0:
                    original_df = pd.read_hdf(data_file, key=k)
                    info_dict.update({k: {
                        "subsystem": original_df.loc['subsystem', 'Value'],
                        "unit": original_df.loc['unit', 'Value'],
                        "label": original_df.loc['label', 'Value'],
                        "event_type": original_df.loc['event_type', 'Value'],
                        "lower_lim_var": original_df.loc['lower_lim_var', 'Value'],
                        "upper_lim_var": original_df.loc['upper_lim_var', 'Value'],
                        "lower_lim_abs": original_df.loc['lower_lim_abs', 'Value'],
                        "upper_lim_abs": original_df.loc['upper_lim_abs', 'Value'] # is ok to have 'None' or do I have to convert it???
                    }})
                continue

            original_df = pd.read_hdf(data_file, key=k)

            # mean dataframe is kept 
            if "_mean" in k:
                original_df.to_hdf(new_file, key=k, mode='a')
                continue

            original_df.index = pd.to_datetime(original_df.index)
            # resample
            resampled_df = original_df.resample(resample_unit).mean()
            # substitute the original df with the resampled one
            original_df = resampled_df
            # append resampled data to the new file
            resampled_df.to_hdf(new_file, key=k, mode='a')
        
        print(new_file, "was created :)")

        # do it once
        if idx==0:
            json_output  = os.path.join(my_path, f'generated/plt/phy/{period}/{run}/l200-{period}-{run}-phy-geds-info.json')
            with open(json_output, 'w') as file:
                json.dump(info_dict, file, indent=4)
            print(json_output, "was created :)")



##################### SAME BUT FOR SLOW CONTROL DATA #####################
##########################################################################
def build_new_files_SC(my_path, period, run):
    
    for idx,period in enumerate(['p03', 'p04', 'p05', 'p06', 'p07', 'p08']):
        runs = [['r000', 'r001', 'r002', 'r003', 'r004', 'r005'], ['r000', 'r001', 'r002', 'r003', 'r006'], ['r000', 'r001', 'r002', 'r004'], ['r000', 'r001', 'r002', 'r003', 'r004', 'r005'], ['r000', 'r001', 'r002', 'r003', 'r004', 'r005', 'r006', 'r007'], ['r000', 'r001', 'r002', 'r003', 'r004', 'r005', 'r006', 'r007', 'r008']]
        for run in runs[idx]:
            print("..................", period, run)

            my_path = '/data1/users/calgaro/prod-ref-v3-auto'

            data_file = os.path.join(my_path, f'generated/plt/phy/{period}/{run}/l200-{period}-{run}-phy-slow_control.hdf')
            if not os.path.exists(data_file):
                print(data_file, "does not exists!!!")
                continue

            with h5py.File(data_file, 'r') as f:
                my_keys = list(f.keys())

            resampling_times = ["1min", "5min", "10min", "30min", "60min"] # as proposed by Valerio

            for idx,resample_unit in enumerate(resampling_times):
                print("................................", resample_unit)
                new_file = f'{my_path}/generated/plt/phy/{period}/{run}/l200-{period}-{run}-phy-slow_control-res_{resample_unit}.hdf'
                # remove it if already exists so we can start again to append resampled data
                if os.path.exists(new_file):
                    os.remove(new_file)
                    print(new_file, 'was removed!')

                for k in my_keys:
                    print(".......................................", k)
                    original_df = pd.read_hdf(data_file, key=k)
                    original_df['tstamp'] = pd.to_datetime(original_df['tstamp'], utc=True)
                    original_df['value'] = pd.to_numeric(original_df['value'], errors='coerce')  # handle errors as NaN
                    original_df.set_index('tstamp', inplace=True)
                    resampled_df = original_df.resample('10T').mean()
                    resampled_df = resampled_df.dropna()
                    resampled_df["unit"] = original_df["unit"][0]
                    resampled_df.reset_index(inplace=True)
                        
                    resampled_df.to_hdf(new_file, key=k, mode='a')

                    print(new_file, "was created :)")