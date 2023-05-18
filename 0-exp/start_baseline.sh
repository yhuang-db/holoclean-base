#!/usr/bin/env bash
# Set & move to home directory
source ../set_env.sh

if [ $# -eq 2 ]; then
  city="$1"
  dataset="$2"
fi

# init db
db_name="holodb_hc_$dataset"

sudo -u "$USER" psql -d postgres <<PGSCRIPT
DROP DATABASE IF EXISTS $db_name;
CREATE DATABASE $db_name;
GRANT ALL PRIVILEGES ON DATABASE $db_name TO holouser ;
\c $db_name
GRANT ALL ON SCHEMA public TO holouser;
CREATE EXTENSION postgis;
PGSCRIPT

echo "DB $db_name created/reset."

# launch experiment
exp_config="$city"-"$dataset"/"$city"_"$dataset".toml

echo "Launching experiment config $exp_config"
python hc_baseline_driver.py -t "$exp_config" -d "$db_name"
