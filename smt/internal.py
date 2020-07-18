# This files includes all code which needs to actually call the SMT solver

import random
import copy
import types

import z3

from .utils import flatten

from .base import EqVal, NeqVal

# A variable is a dictionary mapping values to their SAT variable


class Solver:
    def __init__(self, puzzle):
        self._puzzle = puzzle
        self._solver = z3.Solver()

        # Map from internal booleans to constraints
        self._conmap = {}

        # Quick access to every internal boolean which represents a constraint
        self._conlits = set()

        # Set up variable mappings -- we make a bunch as we need these to be fast.
        # 'lit' refers to base.EqVal and base.NeqVar, objects which users should see.
        # 'smt' refers to the solver's internal representation

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
                    b = z3.Bool(str(lit))

                    self._varlit2smtmap[lit] = b
                    self._varlit2smtmap[neglit] = z3.Not(b)
                    self._varsmt2litmap[b] = lit
                    self._varsmt2neglitmap[b] = neglit
                    self._varsmt.add(b)
    
        # Unique identifier for each introduced variable
        count = 0

        for mat in puzzle.vars():
            for c in mat.constraints():
                name = "{}{}".format(mat.varname, count)
                count = count + 1
                var = z3.Bool(name)
                self._solver.add(z3.Implies(var, self._buildConstraint(c)))
                self._conmap[var] = c
                self._conlits.add(var)

     
        count = 0
        for c in self._puzzle.constraints():
            name = "con{}".format(count)
            count = count + 1
            var = z3.Bool(name)
            self._solver.add(z3.Implies(var, self._buildConstraint(c)))
            self._conmap[var] = c
            self._conlits.add(var)

        # Used for tracking in push/pop/addLits
        self._stackknownlits = []
        self._knownlits = []

    def puzzle(self):
        return self._puzzle

    def _buildConstraint(self, constraint):
        cs = constraint.clauseset()
        z3clauses = [z3.Or([self._varlit2smtmap[lit] for lit in c]) for c in cs]
        # Tiny optimisation
        if len(z3clauses) == 1:
            return z3clauses[0]
        else:
            return z3.And(z3clauses)
    
    # Check if there is a single solution, or return 'None'
    def _solve(self, smtassume = tuple()):
        result = self._solver.check(self._conlits.union(smtassume))
        if result == z3.sat:
            return self._solver.model()
        else:
            return None
    
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
        sol = self._solve(smtassume)
        if sol is None:
            return None

        # Save the state of the solver so we can add another constraint
        self._solver.push()

        # At least one variable must take a different variable
        clause = []
        for l in self._varsmt:
            clause.append(l != sol[l])
        self._solver.add(z3.Or(clause))

        newsol = self._solve(smtassume)

        self._solver.pop()

        if newsol is None:
            return self.var_smt2lits(sol)
        else:
            return self.Multiple

    def basicCore(self, core):
        solve = self._solver.check(core)
        if solve == z3.sat:
            return None
        core = self._solver.unsat_core()
        return core

    def MUS(self, assume = [], earlycutsize = None):
        smtassume = [self._varlit2smtmap[l] for l in assume]

        core = self.basicCore(set(smtassume).union(self._conlits))
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
        
        return [self._conmap[x] for x in core if x in self._conmap]

    def addLit(self, lit):
        self._solver.add(self._varlit2smtmap[lit])
        self._knownlits.append(lit)

    # Storing and restoring assignments
    def push(self):
        self._solver.push()
        self._stackknownlits.append(copy.deepcopy(self._knownlits))
    
    def pop(self):
        self._solver.pop()
        self._knownlits = self._stackknownlits.pop()

    
    def explain(self, c):
        return c.explain(self._knownlits)
