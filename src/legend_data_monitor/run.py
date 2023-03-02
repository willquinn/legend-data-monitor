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
      $ legend-data-monitor --help # help section

    Example JSON configuration file:
    .. code-block:: json
        {
            "dataset": {
                "exp": "l60",
                "period": "p01",
                "version": "v06.00",
                "path": "/data1/shared/l60/l60-prodven-v1/prod-ref",
                "type": "phy",
                "selection": {
                    "runs": 25
                }
            },
            "subsystems": {
                "pulser": {
                    "quality_cut": false,
                    "parameters": ["baseline"],
                    "status": "problematic / all ?"
                }
            },
            "plotting": {
                "output": "dm_out",
                "sampling": "3T",
                "parameters": {
                    "baseline": {
                        "events": "all",
                        "plot_style" : "histogram",
                        "some_name": "absolute"
                    }
                }
            },
            "verbose": true
        }

    Otherwise, you can provide a path to a file containing a list of keys of the format: {exp}-{period}-{run}-{data_type}-{timestamp}.
    """
    parser = argparse.ArgumentParser(
        prog="legend-data-monitor", description="Software's command-line interface."
    )

    # global options
    parser.add_argument(
        "--version",
        action="store_true",
        help="""Print version and exit (NOT IMPLEMENTED).""",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="""Increase the program verbosity (NOT IMPLEMENTED).""",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="""Increase the program verbosity to maximum (NOT IMPLEMENTED).""",
    )

    subparsers = parser.add_subparsers()

    # functions for different purpouses
    add_user_config_parser(subparsers)
    add_auto_prod_parser(subparsers)

    if len(sys.argv) < 2:
        parser.print_usage(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    """
    if args.verbose:
        legend_data_monitor.logging.setup(logging.DEBUG)
    elif args.debug:
        legend_data_monitor.logging.setup(logging.DEBUG, logging.root)
    else:
        legend_data_monitor.logging.setup()

    if args.version:
        print(legend_data_monitor.__version__)
        sys.exit()
    """

    args.func(args)


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
