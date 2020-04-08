Music Daemon is server-side software for streaming radio

# Install Pre-Requirements
You must install libshout on your system.

Windows does not support currently.

## Mac OS X
run code in terminal

    ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)" < /dev/null 2> /dev/null
    brew install libshout

## Ubuntu

    sudo apt install libshout3

# Install

    pip3 install -r requirement.txt

# TODO
- [ ] AAC support
- [ ] Google Cloud Storage mount
- [ ] AWS S3 mount


# Config
This section describe how to configure config.ini

## daemon section

    [daemon]
    musicdaemon = yui, alice, miku
    server = server

This section is configure daemon

- musicdaemon: Name of music daemons. Also used for mount point of ICECAST2
- server: Name of HTTP interface. 'server' is recommand

## icecast2 section

    [icecast2_yui]
    host = 127.0.0.1
    port = 8000
    mount = yui
    user = source
    password = hackme
    codec = mp3
    name = A Power of Trance CH.YUI
    genre = Trance
    bitrate = 128000
    samplerate = 44100
    url =

This section is configure ICECAST2.
The name of section must format of 'icecast_[daemon name in daemon section]'

## callback section

    [callback_yui]
    on_startup = https://r3xgeyodxb.execute-api.ap-northeast-2.amazonaws.com/test
    on_play = https://ezlzag93l0.execute-api.ap-northeast-2.amazonaws.com/test
    on_stop = https://rnw46ry881.execute-api.ap-northeast-2.amazonaws.com/test

This section is configure external callback.
The name of section must format of 'callback_[daemon name in daemon section]'

- on_startup: call when start each music daemon and also used for setup playlist first
- on_play: call when play each music and also used for play statistics
- on_stop: call when stop each music and also used for queue-in another music

on_startup and on_stop is called by 'GET' method and parameters can be include in url-path or ? query-string.

on_play is called by 'POST' method and post data is a JSON format like below queue format

# Queue Format
Queue format used for queue-in music or replace playlist.

- on_startup callback response must be array of queue format.
- also on_stop callback response must be this format.
- on_play callback only using 'id' parameter.

## Format detail
    {
        "id": "0",
        "location": "/Users/whiteblue3/Documents/dev/projects/apoweroftrance.com/source/radio/volumes/demo.mp3",
        "artist": "MOBIUS",
        "title": "Trance Template"
    }

- id: track id
- location: music file path in system
- artist: artist name
- title: name of track

# Command Set of MusicDaemon
MusicDaemon has built-in HTTP REST API for control.
This interface include 'GET' and 'POST' method.

- GET method used for retrieve status of daemon
- POST method used for queue-in the track to playlist

## GET calling rule
Call like this

    http://127.0.0.1:9000/[music daemon name]

## POST calling rule
Call like this

    http://127.0.0.1:9000

You can post data like this

    {
        "host": "server",
        "target": "yui",
        "command": "queue",
        "data": {
            "id": "0",
            "location": "/Users/whiteblue3/Documents/dev/projects/apoweroftrance.com/source/radio/volumes/demo.mp3",
            "artist": "MOBIUS",
            "title": "Trance Template"
        }
    }

- host: Name of HTTP interface. Generally this value is 'server'
- target: Name of Music Damon
- command: queue, unqueue or setlist

data format like below

### queue data
queue command is add music to playlist

    {
        "host": "server",
        "target": "yui",
        "command": "queue",
        "data": {
            "id": "0",
            "location": "/Users/whiteblue3/Documents/dev/projects/apoweroftrance.com/source/radio/volumes/demo.mp3",
            "artist": "MOBIUS",
            "title": "Trance Template"
        }
    }

data format is same for queue format

### unqueue data
unqueue command is remove music from playlist.
data format like this

    {
        "host": "server",
        "target": "yui",
        "command": "unqueue",
        "data": {
            "index_at": 0
        }
    }

- index_at: Index of playlist

### setlist data
setlist command is replace the playlist

    {
        "host": "server",
        "target": "yui",
        "command": "setlist",
        "data": [
            {
                "id": "0",
                "location": "/Users/whiteblue3/Documents/dev/projects/apoweroftrance.com/source/radio/volumes/demo.mp3",
                "artist": "MOBIUS",
                "title": "Trance Template"
            }
        ]
    }

data format is array of queue format
