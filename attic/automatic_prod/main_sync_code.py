import os
import re
import json
import logging
import argparse
import subprocess
from pathlib import Path
from fix_hdf_output import build_new_files

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

def main():
    parser = argparse.ArgumentParser(description="Main code for automatically load and plot processed data on legend-login or NERSC cluster.")
    parser.add_argument("--cluster", help="Name of the cluster where you are operating; pick among 'lngs' or 'nersc'.", default="lngs")
    parser.add_argument("--ref_version", help="Version of processed data to inspect.", default="ref-v1.0.0")
    parser.add_argument("--rsync_path", help="Path where to store results of the automatic running (eg loaded keys, input config files, etc).", default="output")
    parser.add_argument("--output_folder", help="Path where to store the automatic results (plots and summary files).", default="tmp")
    parser.add_argument("--partition", default=False, help="False (default) if not partition data, else True")
    parser.add_argument("--pswd", help="Password to access the Slow Control database (NOT available on NERSC).")
    parser.add_argument("--pswd_email", help="Password to access the legend.data.monitoring@gmail.com account for sending alert messages.")
    

    args = parser.parse_args()
    cluster = args.cluster
    ref_version = args.ref_version
    rsync_path = args.rsync_path
    output_folder = args.output_folder
    partition = False if args.partition=="False" else True
    pswd = args.pswd
    pswd_email = args.pswd_email

    if not os.path.exists(rsync_path):
        os.makedirs(rsync_path)
    
    # paths
    auto_dir = "/global/cfs/cdirs/m2676/data/lngs/l200/public/prodenv/prod-blind/" if cluster == "nersc" else "/data2/public/prodenv/prod-blind/"
    auto_dir_path = os.path.join(auto_dir, ref_version)
    
    search_directory = os.path.join(auto_dir_path, 'generated/tier/dsp/phy')
    def search_latest_folder(my_dir):
      directories = [d for d in os.listdir(my_dir) if os.path.isdir(os.path.join(my_dir, d))]
      directories.sort(key=lambda x: Path(my_dir, x).stat().st_ctime)
      return directories[-1]
    
    # Period to monitor
    period = search_latest_folder(search_directory)
    # Run to monitor
    search_directory = os.path.join(search_directory, period)
    run = search_latest_folder(search_directory)
    
    found = False
    for tier in ["hit", "pht"]:
        source_dir = os.path.join(auto_dir_path, "generated/tier", tier, "phy", period, run)
        if os.path.isdir(source_dir):
            found = True
            break
    
    if found is False:
        logger.debug("No valid folder found. Exiting.")
        exit()
    
    # commands to run the container
    cmd = "shifter --image=legendexp/legend-base:latest" if cluster == "nersc" else "apptainer run"
    if cluster == "nersc":
        cmd = "shifter --image=legendexp/legend-base:latest"
    else:
        cmd = "apptainer run --cleanenv /data2/public/prodenv/containers/legendexp_legend-base_latest.sif" 
    
    # ===========================================================================================
    # BEGINNING OF THE ANALYSIS
    # ===========================================================================================
    # Configs definition
    
    # define slow control dict
    scdb = {
      "output": output_folder,
      "dataset": {
        "experiment": "L200",
        "period": period,
        "version": ref_version,
        "path": auto_dir,
        "type": "phy",
        "runs": int(run.split('r')[-1])
      },
      "saving": "overwrite",
      "slow_control": {
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
    with open(os.path.join(rsync_path, "auto_slow_control.json"), "w") as f:
        json.dump(scdb, f)
    
    # define geds dict
    my_config = {
      "output": output_folder,
      "dataset": {
        "experiment": "L200",
        "period": period,
        "version": ref_version,
        "path": auto_dir,
        "type": "phy",
        "runs": int(run.split('r')[-1])
      },
      "saving": "append",
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
    with open(os.path.join(rsync_path, "auto_config.json"), "w") as f:
        json.dump(my_config, f)
    
    # ===========================================================================================
    # Get not-analyzed files
    # =========================================================================================== 
    
    # File to store the timestamp of the last check
    timestamp_file = os.path.join(rsync_path, f"last_checked_{period}_{run}.txt")
    
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
        logger.debug("Creating the file containing the keys to inspect...")
        with open(os.path.join(rsync_path, "new_keys.filekeylist"), 'w') as f:
            for new_file in new_files:
                new_file = new_file.split('-tier')[0]
                f.write(new_file + '\n')
        logger.debug("...done!")
    
        # ...run the plot production
        logger.debug("Running the generation of plots...")
        config_file = os.path.join(rsync_path, "auto_config.json")
        keys_file = os.path.join(rsync_path, "new_keys.filekeylist")
    
        bash_command = f"{cmd} ~/.local/bin/legend-data-monitor user_rsync_prod --config {config_file} --keys {keys_file}"
        logger.debug(f"...running command \033[95m{bash_command}\033[0m")
        #subprocess.run(bash_command, shell=True)
        logger.debug("...done!")
    
        # compute resampling + info json
        #build_new_files(output_folder, period, run)
    
        # ===========================================================================================
        # Analyze Slow Control data (for the full run - overwrite of previous info)
        # =========================================================================================== 
        if cluster == "lngs":
            # run slow control data retrieving
            logger.debug("Retrieving Slow Control data...")
            scdb_config_file = os.path.join(rsync_path, "auto_slow_control.json")
        
            bash_command = f"{cmd} ~/.local/bin/legend-data-monitor user_scdb --config {scdb_config_file} --port 8282 --pswd {pswd}"
            logger.debug(f"...running command \033[92m{bash_command}\033[0m")
            subprocess.run(bash_command, shell=True)
            logger.debug("...SC done!")
    
        
        # ===========================================================================================
        # Generate Gain Monitoring Summary Plots 
        # =========================================================================================== 
        # create monitoring-plots folder
        mtg_folder = os.path.join(output_folder, ref_version, 'generated/mtg')
        if not os.path.exists(mtg_folder):
            os.makedirs(mtg_folder)
            logger.info(f"Folder '{mtg_folder}' created.")
        mtg_folder = os.path.join(mtg_folder, 'phy')
        if not os.path.exists(mtg_folder):
            os.makedirs(mtg_folder)
            logger.info(f"Folder '{mtg_folder}' created.")
    
        # define dataset depending on the (latest) monitored period/run
        avail_runs = sorted(os.listdir(os.path.join(mtg_folder.replace('mtg', 'plt'), period)))
        dataset = {
            period: avail_runs
        }
        if dataset[period] != []:
          # get first timestamp of first run of the given period
          start_key = (sorted(os.listdir(os.path.join(search_directory, avail_runs[0])))[0]).split('-')[4]
    
          # get pulser monitoring plot for a full period
          phy_mtg_data = mtg_folder.replace('mtg', 'plt')

          # Note: quad_res is set to False by default in these plots
          if partition == False:
            mtg_bash_command = f"{cmd} python monitoring.py --public_data {auto_dir_path} --hdf_files {phy_mtg_data} --output {mtg_folder} --start {start_key} --p {period} --runs {avail_runs} --cluster {cluster} --pswd_email {pswd_email}"
          else:
            mtg_bash_command = f"{cmd} python monitoring.py --public_data {auto_dir_path} --hdf_files {phy_mtg_data} --output {mtg_folder} --start {start_key} --p {period} --runs {avail_runs} --cluster {cluster} --pswd_email {pswd_email} --partition True"

            subprocess.run(mtg_bash_command, shell=True)
          logger.info("...monitoring plots generated!")
    
    
    # Update the last checked timestamp
    with open(timestamp_file, 'w') as file:
        file.write(str(os.path.getmtime(max([os.path.join(source_dir, file) for file in current_files], key=os.path.getmtime))))



if __name__=="__main__":
    main()
