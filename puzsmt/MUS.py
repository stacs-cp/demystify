import copy
import types
import math
import random
import logging
import itertools
import copy

from time import time

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
    

def MUS(r, solver, assume, earlycutsize, minsize, *, initial_cons = None):
    smtassume = [solver._varlit2smtmap[a] for a in assume]

    r.shuffle(smtassume)

    if initial_cons is None:
        cons = list(solver._conlits)
    else:
        cons = [solver._conlit2conmap[x] for x in initial_cons]

    # Need to use 'sample' as solver._conlits is a set
    r.shuffle(cons)
    #cons = r.sample(initial_conlits, len(initial_conlits))

    core = solver.basicCore(smtassume + cons)
    # If this ever fails, check why then maybe remove
    assert core is not None
    if core is None:
        logging.info("Asked for invalid core!")
        return None
    
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
                    logging.debug("Core for %s None exit: %s", assume, lens)
                    return None

        # Should never be satisfiable on the first pass
        assert core is not None
        if earlycutsize is not None and len(core) > earlycutsize:
            logging.debug("Core for %s early exit: %s", assume, lens)
            return None

    # So we can find different cores if we recall method
    r.shuffle(core)


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
    stepcount = 0
    badcount = 0
    probability = 1
    corecpy = list(core)
    for lit in corecpy:
        if lit in core and len(core) > 2:
            to_test = list(core)
            to_test.remove(lit)
            newcore = solver.basicCore(to_test)
            stepcount += 1
            if newcore is not None:
                core = newcore
                probability = 1
            else:
                badcount += 1
                probability *= minsize/len(core)
                if CONFIG["earlyExitAllFailed"] and probability < 1/10000:
                    logging.debug("Core for %s: failed - probability: %s -- %s %s %s %s", assume, probability, badcount, stepcount, minsize, len(core))
                    return None
                if CONFIG["earlyExit"] and badcount > minsize:
                    logging.debug("Core for %s : failed - badcount too big: %s / %s > 5 * %s / %s", assume, badcount, stepcount, minsize, len(core))
                    return None
                if CONFIG["earlyExitMaybe"] and (badcount > minsize or (badcount/stepcount) > 5*minsize/len(core)):
                    logging.debug("Core for %s: failed - minsize: %s / %s > 5 * %s / %s", assume, badcount, stepcount, minsize, len(core))
                    return None
    
    logging.debug("Core for %s : %s to %s, with %s steps, %s bad", assume, lens, len(core), stepcount, badcount)
    return [solver._conmap[x] for x in core if x in solver._conmap]

# Needs to be global so we can call it from a child process
_parfunc_dotinymus_solver = None
def _parfunc_dotinymus(p):
    return (p,tinyMUS(_parfunc_dotinymus_solver, [p.neg()]))

def getTinyMUSes(solver, puzlits, musdict, repeats):
    global _parfunc_dotinymus_solver
    _parfunc_dotinymus_solver = solver
    with getPool(CONFIG["cores"]) as pool:
        res = pool.map(_parfunc_dotinymus, [p for r in range(repeats) for p in puzlits])
        for (p,mus) in res:
            if mus is not None and (p not in musdict or len(musdict[p]) > len(mus)):
                    # If this ever fails, check out why. Might mean tinyMUS cannot promise size 1 MUSes
                    assert(len(mus) == 1)
                    musdict[p] = mus

from multiprocessing import Pool, Process, get_start_method, Queue

# Fake Pool for profiling with py-spy
class FakePool:
    def __init__(self):
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
        return ProcessPool(processes=cores)
    #    return Pool(processes=cores)

_process_parfunc = None

def doprocess(id, inqueue, outqueue):
    count = 0
    while True:
        # print("! {} Waiting for task".format(id))
        (func, msg) = inqueue.get()
        # print("! {} Got task {}".format(id,count))
        if func is None:
            # print("! {} exit".format(id))
            break
        outqueue.put(func(msg))
        # print("! {} Done task {}".format(id,count))
        count += 1

# Magic from https://stackoverflow.com/questions/2130016/splitting-a-list-into-n-parts-of-approximately-equal-length
def split(a, n):
    k, m = divmod(len(a), n)
    # Listify this so we check the lengths here
    return list(list(a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)]) for i in range(n))

