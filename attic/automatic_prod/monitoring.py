# Adaptation of William's code to read auto monitoring hdf files for phy data 
# and automatically create monitoring plots that'll be later uploaded on the dashboard.
import glob
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import cycler, patches
from matplotlib.colors import LogNorm
from datetime import datetime
import os, json
from lgdo import lh5
import numpy as np
from lgdo import ls , show
from legendmeta import LegendMetadata
import pandas as pd
import h5py
import shelve
import logging
import argparse
import re, pickle
import legend_data_monitor
from tqdm.notebook import tqdm

# -------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# stream handler (console)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)

# format
formatter = logging.Formatter("%(asctime)s:  %(message)s")
stream_handler.setFormatter(formatter)

# add to logger
logger.addHandler(stream_handler)

# -------------------------------------------------------------------------

IPython_default = plt.rcParams.copy()
SMALL_SIZE = 8
MEDIUM_SIZE = 10
BIGGER_SIZE = 12

figsize = (4.5, 3)

plt.rc('font', size=SMALL_SIZE)  # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)  # fontsize of the axes title
plt.rc('axes', labelsize=SMALL_SIZE)  # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)  # legend fontsize
plt.rc('figure', titlesize=SMALL_SIZE)  # fontsize of the figure title
plt.rcParams["font.family"] = "serif"

matplotlib.rcParams['mathtext.fontset'] = 'stix'
#matplotlib.rcParams['font.family'] = 'STIXGeneral'

marker_size = 2
line_width = 0.5
cap_size = 0.5
cap_thick = 0.5

# colors = cycler('color', ['b', 'g', 'r', 'm', 'y', 'k', 'c', '#8c564b'])
plt.rc('axes', facecolor='white', edgecolor='black',
       axisbelow=True, grid=True)

def transform_string(input_string):
    """From st1 to String:01."""
    # extract numeric part from the input string using regular expression
    match = re.match(r'\D*(\d+)', input_string)
    numeric_part = match.group(1)
    # Format the numeric part with leading zeros and combine with 'String:'
    result_string = f'String:{int(numeric_part):02}'
    return result_string

def parse_json_or_dict(value):
    """Either load data stored in a JSON file or return the input dictionary."""
    try:
        # Attempt to load value as JSON
        with open(value) as json_file:
            return json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        # Treat value as dictionary
        return eval(value)

def get_calib_data_dict(calib_data, channel, tiers, pars, period, run, tier, key_result, fit):
    sto = lh5.LH5Store()

    folder_tier = os.path.join(tiers[0], "cal", period, run) if tier == 'hit' else os.path.join(tiers[1], "cal", period, run)
    timestamp = os.listdir(folder_tier)[-1].split('-')[-2]

    folder_par = os.path.join(pars[2], "cal", period, run) if tier == 'hit' else os.path.join(pars[3], "cal", period, run)
    jsonfile = [f for f in os.listdir(folder_par) if ".json" in f][0]
    pars_dict = json.load(open(os.path.join(folder_par, jsonfile),'r'))

    # for FEP peak, we want to look at the behaviour over time --> take 'ecal' results (not partition ones!)
    if channel not in pars_dict.keys():
        fep_peak_pos = np.nan
        fep_peak_pos_err = np.nan
        fep_gain = np.nan
        fep_gain_err = np.nan
    else:
        pk_fits = pars_dict[channel]['results']['ecal']['cuspEmax_ctc_runcal']['pk_fits']
        fep_energy = [p for p in sorted(pk_fits) if float(p) >2613 and float(p) < 2616][0]
        try:
            pk_fits = pars_dict[channel]['results']['ecal']['cuspEmax_ctc_runcal']['pk_fits']
            fep_energy = [p for p in sorted(pk_fits) if float(p) >2613 and float(p) < 2616][0]
            try:
                fep_peak_pos =  pk_fits[fep_energy]['parameters_in_ADC']['mu']
                fep_peak_pos_err =  pk_fits[fep_energy]['uncertainties_in_ADC']['mu']
            except:
                fep_peak_pos =  pk_fits[fep_energy]['parameters']['mu']
                fep_peak_pos_err =  pk_fits[fep_energy]['uncertainties']['mu']
                
            fep_gain = fep_peak_pos/2614.5
            fep_gain_err = fep_peak_pos_err/2614.5
        except:
            fep_peak_pos = np.nan
            fep_peak_pos_err = np.nan
            fep_gain = np.nan
            fep_gain_err = np.nan

    
    # load the resolution at Qbb, both linear and quadratic if needed
    if channel not in pars_dict.keys():
        Qbb_fwhm = np.nan
        Qbb_fwhm_quad = np.nan   
    else:
        # pay attention to cap of V in keV
        Qbb_fwhm = np.nan
        Qbb_fwhm_quad =  np.nan
        key_fit = "eres_linear" if fit == "linear" else "eres_quadratic"
        exist = True if pars_dict[channel]['results'][key_result]['cuspEmax_ctc_cal'] else False 
        Qbb_key = [k for k in pars_dict[channel]['results'][key_result]['cuspEmax_ctc_cal']['eres_linear'].keys() if "Qbb_fwhm_in_" in k][0]

        if exist:
            try:
                Qbb_fwhm = pars_dict[channel]['results'][key_result]['cuspEmax_ctc_cal']['eres_linear'][Qbb_key]
            except:
                Qbb_fwhm = pars_dict[channel]['results'][key_result]['cuspEmax_ctc_cal']['eres_linear'][Qbb_key]

            if fit != "linear":
                try:
                    Qbb_fwhm_quad = pars_dict[channel]['results'][key_result]['cuspEmax_ctc_cal']['eres_quadratic'][Qbb_key]
                except:
                    Qbb_fwhm_quad = pars_dict[channel]['results'][key_result]['cuspEmax_ctc_cal']['eres_quadratic'][Qbb_key]

    
    # load the calibrated FEP position --> take 'ecal' results (not partition ones!)
    if channel not in pars_dict.keys():
        fep_cal = np.nan
        fep_cal_err = np.nan
    else:
        expr = pars_dict[channel]['pars']['operations']["cuspEmax_ctc_runcal"]["expression"]
        params = pars_dict[channel]['pars']['operations']["cuspEmax_ctc_runcal"]["parameters"]
        eval_context = {**params, "cuspEmax_ctc": fep_peak_pos}
        fep_cal = eval(expr, {}, eval_context)
        eval_context = {**params, "cuspEmax_ctc": fep_peak_pos_err}
        fep_cal_err = eval(expr, {}, eval_context)


    # get timestamp for additional-final cal run (only for FEP gain display)
    if run not in os.listdir(os.path.join(tiers[-1], "phy", period)):
        run_files = sorted(os.listdir(folder_tier))
        run_end_time = pd.to_datetime(sto.read("ch1027201/dsp/timestamp", os.path.join(folder_tier, run_files[-1]))[-1], unit='s')
        run_start_time = run_end_timey
    else:
        run_files = sorted(os.listdir(folder_tier))
        run_start_time = pd.to_datetime(
            sto.read("ch1027201/dsp/timestamp", os.path.join(folder_tier, run_files[0]))[0], unit='s')
        run_end_time = pd.to_datetime(
            sto.read("ch1027201/dsp/timestamp", os.path.join(folder_tier, run_files[-1]))[-1], unit='s')

    calib_data['fep'].append(fep_gain)
    calib_data['fep_err'].append(fep_gain_err)
    calib_data['cal_const'].append(fep_cal)
    calib_data['cal_const_err'].append(fep_cal_err)
    calib_data['run_start'].append(run_start_time)
    calib_data['run_end'].append(run_end_time)
    calib_data['res'].append(Qbb_fwhm)
    calib_data['res_quad'].append(Qbb_fwhm_quad)

    return calib_data

