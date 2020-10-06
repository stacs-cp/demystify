#!/usr/bin/env python3
import copy
import sys
import os
import logging

# Let me import demystify from one directory up
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import demystify
import demystify.base
import demystify.internal
import demystify.MUS
import demystify.solve
import demystify.prettyprint
import demystify.buildpuz

logging.basicConfig(
    level=logging.INFO, format="%(levelname)s:%(name)s:%(relativeCreated)d:%(message)s"
)

demystify.config.LoadConfigFromDict({"repeats": 5, "solverIncremental": False})

# Make a matrix of variables (we can make more than one)
vars = demystify.base.VarMatrix(lambda t: (t[0] + 1, t[1] + 1), (9, 9), range(1, 9 + 1))

# Build the puzzle (we can pass multiple matrices, depending on the puzzle)
puz = demystify.base.Puzzle([vars])

constraints = []
constraints += demystify.buildpuz.alldiffRowsCols(vars)
constraints += demystify.buildpuz.buildCage(
    "Cage 1",
    [vars[x][y] for (x, y) in [(i, j) for i in range(3) for j in range(3)]],
    vars.domain(),
)
constraints += demystify.buildpuz.buildCage(
    "Cage 2",
    [
        vars[x][y]
        for (x, y) in [
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (0, 7),
            (1, 3),
            (1, 4),
            (1, 5),
            (1, 6),
        ]
    ],
    vars.domain(),
)
puz.addConstraints(constraints)

solver = demystify.internal.Solver(puz)

for (x, y) in [(0, 8), (1, 7), (1, 8)]:
    for d in [1, 2, 3, 4, 5, 6]:
        solver.addLit(demystify.base.NeqVal(vars[x][y], d))


print(solver.solve([], getsol=True))

puzlits = [demystify.base.NeqVal(vars[2][2], 2)]

MUS = demystify.MUS.CascadeMUSFinder(solver)

trace = demystify.solve.html_solve(sys.stdout, solver, puzlits, MUS)

print("Minitrace: ", [(s, mins[0], len(mins)) for (s, mins) in trace])


logging.info("Finished")
logging.info("Full Trace %s", trace)
