#!/usr/bin/env python3
import copy
import sys
import os
import logging

# Let me import puzsmt from one directory up
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import puzsmt
import puzsmt.base
import puzsmt.internal
import puzsmt.MUS
import puzsmt.prettyprint
import puzsmt.solve
import buildpuz

import puzsmt.config

logging.basicConfig(
    level=logging.INFO, format="%(levelname)s:%(name)s:%(relativeCreated)d:%(message)s"
)


def doSingleStep(delvals, target):
    # Make a matrix of variables (we can make more than one)
    vars = puzsmt.base.VarMatrix(
        lambda t: (t[0] + 1, t[1] + 1), (9, 9), range(1, 9 + 1)
    )

    # Build the puzzle (we can pass multiple matrices, depending on the puzzle)
    puz = puzsmt.base.Puzzle([vars])
    puz.addConstraints(buildpuz.basicSudoku(vars))

    solver = puzsmt.internal.Solver(puz)

    # Now, let's get an actual Sudoku!

    for (var, vals) in delvals:
        for v in vals:
            lit = puzsmt.base.NeqVal(vars[var[0]][var[1]], v)
            solver.addLit(lit)

    # print(solver.solve(getsol=True))
    ((x, y), v) = target

    # The 'puzlits' are all the booleans we have to solve
    # Start by finding the ones which are not part of the known values
    # Horrible hack for v is negative
    if v < 0:
        puzlits = [puzsmt.base.NeqVal(vars[x][y], -v)]
    else:
        puzlits = [puzsmt.base.EqVal(vars[x][y], v)]

    MUS = puzsmt.MUS.CascadeMUSFinder(solver)

    trace = puzsmt.solve.html_solve(sys.stdout, solver, puzlits, MUS)

    print("Minitrace: ", [(s, mins[0], len(mins)) for (s, mins) in trace])

    logging.info("Finished")
    logging.info("Full Trace %s", trace)


for oneclause in [False, True]:
    print("<hr><h1>Setting 'OneClauseAtMost' to", oneclause, "</h1>")
    puzsmt.config.LoadConfigFromDict({"OneClauseAtMost": oneclause})

    print("<hr><h2>Hidden Single</h2>")
    doSingleStep([((0, i), [1]) for i in range(8)], ((0, 8), 1))

    print("<hr><h2>Naked Pair</h2>")

    doSingleStep([((0, i), [j for j in range(1, 8)]) for i in range(2)], ((0, 2), -8))

    print("<hr><h2>Hidden Pair</h2>")

    doSingleStep(
        [((0, i), [j for j in range(1, 3)]) for i in range(2, 9)], ((0, 1), -8)
    )

    print("<hr><h2>Naked Triple</h2>")

    doSingleStep([((0, i), [j for j in range(1, 7)]) for i in range(3)], ((0, 3), -8))

    print("<hr><h2>Hidden Triple</h2>")

    doSingleStep(
        [((0, i), [j for j in range(1, 4)]) for i in range(3, 9)], ((0, 1), -8)
    )

    print("<hr><h2>Naked Quad</h2>")

    doSingleStep([((0, i), [j for j in range(1, 6)]) for i in range(4)], ((0, 4), -8))

    print("<hr><h2>Hidden Quad</h2>")

    doSingleStep(
        [((0, i), [j for j in range(1, 5)]) for i in range(4, 9)], ((0, 1), -8)
    )
