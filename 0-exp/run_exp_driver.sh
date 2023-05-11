#!/usr/bin/env bash
# Set & move to home directory
source ../set_env.sh

if [ $# -eq 1 ]; then
  toml="$1"
fi

echo "Run experiment $toml"
python hc_baseline_driver.py -t $toml
