import sys
import os
import shout
import json
import asyncio
import aiohttp
import redis
import time
import signal
from urllib.parse import urlencode
from datetime import datetime
from dateutil.tz import tzlocal
from commands import QUEUE, UNQUEUE, SETLIST
from process.shared import ns, cmd_queue, get_ns_obj, set_ns_obj, ns_config
from logger import Logger


class MusicDaemon:
    name = None

    redis_server = None
    redis_daemon_key = None

    icecast2_config = None
    callback_config = None
    redis_config = None

    on_startup_callback = None
    on_play_callback = None
    on_stop_callback = None

    # Local playlist
    _PLAYLIST = []

    def __init__(self, name):
        self.name = name
        self.__stop = False
        self.logger = Logger(MusicDaemon.__name__, name)

    def __del__(self):
        pass

    # now_playing for ns
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

    def get_PLAYLIST(self):
        if self.redis_server is None:
            return self._PLAYLIST
        else:
            redis_data = self.get_redis_data()
            if redis_data and redis_data["playlist"]:
                self.playlist = list(redis_data["playlist"])
                return redis_data["playlist"]
            else:
                return None

    def set_PLAYLIST(self, value):
        if self.redis_server is None:
            self._PLAYLIST = value
            self.playlist = value
        else:
            self.playlist = value
            self.set_redis_data("playlist", value)

    def now(self, tz=tzlocal()):
        return datetime.now(tz=tz).isoformat()

    def get_redis_data(self):
        try:
            raw_json = self.redis_server.get(self.redis_daemon_key)
        except AttributeError as e:
            return None
        else:
            if raw_json is None:
                default_data = {
                    "now_playing": None,
                    "playlist": None
                }
                self.redis_server.set(self.redis_daemon_key, json.dumps(default_data, ensure_ascii=False).encode('utf-8'))
            try:
                data_json = json.loads(raw_json)
            except Exception as e:
                self.logger.log('redis error', "{}".format(e))
                return None
            return dict(data_json)

    def set_redis_data(self, key, value):
        try:
            redis_data = self.get_redis_data()
            redis_data[key] = value
            self.redis_server.set(self.redis_daemon_key, json.dumps(redis_data, ensure_ascii=False).encode('utf-8'))
        except TypeError as e:
            pass

    def stop_send_music(self, now_playing):
        if (
                self.on_stop_callback is None or
                self.on_stop_callback is ""
        ):
            pass
        else:
            self.logger.log('on_stop_req', self.now_playing)
            self.request_callback(
                "POST", self.on_stop_callback, self.on_stop_event, json.dumps(now_playing)
            )

        self.now_playing = None
        self.set_redis_data("now_playing", None)

    def main(self):
        self.logger.log('start', {
            'pid': os.getpid()
        })

        ns_object = {
            "now_playing": None,
            "playlist": None
        }
        setattr(ns, self.name, dict(ns_object))

        try:
            self.icecast2_config = ns_config.icecast2[self.name]
        except KeyError:
            pass

        self.logger.log("icecast2_config", self.icecast2_config)

        try:
            self.callback_config = ns_config.callback[self.name]
        except KeyError:
            pass
        else:
            self.on_startup_callback = self.callback_config["on_startup"]
            self.on_play_callback = self.callback_config["on_play"]
            self.on_stop_callback = self.callback_config["on_stop"]

            self.logger.log("callback_config", self.callback_config)

        try:
            self.redis_config = ns_config.redis[self.name]
        except KeyError:
            pass
        else:
            self.logger.log("redis_config", self.redis_config)

        if self.redis_config is not None:
            redis_host = self.redis_config["host"]
            redis_port = int(self.redis_config["port"])
            self.redis_daemon_key = self.redis_config["key"]

            self.redis_server = redis.StrictRedis(host=redis_host, port=redis_port, db=0)

        s = shout.Shout()

        s.host = self.icecast2_config["host"]
        s.port = int(self.icecast2_config["port"])
        s.user = self.icecast2_config["user"]
        s.password = self.icecast2_config["password"]
        # s.password = ""
        s.mount = '/' + self.icecast2_config["mount"]
        s.format = self.icecast2_config["codec"]
        s.protocol = 'http'
        s.name = self.icecast2_config["name"]
        s.description = self.icecast2_config["description"]
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
            self.logger.log('icecast2', "{}".format(e))
            is_connected = False
        else:
            self.logger.log('icecast2', "icecast2 server connected")

            if self.redis_server:
                redis_data = self.get_redis_data()

                if redis_data:
                    if redis_data["now_playing"] is not None:
                        self.now_playing = redis_data["now_playing"]
                    if redis_data["playlist"]:
                        self.set_PLAYLIST(redis_data["playlist"])

            if not self.get_PLAYLIST():
                if (
                    self.on_startup_callback is None or
                    self.on_startup_callback is ""
                ):
                    pass
                else:
                    self.request_callback("GET", self.on_startup_callback, self.on_startup_event)

        is_streaming = False
        f = None

        if is_connected:
            while not self.__stop:
                self.loop()

                if is_streaming is False:
                    if self.get_PLAYLIST():
                        try:
                            playlist = self.get_PLAYLIST()

                            if not self.now_playing:
                                self.now_playing = playlist.pop(0)
                                self.set_PLAYLIST(playlist)

                            if self.redis_server is not None:
                                self.set_redis_data("now_playing", self.now_playing)

                            if self.now_playing is not None:
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
                                    self.logger.log('on_play_req', self.now_playing)
                                    self.request_callback(
                                        "POST", self.on_play_callback, self.on_play_event, json.dumps(self.now_playing)
                                    )

                                f = open(filename, 'rb')
                        except shout.ShoutException:
                            self.now_playing = None
                            self.set_redis_data("now_playing", None)
                            is_streaming = False
                            continue
                        except IndexError:
                            continue
                        except FileNotFoundError as e:
                            self.now_playing = None
                            self.set_redis_data("now_playing", None)
                            is_streaming = False
                            self.logger.log('streaming error', "{}".format(e))
                            continue
                        except OSError:
                            self.now_playing = None
                            self.set_redis_data("now_playing", None)
                            is_streaming = False
                            continue
                        else:
                            is_streaming = True
                    else:
                        is_streaming = False
                else:
                    try:
                        chunk = f.read(4096)
                    except AttributeError as e:
                        self.now_playing = None
                        self.set_redis_data("now_playing", None)
                        is_streaming = False
                        self.logger.log('streaming error', "{}".format(e))
                    else:
                        if not chunk:
                            is_streaming = False
                            f.close()
                            f = None

                            self.stop_send_music(self.now_playing)
                        else:
                            try:
                                s.send(chunk)
                                s.sync()
                            except shout.ShoutException:
                                is_streaming = False
                                f.close()
                                f = None

                                self.stop_send_music(self.now_playing)

        if is_connected:
            s.close()

        pid = os.getpid()
        self.logger.log('stop', {
            'pid': pid
        })
        os.kill(pid, signal.SIGTERM)
        os.kill(pid, signal.SIGKILL)
        # os.system('kill -9 %s' % pid)
        return 0

    def stop(self):
        self.__stop = True

    def request_callback(self, method, url, callback, data=None):
        time.sleep(1)
        if sys.version_info >= (3, 7):
            tasks = [self.request(method, url, callback, data)]
            asyncio.run(asyncio.wait(tasks))
        else:
            futures = [self.request(method, url, callback, data)]
            # loop = asyncio.get_event_loop()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(asyncio.wait(futures))
            loop.close()

    def on_startup_event(self, resp):
        print("on_startup_resp: %s" % resp)
        try:
            data = json.loads(resp)
            self.logger.log('on_startup', data)
            if not self.redis_server:
                self.process_setlist(data)
        except Exception as e:
            self.logger.log('on_startup_error', str(e).encode('utf-8'))

    def on_play_event(self, resp):
        print("on_play_resp: %s" % resp)
        try:
            data = json.loads(resp)
            self.logger.log('on_play', data)
        except Exception as e:
            self.logger.log('on_play_error', str(e).encode('utf-8'))

    def on_stop_event(self, resp):
        print("on_stop_resp: %s" % resp)
        try:
            data = json.loads(resp)
            self.logger.log('on_stop', data)
            if not self.redis_server:
                self.process_queue(data)
        except Exception as e:
            self.logger.log('on_stop_error', str(e).encode('utf-8'))

    async def request(self, method, url, callback, data=None):
        headers = {'content-type': 'application/json'}
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                if data is not None:
                    query_string = urlencode(data)
                    request_url = "{0}?{1}".format(url, query_string)
                else:
                    request_url = url
                async with session.get(request_url, headers=headers) as resp:
                    response = await resp.read()
                    callback(response.decode('utf-8'))
            elif method == "POST":
                async with session.post(url, data=data, headers=headers) as resp:
                    response = await resp.read()
                    callback(response.decode('utf-8'))

    def process_queue(self, data):
        is_no_error = self.validate_queue(data)
        if is_no_error:
            playlist = self.get_PLAYLIST()
            playlist.append(data)
            self.set_PLAYLIST(playlist)
            self.logger.log('QUEUE', data)

    def process_unqueue(self, data):
        try:
            index_at = data["index_at"]
        except KeyError as e:
            self.logger.log('error', str(e))
        else:
            playlist = self.get_PLAYLIST()
            playlist.pop(index_at)
            self.set_PLAYLIST(playlist)
            self.logger.log('UNQUEUE', {"index_at": index_at})

    def process_setlist(self, data):
        is_no_error = False
        for queue in data:
            is_no_error = self.validate_queue(queue)

        if is_no_error:
            self.set_PLAYLIST(data)

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
