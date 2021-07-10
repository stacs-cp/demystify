import math
import logging
import sys
import math

from sortedcontainers import *
from pysat.formula import WCNF

from .mus import getTinyMUSes
from .optuxext import OptUxExt
from .utils import flatten
from .config import CONFIG
from .musdict import MusDict
from .parallel import (
    getPool,
    setChildSolver,
    getChildSolver,
    setChildForqes,
    getChildForqes,
)

"""
    MUSForqes instruments the FORQES algorithm (see optux.py and optuxext.py) to
    find the smallest MUSs (as an alternative to CascadeMUSFinder).
"""
class ForqesMUSFinder:
    def __init__(self, solver):
        self._solver = solver
        self._bestcache = {}

        # The constraint selectors
        cons = list(solver._conlits)

        # The puzzle rules in CNF
        puzzleCNF = solver._cnf

        # FORQES requires a weighted CNF formula
        weightedCNF = WCNF()
        weightedCNF.extend(puzzleCNF.clauses)

        # Add the constraints as 'soft' clauses.
        for constraint in cons:
            weightedCNF.append([constraint], weight=1)

        # FORQES optimal MUS extractor (extended)
        self._forqes = OptUxExt(
            weightedCNF,
            solver="g4",
            verbose=0,
            adapt=True,
            exhaust=True,
            minz=True,
        )

    def smallestMUS(self, puzlits):
        """
        This method should return the smallest MUSes among problems of the
        form P ∧ (l != a), where P is the problem constraints + already
        known literals, l is some literal and a is some value in the known
        solution.
        """
        musdict = MusDict({})

        # Heuristic check for MUSes of size 1.
        if CONFIG["checkSmall1"]:
            logging.info("Doing checkSmall1")
            getTinyMUSes(
                self._solver,
                puzlits,
                musdict,
                repeats=CONFIG["smallRepeats"],
                distance=1,
                badlimit=3
            )

        # Early exit for trivial case
        if musdict.minimum() <= 1:
            logging.info("Early exit from checkSmall1")
            return musdict

        # Otherwise, main FORQES loop.
        forqesMUS(self._solver, self._forqes, puzlits, musdict, CONFIG)

        return musdict


def forqesMUS(solver, forqes, puzlits, musdict, config):
    """
    This function searches increasing MUSes sizes, using FORQES to check
    for each problem involving a negated solution literal, whether there is
    a smallest MUS less than that size. It has optional parallesiation.
    """

    # Make the solver and forqes objects accessible by child processes.
    setChildSolver(solver)
    setChildForqes(forqes)

    maxSize = 1
    while True:
        with getPool(CONFIG["cores"]) as pool:
            res = pool.map(
                _findSmallestMUS_func, [(p, config, maxSize) for p in puzlits]
            )
            res = list(filter(None, res))

            # If there are any MUSes less than this size, we are done.
            if len(res) != 0:
                break

        # Otherwise search for MUSes twice as large.
        maxSize *= 2

    for (p, mus) in res:
        musdict.update(p, mus)


def _findSmallestMUS_func(tup):
    """
    Function to allow parallelisation.
    """
    (p, config, maxSize) = tup
    mus = MUS(
        getChildSolver(),
        getChildForqes(),
        [p.neg()],
        config=config,
        maxSize=maxSize,
    )

    if mus == False:
        return False

    return (p, mus)


def MUS(solver, forqes, assume, config, maxSize=float("inf")):
    """
    Calculate the best MUS for a given assumption using FORQES, return false
    if the best MUS is larger than the given maximum size.
    """

    # The negation of a literal we know to be in the solution
    assume = [solver._varlit2smtmap[a] for a in assume]

    # The solution values we have already explained
    known = [k for k in solver._solver._knownlits]

    # FORQES
    if forqes.initialise(assume, known, maxSize=maxSize):
        softClauseIndices = forqes.compute()
    else:
        return False

    # If we didn't find a small enough MUS, return false
    if softClauseIndices == False:
        return False

    # FORQES returns indices of soft clauses (constraint selectors)
    bestMUS = flatten([forqes.formula.soft[i - 1] for i in softClauseIndices])

    result = [solver._conmap[x] for x in bestMUS if x in solver._conmap]

    return result
