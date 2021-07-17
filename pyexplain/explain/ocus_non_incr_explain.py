from pyexplain.explain.ocus_explain import OCUSExplain
import time
from pyexplain.solvers.bestStep import BestStepComputer
from pyexplain.solvers.hittingSet import CondOptHS
from pysat.formula import CNF
from pyexplain.explain.csp_explain import CSPExplain
from pyexplain.solvers.params import COusNonIncrParams


class OCUSExplainNotIncremental(OCUSExplain, BestStepComputer):
    def __init__(self, C: CNF, params: COusNonIncrParams, verbose=True, matching_table=None):
        OCUSExplain.__init__(self, C=C, params=params, verbose=verbose, matching_table=matching_table)
        BestStepComputer.__init__(self, cnf=C, sat=self.sat,params=params)

    def preprocess(self, U: set, f, I0: set, Iend):
        # initial values
        self.I0 = set(I0)
        self.Iend = Iend
        self.U = set(U) | set(-l for l in U)
        self.hittingset_solver = None

    def bestStep(self, f, Iend: set, I: set):
        """
        bestStep computes a subset A' of A that satisfies p s.t.
        C u A' is UNSAT and A' is f-optimal.

        Args:

            f (list): A cost function mapping 2^A -> N.
            Iend (set): The cautious consequence, the set of literals that hold in
                        all models.
            I (set): A partial interpretation such that I \subseteq Iend.
            sat (pysat.Solver): A SAT solver initialized with a CNF.
        """

        self.I = set(I)

        Iexpl = Iend - I

        F = set(l for l in Iend) | set(-l for l in Iend)

        F -= {-l for l in I}

        A = I | {-l for l in Iexpl}
        topt = time.time()
        self.hittingset_solver = CondOptHS(U=self.U, Iend=Iend, I=self.I)
        self.time_statisitics["opt"].append([time.time() - topt])

        cOUS = self.bestStepCOUS(f, F, A)

        self.hittingset_solver.delete()

        return cOUS
