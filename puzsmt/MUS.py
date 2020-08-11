import copy
import types
import math
import random

from .utils import flatten, chainlist, shuffledcopy

from .base import EqVal, NeqVal

# This calculates Minimum Unsatisfiable Sets
# It users internals from solver, but is put in another file just for "neatness"



def MUS(r, solver, assume, earlycutsize):
    smtassume = [solver._varlit2smtmap[l] for l in assume]

    l = chainlist(shuffledcopy(r, smtassume), shuffledcopy(r, solver._conlits))
    core = solver.basicCore(l)

    # Should never be satisfiable on the first pass
    assert core is not None
    if earlycutsize is not None and len(core) > earlycutsize:
        return None

    # So we can find different cores if we recall method
    solver.random.shuffle(core)

    # First try chopping big bits off
    step = int(len(core) / 4)
    while step > 1:
        i = 0
        while step > 1 and i < len(core) - step:
            to_test = core[:i] + core[(i+step):]
            newcore = solver.basicCore(to_test)
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
        if lit in core:
            to_test = list(core)
            to_test.remove(lit)
            newcore = solver.basicCore(to_test)
            if newcore is not None:
                core = newcore
    
    return [solver._conmap[x] for x in core if x in solver._conmap]



def findSmallestMUS(solver, puzlits):
    musdict = {}
    # First check for really tiny ones
    for iter in range(5):
        for p in puzlits:
            mus = MUS(random.Random("{}{}{}".format(iter,p,5)), solver, [p.neg()], 5)
            if mus is not None and (p not in musdict or len(musdict[p]) > len(mus)):
                musdict[p] = mus
        # Early exit for trivial case
        if len(musdict) > 0 and min([len(v) for v in musdict.values()]) == 1:
            return musdict
    if len(musdict) > 0:
        return musdict
    for size in [100,1000,10000, math.inf]:
        for iter in range(50):
            for p in puzlits:
                mus = MUS(random.Random("{}{}{}".format(iter,p,size)), solver, [p.neg()], size)
                if mus is not None and (p not in musdict or len(musdict[p]) > len(mus)):
                    musdict[p] = mus
            if len(musdict) > 0:
                return musdict
    return musdict