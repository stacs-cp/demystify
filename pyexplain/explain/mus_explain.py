import time
from pyexplain.solvers.bestStep import optimalPropagate
from pysat.formula import WCNF, CNF
from pysat.examples.musx import MUSX
from pyexplain.explain.csp_explain import CSPExplain
from pyexplain.solvers.params import MUSParams


class MUSExplain(CSPExplain):
    def __init__(self, C: CNF, params: MUSParams, verbose=False, matching_table=None):
        super().__init__(C=C,verbose=verbose, matching_table=matching_table)
        self.params = params

    def explain(self, U: set, f, I0: set):
        # check literals of I are all user vocabulary
        assert all(True if abs(lit) in U else False for lit in I0), f"Part of supplied literals not in U (user variables): {lits for lit in I if lit not in U}"

        # Initialise the sat solver with the cnf
        assert self.sat.solve(assumptions=I0), f"CNF is unsatisfiable with given assumptions {I0}."

        # Explanation sequence
        self.E = []

        I = set(I0)
        tstart_explain = time.time()

        # Most precise intersection of all models of C project on U
        tstart = time.time()
        Iend = optimalPropagate(U=U, I=I, sat=self.sat)
        self.time_statisitics["prop"].append(time.time() - tstart)
        self.call_statistics["prop"] += 1

        super().preprocess(U, f, I, Iend)

        while(len(Iend - I) > 0):
            costExpl = 0
            # Compute optimal explanation explanation assignment to subset of U.
            tstart = time.time()
            costExpl, Ei = self.bestStep(f, U, I)
            self.time_statisitics["explain"].append(time.time() - tstart)
            self.time_statisitics["cumul_explain"].append(time.time() - tstart_explain)

            # facts used
            Ibest = I & Ei

            tstart = time.time()
            # New information derived "focused" on
            Nbest = optimalPropagate(U=U, I=Ibest, sat=self.sat) - I
            self.call_statistics["prop"] += 1
            self.time_statisitics["prop"].append(time.time() - tstart)

            assert len(Nbest - Iend) == 0

            self.E.append({
                "constraints": list(Ibest),
                "derived": list(Nbest),
                "cost": costExpl
            })

            I |= Nbest
            self.call_statistics["explained"] += len(Nbest)

            if self.verbose > 0:
                self.get_expl(Ibest)
                print(f"\nOptimal explanation \t {len(Iend-I)}/{len(Iend-I0)} \t {Ibest} => {Nbest}\n")
                self.print_statistics()

        self.time_statisitics["totalTime"] = time.time() - tstart_explain

    def MUSExtraction(self, C):
        wcnf = WCNF()
        wcnf.extend(self.cnf.clauses)
        wcnf.extend([[l] for l in C], [1]*len(C))
        with MUSX(wcnf, verbosity=0) as musx:
            mus = musx.compute()
            # gives back positions of the clauses !!
            return set(C[i-1] for i in mus)

    def candidate_explanations(self, U, I: set):
        candidates = []
        # kinda hacking here my way through I and C
        tstart = time.time()
        J = optimalPropagate(U=U, I=I, sat=self.sat) - I
        self.time_statisitics["prop"].append(time.time() - tstart)
        self.call_statistics["prop"] += 1

        mus_times = []
        for a in J - I:
            unsat = list(set({-a}) | I)
            tstart = time.time()
            X = self.MUSExtraction(unsat)
            mus_times.append(time.time() - tstart)
            candidates.append(X)
        self.time_statisitics["mus"].append(mus_times)
        return candidates

    def bestStep(self, f, U, I):
        Candidates = []
        cands = self.candidate_explanations(U, I)
        for cand in cands:
            cost_cand = sum(f(l) for l in cand)
            Candidates.append((cost_cand, cand))

        return min(Candidates, key=lambda cand: cand[0])

    def print_statistics(self):
        print("texpl=", round(self.time_statisitics["explain"][-1], 2), "s\n")
        # if isinstance(self, MUSExplain):
        # elif isinstance(self, OCUSExplain):
        t_explain = self.time_statisitics["explain"][-1]
        avgmus = round(sum(self.time_statisitics["mus"][-1])/len(self.time_statisitics["mus"][-1]), 2)

        print("\t propagating=", round(self.time_statisitics["prop"][-2], 2), "s")
        print("\t mus avg=",avgmus , "s")
        print("\t mus tot=",round(sum(self.time_statisitics["mus"][-1]), 2),"s")