def get_calib_pars(cluster, path, period, run_list, channel, partition, escale=2039, fit='linear'):
    sto = lh5.LH5Store()
    # add special calib runs at the end of a period
    if (isinstance(period,list) and isinstance(run_list, dict)):
        my_runs = run_list["p09"]
        run_list['p09'] = my_runs + ['r006']
    else:
        if period=='p04': run_list.append('r004')
        if period=='p07': run_list.append('r008')
        if period=='p08': run_list.append('r015')
        if period=='p09': run_list.append('r006')
        if period=='p10': run_list.append('r007')
        if period=='p11': run_list.append('r005')

    calib_data = {
        'fep': [],
        'fep_err': [],
        'cal_const': [],
        'cal_const_err': [],
        'run_start': [],
        'run_end': [],
        'res': [],
        'res_quad': []
    }

    # config with info on all tier folder
    config_proc = json.load(open(os.path.join(path.replace("1.0.0", "2.1.5"), "config.json")))

    tier_dsp = os.path.join(path, config_proc["setups"]["l200"]["paths"]["tier_dsp"].replace("$_/",""))
    tier_psp = os.path.join(path, config_proc["setups"]["l200"]["paths"]["tier_psp"].replace("$_/",""))
    tier_hit = os.path.join(path, config_proc["setups"]["l200"]["paths"]["tier_hit"].replace("$_/",""))
    tier_pht = os.path.join(path, config_proc["setups"]["l200"]["paths"]["tier_pht"].replace("$_/",""))
    tier_raw = os.path.join(path, config_proc["setups"]["l200"]["paths"]["tier_raw"].replace("$_/",""))
    tiers = [tier_dsp, tier_psp, tier_hit, tier_pht, tier_raw]
    par_dsp = os.path.join(path, config_proc["setups"]["l200"]["paths"]["par_dsp"].replace("$_/",""))
    par_psp = os.path.join(path, config_proc["setups"]["l200"]["paths"]["par_psp"].replace("$_/",""))
    par_hit = os.path.join(path, config_proc["setups"]["l200"]["paths"]["par_hit"].replace("$_/",""))
    par_pht = os.path.join(path, config_proc["setups"]["l200"]["paths"]["par_pht"].replace("$_/",""))
    pars = [par_dsp, par_psp, par_hit, par_pht]

    tier = 'hit'
    key_result = 'ecal'
    if os.path.isdir(tier_psp):
        if os.listdir(tier_psp) != []:
            tier = 'pht'
            key_result = 'partition_ecal'
    
    # multiple periods together
    if (isinstance(period,list) and isinstance(run_list, dict)):
        for p in period:
            for r in run_list[p]:
                calib_data = get_calib_data_dict(calib_data, channel, tiers, pars, p, r, tier, key_result, fit)
    ### one period only
    else:
        for run in run_list:
            calib_data = get_calib_data_dict(calib_data, channel, tiers, pars, period, run, tier, key_result, fit)

    for key, item in calib_data.items(): calib_data[key] = np.array(item)
        
    init_cal_const, init_fep = 0, 0
    for cal_, fep_ in zip(calib_data['cal_const'], calib_data['fep']):
        if init_fep == 0 and fep_ != 0: init_fep = fep_
        if init_cal_const == 0 and cal_ != 0: init_cal_const = cal_
    
    if init_cal_const == 0:
        calib_data['cal_const_diff'] = np.array([np.nan for i in range(len(calib_data['cal_const']))])
    else:
        calib_data['cal_const_diff'] = (calib_data['cal_const'] - init_cal_const)/init_cal_const * escale

    if init_fep == 0:
        calib_data['fep_diff'] = np.array([np.nan for i in range(len(calib_data['fep']))])
    else:
        calib_data['fep_diff'] = (calib_data['fep'] - init_fep)/init_fep * escale
    
    return calib_data

def custom_resampler(group, min_required_data_points=100):
    if len(group) >= min_required_data_points:
        return group
    else:
        return None

