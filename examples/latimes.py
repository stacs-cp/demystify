#!/usr/bin/env python3
import copy
import sys
import os
import logging
import argparse
import json

# Let me import demystify from one directory up
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import demystify
import demystify.base
import demystify.internal
import demystify.MUS
import demystify.solve
import demystify.prettyprint
import buildpuz


parser = argparse.ArgumentParser()

parser.add_argument("sudoku", help="which latimes sudoku to use", type=int)
parser.add_argument("config", help="solver config", type=str)
args = parser.parse_args()

logging.basicConfig(
    level=logging.INFO, format="%(levelname)s:%(name)s:%(relativeCreated)d:%(message)s"
)

demystify.config.LoadConfigFromDict({"cores": 2, "smallRepeats": 1, "repeats": 50})
demystify.config.LoadConfigFromDict(json.loads(args.config))

# Make a matrix of variables (we can make more than one)
vars = demystify.base.VarMatrix(lambda t: (t[0] + 1, t[1] + 1), (9, 9), range(1, 9 + 1))

# Build the puzzle (we can pass multiple matrices, depending on the puzzle)
puz = demystify.base.Puzzle([vars])
puz.addConstraints(buildpuz.basicSudoku(vars))


solver = demystify.internal.Solver(puz)

#Diaboloical - 21 Aug 2020
gridtypes= [
    [
    "070003060",
    "000102000",
    "005000709",
    "007200001",
    "006010840",
    "800000500",
    "704000900",
    "000708000",
    "090600050"
    ],
    [ # Tough Thu, 20-Aug-2020
    "850020000",
    "020000003",
    "009108000",
    "040080150",
    "090010020",
    "083060070",
    "000605800",
    "200000030",
    "000090047"
    ],
    [ # Moderate Wed 19-Aug-2020
    "040000120",
    "300107000",
    "080000073",
    "200001700",
    "900402001",
    "008900006",
    "820000010",
    "000703008",
    "093000050",
    ],
    [ # Gentle Tue 18-Aug-2020
    "100080009",
    "000000863",
    "000300017",
    "003400200",
    "000825000",
    "005009600",
    "980003000",
    "376000000",
    "200090001"
    ]
]

grid = gridtypes[args.sudoku]

sudoku = [[None] * 9 for _ in range(9)]
for i in range(9):
    for j in range(9):
        if grid[i][j] != '0':
            sudoku[i][j] = int(grid[i][j])

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
