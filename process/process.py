import signal
from .shared import ns

class Process:
    """Child Process"""
    name = None
    process = None

    def __init__(self, name):
        self.name = name

    def main(self, process_class):
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        self.process = process_class(self.name)
        res = self.process.main()
        return res

    def stop(self, signum, frame):
        if self.process is not None:
            self.process.stop()
