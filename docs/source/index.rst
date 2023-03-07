Welcome to legend-data-monitor's documentation!
===============================================

*legend-data-monitor* is a Python package developed to inspect HPGe diodes and SiPMs data.
The tool has been tested on legend machines at LNGS for L60 commissioning data.
In particular, this tool helps

* opening and reading variables saved in dsp and/or hit tier files
* plotting percentage or absolute values as a function of the time in order to inspect given parameters, separately for each detector type
* inspect parameters by providing either a time interval, runs or keys to inspect as an input
* plotting heatmaps with status info (e.g., ON/OFF/...) for each channel, spotting those that are problematic when overcoming/undercoming given thresholds
* visualizing the obtained plots and heatmaps through a jupyter notebook

Getting started
---------------
*legend-data-monitor* can be installed with `pip <https://pip.pypa.io/en/stable/getting-started>`_:

.. code-block::

   $ pip install legend-data-monitor@git+https://github.com/legend-exp/legend-data-monitor/main

.. attention::

   Before running it, make sure ``~/.local/bin`` (where you can find the legend-data-monitor executable) is appended to ``PATH``.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2

   manuals/index
   Package API reference <api/modules>
