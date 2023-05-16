How to load and plot Slow Control data
======================================

How to load SC data
-------------------

A number of parameters related to the LEGEND hardware configuration and status are recorded in the Slow Control (SC) database.
The latter, PostgreSQL database resides on the ``legend-sc.lngs.infn.it`` host, part of the LNGS network.
To access the SC database, follow the `Confluence (Python Software Stack) <https://legend-exp.atlassian.net/wiki/spaces/LEGEND/pages/494764033/Python+Software+Stack>`_ instructions.
Data are loaded following the ``pylegendmeta`` tutorial , which shows how to inspect the database.


... put here some text on how to specify the plotting of a SC parameter in the config file (no ideas for the moment)...


Files are collected in the output folder specified in the ``output`` config entry:

.. code-block:: json

  {
  "output": "<some_path>/out",
  // ...

In principle, for plotting the SC data you would need just the start and the end of a time interval of interest. This means that SC data does not depend on any dataset info (``experiment``, ``period``, ``version``, ``type``) but ``time_selection``.
However, there are cases were we want to inspect a given run or time period made of keys as we usually do with germanium.

In the first case, we end up saving data in the following folder:

.. code-block::

  <some_path>/out/
    └── generated
      └── plt
        └── SC
          └── <time_selection>
            ├── SC-<time_selection>.pdf
            ├── SC-<time_selection>.log
            └── SC-<time_selection>.{dat,bak,dir}

Otherwise, we store the SC data/plots as usual:

.. code-block::

  <some_path>/out/
    └── generated
      └── plt
        └── <type>
          └── <period>
            └── SC
              └── <time_selection>
                ├── SC-<time_selection>.pdf
                ├── SC-<time_selection>.log
                └── SC-<time_selection>.{dat,bak,dir}


.. note::

  ``time_selection`` can assume one of the following formats, depending on what we put as a time range into ``dataset``:

  - if ``{'start': '20220928T080000Z', 'end': '20220928T093000Z'}`` (start + end), then <time_selection> = ``20220928T080000Z_20220928T093000Z``;
  - if ``{'timestamps': ['20230207T103123Z']}`` (one key), then <time_selection> = ``20230207T103123Z``;
  - if ``{'timestamps': ['20230207T103123Z', '20230207T141123Z', '20230207T083323Z']}`` (multiple keys), then <time_selection> = ``20230207T083323Z_20230207T141123Z`` (min/max timestamp interval)
  - if ``{'runs': 1}`` (one run), then <time_selection> = ``r001``;
  - if ``{'runs': [1, 2, 3]}`` (multiple runs), then <time_selection> = ``r001_r002_r003``.

Shelve output objects
~~~~~~~~~~~~~~~~~~~~~
*Under construction...*


Available SC parameters
-----------------------

Available parameters include:

- ``PT114``, ``PT115``, ``PT118`` (cryostat pressures)
- ``PT202``, ``PT205``, ``PT208`` (cryostat vacuum)
- ``LT01`` (water loop fine fill level)
- ``RREiT`` (injected air temperature clean room), ``RRNTe`` (clean room temperature north), ``RRSTe`` (clean room temperature south), ``ZUL_T_RR`` (supply air temperature clean room)
- ``DaqLeft-Temp1``, ``DaqLeft-Temp2``, ``DaqRight-Temp1``, ``DaqRight-Temp2`` (rack present temperatures)
