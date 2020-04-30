FROM python:3.6-slim

COPY ./service/musicdaemon /etc/logrotate.d/musicdaemon/
COPY ./service/musicdaemon.service /etc/systemd/system/

RUN chmod a+x /etc/systemd/system/musicdaemon.service

RUN mkdir /opt/musicdaemon
WORKDIR /opt/musicdaemon

RUN apt-get update && apt-get install --no-install-recommends -y vim gnupg curl \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get -y update
RUN apt-get install -y build-essential software-properties-common libshout3-dev

RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install python-shout

EXPOSE 9000

RUN mkdir -p /srv/media

COPY ./startup.sh /opt/musicdaemon/startup.sh
RUN chmod a+x /opt/musicdaemon/startup.sh

ENV USER=ubuntu
RUN useradd -rm -d /home/${USER} -s /bin/bash -G root ${USER}

RUN chown -R ${USER}:${USER} /opt/musicdaemon
RUN chown -R ${USER}:${USER} /srv/media

ENV FUSE none

ENV MOUNT_POINT /mnt

# ignore when FUSE is none
ENV BUCKET ""

# using when FUSE is gcs
ENV GOOGLE_APPLICATION_CREDENTIALS /etc/gcloud/service-account-key.json

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates wget \
  && echo "deb http://packages.cloud.google.com/apt cloud-sdk-xenial main" | tee /etc/apt/sources.list.d/google-cloud.sdk.list \
  && echo "deb http://packages.cloud.google.com/apt gcsfuse-xenial main" | tee /etc/apt/sources.list.d/gcsfuse.list \
  && wget -qO- https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
  && apt-get update && apt-get install -y --no-install-recommends google-cloud-sdk gcsfuse \
  && echo 'user_allow_other' > /etc/fuse.conf \
  && rm -rf /var/lib/apt/lists

RUN mkdir -p /etc/gcloud

ENV WAIT_SERVICE 0
ENV WAIT_URL "127.0.0.1"
ENV WAIT_PORT 8090
RUN apt-get update && apt-get install netcat-openbsd -y

USER ${USER}

# Uncomment when production
#COPY . /opt/musicdaemon/
#COPY ./requirement.txt /opt/musicdaemon/
#RUN python3 -m pip install --no-cache-dir -r requirement.txt

ENTRYPOINT ["./startup.sh"]
