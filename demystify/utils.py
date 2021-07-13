import math
import itertools
import resource
import logging
import sys
import copy

from sortedcontainers import *

from typing import Iterable, List
from multiprocessing import current_process

# Some boring utility functions

# Deal with y being too large, or x being a fraction
def safepow(x, y):
    p = math.pow(float(x), float(y))
    if p < 1000000:
        return int(p)
    else:
        return math.inf


# Flatten a (possibly even more nested) list of lists
def flatten_internal(arr):
    for i in arr:
        if isinstance(i, Iterable):
            yield from flatten(i)
        else:
            yield i


def flatten(arr: List) -> List:
    return list(flatten_internal(arr))

def in_flattened_internal(arr, x):
    for i in arr:
        if isinstance(i, Iterable):
            if in_flattened_internal(i, x):
                return True
        else:
            if i == x:
                return True
    return False


def in_flattened(arr: List, x) -> bool:
    return in_flattened_internal(arr, x)


def intsqrt(i: int) -> int:
    root = int(math.sqrt(i) + 0.5)
    if root * root != i:
        return None
    else:
        return root


def lowsqrt(i: int) -> int:
    return int(math.sqrt(i))


def chainlist(*lists):
    return list(itertools.chain(*lists))


def shuffledcopy(r, l):
    cpy = l[:]
    r.shuffle(cpy)
    return cpy


def get_cpu_time_with_children():
    time_self = resource.getrusage(resource.RUSAGE_SELF)
    time_children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return (
        time_self.ru_utime
        + time_self.ru_stime
        + time_children.ru_utime
        + time_children.ru_stime
    )


def get_cpu_time():
    time_self = resource.getrusage(resource.RUSAGE_SELF)
    return time_self.ru_utime + time_self.ru_stime


import numpy


def randomFromSeed(seed):
    if isinstance(seed, str):
        seed = [ord(c) for c in seed]
    return numpy.random.RandomState(seed)
    # return random.Random(seed)


def parseSavileRowName(vars, auxvars, n):
    varmatch = [v for v in vars if n.startswith(v)]
    if len(varmatch) == 0:
        if not any(v for v in auxvars if n.startswith(v)):
            print(
                "Cannot find {} in the VAR list {} -- should it be AUX?".format(
                    n, vars
                )
            )
        return None
    if len(varmatch) > 1:
        print(
            "Variables cannot have a common prefix: Can't tell if {} is {}".format(
                n, varmatch
            )
        )
        sys.exit(1)

    varmatch = varmatch[0]

    n = n[len(varmatch) + 1 :]

    splits = n.split("_")
    args = []
    for arg in splits:
        if arg != "":
            if arg.startswith("n"):
                c = -1 * int(arg[1:])
            else:
                c = str(int(arg))
            args.append(c)
    return (varmatch, tuple(args))


def build_lit2conmap(clauses):
    lit2conmap = dict()
    for c in clauses:
        for l in c:
            if -l not in lit2conmap:
                lit2conmap[-l] = SortedSet()
            lit2conmap[-l].update(c)

    # Blank out counts for variables in unit clauses
    for c in clauses:
        if len(c) == 1:
            lit2conmap[c[0]] = SortedSet()
            lit2conmap[-c[0]] = SortedSet()
    return lit2conmap

def build_lit2clausemap(clauses):
    litmap = dict()
    for c in clauses:
        for l in c:
            if -l not in litmap:
                litmap[-l] = []
            litmap[-l].append(c)

    return litmap

# Check if this constraint is already known
# We classify a constraint as 'known' if the clauses
# it appears in are all the same as a pre-existing clause
def checkConstraintAlreadyParsed(formula, con, name):
    if not hasattr(formula, "lit2conmap"):
        formula.lit2clausemap = build_lit2clausemap(formula.clauses)

    lit2clausemap = formula.lit2clausemap

    if not hasattr(formula, "concollection"):
        formula.concollection = {}

    if con not in lit2clausemap:
        logging.debug("Constraint never mentioned: %s", name)
        return True

    # Generate clauses, normalising the 'constraint' variable
    logging.debug("Check: %s", lit2clausemap[con])

    # x*2 just to make sure we can use 1/-1 to normalise the constraint
    concpy = tuple(SortedSet([tuple(SortedSet([1 if x == con else -1 if x == -con else x*2 for x in c])) for c in lit2clausemap[con]]))


    logging.debug("Check2: %s", concpy)

    if concpy == () or concpy==((-1,1),):
        logging.debug("Constraint never used: %s", name)
        return True

    if concpy in formula.concollection:
        logging.info("duplicate found: %s = %s", name, formula.concollection[concpy])
        return True
    else:
        formula.concollection[concpy] = name
        return False



def getConnectedVars(formula, con, varlits_in):
    varlits = SortedSet(varlits_in.union([-v for v in varlits_in]))

    if not hasattr(formula, "lit2conmap"):
        formula.lit2conmap = build_lit2conmap(formula.clauses)

    lit2conmap = formula.lit2conmap

    if con not in lit2conmap:
        return SortedSet()

    found = SortedSet(lit2conmap[con])
    todo = SortedSet()
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
