import matplotlib.pyplot as plt
import numpy as np
import glob
import yaml
import os
import json

from legendmeta import LegendMetadata

from . import utils

plt.rcParams.update({
    'axes.titlesize': 16,  
    'xtick.labelsize': 14, 
    'ytick.labelsize': 14, 
    'axes.labelsize': 14,  
    'font.size': 10,       
    'legend.fontsize': 14  
})

def deep_get(d, keys, default=None):
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d

def load_fit_pars_from_yaml(pars_files_list: list, detectors_list: list, detectors_name: list, runs_to_keep: list):
    """
    Load detector data from YAML files and return directly as a dict.

    Parameters
    ----------
    pars_files_list : list
        List of file paths to YAML parameter files.
    detectors_list : list
        List of detector raw IDs (eg. 'ch1104000') to extract data for.
    runs_to_keep : list or None
        Runs to keep (e.g. [4, 5, 6]); if None, keep all.

    Returns
    -------
    dict
        {
          "V11925A": {
              "r004": {"mean": ..., "mean_err": ..., "sigma": ..., "sigma_err": ...},
              "r005": {...},
              ...
          },
          "V11925B": {
              "r004": {...},
              ...
          }
        }
    """
    results = {}

    for file_path in pars_files_list:
        run_idx = int(file_path.split('/')[-2].split('r')[-1])
        run_str = f"r{run_idx:03d}"
        if run_str not in runs_to_keep:
            continue

        run_data = utils.read_json_or_yaml(file_path)
        time = 0 if "par_hit" in file_path else file_path.split('-')[-2]

        for idx, det in enumerate(detectors_list):
            det_key = det if det in run_data else detectors_name[idx] 

            pars = deep_get(run_data or {}, [det_key, "results", "aoe", "1000-1300keV", time], {})

            results.setdefault(detectors_name[idx], {})[run_str] = {
                "mean": pars.get("mean"),
                "mean_err": pars.get("mean_err"),
                "sigma": pars.get("sigma"),
                "sigma_err": pars.get("sigma_err"),
            }

    return results or None

def none_to_nan(seq):
    return [np.nan if v is None else v for v in seq]
    
