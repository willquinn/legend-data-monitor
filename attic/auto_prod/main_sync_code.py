import os
import re
import json
import subprocess

# Directory to monitor
period = "p06"
run = "r003"

# commands to run the container
cmd = "apptainer run" # run command for loadin the container
arg = "/data2/public/prodenv/containers/legendexp_legend-base_latest.sif" # container's path
output_folder = "/data1/users/calgaro/prod-ref-v2" # where to store output files of monitoring plots

# paths
auto_dir_path = "/data2/public/prodenv/prod-blind/tmp/auto" # where to retrieve lh5 dsp/hit files
source_dir = f"{auto_dir_path}/generated/tier/dsp/phy/{period}/{run}/" # same as auto_dir_path, but we look for a specifi run of a given period
rsync_path = "/data1/users/calgaro/rsync-env/output/" # where to store some output files that are used by this script to keep trace of what has been already analyzed

# ===========================================================================================
# BEGINNING OF THE ANALYSIS
# ===========================================================================================

# ===========================================================================================
# Configs definition
# =========================================================================================== 

# define slow control dict
scdb = {
  "output": output_folder,
  "dataset": {
    "experiment": "L200",
    "period": period,
    "version": "",
    "path": auto_dir_path,
    "type": "phy",
    "runs": int(run.split('r')[-1])
  },
  "saving": "overwrite", # LEAVE ME LIKE THIS
  "slow_control": { # here you can put the parameters you want to retrieve from Slow Control
    "parameters": [
      "DaqLeft-Temp1",
      "DaqLeft-Temp2",
      "DaqRight-Temp1",
      "DaqRight-Temp2",
      "RREiT",
      "RRNTe",
      "RRSTe",
      "ZUL_T_RR"
    ]
  }
}
with open(f"{rsync_path}auto_slow_control.json", "w") as f:
    json.dump(scdb, f)

# define geds dict
my_config = {
  "output": output_folder,
  "dataset": {
    "experiment": "L200",
    "period": period,
    "version": "",
    "path": auto_dir_path,
    "type": "phy",
    "runs": int(run.split('r')[-1])
  },
  "saving": "append", # LEAVE ME LIKE THIS
  "subsystems": {
    "geds": {
      "Event rate in pulser events": {
        "parameters": "event_rate",
        "event_type": "pulser",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "time_window": "20S"
      },
      "Event rate in FCbsln events": {
        "parameters": "event_rate",
        "event_type": "FCbsln",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "time_window": "20S"
      },
      "Baselines (dsp/baseline) in pulser events": {
        "parameters": "baseline",
        "event_type": "pulser",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "AUX_ratio": True,
        "variation": True,
        "time_window": "10T"
      },
      "Baselines (dsp/baseline) in FCbsln events": {
        "parameters": "baseline",
        "event_type": "FCbsln",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "variation": True,
        "time_window": "10T"
      },
      "Mean baselines (dsp/bl_mean) in pulser events": {
        "parameters": "bl_mean",
        "event_type": "pulser",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "AUX_ratio": True,
        "variation": True,
        "time_window": "10T"
      },
      "Mean baselines (dsp/bl_mean) in FCbsln events": {
        "parameters": "bl_mean",
        "event_type": "FCbsln",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "variation": True,
        "time_window": "10T"
      },
      "Uncalibrated gain (dsp/cuspEmax) in pulser events": {
        "parameters": "cuspEmax",
        "event_type": "pulser",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "AUX_ratio": True,
        "variation": True,
        "time_window": "10T"
      },
      "Uncalibrated gain (dsp/cuspEmax) in FCbsln events": {
        "parameters": "cuspEmax",
        "event_type": "FCbsln",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "AUX_ratio": True,
        "variation": True,
        "time_window": "10T"
      },
      "Calibrated gain (hit/cuspEmax_ctc_cal) in pulser events": {
        "parameters": "cuspEmax_ctc_cal",
        "event_type": "pulser",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "variation": True,
        "time_window": "10T"
      },
      "Calibrated gain (hit/cuspEmax_ctc_cal) in FCbsln events": {
        "parameters": "cuspEmax_ctc_cal",
        "event_type": "FCbsln",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "variation": True,
        "time_window": "10T"
      },
      "Noise (dsp/bl_std) in pulser events": {
        "parameters": "bl_std",
        "event_type": "pulser",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "AUX_ratio": True,
        "variation": True,
        "time_window": "10T"
      },
      "Noise (dsp/bl_std) in FCbsln events": {
        "parameters": "bl_std",
        "event_type": "FCbsln",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "AUX_ratio": True,
        "variation": True,
        "time_window": "10T"
      },
      "A/E (from dsp) in pulser events": {
        "parameters": "AoE_Custom",
        "event_type": "pulser",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "variation": True,
        "time_window": "10T"
      },
      "A/E (from dsp) in FCbsln events": {
        "parameters": "AoE_Custom",
        "event_type": "FCbsln",
        "plot_structure": "per string",
        "resampled": "only",
        "plot_style": "vs time",
        "variation": True,
        "time_window": "10T"
      }
    }
  }
}
with open(f"{rsync_path}auto_config.json", "w") as f:
    json.dump(my_config, f)

