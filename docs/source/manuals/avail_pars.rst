Available parameters
====================
| The following table shows which parameter are available (and tested) separately for each detector type.


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
  * - ``FWHM``
    - ✓
    - x
    - x
  * - ``wf_max_rel``
    - ✓
    - x
    - ✓

.. note::

  In general, all saved timestamps will be plotted.
  But you can also pick some given entries (see the config file), eg.

  - you can pick only ``phy`` or ``all`` entries
  - you can flag special events, like ``pulser``, ``pulser01ana``, ``FCbsln`` or ``muon`` events

.. important::

  Special parameters are typically saved under ``settings/special-parameters.json`` and carefully handled when loading data.
