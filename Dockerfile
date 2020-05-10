FROM python:3.6-slim AS build
MAINTAINER @whiteblue3 https://github.com/whiteblue3

RUN mkdir /opt/musicdaemon
WORKDIR /opt/musicdaemon

COPY ./requirement.txt /opt/musicdaemon/requirement.txt

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends build-essential software-properties-common gcc libshout3-dev \
    && python3 -m pip install --upgrade pip setuptools wheel \
    && python3 -m pip install --no-cache-dir python-shout \
    && python3 -m pip install --no-cache-dir psutil \
    && python3 -m pip install --no-cache-dir -r requirement.txt \
    && apt-get remove --purge -y build-essential software-properties-common \
    && apt-get -y autoremove \
    && apt-get -y clean \
    && rm -f /var/cache/apt/archives/*.rpm /var/cache/apt/*.bin /var/lib/apt/lists/*.*;


FROM python:3.6-slim AS deploy
MAINTAINER @whiteblue3 https://github.com/whiteblue3

COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

ENV PYTHONUNBUFFERED 0
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y --no-install-recommends gnupg curl ca-certificates wget libshout3-dev netcat-openbsd \
    && echo "deb http://packages.cloud.google.com/apt gcsfuse-xenial main" | tee /etc/apt/sources.list.d/gcsfuse.list \
    && wget -qO- https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update && apt-get install -y --no-install-recommends gcsfuse \
    && echo 'user_allow_other' > /etc/fuse.conf \
    && apt-get -y autoremove \
    && apt-get -y clean \
    && rm -f /var/cache/apt/archives/*.rpm /var/cache/apt/*.bin /var/lib/apt/lists/*.*;

COPY ./service/musicdaemon /etc/logrotate.d/musicdaemon/
COPY ./service/musicdaemon.service /etc/systemd/system/

RUN chmod a+x /etc/systemd/system/musicdaemon.service

EXPOSE 9000

WORKDIR /opt/musicdaemon
RUN mkdir -p /srv/media

COPY ./startup.sh /opt/musicdaemon/startup.sh
RUN chmod a+x /opt/musicdaemon/startup.sh

ENV USER=ubuntu
RUN useradd -rm -d /home/${USER} -s /bin/bash -G root ${USER}

RUN chown -R ${USER}:${USER} /opt/venv

RUN chown -R ${USER}:${USER} /opt/musicdaemon
RUN chown -R ${USER}:${USER} /srv/media

#######################
# cloud storage mount #

# s3, gcs or none
ENV FUSE none

# mount point of bucket
ENV MOUNT_POINT /srv/media

# s3 or gcs bucket
# ignore when FUSE is none
ENV BUCKET ""

# using when FUSE is gcs
ENV GOOGLE_APPLICATION_CREDENTIALS /etc/gcloud/service-account-key.json

RUN mkdir -p /etc/gcloud

###########################
# service depends control #

# if 1, wait to start the depends service is up
ENV WAIT_SERVICE 0
ENV WAIT_URL "127.0.0.1"
ENV WAIT_PORT 8091

###################
# startup control #

# pip install when start (dev usally)
ENV INSTALL 0

# automatic start deamon
ENV AUTOSTART 1


# Uncomment when production
FROM deploy AS production
MAINTAINER @whiteblue3 https://github.com/whiteblue3
COPY . /opt/musicdaemon/
RUN chown -R ${USER}:${USER} /opt/musicdaemon/
RUN rm requirement.txt && rm Dockerfile && rm build_push_docker_image.sh && rm -rf .git && rm -rf .gitignore \
    && rm -rf service

USER ${USER}
ENTRYPOINT ["./startup.sh"]