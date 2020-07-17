# This files includes all code which needs to actually call the SMT solver

import z3
import random
import copy
from .utils import flatten

def Bool(name):
    return z3.Bool(name)

# A variable is a dictionary mapping values to their SAT variable
def buildLit(lit):
    if lit.equal:
        return lit.var.litmap()[lit.val]
    else:
        return z3.Not(lit.var.litmap()[lit.val])

def buildConstraint(constraint):
    cs = constraint.clauseset()
    z3clauses = [z3.Or([buildLit(lit) for lit in c]) for c in cs]
    # Tiny optimisation
    if len(z3clauses) == 1:
        return z3clauses[0]
    else:
        return z3.And(z3clauses)

class Solver:
    def __init__(self, puzzle):
        self._puzzle = puzzle
        self._solver = z3.Solver()

        # Map from z3 booleans to constraints
        self._conmap = {}

        # Quick access to every boolean which represents a constraint
        self._conlits = set()

        # Quick access to every boolean which represents a puzzle variable
        self._puzlits = flatten([list(v.litmap().values()) for mat in self._puzzle.vars() for v in mat.varlist()])

        # Unique identifier for each introduced variable
        count = 0

        for mat in puzzle.vars():
            for c in mat.constraints():
                name = "{}{}".format(mat.varname, count)
                count = count + 1
                var = z3.Bool(name)
                self._solver.add(z3.Implies(var, buildConstraint(c)))
                self._conmap[var] = c
                self._conlits.add(var)

     
        count = 0
        for c in self._puzzle.constraints():
            name = "con{}".format(count)
            count = count + 1
            var = z3.Bool(name)
            self._solver.add(z3.Implies(var, buildConstraint(c)))
            self._conmap[var] = c
            self._conlits.add(var)

        # Used for tracking in push/pop/addLits
        self._stackknownlits = []
        self._knownlits = []

    def puzzle(self):
        return self._puzzle

    def puzlits(self):
        return self._puzlits
    
    # Check if there is a single solution, or return 'None'
    def solve(self, assumptions = []):
        result = self._solver.check(self._conlits.union(assumptions))
        if result == z3.sat:
            return self._solver.model()
        else:
            return None
    
    Multiple = "Multiple"
    # This is the same as 'solve', but checks if there are many solutions,
    # returning Solver.Multiple if there is more than one solution
    def solveSingle(self, varassumptions = []):
        sol = self.solve(varassumptions)
        if sol is None:
            return None

        # Save the state of the solver so we can add another constraint
        self._solver.push()

        # At least one variable must take a different variable
        clause = []
        for l in self._puzlits:
            assert sol[l] == True or sol[l] == False
            clause.append(l != sol[l])
        self._solver.add(z3.Or(clause))

        newsol = self.solve(varassumptions)

        self._solver.pop()


        if newsol is None:
            return sol
        else:
            return self.Multiple

    def basicCore(self, core):
        solve = self._solver.check(core)
        if solve == z3.sat:
            return None
        core = self._solver.unsat_core()
        return core

    def MUS(self, varassumptions = [], earlycutsize = None):
        core = self.basicCore(set(varassumptions).union(self._conlits))
        # Should never be satisfiable on the first pass
        assert core is not None
        if earlycutsize is not None and len(core) > earlycutsize:
            return None

        # So we can find different cores if we recall method
        random.shuffle(core)

        # First try chopping big bits off
        step = int(len(core) / 4)
        while step > 1:
            i = 0
            while i < len(core) - step:
                to_test = core[:i] + core[(i+step):]
                newcore = self.basicCore(to_test)
                if newcore is not None:
                    core = newcore
                    i = 0
                else:
                    i += step
            step = int(step / 2)

        # Final cleanup
        # We need to be prepared for things to disappear as
        # we reduce the core, so make a copy and iterate through
        # that
        corecpy = list(core)
        for lit in corecpy:
            if lit in core:
                to_test = list(core)
                to_test.remove(lit)
                newcore = self.basicCore(to_test)
                if newcore is not None:
                    core = newcore
        
        return core

    def addLit(self, lit, val):
        if val:
            self._solver.add(lit)
            self._knownlits.append(lit)
        else:
            self._solver.add(z3.Not(lit))
            self._knownlits.append(z3.Not(lit))

    # Storing and restoring assignments
    def push(self):
        self._solver.push()
        self._stackknownlits.append(copy.deepcopy(self._knownlits))
    
    def pop(self):
        self._solver.pop()
        self._knownlits = self._stackknownlits.pop()

    
    def explain(self, var):
        if var in self._puzlits:
            return str(self._puzlits)
        if var in self._conlits:
            return self._conmap[var].explain([])
        else:
            return "???"