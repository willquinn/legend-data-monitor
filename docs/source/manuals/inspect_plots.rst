How to inspect plots
====================

Output files
------------

After the code has run, pickle files containing the plots for given parameters as a function
of time are produced, together with a pdf file containing all the generated plots.

Files are usually collected in the output folder ``out/``, whose path can be specified
in ``src/legend_data_monitor/settings/lngs-config.json``:

.. code-block:: json

  {
  "run_info": {
    // ...
    "path": {
      // ...
      "output": "/data1/users/calgaro/legend-data-monitor/out/"
    }
  },
  // ...


The output folder is structured as it follows (note: here we are assuming to plot the baseline
for all germanium strings using L60 data):

::

    out/
    ├── json-files/
    │   └── l60-p01-phy_20220922T093400Z_20220922T161000Z.json
    ├── log-files/
    │   └── l60-p01-phy_20220922T093400Z_20220922T161000Z.log
    ├── pdf-files/
    │   ├── heatmaps/
    │   │   └── l60-p01-phy_20220922T093400Z_20220922T161000Z.pdf
    │   └── par-vs-time/
    │       └── l60-p01-phy_20220922T093400Z_20220922T161000Z.pdf
    └── pkl-files/
        ├── heatmaps/
        │   └── l60-p01-phy-20220922T093400Z_20220922T161000Z-baseline.pkl
        └── par-vs-time/
            └── l60-p01-phy-20220922T093400Z_20220922T161000Z-baseline-S1.pkl
            └── l60-p01-phy-20220922T093400Z_20220922T161000Z-baseline-S2.pkl
            └── l60-p01-phy-20220922T093400Z_20220922T161000Z-baseline-S7.pkl
            └── l60-p01-phy-20220922T093400Z_20220922T161000Z-baseline-S8.pkl

In particular,

* ``out/json-files/`` stores json files containing info about mean values for those parameters that were chosen to be plotted not in absolute value, but computing the percentage variations with respect to an average value evaluated over the first entries. The mean values are stored separately for each channel and parameter. The mean values listed in these files are the same ones that appear in the legend of plots.
* ``out/log-files/`` stores files with detailed info about the code compilation.
* ``out/pdf-files/`` stores pdf files collecting plots for the plotted parameters and for the enabled detector types.
* ``out/pkl-files/`` stores pkl files collecting plots for the plotted parameters and for the enabled detector types, separately for each parameter and string/barrel.
* ``heatmaps/``  files store maps containing info about statuses of each HPGe/SiPM channel; ``par-vs-time/`` files store time evolutions of given parameters.

.. note::
  Files are usually saved using the following format: ``exp-period-datatype-time_interval``:

  * ``exp`` identifies the experiment (e.g. *l60*)
  * ``period`` identifies a certain period of data taking (e.g. *p01*)
  * ``datatype`` denotes the run type (e.g. *phy*, *cal*, ...)
  * ``time_interval`` has the format ``start_stop``, where ``start`` is the initial timestamp in UTC+00 format (e.g. *20220922T093400Z*), while ``stop`` is the final timestamp in UTC+00 format (e.g. *20220922T161000Z*)

Inspect plots
-------------

Jupyter Notebook
~~~~~~~~~~~~~~~~

``legend-data-monitor/notebook`` contains a notebook that one can use to read and plot pickle files containing plots of given parameters and detectors.

In that folder, you find:

* ``monitor-par-vs-time-2D.ipynb`` that helps plotting separately *geds*, *spms* and *ch000*. Some widget buttons are present on top of plots that let you inspect different parameters and strings/barrels. A box containing info about applied time cuts is present too on the left side of widget buttons (e.g. *2022/09/22 09:34 -> 2022/09/22 16:10*); selecting a given time cut, you can inspect different time intervals. This notebook does not work if we use a 3D-plot representation.
* ``monitor-par-vs-time-3D.ipynb`` that helps plotting *geds*. This notebook does not visualize SiPMs parameter plots since their parameters (e.g. energy in PE, trigger position) are plotted as maps. Even ch000 is left out from this notebook since there is not advantage in plotting the channel in 3D. If necessary, it can be implemented in the future.

New notebooks can be simply implemented by the users themselves, based on the already available ones. The main functions used to define widgets and plot results are in ``src/legend_data_monitor/ipynb_info.py``.

.. note::
  The plots are interactive: you can perform zooms (x-axis is shared among different channels, while y-axis is not shared) and
  separately save each canvas to your local environment.

.. attention::
  During normal data taking, the offline monitoring is performed on 2D plots only.
  The option of having 3D plots too was left for a personal usage.
