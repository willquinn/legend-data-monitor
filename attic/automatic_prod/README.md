# Automatic generation of plots

This basic example file can be used to automatically generate monitoring plots, based on new .lh5 dsp/hit files appearing in the production folder (the processing version can be specified at input).

To run the script, you have to parse different inputs - you can check them via `$ python main_sync_code.py --help`. For automatic generation of plots on lngs, use

```console
$ python main_sync_code.py --cluster nersc --ref_version tmp-auto --rsync_path /global/cfs/cdirs/m2676/data/lngs/l200/public/prodenv/prod-blind/ --output_folder /global/cfs/cdirs/m2676/data/lngs/l200/public/prodenv/prod-blind/ --chunk_size 30 --pswd_email <password>
```

Notice you can provide the password to access the `legend.data.monitoring@gmail.com` account for sending automatic emails to a list of designed people for any parameter out of range (eg. energy gain).
The run and period to inspect can also be specified by parsing the desired values (eg. p03 r000):

```console
$ python main_sync_code.py --cluster nersc --ref_version <ref> --rsync_path <path1> --output_folder <path2> --chunk_size 30 --pswd_email <password> -p p03 -r r000
```

HDF files will be stored under `<path2>/<ref>/generated/plt/phy/<period>/<run>`.
Monitoring shelve (and pdf) files will be stored under `<path2>/<ref>/generated/mtg/phy/<period>/`.

You can also enable the saving of pdf files for monitoring plots via `--pdf True`.
You can also enable a fixed y-zoom in $\pm$3 keV by using `--zoom True`.
You can change the value at which evaluating the gain differences by giving the new value `--escale <value>` as input; the default value is 2039 keV ($^{76}$Ge Q$_{\beta\beta}$).

## Slow Control data
Slow Control data are automatically retrieved from the database (you need to provide the port you are using to connect to the database together with the password you can find on Confluence).
This will only work if you run the script at the LNGS cluster, ie if you use `--cluster lngs` (default).
Notice that not always you want to retrieve data, so in order to so you have to add the flag `--sb True` (default: False).

# Automatic running

## How to set up a cronjob

You can run this command as a cronejob. On terminal, type

```console
$ crontab -e
```

and add a new line in this file of the following type:

```console
0 */6 * * * rm <path>/output.log && python <path>/main_syc_code.py <parse_inputs> >> <path>/output.log 2>&1
```

This will automatically look for new processed .lh5 files every 6 hours for instance (parse all the necessary inputs when you run the main code) and save the terminal output in a respective .log file for potential checks of issues if the code stops running.
The command will remove the .log file if previously generated (you can skip this first step if wanted).


## How to set up a bash script
If the crontab command is not available on your cluster, you can use the provided run script (`automatic_run.sh`) to run an infinite `while true` loop:

```bash
#!/bin/bash
while true; do
  python <path>/main_sync_code.py <parse_inputs>
  echo "Running job at $(date)"
  sleep 3600  # every hour
done
```

Here, you can change the absolute path to your `main_sync_code.py`, the name of the cluster (either `lngs` or `nersc`), the processing version, the password to access `legend.data.monitor@gmail.com` (in order to send automatic alerts via email), the time (in seconds) every which you want to execute the python command (here set to 1 H).

In order to run the above script in a resilient way such that survives your logout or SSH disconnects, run it like this:

```console
$ nohup ./automatic_run.sh > output.log 2>&1 &
```

If you want to stop the process, you have first to find the associated process ID (PID) with one of these commands:

```console
ps aux | grep automatic_run.sh
```

or more specifically:

```console
pgrep -f automatic_run.sh
```

This will return the process ID(s) (e.g., `12345`).

Once you have the PID, stop it like this:

```console
kill 12345
```

# Keys to ignore

An external file `inore-keys.json` with information about time ranges to remove from inspected data is retrieved from `../src/legend_data_monitor/settings/`.
The structure of this file is of the following type:

```json
{
    "p03": {
        "start_keys": ["20230327T145702Z", "20230406T135529Z"],
        "stop_keys": ["20230327T145751Z", "20230406T235540Z"]
    },
    ...
```

where for instance we remove all file keys falling in the time range from `20230327T145702Z` (included) to `20230327T145751Z` (excluded), and `20230406T135529Z` (included) to `20230406T235540Z` (excluded).
