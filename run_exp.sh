#!/bin/bash

bash 51x_reset_pg_db_user.sh

echo "DONE reset pg."

bash init_venv.sh

echo "DONE init venv."

source venv/bin/activate

echo "DONE activate venv."

cd 0_exp

echo "START exp."

bash start_exp.sh nyc-crash/hc_nyc_crash.py