def evaluate_psd_usability_and_plot(fit_results_cal: dict, det_name: str, output_dir: str, output_file: str):
    """
    Plot fit results (mean and sigma + std devs) across runs, with optional LAC point added separately.
    Also evaluates detector performance and writes summary to output file.
    """
    run_labels = sorted(fit_results_cal.keys())
    run_positions = list(range(len(run_labels)))

    # Extract values
    mean_vals   = none_to_nan([fit_results_cal[r]["mean"]      for r in sorted(fit_results_cal)])
    mean_errs   = none_to_nan([fit_results_cal[r]["mean_err"]  for r in sorted(fit_results_cal)])
    sigma_vals  = none_to_nan([fit_results_cal[r]["sigma"]     for r in sorted(fit_results_cal)])
    sigma_errs  = none_to_nan([fit_results_cal[r]["sigma_err"] for r in sorted(fit_results_cal)])

    if all(np.isnan(x) for x in mean_vals):
        # Write to output file (append mode)
        with open(output_file, 'a') as f:
            f.write(f"{det_name} - all nan entries" + '\n')
        return 

    fig, axs = plt.subplots(2, 2, figsize=(15, 9), sharex=True)
    (ax1, ax3), (ax2, ax4) = axs

    # === Plot 1: Mean
    # Average value of mu over the period
    mean_avg = np.nanmean(mean_vals)
    mean_std = np.nanstd(mean_vals)

    h1 = ax1.errorbar(run_positions, mean_vals, yerr=mean_errs,
                    fmt='s', color='blue', capsize=4, label=r"$\mu_{i}$ cal runs")
    h2 = ax1.axhline(mean_avg, linestyle='--', color='steelblue', label = rf"$\bar{{\mu}} = {mean_avg:.5f}$")
    h3 = ax1.fill_between(run_positions, mean_avg - mean_std, mean_avg + mean_std,
                     color='steelblue', alpha=0.2, label=f"±1 std dev ({mean_std:.5f})")
    
    ax1.set_ylabel("Mean stability",fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.legend(handles=[h1, h2, h3], fontsize=12)
    
            
    # === Plot 2: Sigma
    # Average value of sigma over the period
    sigma_avg = np.nanmean(sigma_vals)
    sigma_std = np.nanstd(sigma_vals)

    h1 = ax2.errorbar(run_positions, sigma_vals, yerr=sigma_errs,
                    fmt='s', color='darkorange', capsize=4, label=r"$\sigma_{i}$ cal runs")
    h2 = ax2.axhline(sigma_avg, linestyle='--', color='peru', label = rf"$\bar{{\sigma}} = {sigma_avg:.5f}$")
    h3 = ax2.fill_between(run_positions, sigma_avg - sigma_std, sigma_avg + sigma_std,
                     color='peru', alpha=0.2, label=f"±1 std dev ({sigma_std:.5f})")
    

    ax2.set_ylabel("Sigma stability", fontsize=14)
    ax2.set_xlabel("Run", fontsize=14)
    ax2.grid(True, alpha=0.3)
    ax2.legend(handles=[h1, h2, h3], fontsize=12)


    # === Plot 3: (μ[i] - μ[0]) / σ_avg
    # Calculate (μ[i] - μ[k]) / σ_avg for all points (where μ[k]!=nan)
    valid_idx = np.where(~np.isnan(mean_vals))[0][0]
    slow_shifts = [(v - mean_vals[valid_idx]) / sigma_avg for v in mean_vals]

    ax3.plot(run_positions, slow_shifts, marker='^', linestyle='-', color='darkorchid', label="Slow shifts", markersize=8, linewidth=1)
    ax3.axhline(0, color='black', linestyle='--', linewidth=1)
    ax3.axhline(0.5, color='crimson', linestyle='--', linewidth=2)
    ax3.axhline(-0.5, color='crimson', linestyle='--', linewidth=2)
    ax3.set_ylabel(r"$(\mu_{i}-\mu_{0})/\bar{\sigma}$", fontsize=14)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="upper left", bbox_to_anchor=(0, 0.95), fontsize=12)


    # === Plot 4: (μ[i+1] - μ[i]) / σ[i] 
    sudden_shifts = []
    sequential_positions = []

    # Add 0 for the first run
    if run_positions:
        # find first valid mean
        valid_idx = next((i for i, v in enumerate(mean_vals) if not np.isnan(v)), None)
    
        if valid_idx is not None:
            sudden_shifts.append(0)                        # baseline shift
            sequential_positions.append(run_positions[valid_idx])  # align with valid run

    # Calculate sequential differences for cal runs
    for i in range(len(mean_vals) - 1):
        sequential_positions.append(run_positions[i+1])  # second point in the difference
        
        v1, v2, s = mean_vals[i], mean_vals[i+1], sigma_vals[i]
    
        if np.isnan(v1) or np.isnan(v2) or np.isnan(s) or s == 0:
            sudden_shifts.append(np.nan)  # invalid or div-by-zero
        else:
            diff = abs(v2 - v1) / s
            sudden_shifts.append(diff)

    # Convert to arrays for convenience
    x = np.array(sequential_positions)
    y = np.array(sudden_shifts)
    # Keep only valid points (non-NaN)
    mask = ~np.isnan(y)
    x_valid = x[mask]
    y_valid = y[mask]
    
    ax4.plot(x_valid, y_valid, marker='^', linestyle='-', color='green', 
         label="Sudden shifts", markersize=8, linewidth=1)
    ax4.axhline(0, color='black', linestyle='--', linewidth=1)
    ax4.axhline(0.25, color='crimson', linestyle='--', linewidth=2)
    ax4.set_ylabel(r"$|(\mu_{i+1}-\mu_{i})/\sigma_{i}|$", fontsize=14)
    ax4.set_xlabel("Run", fontsize=14)
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc="upper left", bbox_to_anchor=(0, 0.95), fontsize=12)

    for ax in axs.flatten():
        ax.set_xticks(run_positions)
        ax.set_xticklabels(run_labels, rotation=0)

    fig.suptitle(f"{det_name}", fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    plt.savefig(os.path.join(output_dir, f"{det_name}_PSD_USABILITY.pdf"), bbox_inches='tight')
    plt.close()
    
    # === Performance Evaluation

    # Check slow shift: (μ[i] - μ[0]) / σ_avg outside ±0.5
    slow_shift_failed = any(abs(z) > 0.5 for z in slow_shifts)
    # Find which runs fail
    slow_shift_fail_runs = [run_labels[i] for i, z in enumerate(slow_shifts) if abs(z) > 0.5]
    
    # Check sudden shift: |μ[i+1] - μ[i]| / σ[i] >= 0.25 (excluding first point which is 0 by default)
    sudden_shift_failed = any(diff >= 0.25 for diff in sudden_shifts[1:]) 
    # Find which runs fail
    sudden_shift_fail_runs = [f"{run_labels[i-1]}TO{run_labels[i]}" for i, z in enumerate(sudden_shifts) if z >= 0.25]


    
    # Determine detector status
    if not slow_shift_failed and not sudden_shift_failed:
        status = f"{det_name} - valid psd"
    else:
        status = f"{det_name} - unstable psd"
        if slow_shift_failed and sudden_shift_failed:
            status += f" (slow shift - {slow_shift_fail_runs})(sudden shift - {sudden_shift_fail_runs})"
        elif slow_shift_failed:
            status += f" (slow shift - {slow_shift_fail_runs})"
        elif sudden_shift_failed:
            status += f" (sudden shift - {sudden_shift_fail_runs})"

    # Write to output file (append mode)
    with open(output_file, 'a') as f:
        f.write(status + '\n')
    



def check_psd(auto_dir_path: str, output_dir: str, period: str):
    
    found = False
    for tier in ["hit", "pht"]:
        cal_path = os.path.join(auto_dir_path, "generated/par", tier, "cal", period)
        if os.path.isdir(cal_path):
            found = True
            break
    if found is False:
        logger.debug(f"No valid folder {cal_path} found. Exiting.")
        exit()
    
    pars_files_list = sorted(glob.glob(f"{cal_path}/*/*.yaml"))
    if not pars_files_list:
        pars_files_list = sorted(glob.glob(f"{cal_path}/*/*.json"))

    metadata_path = os.path.join(auto_dir_path, "inputs")
    lmeta = LegendMetadata(metadata_path)
    chmap = lmeta.channelmap()
    detectors_name = [det for det, info in chmap.items() if info['system'] == 'geds']
    detectors_list = [f"ch{chmap[det]['daq']['rawid']}" for det in detectors_name if chmap[det]['name']==det]

    # retireve all dets info
    cal_runs = sorted(os.listdir(cal_path))
    cal_psd_info = load_fit_pars_from_yaml(pars_files_list, detectors_list, detectors_name, cal_runs)
    if cal_psd_info is None:
        utils.logger.debug("...no data are available at the moment")
        return

    # Create the folder and parents if missing
    output_dir = os.path.join(output_dir, period)
    os.makedirs(output_dir, exist_ok=True)
    
    # inspect one single det: plot+saving
    for det_name in detectors_name:
        usability_map_file = os.path.join(output_dir, "psd_usability.yaml")
        evaluate_psd_usability_and_plot(cal_psd_info[det_name], det_name, output_dir, usability_map_file) 

