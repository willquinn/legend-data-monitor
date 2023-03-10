How to inspect plots
====================

Output files
------------

After the code has run, shelve object files containing the data and plots generated for the inspected parameters/subsystems
are produced, together with a pdf file containing all the generated plots and a log file containing running information. In particular,
the last two files are created for each inspected subsystem (pulser, geds, spms).

Files are usually collected in the output folder specified in the ``output`` config entry:

.. code-block:: json

  {
  "output": "<some_path>/out",
  // ...

Then, depending on the chosen dataset (``experiment``, ``period``, ``version``, ``type``, time selection),
different output folders can be created. In general, the output folder is structured as it follows:

.. code-block::

  <some_path>/out/
    └── prod-ref
      └── <version>
        └── generated
          └── plt
            └── <type>
              └── <period>
                └── <time_selection>
                  ├── <experiment>-<period>-<time_selection>-<type>-<subsystem>.pdf
                  ├── <experiment>-<period>-<time_selection>-<type>-<subsystem>.log
                  └── <experiment>-<period>-<time_selection>-<type>.{dat,bak,dir}


Files are usually saved using the following format ``exp-period-datatype-time_interval``:

- ``experiment`` identifies the experiment (e.g. *l200*);
- ``period`` identifies a certain period of data taking (e.g. *p01*);
- ``time_selection`` can differ depending on the selected time range (see below for more details);
- ``type`` denotes the run type (e.g. *phy*, *cal*, or *cal_phy* if multiple types are selected in a row).

.. note::

  ``time_selection`` can assume one of the following formats, depending on what we put as a time range into ``dataset``:

  - if ``{'start': '20220928T080000Z', 'end': '20220928T093000Z'}`` (start + end), then <time_selection> = ``20220928T080000Z_20220928T093000Z``;
  - if ``{'timestamps': ['20230207T103123Z']}`` (one key), then <time_selection> = ``20230207T103123Z``;
  - if ``{'timestamps': ['20230207T103123Z', '20230207T141123Z', '20230207T083323Z']}`` (multiple keys), then <time_selection> = ``20230207T083323Z_20230207T141123Z`` (min/max timestamp interval)
  - if ``{'runs': 1}`` (one run), then <time_selection> = ``r001``;
  - if ``{'runs': [1, 2, 3]}`` (multiple runs), then <time_selection> = ``r001_r002_r003``.


Shelve output objects
~~~~~~~~~~~~~~~~~~~~~
*Under construction... (structure might change over time, but content should remain the same)*

The output object ``<experiment>-<period>-<time_selection>-<type>.{dat,bak,dir}`` has the following structure:

.. code-block::

  <experiment>-<period>-<time_selection>-<type>
      └── monitoring
            ├── pulser // event type
            │   └── cuspEmax_ctc_cal // parameter
            │   	├── 4 // this is the channel FC id
            │   	│       ├── values // these are y plot-values shown
            │           │       │     ├── all // every timestamp entry
            │           │       │     └── resampled // after the resampling
            │           │	├── timestamp // these are plot-x values shown
            │           │       │     ├── all
            │           │       │     └── resampled
            │           │ 	├── mean // mean over the first 10% of data within the range inspected by the user
            │   	│	└── plot_info // some useful plot-info: ['title', 'subsystem', 'locname', 'unit', 'plot_style', 'parameter', 'label', 'unit_label', 'time_window', 'limits']
            │   	├── ...other channels...
            │   	├── df_geds // dataframe containing all geds channels for a given parameter
            │   	├── <figure> // Figure object
            │   	└── map_geds // geds status map (if present)
            ├─all
            │   └── baseline
            │   	├── ...channels data/info...
            │   	└── ...other summary objects (df/status map/figures)...
            │   └── wf_max
            │   	└── ...
            └──phy
                └── ...

One way to open it and inspect the saved objects for a given channel, eg. ID='4', is to do

.. code-block:: python

  import shelve

  with shelve.open("<experiment>-<period>-<time_selection>-<type>") as file:
    # get y values
    all_data_ch4 = file['monitoring']['pulser']['baseline']['4']['values']['all']
    resampled_data_ch4 = file['monitoring']['pulser']['baseline']['4']['values']['resampled']
    # get info for plotting data
    plot_info_ch4 = file['monitoring']['pulser']['baseline']['4']['plot_info']

To get the corresponding dataframe (containing all channels with map/status info and loaded parameters), you can use

.. code-block:: python

  import shelve

  with shelve.open("<experiment>-<period>-<time_selection>-<type>") as file:
    df_geds = file['monitoring']['pulser']['baseline']['df_geds'].data

To open the saved figure for a given parameter, one way to do it is through

.. code-block:: python

  import io
  from PIL import Image
  with io.BytesIO(shelf['monitoring']['pulser']['baseline']['<figure>']) as obj:
    # create a PIL Image object from the bytes
    pil_image = Image.open(obj)
    # convert the image to RGB color space (to enable PDF saving)
    pil_image = pil_image.convert('RGB')
    # save image to disk
    pil_image.save('figure.pdf', bbox_inches="tight")

.. important::

The key name ``<figure>`` changes depending on the used ``plot_style`` for producing that plot. In particular,

- if you use ``"plot_style": "per channel"``, then ``<figure> = figure_plot_string_<string_no>``, where ``string_no`` is the number of one of the available strings;
- if you use ``"plot_style": "per cc4"`` or ``"per string"`` or ``"array"``, then ``<figure> = figure_plot``;
- if you use ``"plot_style": "per barrel"``, then ``<figure> = figure_plot_<location>_<position>``, where ``<location>`` is either "IB" or "OB, while ``<position>`` is either "top" or "bottom".

.. note::

  There is no need to create one shelve object for each inspected subsystem.
  Indeed, one way to separate among pulser, geds and spms is to look at channel IDs.
  In any case, the subsystem info is saved under ``["monitoring"][<event_type>][<parameter>]["plot_info"]["subsystem"]``.


Inspect plots
-------------

*Under construction*

- Near future: `Dashboard <https://legend-exp.atlassian.net/wiki/spaces/LEGEND/pages/637861889/Monitoring+Dashboard+Manual>`_ tool
- Future: notebook to interactively inspect plots (with buttons?)
