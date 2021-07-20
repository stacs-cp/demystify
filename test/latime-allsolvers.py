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
import demystify.prettyprint
import demystify.solve
import demystify.config
import demystify.buildpuz
import time

logging.basicConfig(
    level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s"
)

grid = [ # Tough Thu, 20-Aug-2020
    "850020000",
    "020000003",
    "009108000",
    "040080150",
    "090010020",
    "083060070",
    "000605800",
    "200000030",
    "000090047"
    ]

sudoku = [[None] * 9 for _ in range(9)]
for i in range(9):
    for j in range(9):
        if grid[i][j] != '0':
            sudoku[i][j] = int(grid[i][j])

for solvername in ["cd", "g3", "g4", "lgl", "mcb", "mcm", "mpl", "mc", "m22", "mgh"]:
    demystify.config.LoadConfigFromDict(
        {
            "solver": solvername,
            "solverIncremental": False,
            "solveLimited": False,
            "cores": 4, "repeats": 5
        }
    )
    start_time = time.time()
    # Make a matrix of variables (we can make more than one)
    vars = demystify.base.VarMatrix(
        lambda t: (t[0] + 1, t[1] + 1), (9, 9), range(1, 9 + 1)
    )

    # Build the puzzle (we can pass multiple matrices, depending on the puzzle)
    puz = demystify.base.Puzzle([vars])
    puz.addConstraints(demystify.buildpuz.basicSudoku(vars))

    solver = demystify.internal.Solver(puz)

    # First, we turn it into an assignment (remember technically an assignment is a list of variables, so we pass [sudoku])

    sudokumodel = puz.assignmentToModel([sudoku])

    fullsolution = solver.solveSingle(sudokumodel)

    # Then we 'add' all the assignments that we know (this is what we can undo later with a 'pop')
    for s in sudokumodel:
        solver.addLit(s)

    # The 'puzlits' are all the booleans we have to solve
    # Start by finding the ones which are not part of the known values
    puzlits = [p for p in fullsolution if p not in sudokumodel]

    MUS = demystify.MUS.CascadeMUSFinder(solver)

    trace = demystify.solve.html_solve(sys.stdout, solver, puzlits, MUS)

    print("Minitrace: ", [(s, mins[0], len(mins)) for (s, mins) in trace])

    logging.info("Finished")
    logging.info("Full Trace %s", trace)
