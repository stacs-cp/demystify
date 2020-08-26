#!/usr/bin/env python3
import copy
import sys
import os
import logging
import time

# Let me import demystify from one directory up
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import demystify
import demystify.base
import demystify.internal
import demystify.MUS
import demystify.solve
import demystify.prettyprint
import buildpuz

logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s:%(name)s:%(message)s"
#    level=logging.INFO, format="%(levelname)s:%(name)s:%(relativeCreated)d:%(message)s"
)


import pysolvers

jigsawH = "111223333112223633112225633411525666444555666444585996774588899774788899777788999" # 18, H, Bob & Debbie Scott, krydak@yahoo.com
zigzag =	"111123333114122333144522236144552236447555266487755669487775669888779699888879999"#, // 20 zigzag, Gérard Coteau, coteau41@wanadoo.fr

#assert pysolvers.glucose41_set_argc(["-rnd-init", "-no-gr", "-rnd-freq=1"])

#demystify.config.LoadConfigFromDict({"cores": 12, "smallRepeats": 2, "repeats": 500, "prechopMUSes": True})

def doSingleStep(domains, targets = None, *, sudokutype = None, sudokuarg = None):
    # Make a matrix of variables (we can make more than one)
    vars = demystify.base.VarMatrix(
        lambda t: (t[0] + 1, t[1] + 1), (9, 9), range(1, 9 + 1)
    )

    # Build the puzzle (we can pass multiple matrices, depending on the puzzle)
    puz = demystify.base.Puzzle([vars])
    if sudokuarg is None:
        puz.addConstraints(sudokutype(vars))
    else:
        puz.addConstraints(sudokutype(vars, sudokuarg))

    solver = demystify.internal.Solver(puz)

    # Now, let's get an actual Sudoku!


    baselits = []
    for (i,row) in enumerate(domains):
        for (j,cell) in enumerate(row):
            assert len(cell) > 0
            if len(cell) == 1:
                baselits.append(demystify.base.EqVal(vars[i][j], cell[0]))
            for d in range(1, 9+1):
                if d not in cell:
                    baselits.append(demystify.base.NeqVal(vars[i][j], d))

    for l in baselits:
        solver.addLit(l)

    sol = solver.solve(getsol=True)

    if targets is None:
        targets = [p for p in sol if p not in baselits]
    else:
        targets = [demystify.base.NeqVal(vars[i][j], d) for ((i,j),d) in targets]

    MUS = demystify.MUS.CascadeMUSFinder(solver)

    trace = demystify.solve.html_solve(sys.stdout, solver, targets, MUS, steps=1)

    print("Minitrace: ", [(s, mins[0], len(mins)) for (s, mins) in trace])

    logging.info("Finished")
    logging.info("Full Trace %s", trace)

# https://www.sudokuwiki.org/X_Wing_Strategy
#sudokudoms = [[[1],[3,7,8],[3,7],[2,3,4,7,8],[2,7,8],[2,3,4,7,8],[5],[6],[9]],[[4],[9],[2],[3,7],[5],[6],[1],[3,7],[8]],[[3,7,8],[5],[6],[1],[7,8],[9],[2],[4],[3,7]],[[3,5,7],[3,7],[9],[6],[4],[2,7],[8],[2,5],[1]],[[5,7],[6],[4],[2,7,8,9],[1],[2,7,8],[3,7,9],[2,5],[3,7]],[[2],[1],[8],[7,9],[3],[5],[6],[7,9],[4]],[[3,7,8],[4],[3,7],[5],[2,7,8,9],[2,3,7,8],[3,7,9],[1],[6]],[[9],[3,7,8],[5],[3,7,8],[6],[1],[4],[3,7,8],[2]],[[6],[2],[1],[3,4,7,8],[7,8,9],[3,4,7,8],[3,7,9],[3,7,8,9],[5]]]

if False:
  for solvername in ["cd", "g3", "g4", "lgl", "mcb", "mcm", "mpl", "mc", "m22", "mgh"]:
    demystify.config.LoadConfigFromDict(
    {
        "solver": solvername, "solveLimited": False
    })
    sudokudoms = [[[1],[3,7,8],[3,7],[2,3,4,7,8],[2,7,8],[2,3,4,7,8],[5],[6],[9]],[[4],[9],[2],[3,7],[5],[6],[1],[3,7],[8]],[[3,7,8],[5],[6],[1],[7,8],[9],[2],[4],[3,7]],[[3,5,7],[3,7],[9],[6],[4],[2,7],[8],[2,5],[1]],[[5,7],[6],[4],[2,7,8,9],[1],[2,7,8],[3,7,9],[2,5],[3,7]],[[2],[1],[8],[1,2,3,4,5,7,9],[3],[5],[6],[1,2,3,4,5,7,9],[4]],[[3,7,8],[4],[3,7],[5],[2,7,8,9],[2,3,7,8],[3,7,9],[1],[6]],[[9],[3,7,8],[5],[3,7,8],[6],[1],[4],[3,7,8],[2]],[[6],[2],[1],[3,4,7,8],[7,8,9],[3,4,7,8],[3,7,9],[3,7,8,9],[5]]]
    print("<hr><h2>X_Wing_Strategy 1A {}</h2>".format(solvername))
    doSingleStep(sudokudoms,[((0,3),7)])

    sudokudoms = [[[1],[3,7,8],[3,7],[2,3,4,7,8],[2,7,8],[2,3,4,7,8],[5],[6],[9]],[[4],[9],[2],[3,7],[5],[6],[1],[3,7],[8]],[[3,7,8],[5],[6],[1],[7,8],[9],[2],[4],[3,7]],[[3,5,7],[3,7],[9],[6],[4],[2,7],[8],[2,5],[1]],[[5,7],[6],[4],[2,7,8,9],[1],[2,7,8],[3,7,9],[2,5],[3,7]],[[2],[1],[8],[7,9],[3],[5],[6],[7,9],[4]],[[3,7,8],[4],[3,7],[5],[2,7,8,9],[2,3,7,8],[3,7,9],[1],[6]],[[9],[3,7,8],[5],[3,7,8],[6],[1],[4],[3,7,8],[2]],[[6],[2],[1],[3,4,7,8],[7,8,9],[3,4,7,8],[3,7,9],[3,7,8,9],[5]]]
    print("<hr><h2>X_Wing_Strategy 1B {}</h2>".format(solvername))
    doSingleStep(sudokudoms,[((0,3),7)])

#sys.exit(0)



def dotest(doms, name, pos, *, sudokutype = buildpuz.basicSudoku, sudokuarg = None):
    print("<hr><h2>{}</h2>".format(name))
    doSingleStep(doms, pos, sudokutype = sudokutype, sudokuarg = sudokuarg)

