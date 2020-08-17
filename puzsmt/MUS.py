import copy
import types
import math
import random
import logging
import itertools

from .utils import flatten, chainlist, shuffledcopy

from .base import EqVal, NeqVal

from .config import CONFIG

# This calculates Minimum Unsatisfiable Sets
# It uses internals from solver, but is put in another file just for "neatness"


def tinyMUS(solver, assume):
    smtassume = [solver._varlit2smtmap[l] for l in assume]

    cons = flatten([solver._varlit2con[l] for l in assume])

    core = solver.basicCore(smtassume + cons)
    if core is None:
        return None

    corecpy = list(core)
    for lit in corecpy:
        if lit in core and len(core) > 2:
            to_test = list(core)
            to_test.remove(lit)
            newcore = solver.basicCore(to_test)
            if newcore is not None:
                core = newcore
    
    return [solver._conmap[x] for x in core if x in solver._conmap]
    

def MUS(r, solver, assume, earlycutsize, minsize):
    smtassume = [solver._varlit2smtmap[a] for a in assume]

    r.shuffle(smtassume)

    # Need to use 'sample' as solver._conlits is a set
    cons = r.sample(solver._conlits, len(solver._conlits))

    core = solver.basicCore(smtassume + cons)
    
    lens = [len(core)]

    if False:
        while len(lens) <= 5 and len(core) > 2:
            shufcpy = shuffledcopy(r, core)
            del shufcpy[-1]
            newcore = solver.basicCore(shufcpy)
            if newcore is not None:
                core = newcore
                lens.append(len(core))
            else:
                lens.append(None)
                if len(core) > earlycutsize:
                    logging.info("Core for %s None exit: %s", assume, lens)
                    return None

        # Should never be satisfiable on the first pass
        assert core is not None
        if earlycutsize is not None and len(core) > earlycutsize:
            logging.info("Core for %s early exit: %s", assume, lens)
            return None

    # So we can find different cores if we recall method
    r.shuffle(core)

    stepcount = 0
    badcount = 0
    # First try chopping big bits off
    if False:
        step = int(len(core) / 4)
        while step > 1 and len(core) > 2:
            i = 0
            while step > 1 and i < len(core) - step:
                to_test = core[:i] + core[(i+step):]
                newcore = solver.basicCore(to_test)
                stepcount += 1
                if newcore is not None:
                    assert(len(newcore) < len(core))
                    core = newcore
                    i = 0
                    step = int(len(core) / 4)
                else:
                    i += step
            step = int(step / 2)

    # Final cleanup
    # We need to be prepared for things to disappear as
    # we reduce the core, so make a copy and iterate through
    # that
    corecpy = list(core)
    for lit in corecpy:
        if lit in core and len(core) > 2:
            to_test = list(core)
            to_test.remove(lit)
            newcore = solver.basicCore(to_test)
            stepcount += 1
            if newcore is not None:
                core = newcore
            else:
                badcount += 1
                if badcount > minsize:
                    logging.info("Core for %s : failed - badcount too big: %s / %s > 5 * %s / %s", assume, badcount, stepcount, minsize, len(core))
                    return None
                if badcount > minsize or (badcount/stepcount) > 5*minsize/len(core):
                    logging.info("Core for %s: failed - minsize: %s / %s > 5 * %s / %s", assume, badcount, stepcount, minsize, len(core))
                    return None
    
    logging.info("Core for %s : %s to %s, with %s steps, %s bad", assume, lens, len(core), stepcount, badcount)
    return [solver._conmap[x] for x in core if x in solver._conmap]

def getTinyMUSes(solver, puzlits, musdict):
    for p in puzlits:
        mus = tinyMUS(solver, [p.neg()])
        if mus is not None:
            assert(len(mus) == 1)
            musdict[p] = mus



from multiprocessing import Pool

# Fake Pool for profiling with py-spy
class FakePool:
    def __init__(self, processes):
        pass
    
    def map(self, func, args):
        return list(map(func, args))

    def __enter__(self):
        return self

    def __exit__(self,a,b,c):
        pass

def getPool(cores):
    if cores <= 1:
        return FakePool()
    else:
        return Pool(processes=cores)


# Code for parallelisation of findSmallestMUSParallel
parsolver = []
def dopar(tup):
    (p, randstr, shortcutsize, minsize) = tup
    return (p,MUS(random.Random(randstr), parsolver, [p.neg()], shortcutsize, minsize))


def findSmallestMUS(solver, puzlits, repeats=3):
    musdict = {}
    muscount = {p:0 for p in puzlits}

    # We need this to be accessible by the pool
    global parsolver
    parsolver = solver

    getTinyMUSes(solver, puzlits, musdict)

    # Early exit for trivial case
    if len(musdict) > 0 and min([len(v) for v in musdict.values()]) == 1:
        return musdict

    with getPool(CONFIG["cores"]) as pool:
        for (shortcutsize,minsize) in [(50,3),(200,5),(500,8),(1000,20),(math.inf,math.inf)]:
            for iter in range(repeats):
                res = pool.map(dopar,[(p,"{}{}{}".format(iter,p,shortcutsize),shortcutsize,minsize)  for p in puzlits if muscount[p] < repeats])
                for (p,mus) in res:
                    if mus is not None and (p not in musdict or len(musdict[p]) > len(mus)):
                        assert(len(mus) > 1)
                        musdict[p] = mus
                        muscount[p] += 1
            if len(musdict) > 0 and min([len(v) for v in musdict.values()]) <= minsize:
                return musdict
        return musdict


def cascadeMUS(solver, puzlits, repeats):
    musdict = {}
    muscount = {p:0 for p in puzlits}

    # We need this to be accessible by the pool
    global parsolver
    parsolver = solver

    getTinyMUSes(solver, puzlits, musdict)

    # Early exit for trivial case
    if len(musdict) > 0 and min([len(v) for v in musdict.values()]) == 1:
        return musdict

    with Pool(processes=12) as pool:
        for minsize in range(2,200,1):
            for iter in range(repeats):
                res = pool.map(dopar,[(p,"{}{}{}".format(iter,p,minsize),math.inf,minsize*2)  for p in puzlits if muscount[p] < repeats])
                for (p,mus) in res:
                    if mus is not None and (p not in musdict or len(musdict[p]) > len(mus)):
                        assert(len(mus) > 1)
                        musdict[p] = mus
            if len(musdict) > 0 and min([len(v) for v in musdict.values()]) <= minsize:
                return musdict
        return musdict

class BasicMUSFinder:

    def __init__(self, solver):
        self._solver = solver
    
    def smallestMUS(self, puzlits):
        return findSmallestMUS(self._solver, puzlits, CONFIG["repeats"])


class CascadeMUSFinder:

    def __init__(self, solver, repeats=1):
        self._solver = solver
        self._repeats = repeats
    
    def smallestMUS(self, puzlits):
        return cascadeMUS(self._solver, puzlits, CONFIG["repeats"])