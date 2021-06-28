# This files includes all code which needs to actually call the SMT solver

import copy
import types
import random
import logging
from sortedcontainers import *

from .utils import flatten, chainlist, randomFromSeed

from .base import EqVal, NeqVal

from .config import CONFIG

# A variable is a dictionary mapping values to their SAT variable

from .solvers.z3impl import Z3Solver
from .solvers.pysatimpl import SATSolver


class Solver:
    def __init__(self, puzzle, *, cnf=None, litmap=None, conmap=None):
        assert puzzle is not None

        self._puzzle = puzzle
        if CONFIG["solver"] == "z3":
            self._solver = Z3Solver()
        else:
            self._solver = SATSolver()

        # We want a reliable random source
        self.random = randomFromSeed(1)

        # Map from internal booleans to constraints and vice versa
        self._conmap = {}
        self._conlit2conmap = {}

        # Quick access to every internal boolean which represents a constraint
        self._conlits = SortedSet()

        # Set up variable mappings -- we make a bunch as we need these to be fast.
        # 'lit' refers to base.EqVal and base.NeqVar, objects which users should see.
        # 'demystify' refers to the solver's internal representation

        # Map EqVal and NeqVal to internal variables
        self._varlit2smtmap = {}

        # Map internal to EqVal
        self._varsmt2litmap = {}

        # Map internal to a NeqVal (for when they are False in the model)
        self._varsmt2neglitmap = {}

        # Set, so we quickly know is an internal variable represents a variable
        self._varsmt = SortedSet([])

        # Used for tracking in push/pop/addLits
        self._stackknownlits = []
        self._knownlits = []

        # For benchmarking
        self._corecount = 0

        self._cnf = []

        if cnf is not None:
            self.init_fromCNF(cnf, litmap, conmap)

            self.init_litmappings()
            return

        for mat in self._puzzle.vars():
            for v in mat.varlist():
                for d in v.dom():
                    lit = EqVal(v, d)
                    neglit = NeqVal(v, d)
                    b = self._solver.Bool(str(lit))

                    self._varlit2smtmap[lit] = b
                    self._varlit2smtmap[neglit] = self._solver.negate(b)
                    self._varsmt2litmap.setdefault(b, SortedSet()).add(lit)
                    self._varsmt2neglitmap.setdefault(b, SortedSet()).add(
                        neglit
                    )
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
                assert c not in self._conlit2conmap
                self._conlit2conmap[c] = var
                self._conlits.add(var)

        self._solver.set_phases(positive=self._varsmt, negative=self._conlits)

        count = 0
        for c in self._puzzle.constraints():
            name = "con{}".format(count)
            count = count + 1
            var = self._solver.Bool(name)
            self._solver.addImplies(var, self._buildConstraint(c))
            self._conmap[var] = c
            logging.debug("Assigned %s to %s", c, var)
            assert c not in self._conlit2conmap
            self._conlit2conmap[c] = var
            self._conlits.add(var)

        self.init_litmappings()

    def init_fromCNF(self, cnf, litmap, conmap):
        assert CONFIG["solver"] != "z3"
        self._solver = SATSolver(cnf)
        self._cnf = cnf
        for (lit, b) in litmap.items():
            neglit = lit.neg()
            if b < 0:
                neglit, lit = lit, neglit
                b = b * -1
            self._varlit2smtmap[lit] = b
            self._varlit2smtmap[neglit] = self._solver.negate(b)

            self._varsmt2litmap.setdefault(b, SortedSet()).add(lit)
            self._varsmt2neglitmap.setdefault(b, SortedSet()).add(neglit)
            self._varsmt.add(b)

        for (con, var) in conmap.items():
            self._conmap[var] = con
            self._conlit2conmap[con] = var
            self._conlits.add(var)

    def init_litmappings(self):
        # Set up some mappings for efficient finding of tiny MUSes
        # Map from a var lit to all the constraints it is in
        self._varlit2con = {l: SortedSet() for l in self._varlit2smtmap.keys()}

        # Map from a var lit to the negation of all lits it is in a constraint with
        # (to later make distance 2 mappings)
        self._varlit2negconnectedlits = {
            l: SortedSet() for l in self._varlit2smtmap.keys()
        }

        for (cvar, con) in self._conmap.items():
            lits = con.lits()
            # Negate all the lits
            neglits = [l.neg() for l in lits]
            for l in neglits:
                self._varlit2con[l].add(cvar)
                self._varlit2negconnectedlits[l].update(neglits)

        # Map from a var lit to all constraints it is distance 2 from
        self._varlit2con2 = (
            {}
        )  # {l : SortedSet() for l in self._varlit2smtmap.keys() }
        for (lit, connected) in self._varlit2negconnectedlits.items():
            allcon = SortedSet.union(
                *[self._varlit2con[x] for x in connected], SortedSet()
            ).union(self._varlit2con[lit])
            self._varlit2con2[lit] = allcon

    def puzzle(self):
        return self._puzzle

    def _buildConstraint(self, constraint):
        cs = constraint.clauseset()
        clauses = [
            self._solver.Or([self._varlit2smtmap[lit] for lit in c]) for c in cs
        ]
        return clauses

    # Check if there is a single solution, or return 'None'
    def _solve(self, smtassume=tuple(), *, getsol):
        # print("conlits:", self._conlits)
        return self._solver.solve(
            chainlist(self._conlits, smtassume), getsol=getsol
        )

    # Check if there is a single solution and return True/False, or return 
    # 'None' if timeout
    def _solveLimited(self, smtassume=tuple()):
        return self._solver.solveLimited(chainlist(self._conlits, smtassume))

    # Check if there is a single solution, or return 'None'
    def _solveSingle(self, smtassume=tuple()):
        return self._solver.solveSingle(
            self._varsmt, chainlist(self._conlits, smtassume)
        )

    def _solveAll(self, smtassume=tuple()):
        return self._solver.solveAll(
            self._varsmt, chainlist(self._conlits, smtassume)
        )

    def reboot(self, seed):
        self._solver.reboot(seed)

    Multiple = "Multiple"

    def var_smt2lits(self, model):
        ret = []
        for l in self._varsmt:
            if l in model:
                if model[l]:
                    ret.extend(self._varsmt2litmap[l])
                else:
                    ret.extend(self._varsmt2neglitmap[l])
        return ret

    def solve(self, assume=tuple(), *, getsol):
        smtassume = [self._varlit2smtmap[l] for l in assume]
        # print("smtassume: ", smtassume)
        sol = self._solve(smtassume, getsol=getsol)
        if getsol == False:
            return sol

        if sol is None:
            return None
        else:
            return self.var_smt2lits(sol)

    # This is the same as 'solve', but checks if there are many solutions,
    # returning Solver.Multiple if there is more than one solution
    def solveSingle(self, assume=tuple()):
        smtassume = [self._varlit2smtmap[l] for l in assume]
        sol = self._solveSingle(smtassume)
        if sol is None:
            return None
        elif sol == self.Multiple:
            return self.Multiple
        else:
            return self.var_smt2lits(sol)

    # This is the same as 'solve', but checks if there are many solutions,
    # returning Solver.Multiple if there is more than one solution
    def solveAll(self, assume=tuple()):
        smtassume = [self._varlit2smtmap[l] for l in assume]
        sol = self._solveAll(smtassume)
        return self.var_smt2lits(sol)

    # Return a subset of 'lits' which forms a core, or
    # None if no core exists (or can be proved in the time limit)
    def basicCore(self, lits):
        self._corecount += 1
        solve = self._solver.solveLimited(lits)
        if solve is True or solve is None:
            return None
        if CONFIG["useUnsatCores"]:
            core = self._solver.unsat_core()
            assert SortedSet(core).issubset(SortedSet(lits))
        else:
            core = lits
        return core

    def addLit(self, lit):
        if lit not in self._knownlits:
            self._solver.addLit(self._varlit2smtmap[lit])
            self._knownlits.append(lit)

    def getKnownLits(self):
        return self._knownlits

    def getCurrentDomain(self):
        return self._puzzle.modelToAssignment(self.getKnownLits(), partial=True)

    # Storing and restoring assignments
    def push(self):
        self._solver.push()
        self._stackknownlits.append(copy.deepcopy(self._knownlits))

    def pop(self):
        self._solver.pop()
        self._knownlits = self._stackknownlits.pop()

    def explain(self, c):
        return c.explain(self._knownlits)

    def reset_stats(self):
        self._solver.reset_stats()

    def get_stats(self):
        return copy.deepcopy(self._solver.get_stats())

    def add_stats(self, d):
        self._solver.add_stats(d)
