FROM ubuntu:18.04

COPY ./service/musicdaemon /etc/logrotate.d/musicdaemon
COPY ./service/musicdaemon.service /etc/systemd/system

RUN chmod a+x /etc/systemd/system/musicdaemon.service

COPY . /opt/musicdaemon
WORKDIR /opt/musicdaemon

RUN mkdir -p /srv/media

VOLUME ["/srv/media"]
COPY config.ini ./config.ini

RUN apt-get -y update
RUN apt-get install -y python3.6 python3-pip software-properties-common libshout3-dev
#RUN python-setuptools build-essential git libvorbis-dev libogg-dev libfdk-aac-dev

#WORKDIR /root
#RUN git clone https://github.com/whiteblue3/libshout-aac.git
#WORKDIR /root/libshout-aac
#RUN ./configure
#RUN make
#RUN make install

WORKDIR /opt/musicdaemon
RUN python3 -m pip install -r requirement.txt

EXPOSE 9000

ENTRYPOINT ["python3", "main.py"]

#CMD ["systemctl enable /etc/systemd/system/musicdaemon.service"]
#CMD ["systemctl start /etc/systemd/system/musicdaemon.service"]
