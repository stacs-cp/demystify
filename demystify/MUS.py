import copy
import math
import random
import logging
import itertools
import sys
import math
from time import time

from .utils import flatten, chainlist, shuffledcopy

from .base import EqVal, NeqVal

from .config import CONFIG

# This calculates Minimum Unsatisfiable Sets
# It uses internals from solver, but is put in another file just for "neatness"

# Deal with y being a infinity, or x being a fraction
def safepow(x,y):
    p = math.pow(float(x),float(y))
    if p < 1000000:
        return int(p)
    else:
        return p

def tinyMUS(solver, assume, distance):
    smtassume = [solver._varlit2smtmap[l] for l in assume]

    if distance == 1:
        cons = flatten([solver._varlit2con[l] for l in assume])
    elif distance == 2:
        cons = flatten([solver._varlit2con2[l] for l in assume])
    else:
        print("!! Invalid distance")
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


def MUS(r, solver, assume, earlycutsize, minsize, *, initial_cons=None):
    smtassume = [solver._varlit2smtmap[a] for a in assume]

    r.shuffle(smtassume)

    if initial_cons is None:
        if CONFIG["checkCloseFirst"]:
            closecons = set(flatten([solver._varlit2con[l] for l in assume]))
            farcons = solver._conlits - closecons
            cons = r.sample(closecons, len(closecons)) + r.sample(farcons, len(farcons))
        else:
            cons = list(solver._conlits)
            r.shuffle(cons)

    else:
        cons = [solver._conlit2conmap[x] for x in initial_cons]
        r.shuffle(cons)

    # Need to use 'sample' as solver._conlits is a set
    # cons = r.sample(initial_conlits, len(initial_conlits))
    core = cons

    # We used to start with one 'core' calculation, stop that because
    # it might send us down a bad track
    # core = solver.basicCore(smtassume + cons)

    lens = [len(core)]

    if CONFIG["prechopMUSes12"]:
        step = len(core) // 2
        while step > 1 and len(core) > minsize:
            to_test = core[:-step]
            newcore = solver.basicCore(smtassume + to_test)
            if newcore is not None:
                #print("Prechop %s -> %s with step %s", len(core), len(newcore), step)
                assert len(newcore) < len(core)
                core = newcore
            step = min(step//2, len(core)//2)

    if CONFIG["tryManyChopMUS"]:
        for squash in [1/2, 1/4, 1/8, 1/16, 1/32, 1/64, 1/128, 1/256, 1/512, 1/1024, 1/2048, 1/4096]:
            step = int(len(core)*squash)
            loopsize = safepow(1/(1-squash), minsize + 1)
            if loopsize <= 10:
                break
        
        
        logging.debug("tryManyChop: %s %s %s %s %s", squash, step, loopsize, len(core), minsize)

        done = False
        for tries in range(loopsize*2):
            random.sample(core, len(core))
            newcore = solver.basicCore(smtassume + core[:-step])
            if newcore is not None:
                logging.debug("prechop: %s %s %s", tries, loopsize, len(newcore))
                done = True
                core = newcore
                break
        
        if not done:
            logging.debug("tryManyChop miss")
            return None
        else:
            logging.debug("tryManyChop hit : %s", len(core))

    if CONFIG["minPrecheckMUS"]:
        step = len(core)//(minsize*2)
        if step > 1:
            i = 0
            badcount = 0
            while i*step < len(core):
                to_test = core[:(i*step)] + core[((i+1)*step):]
                solvable = solver._solver.solveLimited(smtassume + to_test)
                logging.debug("minprecheck: %s %s %s %s %s %s %s", i, step, (i*step), ((i+1)*step), len(core), solvable, solver._solver._lasttime)
                if solvable == False:
                    core = to_test
                else:
                    i += 1
                    if solvable is not None:
                        badcount += 1
                        if badcount > minsize:
                            logging.debug("minprecheck reject: %s %s %s", i, step, len(core))
                            return None

    if CONFIG["minPrecheckStepsMUS"]:
        step = len(core)//(minsize*2)
        while step > 2:
            oldsize = len(core)
            i = 0
            badcount = 0
            while i*step < len(core):
                to_test = core[:(i*step)] + core[((i+1)*step):]
                solvable = solver._solver.solveLimited(smtassume + to_test)
                logging.debug("minprecheckstep: %s %s %s %s %s %s %s", i, step, (i*step), ((i+1)*step), len(core), solvable, solver._solver._lasttime)
                if solvable == False:
                    core = to_test
                else:
                    i += 1
                    if solvable is not None:
                        badcount += 1
                        if badcount > minsize:
                            logging.debug("minprecheckstep reject: %s %s %s", i, step, len(core))
                            return None
            if len(core) == oldsize:
                logging.debug("minprecheck stuck")
                # Got stuck
                return None
            logging.debug("minprecheckstep loop: %s %s %s %s %s %s", oldsize, len(core), step, len(core)//(minsize*2), i, badcount)
            step = len(core)//(minsize*2)

    if CONFIG["gallopingMUSes"]:
        step = 1
        pos = 0
        calls = 0
        while True:

            # Stage 1: Look for something to delete
            solvable = False
            while not solvable:
                logging.debug("Core step up: %s %s %s", pos, len(core), step)
                if pos >= len(core):
                    logging.debug("Core passed: %s %s %s", assume, len(core), calls)
                    return [solver._conmap[x] for x in core if x in solver._conmap]

                to_test = core[:pos] + core[(pos + step):]
                assert(len(to_test) < len(core))
                solvable = solver._solver.solve(smtassume + to_test,getsol=False)
                if solvable == False:
                    core = to_test
                    step = step * 2

            logging.debug("Core Stage 2: %s %s %s", pos, len(core), step)

            step = step // 2
            # Stage 2: Focus
            while step > 0:
                logging.debug("Core Stage 2 step: %s %s %s", pos, len(core), step)
                to_test = core[:pos] + core[(pos + step):]
                assert(len(to_test) < len(core))
                solvable = solver._solver.solve(smtassume + to_test,getsol=False)
                if solvable == False:
                    core = to_test
                step = step // 2
            
            step = 1
            # Step
            to_test = core[:pos] + core[(pos + step):]
            assert solver._solver.solve(smtassume + to_test,getsol=False) == True
            pos += 1
            if pos >= minsize:
                to_test = core[:pos]
                if solver._solver.solve(smtassume + to_test,getsol=False) != False:
                    logging.debug("Core failed: %s %s %s", assume, minsize, calls)
                    return None
                else:
                    logging.debug("Core found: %s %s %s", assume, minsize, calls)
                    return [solver._conmap[x] for x in to_test if x in solver._conmap]


    # Final cleanup
    # We need to be prepared for things to disappear as
    # we reduce the core, so make a copy and iterate through
    # that
    stepcount = 0
    badcount = 0
    corecpy = list(core)
    for lit in corecpy:
        if lit in core:
            logging.debug("Trying to remove %s", lit)
            to_test = list(core)
            to_test.remove(lit)
            newcore = solver.basicCore(smtassume + to_test)
            stepcount += 1
            if newcore is not None:
                logging.debug("Can remove: %s", lit)
                core = newcore
                lens.append((lit,len(core)))
            else:
                logging.debug("Failed to remove: %s", lit)
                badcount += 1

                if CONFIG["earlyExit"] and badcount > minsize:
                    logging.debug(
                        "Core for %s %s: failed - badcount too big: %s of %s failed towards %s",
                        assume,
                        lens,
                        badcount,
                        stepcount,
                        minsize,
                    )
                    return None

    logging.debug(
        "Core for %s : %s to %s, with %s steps, %s bad (minsize %s)",
        assume,
        lens,
        len(core),
        stepcount,
        minsize,
        badcount,
    )
    return [solver._conmap[x] for x in core if x in solver._conmap]


# Needs to be global so we can call it from a child process
_global_solver_ref = None


def update_musdict(musdict, p, mus):
    if mus is None:
        return
    elif p not in musdict:
        logging.info("XX found first {} {}".format(p, len(mus)))
        musdict[p] = [tuple(sorted(mus))]
    elif len(musdict[p][0]) > len(mus):
        logging.info("XX found new best {} {} {}".format(p, len(musdict[p][0]), len(mus)))
        musdict[p] = [tuple(sorted(mus))]
    elif p in musdict and len(musdict[p][0]) == len(mus):
        logging.info("XX add new best {} {} {}".format(p, len(musdict[p][0]), len(mus)))
        musdict[p].append(tuple(sorted(mus)))
    else:
        assert len(musdict[p][0]) < len(mus)

def musdict_minimum(musdict):
    if len(musdict) == 0:
        return math.inf
    return min(len(v[0]) for v in musdict.values())

def _parfunc_dotinymus(args):
    (p, distance) = args
    return (p, tinyMUS(_global_solver_ref, [p.neg()], distance))


def getTinyMUSes(solver, puzlits, musdict, *, distance, repeats):
    global _global_solver_ref
    _global_solver_ref = solver
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

def _parfunc_docheckmus(args):
    (p, oldmus) = args
    return (
        p,
        MUS(
            random.Random("X"),
            _global_solver_ref,
            [p.neg()],
            math.inf,
            math.inf,
            initial_cons=oldmus,
        ),
    )


# Check an existing dictionary. Reject any invalid MUS and squash any good MUS
def checkMUS(solver, puzlits, oldmus, musdict):
    global _global_solver_ref
    _global_solver_ref = solver
    if len(oldmus) > 0:
        with getPool(CONFIG["cores"]) as pool:
            res = pool.map(
                _parfunc_docheckmus, [(p, mus) for p in puzlits if p in oldmus for mus in oldmus[p]]
            )
            for (p, newmus) in res:
                # print("!!! {} :: {}".format(oldmus[p], newmus))
                assert newmus is not None
                update_musdict(musdict, p, newmus)


from multiprocessing import Pool, Process, get_start_method, Queue

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


def getPool(cores):
    if cores <= 1:
        return FakePool()
    else:
        return ProcessPool(processes=cores)
    #    return Pool(processes=cores)


_process_parfunc = None


def doprocess(id, inqueue, outqueue):
    count = 0
    if CONFIG["resetSolverFork"]:
        _global_solver_ref.reboot(id)
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
    return list(
        list(a[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)]) for i in range(n)
    )


global_process_counter = 0


def getGlobalProcessCounter():
    global global_process_counter
    global_process_counter += 1
    return global_process_counter


class ProcessPool:
    def __init__(self, processes):
        assert processes > 1
        self._processcount = processes

    def map(self, func, args):
        # Make this repeatable, but shuffled differently on each call
        random.Random(getGlobalProcessCounter()).shuffle(args)
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
        ## print("! enter")
        self._inqueues = [Queue() for i in range(self._processcount)]
        self._outqueues = [Queue() for i in range(self._processcount)]
        self._processes = [
            Process(target=doprocess, args=(getGlobalProcessCounter(), self._inqueues[i], self._outqueues[i]))
            for i in range(self._processcount)
        ]
        for p in self._processes:
            p.start()
        return self

    # Clean up
    def __exit__(self, a, b, c):
        ## print("! exit")
        for q in self._inqueues:
            q.put((None, None))
        for p in self._processes:
            p.join()
        return False

def _findSmallestMUS_func(tup):
    (p, randstr, shortcutsize, minsize) = tup
    #logging.info("Random str: '%s'", randstr)
    return (
        p,
        MUS(
            random.Random(randstr),
            _global_solver_ref,
            [p.neg()],
            shortcutsize,
            minsize,
        ),
    )


def cascadeMUS(solver, puzlits, repeats, musdict):
    # We need this to be accessible by the pool
    global _global_solver_ref
    _global_solver_ref = solver

    # Have to duplicate code, to swap loops around
    if CONFIG["resetSolverMUS"]:
        for minsize in range(CONFIG["baseSizeMUS"], 200, 1):
            with getPool(CONFIG["cores"]) as pool:
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
                            math.inf,
                            minsize * CONFIG["cascadeMult"],
                        )
                        for r in range(repeats)
                        for p in puzlits
                    ],
                )
                for (p, mus) in res:
                    if mus is not None and len(mus) < minsize:
                        logging.info("!! Found smaller !!!! {} {}".format(len(mus), minsize))
                    if mus is not None and len(mus) > minsize:
                        logging.info("!! Found bigger !!!! {} {}".format(len(mus), minsize))
                    update_musdict(musdict, p, mus)
                if musdict_minimum(musdict) <= minsize:
                    return
    else:
        with getPool(CONFIG["cores"]) as pool:
            for minsize in range(CONFIG["baseSizeMUS"], 200, 1):
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
                            math.inf,
                            minsize * CONFIG["cascadeMult"],
                        )
                        for r in range(repeats)
                        for p in puzlits
                    ],
                )
                for (p, mus) in res:
                    if mus is not None and len(mus) < minsize:
                        logging.info("!! Found smaller !!!! {} {}".format(len(mus), minsize))
                    if mus is not None and len(mus) > minsize:
                        logging.info("!! Found bigger !!!! {} {}".format(len(mus), minsize))
                    update_musdict(musdict, p, mus)
                if musdict_minimum(musdict) <= minsize:
                    return

