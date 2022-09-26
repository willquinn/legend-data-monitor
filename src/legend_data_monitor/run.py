from __future__ import annotations

import logging
import os
from datetime import datetime

import matplotlib as mpl
from matplotlib.backends.backend_pdf import PdfPages

# modules
from . import analysis, plot, timecut

log = logging.getLogger(__name__)

# config JSON info
j_config, j_par, _ = analysis.read_json_files()
exp = j_config[0]["exp"]
files_path = j_config[0]["path"]["lh5-files"]
version = j_config[0]["path"]["version"]
output_path = j_config[0]["path"]["output-path"]
period = j_config[1]
run = j_config[2]
datatype = j_config[3]
det_type = j_config[4]
par_to_plot = j_config[5]
two_dim_pars = j_config[6]["two_dim_pars"]
time_window = j_config[7]
last_hours = j_config[8]
verbose = j_config[11]


# for multiple detectors
def dump_all_plots_together(
    dsp_files: list[str], time_cut: list[str], path: str, map_path: str
) -> None:
    """
    Create and dump plot in single pdf and multiple pkl files.

    Parameters
    ----------
    dsp_files
                Strings of lh5 dsp files
    time_cut
                List with info about time cuts
    path
                Path where to save output files
    map_path
                Path where to save output heatmaps
    """
    if isinstance(dsp_files, str):
        dsp_files = [dsp_files]

    #dsp_files = dsp_files[17:] # remove data prior to 20220817T124844Z in run22
    #dsp_files = dsp_files[25:]
    #dsp_files = dsp_files[17:50]  # keep only first data (to perform tests in a quick way)

    # exit if no dsp files are found
    if len(dsp_files) == 0:
        logging.warning("There are no files to inspect!")
        sys.exit(1)

    raw_files = [dsp_file.replace("dsp", "raw") for dsp_file in dsp_files]
    geds_dict, spms_dict, other_dict = analysis.load_channels(raw_files)
    all_ievt, puls_only_ievt, not_puls_ievt = analysis.get_puls_ievt(dsp_files)

    with PdfPages(path) as pdf:
        # with PdfPages(map_path) as pdf_map: # <- enable it for heatmaps
        if (
            det_type["geds"] is False
            and det_type["spms"] is False
            and det_type["ch000"] is False
        ):
            logging.error(
                "NO detectors have been selected! Enable geds and/or spms and/or ch000 in config.json"
            )
            return

        # Geds plots
        if det_type["geds"] is True:
            string_geds, string_geds_name = analysis.read_geds(geds_dict)
            geds_par = par_to_plot["geds"]
            if len(geds_par) == 0:
                logging.error("Geds: NO parameters have been enabled!")
            else:
                logging.error("Geds will be plotted...")
                for par in geds_par:
                    det_status_dict = {}
                    for (det_list, string) in zip(string_geds, string_geds_name):
                        #if det_list==string_geds[3]: # keep 1 string (per far prima)

                        if len(det_list) == 0:
                            continue  

                        if par not in two_dim_pars:
                          map_dict = plot.plot_wtrfll(
                                  dsp_files,
                                  det_list,
                                  par,
                                  time_cut,
                                  "geds",
                                  string,
                                  geds_dict,
                                  all_ievt, 
                                  puls_only_ievt, 
                                  not_puls_ievt,
                                  pdf,
                          )
                        else:
                            map_dict = plot.plot_par_vs_time(
                                  dsp_files,
                                  det_list,
                                  par,
                                  time_cut,
                                  "geds",
                                  string,
                                  geds_dict,
                                  all_ievt, 
                                  puls_only_ievt, 
                                  not_puls_ievt,
                                  pdf,
                            )
                        if map_dict is not None:
                            for det, status in map_dict.items():
                                det_status_dict[det] = status

                        if verbose is True:
                            if map_dict is not None:
                                logging.error(
                                    f"\t...{par} for geds (string #{string}) has been plotted!"
                                )
                            else:
                                logging.error(
                                    f"\t...no {par} plots for geds - string #{string}!"
                                )
                    # maps are disabled!
                    # if det_status_dict != []:
                    #    map.geds_map(
                    #        par,
                    #        geds_dict,
                    #        string_geds,
                    #        string_geds_name,
                    #        det_status_dict,
                    #        time_cut,
                    #        map_path,
                    #        pdf_map,
                    #    )

        # Spms plots
        if det_type["spms"] is True:
            if datatype == "cal":
                logging.error("No SiPMs for calibration data!")
            else:
                (
                    spms_merged,
                    spms_name_merged,
                    string_spms,
                    string_spms_name,
                ) = analysis.read_spms(spms_dict)
                spms_par = par_to_plot["spms"]
                if len(spms_par) == 0:
                    logging.error("Spms: NO parameters have been enabled!")
                else:
                    logging.error("Spms will be plotted...")
                    for par in spms_par:
                        if par == "gain":
                            for (det_list, string) in zip(
                                spms_merged, spms_name_merged
                            ):
                                plot.plot_par_vs_time_2d(
                                    dsp_files,
                                    det_list,
                                    time_cut,
                                    "spms",
                                    string,
                                    spms_dict,
                                    pdf,
                                )
                                if verbose is True:
                                    logging.error(
                                        f"\t...{par} for spms ({string}) has been plotted!"
                                    )
                        else:
                            det_status_dict = {}
                            for (det_list, string) in zip(
                                string_spms, string_spms_name
                            ):
                                if len(det_list) == 0:
                                    continue
                                if len(string) != 0:
                                    map_dict = plot.plot_par_vs_time(
                                        dsp_files,
                                        det_list,
                                        par,
                                        time_cut,
                                        "spms",
                                        string,
                                        spms_dict,
                                        None,
                                        None,
                                        None,
                                        pdf,
                                    )
                                if map_dict is not None:
                                    for det, status in map_dict.items():
                                        det_status_dict[det] = status

                                if verbose is True:
                                    if map_dict is not None:
                                        logging.error(
                                            f"\t...{par} for spms ({string}) has been plotted!"
                                        )
                                    else:
                                        logging.error(
                                            f"\t...no {par} plots for spms - {string}!"
                                        )
                            # maps are disabled!
                            # if det_status_dict != []:
                            #    map.spms_map(
                            #        par,
                            #        spms_dict,
                            #        spms_merged,
                            #        spms_name_merged,
                            #        det_status_dict,
                            #        time_cut,
                            #        map_path,
                            #        pdf_map,
                            #    )

        # ch000 plots
        if det_type["ch000"] is True:
            ch000_par = par_to_plot["ch000"]
            if len(ch000_par) == 0:
                logging.error("ch000: NO parameters have been enabled!")
            else:
                logging.error("ch000 will be plotted...")
                for par in ch000_par:
                    map_dict = plot.plot_par_vs_time_ch000(
                        dsp_files,
                        par,
                        time_cut,
                        "ch000",
                        all_ievt, 
                        puls_only_ievt, 
                        not_puls_ievt,
                        pdf,
                    )
                    if verbose is True:
                        if map_dict is not None:
                            logging.error(f"\t...{par} for ch000 has been plotted!")
                        else:
                            logging.error(f"\t...no {par} plots for ch000!")

    if verbose is True:
        logging.error(f"Plots are in {path}")
        logging.error(f"Heatmaps are in {map_path}")


