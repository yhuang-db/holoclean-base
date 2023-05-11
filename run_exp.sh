#!/bin/bash

bash 51x_reset_pg_db_user.sh

echo "DONE reset pg."

bash init_venv.sh

echo "DONE init venv."

source venv/bin/activate

echo "DONE activate venv."

cd 0-exp

if [ $# -eq 2 ]; then
  city="$1"
  dataset="$2"
fi

echo "START exp $city-$dataset."

bash run_exp_driver.sh "$city"_"$dataset".toml
