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

bash start_exp.sh "$city"-"$dataset"/hc_"$city"_"$dataset".py
