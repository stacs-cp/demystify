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

demystify.config.LoadConfigFromDict({"cores": 16, "smallRepeats": 1, "repeats": 100, "solver": "cadical", "solveLimited": False})
demystify.config.LoadConfigFromDict(json.loads(args.config))

# Make a matrix of variables (we can make more than one)
vars = demystify.base.VarMatrix(lambda t: (t[0] + 1, t[1] + 1), (9, 9), range(1, 9 + 1))

# Build the puzzle (we can pass multiple matrices, depending on the puzzle)
puz = demystify.base.Puzzle([vars])
puz.addConstraints(buildpuz.basicSudoku(vars))


solver = demystify.internal.Solver(puz)

gridtypes= [ 
    ([# Diabolical - 4 Sept 2020
    "007010600",
    "000537000",
    "020004010",
    "012000000",
    "800000004",
    "003000250",
    "060700030",
    "000498000",
    "004620900"
    ], []),
    ([# Tough - 3 Sept 2020
    "000000034",
    "007860000",
    "100030008",
    "008009720",
    "000000000",
    "016200900",
    "400090006",
    "000074210",
    "000000000"
    ], []),
    ([# Tough - 30 Aug 2020
    "000567000",
    "080000000",
    "090408501",
    "470000002",
    "009000800",
    "600000039",
    "804302075",
    "000000060",
    "000970000"
    ],[((2,1),1),((2,1),2),((2,3),1),((2,3),2),((4,7),1)] ),
    ([# Diabolical - 28 Aug 2020
    "500009006",
    "300108000",
    "604000020",
    "008900500",
    "050000030",
    "001004900",
    "000000705",
    "000802004",
    "000700003"
    ],[((1,2),2),((1,3),2),((3,4),3)] ),
    ([# Tough - 27 Aug 2020
    "000094060",
    "710502000",
    "000000020",
    "108000352",
    "200000008",
    "945000706",
    "020000000",
    "000705031",
    "070480000"
    ],[((2,3),3)]  ),
    ([# Tough - 23 Aug 2020
    "300700400",
    "080003910",
    "000000000",
    "950070004",
    "400001006",
    "000060023",
    "000000000",
    "020507030",
    "008004009"
    ],[((7,5),1),((7,7),8)] ),
    ([#Diaboloical - 21 Aug 2020
    "070003060",
    "000102000",
    "005000709",
    "007200001",
    "006010840",
    "800000500",
    "704000900",
    "000708000",
    "090600050"
    ],[((8,7),3), ((5,9),3), ((6,2),3), ((6,3),3), ((9,5),3)]  ),
    ([ # Tough Thu, 20-Aug-2020
    "850020000",
    "020000003",
    "009108000",
    "040080150",
    "090010020",
    "083060070",
    "000605800",
    "200000030",
    "000090047"
    ], [((3,5),3)] )
]

tooeasygrids = [
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

(grid, moves) = gridtypes[args.sudoku]

if moves is not None:
    lits = [demystify.base.NeqVal(vars[x-1][y-1], d) for ((x,y),d) in moves]
else:
    lits = None

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

trace = demystify.solve.html_solve(sys.stdout, solver, puzlits, MUS, forcechoices = lits)

print("Minitrace: ", [(s, mins[0], len(mins)) for (s, mins) in trace])


logging.info("Finished")
logging.info("Full Trace %s", trace)
