import copy
import logging
from sortedcontainers import *

from pysat.solvers import Solver
from ..utils import chainlist, get_cpu_time, randomFromSeed
from ..config import CONFIG

import pysat
import inspect
import multiprocessing
import traceback
import random

# print(inspect.getfile(pysat))


class SATSolver:
    def __init__(self, cnf=None):
        if cnf is None:
            self._solver = Solver(name=CONFIG["solver"], incr=CONFIG["solverIncremental"])
            self._boolcount = 1
            self._clauses = []
        else:
            self._boolcount = cnf.nv
            self._solver = Solver(name=CONFIG["solver"], incr=CONFIG["solverIncremental"],bootstrap_with=cnf.clauses)
            self._clauses = cnf.clauses
                    

        self._stack = []
        self._boolnames = {}
        self._knownlits = SortedSet()
        if CONFIG["dumpSAT"]:
            assert(cnf is None)
            self._rawclauses = []
        self._lasttime = -1

        self.reset_stats()

    def Bool(self, name):
        newbool = self._boolcount
        self._boolcount += 1
        self._boolnames[newbool] = name
        return newbool

    def negate(self, var):
        return -var

    def Or(self, lits):
        return list(lits)

    def addConstraint(self, clause):
        self._clauses.append(clause)
        if CONFIG["dumpSAT"]:
            self._rawclauses.append(clause)
        self._solver.add_clause(clause)

    def addImplies(self, var, clauses):
        for c in clauses:
            self._clauses.append(c + [-var])
            self._solver.add_clause(c + [-var])
            if CONFIG["dumpSAT"]:
                assert len(clauses) == 1
                self._rawclauses.append(c)

    # Recreate solver, throwing away all learned clauses
    def reboot(self, seed):
        self._solver.delete()
        if CONFIG["changeSolverSeed"]:
            import pysolvers
            assert pysolvers.glucose41_set_argc(["-rnd-seed="+ str(seed)])
        self._solver = Solver(
            name=CONFIG["solver"],
            incr=CONFIG["solverIncremental"],
            bootstrap_with=randomFromSeed(seed).sample(self._clauses, len(self._clauses))
        )
    
    def dumpSAT(self, filename, assume):
        assert len(assume) == 1
        known = SortedSet(list(self._knownlits) + assume)
        needed = [c for c in self._rawclauses if len(known.intersection(c)) == 0]
        simplified = [ [x for x in c if (-x) not in known ] for c in needed ]
        #simplified = SortedSet([ tuple(s) for s in simplified if len(s) > 0 ])
        with open(filename, "w") as f:
            print("p cnf {} {}".format(max(abs(x) for c in self._clauses for x in c), len(simplified) ), file=f)
            for c in simplified:
                print(" ".join(str(x) for x in c) + " 0", file=f)



    # SAT assignments look like a list of integers, where:
    # '5' means variable 5 is true
    # '-5' means variable 5 is false
    # We want a map where m[5] is true if 5 is true
    def satassignment2map(self, l):
        return {abs(x): x > 0 for x in l}

    def solve(self, lits, *, getsol):
        # if multiprocessing.current_process().name == "MainProcess":
        #    print("!! solving in the main thread")
        #    traceback.print_stack()
        if CONFIG["resetSolverFull"]:
            self.reboot()

        start_time = get_cpu_time()
        x = self._solver.solve(assumptions=chainlist(lits, self._knownlits))
        end_time = get_cpu_time()
        self._stats["solveCount"] += 1
        self._stats["solveTime"] += end_time - start_time
        self._lasttime = end_time - start_time
        if self._lasttime > 5:
            logging.info("Long time solve: %s %s", len(lits), end_time - start_time)
        if getsol == False:
            return x
        if x:
            return self.satassignment2map(self._solver.get_model())
        else:
            return None

    def solveLimited(self, lits):
        # if multiprocessing.current_process().name == "MainProcess":
        #    print("!! solveLimited in the main thread")
        #    traceback.print_stack()
        if CONFIG["resetSolverFull"]:
            self.reboot()

        start_time = get_cpu_time()
        start_stats = self._solver.accum_stats()
        if CONFIG["solveLimited"]:
            self._solver.prop_budget(CONFIG["solveLimitedBudget"])
            x = self._solver.solve_limited(assumptions=chainlist(lits, self._knownlits))
        else:
            x = self._solver.solve(assumptions=chainlist(lits, self._knownlits))
        end_time = get_cpu_time()
        self._stats["solveCount"] += 1
        self._stats["solveTime"] += end_time - start_time
        self._lasttime = end_time - start_time
        if self._lasttime > 5:
            logging.info(
                "Long time solveLimited: %s %s", len(lits), end_time - start_time
            )
        return x

    def solveSingle(self, puzlits, lits):
        # if multiprocessing.current_process().name == "MainProcess":
        #    print("!! solveSingle in the main thread")
        # We just brute force check all assignments to other variables
        sol = self.solve(lits, getsol=True)
        if sol is None:
            return sol
        for p in puzlits:
            if sol[p]:
                extrasol = self.solve(chainlist(lits, [-p]), getsol=False)
            else:
                extrasol = self.solve(chainlist(lits, [p]), getsol=False)
            if extrasol:
                return "Multiple"
        return sol

    def solveAll(self, puzlits, lits):
        # if multiprocessing.current_process().name == "MainProcess":
        #    print("!! solveSingle in the main thread")
        # We just brute force check all assignments to other variables
        sol = {}
        for p in puzlits:
            pos = self.solve(chainlist(lits, [p]), getsol=False)
            neg = self.solve(chainlist(lits, [-p]), getsol=False)
            if not (pos and neg):
                if pos:
                    sol[p] = True
                else:
                    sol[p] = False
        return sol

    # Returns unsat_core from last solve
    def unsat_core(self):
        core = [x for x in self._solver.get_core() if x not in self._knownlits]
        # logging.info("Core size: %s", len(core))
        return core

    def push(self):
        self._stack.append(copy.deepcopy(self._knownlits))

    def pop(self):
        self._knownlits = self._stack.pop()

    def addLit(self, var):
        # We used to check this, but now one high-level variable can be named with multiple lits
        #assert var not in self._knownlits
        if var not in self._knownlits:
            self._knownlits.add(var)

    def set_phases(self, positive, negative):
        # TODO: Ignore the positive ones seems to be best
        if CONFIG["setPhases"]:
            l = [-x for x in negative]
            self._solver.set_phases(l)

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
