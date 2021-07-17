from pyexplain.utils.utils import get_expl
import time
from pyexplain.solvers.bestStep import BestStepComputer
from pyexplain.solvers.hittingSet import CondOptHS
from pysat.formula import CNF
from pyexplain.explain.csp_explain import CSPExplain
from pyexplain.solvers.params import COusParams


class OCUSExplain(CSPExplain, BestStepComputer):
    def __init__(self, C: CNF, params: COusParams, verbose=True, matching_table=None):
        CSPExplain.__init__(self, C=C, verbose=verbose, matching_table=matching_table)
        BestStepComputer.__init__(self, cnf=C, sat=self.sat,params=params)

    def preprocess(self, U: set, f, I0: set, Iend):
        # initial values
        self.I0 = set(I0)
        self.Iend = Iend
        self.U = set(U) | set(-l for l in U)

        topt = time.time()
        self.hittingset_solver = CondOptHS(U=U, Iend=Iend, I=I0)
        self.time_statisitics["opt"].append([time.time() - topt])

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

        return self.bestStepCOUS(f, F, A)

    def bestStepCOUS(self, f, F, A: set):
        """Given a set of assumption literals A subset of F, bestStepCOUS
        computes a subset a subset A' of A that satisfies p s.t C u A' is
        UNSAT and A' is f-optimal based on [1].

        Args:
            f (func): Cost function mapping from lit to int.
            F (set): Set of literals I + (Iend \\ I)) + (-Iend \\ -I).
            A (set): Set of assumption literals I + (-Iend \\ -I).

        Returns:
            set: a subset A' of A that satisfies p s.t C u A' is UNSAT
                 and A' is f-optimal.
        """
        # UPDATE OBJECTIVE WEIGHTS
        self.hittingset_solver.updateObjective(f, A)

        # update weights
        nHS, nOPT, nSAT, nGROW  = 0, 0, 0, 0

        # time spent
        t_opt,t_sat,t_grow  = [], [], []

        while(True):
            topt = time.time()

            # COMPUTING OPTIMAL HITTING SET
            HS = self.hittingset_solver.CondOptHittingSet()
            if self.verbose > 1:
                print("\nHS\t= ", get_expl(self.matching_table, HS))
            # print('hs=', HS)
            t_opt.append(time.time() -topt)
            nHS += 1
            nOPT += 1

            tsat = time.time()

            # CHECKING SATISFIABILITY
            sat, HS_model = self.checkSat(HS, phases=self.Iend)

            t_sat.append(time.time() -tsat)
            nSAT += 1

            # OUS FOUND?
            if not sat:
                # call statistics
                self.call_statistics["hs"].append(nHS)
                self.call_statistics["opt"].append(nOPT)
                self.call_statistics["sat"].append(nSAT)
                self.call_statistics["grow"].append(nGROW)
                # timings
                self.time_statisitics["opt"].append(t_opt)
                self.time_statisitics["grow"].append(t_grow)
                self.time_statisitics["sat"].append(t_sat)

                return HS

            tgrow = time.time()
            SS = self.grow(f=f, A=A, HS=HS, HS_model=HS_model)

            if self.verbose > 1:
                print("SS\t= ", get_expl(self.matching_table, SS))

            t_grow.append(time.time() - tgrow)
            nGROW += 1

            # complement
            C = F - SS
            if self.verbose > 1:
                print("F \ SS\t= ", get_expl(self.matching_table, C))

            self.hittingset_solver.addCorrectionSet(C)

    def __del__(self):
        """Ensure sat solver is deleted after garbage collection.
        """
        self.hittingset_solver.__del__()

    def print_statistics(self):

        t_explain = self.time_statisitics["explain"][-1]

        t_opt = self.time_statisitics["opt"][-1]
        t_opt_explain = round(sum(t_opt)/t_explain*100)
        t_call_opt = round(sum(t_opt)/len(t_opt), 3)
        print("\t opt =", round(sum(t_opt),2),f"s\t[{t_opt_explain}%]\t",  t_call_opt, "[s/call]")

        t_grow = self.time_statisitics["grow"][-1]

        if len(t_grow) > 0:
            t_grow_explain = round(sum(t_grow)/t_explain*100)
            t_call_grow = round(sum(t_grow)/len(t_grow), 3)
            print("\t grow=", round(sum(t_grow),2),f"s\t[{t_grow_explain}%]\t",t_call_grow, "[s/call]")

        t_sat = self.time_statisitics["sat"][-1]
        t_sat_explain = round(sum(t_sat)/t_explain*100)
        t_call_sat =round(sum(t_sat)/len(t_sat), 3)
        print("\t sat =", round(sum(t_sat),2),f"s\t[{t_sat_explain}%]\t",  t_call_sat, "[s/call]")
