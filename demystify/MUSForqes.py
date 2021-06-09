import copy
import math
import random
import logging
import itertools
import sys
import math
import numpy

from time import time
from sortedcontainers import *

from .utils import flatten, chainlist, shuffledcopy, randomFromSeed

from .base import EqVal, NeqVal

from .config import CONFIG

from .parallel import getPool, setChildSolver, getChildSolver


# This calculates Minimum Unsatisfiable Sets
# It uses internals from solver, but is put in another file just for "neatness"

# Deal with y being too large, or x being a fraction
def safepow(x, y):
    p = math.pow(float(x), float(y))
    if p < 1000000:
        return int(p)
    else:
        return math.inf


def tinyMUS(solver, assume, distance):
    smtassume = [solver._varlit2smtmap[l] for l in assume]

    if distance == 1:
        cons = flatten([solver._varlit2con[l] for l in assume])
    elif distance == 2:
        cons = flatten([solver._varlit2con2[l] for l in assume])
    else:
        sys.exit(1)

    core = solver.basicCore(smtassume + cons)
    if core is None:
        return None

    corecpy = list(core)
    badcount = 1
    for lit in corecpy:
        if lit in core and len(core) > 2:
            to_test = list(core)
            to_test.remove(lit)
            newcore = solver.basicCore(to_test)
            if newcore is not None:
                core = newcore
            else:
                badcount += 1
                if badcount > 5:
                    return None

    return [solver._conmap[x] for x in core if x in solver._conmap]


count = 0


def MUS(r, solver, assume, minsize, *, config, initial_cons=None, just_check=False):
    # print("!!",assume)
    smtassume = [solver._varlit2smtmap[a] for a in assume]

    """
    smtassume = [solver._varlit2smtmap[a] for a in assume]
    cons = list(solver._conlits)
    
    # smtassume: hard, cons: soft
    # solver._knownlits: hard
    
    wcnf = makeWCNF(smtassume, cons)

    magicMUSFIND(wcnf)

    """

    return [solver._conmap[x] for x in core if x in solver._conmap]


def update_musdict(musdict, p, mus):
    if mus is None:
        return
    elif p not in musdict:
        logging.info("XX found first {} {}".format(p, len(mus)))
        musdict[p] = [tuple(sorted(mus))]
    elif len(musdict[p][0]) > len(mus):
        logging.info("XX found new best {} {} {}".format(
            p, len(musdict[p][0]), len(mus)))
        musdict[p] = [tuple(sorted(mus))]
    elif p in musdict and len(musdict[p][0]) == len(mus):
        logging.info("XX add new best {} {} {}".format(
            p, len(musdict[p][0]), len(mus)))
        musdict[p].append(tuple(sorted(mus)))
    else:
        assert len(musdict[p][0]) < len(mus)


def musdict_minimum(musdict):
    if len(musdict) == 0:
        return math.inf
    return min(len(v[0]) for v in musdict.values())


def _parfunc_dotinymus(args):
    (p, distance) = args
    return (p, tinyMUS(getChildSolver(), [p.neg()], distance))


def getTinyMUSes(solver, puzlits, musdict, *, distance, repeats):
    setChildSolver(solver)
    logging.info(
        "Getting tiny MUSes, distance %s, for %s puzlits, %s repeats",
        distance,
        len(puzlits),
        repeats,
    )
    with getPool(CONFIG["cores"]) as pool:
        res = pool.map(
            _parfunc_dotinymus, [(p, distance)
                                 for r in range(repeats) for p in puzlits]
        )
        for (p, mus) in res:
            update_musdict(musdict, p, mus)


def _parfunc_docheckmus(args):
    (p, oldmus) = args
    return (
        p,
        MUS(
            randomFromSeed("X"),
            getChildSolver(),
            [p.neg()],
            math.inf,
            initial_cons=oldmus,
            config=CONFIG
        ),
    )


# Check an existing dictionary. Reject any invalid MUS and squash any good MUS
def checkMUS(solver, puzlits, oldmus, musdict):
    setChildSolver(solver)
    if len(oldmus) > 0:
        with getPool(CONFIG["cores"]) as pool:
            res = pool.map(
                _parfunc_docheckmus, [
                    (p, mus) for p in puzlits if p in oldmus for mus in oldmus[p]]
            )
            for (p, newmus) in res:
                # print("!!! {} :: {}".format(oldmus[p], newmus))
                if newmus is not None:
                    update_musdict(musdict, p, newmus)


def _parfunc_dochecklitsmus(args):
    (p, oldmus) = args
    return (
        p,
        MUS(
            randomFromSeed("X"),
            getChildSolver(),
            [p.neg()],
            math.inf,
            initial_cons=oldmus,
            just_check=True,
            config=CONFIG
        ),
    )

# Check which literals are filtered by a particular MUS


def checkWhichLitsAMUSProves(solver, puzlits, mus):
    setChildSolver(solver)
    if len(puzlits) > 0:
        with getPool(CONFIG["cores"]) as pool:
            res = pool.map(
                _parfunc_dochecklitsmus, [(p, mus) for p in puzlits]
            )
            return list(p for (p, musvalid) in res if musvalid)
    else:
        return []


def _findSmallestMUS_func(tup):
    (p, randstr, minsize, config) = tup
    # logging.info("Random str: '%s'", randstr)
    return (
        p,
        MUS(
            randomFromSeed(randstr),
            getChildSolver(),
            [p.neg()],
            minsize,
            config=config,
        ),
    )


def cascadeMUS(solver, puzlits, repeats, musdict, config):
    # We need this to be accessible by the pool
    setChildSolver(solver)

    with getPool(CONFIG["cores"]) as pool:
        for minsize in range(config["baseSizeMUS"], max(config["baseSizeMUS"]+1, 10000), 1):
            # Do 'range(repeats)' first, so when we distribute we get an even spread of literals on different cores
            # minsize+1 for MUS size, as the MUS will include 'p'
            logging.info(
                  "Considering %s * %s jobs for minsize=%s",
                  repeats,
                  len(puzlits),
                  minsize,
                  )
            res = pool.map(
                   _findSmallestMUS_func,
                   [
                        (
                            p,
                            "{}:{}:{}".format(r, p, minsize),
                            minsize * CONFIG["cascadeMult"],
                            config
                        )
                        for r in range(repeats)
                        for p in puzlits
                    ],
                   )
            for (p, mus) in res:
                    if mus is not None and len(mus) < minsize:
                        logging.info(
                            "!! Found smaller !!!! {} {}".format(len(mus), minsize))
                    if mus is not None and len(mus) > minsize:
                        logging.info(
                            "!! Found bigger !!!! {} {}".format(len(mus), minsize))
                    update_musdict(musdict, p, mus)
            if musdict_minimum(musdict) <= minsize:
                return


class ForqesMUSFinder:
    def __init__(self, solver):
        self._solver = solver
        self._bestcache = {}

    def smallestMUS(self, puzlits):
        musdict = {}

        cascadeMUS(self._solver, puzlits, CONFIG["repeats"], musdict, CONFIG)

        return musdict
