import sys
import os
import shout
import json
import asyncio
import aiohttp
from urllib.parse import urlencode
from datetime import datetime
from dateutil.tz import tzlocal
from commands import QUEUE, UNQUEUE, SETLIST
from process.shared import ns, cmd_queue, get_ns_obj, set_ns_obj, ns_config
from logger import Logger


class MusicDaemon:
    name = None
    icecast2_config = None
    callback_config = None

    on_startup_callback = None
    on_play_callback = None
    on_stop_callback = None

    # Local playlist
    PLAYLIST = []

    def __init__(self, name):
        self.name = name
        self.__stop = False
        self.logger = Logger(MusicDaemon.__name__, name)

        ns_object = {
            "now_playing": {
                "artist": None,
                "title": None,
                "location": None
            },
            "playlist": []
        }
        setattr(ns, name, ns_object)

        try:
            self.icecast2_config = ns_config.icecast2[name]
        except KeyError:
            pass

        self.logger.log("icecast2_config", self.icecast2_config)

        try:
            self.callback_config = ns_config.callback[name]
        except KeyError:
            pass

        self.on_startup_callback = self.callback_config["on_startup"]
        self.on_play_callback = self.callback_config["on_play"]
        self.on_stop_callback = self.callback_config["on_stop"]

        self.logger.log("callback_config", self.callback_config)

    def __del__(self):
        pass

    @property
    def now_playing(self):
        return get_ns_obj(self.name, "now_playing")

    @now_playing.setter
    def now_playing(self, value):
        set_ns_obj(self.name, "now_playing", value)

    # playlist for ns
    @property
    def playlist(self):
        return get_ns_obj(self.name, "playlist")

    @playlist.setter
    def playlist(self, value):
        set_ns_obj(self.name, "playlist", value)

    def now(self, tz=tzlocal()):
        return datetime.now(tz=tz).isoformat()

    def main(self):
        self.logger.log('start', {
            'pid': os.getpid()
        })

        s = shout.Shout()

        s.host = self.icecast2_config["host"]
        s.port = int(self.icecast2_config["port"])
        s.user = self.icecast2_config["user"]
        s.password = self.icecast2_config["password"]
        s.mount = '/' + self.icecast2_config["mount"]
        s.format = self.icecast2_config["codec"]
        s.protocol = 'http'
        s.name = self.icecast2_config["name"]
        s.genre = self.icecast2_config["genre"]
        s.url = self.icecast2_config["url"]
        s.public = 1    # 0 | 1
        s.audio_info = {
            shout.SHOUT_AI_BITRATE: self.icecast2_config["bitrate"],
            shout.SHOUT_AI_SAMPLERATE: self.icecast2_config["samplerate"]
        }

        is_connected = True
        try:
            s.open()
            self.logger.log('icecast2', "connecting icecast2 server")
        except shout.ShoutException as e:
            is_connected = False
            self.logger.log('icecast2', "{}".format(e))
        else:
            self.logger.log('icecast2', "icecast2 server connected")

            if (
                self.on_startup_callback is None or
                self.on_startup_callback is ""
            ):
                pass
            else:
                self.request_callback("GET", self.on_startup_callback, self.on_startup_event)

        is_streaming = False
        f = None

        while not self.__stop:
            self.loop()

            if is_connected is True:
                if is_streaming is False:
                    if len(self.PLAYLIST) > 0:
                        try:
                            self.now_playing = self.PLAYLIST.pop()
                            self.playlist = self.PLAYLIST

                            filename = str(self.now_playing["location"])
                            s.set_metadata(
                                {'song': "{0} - {1}".format(self.now_playing["artist"], self.now_playing["title"])}
                            )

                            if (
                                self.on_play_callback is None or
                                self.on_play_callback is ""
                            ):
                                pass
                            else:
                                self.request_callback(
                                    "POST", self.on_play_callback, self.on_play_event, json.dumps(self.now_playing)
                                )

                            f = open(filename, 'rb')
                        except IndexError:
                            continue
                        except FileNotFoundError as e:
                            self.now_playing = None
                            is_streaming = False
                            self.logger.log('streaming', "{}".format(e))
                            continue
                        else:
                            is_streaming = True
                else:
                    chunk = f.read(4096)
                    if not chunk:
                        is_streaming = False
                        f.close()

                        if (
                            self.on_stop_callback is None or
                            self.on_stop_callback is ""
                        ):
                            pass
                        else:
                            self.request_callback(
                                "POST", self.on_stop_callback, self.on_stop_event, json.dumps(self.now_playing)
                            )

                        self.now_playing = None

                    else:
                        s.send(chunk)
                        s.sync()

        s.close()

        self.logger.log('stop', {
            'pid': os.getpid()
        })
        return 0

    def stop(self):
        self.__stop = True

    def request_callback(self, method, url, callback, data=None):
        if sys.version_info >= (3, 7):
            tasks = [self.request(method, url, callback, data)]
            asyncio.run(asyncio.wait(tasks))
        else:
            futures = [self.request(method, url, callback, data)]
            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.wait(futures))

    def on_startup_event(self, resp):
        try:
            data = json.loads(resp)
            self.process_setlist(data)
        except Exception as e:
            self.logger.log('on_startup_error', str(e))

    def on_play_event(self, resp):
        try:
            data = json.loads(resp)
            self.logger.log('on_play', data)
        except Exception as e:
            self.logger.log('on_play_error', str(e))

    def on_stop_event(self, resp):
        try:
            data = json.loads(resp)
            self.process_queue(data)
        except Exception as e:
            self.logger.log('on_stop_error', str(e))

    async def request(self, method, url, callback, data=None):
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                if data is not None:
                    query_string = urlencode(data)
                    request_url = "{0}?{1}".format(url, query_string)
                else:
                    request_url = url
                async with session.get(request_url) as resp:
                    response = await resp.read()
                    callback(response)
            elif method == "POST":
                async with session.post(url, data=data) as resp:
                    response = await resp.read()
                    callback(response)

    def process_queue(self, data):
        is_no_error = self.validate_queue(data)
        if is_no_error:
            self.playlist.append(data)
            self.PLAYLIST.append(data)
            self.logger.log('QUEUE', data)

    def process_unqueue(self, data):
        try:
            index_at = data["index_at"]
        except KeyError as e:
            self.logger.log('error', str(e))
        else:
            self.playlist.pop(index_at)
            self.PLAYLIST.pop(index_at)
            self.logger.log('UNQUEUE', {"index_at": index_at})

    def process_setlist(self, data):
        is_no_error = False
        for queue in data:
            is_no_error = self.validate_queue(queue)

        if is_no_error or len(data) == 0:
            self.playlist = data
            self.PLAYLIST = data
            self.logger.log('SETLIST', self.playlist)

    def validate_queue(self, queue):
        is_no_error = False
        try:
            _ = queue["id"]
        except KeyError as e:
            self.logger.log('error', str(e))
        else:
            try:
                _ = queue["location"]
            except KeyError as e:
                self.logger.log('error', str(e))
            else:
                try:
                    _ = queue["artist"]
                except KeyError as e:
                    self.logger.log('error', str(e))
                else:
                    try:
                        _ = queue["title"]
                    except KeyError as e:
                        self.logger.log('error', str(e))
                    else:
                        is_no_error = True

        return is_no_error

    def loop(self):
        if cmd_queue is not None and cmd_queue.empty() is False:
            # Dequeue from queue (pop)
            cmd = cmd_queue.get()
            if self.name == cmd.target:
                # cmd_data = json.loads(cmd.data)
                self.logger.log('CMD RECV', cmd)

                if QUEUE == cmd.command:
                    self.process_queue(cmd.data)
                elif UNQUEUE == cmd.command:
                    self.process_unqueue(cmd.data)
                elif SETLIST == cmd.command:
                    self.process_setlist(cmd.data)
            else:
                # If else, rollback to queue
                cmd_queue.put(cmd)
