import ast
from configparser import ConfigParser, NoSectionError
from process.master import Master
from daemon import MusicDaemon
from server import TCPServer
from process.shared import ns_config


class Child:
    name = None
    process_class = None

    def __init__(self, name, process_class):
        self.name = name
        self.process_class = process_class


if __name__ == '__main__':
    config = ConfigParser()
    config.read('config.ini')

    musicdaemon = config.get('daemon', 'musicdaemon').replace(' ', '').split(',')
    server = config.get('daemon', 'server').replace(' ', '').split(',')

    empty_index_musicdaemon = -1
    try:
        empty_index_musicdaemon = musicdaemon.index('')
    except ValueError:
        pass
    else:
        musicdaemon.pop(empty_index_musicdaemon)

    empty_index_server = -1
    try:
        empty_index_server = server.index('')
    except ValueError:
        pass
    else:
        server.pop(empty_index_server)

    icecast2_config = {}
    callback_config = {}
    for daemon in musicdaemon:
        try:
            icecast2_daemon_config = config.options("icecast2_{0}".format(daemon))
            icecast2_config[daemon] = {}

            for key in icecast2_daemon_config:
                icecast2_config[daemon][key] = config.get("icecast2_{0}".format(daemon), key)
        except NoSectionError:
            pass

        try:
            callback_daemon_config = config.options("callback_{0}".format(daemon))
            callback_config[daemon] = {}

            for key in callback_daemon_config:
                callback_config[daemon][key] = config.get("callback_{0}".format(daemon), key)
        except NoSectionError:
            pass

    ns_config.icecast2 = icecast2_config
    ns_config.callback = callback_config

    process_list = []
    if musicdaemon:
        for daemon in musicdaemon:
            child = Child(daemon, process_class=MusicDaemon)
            process_list.append(child)
    if server:
        for daemon in server:
            child = Child(daemon, process_class=TCPServer)
            process_list.append(child)

    master = Master(process_list)
    exit_code = master.main()
    exit(exit_code)
