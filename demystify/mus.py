import copy
import math
import logging
import sys
import math
import multiprocessing

from sortedcontainers import *

from .utils import flatten, randomFromSeed, safepow
from .config import CONFIG
from .parallel import getPool, setChildSolver, getChildSolver
from .musdict import MusDict

# This calculates Minimum Unsatisfiable Sets
# It uses internals from solver, but is put in another file just for "neatness"

def tinyMUS(solver, assume, distance, badlimit):
    smtassume = [solver._varlit2smtmap[l] for l in assume]
    if distance == 1:
        cons = flatten([solver._varlit2con[l] for l in assume])
    elif distance == 2:
        cons = flatten([solver._varlit2con2[l] for l in assume])
    else:
        cons = list(solver._conlits)

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
                if badcount > badlimit:
                    logging.info("ZZFail %s %s %s", lit, len(core), badcount)
                    return None

    logging.info("ZZPass %s %s %s", lit, len(core), badcount)
    return [solver._conmap[x] for x in core if x in solver._conmap]


count = 0


def MUS(
    r, solver, assume, minsize, *, config, initial_cons=None, just_check=False
):
    smtassume = [solver._varlit2smtmap[a] for a in assume]

    if config["dumpSAT"]:
        global count
        count += 1
        solver._solver.dumpSAT(
            str(count) + "-" + str(assume) + ".cnf", smtassume
        )

    r.shuffle(smtassume)

    if initial_cons is None:
        if config["checkCloseFirst"]:
            closecons = SortedSet(
                flatten([solver._varlit2con[l] for l in assume])
            )
            farcons = solver._conlits - closecons
            cons = r.sample(closecons, len(closecons)) + r.sample(
                farcons, len(farcons)
            )
        else:
            cons = list(solver._conlits)
            r.shuffle(cons)

    else:
        cons = [solver._conlit2conmap[x] for x in initial_cons]
        r.shuffle(cons)

    # Need to use 'sample' as solver._conlits is a SortedSet
    # cons = r.sample(initial_conlits, len(initial_conlits))
    core = cons

    if just_check:
        return solver.basicCore(smtassume + cons) is not None

    # Check if the initial input was not even a MUS
    if initial_cons is not None and solver.basicCore(smtassume + cons) is None:
        return None

    lens = [len(core)]

    if config["prechopMUSes12"]:
        step = len(core) // 2
        while step > 1 and len(core) > minsize:
            to_test = core[:-step]
            newcore = solver.basicCore(smtassume + to_test)
            if newcore is not None:
                assert len(newcore) < len(core)
                core = newcore
                break
            step = min(step // 2, len(core) // 2)

    if config["tryManyChopMUS"]:
        for squash in [
            1 / 2,
            1 / 4,
            1 / 8,
            1 / 16,
            1 / 32,
            1 / 64,
            1 / 128,
            1 / 256,
            1 / 512,
            1 / 1024,
            1 / 2048,
            1 / 4096,
        ]:
            step = int(len(core) * squash)
            loopsize = safepow(1 / (1 - squash), minsize + 1)
            if loopsize <= 10:
                break

        logging.debug(
            "tryManyChop: %s %s %s %s %s %s",
            assume, squash,
            step,
            loopsize,
            len(core),
            minsize,
        )

        if loopsize <= 10:
            done = False
            for tries in range(loopsize):
                r.shuffle(core)
                newcore = solver.basicCore(smtassume + core[:-step])
                if newcore is not None:
                    logging.debug(
                        "prechop: %s %s %s", tries, loopsize, len(newcore)
                    )
                    done = True
                    core = newcore
                    break

            if not done:
                logging.debug("tryManyChop miss")
                return None
            else:
                logging.debug("tryManyChop hit : %s", len(core))
        else:
            logging.debug("Skip tryManyChop")

    if config["minPrecheckMUS"]:
        step = len(core) // (minsize * 2)
        if step > 1:
            i = 0
            badcount = 0
            while i * step < len(core):
                to_test = core[: (i * step)] + core[((i + 1) * step) :]
                solvable = solver._solver.solveLimited(smtassume + to_test)
                logging.debug(
                    "minprecheck: %s %s %s %s %s %s %s",
                    i,
                    step,
                    (i * step),
                    ((i + 1) * step),
                    len(core),
                    solvable,
                    solver._solver._lasttime,
                )
                if solvable == False:
                    core = to_test
                else:
                    i += 1
                    if solvable is not None:
                        badcount += 1
                        if badcount > minsize:
                            logging.debug(
                                "minprecheck reject: %s %s %s",
                                i,
                                step,
                                len(core),
                            )
                            return None

    if config["minPrecheckStepsMUS"]:
        step = len(core) // (minsize * 2)
        while step > 2:
            oldsize = len(core)
            i = 0
            badcount = 0
            while i * step < len(core):
                to_test = core[: (i * step)] + core[((i + 1) * step) :]
                solvable = solver._solver.solveLimited(smtassume + to_test)
                logging.debug(
                    "minprecheckstep: %s %s %s %s %s %s %s",
                    i,
                    step,
                    (i * step),
                    ((i + 1) * step),
                    len(core),
                    solvable,
                    solver._solver._lasttime,
                )
                if solvable == False:
                    core = to_test
                else:
                    i += 1
                    if solvable is not None:
                        badcount += 1
                        if badcount > minsize:
                            logging.debug(
                                "minprecheckstep reject: %s %s %s",
                                i,
                                step,
                                len(core),
                            )
                            return None
            if len(core) == oldsize:
                logging.debug("minprecheck stuck")
                # Got stuck
                return None
            logging.debug(
                "minprecheckstep loop: %s %s %s %s %s %s",
                oldsize,
                len(core),
                step,
                len(core) // (minsize * 2),
                i,
                badcount,
            )
            step = len(core) // (minsize * 2)

    if config["gallopingMUSes"]:
        calls = 0
        step = 1
        pos = 0
        while True:

            # Stage 1: Look for something to delete
            solvable = False
            while not solvable:
                logging.debug("Core step up: %s %s %s", pos, len(core), step)
                if pos >= len(core):
                    logging.debug(
                        "Core passed: %s %s %s", assume, len(core), calls
                    )
                    return [
                        solver._conmap[x] for x in core if x in solver._conmap
                    ]

                to_test = core[:pos] + core[(pos + step) :]
                assert len(to_test) < len(core)
                solvable = solver._solver.solve(
                    smtassume + to_test, getsol=False
                )
                if solvable == False:
                    core = to_test
                    step = step * 2

            logging.debug("Core Stage 2: %s %s %s", pos, len(core), step)

            step = step // 2
            # Stage 2: Focus
            while step > 0:
                logging.debug(
                    "Core Stage 2 step: %s %s %s", pos, len(core), step
                )
                to_test = core[:pos] + core[(pos + step) :]
                assert len(to_test) < len(core)
                solvable = solver._solver.solve(
                    smtassume + to_test, getsol=False
                )
                if solvable == False:
                    core = to_test
                step = step // 2

            step = 1
            # Step
            to_test = core[:pos] + core[(pos + step) :]
            assert (
                solver._solver.solve(smtassume + to_test, getsol=False) == True
            )
            pos += 1
            if pos >= minsize:
                to_test = core[:pos]
                if (
                    solver._solver.solve(smtassume + to_test, getsol=False)
                    != False
                ):
                    logging.debug(
                        "Core failed: %s %s %s", assume, minsize, calls
                    )
                    return None
                else:
                    logging.debug(
                        "Core found: %s %s %s", assume, minsize, calls
                    )
                    return [
                        solver._conmap[x]
                        for x in to_test
                        if x in solver._conmap
                    ]

    # Final cleanup
    # We need to be prepared for things to disappear as we reduce the core, so 
    # make a copy and iterate through that.
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
                lens.append((lit, len(core)))
            else:
                logging.debug("Failed to remove: %s (%d of %d)", lit, badcount, minsize)
                badcount += 1

                if badcount == minsize:
                    cutcore = core[:minsize]
                    # Check if the core is already minimal first
                    if cutcore != core and (
                        solver._solver.solve(smtassume + cutcore, getsol=False)
                        != False
                    ):
                        logging.debug(
                            "Core failed: %s %s %s %s",
                            assume,
                            minsize,
                            badcount,
                            stepcount,
                        )
                        return None
                    else:
                        logging.info(
                            "Core found by badcount: %s %s %s %s %s",
                            assume,
                            minsize,
                            badcount,
                            stepcount,
                            len(cutcore)
                        )
                        return [
                            solver._conmap[x]
                            for x in cutcore
                            if x in solver._conmap
                        ]

    logging.info(
        "Core for %s : %s to %s, with %s steps, %s bad (minsize %s)",
        assume,
        lens,
        len(core),
        stepcount,
        minsize,
        badcount,
    )
    return [solver._conmap[x] for x in core if x in solver._conmap]


def _parfunc_dotinymus(args):
    (p, distance, badlimit) = args
    return (p, tinyMUS(getChildSolver(), [p.neg()], distance, badlimit))


def getTinyMUSes(solver, puzlits, musdict, *, distance, repeats, badlimit):
    setChildSolver(solver)
    logging.info(
        "Getting tiny MUSes, distance %s, for %s puzlits, %s repeats",
        distance,
        len(puzlits),
        repeats,
    )
    with getPool(CONFIG["cores"]) as pool:
        res = pool.map(
            _parfunc_dotinymus,
            [(p, distance, badlimit) for r in range(repeats) for p in puzlits],
        )
        for (p, mus) in res:
            musdict.update(p, mus)


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
            config=CONFIG,
        ),
    )


