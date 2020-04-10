FROM ubuntu:18.04

# gcs or s3 or none
ENV FUSE none

# ignore when FUSE is none
ENV BUCKET apoweroftrance-media

# using when FUSE is gcs
ENV GOOGLE_APPLICATION_CREDENTIALS /root/service-account-key.json

COPY ./service/musicdaemon /etc/logrotate.d/musicdaemon
COPY ./service/musicdaemon.service /etc/systemd/system

RUN chmod a+x /etc/systemd/system/musicdaemon.service

#COPY . /opt/musicdaemon
WORKDIR /opt/musicdaemon

COPY ./entrypoint.sh /opt/musicdaemon/entrypoint.sh

VOLUME ["/srv/media"]
#COPY config.ini ./config.ini

RUN apt-get -y update
RUN apt-get install -y curl
RUN apt-get install -y python3.6 python3-pip software-properties-common libshout3-dev vim
#RUN python-setuptools build-essential git libvorbis-dev libogg-dev libfdk-aac-dev

# Install gcsfuse.
RUN echo "deb http://packages.cloud.google.com/apt gcsfuse-bionic main" | tee /etc/apt/sources.list.d/gcsfuse.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN apt-get update
RUN apt-get install -y gcsfuse

# Config fuse
RUN chmod a+r /etc/fuse.conf
RUN perl -i -pe 's/#user_allow_other/user_allow_other/g' /etc/fuse.conf

# Install gcloud.
RUN apt-get install -y apt-transport-https
RUN apt-get install -y ca-certificates
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt-get update
RUN apt-get install -y google-cloud-sdk

#WORKDIR /root
#RUN git clone https://github.com/whiteblue3/libshout-aac.git
#WORKDIR /root/libshout-aac
#RUN ./configure
#RUN make
#RUN make install

WORKDIR /opt/musicdaemon
#RUN python3 -m pip install -r requirement.txt

EXPOSE 9000

RUN chmod a+x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]

#ENTRYPOINT ["python3", "main.py"]

#CMD ["systemctl enable /etc/systemd/system/musicdaemon.service"]
#CMD ["systemctl start /etc/systemd/system/musicdaemon.service"]
