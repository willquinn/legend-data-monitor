# Automatic generation of plots

This basic example file can be used to automatically generate monitoring plots, based on new .lh5 dsp/hit files appearing in the production folders. Slow Control data are automatically retrieved from the database (you need to provide the port you are using to connect to the database together with the password you can find on Confluence).

You need to specify the period and run you want to analyze in the script. You can then run the code through

```console
$ python main_sync_code.py
```

The output text is saved in an output file called "output.log".

## Automatic running

### How to set up a cronjob

You can run this command as a cronejob. On terminal, type

```console
$ crontab -e
```

and add a new line in this file of the following type:

```console
0 */6 * * * rm output.log && python main_syc_code.py >> output.log 2>&1
```

This will automatically look for new processed .lh5 files every 6 hours for instance.
You need to specify all input and output paths within the script itself.


### How to set up a bash script
If the crontab command is not available on your cluster, you can use the provided run script (`automatic_run.sh`) to run an infinite `while true` loop:

```bash
#!/bin/bash
while true; do
  python <path>/main_sync_code.py --cluster nersc --ref_version tmp-auto --pswd_email <insert_pswd>
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
