from .musdict import MusDict
# from ocussolvers.bestStep import optimalPropagate
# from ocussolvers.bestStep import BestStepComputer
# from ocussolvers.params import COusParams
# from ocussolvers.hittingSet import CondOptHS
from pysat.formula import CNF
from pysat.solvers import Solver

def cost_puzzle():
    def cost_lit(lit):
        return 1

    return cost_lit

class OcusMUSFinder(BestStepComputer):
    def __init__(self, solver):
        
        self._solver = solver
        self.sat = Solver(bootstrap_with=solver._cnf.clauses)
        BestStepComputer.__init__(self, cnf=solver._cnf, sat=self.sat, params=COusParams())
        p_user_vars = set([solver._varlit2smtmap[a] for a in solver.solveSingle([])])

        self.U = p_user_vars | set(solver._conlits)
        self.I = set(solver._conlits)
        
        self.I0 = set(self.I)
        self.f = cost_puzzle()

        assert self.sat.solve(assumptions=self.I0), f"CNF is unsatisfiable with given assumptions {self.I0}."
        self.Iend = optimalPropagate(U=self.U, I=self.I0, sat=self.sat)

        self.hittingset_solver = CondOptHS(U=self.U, Iend=self.Iend, I=self.I0)
        pass

    def smallestMUS(self, puzlits):
        musdict = MusDict({})
        self.ocusMUS(musdict)
        return musdict

    def ocusMUS(self, musdict):

        expl = self.bestStep(self.f, self.Iend, self.I)
        Ibest = self.I & expl
        Nbest = optimalPropagate(U=self.U, I=Ibest, sat=self.sat) - self.I
        mus = [self._solver._conmap[x] for x in expl if x in self._solver._conmap]
        musdict.update(list(Nbest)[0], mus)

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

        while(True):

            # COMPUTING OPTIMAL HITTING SET
            HS = self.hittingset_solver.CondOptHittingSet()

            nHS += 1
            nOPT += 1

            # CHECKING SATISFIABILITY
            sat, HS_model = self.checkSat(HS, phases=self.Iend)

            nSAT += 1

            # OUS FOUND?
            if not sat:
                return HS

            SS = self.grow(f=f, A=A, HS=HS, HS_model=HS_model)

            nGROW += 1

            # complement
            C = F - SS

            self.hittingset_solver.addCorrectionSet(C)