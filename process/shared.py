import multiprocessing

# CMD Queue
cmd_queue = multiprocessing.Queue()

manager = multiprocessing.Manager()

# MusicDaemon variable
ns = manager.Namespace()


def get_ns_obj(namespace, objname):
    ns_object = getattr(ns, namespace)
    return ns_object[objname]


def set_ns_obj(namespace, objname, value):
    ns_object = getattr(ns, namespace)
    ns_object[objname] = value
    setattr(ns, namespace, ns_object)


# Application config
ns_config = manager.Namespace()
