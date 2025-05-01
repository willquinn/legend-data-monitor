#!/bin/bash
while true; do
  python <path>/main_sync_code.py --cluster nersc --ref_version tmp-auto --pswd_email <insert_pswd>
  echo "##myscript## Running job at $(date)"
  sleep 3600  # every hour
done