class ProcessPool:
    def __init__(self, processes):
        assert processes > 1
        self._processcount = processes

    def map(self, func, args):
        # TODO: This can be unbalanced
        chunks = split(args, self._processcount)
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
            logging.error("Missing answers: {} {} {} {}".format([len(r) for r in results], [len(c) for c in chunks], sum([len(c) for c in chunks]), len(args)))
            assert len(list(itertools.chain(*results))) == len(args)
        # print("!B ", results)
        # print("!C", list(itertools.chain(*results)))
        return list(itertools.chain(*results))

    def __enter__(self):
        assert get_start_method() == 'fork'
        ## print("! enter")
        self._inqueues = [Queue() for i in range(self._processcount)]
        self._outqueues = [Queue() for i in range(self._processcount)]
        self._processes = [Process(target = doprocess, args=(i,self._inqueues[i], self._outqueues[i])) for i in range(self._processcount)]
        for p in self._processes:
            p.start()
        return self

    # Clean up
    def __exit__(self,a,b,c):
        ## print("! exit")
        for q in self._inqueues:
            q.put((None,None))
        for p in self._processes:
            p.join()
        return False


# Code for parallelisation of findSmallestMUSParallel
_findSmallestMUS_solver = None
def _findSmallestMUS_func(tup):
    (p, randstr, shortcutsize, minsize) = tup
    return (p,MUS(random.Random(randstr), _findSmallestMUS_solver, [p.neg()], shortcutsize, minsize))


def findSmallestMUS(solver, puzlits, repeats=3):
    musdict = {}

    # We need this to be accessible by child processes
    global _findSmallestMUS_solver
    _findSmallestMUS_solver = solver

    getTinyMUSes(solver, puzlits, musdict, repeats)

    # Early exit for trivial case
    if len(musdict) > 0 and min([len(v) for v in musdict.values()]) == 1:
        return musdict

    with getPool(CONFIG["cores"]) as pool:
        for (shortcutsize,minsize) in [(50,3),(200,5),(500,8),(1000,20),(math.inf,math.inf)]:
            for iter in range(repeats):
                res = pool.map(_findSmallestMUS_func,
                    [(p,"{}{}{}".format(iter,p,shortcutsize),shortcutsize,minsize)  for p in puzlits])
                for (p,mus) in res:
                    if mus is not None and (p not in musdict or len(musdict[p]) > len(mus)):
                        assert(len(mus) > 1)
                        musdict[p] = mus
            if len(musdict) > 0 and min([len(v) for v in musdict.values()]) <= minsize:
                return musdict
        return musdict


# Check an existing dictionary. Reject any invalid MUS and squash any good MUS
def checkMUS(solver, puzlits, oldmus, musdict):
    for p in puzlits:
        if p in oldmus and len(oldmus[p]) < 12:
            newmus = MUS(random.Random("X"), solver, [p.neg()], math.inf, math.inf, initial_cons = oldmus[p])
            #print("!!! {} :: {}".format(oldmus[p], newmus))
            assert newmus is not None
            if len(newmus) < len(oldmus[p]):
                logging.info("Squashed a MUS %s %s -> %s", p, len(oldmus[p]), len(newmus))
            musdict[p] = newmus

def cascadeMUS(solver, puzlits, repeats, musdict):
    # We need this to be accessible by the pool
    global _findSmallestMUS_solver
    _findSmallestMUS_solver = solver

    with getPool(CONFIG["cores"]) as pool:
        for minsize in range(2,200,1):
            # Do 'range(repeats)' first, so when we distribute we get an even spread of literals on different cores
            res = pool.map(_findSmallestMUS_func,[(p,"{}{}{}".format(iter,p,minsize),math.inf,minsize*CONFIG["cascadeMult"]) for _ in range(repeats) for p in puzlits])
            for (p,mus) in res:
                if mus is not None and (p not in musdict or len(musdict[p]) > len(mus)):
                    assert(len(mus) > 1)
                    musdict[p] = mus
            if len(musdict) > 0 and min([len(v) for v in musdict.values()]) <= minsize:
                return musdict
        return

class BasicMUSFinder:

    def __init__(self, solver):
        self._solver = solver
    
    def smallestMUS(self, puzlits):
        return findSmallestMUS(self._solver, puzlits, CONFIG["repeats"])


class CascadeMUSFinder:

    def __init__(self, solver, repeats = CONFIG["repeats"]):
        self._solver = solver
        self._repeats = repeats
        self._bestcache = {}
    
    def smallestMUS(self, puzlits):
        musdict = {}
        getTinyMUSes(self._solver, puzlits, musdict, self._repeats)

        # Early exit for trivial case
        if len(musdict) > 0 and min([len(v) for v in musdict.values()]) == 1:
            return musdict

        if CONFIG["useCache"]:
            checkMUS(self._solver, puzlits, self._bestcache, musdict)

        cascadeMUS(self._solver, puzlits, self._repeats, musdict)

        if CONFIG["useCache"]:
            self._bestcache = copy.deepcopy(musdict)

        #print("!! {} {}".format(min(len(v) for v in musdict.values()), max(len(v) for v in musdict.values())))
        return musdict