#!/bin/bash
set -e

if [[ ${FUSE} == *"gcs"* ]]; then
  mkdir -p /srv/media
  chmod a+w /srv/media
  gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
  gcsfuse --key-file=${GOOGLE_APPLICATION_CREDENTIALS} --implicit-dirs ${BUCKET} /srv/media
elif [[ ${FUSE} == *"s3"* ]]; then
  mkdir -p /srv/media
  chmod a+w /srv/media
  echo "S3 does not support currently"
else
  echo "FUSE not using"
fi

python3 /opt/musicdaemon/main.py
