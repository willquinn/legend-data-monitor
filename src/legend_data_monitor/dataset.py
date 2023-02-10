import os
import re
from datetime import timedelta


class Dataset:
    # : config.Config
    def __init__(self, config):
        #print('----------------------------------------------------')
        #print('--- Setting up dataset')
        #print('----------------------------------------------------')
        
        # e.g. path to period = path + v06.00/generated/tier (+ dsp/phy/p01 later)
        self.path = os.path.join(config.dataset.path, config.dataset.version, 'generated', 'tier')
        #print('Data path: ' + self.path)

        # determine QC cut column name based on version
        self.qc_name = (
            "isQC_flag" if config.dataset.version > "v06.00" else "QualityCuts_flag"
        )

        # type of data (phy or cal or both, always list)
        self.type = config.dataset.type
        #print('Data type: ' + ','.join(self.type))
        
        # get list of all dsp files in period to later get final file time range
        # !! not really needed except for SiPM quickfix cause of DataLoader not working
        # avoid for now because now type can be multiple
        # self.period_dsp = self.period_filelist(config)

        # get user time range in format of keys - for selection and plotting
        self.user_time_range = self.get_user_time_range(config)
        #print('User requested time range: {} - {}'.format(self.user_time_range['start'], self.user_time_range['end']))
        
        # get final time range based on dsp files available
        # !! ignore for now because there can be multiple type like both cal and phy
        self.time_range = self.user_time_range
        # self.time_range = self.get_final_time_range()
        # print('Resulting file time range: {} - {}'.format(self.time_range['start'], self.time_range['end']))

    # def period_filelist(self, config):
    #     """
    #     Get list of dsp files belonging to dataset
    #     """

    #     period_path = os.path.join(self.path, 'dsp', config.dataset.type, config.dataset.period)
    #     # list of all runs in period e.g. r027
    #     period_runs = os.listdir(period_path)
    #     # list of all files in all period runs
    #     # file format: l60-p01-r027-phy-20221002T192555Z-tier_dsp.lh5
    #     period_dsp = []
    #     for r in period_runs:
    #         run_path = os.path.join(period_path,r)
    #         run_files = os.listdir(run_path)
    #         # ?? we only want to load dsp files that also have hit level
    #         run_files = [f for f in run_files if os.path.isfile(os.path.join(run_path, f).replace('dsp', 'hit'))]
    #         period_dsp += run_files

    #     if len(period_dsp) == 0:
    #         logging.error("There are no files to inspect for data type {} period {}!".format(config.dataset.type, config.dataset.period))
    #         logging.error('The path you selected: ' + config.dataset.path)
    #         sys.exit(1)

    #     period_dsp.sort()
    #     return period_dsp

    def get_user_time_range(self, config):
        """
        Get time range requested by user converted to key format.

        Directly from input if selection mode is time range, time window, or key(s);
        from dsp files if selection mode is 'runs'.
        
        >>> dataset.get_user_time_range()
        ['20220928T080000Z','20220928093000Z']
        """
        time_range = {'start': 0, 'end': 0} # convenient for the loop
        message = 'Time selection mode: '

        # option 1: time window
        if "start" in config.dataset.selection:
            message += "time range"
            for point in time_range:
                date, time = config.dataset.selection[point].split(" ")
                time_range[point] = (
                    "".join(date.split("/")) + "T" + "".join(time.split(":")) + "Z"
                )

        elif "window" in config.dataset.selection:
            message += "time window"
            time_range["end"] = config.start_code
            days, hours, minutes = re.split(r"d|h|m", config.dataset.selection.window)[
                :-1
            ]  # -1 for trailing ''
            dt = timedelta(days=days, hours=hours, minutes=minutes)
            time_range["start"] = (
                time_range["end"].strptime("%Y%m%dT%H%M%SZ") - dt
            ).strftime("%Y%m%dT%H%M%SZ")

        # !! ToDo later: will query DataLoader by run, while other methods query by timestamp
        else:
            # keys or runs
            index = {0: "start", -1: "end"}
            field = list(config.dataset.selection.keys())[0]  # "keys" or "runs"
            lst = config.dataset.selection[field]
            lst.sort()

            for idx in index:
                # in case of keys will be timestamp string
                # in case of runs will be rXXX
                time_range[index[idx]] = (
                    lst[idx] if field == "timestamps" else "r" + str(lst[idx]).zfill(3)
                )

        return time_range

    # !! not needed except for SiPM not loading with DataLoader
    # ignore for now because diabled period_list because now type can be multiple
    # def get_final_time_range(self):
    #     # apply user time range to available dsp files
    #     selected_files = [f for f in self.period_dsp if get_key(f) > self.user_time_range['start'] and get_key(f) < self.user_time_range['end']]
    #     if len(selected_files) == 0:
    #         logging.error('No files for given time selection!')
    #         sys.exit(1)

    #     selected_files.sort()

    #     return {'start': get_key(selected_files[0]), 'end': get_key(selected_files[-1])}


# helper functions


def get_run(dsp_fname: str):
    '''Eextract run from lh5 filename.'''    
    return re.search('r-\d{3}', dsp_fname).group(0)[2:]

def get_key(dsp_fname: str):
    '''Extract key from lh5 filename.'''
    return re.search('-\d{8}T\d{6}Z', dsp_fname).group(0)[1:]    
