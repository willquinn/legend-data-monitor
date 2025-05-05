from __future__ import annotations

import argparse
import json
import sys

import legend_data_monitor


def main():
    """legend-data-monitor's starting point.

    Here you define the path to the JSON configuration file you want to use when generating the plots.
    To learn more, have a look at the help section:

    .. code-block:: console
      $ legend-data-monitor --help

    """
    parser = argparse.ArgumentParser(
        prog="legend-data-monitor", description="Software's command-line interface."
    )

    # global options
    parser.add_argument(
        "--version",
        action="store_true",
        help="""Print version and exit.""",
    )

    subparsers = parser.add_subparsers()

    # functions for different purpouses
    add_user_scdb(subparsers)
    add_user_config_parser(subparsers)
    add_user_bunch_parser(subparsers)
    add_user_rsync_parser(subparsers)
    add_auto_prod_parser(subparsers)

    if len(sys.argv) < 2:
        parser.print_usage(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    if args.version:
        legend_data_monitor.utils.logger.info(
            "Version: %s", legend_data_monitor.__version__
        )
        sys.exit()

    args.func(args)


def add_user_scdb(subparsers):
    """Configure :func:`.core.control_plots` command line interface."""
    parser_auto_prod = subparsers.add_parser(
        "user_scdb",
        description="""Retrieve Slow Control data from database by giving a full config file with parameters/subsystems info to plot. Available only when working in LNGS machines.""",
    )
    parser_auto_prod.add_argument(
        "--config",
        help="""Path to config file (e.g. \"some_path/config_L200_r001_phy.json\").""",
    )
    parser_auto_prod.add_argument(
        "--port",
        help="""Local port.""",
    )
    parser_auto_prod.add_argument(
        "--pswd",
        help="""Password to get access to the Slow Control database (check on Confluence).""",
    )
    parser_auto_prod.set_defaults(func=user_scdb_cli)


def user_scdb_cli(args):
    """Pass command line arguments to :func:`.core.retrieve_scdb`."""
    # get the path to the user config file
    config_file = args.config
    # get the local port
    port = args.port
    # get the password to the SC database
    password = args.pswd

    # start loading data
    legend_data_monitor.core.retrieve_scdb(config_file, port, password)


def add_user_config_parser(subparsers):
    """Configure :func:`.core.control_plots` command line interface."""
    parser_auto_prod = subparsers.add_parser(
        "user_prod",
        description="""Inspect LEGEND HDF5 (LH5) processed data by giving a full config file with parameters/subsystems info to plot.""",
    )
    parser_auto_prod.add_argument(
        "--config",
        help="""Path to config file (e.g. \"some_path/config_L200_r001_phy.json\").""",
    )
    parser_auto_prod.set_defaults(func=user_config_cli)


def user_config_cli(args):
    """Pass command line arguments to :func:`.core.control_plots`."""
    # get the path to the user config file
    config_file = args.config

    # start loading data & generating plots
    legend_data_monitor.core.control_plots(config_file)


def add_user_bunch_parser(subparsers):
    """Configure :func:`.core.control_plots` command line interface."""
    parser_auto_prod = subparsers.add_parser(
        "user_bunch",
        description="""Inspect LEGEND HDF5 (LH5) processed data by giving a full config file with parameters/subsystems info to plot. Files will be bunched in groups of n_files files each, and every time the code is run you will append new data to the previously generated ones.""",
    )
    parser_auto_prod.add_argument(
        "--config",
        help="""Path to config file (e.g. \"some_path/config_L200_r001_phy.json\").""",
    )
    parser_auto_prod.add_argument(
        "--n_files",
        help="""Number (int) of files of a given run you want to inspect at each cycle.""",
    )
    parser_auto_prod.set_defaults(func=user_bunch_cli)


def user_bunch_cli(args):
    """Pass command line arguments to :func:`.core.control_plots`."""
    # get the path to the user config file
    config_file = args.config
    # get the number of files for each cycle
    n_files = args.n_files

    # start loading data & generating plots
    legend_data_monitor.core.control_plots(config_file, n_files)


def add_user_rsync_parser(subparsers):
    """Configure :func:`.core.control_rsync_plots` command line interface."""
    parser_auto_prod = subparsers.add_parser(
        "user_rsync_prod",
        description="""Inspect LEGEND HDF5 (LH5) processed data by giving a full config file with parameters/subsystems info to plot, syncing with new produced data.""",
    )
    parser_auto_prod.add_argument(
        "--config",
        help="""Path to config file (e.g. \"some_path/config_L200_r001_phy.json\").""",
    )
    parser_auto_prod.add_argument(
        "--keys",
        help="""Path to file containing new keys to inspect (e.g. \"some_path/new_keys.filekeylist\").""",
    )
    parser_auto_prod.set_defaults(func=user_rsync_cli)


def user_rsync_cli(args):
    """Pass command line arguments to :func:`.core.control_rsync_plots`."""
    # get the path to the user config file
    config_file = args.config
    keys_file = args.keys

    # start loading data & generating plots
    legend_data_monitor.core.auto_control_plots(config_file, keys_file, "", {})


def add_auto_prod_parser(subparsers):
    """Configure :func:`.core.auto_control_plots` command line interface."""
    parser_auto_prod = subparsers.add_parser(
        "auto_prod",
        description="""Inspect LEGEND HDF5 (LH5) processed data by giving a partial config file with parameters/subsystems info to plot,\na file with a list of keys to load, and a path to the production environment.""",
    )
    parser_auto_prod.add_argument(
        "--plot_config",
        help="""Path to config file with parameters/subsystems info to plot (e.g. \"some_path/plot_config.json\").""",
    )
    parser_auto_prod.add_argument(
        "--filekeylist",
        help="""File-keylist name (e.g. \"all-l200-p02-r001-phy.filekeylist\").""",
    )
    parser_auto_prod.add_argument(
        "--prod_path",
        help="""Path to production environment (e.g. \"/data1/shared/l200/l200-prodenv/prod-ref/vXX.YY/\").\nHere, you should find \"config.json\" containing input/output folders info.""",
    )  # what if the file is not there?
    parser_auto_prod.set_defaults(func=auto_prod_cli)


def auto_prod_cli(args):
    """Pass command line arguments to :func:`.core.auto_control_plots`."""
    # get the path to the user config file
    plot_config = args.plot_config
    file_keys = args.filekeylist
    prod_path = args.prod_path

    # get the production config file
    prod_config_file = (
        f"{prod_path}config.json"
        if prod_path.endswith("/")
        else f"{prod_path}/config.json"
    )
    with open(prod_config_file) as f:
        prod_config = json.load(f)

    # get the filelist file path
    folder_filelists = prod_config["setups"]["l200"]["paths"]["tmp_filelists"][3:]
    file_keys = (
        f"{prod_path}{folder_filelists}"
        if prod_path.endswith("/")
        else f"{prod_path}/{folder_filelists}"
    )
    file_keys += args.filekeylist if file_keys.endswith("/") else f"/{args.filekeylist}"

    # start loading data & generating plots
    legend_data_monitor.core.auto_control_plots(
        plot_config, file_keys, prod_path, prod_config
    )
