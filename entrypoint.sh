#!/bin/sh
export LD_LIBRARY_PATH=/usr/local/lib
python3 update_new_data.py
exec "$@"
