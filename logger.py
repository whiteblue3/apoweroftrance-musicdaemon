import json
import logging
from datetime import datetime

from dateutil.tz import tzlocal


class Logger:
    def __init__(self, type, name):
        self.type = type
        self.name = name

        self.local_tz = tzlocal()

        logging.basicConfig(level=logging.INFO, format='%(message)s')
        self.logger = logging.getLogger(self.type)

    def __timestamp(self):
        return str(datetime.now(tz=self.local_tz).isoformat())

    def log(self, event, event_value):
        log = {
            'timestamp': self.__timestamp(),
            'component': self.type,
            'process': self.name,
            'log': {
                'event': event,
                'event_value': event_value
             }
        }
        self.logger.info(json.dumps(log))

