import math
import itertools
import resource
import logging

from typing import Iterable, List
from multiprocessing import current_process
# Some boring utility functions

# Flatten a (possibly even more nested) list of lists
def flatten_internal(arr):
    for i in arr:
        if isinstance(i, Iterable):
            yield from flatten(i)
        else:
            yield i


def flatten(arr: List) -> List:
    return list(flatten_internal(arr))


def intsqrt(i: int) -> int:
    root = int(math.sqrt(i) + 0.5)
    if root * root != i:
        return None
    else:
        return root


def chainlist(*lists):
    return list(itertools.chain(*lists))


def shuffledcopy(r, l):
    cpy = l[:]
    r.shuffle(cpy)
    return cpy



def get_cpu_time_with_children():
    time_self = resource.getrusage(resource.RUSAGE_SELF)
    time_children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time_self.ru_utime + time_self.ru_stime + time_children.ru_utime + time_children.ru_stime


def get_cpu_time():
    time_self = resource.getrusage(resource.RUSAGE_SELF)
    return time_self.ru_utime + time_self.ru_stime

import numpy

def randomFromSeed(seed):
    if isinstance(seed, str):
        seed = [ord(c) for c in seed]
    return numpy.random.RandomState(seed)
    # return random.Random(seed)

def parseSavileRowName(n):
    splits = n.split("_")
    args = []
    for arg in splits[1:]:
        if arg.startswith("n"):
            c = -1 * int(arg[1:])
        else:
            c = int(arg)
        args.append(c)
    return (splits[0], tuple(args))


def getConnectedVars(clauses, con, varlits_in):
    varlits = set(varlits_in.union([-v for v in varlits_in]))

    lit2conmap = dict()
    for c in clauses:
        for l in c:
            if -l not in lit2conmap:
                lit2conmap[-l] = set()
            lit2conmap[-l].update(c)

    # Blank out counts for variables in unit clauses
    for c in clauses:
        if len(c) == 1:
            lit2conmap[c[0]] = set()
            lit2conmap[-c[0]] = set()

    if con not in lit2conmap:
        return set()
        
    found = set(lit2conmap[con])
    todo = set()
    for v in found:
        if v not in varlits:
            todo.add(v)
    while len(todo) > 0:
        val = todo.pop()
        for v in lit2conmap[-val]:
            if v not in found:
                found.add(v)
                if v not in varlits:
                    todo.add(v)
    return found.intersection(varlits)
            
