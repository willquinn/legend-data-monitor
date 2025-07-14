import argparse
import logging
import os
import re
import subprocess
from pathlib import Path

import yaml

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
    parser = argparse.ArgumentParser(
        description="Main code for automatically load and plot processed data on legend-login or NERSC cluster."
    )
    parser.add_argument(
        "--cluster",
        help="Name of the cluster where you are operating; pick among 'lngs' or 'nersc'.",
        default="lngs",
    )
    parser.add_argument(
        "--ref_version",
        help="Version of processed data to inspect (eg. tmp-auto or ref-v2.1.0).",
        default="ref-v1.0.0",
    )
    parser.add_argument(
        "--rsync_path",
        help="Path where to store results of the automatic running (eg loaded keys, input config files, etc).",
        default="output",
    )
    parser.add_argument(
        "--output_folder",
        help="Path where to store the automatic results (plots and summary files).",
        default="tmp",
    )
    parser.add_argument(
        "--partition",
        default=False,
        help="False (default) if not partition data, else True",
    )
    parser.add_argument(
        "--pswd",
        help="Password to access the Slow Control database (NOT available on NERSC).",
    )
    parser.add_argument(
        "--pswd_email",
        default=None,
        help="Password to access the legend.data.monitoring@gmail.com account for sending alert messages.",
    )
    parser.add_argument(
        "--chunk_size",
        default=20,
        type=int,
        help="Maximum integer number of files to read at each loop in order to avoid the kernel to be killed.",
    )
    parser.add_argument(
        "--p",
        default=None,
        help="Period to inspect.",
    )
    parser.add_argument(
        "--r",
        default=None,
        help="Run to inspect.",
    )
    parser.add_argument(
        "--sc",
        default=False,
        help="Boolean for retrieving Slow Control data (default: False).",
    )
    parser.add_argument(
        "--escale",
        default=2039,
        help="Energy sccale at which evaluating the gain differences; default: 2039 keV (76Ge Qbb).",
    )
    parser.add_argument(
        "--pdf",
        default="False",
        help="True if you want to save pdf files too; default: False",
    )

    args = parser.parse_args()
    cluster = args.cluster
    ref_version = args.ref_version
    rsync_path = args.rsync_path
    output_folder = args.output_folder
    partition = False if args.partition is False else True
    pswd = args.pswd
    pswd_email = args.pswd_email
    chunk_size = args.chunk_size
    input_period = args.p
    input_run = args.r
    get_sc = False if args.sc is False else True
    save_pdf = args.pdf
    escale_val = args.escale

    if not os.path.exists(rsync_path):
        os.makedirs(rsync_path)

    # paths
    auto_dir = (
        "/global/cfs/cdirs/m2676/data/lngs/l200/public/prodenv/prod-blind/"
        if cluster == "nersc"
        else "/data2/public/prodenv/prod-blind/"
    )
    auto_dir_path = os.path.join(auto_dir, ref_version)
    search_directory = os.path.join(auto_dir_path, "generated/tier/dsp/phy")

    def search_latest_folder(my_dir):
        directories = [
            d for d in os.listdir(my_dir) if os.path.isdir(os.path.join(my_dir, d))
        ]
        directories.sort(key=lambda x: Path(my_dir, x).stat().st_ctime)
        return directories[-1]

    # Period to monitor
    period = (
        search_latest_folder(search_directory) if input_period is None else input_period
    )
    # Run to monitor
    search_directory = os.path.join(search_directory, period)
    run = search_latest_folder(search_directory) if input_run is None else input_run

    found = False
    for tier in ["hit", "pht", "dsp", "psp", "evt", "pet", "skm"]:
        source_dir = os.path.join(
            auto_dir_path, "generated/tier", tier, "phy", period, run
        )
        if os.path.isdir(source_dir):
            found = True
            break

    if found is False:
        logger.debug(f"No valid folder {source_dir} found. Exiting.")
        exit()

    # commands to run the container
    cmd = (
        "shifter --image=legendexp/legend-base:latest"
        if cluster == "nersc"
        else "apptainer run"
    )
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
            "runs": int(run.split("r")[-1]),
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
                "ZUL_T_RR",
            ]
        },
    }
    with open(os.path.join(rsync_path, "auto_slow_control.yaml"), "w") as f:
        yaml.dump(scdb, f, sort_keys=False)

    # define geds dict
    my_config = {
        "output": output_folder,
        "dataset": {
            "experiment": "L200",
            "period": period,
            "version": ref_version,
            "path": auto_dir,
            "type": "phy",
            "runs": int(run.split("r")[-1]),
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
                    "time_window": "20S",
                },
                "Event rate in FCbsln events": {
                    "parameters": "event_rate",
                    "event_type": "FCbsln",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "time_window": "20S",
                },
                "Baselines (dsp/baseline) in pulser events": {
                    "parameters": "baseline",
                    "event_type": "pulser",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "AUX_ratio": True,
                    "variation": True,
                    "time_window": "10T",
                },
                "Baselines (dsp/baseline) in FCbsln events": {
                    "parameters": "baseline",
                    "event_type": "FCbsln",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "variation": True,
                    "time_window": "10T",
                },
                "Mean baselines (dsp/bl_mean) in pulser events": {
                    "parameters": "bl_mean",
                    "event_type": "pulser",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "AUX_ratio": True,
                    "variation": True,
                    "time_window": "10T",
                },
                "Mean baselines (dsp/bl_mean) in FCbsln events": {
                    "parameters": "bl_mean",
                    "event_type": "FCbsln",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "variation": True,
                    "time_window": "10T",
                },
                "Uncalibrated gain (dsp/trapEmax) in pulser events": {
                    "parameters": "trapEmax",
                    "event_type": "pulser",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "AUX_ratio": True,
                    "variation": True,
                    "time_window": "10T",
                },
                "Uncalibrated gain (dsp/trapEmax) in FCbsln events": {
                    "parameters": "trapEmax",
                    "event_type": "FCbsln",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "AUX_ratio": True,
                    "variation": True,
                    "time_window": "10T",
                },
                "Calibrated gain (hit/trapEmax_ctc_cal) in pulser events": {
                    "parameters": "trapEmax_ctc_cal",
                    "event_type": "pulser",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "variation": True,
                    "time_window": "10T",
                },
                "Calibrated gain (hit/trapEmax_ctc_cal) in FCbsln events": {
                    "parameters": "trapEmax_ctc_cal",
                    "event_type": "FCbsln",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "variation": True,
                    "time_window": "10T",
                },
                "Noise (dsp/bl_std) in pulser events": {
                    "parameters": "bl_std",
                    "event_type": "pulser",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "AUX_ratio": True,
                    "variation": True,
                    "time_window": "10T",
                },
                "Noise (dsp/bl_std) in FCbsln events": {
                    "parameters": "bl_std",
                    "event_type": "FCbsln",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "AUX_ratio": True,
                    "variation": True,
                    "time_window": "10T",
                },
                "A/E (from dsp) in pulser events": {
                    "parameters": "AoE_Custom",
                    "event_type": "pulser",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "variation": True,
                    "time_window": "10T",
                },
                "A/E (from dsp) in FCbsln events": {
                    "parameters": "AoE_Custom",
                    "event_type": "FCbsln",
                    "plot_structure": "per string",
                    "resampled": "only",
                    "plot_style": "vs time",
                    "variation": True,
                    "time_window": "10T",
                },
                "Quality cuts in physics events": {
                    "parameters": "quality_cuts",
                    "event_type": "phy",
                    "qc_flags": True,
                    "qc_classifiers": False,
                },
            }
        },
    }
    with open(os.path.join(rsync_path, "auto_config.yaml"), "w") as f:
        yaml.dump(my_config, f, sort_keys=False)

    # ===========================================================================================
    # Get not-analyzed files
    # ===========================================================================================

    # File to store the timestamp of the last check
    timestamp_file = os.path.join(rsync_path, f"last_checked_{period}_{run}.txt")

    # Read the last checked timestamp
    last_checked = None
    if os.path.exists(timestamp_file):
        with open(timestamp_file) as file:
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
    new_files = sorted(new_files)

    # remove keys stored in ignore-keys.yaml (eg bad/heavy keys)
    with open(
        "../../src/legend_data_monitor/settings/ignore-keys.yaml"
    ) as f:  # TODO: more general
        ignore_keys = yaml.load(f, Loader=yaml.CLoader)

    def remove_key(timestamp, ignore_keys, period):
        for idx in range(0, len(ignore_keys[period]["start_keys"])):
            start = ignore_keys[period]["start_keys"][idx]
            end = ignore_keys[period]["stop_keys"][idx]
            if start <= timestamp < end:
                return True
        return False

    new_files = [
        fname
        for fname in new_files
        if not remove_key(fname.split("-")[4], ignore_keys, period)
    ]

    # If new files are found, run the shell command
    if new_files:
        # Replace this command with your desired shell command
        command = "echo New files found: \033[91m{}\033[0m".format(" ".join(new_files))
        subprocess.run(command, shell=True)

        # create the file containing the keys with correct format to be later used by legend-data-monitor (it must be created every time with the new keys; NOT APPEND)
        logger.debug("Creating the file containing the keys to inspect...")
        with open(os.path.join(rsync_path, "new_keys.filekeylist"), "w") as f:
            for new_file in new_files:
                new_file = new_file.split("-tier")[0]
                f.write(new_file + "\n")
        logger.debug("...done!")

        # run the plot production
        logger.debug("Running the generation of plots...")
        config_file = os.path.join(rsync_path, "auto_config.yaml")
        keys_file = os.path.join(rsync_path, "new_keys.filekeylist")

        # read all lines from the original file
        with open(keys_file) as f:
            lines = f.readlines()
        num_lines = len(lines)
        if num_lines > chunk_size:
            # split lines into chunks and write to multiple files
            for idx, i in enumerate(range(0, num_lines, chunk_size), start=1):
                chunk = lines[i : i + chunk_size]
                output_file = os.path.join(
                    rsync_path, f"new_keys_part_{i // chunk_size + 1}.filekeylist"
                )

                with open(output_file, "w") as out_f:
                    out_f.writelines(chunk)

                # TODO: do I have to change from overwrite to append???
                total_parts = (num_lines + chunk_size - 1) // chunk_size
                logger.debug(
                    f"[{idx}/{total_parts}] Created file: {output_file} with {len(chunk)} lines."
                )
                bash_command = f"{cmd} ~/.local/bin/legend-data-monitor user_rsync_prod --config {config_file} --keys {output_file}"
                logger.debug(f"...running command \033[95m{bash_command}\033[0m")
                subprocess.run(bash_command, shell=True)
        else:
            logger.debug(f"File has {num_lines} lines. No need to split.")
            bash_command = f"{cmd} ~/.local/bin/legend-data-monitor user_rsync_prod --config {config_file} --keys {keys_file}"
            logger.debug(f"...running command \033[95m{bash_command}\033[0m")
            subprocess.run(bash_command, shell=True)
        logger.debug("...done!")

        # compute resampling + info yaml
        logger.debug("Resampling outputs...")
        files_folder = os.path.join(output_folder, ref_version)
        bash_command = (
            f'{cmd} python -c "from monitoring import build_new_files; '
            f"build_new_files('{files_folder}', '{period}', '{run}')\""
        )
        logger.debug(f"...running command \033[95m{bash_command}\033[0m")
        subprocess.run(bash_command, shell=True)
        logger.debug("...done!")

        # ===========================================================================================
        # Analyze Slow Control data (for the full run - overwrite of previous info)
        # ===========================================================================================
        if cluster == "lngs" and get_sc is True:
            try:
                logger.debug("Retrieving Slow Control data...")
                scdb_config_file = os.path.join(rsync_path, "auto_slow_control.yaml")

                bash_command = f"{cmd} ~/.local/bin/legend-data-monitor user_scdb --config {scdb_config_file} --port 8282 --pswd {pswd}"
                logger.debug(f"...running command \033[92m{bash_command}\033[0m")
                subprocess.run(bash_command, shell=True)
                logger.debug("...SC done!")
            except subprocess.CalledProcessError as e:
                logger.error(f"Slow Control command failed: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error while retrieving Slow Control data: {e}"
                )

        # ===========================================================================================
        # Generate Gain Monitoring Summary Plots
        # ===========================================================================================
        mtg_folder = os.path.join(output_folder, ref_version, "generated/mtg/phy")
        os.makedirs(mtg_folder, exist_ok=True)
        logger.info(f"Folder {mtg_folder} ensured")

        # define dataset depending on the (latest) monitored period/run
        avail_runs = sorted(
            os.listdir(os.path.join(mtg_folder.replace("mtg", "plt"), period))
        )
        dataset = {period: avail_runs}
        if dataset[period] != []:
            logger.debug("Generating monitoring plots...")
            # get first timestamp of first run of the given period
            start_key = (
                sorted(os.listdir(os.path.join(search_directory, avail_runs[0])))[0]
            ).split("-")[4]

            # get pulser monitoring plot for a full period
            phy_mtg_data = mtg_folder.replace("mtg", "plt")

            # Note: quad_res is set to False by default in these plots
            mtg_bash_command = f"{cmd} python monitoring.py --public_data {auto_dir_path} --hdf_files {phy_mtg_data} --output {mtg_folder} --start {start_key} --p {period} --runs {avail_runs} --cluster {cluster} --pswd_email {pswd_email} --escale {escale_val}"
            if partition is True:
                mtg_bash_command += "--partition True"
            if save_pdf is True:
                mtg_bash_command += "--pdf True"

            subprocess.run(mtg_bash_command, shell=True)
            logger.info("...monitoring plots generated!")
    else:
        logger.debug("No new files were detected.")

    # Update the last checked timestamp
    with open(timestamp_file, "w") as file:
        file.write(
            str(
                os.path.getmtime(
                    max(
                        [os.path.join(source_dir, file) for file in current_files],
                        key=os.path.getmtime,
                    )
                )
            )
        )


if __name__ == "__main__":
    main()
