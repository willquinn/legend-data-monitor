Available parameters
====================
| *Under construction...*
| The following table shows which parameter are available (and tested) separately for each detector type.
| In general, the full list of dsp/hit variables that were generated within a given version vXX.YY can be found at legend-login LNGS machine under ``/data1/shared/l60/l60-prodven-v1/prod-ref/vXX.YY/inputs/config/``.


.. list-table::
  :widths: 30 25 25 25
  :header-rows: 1

  * - Available parameters
    - HPGe
    - SiPM
    - ch000
  * - dsp variables
    - all
    - x
    - all
  * - hit variables
    - all
    - all
    - x
  * - ``event_rate``
    - ✓
    - ✓
    - ✓
  * - ``K_lines``
    - ✓
    - x
    - x
  * - ``uncal_puls``
    - ✓
    - x
    - ✓
  * - ``cal_puls``
    - ✓
    - x
    - ✓

.. note::

  In general, all entries will be plotted.
  But you can also pick some given entries (see the config file), eg.
  * you can pick only pulser, physical or all entries
  * you can apply quality cuts, keeping only given entries
