import json
import sys


# WOOO EVERY LOVES GLOBAL VARIABLES!!!


# let's put all our config into one variable because.. then we only have one global?


CONFIG = {
    # How many cores to use when running in parallel
    # Set to 1 (or 0) to disable parallelisation
    "cores": 8,
    # How many times to look for very tiny cores
    # Incrasing this past 2 doesn't (seem) to be useful
    "smallRepeats": 1,
    # How many times to try looking for each size of core
    "repeats": 2,
    # Encode "at most one thing is true" as a single clause
    "OneClauseAtMost": False,
    # Limit search to searchLimitedBudget conflicts
    "solveLimited": True,
    "solveLimitedBudget": 10000,
    # Dump out SAT instances, for other MUS solvers
    # WHen using this, set cores=0 and repeats=1
    "dumpSAT": False,
    # TO CHECK: Does this help?
    "setPhases": False,
    # Cache MUSes between steps
    "useCache": True,
    # Which solver to use (g4 = glucose), z3 = Use Z3
    "solver": "g4",
    # Use 'incremental' mode in solver
    # Todo: Sometimes this makes the solver go super-slow
    "solverIncremental": False,
    # Exit when a MUS of required size has been found
    "earlyExit": True,
    # When "officially" looking for a mus of size k,
    # instead look for cascadeMult*k, because it is not too much
    # more work and we might want it later
    "cascadeMult": 2,
    "checkSmall1": True,
    "checkSmall2": False,
    "checkCloseFirst": False,
    # Smallest size of MUS to look for
    "baseSizeMUS": 4,
    # Make use of unsat cores when shrinking MUSes
    "useUnsatCores": True,
    # Reset solver for each size of MUS
    "resetSolverMUS": False,
    # Reset solver for every call (VERY slow)
    "resetSolverFull": False,
    # Use same pool of solvers throughout
    "reusePool": False,
    # Change glucose's random seed at each solver reboot (requires chris' patched python-sat)
    "changeSolverSeed": False,
    # Alternative, safer, MUS-finding algorithm
    "gallopingMUSes": False,
    # Start by chopping big bits off MUSes, to encourage variety
    "prechopMUSes12": False,
    # Start Gallops with big steps
    "highGallop": False,
    "tryManyChopMUS": True,
    "minPrecheckMUS": False,
    "minPrecheckStepsMUS": False,
}


def LoadConfigFromDict(dict):
    global CONFIG
    for (k, v) in dict.items():
        if k not in CONFIG:
            print("Invalid CONFIG option: " + k)
            sys.exit(1)
        CONFIG[k] = v


def LoadConfigFromFile(file):
    with open(file) as f:
        data = json.load(f)
        LoadConfigFromDict(data)
