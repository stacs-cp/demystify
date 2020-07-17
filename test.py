import z3
import random

s = z3.Solver()


vars = [z3.Bool(str(i)) for i in range(20)]

# Set up an interesting problem

impls = [z3.Bool("i" + str(i)) for i in range(40)]

for i in range(40):
    s.add(z3.Implies(impls[i], z3.Or(random.choice(vars), z3.Not(random.choice(vars)))))

impls = set(impls)


# Check if there is a single solution, or return 'None'
def solve(self, assumptions = []):
    result = s.check(impls.union(assumptions))
    if result == z3.sat:
        return s.model()
    else:
        return None

# This is the same as 'solve', but checks if there are many solutions,
# returning Solver.Multiple if there is more than one solution
def solveSingle(s, assumptions = []):
    sol = solve(s,assumptions)
    if sol is None:
        return None

    # Save the state of the solver so we can add another constraint
    s.push()
    # At least one variable must take a different variable
    s.add(z3.Or([l != sol[l] for l in vars]))
    newsol = solve(s,assumptions)
    s.pop()
    
    if newsol is None:
        return sol
    else:
        return "Multiple"
