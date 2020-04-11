#!/bin/bash
set -e

if [[ ${FUSE} == *"gcs"* ]]; then
  gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
  gcsfuse --key-file=${GOOGLE_APPLICATION_CREDENTIALS} --implicit-dirs ${BUCKET} /srv/media
elif [[ ${FUSE} == *"s3"* ]]; then
  echo "S3 does not support currently"
else
  echo "FUSE not using"
fi

# Comment when production
python3 -m pip install -r requirement.txt
python3 /opt/musicdaemon/main.py