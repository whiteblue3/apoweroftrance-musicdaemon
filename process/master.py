import os
import time
import signal
import psutil
from logger import Logger
from process.process import Process


class Master:

    def __init__(self, child_process):
        self.__stop = False
        self.process = []
        self.logger = Logger(Master.__name__, 'musicdaemon')

        self.child_process = child_process
        self.num_process = len(self.child_process)

    def main(self):
        master_pid = os.getpid()
        self.logger.log("start", "Start Master, PID {0}".format(master_pid))

        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        process_class_index = 0
        for child_process_id in range(self.num_process):
            pid = os.fork()
            child_process = self.child_process[process_class_index]
            process_name = child_process.name
            process_class = child_process.process_class

            if pid == 0:
                process = Process(child_process.name)
                exit_code = process.main(process_class)
                exit(exit_code)
            else:
                self.logger.log("start",
                                "Start {0} Process {1} Process-{2} PID {3}".format(
                                    process_class.__name__, process_name, child_process_id, pid
                                ))
                self.process.append({"id": child_process_id, "pid": pid, "name": process_name})

            process_class_index += 1

        while not self.__stop:
            # os.system("ps aux | awk '{ print $8 " " $2 }' | grep -w Z")
            for proc in psutil.process_iter():
                try:
                    pinfo = proc.as_dict(attrs=['pid'])
                    for p in self.process:
                        if pinfo['pid'] == p['pid']:
                            # print(p['name'], proc.status())
                            if proc.status() == "zombie":
                                proc.kill()
                                self.process.pop(self.process.index(p))
                            # else:
                            #     print(p['name'], proc.status())
                except psutil.NoSuchProcess:
                    pass
            if len(self.process) == 1 and self.process[0]['name'] == 'server':
                self.stop(signal.SIGINT, 0)
            time.sleep(1)

        self.logger.log("stop", "Stop Master, PID {0}".format(os.getpid()))

    def stop(self, signum, frame):
        self.__stop = True
        self.logger.log("stop", "Receive Signal {0}".format(signum))

        for process in self.process:
            self.logger.log("stop",
                            "Send Signal {0} to {1} Process-{2} PID {3}".format(
                                signal.SIGTERM, process['name'], process['id'], process['pid']
                            ))
            os.kill(process['pid'], signal.SIGTERM)
            os.kill(process['pid'], signal.SIGKILL)
