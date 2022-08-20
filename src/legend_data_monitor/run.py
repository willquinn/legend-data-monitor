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
files_path = j_config[0]["path"]['lh5-files']
period = j_config[1]
run = j_config[2]
datatype = j_config[3]
det_type = j_config[4]
par_to_plot = j_config[5]
time_window = j_config[7]
last_hours = j_config[8]
verbose = j_config[11]


# for multiple detectors
def dump_all_plots_together(raw_files, time_cut, path, map_path):
    """
    Create and dump plot in single pdf and multiple pkl files.

    Description
    -----------
    Dump plots for multiple detectors (geds, spms) grouped together
    in single plot by string (geds) or inner/outer and top/bot barrel (spms).

    Parameters
    ----------
    raw_files : list
                Strings of lh5 raw files
    time_cut  : list
                List with info about time cuts
    path      : string
                Path where to save output files
    map_path  : string
                Path where to save output heatmaps
    """
    if isinstance(raw_files, str):
        raw_files = [raw_files]

    geds_dict, spms_dict, other_dict = analysis.load_channels(raw_files)

    det_status_dict = {}

    with PdfPages(path) as pdf:
        with PdfPages(map_path) as pdf_map:
            logging.info(
                f"Devo usare la variable {pdf_map} altrimenti mi crea problemi" # TOGLIERE QUESTO PEZZO DOPO AVER IMPLEMENTATO map.py
            )
            if det_type["geds"] is False and det_type["spms"] is False:
                logging.info(
                    "NO detectors have been selected! Enable geds and/or spms in config.json"
                )
                return

            # Geds plots
            if det_type["geds"] is True:
                # list of geds
                string_geds, string_geds_name = analysis.read_geds(geds_dict)
                geds_par = par_to_plot["geds"]
                if len(geds_par) == 0:
                    logging.info("Geds: NO parameters have been enabled!")
                else:
                    logging.info("Geds will be plotted...")
                    for par in geds_par:
                        for (det_list, string) in zip(string_geds, string_geds_name):
                            if len(det_list) == 0:
                                continue  # no detectors in a string
                            logging.info(f'Plotting "{par}" for string #{string}')

                            map_dict = plot.plot_par_vs_time(
                                raw_files,
                                det_list,
                                par,
                                time_cut,
                                "geds",
                                string,
                                geds_dict,
                                pdf,
                            )
                            if map_dict!=None:
                               for det, status in map_dict.items():
                                   det_status_dict[det] = status

                            if verbose is True:
                                logging.info(
                                    f"\t...{par} for geds (string #{string}) has been plotted!"
                                )
                        # map.geds_map(geds_dict, string_geds, string_geds_name, det_status_dict, map_path, pdf_map)

            # Spms plots
            if det_type["spms"] is True:
              if datatype=='cal':
                  logging.info("No SiPMs for calibration data!")
              else:
                # list of spms
                spms_merged, spms_name_merged, string_spms, string_spms_name = analysis.read_spms(spms_dict)
                spms_par = par_to_plot["spms"]
                if len(spms_par) == 0:
                    logging.info("Spms: NO parameters have been enabled!")
                else:
                    logging.info("Spms will be plotted...")
                    for par in spms_par:
                        for (det_list, string) in zip(string_spms, string_spms_name):
                            if len(det_list) == 0:
                                continue  # no detectors in a string
                            logging.info(f'Plotting "{par}" for {string} SiPMS')

                            if par == "gain":
                                plot.plot_par_vs_time_2d(
                                    raw_files,
                                    det_list,
                                    time_cut,
                                    "spms",
                                    string,
                                    spms_dict,
                                    pdf,
                                )
                            else:
                                if len(string) != 0:
                                    map_dict = plot.plot_par_vs_time(
                                        raw_files,
                                        det_list,
                                        par,
                                        time_cut,
                                        "spms",
                                        string,
                                        spms_dict,
                                        pdf,
                                    )
                            if map_dict!=None:
                               for det, status in map_dict.items():
                                   det_status_dict[det] = status

                            if verbose is True:
                                logging.info(
                                    f"\t...{par} for spms ({string}) has been plotted!"
                                )
                    #map.spms_map(spms_dict, spms_merged, spms_name_merged, det_status_dict, map_path, pdf_map)

    if verbose is True:
        logging.info(f"Plots are in {path}")
        logging.info(f"Heatmaps are in {map_path}")

    return


def select_and_plot_run(path, plot_path, map_path):
    """
    Select run and call dump_all_plots_together().

    Parameters
    ----------
    path      : string
                Path to pgt folder
    plot_path : string
                Path where to save output plots
    map_path  : string
                Path where to save output heatmaps
    """
    full_path = os.path.join(path, "raw", datatype, period, run)

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
            logging.info("Calib runs have been loaded")
    if datatype == "phy":
        runs = [file for file in lh5_files if "phy" in file]
        if verbose is True:
            logging.info("Phys runs have been loaded")

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
    path = files_path
    cwd_path = os.path.join(os.getcwd(), "out/")
    if os.path.isdir(cwd_path) is False:
       os.mkdir(cwd_path)
    pdf_path = os.path.join(cwd_path, "pdf-files")
    log_path = os.path.join(cwd_path, "log-files")

    for out_dir in ["log-files", "pdf-files", "pkl-files"]:
        if out_dir not in os.listdir(cwd_path):
            os.mkdir(cwd_path + out_dir)
        dirs = ["pdf-files", "pkl-files"]
        if out_dir in dirs:
            for out_subdir in ["par-vs-time", "heatmaps"]:
                if os.path.isdir(f"{cwd_path}{out_dir}/{out_subdir}") is False:
                    os.mkdir(f"{cwd_path}{out_dir}/{out_subdir}")

    plot_path = pdf_path + "/par-vs-time"
    map_path = pdf_path + "/heatmaps"

    time_cut = timecut.build_timecut_list(time_window, last_hours)
    if len(time_cut) != 0:
        start, end = timecut.time_dates(time_cut)
        log_name = f"{log_path}/{exp}-{period}-{run}-{datatype}_{start}_{end}.log"
    else:
        log_name = f"{log_path}/{exp}-{period}-{run}-{datatype}.log"

    logging.basicConfig(
        filename=log_name,
        level=logging.INFO,
        filemode="w",
        format="%(levelname)s: %(message)s",
    )

    logging.info(
        f'Started compiling at {(datetime.now()).strftime("%d/%m/%Y %H:%M:%S")}'
    )
    select_and_plot_run(path, plot_path, map_path)
    logging.info(
        f'Finished compiling at {(datetime.now()).strftime("%d/%m/%Y %H:%M:%S")}'
    )
