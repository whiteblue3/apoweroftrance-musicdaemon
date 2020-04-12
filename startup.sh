#!/bin/bash
set -e

cd /opt/musicdaemon

# Comment when production
python3 -m pip install -r requirement.txt

python3 /opt/musicdaemon/main.py
exec "$@"