class CascadeMUSFinder:
    def __init__(self, solver):
        self._solver = solver
        self._bestcache = {}

    def smallestMUS(self, puzlits):
        musdict = {}
        if CONFIG["checkSmall1"]:
            logging.info("Doing checkSmall1")
            getTinyMUSes(
                self._solver,
                puzlits,
                musdict,
                repeats=CONFIG["smallRepeats"],
                distance=1,
            )

        # Early exit for trivial case
        if musdict_minimum(musdict) == 1:
            logging.info("Early exit from checkSmall1")
            return musdict

        if CONFIG["useCache"]:
            checkMUS(self._solver, puzlits, self._bestcache, musdict)

        if CONFIG["checkSmall2"]:
            logging.info("Doing checkSmall2")
            getTinyMUSes(
                self._solver,
                puzlits,
                musdict,
                repeats=CONFIG["smallRepeats"],
                distance=2,
            )

        if (not CONFIG["checkSmall2"]) or (
           musdict_minimum(musdict) > 3
        ):
            cascadeMUS(self._solver, puzlits, CONFIG["repeats"], musdict)
        else:
            logging.info("Early exit: skipping cascade")

        if CONFIG["useCache"]:
            # Only store first element, to stop excessive growth
            self._bestcache = copy.deepcopy(musdict)

        return musdict
