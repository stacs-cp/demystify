#!/usr/bin/env python3
import copy
import sys
import os
import logging
import random

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
    level=logging.INFO, format="%(levelname)s:%(name)s:%(relativeCreated)d:%(message)s"
)

demystify.config.LoadConfigFromDict(
    {"solverIncremental": False, "cores": 12, "repeats": 10}
)

# Make a matrix of variables (we can make more than one)
vars = demystify.base.VarMatrix(lambda t: (t[0] + 1, t[1] + 1), (9, 9), range(1, 9 + 1))

# Build the puzzle (we can pass multiple matrices, depending on the puzzle)
puz = demystify.base.Puzzle([vars])
puz.addConstraints(buildpuz.basicSudoku(vars))

puz.addConstraints(buildpuz.diffByDist(vars, 2, 1))
#puz.addConstraints(buildpuz.knightsMove(vars))


solver = demystify.internal.Solver(puz)

fullsolution = [lit for lit in solver.solve(getsol=True) if lit.equal]

instance = fullsolution[:]


random.shuffle(instance)

print(instance)


if False:
    i = 0
    while i < len(instance):
        newi = instance[:i] + instance[(i+1):] 
        if solver.solveSingle(newi) != "Multiple" and instance[i].val != 2:
            instance = newi
        else:
            i += 1
        print(len(instance), i)
    print(instance)

instance = [i for i in instance if i.val == 1 or i.val == 9]

for i in instance:
    print("sudoku[{}][{}] = {}".format(i.var._location[0], i.var._location[1], i.val))
# Then we 'add' all the assignments that we know (this is what we can undo later with a 'pop')
for s in instance:
    solver.addLit(s)

print(solver.solveSingle([]))

# The 'puzlits' are all the booleans we have to solve
# Start by finding the ones which are not part of the known values
puzlits = [p for p in fullsolution if p not in instance]

MUS = demystify.MUS.CascadeMUSFinder(solver)

trace = demystify.solve.html_solve(sys.stdout, solver, puzlits, MUS)

print("Minitrace: ", [(s, mins[0], len(mins)) for (s, mins) in trace])


logging.info("Finished")
logging.info("Full Trace %s", trace)
