from .utils import flatten, intsqrt, lowsqrt
from .base import EqVal, NeqVal
import logging
import sys
import math
import io
import pprint
import uuid
import json

from .prettyprint import print_explanation

from .MUS import musdict_minimum, checkWhichLitsAMUSProves

# Make a unique id
id_counter = 0

def get_id():
    global id_counter
    id_counter += 1
    return "id{}".format(id_counter)


# Make a div which starts hidden
def hidden(name, content):
    id = get_id()
    s = ""
    s += """<input type='submit' value='{}' onclick="toggle('{}');">""".format(name, id)
    s += "<div id={} style='display:none;'>\n".format(id)
    s += content
    s += "\n</div>\n"
    return s

# Return all the values involved with a single cell of a puzzle grid, c.f print_var
def cell_values(variable, known, involved, involvedset, targets):
    cell = []
    dom = variable.dom()
    
    splitsize = 1
    domsize = len(dom)
    if intsqrt(domsize) is not None:
        splitsize = intsqrt(domsize)
    elif domsize % 2 == 0:
        splitsize = domsize // 2
    else:
        splitsize = lowsqrt(domsize)

    cellRow = 0
    for dsublist in [dom[i : i + splitsize] for i in range(0, len(dom), splitsize)]:
        cell_values = []
        for d in dsublist:
            value = {}
            markers = []

            poslit = EqVal(variable, d)
            neglit = NeqVal(variable, d)
            if neglit in targets:
                markers.append("nit")
            elif poslit in targets:
                markers.append("pit")
            # Put this neglit check here, as we want to skip displaying it we already know it is gone
            elif neglit in known:
                markers.append("nik")
            elif poslit in involvedset:
                markers.append("pii")
            elif neglit in involvedset:
                markers.append("nii")

            if poslit in known:
                markers.append("pik")
            
            for i, clause in enumerate(involved):
                if (poslit in flatten(clause)) or (neglit in flatten(clause)):
                    markers.append(str(i))

            value["markers"] = markers
            value["value"] = d

            if not "nik" in value["markers"]:
                cell_values.append(value)
            

        if len(cell_values) != 0:
            cell.append({"cellValues":cell_values})

        
        
    return {"cellRows": cell}

# Return a single puzzle grid state, c.f. print_matrix
def puzzle_matrix(matrix, known, involved, involvedset, targets):
    output_matrix = []
    matrixRow = 0

    for rowcount, row in enumerate(matrix.varmat()):
        output_matrix.append({"cells": []})
        for cell in row:
            output_matrix[matrixRow]["cells"].append(cell_values(cell, known, involved, involvedset, targets))
        matrixRow+=1

    return {"rows": output_matrix}

# Return all the current puzzle grid states with involved literals marked, c.f. print_explanation
def puzzle_state(solver, mus, targets):
    state = []

    
    vars = solver.puzzle().vars()
    known = solver.getKnownLits()
    involved = [m.clauseset() for m in flatten(mus)]

    for matrix in vars:
        state.append(puzzle_matrix(matrix, set(known), involved, set(flatten(involved)), set(targets)))
    return {"matrices": state}


# Return decision along with a list of justifications
def explain(solver, lits, reason):
    exp = {}
    exp["decision"] = "Setting " + ", ".join(str(l) for l in lits) + " because:"
    exp["reason"] = []
    if len(reason) == 0:
        exp["reason"].append("The basic design of the problem")
    else:
        for i, clause in enumerate(sorted(reason)):
            exp["reason"].append(str(solver.explain(clause)))

    return exp

def list_counter(l):
    d = dict()
    for i in l:
        d[i] = d.get(i, 0) + 1
    return d

def json_step(step_object, solver, p, choices, bestchoice):

    step_object["puzzleState"] = puzzle_state(solver, bestchoice, p)

    step_object["smallestMUSSize"] = len(bestchoice)

    step_object["deductions"] = explain(solver, p, bestchoice)

    step_object["otherMethods"] = []

    if len(choices) > 1:
            other_method = {}

            for c in (c for c in choices if c != bestchoice):
                other_method["puzzleState"] = puzzle_state(solver, c, p)
                other_method["smallestMUSSize"] = len(c)
                other_method["deductions"] = explain(solver, p, c)
            step_object["otherMethods"].append(other_method)

