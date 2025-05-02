#!/bin/bash
while true; do
  python python /your/real/path/main_sync_code.py --cluster nersc --ref_version tmp-auto --pswd_email your_password

  echo "##myscript## Running job at $(date)"
  sleep 3600  # every hour
done
