This basic example file can be used to automatically generate monitoring plots, based on new .lh5 dsp/hit files appearing in the production folders. Slow Control data are automatically retrieved from the database (you need to provide the port you are using to connect to the database together with the password you can find on Confluence).

You need to specify the period and run you want to analyze in the script. You can then run the code through

```console
$ python main_sync_code.py
```

The output text is saved in an output file called "output.log".

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
