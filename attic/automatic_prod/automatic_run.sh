#!/bin/bash
while true; do
  python3 /global/cfs/cdirs/m2676/users/calgaro/legend-data-monitor/attic/automatic_prod/main_sync_code.py --cluster nersc --ref_version tmp-auto --pswd_email kghuwydqfmgzihln

  echo "##myscript## Running job at $(date)"
  sleep 3600  # every hour
done
