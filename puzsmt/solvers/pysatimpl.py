import copy


from pysat.solvers import Solver
from ..utils import chainlist

import pysat
import inspect

print(inspect.getfile(pysat))

class SATSolver:
    def __init__(self):
        self._solver = Solver(name="g4", incr=True)
        self._boolcount = 1
        self._boolnames = {}
        self._knownlits = set()
        self._stack = []

    def Bool(self, name):
        newbool = self._boolcount
        self._boolnames[newbool] = name
        self._boolcount += 1
        return newbool

    def negate(self, var):
        return -var

    def Or(self, lits):
        return list(lits)

    def addConstraint(self, clause):
        self._solver.add_clause(clause)

    def addImplies(self, var, clauses):
        for c in clauses:
            self._solver.add_clause(c + [-var])
    
    # SAT assignments look like a list of integers, where:
    # '5' means variable 5 is true
    # '-5' means variable 5 is false
    # We want a map where m[5] is true if 5 is true
    def satassignment2map(self, l):
        return {abs(x): x > 0 for x in l}

    def solve(self, lits):
        x = self._solver.solve(assumptions=chainlist(lits, self._knownlits))
        if x:
            return self.satassignment2map(self._solver.get_model())
        else:
            return None

    def solveSingle(self, puzlits, lits):
        # We just brute force check all assignments to other variables
        sol = self.solve(lits)
        if sol is None:
            return sol
        for p in puzlits:
            if sol[p]:
                extrasol = self.solve(chainlist(lits, [-p]))
            else:
                extrasol = self.solve(chainlist(lits, [p]))
            if extrasol is not None:
                return "Multiple"
        return sol

    # Returns unsat_core from last solve
    def unsat_core(self):
        return [x for x in self._solver.get_core() if x not in self._knownlits]

    def push(self):
        self._stack.append(copy.deepcopy(self._knownlits))
    
    def pop(self):
        self._knownlits = self._stack.pop()

    def addLit(self, var):
        assert var not in self._knownlits
        self._knownlits.add(var)
