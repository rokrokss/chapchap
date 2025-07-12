#!/bin/bash

while true; do
    current_hour=$(date +%H)
    echo "Current time: $(date +%H:%M)"
    if [ "$current_hour" == "08" ] || [ "$current_hour" == "15" ]; then
        make all
    fi

    sleep 3600
done