def get_dfs(phy_mtg_data, period, run_list):
    geds_df_cuspEmax_abs = pd.DataFrame()
    geds_df_cuspEmax_var = pd.DataFrame()
    geds_df_cuspEmax_abs_corr = pd.DataFrame()
    geds_df_cuspEmax_var_corr = pd.DataFrame()
    puls_df_cuspEmax_abs = pd.DataFrame()
    puls_df_cuspEmax_var = pd.DataFrame()
    geds_df_cuspEmaxCtcCal_abs = pd.DataFrame()
    geds_df_cuspEmaxCtcCal_var = pd.DataFrame()

    # multiple periods together
    if (isinstance(period,list) and isinstance(run_list, dict)):
        for p in period:
            phy_mtg_data_p = os.path.join(phy_mtg_data, p)
            runs = os.listdir(phy_mtg_data_p)
            for r in runs:
                if (p=='p08' and r in ['r010','r011','r012','r013','r014'] and 'ref-v1.0.0' in phy_mtg_data_p):
                    phy_mtg_data_p = phy_mtg_data_p.replace('ref-v1.0.0', 'tmp-auto')
                if (p=='p08' and r in ['r000','r001','r002','r003','r004','r005','r006','r007','r008','r009'] and 'tmp-auto' in phy_mtg_data_p):
                    phy_mtg_data_p = phy_mtg_data_p.replace('tmp-auto', 'ref-v1.0.0')
                # keep only specified runs
                if r not in run_list[p]:
                    logger.debug(phy_mtg_data_p, r, p, run_list[p])
                    continue
                files = os.listdir(os.path.join(phy_mtg_data_p, r))
                # get only geds files 
                hdf_geds = [f for f in files if "hdf" in f and "geds" in f] 
                if len(hdf_geds) == 0:
                    return None, None, None, None
                hdf_geds = os.path.join(phy_mtg_data_p, r, hdf_geds[0]) # should be 1
                # get only puls files 
                hdf_puls = [f for f in files if "hdf" in f and "pulser01ana" in f]
                if len(hdf_puls) == 0:
                    return None, None, None, None 
                hdf_puls = os.path.join(phy_mtg_data_p, r, hdf_puls[0]) # should be 1

                # GEDS DATA ========================================================================================================
                geds_abs = pd.read_hdf(hdf_geds, key=f'IsPulser_Cuspemax')
                geds_df_cuspEmax_abs = pd.concat([geds_df_cuspEmax_abs, geds_abs], ignore_index=False, axis=0)
                #geds_ctc_cal_abs = pd.read_hdf(hdf_geds, key=f'IsPulser_CuspemaxCtcCal')
                #geds_df_cuspEmaxCtcCal_abs = pd.concat([geds_df_cuspEmaxCtcCal_abs, geds_ctc_cal_abs], ignore_index=False, axis=0)
                # GEDS PULS-CORRECTED DATA =========================================================================================
                geds_puls_abs = pd.read_hdf(hdf_geds, key=f'IsPulser_Cuspemax_pulser01anaDiff')
                geds_df_cuspEmax_abs_corr = pd.concat([geds_df_cuspEmax_abs_corr, geds_puls_abs], ignore_index=False, axis=0)
                # PULS DATA ========================================================================================================
                puls_abs = pd.read_hdf(hdf_puls, key=f'IsPulser_Cuspemax')
                puls_df_cuspEmax_abs = pd.concat([puls_df_cuspEmax_abs, puls_abs], ignore_index=False, axis=0)
    else:
        phy_mtg_data = os.path.join(phy_mtg_data, period)
        runs = os.listdir(phy_mtg_data)
        for r in runs:
            # keep only specified runs
            if r not in run_list:
                continue
            files = os.listdir(os.path.join(phy_mtg_data, r))
            # get only geds files 
            hdf_geds = [f for f in files if "hdf" in f and "geds" in f] 
            if len(hdf_geds) == 0:
                return None, None, None, None
            hdf_geds = os.path.join(phy_mtg_data, r, hdf_geds[0]) # should be 1
            # get only puls files 
            hdf_puls = [f for f in files if "hdf" in f and "pulser01ana" in f]
            if len(hdf_puls) == 0:
                return None, None, None, None 
            hdf_puls = os.path.join(phy_mtg_data, r, hdf_puls[0]) # should be 1

            # GEDS DATA ========================================================================================================
            geds_abs = pd.read_hdf(hdf_geds, key=f'IsPulser_Cuspemax')
            geds_df_cuspEmax_abs = pd.concat([geds_df_cuspEmax_abs, geds_abs], ignore_index=False, axis=0)
            #geds_ctc_cal_abs = pd.read_hdf(hdf_geds, key=f'IsPulser_CuspemaxCtcCal')
            #geds_df_cuspEmaxCtcCal_abs = pd.concat([geds_df_cuspEmaxCtcCal_abs, geds_ctc_cal_abs], ignore_index=False, axis=0)
            # GEDS PULS-CORRECTED DATA =========================================================================================
            geds_puls_abs = pd.read_hdf(hdf_geds, key=f'IsPulser_Cuspemax_pulser01anaDiff')
            geds_df_cuspEmax_abs_corr = pd.concat([geds_df_cuspEmax_abs_corr, geds_puls_abs], ignore_index=False, axis=0)
            # PULS DATA ========================================================================================================
            puls_abs = pd.read_hdf(hdf_puls, key=f'IsPulser_Cuspemax')
            puls_df_cuspEmax_abs = pd.concat([puls_df_cuspEmax_abs, puls_abs], ignore_index=False, axis=0)

    cols = geds_df_cuspEmax_abs.columns

    return geds_df_cuspEmax_abs, geds_df_cuspEmax_abs_corr, puls_df_cuspEmax_abs, geds_df_cuspEmaxCtcCal_abs