# Check an existing dictionary. Reject any invalid MUS and squash any good MUS
def checkMUS(solver, puzlits, oldmus, musdict):
    setChildSolver(solver)
    if len(oldmus) > 0:
        with getPool(CONFIG["cores"]) as pool:
            res = pool.map(
                _parfunc_docheckmus,
                [(p, mus) for p in puzlits if oldmus.contains(p) for mus in oldmus.get(p)],
            )
            for (p, newmus) in res:
                # print("!!! {} :: {}".format(oldmus[p], newmus))
                if newmus is not None:
                    musdict.update(p, newmus)


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
            config=CONFIG,
        ),
    )


# Check which literals are filtered by a particular MUS
def checkWhichLitsAMUSProves(solver, puzlits, mus):
    setChildSolver(solver)
    if len(puzlits) > 0:
        with getPool(CONFIG["cores"]) as pool:
            res = pool.map(_parfunc_dochecklitsmus, [(p, mus) for p in puzlits])
            return list(p for (p, musvalid) in res if musvalid)
    else:
        return []


MUSSizeFound = None
MUSSizeRequired = None

MAX_MUS = 999999999

def _findSmallestMUS_func(tup):
    (p, randstr, minsize, config) = tup

    logging.info("YY %s %s %s %s", MUSSizeFound.value, MUSSizeRequired.value, minsize, p)

    if CONFIG["earlyExit"] and MUSSizeFound.value <= MUSSizeRequired.value:
        logging.info("Early Exit!")
        return (p, None)

    # logging.info("Random str: '%s'", randstr)
    (ret, mus) = (
        p,
        MUS(
            randomFromSeed(randstr),
            getChildSolver(),
            [p.neg()],
            minsize,
            config=config,
        ),
    )
    if mus is not None:
        if len(mus) < MUSSizeFound.value:
            logging.info("Found new best MUS size: %s -> %s", MUSSizeFound.value, len(mus))
            MUSSizeFound.value = len(mus)
    return (ret, mus)



