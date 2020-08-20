import json
import sys
# WOOO EVERY LOVES GLOBAL VARIABLES!!!


# let's put all our config into one variable because.. then we only have one global?


CONFIG = {
    # How many cores to use when running in parallel
    # Set to 1 (or 0) to disable parallelisation
    "cores": 8,

    # How many times to look for very tiny cores
    # Incrasing this past 5 doesn't (seem) to be useful
    "smallRepeats": 5,

    # How many times to try looking for each size of core
    "repeats": 5,

    # Encode "at most one thing is true" as a single clause
    "OneClauseAtMost": False,

    # Limit search to 100,000 conflicts
    "solveLimited": True,
    
    # TO CHECK: Does this help?
    "setPhases": True,

    # Cache MUSes between steps
    "useCache": True,

    # Which solver to use (g4 = glucose)
    "solver": "g4",

    # Use 'incremental' mode in solver
    # Todo: Sometimes this makes the solver go super-slow
    "solverIncremental": False,

    # Exit when MUS is too big
    "earlyExit": True,

    # Exit when MUS might be too big
    "earlyExitAllFailed": False,

    # Exit when MUS might be too big
    "earlyExitMaybe": False,

    # When "officially" looking for a mus of size k,
    # instead look for cascadeMult*k, because it is not too much
    # more work and we might want it later
    "cascadeMult": 1,

    "checkSmall1": True,
    "checkSmall2": True,

    "checkCloseFirst": True,

    # Make use of unsat cores when shrinking MUSes
    "useUnsatCores":True,

    # Reset solver for each size of MUS
    "resetSolverMUS":False,

    # Reset solver for every call (VERY slow)
    "resetSolverFull":False,
}



def LoadConfigFromDict(dict):
    global CONFIG
    for (k,v) in dict.items():
        if k not in CONFIG:
            print("Invalid CONFIG option: " + k)
            sys.exit(1)
        CONFIG[k] = v

def LoadConfigFromFile(file):
    with open(file) as f:
        data = json.load(f)
        LoadConfigFromDict(data)