def get_trapTmax_tp0est(phy_mtg_data, period, run_list):
    geds_df_trapTmax = pd.DataFrame()
    geds_df_tp0est   = pd.DataFrame()
    puls_df_trapTmax = pd.DataFrame()
    puls_df_tp0est   = pd.DataFrame()

    # multiple periods together
    if (isinstance(period,list) and isinstance(run_list, dict)):
        for p in period:
            phy_mtg_data_p = os.path.join(phy_mtg_data, p)
            runs = os.listdir(phy_mtg_data_p)
            for r in runs:
                if (p=='p08' and r in ['r010','r011','r012','r013','r014'] and 'ref-v1.0.0' in phy_mtg_data_p):
                    phy_mtg_data_p = phy_mtg_data_p.replace('ref-v1.0.0', 'tmp-auto')
                if (p=='p08' and r in ['r000','r001','r002','r003','r004','r005','r006','r007','r008','r009'] and 'tmp-auto' in phy_mtg_data_p):
                    phy_mtg_data_p = phy_mtg_data_p.replace('tmp-auto', 'ref-v1.0.0')
                # keep only specified runs
                if r not in run_list[p]:
                    continue
                files = os.listdir(os.path.join(phy_mtg_data_p, r))
                # get only geds files 
                hdf_geds = [f for f in files if "hdf" in f and "geds" in f] 
                if len(hdf_geds) == 0:
                    return None, None, None, None
                hdf_geds = os.path.join(phy_mtg_data_p, r, hdf_geds[0]) # should be 1
                # get only puls files 
                hdf_puls = [f for f in files if "hdf" in f and "pulser01ana" in f] 
                if len(hdf_puls) == 0:
                    return None, None, None, None
                hdf_puls = os.path.join(phy_mtg_data_p, r, hdf_puls[0]) # should be 1

                try:
                    # GEDS DATA ========================================================================================================
                    geds_trapTmax_abs = pd.read_hdf(hdf_geds, key=f'IsPulser_Traptmax')
                    geds_df_trapTmax = pd.concat([geds_df_trapTmax, geds_trapTmax_abs], ignore_index=False, axis=0)
                    geds_tp0est_abs = pd.read_hdf(hdf_geds, key=f'IsPulser_Tp0Est')
                    geds_df_tp0est = pd.concat([geds_df_tp0est, geds_tp0est_abs], ignore_index=False, axis=0)

                    # PULS DATA ========================================================================================================
                    puls_trapTmax_abs = pd.read_hdf(hdf_puls, key=f'IsPulser_Traptmax')
                    puls_df_trapTmax = pd.concat([puls_df_trapTmax, puls_trapTmax_abs], ignore_index=False, axis=0)
                    puls_tp0est_abs = pd.read_hdf(hdf_puls, key=f'IsPulser_Tp0Est')
                    puls_df_tp0est = pd.concat([puls_df_tp0est, puls_tp0est_abs], ignore_index=False, axis=0)
                except:
                    return None, None, None, None

    else:    
        phy_mtg_data = os.path.join(phy_mtg_data, period)
        runs = os.listdir(phy_mtg_data)
        for r in runs:
            # keep only specified runs
            if r not in run_list:
                continue
            files = os.listdir(os.path.join(phy_mtg_data, r))
            # get only geds files 
            hdf_geds = [f for f in files if "hdf" in f and "geds" in f] 
            if len(hdf_geds) == 0:
                return None, None, None, None
            hdf_geds = os.path.join(phy_mtg_data, r, hdf_geds[0]) # should be 1
            # get only puls files 
            hdf_puls = [f for f in files if "hdf" in f and "pulser01ana" in f] 
            if len(hdf_puls) == 0:
                return None, None, None, None
            hdf_puls = os.path.join(phy_mtg_data, r, hdf_puls[0]) # should be 1

            try:
                # GEDS DATA ========================================================================================================
                geds_trapTmax_abs = pd.read_hdf(hdf_geds, key=f'IsPulser_Traptmax')
                geds_df_trapTmax = pd.concat([geds_df_trapTmax, geds_trapTmax_abs], ignore_index=False, axis=0)
                geds_tp0est_abs = pd.read_hdf(hdf_geds, key=f'IsPulser_Tp0Est')
                geds_df_tp0est = pd.concat([geds_df_tp0est, geds_tp0est_abs], ignore_index=False, axis=0)

                # PULS DATA ========================================================================================================
                puls_trapTmax_abs = pd.read_hdf(hdf_puls, key=f'IsPulser_Traptmax')
                puls_df_trapTmax = pd.concat([puls_df_trapTmax, puls_trapTmax_abs], ignore_index=False, axis=0)
                puls_tp0est_abs = pd.read_hdf(hdf_puls, key=f'IsPulser_Tp0Est')
                puls_df_tp0est = pd.concat([puls_df_tp0est, puls_tp0est_abs], ignore_index=False, axis=0)
            except:
                return None, None, None, None


    return geds_df_trapTmax, geds_df_tp0est, puls_df_trapTmax, puls_df_tp0est


