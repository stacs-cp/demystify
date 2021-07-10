import json
import sys
import os
import subprocess
import re
import logging

from sortedcontainers import SortedSet
from pysat.formula import CNF

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import demystify
import demystify.base
import demystify.internal
import demystify.buildpuz


class ParseError(Exception):
    pass


def parse_json(puzzle_json):
    varmap = {}
    varlist = []

    with open(puzzle_json) as json_data:
        d = json.load(json_data)
        for (name, (x, y, dom)) in d["vars"].items():
            v = demystify.base.VarMatrix(
                lambda t: (t[0] + 1, t[1] + 1), (x, y), dom
            )
            varmap[name] = v
            varlist.append(v)

        puz = demystify.base.Puzzle(varlist)

        constraints = []

        for con in d["constraints"]:
            name = con[0]
            if name not in dir(demystify.buildpuz):
                raise ParseError("Invalid constraint: " + name)

            cargs = []
            for a in con[1:]:
                if type(a) is str:
                    a = varmap[a]
                cargs.append(a)

            constraints += getattr(demystify.buildpuz, name)(*cargs)

        puz.addConstraints(constraints)

        solver = demystify.internal.Solver(puz)

        return puz, solver


def parse_essence(eprime, eprimeparam):
    varmap = {}
    varlist = []
    paramjson = subprocess.run(
        ["conjure", "pretty", "--output-format", "json", eprimeparam],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if paramjson.returncode != 0:
        raise ParseError(
            "Conjure pretty-printing of params failed"
            + "\n"
            + paramjson.stdout.decode("utf-8")
            + "\n"
            + paramjson.stderr.decode("utf-8")
        )
    params = json.loads(paramjson.stdout)

    makedimacs = subprocess.run(
        [
            "savilerow",
            "-in-eprime",
            eprime,
            "-in-param",
            eprimeparam,
            "-sat-output-mapping",
            "-sat",
            "-sat-family",
            "lingeling",
            "-S0",
            "-O0",
            "-reduce-domains",
            "-aggregate",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if makedimacs.returncode != 0:
        raise ParseError(
            "savilerow failed"
            + "\n"
            + makedimacs.stdout.decode("utf-8")
            + "\n"
            + makedimacs.stderr.decode("utf-8")
        )

    formula = CNF(from_file=eprimeparam + ".dimacs")

    dvarmatch = re.compile("c Var '(.*)' direct represents '(.*)' with '(.*)'")
    ovarmatch = re.compile("c Var '(.*)' order represents '(.*)' with '(.*)'")

    with open(eprime) as eprime_data:
        vars = SortedSet()
        auxvars = SortedSet()
        cons = dict()
        conmatch = re.compile('\$\#CON (.*) "(.*)"')

        for line in eprime_data:
            if line.find("$#") != -1:

                if line.startswith("$#VAR"):
                    v = line.strip().split(" ")[1]
                    logging.debug("Found VAR: '{}'".format(v))

                    if v in vars or v in auxvars:
                        raise ParseError(f"{v} defined twice")
                    vars.add(v)

                elif line.startswith("$#CON"):
                    logging.debug(line)
                    match = conmatch.match(line)
                    assert match is not None

                    logging.debug(
                        "Found CON: '{}' '{}'".format(match[1], match[2])
                    )

                    if match[1] in cons:
                        raise ParseError(f"{match[1]} defined twice")

                    cons[match[1]] = match[2]

                elif line.startswith("$#AUX"):
                    v = line.strip().split(" ")[1]
                    logging.debug("Found Aux VAR: '{}'".format(v))

                    if v in vars or v in auxvars:
                        raise ParseError

                    auxvars.add(v)

    identifiers = SortedSet.union(vars, cons.keys())

    with open(eprimeparam + ".dimacs") as sat_data:
        varmap = dict()
        ordervarmap = dict()
        for line in sat_data:
            if line.startswith("c Var"):
                dmatch = dvarmatch.match(line)
                omatch = ovarmatch.match(line)
                assert dmatch is not None or omatch is not None
                # At the moment, only care about direct match
                if dmatch is not None:
                    fillmap = varmap
                    match = dmatch
                else:
                    fillmap = ordervarmap
                    match = omatch

                if not match[1].startswith("aux"):

                    var = demystify.utils.parseSavileRowName(
                        identifiers, auxvars, match[1]
                    )

                    if var is not None:
                        if var[0] not in fillmap:
                            fillmap[var[0]] = dict()
                        if var[1] not in fillmap[var[0]]:
                            fillmap[var[0]][var[1]] = dict()
                        fillmap[var[0]][var[1]][int(match[2])] = int(match[3])

        logging.debug(varmap)

    printvarmap = dict()
    litmap = dict()
    invlitmap = dict()
    constraintmap = dict()

    for v in varmap.keys():
        if not (v in vars or v in cons.keys()):
            logging.debug("WARNING: Unknown variable: '{}'".format(v))

    varlits = SortedSet()

    # For each variable / literal, establish maps between the demysify literal
    # and SAT literal.
    for v in SortedSet(varmap.keys()).intersection(vars):
        printvarmap[v] = dict()

        for loc in varmap[v]:
            litsforvar = []
            var = demystify.base.Var(
                f'{v}[{",".join(str(l) for l in loc)}]',
                tuple(varmap[v][loc].keys()),
                loc,
            )

            printvarmap[v][loc] = var
            varlist.append(var)
            for (dom, sat) in varmap[v][loc].items():
                litmap[demystify.base.EqVal(var, dom)] = sat
                invlitmap[sat] = [demystify.base.EqVal(var, dom)]
                if -sat not in invlitmap:
                    invlitmap[-sat] = [demystify.base.NeqVal(var, dom)]
                varlits.add(sat)

                litsforvar.append(demystify.base.EqVal(var, dom))
                litsforvar.append(demystify.base.NeqVal(var, dom))

            # For 'order' variables, just map them to the whole CP variable
            if v in ordervarmap and loc in ordervarmap[v]:
                for (dom, sat) in ordervarmap[v][loc].items():
                    invlitmap[sat] = SortedSet(litsforvar)
                    if -sat not in invlitmap:
                        invlitmap[-sat] = SortedSet(litsforvar)
                    varlits.add(sat)

    for v in SortedSet(varmap.keys()).intersection(SortedSet(cons.keys())):
        # Only want matching '1'
        for k in set(varmap[v].keys()):
            # This should be a boolean -- if this fails, check with Chris
            assert set(varmap[v][k].keys()).issubset(SortedSet([0, 1]))

            # assert 0 in varmap[v][k].keys()
            # -- Removed in place of the error below
            
            if 0 not in varmap[v][k].keys():
                raise ParseError(
                    f"ERROR: Constraint {v}{k} cannot be made false.."
                )
        
            if 1 not in varmap[v][k].keys():
                raise ParseError(
                    f"ERROR: Constraint {v}{k} cannot be satisfied.."
                )

            # Note that 'a' can be accessed in the f string
            a = tuple(k)
            try:
                constraintname = eval('f"' + cons[v] + '"', locals())
            except Exception as e:
                logging.debug("Could not evaluate " + cons[v])
                constraintname = cons[v]

            alreadyparsed = demystify.utils.checkConstraintAlreadyParsed(formula, varmap[v][k][1], constraintname)

            if alreadyparsed:
                formula.append([-varmap[v][k][1]])
            else:
                connected = SortedSet(
                    lit
                    for s in demystify.utils.getConnectedVars(
                        formula, varmap[v][k][1], varlits
                    )
                    for lit in invlitmap[s]
                )

                # Savilerow is too clever, so just put both negative + positive
                # version of all literals in.
                connected = connected.union(
                    SortedSet(lit.neg() for lit in connected)
                )

                assert len(connected) > 0

                # Skip constraints which do not include any variables
                if len(connected) > 0:
                    logging.debug("Adding: " + constraintname)
                    constraintmap[
                        demystify.base.DummyClause(constraintname, connected)
                    ] = varmap[v][k][1]
                else:
                    logging.debug("Skipping: " + constraintname)
                    formula.append([varmap[v][k][1]])

    printvarlist = []

    # Horrible code to fold matrices back into nice python matrices
    for v in printvarmap.keys():
        dim = len(next(iter(printvarmap[v].keys())))

        if dim == 0:
            printvarlist.append(
                demystify.base.VarMatrix(
                    None, (1, 1), (), varmat=[[printvarmap[v].values()[0]]]
                )
            )

        elif dim == 1:
            varlist = list(
                printvarmap[v][k] for k in SortedSet(printvarmap[v].keys())
            )
            printvarlist.append(
                demystify.base.VarMatrix(
                    None, (1, len(varlist)), (), varmat=[varlist]
                )
            )

        elif dim == 2:
            varlist = []
            for index1 in SortedSet(k[0] for k in printvarmap[v].keys()):

                index2 = SortedSet(
                    [k for k in printvarmap[v].keys() if k[0] == index1]
                )

                varlist.append(list(printvarmap[v][k] for k in index2))

            logging.debug(varlist)
            printvarlist.append(
                demystify.base.VarMatrix(
                    None, (len(varlist), len(varlist[0])), (), varmat=varlist
                )
            )
        else:
            assert False

    puz = demystify.base.Puzzle(printvarlist)
    solver = demystify.internal.Solver(
        puz, cnf=formula, litmap=litmap, conmap=constraintmap
    )

    return puz, solver, params
