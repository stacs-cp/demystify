import json
import sys
import copy

# This config contains variables whose values we never expect to change,
# they are used in some experiments.
EXPCONFIG = {
    # Reset solver for each size of MUS
    "resetSolverMUS": False,
    # Reset solver for every call (VERY slow)
    "resetSolverFull": False,
    # Dump out SAT instances, for other MUS solvers
    # WHen using this, set cores=0 and repeats=1
    "dumpSAT": False,
    # Change glucose's random seed at each solver reboot (requires chris' patched python-sat)
    "changeSolverSeed": False,
    # TO CHECK: Does this help?
    "setPhases": False,
    # Cache MUSes between steps
    "useCache": True,
    # Use same pool of solvers throughout
    "reusePool": False,
    # Make use of unsat cores when shrinking MUSes
    "useUnsatCores": True,
    # Use 'incremental' mode in solver
    # Todo: Sometimes this makes the solver go super-slow
    "solverIncremental": False,
    # Limit search to searchLimitedBudget conflicts
    "solveLimited": True,
    "solveLimitedBudget": 10000,
    # Which solver to use (g4 = glucose), z3 = Use Z3
    "solver": "g4",

}

CONFIG_FAST = {
    # How many cores to use when running in parallel
    # Set to 1 (or 0) to disable parallelisation
    "cores": 8,
    # How many times to look for very tiny cores
    # Incrasing this past 2 doesn't (seem) to be useful
    "smallRepeats": 1,
    # How many times to try looking for each size of core
    "repeats": 2,

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

CONFIG_MORE_MUS = copy.deepcopy(CONFIG_FAST)

CONFIG_MORE_MUS["earlyExit"] = False
CONFIG_MORE_MUS["cascadeMult"] = 4
CONFIG_MORE_MUS["baseSizeMUS"] = 6
CONFIG_MORE_MUS["repeats"] = 4

def getDefaultConfig():
    global CONFIG_FAST
    return copy.deepcopy(CONFIG_FAST)

def LoadConfigFromDict(dict):
    global CONFIG_FAST
    for (k, v) in dict.items():
        if k not in CONFIG_FAST:
            print("Invalid CONFIG option: " + k)
            sys.exit(1)
        CONFIG_FAST[k] = v


def LoadConfigFromFile(file):
    with open(file) as f:
        data = json.load(f)
        LoadConfigFromDict(data)