def get_pulser_data(resampling_time, period, dfs, channel, runs_no, escale):
    ser_pul_cusp = dfs[2][1027203] # selection of pulser channel
    ser_ged_cusp = dfs[0][channel] # selection of ged channel
    #ser_ged_ctc_cal_cusp = dfs[-1][channel]

    # check if these dfs are empty or not - if not, then remove spikes
    if isinstance(dfs[6], pd.DataFrame):
        #ser_ged_trapTmax  = dfs[3][channel]
        #ser_ged_tp0est    = dfs[4][channel]
        ser_pul_tp0est    = dfs[6][1027203]

        ##### remove retriggered events  
        target_time = pd.to_datetime('20231205T040733Z', format='%Y%m%dT%H%M%S%z') # start of p08-r009: 20231127T134659Z
        condition1 = (ser_pul_tp0est.index < target_time ) & (ser_pul_tp0est < 5e4) & (ser_pul_tp0est > 4.8e4)
        condition2 = (ser_pul_tp0est.index >= target_time ) & (ser_pul_tp0est < 5e4) & (ser_pul_tp0est > 4.8e4)# (ser_pul_tp0est < 4.8e4) & (ser_pul_tp0est > 4.7e4)
        len_before = len(ser_pul_tp0est)
        logger.debug("Removed retriggered events:\n", ser_pul_tp0est[(~condition1) & (~condition2)])
        ser_pul_tp0est_new = ser_pul_tp0est[(condition1) | (condition2)]
        len_after = len(ser_pul_tp0est_new)

        # if not empty, then remove spikes
        if len(ser_pul_tp0est_new) != 0:
            logger.debug(f"!!! Removing {len_before-len_after} global pulser events !!!")
            ser_ged_cusp = ser_ged_cusp.loc[ser_pul_tp0est_new.index]
            ser_pul_cusp = ser_pul_cusp.loc[ser_pul_tp0est_new.index]
            #ser_ged_ctc_cal_cusp = ser_ged_ctc_cal_cusp.loc[ser_pul_tp0est_new.index]

    ser_ged_cusp = ser_ged_cusp.dropna()
    ser_pul_cusp = ser_pul_cusp.loc[ser_ged_cusp.index]
    #ser_ged_ctc_cal_cusp = ser_ged_ctc_cal_cusp.loc[ser_ged_cusp.index]

    # multiple periods together
    if (isinstance(period,list)):
        for p in period:
            # remove individual isolated cycles
            if p == 'p03' or p == 'p04' or p == 'p06':
                logger.debug("...removing isolated bunch of data")
                if p == 'p03':
                    start_keys = ["20230327T145702Z", "20230406T135529Z"]
                    stop_keys  = ["20230327T145751Z", "20230406T235540Z"] 
                if p == 'p04':
                    start_keys = ["20230424T123443Z", "20230424T185631Z"]
                    stop_keys  = ["20230424T185631Z", "20230425T001708Z"] 
                if p == 'p06':
                    start_keys = ["20230724T145620Z", "20230615T033328Z", "20230630T150257Z", "20230703T134305Z"]
                    stop_keys  = ["20230725T103957Z", "20230615T093432Z", "20230630T202244Z", "20230704T015054Z"] 

                for (ki, kf) in zip(start_keys, stop_keys):
                    isolated_ki = pd.to_datetime(ki, format='%Y%m%dT%H%M%S%z')
                    isolated_kf = pd.to_datetime(kf, format='%Y%m%dT%H%M%S%z')
                    ser_ged_cusp = ser_ged_cusp[(ser_ged_cusp.index < isolated_ki) | ((ser_ged_cusp.index > isolated_kf))]
                    ser_pul_cusp = ser_pul_cusp[(ser_pul_cusp.index < isolated_ki) | ((ser_pul_cusp.index > isolated_kf))]
                    #ser_ged_ctc_cal_cusp = ser_ged_ctc_cal_cusp[(ser_ged_ctc_cal_cusp.index < isolated_ki) | ((ser_ged_ctc_cal_cusp.index > isolated_kf))]

            # remove ranges of temp. fluctuations
            if p == 'p06' or p == "p07" or p == 'p08' or p == 'p09' or p == 'p10':
                logger.debug("...removing temp. fluctuations from data")
                if p == 'p06':
                    start_keys = ["20230615T033328Z", "20230630T150257Z", "20230703T134305Z"]
                    stop_keys  = ["20230615T093432Z", "20230630T202244Z", "20230704T015054Z"] 
                if p == 'p07':
                    start_keys = ["20230914T054230Z", "20230807T150000Z"]
                    stop_keys  = ["20230919T094821Z", "20230814T234656Z"] 
                if p == 'p08': 
                    start_keys = ["20231009T085938Z", "20231103T080046Z", "20231106T163056Z", "20231223T211700Z", "20240106T034702Z"]
                    stop_keys  = ["20231009T105947Z", "20231103T180220Z", "20231109T175924Z", "20231224T061824Z", "20240106T104735Z"]
                if p == 'p09':
                    start_keys = ["20240121T002839Z", "20240202T015625Z", "20240204T150447Z", "20240207T103233Z"] 
                    stop_keys  = ["20240121T133012Z", "20240202T145844Z", "20240205T140721Z", "20240207T233547Z"] 
                if p == 'p10':
                    start_keys = ["20240225T164758Z"]
                    stop_keys  = ["20240227T094934Z"]

                for (ki, kf) in zip(start_keys, stop_keys):
                    isolated_ki = pd.to_datetime(ki, format='%Y%m%dT%H%M%S%z')
                    isolated_kf = pd.to_datetime(kf, format='%Y%m%dT%H%M%S%z')
                    ser_ged_cusp = ser_ged_cusp[(ser_ged_cusp.index < isolated_ki) | ((ser_ged_cusp.index > isolated_kf))]
                    ser_pul_cusp = ser_pul_cusp[(ser_pul_cusp.index < isolated_ki) | ((ser_pul_cusp.index > isolated_kf))]
                    #ser_ged_ctc_cal_cusp = ser_ged_ctc_cal_cusp[(ser_ged_ctc_cal_cusp.index < isolated_ki) | ((ser_ged_ctc_cal_cusp.index > isolated_kf))]
    ## just one period
    else:
        # remove individual isolated cycles
        if period == 'p03' or period == 'p04' or period == 'p06':
            logger.debug("...removing isolated bunch of data")
            if period == 'p03':
                start_keys = ["20230327T145702Z", "20230406T135529Z"]
                stop_keys  = ["20230327T145751Z", "20230406T235540Z"] 
            if period == 'p04':
                start_keys = ["20230424T123443Z", "20230424T185631Z"]
                stop_keys  = ["20230424T185631Z", "20230425T001708Z"] 
            if period == 'p06':
                start_keys = ["20230724T145620Z", "20230615T033328Z", "20230630T150257Z", "20230703T134305Z"]
                stop_keys  = ["20230725T103957Z", "20230615T093432Z", "20230630T202244Z", "20230704T015054Z"] 

            for (ki, kf) in zip(start_keys, stop_keys):
                isolated_ki = pd.to_datetime(ki, format='%Y%m%dT%H%M%S%z')
                isolated_kf = pd.to_datetime(kf, format='%Y%m%dT%H%M%S%z')
                ser_ged_cusp = ser_ged_cusp[(ser_ged_cusp.index < isolated_ki) | ((ser_ged_cusp.index > isolated_kf))]
                ser_pul_cusp = ser_pul_cusp[(ser_pul_cusp.index < isolated_ki) | ((ser_pul_cusp.index > isolated_kf))]
                #ser_ged_ctc_cal_cusp = ser_ged_ctc_cal_cusp[(ser_ged_ctc_cal_cusp.index < isolated_ki) | ((ser_ged_ctc_cal_cusp.index > isolated_kf))]

        # remove ranges of temp. fluctuations
        if period == 'p06' or period == 'p07' or period == 'p08' or period == 'p09' or period == 'p10':
            logger.debug("...removing temp. fluctuations from data")
            if period == 'p06':
                start_keys = ["20230615T033328Z", "20230630T150257Z", "20230703T134305Z"]
                stop_keys  = ["20230615T093432Z", "20230630T202244Z", "20230704T015054Z"] 
            if period == 'p07':
                start_keys = ["20230914T054230Z", "20230807T150000Z"]
                stop_keys  = ["20230919T094821Z", "20230814T234656Z"]
            if period == 'p08': 
                start_keys = ["20231009T085938Z", "20231103T080046Z", "20231106T163056Z", "20231223T211700Z", "20240106T034702Z"]
                stop_keys  = ["20231009T105947Z", "20231103T180220Z", "20231109T175924Z", "20231224T061824Z", "20240106T104735Z"]
            if period == 'p09':
                start_keys = ["20240121T002839Z", "20240202T015625Z", "20240204T150447Z", "20240207T103233Z"] 
                stop_keys  = ["20240121T133012Z", "20240202T145844Z", "20240205T140721Z", "20240207T233547Z"] 
            if period == 'p10':
                start_keys = ["20240225T164758Z"]
                stop_keys  = ["20240227T094934Z"]

            for (ki, kf) in zip(start_keys, stop_keys):
                isolated_ki = pd.to_datetime(ki, format='%Y%m%dT%H%M%S%z')
                isolated_kf = pd.to_datetime(kf, format='%Y%m%dT%H%M%S%z')
                ser_ged_cusp = ser_ged_cusp[(ser_ged_cusp.index < isolated_ki) | ((ser_ged_cusp.index > isolated_kf))]
                ser_pul_cusp = ser_pul_cusp[(ser_pul_cusp.index < isolated_ki) | ((ser_pul_cusp.index > isolated_kf))]
                #ser_ged_ctc_cal_cusp = ser_ged_ctc_cal_cusp[(ser_ged_ctc_cal_cusp.index < isolated_ki) | ((ser_ged_ctc_cal_cusp.index > isolated_kf))]

    
    if runs_no == 1 and resampling_time=="10T":
        hour_counts  = ser_pul_cusp.resample(resampling_time).count()
    else:
        hour_counts  = ser_pul_cusp.resample(resampling_time).count() >= 100

    ged_cusp_av = np.average(ser_ged_cusp.values[:360]) # switch to first 10% of available time interval?
    pul_cusp_av = np.average(ser_pul_cusp.values[:360])
    #ged_cusp_ctc_cal_av = np.average(ser_ged_ctc_cal_cusp.values[:360])
    # if first entries of dataframe are NaN 
    if np.isnan(ged_cusp_av):
        logger.debug('the average is a nan')
        return None

    ser_ged_cuspdiff = pd.Series((ser_ged_cusp.values - ged_cusp_av)/ged_cusp_av, index=ser_ged_cusp.index.values).dropna()
    ser_pul_cuspdiff = pd.Series((ser_pul_cusp.values - pul_cusp_av)/pul_cusp_av, index=ser_pul_cusp.index.values).dropna()
    #ser_ged_cuspdiff_ctc_cal = pd.Series((ser_ged_ctc_cal_cusp.values - ged_cusp_ctc_cal_av)/ged_cusp_ctc_cal_av, index=ser_pul_cusp.index.values).dropna()
    ser_ged_cuspdiff_kev = pd.Series(ser_ged_cuspdiff*escale, index=ser_ged_cuspdiff.index.values)
    ser_pul_cuspdiff_kev = pd.Series(ser_pul_cuspdiff*escale, index=ser_pul_cuspdiff.index.values)

    ged_cusp_hr_av_ = ser_ged_cuspdiff_kev.resample(resampling_time).mean()
    ged_cusp_hr_av_[~hour_counts.values] = np.nan
    ged_cusp_hr_std = ser_ged_cuspdiff_kev.resample(resampling_time).std()
    ged_cusp_hr_std[~hour_counts.values] = np.nan
    pul_cusp_hr_av_ = ser_pul_cuspdiff_kev.resample(resampling_time).mean()
    pul_cusp_hr_av_[~hour_counts.values] = np.nan
    pul_cusp_hr_std = ser_pul_cuspdiff_kev.resample(resampling_time).std()
    pul_cusp_hr_std[~hour_counts.values] = np.nan

    ged_cusp_corr = ser_ged_cuspdiff - ser_pul_cuspdiff
    ged_cusp_corr = pd.Series(ged_cusp_corr[ser_ged_cuspdiff.index.values])
    ged_cusp_corr_kev = ged_cusp_corr*escale
    ged_cusp_corr_kev = pd.Series(ged_cusp_corr_kev[ged_cusp_corr.index.values])
    ged_cusp_cor_hr_av_ = ged_cusp_corr_kev.resample(resampling_time).mean()
    ged_cusp_cor_hr_av_[~hour_counts.values] = np.nan
    ged_cusp_cor_hr_std = ged_cusp_corr_kev.resample(resampling_time).std()
    ged_cusp_cor_hr_std[~hour_counts.values] = np.nan
    
    return {
        'ged': {
            'cusp': ser_ged_cusp,
            'cuspdiff': ser_ged_cuspdiff,
            'cuspdiff_kev': ser_ged_cuspdiff_kev,
            'cusp_av': ged_cusp_hr_av_,
            'cusp_std': ged_cusp_hr_std
        },
        'pul_cusp': {
            'raw': ser_pul_cusp,
            'rawdiff': ser_pul_cuspdiff,
            'kevdiff': ser_pul_cuspdiff_kev,
            'kevdiff_av': pul_cusp_hr_av_,
            'kevdiff_std': pul_cusp_hr_std
        },
        'diff': {
            'raw': None,
            'rawdiff': ged_cusp_corr,
            'kevdiff': ged_cusp_corr_kev,
            'kevdiff_av': ged_cusp_cor_hr_av_,
            'kevdiff_std': ged_cusp_cor_hr_std
        }
    }

        


