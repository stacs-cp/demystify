import copy
import types
import math
import random
import logging

from .utils import flatten, chainlist, shuffledcopy

from .base import EqVal, NeqVal

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
    smtassume = [solver._varlit2smtmap[l] for l in assume]

    l = chainlist(shuffledcopy(r, smtassume), shuffledcopy(r, solver._conlits))
    #l = chainlist(shuffledcopy(r, smtassume), shuffledcopy(r, solver._conlits))
    core = solver.basicCore(l)

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
                    logging.info("Core None exit: %s", lens)
                    return None

        # Should never be satisfiable on the first pass
        assert core is not None
        if earlycutsize is not None and len(core) > earlycutsize:
            logging.info("Core early exit: %s", lens)
            return None

    # So we can find different cores if we recall method
    solver.random.shuffle(core)

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
                    logging.info("Core: failed - badcount too big: %s / %s > 5 * %s / %s",badcount, stepcount, minsize, len(core))
                    return None
                if badcount > minsize or (badcount/stepcount) > 5*minsize/len(core):
                    logging.info("Core: failed - minsize: %s / %s > 5 * %s / %s",badcount, stepcount, minsize, len(core))
                    return None
    
    logging.info("Core: %s to %s, with %s steps, %s bad", lens, len(core), stepcount, badcount)
    return [solver._conmap[x] for x in core if x in solver._conmap]

from multiprocessing import Pool

parsolver = []
def dopar(tup):
    (p, randstr, shortcutsize, minsize) = tup
    return (p,MUS(random.Random(randstr), parsolver, [p.neg()], shortcutsize, minsize))

def findSmallestMUSParallel(solver, puzlits, repeats=3):
    musdict = {}
    muscount = {p:0 for p in puzlits}

    # We need this to be accessible by the pool
    global parsolver
    parsolver = solver

    for p in puzlits:
        mus = tinyMUS(solver, [p.neg()])
        if mus is not None:
            assert(len(mus) == 1)
            musdict[p] = mus
    # Early exit for trivial case
    if len(musdict) > 0 and min([len(v) for v in musdict.values()]) == 1:
        return musdict

    with Pool(processes=12) as pool:
        for (shortcutsize,minsize) in [(50,3),(200,5),(500,8),(1000,math.inf)]:
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

def findSmallestMUS(solver, puzlits, repeats=3):
    return findSmallestMUSParallel(solver, puzlits, repeats=3)
    musdict = {}
    muscount = {p:0 for p in puzlits}

    for p in puzlits:
        mus = tinyMUS(solver, [p.neg()])
        if mus is not None:

            assert(len(mus) == 1)
            musdict[p] = mus
    # Early exit for trivial case
    if len(musdict) > 0 and min([len(v) for v in musdict.values()]) == 1:
        return musdict

    for (shortcutsize,minsize) in [(50,3),(200,5),(500,8),(1000,math.inf)]:
        for iter in range(repeats):
            for p in puzlits:
                if muscount[p] < repeats:
                    mus = MUS(random.Random("{}{}{}".format(iter,p,shortcutsize)), solver, [p.neg()], shortcutsize, minsize)
                    if mus is not None and (p not in musdict or len(musdict[p]) > len(mus)):
                        assert(len(mus) > 1)
                        musdict[p] = mus
                        muscount[p] += 1
        if len(musdict) > 0 and min([len(v) for v in musdict.values()]) <= minsize:
            return musdict
    return musdict