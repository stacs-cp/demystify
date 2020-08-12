# This files includes all code which needs to actually call the SMT solver

import copy
import types
import random

from .utils import flatten, chainlist

from .base import EqVal, NeqVal

# A variable is a dictionary mapping values to their SAT variable

from .solvers.z3impl import Z3Solver
from .solvers.pysatimpl import SATSolver
class Solver:
    def __init__(self, puzzle):
        self._puzzle = puzzle
        #self._solver = Z3Solver()
        self._solver = SATSolver()

        # We want a reliable random source
        self.random = random.Random(1)

        # Map from internal booleans to constraints
        self._conmap = {}

        # Quick access to every internal boolean which represents a constraint
        self._conlits = set()

        # Set up variable mappings -- we make a bunch as we need these to be fast.
        # 'lit' refers to base.EqVal and base.NeqVar, objects which users should see.
        # 'puzsmt' refers to the solver's internal representation

        # Map EqVal and NeqVal to internal variables
        self._varlit2smtmap = {}

        # Map internal to EqVal
        self._varsmt2litmap = {}

        # Map internal to a NeqVal (for when they are False in the model)
        self._varsmt2neglitmap = {}

        # Set, so we quickly know is an internal variable represents a variable
        self._varsmt = set([])

        for mat in self._puzzle.vars():
            for v in mat.varlist():
                for d in v.dom():
                    lit = EqVal(v,d)
                    neglit = NeqVal(v,d)
                    b = self._solver.Bool(str(lit))

                    self._varlit2smtmap[lit] = b
                    self._varlit2smtmap[neglit] = self._solver.negate(b)
                    self._varsmt2litmap[b] = lit
                    self._varsmt2neglitmap[b] = neglit
                    self._varsmt.add(b)
    
        # Unique identifier for each introduced variable
        count = 0

        for mat in puzzle.vars():
            for c in mat.constraints():
                name = "{}{}".format(mat.varname, count)
                count = count + 1
                var = self._solver.Bool(name)
                self._solver.addImplies(var, self._buildConstraint(c))
                self._conmap[var] = c
                self._conlits.add(var)

     
        count = 0
        for c in self._puzzle.constraints():
            name = "con{}".format(count)
            count = count + 1
            var = self._solver.Bool(name)
            self._solver.addImplies(var, self._buildConstraint(c))
            self._conmap[var] = c
            self._conlits.add(var)

        # Used for tracking in push/pop/addLits
        self._stackknownlits = []
        self._knownlits = []

        # For benchmarking
        self._corecount = 0

        self.init_litmappings()

    def init_litmappings(self):
        # Set up some mappings for efficient finding of tiny MUSes
        self._varlit2con = { l : set() for l in self._varlit2smtmap.keys() }
        for (var,con) in self._conmap.items():
            lits = con.lits()
            # Negate all the lits
            neglits = [l.neg() for l in lits]
            for l in neglits:
                self._varlit2con[l].add(var)

        self._varlit2con2 = {l : set() for l in self._varlit2smtmap.keys() }
        for (var,cons) in self._varlit2con.items():
            lits = set(flatten([self._conmap[c].lits() for c in cons]))
            neglits = [l.neg() for l in lits]
            for l in neglits:
                self._varlit2con2[l].add(var)


    def puzzle(self):
        return self._puzzle

    def _buildConstraint(self, constraint):
        cs = constraint.clauseset()
        z3clause = [self._solver.Or([self._varlit2smtmap[lit] for lit in c]) for c in cs]
        return z3clause
    
    # Check if there is a single solution, or return 'None'
    def _solve(self, smtassume = tuple()):
        return self._solver.solve(chainlist(self._conlits, smtassume))

    # Check if there is a single solution, or return 'None'
    def _solveSingle(self, smtassume = tuple()):
        return self._solver.solveSingle(self._varsmt,chainlist(self._conlits,smtassume))
    
    Multiple = "Multiple"

    def var_smt2lits(self, model):
        ret = []
        for l in self._varsmt:
            if model[l]:
                ret.append(self._varsmt2litmap[l])
            else:
                ret.append(self._varsmt2neglitmap[l])
        return ret

    def solve(self, assume = tuple()):
        smtassume = [self._varlit2smtmap[l] for l in assume]
        sol = self._solve(smtassume)
        if sol is None:
            return None
        else:
            return self.var_smt2lits(sol)

    # This is the same as 'solve', but checks if there are many solutions,
    # returning Solver.Multiple if there is more than one solution
    def solveSingle(self, assume = tuple()):
        smtassume = [self._varlit2smtmap[l] for l in assume]
        sol = self._solveSingle(smtassume)
        if sol is None:
            return None
        elif sol == self.Multiple:
            return self.Multiple
        else:
            return self.var_smt2lits(sol)

    def basicCore(self, lits):
        self._corecount += 1
        solve = self._solver.solve(lits)
        if solve is not None:
            return None
        core = self._solver.unsat_core()
        assert set(core).issubset(set(lits))
        return core



    def addLit(self, lit):
        self._solver.addLit(self._varlit2smtmap[lit])
        self._knownlits.append(lit)

    def getKnownLits(self):
        return self._knownlits

    # Storing and restoring assignments
    def push(self):
        self._solver.push()
        self._stackknownlits.append(copy.deepcopy(self._knownlits))
    
    def pop(self):
        self._solver.pop()
        self._knownlits = self._stackknownlits.pop()

    
    def explain(self, c):
        return c.explain(self._knownlits)
