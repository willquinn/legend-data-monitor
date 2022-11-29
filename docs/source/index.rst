Welcome to legend-data-monitor's documentation!
===============================================

*legend-data-monitor* is a Python package developed to inspect HPGe diodes and SiPMs data.
In particular, this tool helps

* opening and reading dsp and/or hit tier variables
* plotting percentage or absolute values as a function of the time, to inspect given parameters, differently for each detector type
* inspect parameters for a given run or among different runs, once a time interval or a file list is provided as input
* visualizing the obtained plots through a jupyter notebook

The tool has been tested on legend machines at LNGS for L60 commissioning (v06.00) data.

Getting started
---------------
*legend-data-monitor* can be installed with `pip <https://pip.pypa.io/en/stable/getting-started>`_:

.. code-block:: console

   $ pip install legend-data-monitor@git+https://github.com/legend-exp/legend-data-monitor/main

Before running it, make sure ``~/.local/bin`` (where you can find the legend-data-monitor executable) is appended to ``PATH``.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 1

   manuals/index
   Package API reference <generated/modules>
