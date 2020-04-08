import sys
import os
import json
# from dateutil.parser import parse
from socketserver import ThreadingMixIn
from http.server import BaseHTTPRequestHandler, HTTPServer
from commands import CMD, COMMAND_LIST, QUEUE, UNQUEUE, SETLIST
from process.shared import ns, cmd_queue, get_ns_obj
from logger import Logger


class TCPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stderr.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format % args))

        if self.server.logger is not None:
            self.server.logger.log("HTTPStream", format % args)

    def queue_cmd(self, cmd):
        if cmd_queue is not None:
            self.server.logger.log("CMD SEND", cmd)
            cmd_queue.put(cmd)

    def _set_response(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        self.log_message("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        # self._set_response()
        # self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

        target = str(self.path)[1:]

        if target == "" or not hasattr(ns, target):
            self._set_response(400)
            response = {
                'error': 'no target'
            }
            self.wfile.write("{}".format(json.dumps(response)).encode('utf-8'))
            return

        now_playing = get_ns_obj(target, "now_playing")
        playlist = get_ns_obj(target, "playlist")

        self._set_response()
        response = {
            'payload': {
                'now_playing': now_playing,
                'playlist': playlist
            }
        }
        self.wfile.write("{}".format(json.dumps(response)).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])    # <--- Gets the size of data
        post_data = self.rfile.read(content_length)             # <--- Gets the data itself
        self.log_message("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                         str(self.path), str(self.headers), post_data.decode('utf-8'))

        # request_path = str(self.path)
        data = json.loads(post_data.decode('utf-8'))

        host = data["host"]
        if host is None or host is "":
            host = self.server.name

        target = data["target"]
        if target is None or target is "":
            self._set_response(400)
            self.wfile.write("{'error': 'no target'}")
            return

        command = data["command"]
        payload = data["data"]
        if (
            command is None or command is "" or payload is None or payload is ""
        ) or (
            command not in COMMAND_LIST
        ):
            self._set_response(400)
            self.wfile.write("{'error': 'bad request'}")
            return

        if command == QUEUE:
            if self.validate_queue_command(data) is False:
                self._set_response(400)
                self.wfile.write("{'error': 'Request is invalid queue command'}")
                return
        elif command == UNQUEUE:
            if self.validate_unqueue_command(data) is False:
                self._set_response(400)
                self.wfile.write("{'error': 'Request is invalid unqueue command'}")
                return
        elif command == SETLIST:
            if self.validate_setlist_command(data) is False:
                self._set_response(400)
                self.wfile.write("{'error': 'Request is invalid setlist command'}")
                return

        cmd = CMD(host=host, target=target, command=command, data=payload)
        self.queue_cmd(cmd)

        self._set_response()
        response = {
            'payload': 'OK'
        }
        self.wfile.write("{}".format(json.dumps(response)).encode('utf-8'))

    def validate_queue_command(self, data):
        command = data["command"]
        payload = data["data"]

        if command not in QUEUE:
            self.log_message("Not a queue command")
            return False

        try:
            _ = payload["id"]
        except KeyError as e:
            self.log_message("'id' is a must have requirement")
            return False

        try:
            _ = payload["location"]
        except KeyError as e:
            self.log_message("'location' is a must have requirement")
            return False

        try:
            _ = payload["artist"]
        except KeyError as e:
            self.log_message("'artist' is a must have requirement")
            return False

        try:
            _ = payload["title"]
        except KeyError as e:
            self.log_message("'title' is a must have requirement")
            return False

        return True

    def validate_unqueue_command(self, data):
        command = data["command"]
        payload = data["data"]

        if command not in UNQUEUE:
            self.log_message("Not a unqueue command")
            return False

        try:
            _ = payload["index_at"]
        except KeyError:
            self.log_message("'index_at' is a must have requirement")
            return False

        return True

    def validate_setlist_command(self, data):
        command = data["command"]
        payload = data["data"]

        if command not in SETLIST:
            self.log_message("Not a setlist command")
            return False

        for queue in payload:
            try:
                _ = queue["id"]
            except KeyError as e:
                self.log_message("'id' is a must have requirement")
                return False

            try:
                _ = queue["location"]
            except KeyError as e:
                self.log_message("'location' is a must have requirement")
                return False

            try:
                _ = queue["artist"]
            except KeyError as e:
                self.log_message("'artist' is a must have requirement")
                return False

            try:
                _ = queue["title"]
            except KeyError as e:
                self.log_message("'title' is a must have requirement")
                return False


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class TCPServer:
    name = None
    httpd = None
    __stop = False

    def __init__(self, name):
        self.name = name
        self.__stop = False
        self.logger = Logger(TCPServer.__name__, name)

        server_address = ('0.0.0.0', 9000)

        self.httpd = ThreadedHTTPServer(server_address, TCPHandler)

    def main(self):
        self.logger.log('start', {
            'pid': os.getpid(),
            'message': 'Starting HTTP Server...\n'
        })
        self.httpd.logger = self.logger
        self.httpd.name = self.name

        while not self.__stop:
            sys.stdout.flush()
            self.httpd.handle_request()

        return 0

    def stop(self):
        self.__stop = True

        self.logger.log('stop', {
            'pid': os.getpid(),
            'message': 'Stopping HTTP Server...\n'
        })
        self.httpd.shutdown()