def select_and_plot_run(path: str, plot_path: str, map_path: str) -> None:
    """
    Select run and call dump_all_plots_together().

    Parameters
    ----------
    path
                Path to pgt folder
    plot_path
                Path where to save output plots
    map_path
                Path where to save output heatmaps
    """
    full_path = os.path.join(path, "dsp", datatype, period, run)

    lh5_files = os.listdir(full_path)
    lh5_files = sorted(
        lh5_files,
        key=lambda file: int(
            ((file.split("-")[4]).split("Z")[0]).split("T")[0]
            + ((file.split("-")[4]).split("Z")[0]).split("T")[1]
        ),
    )

    if datatype == "cal":
        runs = [file for file in lh5_files if "cal" in file]
        if verbose is True:
            logging.error("Calib runs have been loaded")
    if datatype == "phy":
        runs = [file for file in lh5_files if "phy" in file]
        if verbose is True:
            logging.error("Phys runs have been loaded")

    mpl.use("pdf")

    time_cut = timecut.build_timecut_list(time_window, last_hours)

    # time analysis
    if len(time_cut) != 0:
        start, end = timecut.time_dates(time_cut)
        path = os.path.join(
            plot_path, f"{exp}-{period}-{run}-{datatype}_{start}_{end}.pdf"
        )
        map_path = os.path.join(
            map_path, f"{exp}-{period}-{run}-{datatype}_{start}_{end}.pdf"
        )
    # no time cuts
    else:
        path = os.path.join(plot_path, f"{exp}-{period}-{run}-{datatype}.pdf")
        map_path = os.path.join(map_path, f"{exp}-{period}-{run}-{datatype}.pdf")

    if len(time_cut) == 3:
        runs = timecut.cut_below_threshold_filelist(runs, time_cut)
    elif len(time_cut) == 4:
        runs = timecut.cut_min_max_filelist(runs, time_cut)

    runs = [os.path.join(full_path, run_file) for run_file in runs]

    dump_all_plots_together(runs, time_cut, path, map_path)


def main():
    path = files_path + version + "/generated/tier"
    out_path = os.path.join(output_path, "out/")

    if os.path.isdir(out_path) is False:
        os.mkdir(out_path)
    pdf_path = os.path.join(out_path, "pdf-files")
    log_path = os.path.join(out_path, "log-files")

    for out_dir in ["log-files", "pdf-files", "pkl-files"]:
        if out_dir not in os.listdir(out_path):
            os.mkdir(out_path + out_dir)
        dirs = ["pdf-files", "pkl-files"]
        if out_dir in dirs:
            for out_subdir in ["par-vs-time", "heatmaps"]:
                if os.path.isdir(f"{out_path}{out_dir}/{out_subdir}") is False:
                    os.mkdir(f"{out_path}{out_dir}/{out_subdir}")

    plot_path = pdf_path + "/par-vs-time"
    map_path = pdf_path + "/heatmaps"

    time_cut = timecut.build_timecut_list(time_window, last_hours)
    if len(time_cut) != 0:
        start, end = timecut.time_dates(time_cut)
        log_name = f"{log_path}/{exp}-{period}-{run}-{datatype}_{start}_{end}.log"
    else:
        log_name = f"{log_path}/{exp}-{period}-{run}-{datatype}.log"

    # set up logging to file
    logging.basicConfig(
        filename=log_name,
        level=logging.INFO,
        filemode="w",
        format="%(levelname)s: %(message)s",
    )
    # set up logging to console
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(asctime)s:  %(message)s")
    console.setFormatter(formatter)
    logging.getLogger("").addHandler(console)

    logging.error(
        f'Started compiling at {(datetime.now()).strftime("%d/%m/%Y %H:%M:%S")}'
    )
    select_and_plot_run(path, plot_path, map_path)
    logging.error(
        f'Finished compiling at {(datetime.now()).strftime("%d/%m/%Y %H:%M:%S")}'
    )
