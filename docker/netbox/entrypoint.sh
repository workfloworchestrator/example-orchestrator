#!/bin/bash

data_file="/etc/netbox/data.json"
populated_file="/tmp/data_populated"

if [ -f "$populated_file" ]; then
    echo "⏭️ Data has already been loaded. Skipping data population step..."
else
    if [ -f "$data_file" ]; then
        echo "⏳ Loading data from $data_file"
        /opt/netbox/netbox/manage.py loaddata -v 3 "$data_file"
        echo "✅ Finished loading data from $data_file"
        touch "$populated_file"
    else
        echo "⚠️ No data file found to load into netbox!"
    fi
fi

/opt/netbox/launch-netbox.sh
