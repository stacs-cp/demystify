import z3


class Z3Solver:
    def __init__(self):
        self._solver = z3.Solver()
        # TODO
        self._lasttime = -1
        self.reset_stats()

    def Bool(self, name):
        return z3.Bool(name)

    def negate(self, var):
        return z3.Not(var)

    def Or(self, lits):
        return z3.Or(lits)

    def addConstraint(self, clause):
        self._solver.add(clause)

    def addImplies(self, var, clauses):
        # tiny optimisation
        if len(clauses) == 1:
            con = clauses[0]
        else:
            con = z3.And(clauses)
        self._solver.add(z3.Implies(var, con))

    def solve(self, lits, *, getsol):
        self._stats["solveCount"] += 1
        result = self._solver.check(list(lits))
        if getsol == False:
            return result == z3.sat

        if result == z3.unsat:
            return None
        else:
            return self._solver.model()

    def solveSingle(self, puzlits, lits):
        sol = self.solve(lits, getsol=True)
        if sol is None:
            return None

        # Save the state of the solver so we can add another constraint
        self._solver.push()

        # At least one variable must take a different variable
        clause = []
        for l in puzlits:
            clause.append(l != sol[l])
        self.addConstraint(self.Or(clause))

        newsol = self.solve(lits, getsol=False)

        self.pop()
        if newsol:
            return "Multiple"
        else:
            return sol

    # Returns unsat_core from last solve
    def unsat_core(self):
        return self._solver.unsat_core()

    # TODO: Make these more efficient, if we need them
    def push(self):
        self._solver.push()

    def pop(self):
        self._solver.pop()

    def addLit(self, var):
        self._solver.add(var)

    # TODO: Would be more efficient, but not required
    def set_phases(self, positive, negative):
        pass

    def solveLimited(self, lits):
        return self.solve(lits, getsol=False)

    # TODO: In SAT we do this to flush learned clauses
    def reboot(self, seed):
        pass
 
    def reset_stats(self):
        self._stats = {
            "solveCount": 0,
            "solveTime": 0
        }

    def get_stats(self):
        return self._stats

    def add_stats(self, d):
        self._stats["solveCount"] += d["solveCount"]
        self._stats["solveTime"] += d["solveTime"]