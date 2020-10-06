#!/usr/bin/env python3

import sys
import argparse
import random
import copy
import json
import os


# Let me import demystify
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import demystify
import demystify.base
import demystify.internal
import demystify.MUS
import demystify.prettyprint
import demystify.solve
import demystify.buildpuz


parser = argparse.ArgumentParser(description = "Demystify")
parser.add_argument("--puzzle", type=str, help="File containing JSON description of puzzle")

parser.add_argument("--debuginfo", action="store_true", help="Print (lots) of debugging info")

parser.add_argument("--repeats", type=int, default=5, help="Number of times to try generating each MUS")

parser.add_argument("--cores", type=int, default=4, help="Number of CPU cores to use")


args = parser.parse_args()

if args.puzzle is None:
    print("Must give a --puzzle")
    sys.exit(1)

demystify.config.LoadConfigFromDict({"repeats" : args.repeats, "cores": args.cores})

varmap = {}
varlist = []

with open(args.puzzle) as json_data:
    d = json.load(json_data)
    for (name, (x,y,dom)) in d["vars"].items():
        v = demystify.base.VarMatrix(lambda t: (t[0] + 1, t[1] + 1), (x, y), dom)
        varmap[name] = v
        varlist.append(v)

    puz = demystify.base.Puzzle(varlist)

    constraints = []

    for con in d["constraints"]:
        name = con[0]
        if name not in dir(demystify.buildpuz):
            print("Invalid constraint: ", name)
            sys.exit(1)
        
        args = []
        for a in con[1:]:
            if type(a) is str:
                a = varmap[a]
            args.append(a)
        
        constraints += getattr(demystify.buildpuz, name)(*args)

    puz.addConstraints(constraints)

    solver = demystify.internal.Solver(puz)

    model=[]

    if "initial" in d:
        # Replace '0's with 'None' (todo: make this more general)
        for m in d["initial"]:
            for row in m:
                for i in range(len(row)):
                    if row[i] == 0:
                        row[i] = None
    
        model=puz.assignmentToModel(d["initial"])
    
    fullsolution = solver.solveSingle(model)

    for s in model:
        solver.addLit(s)
    

        
    puzlits = [p for p in fullsolution if p not in model]

    MUS = demystify.MUS.CascadeMUSFinder(solver)

    trace = demystify.solve.html_solve(sys.stdout, solver, puzlits, MUS)

    print("Minitrace: ", [(s, mins[0], len(mins)) for (s, mins) in trace])


    logging.info("Finished")
    logging.info("Full Trace %s", trace)

