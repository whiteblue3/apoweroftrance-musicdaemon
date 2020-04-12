FROM python:3.6-slim

COPY ./service/musicdaemon /etc/logrotate.d/musicdaemon/
COPY ./service/musicdaemon.service /etc/systemd/system/

RUN chmod a+x /etc/systemd/system/musicdaemon.service

RUN mkdir /opt/musicdaemon
# Uncomment when production
#COPY . /opt/musicdaemon/
WORKDIR /opt/musicdaemon

RUN apt-get update && apt-get install --no-install-recommends -y vim gnupg curl \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get -y update
RUN apt-get install -y build-essential software-properties-common libshout3-dev

RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install python-shout

EXPOSE 9000

VOLUME ["/srv/media"]

COPY ./startup.sh /opt/musicdaemon/startup.sh
RUN chmod a+x /opt/musicdaemon/startup.sh

ENV USER=ubuntu
RUN useradd -rm -d /home/${USER} -s /bin/bash ${USER}

RUN chown -R ${USER}:${USER} /opt/musicdaemon

#COPY ./requirement.txt /opt/musicdaemon/

# Uncomment when production
#RUN python3 -m pip install --no-cache-dir -r requirement.txt

USER ${USER}

CMD ["./startup.sh"]
