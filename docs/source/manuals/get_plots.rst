How to produce plots
====================

How to run it
-------------
After the installation, a executable is available at ``~/.local/bin``.
The instruction for plotting given parameters of given detector types and within a given time
range are collected in a configuration files under ``src/legend_data_monitor/settings/``.
There, one can find other json files that do not
need any modification containing either style info for plots or info for available parameters one can plot.
Run it via:

.. code-block::
  $ legend-data-monitor <user_config_of_choice.json>


Configuration file
------------------
The core of *legend-data-monitor* is the configuration file. If modified, one can plot either
the time variation or distribution of parameters specified in the configuration file.
In the following, we describe the structure of this configuration file in detail.


Example config
~~~~~~~~~~~~~~
.. code-block:: json
 {
     "dataset": {
         "exp": "l200",
         "period": "p02", // period
         "version": "v06.00", // processing version
         "path": "/data1/users/marshall/prod-ref", // absolute path to processed lh5 files
         "type": "cal", // data type (either cal, phy, or ["cal", "phy"])
         "selection": {
             "start": "2023/01/26 03:30:00", // time cut (here based on start&stop)
             "end": "2023/01/26 08:00:00"
         }
     },
     "subsystems": {
         "pulser": { // type of detector to plot (geds, spms, pulser)
             "quality_cut": false, 
             "parameters": "wf_max_rel", // parameters to plot
             "status": "problematic / all ?"
         }
     },
     "plotting": {
         "output": "/home/redchuk/data_monitor/dm_out", // output folder
         "sampling": "3T",
         "parameters": {
             "wf_max_rel": {
                 "events": "all",
                 "plot_style" : "per channel",
                 "some_name": "absolute"
             }
         }
     },
     "verbose": true
 }


`dataset` settings
~~~~~~~~~~~~~~~~~~

- `exp`: experiment, in lowercase (`l60` or `l200`)
- `period`: format `p0X`. Note: not needed for `DataLoader` as it finds period by itself based on provided selection (see below), only used in output filename -> may be removed
- `version`: version of `pygama` (?), needed for `DataLoader` to look in the desired path
- `path`: path to `prod-ref`
- `type`: type of data, physics (`phy`) or calibration (`cal`). Possible to use one (`"phy"`) or both to make one dataset (`["phy", "cal"]`)
- `selection`: time window to select data1

.. note::
  Time selection is based on:
  - `"start"` and `"end"` in format `YYYY/MM/DD hh:mm:ss`;
  - `"timestamps"` in format `YYYYMMDDThhmmssZ`, either single or a list of timestamps; 
  - `"runs"`: run in integer format, single (e.g., ``10``) or a list of runs (e.g., ``[10, 11]``)

.. note::
  Note: currently taking range between earliest and latest i.e. also including the ones in between that are not listed, will be modified to either 

  1. require only two timestamps as start and end, or 
  2. get only specified timestamps (strange though, because would have gaps in the plot)

  The same happens with run selection.

.. note::
  If you load L200 data but accidentally mark `exp` as `l200`, L200 channel map will be loaded, and the code may or may not crash, 
  most likely not but the mapping would simply be wrong.


`subsystem` settings
~~~~~~~~~~~~~~~~~~~~

Subsystems to be plotted: `geds` or `pulser`, `spms` (not implemented yet due to `DataLoader` not loading SiPM data). For each subsystem to be plotted, specify

- `"quality_cut"`: boolean, applying quality cut to data or not. Note: might be per parameter, not per subsystem, in that case would be moved to `plotting.parameters` (see below). Functionality not tested yet
- `"parameters"`: one or multiple parameters of interest to be plotted for this subsystem. Specify type of events to select from data, plot style etc. for this parameter in `plotting.parameters`  (see **2.4. `plotting` settings**). In addition to any parameter present in `lh5`, the following special parameters are implemented:
    - `"wf_max_rel"`: relative difference between `wf_max` and baseline
    - `"event_rate"`: event rate calculated in windows specified in the field `"sampling"` under `plotting.parameters`. See **How to add new parameters** to define your own one
- `"status"`: which channels to plot: all, problematic, or good. Not implemented yet

More that one subsystem can be entered. Example:

.. code-block:: json
    "subsystems": {
        "pulser": {
            "quality_cut": false,
            "parameters": "wf_max_rel",
            "status": "problematic / all ?"
        },
        "geds": {
            "quality_cut": false,
            "parameters": "baseline",
            "status": "problematic / all ?"
        }
    }


`plotting` settings
~~~~~~~~~~~~~~~~~~~

