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

from .optuxext import OptUxExt
from pysat.formula import WCNF

from .utils import flatten, chainlist, shuffledcopy, randomFromSeed

from .base import EqVal, NeqVal

from .config import CONFIG

from .parallel import getPool, setChildSolver, getChildSolver, setChildForqes, getChildForqes 

muscount = 0

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
            _parfunc_dotinymus, [(p, distance) for r in range(repeats) for p in puzlits]
        )
        for (p, mus) in res:
            update_musdict(musdict, p, mus)

# This calculates Minimum Unsatisfiable Sets using the FORQES algorithm
def MUS(solver, forqes, assume, config, maxSize=float('inf')):
    # The negation of a literal we know to be in the solution
    assume = [solver._varlit2smtmap[a] for a in assume]
    known = [k for k in solver._solver._knownlits]

    # Maybe FORQES will just work
    if forqes.initialise(assume, known, solver='g4', maxSize=maxSize):
        softClauseIndices = forqes.compute()
    else:
        return False

    # If we didn't find a small enough MUS, return false
    if softClauseIndices == False:
        return False

    # Indices appear to be out by 1 for some reason?
    bestMUS = flatten([forqes.formula.soft[i - 1] for i in softClauseIndices])

    result = [solver._conmap[x] for x in bestMUS if x in solver._conmap]
    return result


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

def _parfunc_docheckmus(args):
    (p, oldmus) = args
    return (
        p,
        MUS(
            getChildSolver(),
            [p.neg()],
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
            getChildSolver(),
            [p.neg()],
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
    (p, config, maxSize) = tup
    mus = MUS(
            getChildSolver(),
            getChildForqes(),
            [p.neg()],
            config=config,
            maxSize=maxSize
        )
    
    if mus == False:
        return False
    
    print("MUS returned: " + str(mus))
    global muscount 
    muscount += 1
    print("MUS count: " + str(muscount))
    return (p,mus)

def forqesMUS(solver, forqes, puzlits, musdict, config):
    # Removed parallelisation for now.
    # For future return though, we need the solver to be accessible by the pool
    setChildSolver(solver)
    setChildForqes(forqes)
    print("forqesMUS called")
    maxSize = 1
    while True:
        with getPool(CONFIG["cores"]) as pool:

            res = pool.map(
                    _findSmallestMUS_func,
                    [(p,config, maxSize)
                    for p in puzlits])
            print("made it?")
            res = list(filter(None, res))

            if len(res) != 0:
                break

        maxSize *= 2
                 
    for (p, mus) in res:
        update_musdict(musdict, p, mus)
    
    return


class ForqesMUSFinder:
    def __init__(self, solver):
        self._solver = solver
        self._bestcache = {}

        # The 'switches' for the constraints
        cons = list(solver._conlits)

        # The puzzle rules in CNF
        puzzleCNF = solver._cnf
        weightedCNF = WCNF()
        weightedCNF.extend(puzzleCNF.clauses)

        # Soft clauses
        for constraint in cons:
            weightedCNF.append([constraint], weight=1)
        
        # FORQES optimal MUS extractor
        self._forqes = OptUxExt(weightedCNF, solver='g4', verbose=4)

    def smallestMUS(self, puzlits):
        musdict = {}

        forqesMUS(self._solver, self._forqes, puzlits, musdict, CONFIG)

        return musdict