# ===========================================================================================
# Get not-analyzed files
# =========================================================================================== 

# File to store the timestamp of the last check
timestamp_file = f'{rsync_path}last_checked_{period}_{run}.txt'

# Read the last checked timestamp
last_checked = None
if os.path.exists(timestamp_file):
    with open(timestamp_file, 'r') as file:
        last_checked = file.read().strip()

# Get the current timestamp
current_files = os.listdir(source_dir)
new_files = []

# Compare the timestamps of files and find new files
for file in current_files:
    file_path = os.path.join(source_dir, file)
    if last_checked is None or os.path.getmtime(file_path) > float(last_checked):
        new_files.append(file)

# If new files are found, check if they are ok or not
if new_files:
    pattern = r"\d+"
    correct_files = []

    for new_file in new_files:
        matches = re.findall(pattern, new_file)
        # get only files with correct ending (and discard the ones that are still under processing)
        if len(matches) == 6:
            correct_files.append(new_file)
    
    new_files = correct_files

# ===========================================================================================
# Analyze not-analyzed files
# =========================================================================================== 

# If new files are found, run the shell command
if new_files:
    # Replace this command with your desired shell command
    command = 'echo New files found: \033[91m{}\033[0m'.format(' '.join(new_files))
    subprocess.run(command, shell=True)

    # create the file containing the keys with correct format to be later used by legend-data-monitor (it must be created every time with the new keys; NOT APPEND)
    print("\nCreating the file containing the keys to inspect...")
    with open(f'{rsync_path}new_keys.filekeylist', 'w') as f:
        for new_file in new_files:
            new_file = new_file.split('-tier')[0]
            f.write(new_file + '\n')
    print("...done!")

    # ...run the plot production
    print("\nRunning the generation of plots...")
    config_file = f"{rsync_path}auto_config.json"
    keys_file = f"{rsync_path}new_keys.filekeylist"

    bash_command = f"{cmd} --cleanenv {arg} ~/.local/bin/legend-data-monitor user_rsync_prod --config {config_file} --keys {keys_file}"
    print(f"...running command \033[95m{bash_command}\033[0m")
    subprocess.run(bash_command, shell=True)
    print("...done!")

# Update the last checked timestamp
with open(timestamp_file, 'w') as file:
    file.write(str(os.path.getmtime(max([os.path.join(source_dir, file) for file in current_files], key=os.path.getmtime))))

# ===========================================================================================
# Analyze Slow Control data (for the full run - overwrite of previous info)
# =========================================================================================== 

# run slow control data retrieving
print("\nRetrieving Slow Control data...")
scdb_config_file = f"{rsync_path}auto_slow_control.json"

bash_command = f"{cmd} --cleanenv {arg} ~/.local/bin/legend-data-monitor user_scdb --config {scdb_config_file} --pswd BANANE"
print(f"...running command \033[92m{bash_command}\033[0m")
subprocess.run(bash_command, shell=True)
print("...SC done!")