- `"output"`: path to where plots will be saved. Will create subfolders in given path for different outputs. Will be created if does not exist.
- `"sampling"`: what time window to take for averaging in time. Format `"NA"` where `N` is an integer, and `A` is D for days, H for hours, T for minutes (since M stands for months). Corresponds to the format required for `DataFrame.resample()` function, might be changed to more human-like format (e.g. `"3 minutes"`). Applies only to the `"per_channel"` and `"event_rate"` style plots (see below), but required to be entered even if different plot style is used. Will be changed in the future i.e. moved to `plotting.parameters` (see below) and will apply only for relevant plot styles.
- `"parameters"`: settings for plotting a given parameter
  - `"events"`: what events to keep, `"all"`, `"pulser"` (events flagged as pulser based on AUX channel), `"phy"` (physical i.e. non-pulser events), or `"K_lines"` (K lines selected based on energy). See **6.** **How to add new event types** to add a new selection.
  - `"plot_style"`: style of plotting. Available styles:
    - `"per_channel"`: plot parameter VS time for each channel grouped by location (string or fiber), as well as mean sampled in window given in plot settings
    - `"histogram"`: plot distribution of given parameter. Currently for all channels (used only for pulser which only has one channel present). Will be modified to plot per channel
    - `"all channels"`: same as "per channel" but all channels in one plot with labels in legend (works for small selections of data)
  - `"some_name"`: plot absolute value of the parameter, or variation from the mean. Only implemented for `"per_channel"` plot style. Currently required even if the plot style is not `"per_channel"`, will be fixed in the future. Also looking for a suitable name for this json field

If multiple parameters are plotted for the same subsystem, or multiple subsystems, specify settings for both; example:

.. code-block:: json
    "plotting": {
        "output": "/home/redchuk/data_monitor/dm_out",
        "sampling": "3T",
        "parameters": {
            "wf_max_rel": {
                "events": "all",
                "plot_style" : "histogram",
                "some_name": "absolute"
            },
            "baseline": {
                "events": "pulser",
                "plot_style" : "per channel",
                "some_name": "variation"
            }
        }
    }


How to add new plot styles
--------------------------

Define config keyword
~~~~~~~~~~~~~~~~~~~~~

Each plot style is described by a unique keyword. Define user config keyword for the new plot style under `plotting.parameters` for the given parameter under `plot_style`. For example, `"per channel"`:

