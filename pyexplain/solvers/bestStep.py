
from .hittingSet import CondOptHS, OptHS
from .params import BestStepParams, COusParams, Grow, Interpretation, OusParams, Weighing
from ..utils.exceptions import UnsatError

# pysat imports
from pysat.formula import CNF, WCNF
from pysat.solvers import Solver
from pysat.examples.musx import MUSX
from pysat.examples.rc2 import RC2


def optimalPropagate(sat, I=set(), U=None):
    """
    optPropage produces the intersection of all models of cnf more precise
    projected on focus.

    Improvements:
    - Extension 1:
        + Reuse solver only for optpropagate
    - Extension 2:
        + Reuse solver for all sat calls
    - Extension 3:
        + Set phases

    Args:
    cnf (list): CNF C over V:
            hard puzzle problems with assumptions variables to activate or
            de-active clues.
    I (list): partial interpretation

    U (list):
        +/- literals of all user variables
    """
    solved = sat.solve(assumptions=list(I))

    if not solved:
        raise UnsatError(I)

    model = set(sat.get_model())
    if U:
        model = set(l for l in model if abs(l) in U)

    bi = sat.nof_vars() + 1

    while(True):
        sat.add_clause([-bi] + [-lit for lit in model])
        solved = sat.solve(assumptions=list(I) + [bi])

        if not solved:
            sat.add_clause([-bi])
            return model

        new_model = set(sat.get_model())
        model = model.intersection(new_model)


class BestStepComputer(object):
    def __init__(self, cnf: CNF, sat: Solver, params: BestStepParams):
        self.sat_solver = sat
        self.cnf = cnf
        self.opt_model = None
        self.I0 = None
        self.I = None
        self.Iend = None

        # check parameters
        params.checkParams()
        self.params = params

    def grow_subset_maximal_actual(self,  HS, Ap):
        _, App = self.checkSat(HS | (self.I & Ap), phases=self.I)
        # repeat until subset maximal wrt A
        while (Ap != App):
            Ap = set(App)
            sat, App = self.checkSat(HS | (self.I & Ap), phases=self.I)
        return App

    def grow(self, f, A, HS, HS_model):
        # no actual grow needed if 'HS_model' contains all user vars
        if self.params.grow is Grow.DISABLED:
            return HS
        elif self.params.grow is Grow.SAT:
            return HS_model
        elif self.params.grow is Grow.SUBSETMAX:
            return self.grow_subset_maximal(A, HS, HS_model)
        elif self.params.grow is Grow.MAXSAT:
            return self.grow_maxsat(f, A, HS)
        else:
            raise NotImplementedError("Grow")

    def grow_maxsat(self, f, A, HS):
        remaining, weights = None, None
        wcnf = WCNF()

        # HARD clauses
        wcnf.extend(self.cnf.clauses)
        wcnf.extend([[l] for l in HS])

        # SOFT clauses to grow
        if self.params.interpretation is Interpretation.INITIAL:
            remaining = list(self.I0 - HS)
        elif self.params.interpretation is Interpretation.ACTUAL:
            remaining = list(self.I - HS)
        elif self.params.interpretation is Interpretation.FULL:
            remaining = list(self.Iend - HS)
        elif self.params.interpretation is Interpretation.FINAL:
            remaining = list(A - HS)

        remaining_clauses = [[l] for l in remaining]

        if self.params.maxsat_weighing is Weighing.POSITIVE:
            weights = [f(l) for l in remaining]
        elif self.params.maxsat_weighing is Weighing.INVERSE:
            max_weight = max(f(l) for l in remaining) + 1
            weights = [max_weight - f(l) for l in remaining]
        elif self.params.maxsat_weighing is Weighing.UNIFORM:
            weights = [1] * len(remaining)

        # cost is associated for assigning a truth value to literal not in
        # contrary to A.
        wcnf.extend(clauses=remaining_clauses, weights=weights)

        # solve the MAXSAT problem
        with RC2(wcnf) as s:
            if self.params.maxsat_polarity and hasattr(s, 'oracle'):
                s.oracle.set_phases(literals=list(self.Iend))

            t_model = s.compute()

            return set(t_model)

    def grow_subset_maximal(self, A, HS, Ap):
        # used interpretation
        I = None

        if self.params.interpretation is Interpretation.INITIAL:
            I = set(self.I0)
        elif self.params.interpretation is Interpretation.ACTUAL:
            I = set(self.I)
        elif self.params.interpretation is Interpretation.FINAL:
            I = set(self.Iend)
        elif self.params.interpretation is Interpretation.FULL:
            I = set(A)

        _, App = self.checkSat(HS | (I & Ap), phases=I)

        while (Ap != App):
            Ap = set(App)
            _, App = self.checkSat(HS | (I & Ap), phases=I)

        return App

    def checkSat(self, Ap: set, phases=None):
        """Check satisfiability of given assignment of subset of the variables
        of Vocabulary V.
            - If the subset is unsatisfiable, Ap is returned.
            - If the subset is satisfiable, the model computed by the sat
                solver is returned.

        Args:
            Ap (set): Susbet of literals

        Returns:
            (bool, set): sat value, model assignment
        """
        if phases:
            self.sat_solver.set_phases(literals=phases)

        solved = self.sat_solver.solve(assumptions=list(Ap))

        if not solved:
            return solved, Ap

        model = set(self.sat_solver.get_model())
        return solved, model

