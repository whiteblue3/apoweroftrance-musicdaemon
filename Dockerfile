FROM python:3.6-slim

ARG USER=user
RUN groupadd -r ${USER} && useradd --no-log-init -r -g ${USER} ${USER}

# gcs or s3 or none
ENV FUSE none

# ignore when FUSE is none
ENV BUCKET apoweroftrance-media

# using when FUSE is gcs
ENV GOOGLE_APPLICATION_CREDENTIALS /opt/musicdaemon/service-account-key.json

COPY --chown=${USER}:${USER} ./service/musicdaemon /etc/logrotate.d/musicdaemon/
COPY --chown=${USER}:${USER} ./service/musicdaemon.service /etc/systemd/system/

RUN chmod a+x /etc/systemd/system/musicdaemon.service

RUN mkdir /opt/musicdaemon
# Uncomment when production
#COPY --chown=${USER}:${USER} . /opt/musicdaemon/
WORKDIR /opt/musicdaemon

COPY --chown=${USER}:${USER} ./requirement.txt /opt/musicdaemon/
COPY --chown=${USER}:${USER} ./entrypoint.sh /opt/musicdaemon/

RUN apt-get -y update
RUN apt-get install --no-install-recommends -y curl vim gnupg gnupg2 gnupg1 \
    && rm -rf /var/lib/apt/lists/*

# Install gcsfuse.
RUN echo "deb http://packages.cloud.google.com/apt gcsfuse-bionic main" | tee /etc/apt/sources.list.d/gcsfuse.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN apt-get update
RUN apt-get install --no-install-recommends -y gcsfuse \
    && rm -rf /var/lib/apt/lists/*

# Config fuse
RUN chmod a+r /etc/fuse.conf
RUN perl -i -pe 's/#user_allow_other/user_allow_other/g' /etc/fuse.conf

# Install gcloud.
RUN apt-get install --no-install-recommends -y apt-transport-https ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt-get update
RUN apt-get install --no-install-recommends -y google-cloud-sdk \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get -y update
RUN apt-get install -y build-essential software-properties-common libshout3-dev

WORKDIR /opt/musicdaemon

RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install python-shout

# Uncomment when production
#RUN python3 -m pip install --no-cache-dir -r requirement.txt

EXPOSE 9000

RUN chmod a+x entrypoint.sh

VOLUME ["/srv/media"]

CMD ["/opt/musicdaemon/entrypoint.sh"]

#USER ${USER}:${USER}
#ENTRYPOINT ["/bin/bash"]