def cascadeMUS(solver, puzlits, repeats, musdict, config):
    # We need this to be accessible by the pool
    setChildSolver(solver)
    global MUSSizeFound, MUSSizeRequired
    if musdict.minimum() < math.inf:
        MUSSizeFound = multiprocessing.Value('l', musdict.minimum())
    else:
        MUSSizeFound = multiprocessing.Value('l', MAX_MUS)
 
    MUSSizeRequired = multiprocessing.Value('l', 111)

    # Have to duplicate code, to swap loops around
    if CONFIG["resetSolverMUS"]:
        for minsize in range(
            config["baseSizeMUS"], max(config["baseSizeMUS"] + 1, 10000), 1
        ):
            logging.info("Looking for %s (know %s)", minsize, MUSSizeFound.value)
            MUSSizeRequired.value = minsize
            if CONFIG["earlyExit"] and MUSSizeFound.value <= minsize:
                logging.info("Early exit because MUS already known")
                return

            with getPool(CONFIG["cores"]) as pool:
                # Do 'range(repeats)' first, so when we distribute we get an
                # even spread of literals on different cores minsize+1 for MUS
                # size, as the MUS will include 'p'
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
                            config,
                        )
                        for r in range(repeats)
                        for p in puzlits
                    ],
                )
                for (p, mus) in res:
                    if mus is not None and len(mus) < minsize:
                        logging.info(
                            "!! Found smaller !!!! {} {}".format(
                                len(mus), minsize
                            )
                        )
                    if mus is not None and len(mus) > minsize:
                        logging.info(
                            "!! Found bigger !!!! {} {}".format(
                                len(mus), minsize
                            )
                        )
                    musdict.update(p, mus)
                if musdict.minimum() <= minsize:
                    return
    else:
        with getPool(CONFIG["cores"]) as pool:
            for minsize in range(
                config["baseSizeMUS"], max(config["baseSizeMUS"] + 1, 10000), 1
            ):
                MUSSizeRequired.value = minsize
                # Do 'range(repeats)' first, so when we distribute we get an 
                # even spread of literals on different cores minsize+1 for MUS 
                # size, as the MUS will include 'p'.
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
                            config,
                        )
                        for r in range(repeats)
                        for p in puzlits
                    ],
                )
                for (p, mus) in res:
                    if mus is not None and len(mus) < minsize:
                        logging.info(
                            "!! Found smaller !!!! {} {}".format(
                                len(mus), minsize
                            )
                        )
                    if mus is not None and len(mus) > minsize:
                        logging.info(
                            "!! Found bigger !!!! {} {}".format(
                                len(mus), minsize
                            )
                        )
                    musdict.update(p, mus)
                if musdict.minimum() <= minsize:
                    return


