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
import buildpuz

logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s:%(name)s:%(relativeCreated)d:%(message)s"
)

demystify.config.LoadConfigFromDict({"repeats": 5, "solver": "z3", "cores": 12})

# Make a matrix of variables (we can make more than one)
vars = demystify.base.VarMatrix(lambda t: (t[0] + 1, t[1] + 1), (9, 9), range(1, 9 + 1))

# Build the puzzle (we can pass multiple matrices, depending on the puzzle)
puz = demystify.base.Puzzle([vars])
puz.addConstraints(buildpuz.basicSudoku(vars))


solver = demystify.internal.Solver(puz)

# Now, let's get an actual Sudoku!

# str = "600120384008459072000006005000264030070080006940003000310000050089700000502000190"
sudokustr = (
    "093004560060003140004608309981345000347286951652070483406002890000400010029800034"
)

l = [int(c) for c in sudokustr]

sudoku = [l[i : i + 9] for i in range(0, len(l), 9)]

print("Going to solve:")
print(sudoku)
# We need to put 'None' in places where we don't want a value (in case we want 0, we could hard-wire 0 = empty)

for i in range(9):
    for j in range(9):
        if sudoku[i][j] == 0:
            sudoku[i][j] = None

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
