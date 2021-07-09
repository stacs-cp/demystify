import itertools
import random
import logging
import sys

from multiprocessing import Pool, Process, get_start_method, Queue

from .config import CONFIG
from .utils import randomFromSeed

# Needs to be global so we can call it from a child process
_global_solver_ref = None
_global_forqes_ref = None


def getChildSolver():
    return _global_solver_ref


def setChildSolver(c):
    global _global_solver_ref
    _global_solver_ref = c


def getChildForqes():
    return _global_forqes_ref


def setChildForqes(c):
    global _global_forqes_ref
    _global_forqes_ref = c


# Magic from https://stackoverflow.com/questions/2130016/splitting-a-list-into-n-parts-of-approximately-equal-length
def split(a, n):
    k, m = divmod(len(a), n)
    # Listify this so we check the lengths here
    return list(
        list(a[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)])
        for i in range(n)
    )


# Fake Pool for profiling with py-spy
class FakePool:
    def __init__(self):
        pass

    def map(self, func, args):
        return list(map(func, args))

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        pass


_reuse_process_pool = None


def getPool(cores):
    if cores <= 1:
        return FakePool()
    else:
        if CONFIG["reusePool"]:
            global _reuse_process_pool
            if _reuse_process_pool is None:
                _reuse_process_pool = ProcessPool(processes=cores, reuse=True)
            return _reuse_process_pool
        else:
            return ProcessPool(processes=cores)
    #    return Pool(processes=cores)


global_process_counter = 0


def getGlobalProcessCounter():
    global global_process_counter
    global_process_counter += 1
    return global_process_counter


def doprocess(id, inqueue, outqueue):
    count = 0
    # logging.info("start child stats: %s", _global_solver_ref.get_stats())
    _global_solver_ref.reset_stats()
    # logging.info("reset child stats: %s", _global_solver_ref.get_stats())
    while True:
        # print("! {} Waiting for task".format(id))
        (func, msg) = inqueue.get()
        # print("! {} Got task {} {}".format(id,count, (func,msg)))
        if func is None:
            if msg == "stats":
                # logging.info("get child stats: %s", _global_solver_ref.get_stats())
                outqueue.put({"stats": _global_solver_ref.get_stats()})
                _global_solver_ref.reset_stats()
            elif msg is None:
                break
            else:
                print("Invalid message to child")
                sys.exit(1)
        else:
            outqueue.put(func(msg))
        # print("! {} Done task {}".format(id,count))
        count += 1


class ProcessPool:
    def __init__(self, processes, *, reuse=False):
        assert processes > 1
        self._processcount = processes
        self._reuse = reuse
        self._first = True

    def map(self, func, args):
        # Make this repeatable, but shuffled differently on each call
        randomFromSeed(getGlobalProcessCounter()).shuffle(args)
        # TODO: This can be unbalanced
        chunks = split(args, self._processcount)
        logging.info("Chunked %s in %s", len(args), [len(c) for c in chunks])
        # print("!A ", chunks)
        # Push all the work
        for i, chunk in enumerate(chunks):
            for c in chunk:
                # print("! Putting task {} for {}".format(i, c))
                self._inqueues[i].put((func, c))

        results = []
        for i, q in enumerate(self._outqueues):
            l = []
            # Get one answer for each thing in the chunk
            for _ in chunks[i]:
                x = q.get()
                # print("!X got ", i, x)
                l.append(x)
            results.append(l)

        # print("!Ax {} {} {} {} {}".format(len(args), sum([len(c) for c in chunks]), sum([len(r) for r in results]), [len(c) for c in chunks], [len(r) for r in results]))
        if len(list(itertools.chain(*results))) != len(args):
            logging.error(
                "Missing answers: {} {} {} {}".format(
                    [len(r) for r in results],
                    [len(c) for c in chunks],
                    sum([len(c) for c in chunks]),
                    len(args),
                )
            )
            assert len(list(itertools.chain(*results))) == len(args)
        # print("!B ", results)
        # print("!C", list(itertools.chain(*results)))
        return list(itertools.chain(*results))

    def __enter__(self):
        assert get_start_method() == "fork"
        assert self._reuse or self._first

        if self._first:
            ## print("! enter")
            self._inqueues = [Queue() for i in range(self._processcount)]
            self._outqueues = [Queue() for i in range(self._processcount)]
            self._processes = [
                Process(
                    target=doprocess,
                    args=(
                        getGlobalProcessCounter(),
                        self._inqueues[i],
                        self._outqueues[i],
                    ),
                )
                for i in range(self._processcount)
            ]
            for p in self._processes:
                p.start()
            self._first = False
        return self

    # Clean up
    def __exit__(self, a, b, c):
        # print("!! exiting")
        for q in self._inqueues:
            q.put((None, "stats"))
        for q in self._outqueues:
            s = q.get()
            # logging.info("child stats: %s", s)
            _global_solver_ref.add_stats(s["stats"])
        if not self._reuse:
            self.cleanup()
        return False

    def cleanup(self):
        for q in self._inqueues:
            q.put((None, None))
        for p in self._processes:
            p.join()
