#!/bin/bash

docker build -t musicdaemon:0.0.1 .
docker tag musicdaemon:0.0.1 gcr.io/apoweroftrance/musicdaemon:0.0.1
gcloud docker -- push gcr.io/apoweroftrance/musicdaemon:0.0.1
