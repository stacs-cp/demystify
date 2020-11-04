#!/usr/bin/env python3

import sys
import argparse
import random
import copy
import json
import os
import re
import logging
import subprocess

from pysat.formula import CNF

# Let me import demystify
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import demystify
import demystify.base
import demystify.internal
import demystify.MUS
import demystify.prettyprint
import demystify.solve
import demystify.buildpuz
import demystify.utils


parser = argparse.ArgumentParser(description = "Demystify")
parser.add_argument("--puzzle", type=str, help="File containing JSON description of puzzle")

parser.add_argument("--eprimeparam", type=str, help="savilerow param file")
parser.add_argument("--eprime", type=str, help="savilerow eprime file")

parser.add_argument("--debuginfo", action="store_true", help="Print (lots) of debugging info")

parser.add_argument("--repeats", type=int, default=5, help="Number of times to try generating each MUS")

parser.add_argument("--cores", type=int, default=4, help="Number of CPU cores to use")

parser.add_argument("--skip", type=int, default=-1,help="Skip displaying MUSes of <= this size")

args = parser.parse_args()

if args.puzzle is None and args.eprime is None:
    print("Must give a --puzzle or --eprime")
    sys.exit(1)

if args.puzzle is not None and args.eprime is not None:
    print("Can only give one of --puzzle or --eprime")
    sys.exit(1)

if args.eprime is not None and args.eprimeparam is None:
    print("--eprime requires --eprimeparam")
    sys.exit(1)

if args.debuginfo:
    logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s:%(name)s:%(relativeCreated)d:%(message)s"
)
demystify.config.LoadConfigFromDict({"repeats" : args.repeats, "cores": args.cores})

varmap = {}
varlist = []

if args.puzzle is not None:
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
            
            cargs = []
            for a in con[1:]:
                if type(a) is str:
                    a = varmap[a]
                cargs.append(a)
            
            constraints += getattr(demystify.buildpuz, name)(*cargs)

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