for solver in [
    {"cores": 18, "smallRepeats": 2, "repeats":10},
    {"cores": 18, "smallRepeats": 2, "repeats": 500, "prechopMUSes": True},
    {"cores": 18, "smallRepeats": 2, "repeats": 500, "prechopMUSes": False, "gallopingMUSes": True}
  ]:
    print("<h2>CONFIG: {}</h2>".format(solver))
    demystify.config.LoadConfigFromDict(solver)
    start_time = time.time()

    if False:
        sudokudoms = [[[2,3],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[2,3,5],[2,3,5],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]]]
        dotest(sudokudoms, "Chris Bonus Q (2 AllDiff)", [((0,5),5)])
        
        sudokudoms = [[[2,3],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[2,3,5,6,7],[2,3,5,6,7],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[2,3,5],[2,3,5],[1,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]]]
        dotest(sudokudoms, "Chris Bonus (2 AllDiff)", [((0,5),5)])

        sudokudoms = [[[2,3],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[2,3,5,6,7],[2,3,5,6,7],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[1,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[2,3,5],[4,5,6,7,8,9],[1,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]],[[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9],[1,2,3,4,5,6,7,8,9]]]
        dotest(sudokudoms, "Chris Bonus 2 (2 AllDiff)", [((2,3),5)])

        # X wing
        sudokudoms = [[[1],[3,7,8],[3,7],[2,3,4,7,8],[2,7,8],[2,3,4,7,8],[5],[6],[9]],[[4],[9],[2],[3,7],[5],[6],[1],[3,7],[8]],[[3,7,8],[5],[6],[1],[7,8],[9],[2],[4],[3,7]],[[3,5,7],[3,7],[9],[6],[4],[2,7],[8],[2,5],[1]],[[5,7],[6],[4],[2,7,8,9],[1],[2,7,8],[3,7,9],[2,5],[3,7]],[[2],[1],[8],[1,2,3,4,5,7,9],[3],[5],[6],[1,2,3,4,5,7,9],[4]],[[3,7,8],[4],[3,7],[5],[2,7,8,9],[2,3,7,8],[3,7,9],[1],[6]],[[9],[3,7,8],[5],[3,7,8],[6],[1],[4],[3,7,8],[2]],[[6],[2],[1],[3,4,7,8],[7,8,9],[3,4,7,8],[3,7,9],[3,7,8,9],[5]]]
        dotest(sudokudoms, "X_Wing_Strategy 1A", [((0,3),7)])


        sudokudoms = [[[1],[3,7,8],[3,7],[2,3,4,7,8],[2,7,8],[2,3,4,7,8],[5],[6],[9]],[[4],[9],[2],[3,7],[5],[6],[1],[3,7],[8]],[[3,7,8],[5],[6],[1],[7,8],[9],[2],[4],[3,7]],[[3,5,7],[3,7],[9],[6],[4],[2,7],[8],[2,5],[1]],[[5,7],[6],[4],[2,7,8,9],[1],[2,7,8],[3,7,9],[2,5],[3,7]],[[2],[1],[8],[7,9],[3],[5],[6],[7,9],[4]],[[3,7,8],[4],[3,7],[5],[2,7,8,9],[2,3,7,8],[3,7,9],[1],[6]],[[9],[3,7,8],[5],[3,7,8],[6],[1],[4],[3,7,8],[2]],[[6],[2],[1],[3,4,7,8],[7,8,9],[3,4,7,8],[3,7,9],[3,7,8,9],[5]]]
        dotest(sudokudoms, "X_Wing_Strategy 1B", [((0,3),7)])

        sudokudoms = [[[1,3,5,8],[2,3,5],[1,2,3,5,8],[3,5,6,8],[6,7,8],[3,5,6,7,8],[6,7],[9],[4]],[[7],[6],[4,8],[9],[1],[4,8],[2,3],[5],[2,3]],[[3,4,5],[9],[3,4,5],[3,4,5,6],[4,6,7],[2],[6,7],[8],[1]],[[3,4,6],[7],[2,3,4,6,9],[2,4,6,8],[5],[4,6,8],[2,3,4,8,9],[1],[2,3,8,9]],[[1,3,4,5,6],[2,3,5],[1,2,3,4,5,6],[7],[2,4,6,8],[9],[2,3,4,5,8],[2,3],[2,3,8]],[[4,5],[8],[2,4,5,9],[2,4],[3],[1],[2,4,5,9],[6],[7]],[[2],[4],[3,5,6,8],[1],[6,8],[3,5,6,8],[3,8,9],[7],[3,6,8,9]],[[3,6,8],[1],[3,6,7,8],[2,3,6,8],[9],[3,6,7,8],[2,3,8],[4],[5]],[[9],[3,5],[3,5,6,7,8],[2,3,4,5,6,8],[2,4,6,7,8],[3,4,5,6,7,8],[1],[2,3],[2,3,6,8]]]
        dotest(sudokudoms, "X_Wing_Strategy 2",[((4,2),2)])


        sudokudoms = [[[1,3,5,8],[2],[1,3,5,8],[3,5,6,8],[6,7,8],[3,5,6,7,8],[6,7],[9],[4]],[[7],[6],[4,8],[9],[1],[4,8],[2,3],[5],[2,3]],[[3,4,5],[9],[3,4,5],[3,4,5,6],[4,6,7],[2],[6,7],[8],[1]],[[3,4,6],[7],[2,9],[2,4,6,8],[5],[4,6,8],[2,3,4,8,9],[1],[2,3,8,9]],[[1,3,4,5,6],[3,5],[1,3,4,5,6],[7],[2,4,6,8],[9],[3,4,5,8],[2,3],[3,8]],[[4,5],[8],[2,9],[2,4],[3],[1],[2,4,5,9],[6],[7]],[[2],[4],[3,5,6,8],[1],[6,8],[3,5,6,8],[3,8,9],[7],[3,6,8,9]],[[3,6,8],[1],[3,6,7,8],[2,3,6,8],[9],[3,6,7,8],[2,3,8],[4],[5]],[[9],[3,5],[3,5,6,7,8],[3,4,5,6,8],[2,4,6,7,8],[3,4,5,6,7,8],[1],[2,3],[3,6,8]]]
        dotest(sudokudoms, "X_Wing_Strategy 3",[((4,0),3)])

        # Simple colouring
        sudokudoms = [[[1,4,5],[1,5],[7],[2,5],[8],[3],[6],[1,4,9],[1,2,4,9]],[[1,4,5],[3],[9],[7],[2,5],[6],[8],[1,4],[1,2,4]],[[8],[2],[6],[4],[1],[9],[7],[5],[3]],[[6],[4],[2,5],[1],[9],[2,5],[3],[8],[7]],[[1,5,9],[8],[1,2,5],[3],[6],[7],[2,4,5],[1,4,9],[1,4,5,9]],[[1,9],[7],[3],[2,5],[4],[8],[2,5],[6],[1,9]],[[3],[9],[1,5],[8],[7],[1,4],[4,5],[2],[6]],[[7],[6],[4],[9],[2,5],[2,5],[1],[3],[8]],[[2],[1,5],[8],[6],[3],[1,4],[9],[7],[4,5]]]
        dotest(sudokudoms, "Simple Colouring (single chains) - Twice in a unit (Pre)",[((4,2),5)])


        sudokudoms = [[[2],[3,5,7,9],[3,5,7,8],[3,7,8],[4],[1],[7,8,9],[3,5],[6]],[[4],[3,5,7,9],[3,5,7,8],[6],[3,5,7,8],[2],[7,8,9],[1],[3,7,8]],[[7,8],[1],[6],[3,7,8],[9],[3,5,7],[2,7,8],[2,3,5],[4]],[[3],[5,7],[5,7,8],[1],[2],[9],[6],[4],[7,8]],[[1],[4],[2],[3,7,8],[6],[3,7],[5],[9],[3,7,8]],[[7,8],[6],[9],[5],[3,7,8],[4],[2,7,8],[2,3],[1]],[[5],[8],[4],[2],[1],[6],[3],[7],[9]],[[9],[2],[3,7],[4],[3,7],[8],[1],[6],[5]],[[6],[3,7],[1],[9],[3,5,7],[3,5,7],[4],[8],[2]]]
        dotest(sudokudoms, "Simple Colouring (single chains) - Two colours 'elsewhere'",[((1,4),3)])

        # NOTE: We will typically get a size 5 MUS here, as we only need to see one path
        # Can find (3,4) is not 8, (2,3) it not 8
        sudokudoms = [[[2],[3,5,7,9],[3,5,7,8],[3,7,8],[4],[1],[7,8,9],[3,5],[6]],[[4],[3,5,7,9],[3,5,7,8],[6],[5,7,8],[2],[7,8,9],[1],[3,7]],[[7,8],[1],[6],[3,7,8],[9],[3,5,7],[2,7,8],[2,3,5],[4]],[[3],[5,7],[5,7,8],[1],[2],[9],[6],[4],[7,8]],[[1],[4],[2],[3,7,8],[6],[3,7],[5],[9],[3,7,8]],[[7,8],[6],[9],[5],[3,7,8],[4],[2,7],[2,3],[1]],[[5],[8],[4],[2],[1],[6],[3],[7],[9]],[[9],[2],[3,7],[4],[3,7],[8],[1],[6],[5]],[[6],[3,7],[1],[9],[3,5,7],[3,5,7],[4],[8],[2]]]
        dotest(sudokudoms, "Simple Colouring (single chains) - Two colours 'elsewhere' - 2",[((2,3),8)])


        # Y-Wing
        # Somtimes we find a different reasoning of size 7
        sudokudoms = [[[9],[3,8],[1,3,6,8],[2],[4],[1,3,7,8],[5,7],[5,8],[5,6,8]],[[4,7,8],[5],[4,8],[6],[9],[7,8],[2],[3],[1]],[[1,3,6,7,8],[2],[1,3,6,8],[1,8],[5],[1,3,7,8],[4,7],[9],[4,6,8]],[[1,4,6,8],[9],[1,4,5,6,8],[7],[1,6],[4,8],[3],[2],[4,5,8]],[[1,4,8],[4,8],[2],[9],[3],[5],[6],[1,4,8],[7]],[[1,3,4,6,8],[7],[1,3,4,5,6,8],[4,8],[1,6],[2],[9],[1,4,5,8],[4,5,8]],[[4,8],[6],[9],[1,4,5],[2],[1,4],[1,4,5,8],[7],[3]],[[5],[1],[3,4,8],[3,4],[7],[9],[4,8],[6],[2]],[[2],[3,4],[7],[1,3,4,5],[8],[6],[1,4,5],[4,5],[9]]]
        dotest(sudokudoms, "Y-Wing 1",[((7,2),4)])

        # 2 values to remove - getting something else without a name, and possibly equal complexity
        sudokudoms = [[[9],[3,8],[1,3,6,8],[2],[4],[1,3,7,8],[5,7],[5,8],[5,6,8]],[[4,7,8],[5],[4,8],[6],[9],[7,8],[2],[3],[1]],[[1,3,6,7,8],[2],[1,3,6,8],[1,8],[5],[1,3,7,8],[4,7],[9],[4,6,8]],[[1,4,6,8],[9],[1,4,5,6,8],[7],[1,6],[4,8],[3],[2],[4,5,8]],[[1,4,8],[4,8],[2],[9],[3],[5],[6],[1,4,8],[7]],[[1,3,4,6,8],[7],[1,3,4,5,6,8],[4,8],[1,6],[2],[9],[1,4,5,8],[4,5,8]],[[4,8],[6],[9],[1,4,5],[2],[1,4],[1,4,5,8],[7],[3]],[[5],[1],[3,8],[3,4],[7],[9],[4,8],[6],[2]],[[2],[3,4],[7],[1,3,4,5],[8],[6],[1,4,5],[4,5],[9]]]
        dotest(sudokudoms, "Y-Wing 2",[((6,5),4)]) # ((6,5),4)

        # There is a third y-wing on the page, but it does not occur in the solution, as the solver has been updated

        # MUS size 10: Swordfish (3 columns or 3 8s)
        sudokudoms = [[[5],[2],[9],[4],[1],[6,8],[7],[6,8],[3]],[[4,7,8],[1,4,8],[6],[5,9],[7,8,9],[3],[1,8],[1,4,5,8,9],[2]],[[4,7,8],[1,4,8],[3],[2],[7,8,9],[5,6],[1,8,9],[5,6],[1,4,8,9]],[[4,8],[5],[2],[3],[8,9],[1,4,8],[1,8,9],[7],[6]],[[6],[3],[7],[1,9],[5],[1,4,8],[2],[1,4,8,9],[1,4,8,9]],[[1],[9],[4,8],[6],[2],[7],[5],[3],[4,8]],[[3],[7,8],[1,5,8],[1,5],[6],[9],[4],[2],[1,7,8]],[[2],[4,7],[1,4,5],[8],[3],[1,5],[6],[1,9],[1,7,9]],[[9],[6],[1,8],[7],[4],[2],[3],[1,8],[5]]]
        dotest(sudokudoms, "Swordfish 1",[((1,1),8)]) 

        # For 7,7 we find a much simpler reasoning
        #Setting (7, 7) is not 9 because:
        #
        #    Some cell in column 5 must be 9 (Choices are: (3, 5), (7, 5))
        #    Some cell in column 8 must be 9 (Choices are: (3, 8), (9, 8))
        #    (3, 5) and (3, 8) cannot both be 9 as they are both in row 3
        #    (7, 5) and (7, 7) cannot both be 9 as they are both in row 7
        #    (7, 7) and (9, 8) cannot both be 9 as they are both the cage starting at top-left position (6,6)
        sudokudoms = [[[9],[2],[6],[3,4,5,8],[4,8],[3,5,7,8],[1],[5,7],[5,7,8]],[[5],[3],[7],[6,8,9],[1],[6,8,9],[4],[2],[8,9]],[[8],[4],[1],[2,5,9],[5,9],[2,5,7,9],[6],[5,7,9],[3]],[[2],[5],[9],[7],[3],[4],[8],[1],[6]],[[7],[1],[4],[5,8,9],[6],[5,8,9],[2,5,9],[3],[2,5,9]],[[3],[6],[8],[1],[2],[5,9],[5,7,9],[4],[5,7,9]],[[1],[7,9],[2],[3,6],[5,9],[3,6],[5,7,9],[8],[4]],[[4],[8],[5],[2,9],[7],[1],[3],[6],[2,9]],[[6],[7,9],[3],[2,4,5,8,9],[4,8],[2,5,8,9],[2,5,7,9],[5,7,9],[1]]]
        dotest(sudokudoms, "Swordfish 2",[((6,6),9)]) 

        sudokudoms = [[[1,5,7],[2],[1,5,7,8],[1,7],[4],[3],[1,5,7,8],[6],[9]],[[1,4,5,7],[1,4,5],[3],[8],[9],[6],[2],[4,5],[1,4,5,7]],[[9],[6],[1,4,7,8],[1,7],[2],[5],[1,4,7,8],[3],[1,4,7,8]],[[8],[9],[2,4,7],[5],[6],[2,7],[4,7],[1],[3]],[[6],[1,4,5],[1,2,4,5,7],[2,4,9],[3],[2,7,9],[4,5,7,8,9],[4,5,8],[4,5,7,8]],[[4,5,7],[3],[4,5,7],[4,9],[8],[1],[4,5,7,9],[2],[6]],[[3],[4,5,8],[4,5,6],[2,9],[1],[2,9],[4,5,6,8],[7],[4,5,8]],[[1,5],[1,5,8],[9],[6],[7],[4],[3],[5,8],[2]],[[2],[7],[4,6],[3],[5],[8],[1,4,6],[9],[1,4]]]
        dotest(sudokudoms, "Swordfish 3",[((1,8),4)]) 
    
        sudokudoms = [[[3,8],[9],[2],[4,6],[4,8],[1],[7],[5],[3,4,6]],[[5],[1,3,4],[1,4,6,7],[2],[4,7],[6,7,9],[3,4,6],[1,9],[8]],[[1,4,6],[1,4,8],[1,4,6,7],[4,5,6,9],[3],[5,6,7,8,9],[2],[1,9],[4,6]],[[3,8],[7],[5],[1,3],[1,2,8],[4],[9],[6],[1,2]],[[2],[3,8],[1,4],[1,3,9],[6],[8,9],[1,4,8],[7],[5]],[[1,4],[6],[9],[7],[1,2,5],[2,5,8],[1,4,8],[3],[1,2,4]],[[1,4,6],[1,4,5],[8],[1,4,5,6],[9],[5,6,7],[1,3,5,6],[2],[1,3,6,7]],[[7],[1,2,4,5],[1,4,6],[1,4,5,6],[1,2,4,5],[3],[1,5,6],[8],[9]],[[9],[1,2,5],[3],[8],[1,2,5,7],[2,5,6,7],[1,5,6],[4],[1,6,7]]]
        dotest(sudokudoms, "XYZ Wing 1",[((5,6),1)]) 


        sudokudoms = [[[6],[7,9],[1,3,4,7,9],[5,7],[2,3,4,5,7],[2,3,4],[1,2,5],[1,4,5],[8]],[[5],[1,3],[1,3,4],[9],[2,3,4,6],[8],[1,2,4,6],[1,4,6],[7]],[[8],[2],[4,7],[5,6,7],[4,5,6,7],[1],[4,5,6,9],[3],[6,9]],[[3],[4],[5,6,7],[2],[1,5],[9],[6,7],[8],[1,6]],[[2],[7,9],[5,6,7,9],[1,5],[8],[4,6],[3],[4,6,7],[1,6,9]],[[1],[8],[6,9],[3],[4,6],[7],[4,6,9],[2],[5]],[[7],[5],[1,3,8],[4],[1,3,6],[3,6],[1,6,8],[9],[2]],[[9],[1,3,6],[1,2,3,8],[1,6,7,8],[1,2,3,6,7],[5],[1,6,7,8],[1,6,7],[4]],[[4],[1,6],[1,2,8],[1,6,7,8],[9],[2,6],[1,5,6,7,8],[1,5,6,7],[3]]]
        dotest(sudokudoms, "XYZ Wing 2",[((4,8),6)]) 


        # MUS size 5
        sudokudoms = [[[5,9],[2],[4],[1],[3,5],[5,8],[6],[7],[3,8,9]],[[5,9],[6],[3,8],[2,3,8],[7],[2,5,8],[4],[1],[3,8,9]],[[7],[1,8],[1,3,8],[9],[6],[4],[5,8],[2],[3,5,8]],[[2],[4],[6],[5],[9],[1],[3],[8],[7]],[[1],[3],[5],[4],[8],[7],[2],[9],[6]],[[8],[7],[9],[6],[2],[3],[1],[5],[4]],[[4],[1,8],[1,2,8],[3,8],[3,5],[9],[7],[6],[2,5,8]],[[3],[5],[2,8],[7],[1],[6],[9],[4],[2,8]],[[6],[9],[7],[2,8],[4],[2,5,8],[5,8],[3],[1]]]
        dotest(sudokudoms, "X-Cycle (part 1)",[((2,2),8)]) 

        # MUS size 6
        sudokudoms = [[[8],[1,9],[4],[5],[3],[7],[1,6,9],[1,2,6],[1,2]],[[7,9],[2],[3],[6],[1],[4],[7,9],[8],[5]],[[6],[1,7],[5],[9],[8],[2],[1,7],[3],[4]],[[3,4,9],[3,4,6],[2,6,9],[1],[4,6,9],[5],[8],[7],[2,9]],[[5],[4,9],[1,2],[7],[4,9],[8],[3],[1,2],[6]],[[1,7,9],[8],[1,6,7,9],[2],[6,9],[3],[4],[5],[1,9]],[[2],[4,6,7],[1,6,7],[8],[5],[9],[1,6],[1,4,6],[3]],[[4,9],[5],[6,9],[3],[7],[1],[2],[4,6,9],[8]],[[1,3,9],[3,9],[8],[4],[2],[6],[5],[1,9],[7]]]
        dotest(sudokudoms, "X-Cycle (part 2) - fig 1",[((8,0),9)]) 

        # MUS size 6
        sudokudoms = [[[9],[2],[4],[3,7],[8],[5],[6],[3,7],[1]],[[1,5,6,7],[5,6,7],[3,5,6,7],[4],[1,3,6,7,9],[3,6,7],[2],[8],[3,9]],[[1,6,7,8],[6,7,8],[3,6,7,8],[3,6,7,9],[1,2,3,6,7,9],[2,3,6,7],[3,4,7,9],[5],[3,4,9]],[[3],[6,7,8,9],[1],[2],[6,7],[4],[7,8],[7,9],[5]],[[2,6,7,8],[4,9],[6,7,8],[3,6,7,8],[5],[1],[3,7,8],[4,9],[2,8]],[[2,5,7,8],[4,5,7,8],[5,7,8],[3,7,8],[3,7],[9],[1],[2,3,4,7],[6]],[[4,5,7],[3],[5,7],[5,6,7,9],[2,6,7,9],[2,6,7],[4,8,9],[1],[2,8]],[[4,5,7],[1],[2],[3,5,7,9],[3,7,9],[8],[3,4,9],[6],[3,4,9]],[[6,8],[6,8],[9],[1],[4],[2,3],[5],[2,3],[7]]]
        dotest(sudokudoms, "X-Cycle (part 2) - fig 2",[((4,6),7)]) 

        # MUS size 5
        sudokudoms = [[[1,5],[7],[6],[2],[3,5],[8,9],[4],[5,8,9],[1,3,8,9]],[[5,8],[9],[4],[1],[3,5],[7],[2,3,8],[6],[2,3,8]],[[2],[1,3],[3,5,8],[4],[6],[8,9],[1,8,9],[5,8,9],[7]],[[5,8,9],[6],[2,5,8],[3],[7],[1],[2,5,8,9],[2,4,8,9],[2,4,8,9]],[[7],[4],[3,8],[5],[9],[2],[3,8],[1],[6]],[[1,5,9],[1,2,3],[1,2,3,5],[6],[8],[4],[2,3,5,9],[7],[2,3,9]],[[3],[1,2],[9],[7],[1,2,4],[6],[1,2,8],[2,4,8],[5]],[[6],[8],[1,2],[9],[1,2,4],[5],[7],[3],[1,2,4]],[[4],[5],[7],[8],[1,2],[3],[6],[2,9],[1,2,9]]]
        dotest(sudokudoms, "X-Cycle (part 2) - fig 3",[((1,6),8)])

        sudokudoms = [[[2,3,5,7,8],[1],[4],[2,3,6,8],[2,3,5,8],[2,3,5,6],[3,6,7],[9],[2,3]],[[2,3,5,6,7,8,9],[2,5,7,9],[2,3,5,7,8,9],[2,3,6,8,9],[1],[4],[3,6,7],[2,7],[5,8]],[[2,3,5,6,8,9],[2,5,9],[2,3,5,8,9],[7],[2,3,5,8,9],[2,3,5,6,9],[1],[4],[5,8]],[[1],[6],[2,7],[2,3],[2,3,7],[8],[4],[5],[9]],[[5,7,9],[8],[5,7,9],[1],[4],[7,9],[2],[3],[6]],[[4],[3],[2,9],[5],[6],[2,9],[8],[1],[7]],[[2,3,5,7,8,9],[2,5,7,9],[6],[2,3,8,9],[2,3,5,7,8,9],[1],[3,7,9],[2,7],[4]],[[2,3,7,8,9],[2,7,9],[1],[4],[2,3,7,8,9],[2,3,7,9],[5],[6],[2,3]],[[2,3,7,9],[4],[2,3,5,7,9],[2,3,6,9],[2,3,5,7,9],[2,3,5,6,7,9],[3,7,9],[8],[1]]]
        dotest(sudokudoms, "XSudoku - Pointing Pair",[((8,0),2)], sudokutype = buildpuz.basicXSudoku)

        sudokudoms = [[[1,3,4,8,9],[1,2,4],[2,3,4,8,9],[2,3,4,7,8,9],[6],[1,2,3,4,7,8],[2,7,8],[5],[2,4,7,8]],[[1,3,4,8],[1,2,4],[5],[2,3,4,7,8],[2,3,7,8],[1,2,3,4,7,8],[6],[9],[2,4,7,8]],[[6],[7],[2,4,8,9],[2,4,5,8,9],[2,8,9],[2,4,5,8],[2,8],[1],[3]],[[1,3,4,9],[8],[2,3,4,9],[2,3,6,7],[5],[2,3,6,7],[1,2,3,9],[2,4,6],[2,6,9]],[[3,4,5],[2,4,6],[7],[1],[2,3,8],[9],[2,3,5,8],[2,4,6,8],[2,5,6,8]],[[1,3,5,9],[1,2,6],[2,3,9],[2,3,6,8],[4],[2,3,6,8],[1,2,3,5,8,9],[7],[2,5,6,8,9]],[[2],[9],[1],[4,5,6,7,8],[7,8],[4,5,6,7,8],[5,7,8],[3],[5,6,7,8]],[[7,8],[5],[6],[2,3,7,8,9],[2,3,7,8,9],[2,3,7,8],[4],[2,8],[1]],[[4,7,8],[3],[4,8],[2,5,6,7,8],[1],[2,5,6,7,8],[2,5,7,8,9],[2,6,8],[2,5,6,7,8,9]]]
        dotest(sudokudoms, "XSudoku - Pointing Pair 2",[((0,1),1)], sudokutype = buildpuz.basicXSudoku)

        sudokudoms = [[[3],[8],[5,9],[2],[5,7,9],[6],[4,7],[1],[4,7,9]],[[1,7,9],[7,9],[1,5,6,9],[3,5,8,9],[1,3,5,7,8,9],[4],[3,7],[6,7,9],[2]],[[2],[1,6,7,9],[4],[3,9],[1,3,7,9],[1,3,7,9],[5],[3,6,7,9],[8]],[[1,4,7,8,9],[1,7,9],[2],[5,8,9],[1,3,4,5,7,8,9],[1,7,9],[6],[3,7,8],[1,3,5,7]],[[1,7,8,9],[5],[1,6,9],[3,6,8,9],[2],[1,3,7,8,9],[3,7,8],[4],[1,3,7]],[[1,4,7,8],[1,6,7],[3],[4,6],[1,4,5,6,7,8],[5,7,8],[9],[2],[1,5,7]],[[5],[2],[8],[3,4,6,9],[3,4,6,9],[3,9],[1],[3,7,9],[3,4,7,9]],[[6],[3],[7],[1],[4,5,8,9],[2,5,8,9],[2,4,8],[8,9],[4,9]],[[1,9],[4],[1,9],[7],[3,8],[2,3,8],[2,3,8],[5],[6]]]
        dotest(sudokudoms, "XSudoku - Pointing Pair 3", [((3,0),1)], sudokutype = buildpuz.basicXSudoku)

        sudokudoms = [[[1,4,5,7,9],[1,4,5,7,8,9],[6],[1,3,4,7],[1,3,7,8,9],[7,9],[2],[4,5,7,9],[5,7,9]],[[4,7,9],[3],[2],[5],[6,7,9],[1],[4,6,9],[8],[6,7,9]],[[1,2,4,5,7,9],[1,2,4,5,7,8,9],[1,7,9],[1,4,6,7],[1,6,7,8,9],[2,5,6,7],[4,6,9],[4,5,6,7,9],[3]],[[1,2,5,6,7],[2,4,5,7],[5,7],[9],[6,7],[2,3,5,6,7],[3,4,6],[1,2,3,6,7],[8]],[[2,4,6,7,9],[2,4,6,7,9],[8],[1,2,3,6,7],[1,2,3,6,7],[2,3,6,7],[5],[2,3,6,7,9],[2,6,7,9]],[[1,2,5,6,7,9],[1,2,5,6,7,9],[1,3,5,7,9],[8],[2,3,5,6,9],[4],[3,6,9],[2,3,5,6,7,9],[1,2,6,7,9]],[[8],[2,5,6,7,9],[3,5,7,9],[2,3,6,7],[4],[2,3,6,9],[1],[2,3,5,6,7,9],[2,5,6,7,9]],[[1,2,3,5,6,9],[1,2,5,6,9],[3,5,9],[1,2,6],[2,3,5,6,9],[8],[7],[1,2,3,5,6,9],[4]],[[1,2,3,5,6,7,9],[1,2,5,6,7,9],[4],[1,2,6,7],[2,3,5,6,9],[2,3,6,9],[8],[1,2,3,5,6,7,9],[1,2,5,6,7,9]]]
        dotest(sudokudoms, "Jigsaw - double pointing pair 1", [((8,0),2)], sudokutype = buildpuz.buildJigsaw, sudokuarg = jigsawH)

        sudokudoms = [[[1,4,5,7,9],[1,4,5,7,8,9],[6],[1,3,4,7],[1,3,7,8,9],[7,9],[2],[4,5,7,9],[5,7,9]],[[4,7,9],[3],[2],[5],[6,7,9],[1],[4,6,9],[8],[6,7,9]],[[1,2,4,5,7,9],[1,2,4,5,7,8,9],[1,7,9],[1,4,6,7],[1,6,7,8,9],[2,5,6,7],[4,6,9],[4,5,6,7,9],[3]],[[1,2,5,6,7],[2,4,5,7],[5,7],[9],[6,7],[2,3,5,6,7],[3,4,6],[1,2,3,6,7],[8]],[[2,4,6,7,9],[2,4,6,7,9],[8],[1,3,6,7],[1,2,3,6,7],[2,3,6,7],[5],[2,3,6,7,9],[2,6,7,9]],[[1,2,5,6,7,9],[1,2,5,6,7,9],[1,3,5,7,9],[8],[2,3,5,6,9],[4],[3,6,9],[2,3,5,6,7,9],[1,2,6,7,9]],[[8],[5,6,7,9],[3,5,7,9],[3,6,7],[4],[2,3,6,9],[1],[2,3,5,6,7,9],[2,5,6,7,9]],[[1,3,5,6,9],[1,5,6,9],[3,5,9],[1,2,6],[2,3,5,6,9],[8],[7],[1,2,3,5,6,9],[4]],[[1,3,5,6,7,9],[1,5,6,7,9],[4],[1,2,6,7],[2,3,5,6,9],[2,3,6,9],[8],[1,2,3,5,6,7,9],[1,2,5,6,7,9]]]
        dotest(sudokudoms, "Jigsaw - double pointing pair 2", [((0,0),4)], sudokutype = buildpuz.buildJigsaw, sudokuarg = jigsawH)
    
        sudokudoms = [[[2],[1],[4],[8],[3,5,9],[3,5],[6],[3,9],[7]],[[3,7,9],[3,6],[2,5],[3,6,7],[1,2,3,5,8,9],[1,2,3,8,9],[1,3,5,8],[4],[1,3,5,8]],[[5],[7],[3],[4],[1,6,8,9],[1,6,8,9],[1,8],[1,8,9],[2]],[[3,9],[5,6,9],[5,6],[1,3,5],[1,3,5,8,9],[4],[7],[2],[1,3,5,8]],[[4],[2,5,9],[5,7,8],[1,3,5,7],[1,2,3,7,8,9],[1,2,3,5,8,9],[1,2,3,5,8],[1,3,7,8],[6]],[[1,8],[3,4,5,8],[9],[2],[1,3,5,6,7,8],[1,3,5,6,8],[1,3,5,8],[1,3,7,8],[1,3,4,8]],[[1,8],[2,3,5,8],[5,6,7,8],[1,3,5,6,7],[1,3,5,6,7],[1,2,3,5,8],[4],[1,3,7,8],[9]],[[3,7],[2,3,4,5,8],[2,5,7],[1,3,5],[1,3,4,5],[1,2,3,8],[9],[6],[1,3,4,8]],[[6],[2,3,4,8],[1],[9],[3,4],[7],[2,3,8],[5],[3,4,8]]]
        dotest(sudokudoms, "Jigsaw - double pointing pair 3", [((4,4),2)], sudokutype = buildpuz.buildJigsaw, sudokuarg = zigzag)
    
        # MUS size 7 smaller than the example
        sudokudoms = [[[2,6],[8],[2,4,5],[1],[2,9],[3],[5,9],[7],[4,5,6]],[[3,7],[9],[2,4],[5],[2,7],[6],[1,8],[1,4],[3,4,8]],[[3,7],[5,6],[1],[4],[7,9],[8],[3,5,9],[2],[3,5,6]],[[5],[7],[8],[2],[4],[1],[6],[3],[9]],[[1],[4],[3],[6],[5],[9],[7],[8],[2]],[[9],[2],[6],[8],[3],[7],[4],[5],[1]],[[6,8],[3],[7],[9],[1,6],[5],[2],[1,4],[4,8]],[[2,6,8],[5,6],[2,5],[3],[1,6],[4],[1,8],[9],[7]],[[4],[1],[9],[7],[8],[2],[3,5],[6],[3,5]]]
        dotest(sudokudoms, "XY-Chains example 1 (detected as WXYZ-Wing)", [((0,2),5)])

        # MUS size 9
        sudokudoms = [[[4,8],[9],[2],[1,4,5],[1,8],[1,5,8],[3],[7],[6]],[[4,7,8],[1],[6,8],[2,4,6,7,9],[3],[2,6,8,9],[5],[2,8],[2,4,8]],[[3],[5,6,7],[5,6,8],[2,4,6,7],[2,6,7,8],[2,6,8],[1],[9],[2,4,8]],[[9],[3],[4,6],[8],[5],[2,6],[7],[2,4],[1]],[[7,8],[5,6,7],[1,5,6,8],[3],[1,2,6],[4],[6,8,9],[2,5,8],[2,8,9]],[[2],[5,6],[1,4,5,6,8],[1,6],[9],[7],[6,8],[4,5,8],[3]],[[6],[8],[9],[2,5,7],[2,7],[3],[4],[1],[5,7]],[[5],[2],[3],[1,7,9],[4],[1,8,9],[8,9],[6],[7,8,9]],[[1],[4],[7],[5,6,9],[6,8],[5,6,8,9],[2],[3],[5,8,9]]]
        dotest(sudokudoms, "XY-Chains example 2", [((1,0),8)])
    
        # MUS size 9, last run over complicates the deduction
        sudokudoms = [[[4,8],[9],[2],[1,4,5],[1,8],[1,5,8],[3],[7],[6]],[[4,7],[1],[6,8],[2,4,6,7,9],[3],[2,6,9],[5],[2,8],[2,4]],[[3],[5,6,7],[5,6,8],[2,4,6,7],[2,6,7,8],[2,6,8],[1],[9],[2,4,8]],[[9],[3],[4,6],[8],[5],[2,6],[7],[2,4],[1]],[[7,8],[5,6,7],[1,5,6,8],[3],[1,2,6],[4],[6,8,9],[2,5],[2,8,9]],[[2],[5,6],[1,4,5,6,8],[1,6],[9],[7],[6,8],[4,5,8],[3]],[[6],[8],[9],[2,5,7],[2,7],[3],[4],[1],[5,7]],[[5],[2],[3],[1,7,9],[4],[1,8,9],[8,9],[6],[7,8,9]],[[1],[4],[7],[5,6,9],[6,8],[5,6,8,9],[2],[3],[5,8,9]]]
        dotest(sudokudoms, "Same cells - different XY-Chain", [((2,2),6)])

        #MUS size 11, subset of cells
        sudokudoms = [[[1,7],[9],[3],[8],[2],[4],[5],[6],[1,7]],[[1,4,7],[8],[5],[6],[3,9],[1,3],[4,9],[1,3,7],[2]],[[2],[1,4],[6],[1,3,9],[7],[5],[4,9],[1,3],[8]],[[3],[2],[1],[7],[6],[9],[8],[4],[5]],[[4,6,9],[4,6],[4,9],[2],[5],[8],[3],[1,7],[1,7]],[[5],[7],[8],[1,3],[4],[1,3],[2],[9],[6]],[[8],[5],[4,9],[4,9],[1],[6],[7],[2],[3]],[[1,4,9],[1,3,4],[7],[3,4,9],[8],[2],[6],[5],[4,9]],[[6,9],[3,4,6],[2],[5],[3,9],[7],[1],[8],[4,9]]]
        dotest(sudokudoms, "3D Medusa Rule 1", [((2,1),4)])

        # MUS size 11, subset of cells
        sudokudoms = [[[3],[1,6,8],[1,6,7,9],[1,8,9],[5],[2],[4,6],[4,7,9],[7,8,9]],[[2],[5],[6,7,9],[3],[4,8,9],[4,9],[6,7],[1],[7,8,9]],[[1,9],[1,8],[4],[6],[1,8,9],[7],[5],[2],[3]],[[1,6],[9],[3],[2],[4,6,7],[1,4],[8],[4,7],[5]],[[5],[7],[1,2,6],[8,9],[6,8,9],[1,4,9],[1,2,4,9],[3],[1,9]],[[4],[1,2],[8],[7,9],[3],[5],[1,7,9],[6],[1,2,7]],[[1,6,7,9],[1,2,6],[5],[4],[1,7,9],[8],[3],[7,9],[1,2,7,9]],[[1,7,9],[3],[1,2,9],[5],[1,7,9],[6],[1,2,7,9],[8],[4]],[[8],[4],[1,9],[1,7,9],[2],[3],[1,7,9],[5],[6]]]
        dotest(sudokudoms, "3D Medusa Rule 2", [((1,2),6)])

        # MUS size 7, subset of cells
        sudokudoms = [[[1],[7,9],[2,9],[2,7,8],[5],[6],[4,7,8],[4,8,9],[3]],[[2,5,6],[4],[3],[1,2,7,8],[9],[7,8],[1,5,7,8],[5,6,8],[6,8]],[[8],[6,7,9],[5,6,9],[1,7],[4],[3],[1,5,7],[5,6,9],[2]],[[4,7],[3],[4,8],[5],[6],[7,8,9],[2],[1],[4,9]],[[9],[5],[6,8],[4],[2],[1],[6,8],[3],[7]],[[4,6,7],[2],[1],[7,8],[3],[7,8,9],[4,5,6,8],[4,5,6,8],[4,6,9]],[[3],[1],[7],[9],[8],[2,4],[4,6],[2,4,6],[5]],[[2,4,5,6],[6,8],[2,4,5],[3],[1],[2,4,5],[9],[7],[4,8]],[[2,4,5],[8,9],[2,4,5,9],[6],[7],[2,4,5],[3],[2,4,8],[1]]]
        dotest(sudokudoms, "3D Medusa Rule 4 1", [((1,0),6)])

        # MUS size 11, subset of cells
        sudokudoms = [[[1],[7,9],[2,9],[2,7,8],[5],[6],[4,7,8],[4,8,9],[3]],[[2,5],[4],[3],[1,2,7,8],[9],[7,8],[1,5,7,8],[5,6,8],[6,8]],[[8],[6,7,9],[5,6,9],[1,7],[4],[3],[1,5,7],[5,9],[2]],[[4,7],[3],[4,8],[5],[6],[7,8,9],[2],[1],[4,9]],[[9],[5],[6,8],[4],[2],[1],[6,8],[3],[7]],[[4,6,7],[2],[1],[7,8],[3],[7,8,9],[4,5,6,8],[4,5,6,8],[4,6,9]],[[3],[1],[7],[9],[8],[2,4],[4,6],[2,4,6],[5]],[[2,4,5,6],[6,8],[2,4,5],[3],[1],[2,4,5],[9],[7],[4,8]],[[2,4,5],[8,9],[2,4,5,9],[6],[7],[2,4,5],[3],[2,4,8],[1]]]
        dotest(sudokudoms, "3D Medusa Rule 4 2", [((1,5),8)])

        # MUS size 7, subset of cells
        sudokudoms = [[[9],[2],[3],[4],[6,8],[7],[6,8],[1],[5]],[[8],[7],[6],[1,3],[5],[1,3],[9],[2],[4]],[[5],[1,4],[1,4],[2],[6,8,9],[6,9],[6,7,8],[3],[7,8]],[[7],[6],[9],[3,5,8],[2],[3,5],[1],[4],[3,8]],[[4],[3],[2],[1,6,8],[1,6,7],[1,6],[7,8],[5],[9]],[[1],[8],[5],[3,9],[7,9],[4],[2],[6],[3,7]],[[3,6],[9],[8],[5,6],[4],[2],[3,5],[7],[1]],[[2],[1,5],[7],[1,5,9],[3],[1,5,9],[4],[8],[6]],[[3,6],[1,4,5],[1,4],[7],[1,6],[8],[3,5],[9],[2]]]
        dotest(sudokudoms, "3D Medusa Rule 5", [((2,4),8)])

        # MUS size 7, subset of cells
        sudokudoms = [[[9],[8],[6],[7],[2],[1],[3],[4],[5]],[[3],[1,2],[4],[9],[5],[6],[1,8],[1,2,8],[7]],[[2,5],[1,2,5],[7],[4,8],[3],[4,8],[9],[6],[1,2]],[[2,4,8],[7],[3],[2,4,8],[6],[5],[1,4,8],[1,8],[9]],[[6],[9],[2,8],[2,4,8],[1],[7],[4,5,8],[5,8],[3]],[[1],[4,5],[5,8],[3],[9],[4,8],[2],[7],[6]],[[2,4,5,8],[2,4,5],[2,5,8],[6],[7],[9],[1,5],[3],[1,2,8]],[[2,5,8],[6],[9],[1],[4],[3],[7],[2,5],[2,8]],[[7],[3],[1],[5],[8],[2],[6],[9],[4]]]
        dotest(sudokudoms, "3D Medusa Rule 6 1", [((1,1),2)])

        # MUS size 9, some cells are different
        sudokudoms = [[[9],[3,5],[8],[1,3],[2],[1,3,4],[4,5],[7],[6]],[[6],[2,5],[2,4],[3,8,9],[3,5,9],[7],[1],[4,8],[3,8,9]],[[1],[7],[3,4],[3,6,8,9],[4,5,6,9],[4,6,9],[5,9],[2],[3,8,9]],[[7,8],[2,8],[5],[4],[3,6],[3,6],[2,7],[9],[1]],[[3],[9],[1],[7],[8],[2],[4,6],[4,6],[5]],[[4],[6],[2,7],[1,9],[1,9],[5],[8],[3],[2,7]],[[7,8],[4],[3,7],[1,2,3,6],[1,3,6],[1,3,6,8],[6,9],[5],[2,9]],[[5],[3,8],[6],[2,3,9],[3,4,9],[4,9],[2,7],[1],[7,8]],[[2],[1],[9],[5],[7],[6,8],[3],[6,8],[4]]]
        dotest(sudokudoms, "3D Medusa Rule 6 2, using 3 candidates in a cell", [((0,1),3)])

        # MUS size 11, subset of cells 
        sudokudoms = [[[5,6,7],[2,6,7],[2,6],[9],[1,6],[8],[4],[3],[1,5]],[[5,9],[3,5,9],[4],[7],[1,3],[2],[6],[8],[1,5]],[[3,6],[8],[1],[3,6],[5],[4],[7,9],[7,9],[2]],[[7,8],[4,7],[5],[6,8],[4,6],[3],[1],[2],[9]],[[1,6,9],[4,6,9],[6,9],[5],[2],[1,7],[3],[4,7],[8]],[[1,2],[2,3],[3,8],[4,8],[9],[1,7],[5],[6],[4,7]],[[2,5,6],[5,6],[3,6],[2,4],[7],[9],[8],[1],[3,4]],[[3,8],[1],[7],[2,3],[4,8],[5],[2,9],[4,9],[6]],[[4],[2,9],[2,8,9],[1],[3,8],[6],[2,7],[5],[3,7]]]
        dotest(sudokudoms, "3D Medusa 37 Eliminations by Rule 1", [((0,0),5)])
    
        # MUS size 10, subset of cells
        sudokudoms = [[[2,4,9],[4,6,9],[1],[7],[5],[3],[8],[2,4,6,9],[2,6,9]],[[2,3,4,8,9],[5],[2,3,4,8,9],[1,2],[1,4],[2,4,6],[2,3,6],[2,4,6,9],[7]],[[7],[3,4,6],[2,3,4],[8],[9],[2,4,6],[1],[2,4,5,6],[2,3,5,6]],[[3,4,8,9],[3,4,8,9],[3,4,8,9],[6],[2,3],[1],[5],[7],[2,8]],[[6],[2],[5],[4],[7],[8],[9],[3],[1]],[[3,8],[1],[7],[9],[2,3],[5],[4],[2,6,8],[2,6,8]],[[1,2,3,5,8,9],[3,8,9],[2,3,8,9],[1,2,5],[6],[7],[2,3],[2,5,8,9],[4]],[[2,3,4,5,8,9],[7],[2,3,4,8,9],[2,5],[4,8],[2,4],[2,3,6],[1],[2,3,5,6,8,9]],[[1,2,4,5,8],[4,8],[6],[3],[1,4,8],[9],[7],[2,5,8],[2,5,8]]]
        dotest(sudokudoms, "Example Jellyfish", [((1,7),2)])

        # MUS size 8, a lot smaller than what they have
        sudokudoms = [[[2,3,4,5,6,8],[2,3,6,8],[3,6,8],[4,6,7,8,9],[1,7,8],[4,6,8,9],[1,7,8],[5,8],[4,5,7,8]],[[4,5,6,8],[7],[6,8],[4,6,8],[3],[1,4,6,8],[9],[2],[1,4,5,8]],[[4,8],[1],[9],[4,7,8],[2],[5],[6],[3],[4,7,8]],[[3,6,8,9],[3,6,8],[4],[5,6,7,8],[5,7,8],[3,6,8],[2],[1],[3,5,7,8,9]],[[2,3,6,8,9],[2,3,6,8],[1,3,6,8],[2,4,5,6,8],[1,5,7,8],[2,3,4,6,8],[7,8],[5,8],[3,5,7,8,9]],[[1,2,3,8],[5],[7],[2,8],[9],[1,2,3,8],[4],[6],[3,8]],[[6,8],[9],[5],[1],[4],[2,8],[3],[7],[2,6]],[[7],[3,6,8],[1,3,6,8],[2,5,8,9],[5,8],[2,8,9],[1,8],[4],[2,6]],[[1,8],[4],[2],[3],[6],[7],[5],[9],[1,8]]]
        dotest(sudokudoms, "18 elimination Jellyfish", [((0,0),8)])

        # MUS size 11, not the perfect jellyfish and smaller
        sudokudoms = [[[1,2,3],[5],[1,2,3],[7],[4],[9],[1,2,6],[8],[1,2,6]],[[1,2,4],[8],[9],[5,6],[2,5,6],[3],[4,7],[2,5,7],[1,2,4,5]],[[6],[2,7],[2,4,7],[5,8],[2,5,8],[1],[3],[9],[2,4,5]],[[2,3,8,9],[4],[2,3,5,8],[1,3,5,8,9],[3,5,8,9],[7],[1,2,5],[6],[1,2,3,5]],[[1,2,3,7],[2,3,7],[1,2,3,5,6,7],[4],[3,5,6],[2,6],[8],[2,5,7],[9]],[[2,3,7,8,9],[2,3,7,9],[2,3,5,6,7,8],[1,3,5,6,8,9],[3,5,6,8,9],[2,6,8],[4,7],[2,5,7],[1,2,3,4,5]],[[2,7,8,9],[6],[2,7,8],[3,8,9],[3,7,8,9],[4],[2,5,9],[1],[2,5,8]],[[5],[3,9],[3,8],[2],[1],[6,8],[6,9],[4],[7]],[[2,4,7,8,9],[1],[2,4,7,8],[6,8,9],[6,7,8,9],[5],[2,6,9],[3],[2,6,8]]]
        dotest(sudokudoms, "Perfect Jellyfish", [((1,0),2)])

        # MUS size 10, not fully jellyfish, and smaller 
        sudokudoms = [[[2,4,5,6,8,9],[2,5,9],[6,9],[1,3,4,5,6,7,8,9],[3,6,8,9],[4,5,6,7,8,9],[1,9],[1,5,6,7,9],[7,9]],[[4,5,6,9],[1],[7],[4,5,6,9],[2],[4,5,6,9],[8],[5,6,9],[3]],[[5,6,8,9],[5,6,9],[3],[1,5,6,7,8,9],[6,8,9],[5,6,7,8,9],[2],[1,5,6,7,9],[4]],[[1,9],[8],[4],[2,9],[5],[3],[7],[1,2,9],[6]],[[1,3,5,6],[5,6],[1,6,9],[2,4,6,7,8,9],[6,8,9],[2,4,6,7,8,9],[1,3,4,9],[1,2,3,4,8,9],[8,9]],[[3,6,9],[7],[2],[4,6,8,9],[1],[4,6,8,9],[3,4,9],[3,4,8,9],[5]],[[6,9],[4],[8],[3,6,9],[7],[1],[5],[3,9],[2]],[[2,7,9],[3],[5],[2,8,9],[4],[2,8,9],[6],[7,8,9],[1]],[[1,2,6,7,9],[2,6,9],[1,6,9],[2,3,5,6,8,9],[3,6,8,9],[2,5,6,8,9],[3,4,9],[3,4,7,8,9],[7,8,9]]]
        dotest(sudokudoms, "Jellyfish, 20 eliminations", [((0,0),9)])

    sudokudoms = [[[1],[4,7,8],[3,4,5,7,8],[3,5,6,7],[3,6,8,9],[5,6,7,8],[3,4,8,9],[3,6,9],[2]],[[2,3,8],[9],[3,7,8],[4],[1,2,3,6,8],[1,2,6,7,8],[1,3,8],[5],[3,6,8]],[[2,3,4,5,8],[2,4,8],[6],[1,2,3,5],[1,2,3,8,9],[1,2,5,8],[7],[1,3,9],[3,4,8,9]],[[2,4,6,8],[5],[1,4,7,8],[9],[1,2,4,6],[3],[1,2,8],[1,2,6,7],[6,7,8]],[[2,3,4,6,8,9],[1,2,4,6,8],[1,3,4,8,9],[1,2,6],[7],[1,2,4,6],[1,2,3,5,8,9],[1,2,3,6,9],[3,5,6,8,9]],[[2,3,6,9],[1,2,6,7],[1,3,7,9],[8],[5],[1,2,6],[1,2,3,9],[4],[3,6,7,9]],[[7],[1,4,8],[1,4,5,8,9],[1,2,3,5],[1,2,3,4,8],[1,2,4,5,8],[6],[2,3,9],[3,4,5,9]],[[4,5,6],[3],[1,4,5],[1,2,5,6,7],[1,2,4,6],[9],[2,4,5],[8],[4,5,7]],[[4,5,6,8,9],[4,6,8],[2],[3,5,6,7],[3,4,6,8],[4,5,6,7,8],[3,4,5,9],[3,7,9],[1]]]
    dotest(sudokudoms, "SK Loop, Easter Monster", [((0,3),7)])

    print("<h2>CONFIG: {} TIME: {}</h2>".format(solver, time.time() - start_time))


# Law of Leftovers examples never trigger 'Law of Leftovers'
# 3D Medusa Rule 3 is not triggered by example
# 3D Medusa, in the extra puzzle for rule 5, it is never triggered