.. code-block:: json
    "plotting": {
        "parameters": {
            "baseline": {
                "events": "pulser",
                "plot_style" : "per channel",
                "some_name": "variation"
    }


Write a plotting function
~~~~~~~~~~~~~~~~~~~~~~~~~

Write a function that makes a plot in the new style in `plotting.py`, for example `plot_ch_par_vs_time()`. Each plotting function must take exactly two arguments: a `ParamData` object, and a `PdfPages` object.
.. code-block:: python
def plot_ch_par_vs_time(pardata, pdf)

The function plots a single parameter data among the ones provided in the user conig json under `"parameters"`, also using other standard columns loaded for any parameter (see below).

This is done to provide a homogeneous and therefore flexible pattern in the code that allows automatically calling respective plotting functions based on the keyword, independently of the plotting style (see step 3.2).

In order to write this function, you need to know the structure of the `ParamData` class defined in `parameter_data.py`. In short, `ParamData.data` is a `DataFrame` containing a column with data for given parameter + channel, name, location, position and datetime. The `ParamData` object also contains other attributes useful for plotting in addition to the data table (see **4. Parameter Data class**).

Map the keyword to the function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Map the newly written function to the corresponding keyword in the dictionary `PLOT_STYLE` in the bottom of `plotting.py`.

For example, plot style "per channel" corresponds to the function `plot_ch_par_vs_time(pardata, pdf)`.

.. code-block:: python
PLOT_STYLE = {
    'per channel': plot_ch_par_vs_time,
}

Parameter Data class
--------------------

The `ParamData` class contains the following attributes:

1. `param`: the name of the parameter in question e.g. `"baseline"`

2. `subsys`: the name of the subsystem (`"geds"`, `"spms"`, or `"pulser"`) the parameter data is taken from

3. `locname`: the name of the "location" for the subsystem (`"string"` for geds, `"fiber"` for spms, `""` empty string for pulser)

4. `plot_settings`: plot settings for given parameter, taken from the user config json e.g.

  .. code-block:: python
   {
       "events": "pulser",
       "plot_style" : "per channel",
       "some_name": "variation"
   }

5. `sampling`: sampling taken from user config json e.g. `"3T"` for 3 minutes

6. `data`: a `DataFrame` table with data for given parameter, containing the following columns:

   - `datetime`: a python `datetime` type column in UTC

   - `channel`: FlashCam channel number

   - `name`: name of the channel, depending on sybsystem: `DOOXXXM` for geds, `SXXX` for spms, `AUXXX` for pulser

   - `location`: number of string/fiber for geds/spms, 0 for pulser (dummy)

   - `position`: position of geds/spms in string/fiber, 0 for pulser (dummy)

   - `flag_pulser`: a boolean flag that marks the event as pulser; the events in this table are already subselected based on user config json plotting settings for this parameter: pulser events (all column will be `True`), physical i.e. non-pulser events (all column will be `False`), or all events (mixed values in column)

   - `<parameter>`: a column with data for the single selected parameter (only one-at-a-time parameter plotting is set up in `control_plots.py`)

Example

.. code-block:: bash
       channel                      datetime  flag_pulser  baseline     name  location  position
0            2 2022-09-28 09:11:50.208880901         True     15138  V08682B         8         1
1            2 2022-09-28 09:12:10.207568884         True     15149  V08682B         8         1
2            2 2022-09-28 09:12:30.206283808         True     15125  V08682B         8         1
3            2 2022-09-28 09:12:50.205015898         True     15134  V08682B         8         1
4            2 2022-09-28 09:13:10.203716755         True     15093  V08682B         8         1
...        ...                           ...          ...       ...      ...       ...       ...
16095       43 2022-10-02 20:37:13.169144869         True     14746  V07647B         7         8
16096       43 2022-10-02 20:37:33.167859793         True     14930  V07647B         7         8
16097       43 2022-10-02 20:37:53.166505814         True     15312  V07647B         7         8
16098       43 2022-10-02 20:38:13.165241718         True     15008  V07647B         7         8
16099       43 2022-10-02 20:38:33.163988829         True     15264  V07647B         7         8

[16100 rows x 7 columns]

This class is constructed in such a way to provide **everything a plotting function needs to know to make a plot**. If something is missing for a plot you need, feel free to add an attribute or method to `ParamData`, or contact @sagitta42 (Mariia Redchuk) with technical assistance on how to best implement what you need.

[*Example*] since `ParamData` contains only one parameter of interest, if you want to define a plotting function that need to parameters (e.g. one parameter VS the other), there might be two ways of going about it:

- modify `ParamData` to contain two parameters in the table (corresponding modifications to user config keywords needed as well)
- create a function different to `control_plots.py` that would loop over parameters and create two `ParamData` objects
- ...

@sagitta42 can help you figure out the most convenient way and the technicalities.

How to add new parameters
-------------------------

- Add plot info to `settings/par-settings.json`

  .. code-block:: json
  "<param_name>":{
      "label": "<label>",
      "units": "<unit>"
    },

  In principle this should be optional, and if not provided, parameter name should be taken as label with no units (WIP)

- If this is an lh5 parameter, that's all that's needed.

- If this is a special custom parameter (such as "event_rate" or "wf_max_rel")

  - Specify in `subsystem.py` dictionary `SPECIAL_PARAMETERS` which lh5 parameters are needed to be loaded to calculate the special parameter, for example

    .. code-block:: python
    SPECIAL_PARAMETERS = {
        'wf_max_rel': ['wf_max', 'baseline'],
        'event_rate': None
    }

  - Define the calculation in `parameter_data.ParamData.special_parameters()`. For example, "wf_max_rel" is defined as follows:

    .. code-block:: python
    def special_parameters(self):
        if self.param == 'wf_max_rel':
            # calculate wf max relative to baseline
            self.data['wf_max_rel'] = self.data['wf_max'] - self.data['baseline']
        elif self.param == ... :
            ...

## 6. How to add new event types

Define selection under ``parameter_data.ParamData.special_parameters()` based on the keyword for the new event type. For example, selecting pulser/physical events only is defined as follows

.. code-block:: python
def select_events(self):
    # do we want to keep all, phy or pulser events?
    if self.plot_settings['events'] == 'pulser':
        print('... keeping only pulser events')
        self.data = self.data[ self.data['flag_pulser'] ]
    elif self.plot_settings['events'] == 'phy':
        self.data = self.data[ ~self.data['flag_pulser'] ]

Note that selecting K lines is a bit more complex, because in order to do that in `ParamData`, already before that `Subsystem` should be notified to load energy column. Current implementation a bit cumbersome, feel free to ask for tips if your new event type involves lh5 parameters or is complex in some other way. Currently K lines is implemented as follows:
- in `subsystem.py` define what parameter is needed to loaded from lh5 to do the selection

  .. code-block:: python
  SPECIAL_PARAMETERS = {
      "K_lines": 'cuspEmax_ctc_cal',
      ...
  }

- in `Subsystem` remember that for later by creating a bool whether we need to load that parameter or not

  .. code-block:: python
  self.k_lines = False
  for param in self.parameters:
      # if K lines is asked, set to true
      self.k_lines = self.k_lines or (config.plotting.parameters[param]['events'] == 'K_lines')

- In `Subsystem.get_data()` check that bool and add column to be loaded if needed

  .. code-block:: python
  # add K_lines energy if needed
  if self.k_lines:
      params.append(SPECIAL_PARAMETERS['K_lines'][0])

- Then, as for non-complex parameters, add a condition in `ParamData.select_events()`

  .. code-block:: python
  elif self.plot_settings['events'] == 'K_lines':
      # non-pulser events only
      self.data = self.data[ ~self.data['flag_pulser'] ]
      # energy can be flexibly defined, not always cusp Emax
      energy = SPECIAL_PARAMETERS['K_lines'][0]
      # energy cut
      self.data = self.data[ (self.data[energy] > 1430) & (self.data[energy] < 1575)] 