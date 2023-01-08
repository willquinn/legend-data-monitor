How to produce plots
====================

After the installation, a executable is available at ``~/.local/bin``.
The instruction for plotting given parameters of given detector types and within a given time
range are collected in ``src/legend_data_monitor/settings/lngs-config.json``.
In the folder ``src/legend_data_monitor/settings/``, one can find other json files that do not
need any modification containing a draft of the HPGe channel map (``L60-p01-r022-T%-all-config.json``),
a draft of the SiPM channel map (``SiPM-config.json``), style info for plots (``plot-settings.json``),
and info for available parameters one can plot (``par-settings.json``) such as units/labels/thresholds/etc.


Configuration file
------------------
The core of *legend-data-monitor* is the configuration file. If modified, one can plot -either in 2D or 3D-
the time variation of parameters specified in that json file.
In the following, we describe the structure of this json file in detail.
First of all, one can specify the type of run one wants to study, plus the absolute path to processed lh5 files
(``lh5-files``), orca files (``orca-files``), channel maps (``geds-config``, ``spms-config``), output folder
(``output``), plus the processing version (``version``) and the period (``p01``):

.. code-block:: json

  {
  "run_info": {
    "exp": "l60",
    "path": {
      "lh5-files": "/data1/shared/l60/l60-prodven-v1/prod-ref/",
      "version": "v06.00",
      "orca-files": "/data1/shared/l60/l60-daq/daq-v01/",
      "geds-config": "/data1/users/calgaro/legend-data-monitor/src/legend_data_monitor/settings/L60-p01-r022-T%-all-config.json",
      "spms-config": "/data1/users/calgaro/legend-data-monitor/src/legend_data_monitor/settings/SiPM-config.json",
      "output": "/data1/users/calgaro/legend-data-monitor/out/"
    }
  },
  "period": "p01",
  // ...

A first selection of runs or files one wants to include in the time evolution plots can be done in:

.. code-block:: json

  "run": "",
  "file_list": "",
  "datatype": "phy",
  // ...

.. note::
  * ``run`` can either be a string (eg. ``"r001"``) or a list of strings (eg. ``["r001", "r002"]``)
  * ``file_list`` can either the path to a file containing one key per line, or a list of keys (eg. ``["l60-p01-r022-phy-20220825T091921Z", "l60-p01-r022-phy-20220825T101943Z"]``)

One can also decide which type of detector to plot ('spms'=SiPMs, 'geds'=HPGe, 'ch000'=channel that records HW pulser and FC trigger events):

.. code-block:: json

  "det_type": {
    "spms": false,
    "geds": true,
    "ch000": true
  },
  // ...

Later, one can specify the parameter(s) they want to plot, separately for each type of detector:

.. code-block:: json

  "par_to_plot": {
    "README": "...",
    "spms": ["energy_in_pe", "energies"],
    "geds": ["baseline"],
    "ch000": ["wf_max"],
    // ...

A cut over pulser/trigger events can be applied to either keep these events (``keep_puls_pars``) or discard those events
and keep only the physical ones (``keep_phys_pars``). The selection is done for every parameter; if none of the two options
is applied, all events, i.e. both pulser/trigger and physical events, will be kept:

.. code-block:: json

    "pulser": {
      "README": "...",
      "keep_puls_pars": ["uncal_puls", "baseline", "wf_max"],
      "keep_phys_pars": ["K_lines", "event_rate"]
    },
    // ...

Quality cuts, if available, can be enabled separately for each detector type (note: this is available only for HPGe diodes)
by setting them to ``true``:

.. code-block:: json

    "quality_cuts": {
      "README": "...",
      "spms": false,
      "geds": false,
      "ch000": false,
      //...
    },
    // ...

Since for different processing versions different quality cuts were enabled, the following code block specifies
which method is enabled and for which version. When ``isQC_flag`` is active for the version of data under study,
keep in mind that you need to specify which flag you want to use as a quality cut (here, for instance, we used
``is_valid_0vbb``).

.. code-block:: json

    "quality_cuts": {
      //...
      "version": {
        "README": "Depending on the selected version of files, different methods of quality cuts are enabled in hit files. Specify below the versions that use different hit flags for quality cuts.",
        "QualityCuts_flag": {
          "apply_to_version": "<=v06.00"
        },
        "isQC_flag": {
          "which": "is_valid_0vbb",
          "apply_to_version": ">v06.00"
        }
      }
    },
    // ...

Since parameters can be plotted both as absolute values (e.g. A/E) or percentage variations with respect to an average -typically
evaluated over the first entries of a run or a given time rangte- (e.g. baseline), there is the possibility to specify which parameter
one wants to plot in absolute value:

.. code-block:: json

    "plot_values": {
      "README": "...",
      "no_variation_pars": ["event_rate", "K_lines", "AoE_Classifier", "AoE_Corrected", "wf_max"]
    },
    // ...

The next entry is used to add additional info - that can be modified by a user - for given parameters:

.. code-block:: json

    "par-info": {
      "event_rate": {
        "README": ...",
        "dt": 600,
        "units": "Hz"
      }
    }
  },
  // ...

Two options are available for displaying the time evolution of some parameters: 2D or 3D plots (thus, specify
here for which parameters you want to adopt a 3D representation).
The option ``par_average``, if enabled, evaluates the parameter average over ``avg_interval`` minutes.
In the final plot, the parameter is plotted as a function of the time for each timestamp entry (in gray)
together with the averaged entries (in colours).

.. code-block:: json

  "plot_style": {
    "README": "...",
    "three_dim_pars": [],
    "par_average": true,
    "avg_interval": 10
  },
  // ...

.. important::

  3D plots always show the averaged entries of a given parameter, with the average being computed over ``avg_interval`` minutes.
  Differently from 2D plots, we do not plot all entries together with averaged entries. If you want to look at all entries, you
  must set ``"par_average": false``.

.. attention::

  Not all parameters can be plotted in 3D, e.g. the event rate or the time variation of energies around
  K lines are difficult to inspect when plotted in 3D. In general, the 3D visualization helps in comparing
  different channels of a given string, but it tends to be more difficult to inspect values along the z-axis.
  Changing the rotation angles could help inspecting the 3D plot.
  In general, zooms over given ranges are not so trivial.

.. attention::

  The 3D option is available for all detector types but SiPMs. In general, maps are used to represent the
  available SiPM parameters (e.g. energy or trigger position) as a function of time.
  The event rate time evolution is always plotted using the 2D option.

Another time selection can be done by defining a time window of interest, which can be done in two ways
(enable one by setting ``"enabled": true``): ``time_window`` let you
choose the start time and stop time in which you want to inspect a given parameter; ``last_hours`` will print
entries that lie within the last ``days`` : ``hours`` : ``minutes`` (e.g., with this example, you select only
those entries that lie within the last 48 days from now).
If both analysis are set to 'false', then no time cuts are applied (but they still could be applied through
``run`` or ``file_keys``, as already stated above).

.. code-block:: json

  "time_window": {
    "enabled": true,
    "start_date": "22/09/2022",
    "start_hour": "09:34:00",
    "end_date": "22/09/2022",
    "end_hour": "16:10:00"
  },
  "last_hours": {
    "enabled": false,
    "prod_time": {
      "days": 48,
      "hours": 0,
      "minutes": 0
    }
  },
  // ...

Going higher and higher in Ge mass means dealing with larger and larger number of HPGe channels.
In order to reduce the final number of plots at which one has to look during shifts, we can set fixed
threshold separately for each parameter and detector type and plot only "problematic" detectors, i.e.,
detectors that overcame/undercame the threshold set a priori.

.. attention::

  At the moment, this is partially implemented. A full integration will be done in correspondence
  of threshold determination and inclusion of statuses heatmaps.

.. code-block:: json

  "status": {
    "README": "...",
    "spms": false,
    "geds": false,
    "ch000": false
  },
  // ...

The time format shown in plots can be chosen among some available options.
If verbose is 'true', `logging <https://docs.python.org/3/library/logging.html>`_ messages will be printed on terminal.

.. code-block:: json

  "time-format": {
    "README": "...",
    "frmt": "day/month-time"
  },
  "verbose": true,
  //...

It could happen that some channels are not present in dsp/hit files.
Here you explicitly specify it for each detector type which are the missing channels:

.. code-block:: json

  "no_avail_chs": {
    "geds": [24, 10, 41],
    "spms": [49, 71, 72, 81, 91, 50, 70, 73, 80, 83, 85, 47]
  }