def main():
    parser = argparse.ArgumentParser(description="Main code for gain monitoring plots.")
    parser.add_argument("--public_data", help="Path to tmp-auto public data files (eg /data2/public/prodenv/prod-blind/tmp-auto).", default="/data2/public/prodenv/prod-blind/ref-v1.0.1")
    parser.add_argument("--hdf_files", help="Path to hdf files (eg see files in /data1/users/calgaro/prod-ref-v2/generated/plt/phy).")
    parser.add_argument("--output", default="removal_new_keys", help="Path to output folder.")
    parser.add_argument("--start", help="First timestamp of the inspected range.")
    parser.add_argument("--p", help="Period to inspect.")
    parser.add_argument("--runs", nargs="+", type=str, help="Runs to inspect.")
    parser.add_argument("--partition", default="False", help="False if not partition data; default: False")
    parser.add_argument("--zoom", default="True", help="True to zoom over y axis; default: True")
    parser.add_argument("--quad_res", default="False", help="True if you want to plot the quadratic resolution too; default: False")
    parser.add_argument("--cluster", default="lngs", help="Name of the cluster where you are operating; pick among 'lngs' or 'nersc'.")
    parser.add_argument("--pswd_email", help="Password to access the legend.data.monitoring@gmail.com account for sending alert messages.")

    args = parser.parse_args()

    auto_dir_path = args.public_data 
    phy_mtg_data = args.hdf_files
    output_folder = args.output
    start_key = args.start
    period = args.p
    runs = args.runs
    cluster = args.cluster
    pswd_email = args.pswd_email

    avail_runs = []
    for entry in runs:
        new_entry = entry.replace(",","").replace("[","").replace("]","")
        avail_runs.append(new_entry)

    dataset = {
        period: avail_runs
    }
    logger.debug(f'This is the dataset: {dataset}')

    xlim_idx=1
    partition = False if args.partition=="False" else True
    quadratic = False if args.quad_res=="False" else True
    zoom = True if args.zoom=="True" else False

    fit_flag = 'quadratic' if quadratic is True else 'linear'

    meta = LegendMetadata(os.path.join(auto_dir_path, "inputs/"))
    # get channel map
    chmap = meta.channelmap(start_key)
    # get string info
    str_chns = {}
    # TODO: fix this
    for string in range(13):
        if string in [0, 6]: continue 
        channels = [f"ch{chmap[ged].daq.rawid}" for ged, dic in chmap.items() if dic["system"]=='geds' and dic["location"]["string"]==string] # and dic["analysis"]["processable"]==True 
        if len(channels)>0: 
            str_chns[string] = channels

    email_message = ["ALERT: Data monitoring threshold exceeded."]
    
    period_list = list(dataset.keys())
    for index_i in tqdm(range(len(period_list))):
        period = period_list[index_i]
        run_list = dataset[period]
        
        geds_df_cuspEmax_abs, geds_df_cuspEmax_abs_corr, puls_df_cuspEmax_abs, geds_df_cuspEmaxCtcCal_abs = get_dfs(phy_mtg_data, period, run_list)
        geds_df_trapTmax, geds_df_tp0est, puls_df_trapTmax, puls_df_tp0est = get_trapTmax_tp0est(phy_mtg_data, period, run_list)

        if geds_df_cuspEmax_abs is None or geds_df_cuspEmax_abs_corr is None or puls_df_cuspEmax_abs is None:
            logger.debug("Dataframes are None for %s!", period)
            continue
        if geds_df_cuspEmax_abs.empty or geds_df_cuspEmax_abs_corr.empty or puls_df_cuspEmax_abs.empty:
            logger.debug("Dataframes are empty for %s!",period)
            continue
        dfs = [geds_df_cuspEmax_abs, geds_df_cuspEmax_abs_corr, puls_df_cuspEmax_abs, geds_df_trapTmax, geds_df_tp0est, puls_df_trapTmax, puls_df_tp0est, geds_df_cuspEmaxCtcCal_abs]
        
        string_list = list(str_chns.keys())
        for index_j in tqdm(range(len(string_list))):
            string = string_list[index_j]
            
            channel_list = str_chns[string]
            do_channel = True
            for index_k in range(len(channel_list)):
                channel = channel_list[index_k]
                channel_name = chmap.map("daq.rawid")[int(channel[2:])]["name"]

                resampling_time = "h"#if len(runs)>1 else "10T"
                if int(channel.split('ch')[-1]) not in list(dfs[0].columns):
                    logger.debug(f"{channel} is not present in the dataframe!")
                    continue
                pulser_data = get_pulser_data(resampling_time, period, dfs, int(channel.split('ch')[-1]), len(runs), escale=2039)
                
                fig, ax = plt.subplots(figsize=(12,4))
                pars_data = get_calib_pars(cluster, auto_dir_path, period, run_list, channel, partition, escale=2039, fit=fit_flag)

                # check if gain is over threshold
                kevdiff = pulser_data['diff']['kevdiff_av']
                timestamps = kevdiff.index
                t0 = pars_data['run_start']
                for i in range(len(t0)):  
                    time_range_start = t0[i]
                    time_range_end = time_range_start + pd.Timedelta(days=7)
                
                    # filter timestamps/gain within the time range
                    mask_time_range = (timestamps >= time_range_start) & (timestamps < time_range_end)
                    filtered_timestamps = timestamps[mask_time_range]
                    kevdiff_in_range = kevdiff[mask_time_range]
                
                    threshold = 1e-5#pars_data['res'][i] / 2 
                    mask = (kevdiff_in_range > threshold) | (kevdiff_in_range < -threshold)
                    over_threshold_timestamps = filtered_timestamps[mask]
                
                    if not over_threshold_timestamps.empty:
                        for t in over_threshold_timestamps:
                            email_message.append(f"- Gain over threshold at {t} ({period}) for {channel_name} ({channel})")

                if channel != 'ch1120004': # =B00089D; TODO: make it generic  
                    #plt.plot(pulser_data['ged']['cusp_av'], 'C0', label='GED')
                    plt.plot(pulser_data['pul_cusp']['kevdiff_av'], 'C2', label='PULS01ANA')
                    plt.plot(pulser_data['diff']['kevdiff_av'], 'C4', label='GED corrected')
                    plt.fill_between(
                        pulser_data['diff']['kevdiff_av'].index.values,
                        y1=[float(i) - float(j) for i, j in zip(pulser_data['diff']['kevdiff_av'].values, pulser_data['diff']['kevdiff_std'].values)],
                        y2=[float(i) + float(j) for i, j in zip(pulser_data['diff']['kevdiff_av'].values, pulser_data['diff']['kevdiff_std'].values)],
                        color='k', alpha=0.2, label=r'±1$\sigma$'
                    )
                
                plt.plot(pars_data['run_start'] - pd.Timedelta(hours=5), pars_data['fep_diff'], 'kx', label='FEP gain')#, markersize=8)
                plt.plot(pars_data['run_start'] - pd.Timedelta(hours=5), pars_data['cal_const_diff'], 'rx', label='cal. const. diff')
                
                for ti in pars_data['run_start']: plt.axvline(ti, color='k')
                
                for i in range(len(t0)):
                    if i == len(pars_data['run_start'])-1:
                        plt.plot([t0[i], t0[i] + pd.Timedelta(days=7)], [pars_data['res'][i]/2, pars_data['res'][i]/2], 'b-')
                        plt.plot([t0[i], t0[i] + pd.Timedelta(days=7)], [-pars_data['res'][i]/2, -pars_data['res'][i]/2], 'b-')
                        if quadratic:
                            plt.plot([t0[i], t0[i] + pd.Timedelta(days=7)], [pars_data['res_quad'][i]/2, pars_data['res_quad'][i]/2], color='dodgerblue', linestyle='-')
                            plt.plot([t0[i], t0[i] + pd.Timedelta(days=7)], [-pars_data['res_quad'][i]/2, -pars_data['res_quad'][i]/2], color='dodgerblue', linestyle='-')
                    else:
                        plt.plot([t0[i], t0[i+1]], [pars_data['res'][i]/2, pars_data['res'][i]/2], 'b-')
                        plt.plot([t0[i], t0[i+1]], [-pars_data['res'][i]/2, -pars_data['res'][i]/2], 'b-')
                        if quadratic:
                            plt.plot([t0[i], t0[i+1]], [pars_data['res_quad'][i]/2, pars_data['res_quad'][i]/2], color='dodgerblue', linestyle='-')
                            plt.plot([t0[i], t0[i+1]], [-pars_data['res_quad'][i]/2, -pars_data['res_quad'][i]/2], color='dodgerblue', linestyle='-')
                    if str(pars_data['res'][i]/2*1.1) != 'nan' and i<len(pars_data['res'])-(xlim_idx-1):
                        plt.text(t0[i], pars_data['res'][i]/2*1.1, '{:.2f}'.format(pars_data['res'][i]), color='b')
                    
                    if quadratic:
                        if str(pars_data['res_quad'][i]/2*1.5) != 'nan' and i<len(pars_data['res'])-(xlim_idx-1):
                            plt.text(t0[i], pars_data['res_quad'][i]/2*1.5, '{:.2f}'.format(pars_data['res_quad'][i]), color='dodgerblue')
                    
                fig.suptitle(f'period: {period} - string: {string} - position: {chmap.map("daq.rawid")[int(channel[2:])]["location"]["position"]} - ged: {channel_name}')
                plt.ylabel(r'Energy diff / keV')
                plt.plot([0,1], [0,1], 'b', label='Qbb FWHM keV lin.')
                my_det = channel_name
                if quadratic:
                    plt.plot([1,2], [1,2], 'dodgerblue', label='Qbb FWHM keV quadr.')
                
                if zoom:
                    bound = np.average(pulser_data['diff']['kevdiff_std'].dropna())
                    if channel_name == 'B00089D':plt.ylim(-3,3)
                    else: plt.ylim(-2.5*bound,2.5*bound)
                min_date = pulser_data['pul_cusp']['kevdiff_av'].index.min()
                max_date = pulser_data['pul_cusp']['kevdiff_av'].index.max()
                time_difference = max_date - t0[-xlim_idx]
                time_difference_timedelta = pd.Timedelta(days=time_difference.days)
                plt.xlim(t0[0] - pd.Timedelta(hours=8), t0[-xlim_idx] + time_difference*1.5) #pd.Timedelta(days=7))# --> change me to resize the width of the last run
                plt.legend(loc='lower left')
                plt.tight_layout()

                mgt_folder = os.path.join(output_folder, period, f"st{string}")
                if not os.path.exists(mgt_folder):
                    os.makedirs(mgt_folder)
                    logger.debug('...created %s', mgt_folder)
                
                # ~~~~~~~~~~~~~~~~ save pdfs with plots for an easy/quick access ~~~~~~~~~~~~~~~~
                pdf_name = os.path.join(mgt_folder, f"{period}_string{string}_pos{chmap.map("daq.rawid")[int(channel[2:])]["location"]["position"]}_{channel_name}_gain_shift.pdf")
                plt.savefig(pdf_name)

                # ~~~~~~~~~~~~~~~~ pickle and save plots in a shelve file ~~~~~~~~~~~~~~~~~~~~~~~
                # - serialize the plot 
                serialized_plot = pickle.dumps(plt.gcf())  
                plt.close(fig) 
                # store the serialized plot in a shelve object under key 
                with shelve.open(os.path.join(output_folder, period, f"{period}_gain_shift"), 'c', protocol=pickle.HIGHEST_PROTOCOL) as shelf:
                    shelf[f'{period}_string{string}_pos{chmap.map("daq.rawid")[int(channel[2:])]["location"]["position"]}_{channel_name}'] = serialized_plot
                plt.close(fig)

                # structure of pickle files:
                #  - p08_string1_pos1_V02160A
                #  - p08_string1_pos2_V02160B
                #  - ...
                #  - p08_string2_pos1_B00035C
                #  - p08_string2_pos2_C000RG1
                #  - ...

    if len(email_message) > 1 and pswd_email != None:
        with open('message.txt', 'w') as f:
            for line in email_message:
                f.write(line + '\n')
        legend_data_monitor.utils.send_email_alert(pswd_email, ['sofia.calgaro@physik.uzh.ch'], "message.txt")

if __name__=="__main__":
    main()