def json_solve(outputfile, outstream, solver, puzlits, MUSFind, steps=math.inf, *, gofast = False, fulltrace=False, forcechoices = None, skip=-1, merge=1, force=None):
    trace = []
    ftrace = []
    total_calls = 0
    step = 1
    forcestep = 0
    output_json = [] # This will be the final JSON output, an array of "step objects"

    # Now, we need to check each one in turn to see which is 'cheapest'
    while len(puzlits) > 0 and step <= steps:
        step_object = {} # One step object for each step, note we don't skip tiny MUSes here.

        step_object["stepNumber"] = step

        logging.info("Starting Step %s", step)
        logging.info("Current state %s", solver.getCurrentDomain())

        begin_stats = solver.get_stats()
        musdict = MUSFind.smallestMUS(puzlits)
        end_stats = solver.get_stats()

        stats_diff = {"solveCount": end_stats["solveCount"] - begin_stats["solveCount"],
                      "solveTime": end_stats["solveTime"] - begin_stats["solveTime"] }
        smallest = musdict_minimum(musdict)
        step_object["solverCalls"] = stats_diff["solveCount"]
        
        total_calls += stats_diff["solveCount"]

        if smallest <= merge: # Still merge simple deductions with a single puzzle state
            step += 1

            lits = [k for k in sorted(musdict.keys()) if len(musdict[k][0]) <= merge]

            step_object["puzzleState"] = puzzle_state(solver, [musdict[l][0] for l in lits], lits)
            step_object["simpleDeductions"] = [explain(solver, [p], musdict[p][0]) for p in sorted(lits)]
            
            for p in lits:
                solver.addLit(p)
                puzlits.remove(p)
        else:
            step += 1

            print(list(str(k) for k in sorted(musdict.keys())), "::", force)

            # Set default value
            basemins = [k for k in sorted(musdict.keys()) if len(musdict[k][0]) == smallest]

            # Consider overriding 'basemins' value with 'force'
            if force is not None:
                inforces = list(f for f in force if len(list(k for k in sorted(musdict.keys()) if str(k) == f)) > 0)
                if len(inforces) > 0:
                    basemins = [k for k in sorted(musdict.keys()) if str(k) == inforces[0]]
                    force.remove(inforces[0])
                    if len(force) == 0:
                        force = None
                    print("force = ", force)

            fullinfo = {lit: list_counter(musdict[lit]) for lit in basemins}
            if fulltrace:
                ftrace.append(fullinfo)

            bestlit = None
            bestmus = None
            bestdeletedlits = None
            bestmusstat = (math.inf, math.inf, math.inf)
            deleteddict = {}
            for b in basemins:
                deleteddict[b] = {}
                for mus in musdict[b]:
                    muslits = set.union(set(),*(set(m.lits()) for m in mus))
                    puzlitsinmus = set(p for p in puzlits if p in muslits or p.neg() in muslits)
                    # Explictly add 'b', for the case where the MUS is size 0 in particular
                    deletedlits = set(checkWhichLitsAMUSProves(solver, puzlitsinmus, mus)).union(set([b]))
                    deleteddict[b][mus] = deletedlits
                    musval = (len(mus), len(puzlitsinmus), -len(deletedlits))
                    if musval < bestmusstat:
                        bestmusstat = musval
                        bestlit = b
                        bestmus = mus
                        bestdeletedlits = deletedlits

            assert not gofast


            choices = tuple(sorted(set(musdict[bestlit])))
            #passkeys = checkWhichLitsAMUSProves(solver, puzlits, choices[0])
            json_step(step_object, solver, bestdeletedlits, choices, bestmus)

            trace.append((bestmusstat, bestmus))

            # Not sure about this bit?
            if not gofast:
                if len(basemins) > 1:
                    others = io.StringIO()
                    for p in (p for p in basemins if p != bestlit):
                        choices = tuple(sorted(set(musdict[p])))
                        json_step(step_object, solver, deleteddict[p][choices[0]], choices, choices[0])
                    
                logging.info("Minimal choices : {} {}".format(len(basemins), basemins))
            
            if forcechoices is None:
                logging.info("Choosing {}".format(bestdeletedlits))
                for k in bestdeletedlits:
                    solver.addLit(k)
                    puzlits.remove(k)

            if forcechoices is not None:
                print("<h3>FORCING CHOICE TO {}</h3>".format(forcechoices[forcestep]), file=outstream)
                solver.addLit(forcechoices[forcestep])
                puzlits.remove(forcechoices[forcestep])
                forcestep += 1

            print(hidden("verbose choices info", "<pre>" + pprint.PrettyPrinter(compact=True).pformat(fullinfo) + "</pre>"), file=outstream)

        output_json.append(step_object)

    logging.info("Total Solver Calls %d", total_calls)
    logging.info("Trace: %s", trace)
    logging.info("Trace Quality: %s", [(i, len(j)) for (i, j) in trace])
    logging.info("Trace Sorted: %s", sorted([(i,len(j)) for (i, j) in trace]))

    f = open("./" + outputfile + ".json", "w")
    f.write(json.dumps(output_json))
    f.close()

    if fulltrace:
        return (trace, ftrace)
    else:
        return trace
    
    