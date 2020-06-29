#!/usr/bin/env bash

set -euo pipefail

echo -n 'Password for public API: '
read -s pub_pass

pub_api=''
pub_user='Sarah'

prv_api='--api http://localhost:5000/api'
prv_user='Sarah Privat'
prv_pass='test'
prv_data='test-sarah-private.json'

items=(
    # src  trg  loc  (source subject, target subject, target location)
    '  41   39    6 '  # GeoKom
    '  36   40    6 '  # SuperToll
)

summarize='weekly'  # daily, weekly or monthly

./download.py -y $prv_api -u "$prv_user" -p "$prv_pass" $prv_data
for item in "${items[@]}"; do
    ./upload-summarized-activities.py -y $pub_api -u "$pub_user" -p "$pub_pass" -s $summarize $prv_data $item
done
