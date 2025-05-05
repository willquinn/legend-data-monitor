How to load and plot Slow Control data
======================================

How to load SC data
-------------------

A number of parameters related to the LEGEND hardware configuration and status are recorded in the Slow Control (SC) database.
The latter, PostgreSQL database resides on the ``legend-sc.lngs.infn.it`` host, part of the LNGS network.
To access the SC database, follow the `Confluence (Python Software Stack) <https://legend-exp.atlassian.net/wiki/spaces/LEGEND/pages/494764033/Python+Software+Stack>`_ instructions.
Data are loaded following the `pylegendmeta <https://github.com/legend-exp/pylegendmeta>`_ tutorial, which shows how to retrieve info from the SC database.


Available SC parameters
-----------------------

Available parameters at the moment include:

* ``PT114``, ``PT115``, ``PT118`` (cryostat pressures)
* ``PT202``, ``PT205``, ``PT208`` (cryostat vacuum)
* ``LT01`` (water loop fine fill level)
* ``vmon`` (Ge diode voltage)
* ``imon`` (Ge diode current)
* ``RREiT`` (injected air temperature clean room), ``RRNTe`` (clean room temperature north), ``RRSTe`` (clean room temperature south), ``ZUL_T_RR`` (supply air temperature clean room)
* ``DaqLeft-Temp1``, ``DaqLeft-Temp2``, ``DaqRight-Temp1``, ``DaqRight-Temp2`` (rack present temperatures)
* if you want more, contact us!

These can be easily access for any time range of interest by giving a config.json file as input to the command line in the following way:

.. code-block::

  legend-data-monitor user_scdb --config config.json --port N --pswd ThePassword

.. note::

  - ``N`` is whatever number in the range 1024-65535. Setting a personal port different from the default one (5432) is a safer option, otherwise if a port is already in use by another user, you'll receive an error indicating that the port is already taken and you will not be able to access the SC database;
  - ``ThePassword`` can be found on Confluence at `this page <https://legend-exp.atlassian.net/wiki/spaces/LEGEND/pages/494764033/Python+Software+Stack#Metadata-access>`_.

An example of a config.json file is the following:

.. code-block:: json

  {
  "output": "output_folder",
  "dataset": {
    "experiment": "L200",
    "period": "p09",
    "version": "tmp-auto",
    "path": "/data2/public/prodenv/prod-blind/",
    "type": "phy",
    "time_selection": ...
    },
  "saving": "overwrite",
  "slow_control": {
    "parameters": ["DaqLeft-Temp1", "ZUL_T_RR"]
    }
  }

The meaning of each entry is explained below:

* ``output``: output folder path;
* ``dataset``:
    * ``experiment``: either *L60* (to be checked) or *L200*
    * ``period``: period to inspect
    * ``version``: prodenv version (eg *tmp-auto* or *ref-v1.0.0*)
    * ``path``: global path to prod-blind prodenv folder
    * ``type``: type of data to inspect (either *cal* or *phy*)
    *  ``time selection``: check how to build a config file to see available options for this entry

* ``saving``: option is available to either ``"overwrite"`` any already present output file (or create a new one if not present) or ``"append"`` new data to the previously obtained output files
* ``slow_control``: entry for specifying SC parameters
    * ``parameters``: list of parameters to retrieve

.. note::

  In principle, for plotting the SC data you would need just the start and the end of a time interval of interest. This means that SC data does not depend on any dataset info (i.e. on entries ``experiment``, ``period``, ``version``, ``type``). However, these entries are important to retrieve any channel map of interest for the given time range of interest.


We store SC data in the following way:

.. code-block::

  <output>
    └── <version>
      └── generated
        └── plt
          └── <type>
            └── <period>
                └── <time_selection>
                  ├── SC-<time_selection>.hdf
                  └── SC-<time_selection>.{dat,bak,dir}
