from serializable import Serializable

# Commands of CMD command properties
QUEUE = "queue"
UNQUEUE = "unqueue"
SETLIST = "setlist"


COMMAND_LIST = [QUEUE, UNQUEUE, SETLIST]


# Data of Queue command
class Queue(Serializable):
    id = None
    location = None
    artist = None
    title = None

    def __init__(self, id, location, artist, title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id
        self.location = location
        self.artist = artist
        self.title = title


# Data of UnQueue command
class UnQueue(Serializable):
    # Queue ID
    index_at = None

    def __init__(self, index_at, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index_at = index_at


class CMD(Serializable):
    # Command queued host
    host = None

    target = None

    command = None

    # JSON formatted command data
    data = None

    def __init__(self, host, target, command, data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = host
        self.target = target
        self.command = command
        self.data = data