else:
    paramjson = subprocess.run(["conjure", "pretty", "--output-format", "json", args.eprimeparam], capture_output=True)
    if paramjson.returncode != 0:
        print("Conjure pretty-printing of params failed")
        print(paramjson.stdout)
        print(paramjson.stderr)
    params = json.loads(paramjson.stdout)

    makedimacs = subprocess.run(["savilerow", "-in-eprime", args.eprime, "-in-param", args.eprimeparam, "-sat-output-mapping", "-sat", "-sat-family","lingeling","-S0","-O0","-reduce-domains","-aggregate"])
    if makedimacs.returncode != 0:
        print("savile row failed")
        print(makedimacs.stdout)
        print(makedimacs.stderr)
        sys.exit(1)

    formula = CNF(from_file=args.eprimeparam+".dimacs")
    dvarmatch = re.compile("c Var '(.*)' direct represents '(.*)' with '(.*)'")
    ovarmatch = re.compile("c Var '(.*)' order represents '(.*)' with '(.*)'")

    with open(args.eprime) as eprime_data:
        vars = set()
        cons = dict()
        conmatch = re.compile('\$\#CON (.*) "(.*)"')
        for line in eprime_data:
            if line.find("$#") != -1:
                if line.startswith("$#VAR"):
                    v = line.strip().split(" ")[1]
                    print("Found VAR: '{}'".format(v))
                    if v in vars:
                        #print(f"{v} defined twice")
                        sys.exit(1)
                    vars.add(v)
                elif line.startswith("$#CON"):
                    logging.debug(line)
                    match = conmatch.match(line)
                    assert match is not None
                    print("Found CON: '{}' '{}'".format(match[1],match[2]))
                    if match[1] in cons:
                        #print(f"{match[1]} defined twice")
                        sys.exit(1)
                    cons[match[1]] = match[2]

    identifiers = set.union(vars, cons.keys())

    with open(args.eprimeparam+".dimacs") as sat_data:
        varmap = dict()
        for line in sat_data:
            if line.startswith("c Var"):
                dmatch = dvarmatch.match(line)
                omatch = ovarmatch.match(line)
                assert dmatch is not None or omatch is not None
                # At the moment, only care about direct match
                if dmatch is not None:
                    if not dmatch[1].startswith("aux"):
                        var = demystify.utils.parseSavileRowName(identifiers, dmatch[1])
                        if var is not None:
                            if var[0] not in varmap:
                                varmap[var[0]] = dict()
                            if var[1] not in varmap[var[0]]:
                                varmap[var[0]][var[1]] = dict()
                            varmap[var[0]][var[1]][int(dmatch[2])] = int(dmatch[3])
        logging.debug(varmap)

    printvarmap = dict()
    litmap = dict()
    invlitmap = dict()
    constraintmap = dict()

    for v in varmap.keys():
        if not(v in vars or v in cons.keys()):
            print("WARNING: Unknown variable: '{}'".format(v))


    varlits = set()

    for v in set(varmap.keys()).intersection(vars):
            printvarmap[v] = dict()
            for loc in varmap[v]:
                var = demystify.base.Var(f'{v}[{",".join(str(l) for l in loc)}]', tuple(varmap[v][loc].keys()), loc)
                printvarmap[v][loc] = var
                varlist.append(var)
                for (dom, sat) in varmap[v][loc].items():
                    litmap[demystify.base.EqVal(var, dom)] = sat
                    invlitmap[sat] = demystify.base.EqVal(var,dom)
                    if -sat not in invlitmap:
                        invlitmap[-sat] = demystify.base.NeqVal(var, dom)
                    varlits.add(sat)


    for v in set(varmap.keys()).intersection(set(cons.keys())):
        # Only want matching '1'
        for k in varmap[v].keys():
            # This should be a boolean -- if this fails, check with Chris
            assert set(varmap[v][k].keys()).issubset(set([0,1]))
            assert 0 in varmap[v][k].keys()
            if 1 not in varmap[v][k].keys():
                print(f"ERROR: Constraint {v}{k} cannot be satisfied..")
                sys.exit(1)

            # Note that 'a' can be accessed in the f string
            a = tuple(k)
            constraintname = eval('f"' + cons[v] + '"', locals())
            logging.debug(constraintname)
            connected = [invlitmap[s] for s in demystify.utils.getConnectedVars(formula.clauses, varmap[v][k][1], varlits)]
            constraintmap[demystify.base.DummyClause(constraintname, connected)] = varmap[v][k][1]

    printvarlist = []
    # Horrible code to fold matrices back into nice python matrices
    for v in printvarmap.keys():
        dim = len(next(iter(printvarmap[v].keys())))
        if dim==0:
            printvarlist.append(demystify.base.VarMatrix(None, (1,1), (), varmat = [[printvarmap[v].values()[0]]]))
        elif dim==1:
            varlist = list(printvarmap[v][k] for k in sorted(set(printvarmap[v].keys())))
            printvarlist.append(demystify.base.VarMatrix(None, (1,len(varlist)), (), varmat = [varlist]))
        elif dim == 2:
            varlist = []
            for index1 in sorted(set(k[0] for k in printvarmap[v].keys())):
                index2 = sorted(set([k for k in printvarmap[v].keys() if k[0]==index1]))
                varlist.append(list(printvarmap[v][k] for k in index2))
            logging.debug(varlist)
            printvarlist.append(demystify.base.VarMatrix(None, (len(varlist), len(varlist[0])), (), varmat = varlist))
        else:
            assert False

    puz = demystify.base.Puzzle(printvarlist)
    solver = demystify.internal.Solver(puz, cnf=formula, litmap=litmap, conmap=constraintmap)

    logging.debug(solver.solve(getsol=True))
    print(solver.solve(getsol=True))
    fullsolution = solver.solveSingle([])
    logging.debug(fullsolution)
    puzlits = fullsolution


if fullsolution is None:
    print("Your problem has no solution!")
    sys.exit(1)

if fullsolution == "Multiple":
    print("Your problem has multiple solutions!")
    sys.exit(1)



MUS = demystify.MUS.CascadeMUSFinder(solver)

trace = demystify.solve.html_solve(sys.stdout, solver, puzlits, MUS, skip=args.skip)

print("Minitrace: ", [(s, mins[0], len(mins)) for (s, mins) in trace])


logging.info("Finished")
logging.info("Full Trace %s", trace)

