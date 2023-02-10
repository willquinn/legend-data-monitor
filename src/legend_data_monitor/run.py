from __future__ import annotations

import argparse

from . import control_plots

def main():
    """legend-data-monitor's starting point.

    Here you define the JSON configuration file you want to use when generating the plots. 
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

    """
    parser = argparse.ArgumentParser(
        prog="legend-data-monitor", description="Software's command-line interface"
    )
    # one input argument: config file
    parser.add_argument('config_file', help='Name of the configuration file you want to use')

    # load input config file
    args = parser.parse_args()
    user_config = args.config_file
    
    # start loading data & generating plota
    control_plots.control_plots(user_config)