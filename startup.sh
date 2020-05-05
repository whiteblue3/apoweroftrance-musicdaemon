#!/bin/bash
set -e
set -x

if [[ ${FUSE} == *"gcs"* ]]; then
  gcsfuse --key-file=${GOOGLE_APPLICATION_CREDENTIALS} -o nonempty -o allow_other --implicit-dirs ${BUCKET} /srv/media
elif [[ ${FUSE} == *"s3"* ]]; then
  echo "S3 does not support currently"
else
  echo "FUSE not using"
fi

cd /opt/musicdaemon

if [[ ${INSTALL} == *"1"* ]]; then
  python3 -m pip install -r requirement.txt
fi

if [[ ${WAIT_SERVICE} == *"1"* ]]; then
  while ! nc ${WAIT_URL} ${WAIT_PORT}; do
    >&2 echo "Wait depends service - sleeping"
    sleep 1
  done
fi

if [[ ${AUTOSTART} == *"1"* ]]; then
  python3 /opt/musicdaemon/main.py
fi

exec "$@"
