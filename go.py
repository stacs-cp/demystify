#!/usr/bin/env python3

import demystify
import demystify.internal
import demystify.buildpuz

import copy
import sys

# Make a matrix of variables (we can make more than one)
vars = demystify.base.VarMatrix(lambda t: (t[0] + 1, t[1] + 1), (9, 9), range(1, 9 + 1))

# Build the puzzle (we can pass multiple matrices, depending on the puzzle)
puz = demystify.base.Puzzle([vars])


puz.addConstraints(demystify.buildpuz.basicSudoku(vars))


solver = demystify.internal.Solver(puz)

model = solver.solve(getsol=True)

print(model)

# Note that a model is mapping of all variables, both those that make the puzzle
# and the constraints. We usually have to do some processing before we can use this.

# We can can get a 'nice assignment'
solutionassignment = puz.modelToAssignment(model)


# We can go 'back to the model'. This gives us a set of SAT variables we have to make true
solutionmodel = puz.assignmentToModel(solutionassignment)

print(solutionassignment, solutionmodel)


print(solver.solveSingle([]))

# Let's try finding a minimal Sudoku
# We start by taking each element of our 'solution' and trying to remove it, and check if the result
# still has a single solution, using 'solveSingle', which returns 'None', solver.Multiple, or the solution (if it is unique)


count = len(solutionmodel)
while count < len(solutionmodel):
    solutioncpy = copy.deepcopy(solutionmodel)
    cpy = solutioncpy[count]
    del solutioncpy[count]
    sol = solver.solveSingle(solutioncpy)
    # This cannot have lead to an unsolvable problem
    assert sol is not None
    if sol == solver.Multiple:
        print("Can't remove " + str(cpy))
        count = count + 1
    else:
        print("Popped " + str(cpy))
        solutionmodel = solutioncpy


print(solutionmodel)
# Print out the model turned back into a solution, using 'partial=true' to allow missing values

print(puz.modelToAssignment(model, partial=True))


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

print(solver.solve(sudokumodel, getsol=True))

# Now, we solve it, and check it has one solution

fullsolution = solver.solveSingle(sudokumodel)
print(fullsolution)
print(sudokumodel)
# The full solution is an extension of sudokumodel to all literals
assert set(sudokumodel).issubset(set(fullsolution))

print(puz.modelToAssignment(fullsolution))

# Start by 'pushing' the state of the solver. This lets us revert later
solver.push()

# Then we 'add' all the assignments that we know (this is what we can undo later with a 'pop')
for s in sudokumodel:
    solver.addLit(s)

# The 'puzlits' are all the booleans we have to solve
# Start by finding the ones which are not part of the known values
puzlits = [p for p in fullsolution if p not in sudokumodel]

# Now, we need to check each one in turn to see which is 'cheapest'
# while len(puzlits) > 0:
for i in range(3):
    musdict = {}
    for p in puzlits:
        mus = puzsat.MUS.MUS(solver, [p.neg()], 50)
        if mus is not None:
            # print(p, ":", len(mus))
            musdict[p] = mus
    smallest = min([len(v) for v in musdict.values()])
    print("Smallest mus size:", smallest)

    if smallest == 1:
        print("Doing some simple deductions: ")
        for p in [k for k in musdict if len(musdict[k]) == 1]:
            print("Setting ", p, " because ", [solver.explain(c) for c in musdict[p]])
            solver.addLit(p)
            puzlits.remove(p)
    else:
        # Find first thing with smallest value
        p = [k for k in musdict if len(musdict[k]) == smallest][0]
        print("Setting ", p, " because ", [solver.explain(c) for c in musdict[p]])
        solver.addLit(p)
        puzlits.remove(p)
