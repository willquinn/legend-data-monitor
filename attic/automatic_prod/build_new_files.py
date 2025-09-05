import argparse
import logging
import os
import sys

import h5py
import pandas as pd
import yaml

logger = logging.getLogger(__name__)


def main(my_path, period, run):
    data_file = os.path.join(
        my_path, "generated/plt/phy", period, run, f"l200-{period}-{run}-phy-geds.hdf"
    )

    if not os.path.exists(data_file):
        logger.debug(f"File not found: {data_file}. Exit here.")
        sys.exit()

    with h5py.File(data_file, "r") as f:
        my_keys = list(f.keys())

    info_dict = {"keys": my_keys}

    resampling_times = ["1min", "5min", "10min", "30min", "60min"]

    for idx, resample_unit in enumerate(resampling_times):
        new_file = os.path.join(
            my_path,
            "generated/plt/phy",
            period,
            run,
            f"l200-{period}-{run}-phy-geds-res_{resample_unit}.hdf",
        )
        # remove it if already exists so we can start again to append resampled data
        if os.path.exists(new_file):
            os.remove(new_file)

        for k in my_keys:
            if "info" in k:
                # do it once
                if idx == 0:
                    original_df = pd.read_hdf(data_file, key=k)
                    info_dict.update(
                        {
                            k: {
                                "subsystem": original_df.loc["subsystem", "Value"],
                                "unit": original_df.loc["unit", "Value"],
                                "label": original_df.loc["label", "Value"],
                                "event_type": original_df.loc["event_type", "Value"],
                                "lower_lim_var": original_df.loc[
                                    "lower_lim_var", "Value"
                                ],
                                "upper_lim_var": original_df.loc[
                                    "upper_lim_var", "Value"
                                ],
                                "lower_lim_abs": original_df.loc[
                                    "lower_lim_abs", "Value"
                                ],
                                "upper_lim_abs": original_df.loc[
                                    "upper_lim_abs", "Value"
                                ],
                            }
                        }
                    )
                continue

            original_df = pd.read_hdf(data_file, key=k)

            # mean dataframe is kept
            if "_mean" in k:
                original_df.to_hdf(new_file, key=k, mode="a")
                continue

            original_df.index = pd.to_datetime(original_df.index)
            # resample
            resampled_df = original_df.resample(resample_unit).mean()
            # substitute the original df with the resampled one
            original_df = resampled_df
            # append resampled data to the new file
            resampled_df.to_hdf(new_file, key=k, mode="a")

        if idx == 0:
            yaml_output = os.path.join(
                my_path,
                "generated/plt/phy",
                period,
                run,
                f"l200-{period}-{run}-phy-geds-info.yaml",
            )
            with open(yaml_output, "w") as file:
                yaml.dump(info_dict, file, default_flow_style=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Resample HDF5 file and extract metadata."
    )
    parser.add_argument("--my_path", help="Base path to generated data")
    parser.add_argument("--period", help="Period string, e.g. p14")
    parser.add_argument("--run", help="Run string, e.g. r004")

    args = parser.parse_args()

    main(args.my_path, args.period, args.run)