class CascadeMUSFinder:
    def __init__(self, solver):
        self._solver = solver
        self._bestcache = MusDict({})

    def smallestMUS(self, puzlits):
        musdict = MusDict({})
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

        logging.info("Smallest MUS A: %s ", musdict.minimum())

        # Early exit for trivial case
        if musdict.minimum() <= 1:
            logging.info("Early exit from checkSmall1")
            return musdict

        # Try looking for general tiny MUSes, to prime search
        logging.info("Looking for small")
        getTinyMUSes(
                self._solver,
                puzlits,
                musdict,
                repeats=CONFIG["smallRepeats"],
                distance=999,
                badlimit=CONFIG["baseSizeMUS"]*2
        )

        logging.info("Smallest MUS B: %s ", musdict.minimum())

        # Early exit for trivial case
        if musdict.minimum() <= 1:
            logging.info("Early exit from checkSmall general")
            return musdict

        logging.info("Checking cache")

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
                badlimit=5
            )

        if not CONFIG["checkSmall2"]:
            logging.info("Running cascade algorithm")        
            cascadeMUS(
                self._solver, puzlits, CONFIG["repeats"], musdict, CONFIG
            )
        else:
            logging.info("Early exit: skipping cascade")

        if CONFIG["useCache"]:
            # Only store first element, to stop excessive growth
            self._bestcache = copy.deepcopy(musdict)

        return musdict
