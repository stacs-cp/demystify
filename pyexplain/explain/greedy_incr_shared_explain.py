import time
from pysat.formula import CNF
from pyexplain.solvers.params import OusIncrSharedParams
from pyexplain.solvers.bestStep import BestStepComputer
from pyexplain.solvers.hittingSet import OptHS
from pyexplain.explain.csp_explain import CSPExplain


class GreedyIncrSharedExplain(CSPExplain, BestStepComputer):
    def __init__(self, C: CNF, params: OusIncrSharedParams, verbose=True, matching_table=None):
        CSPExplain.__init__(self, C=C, verbose=verbose, matching_table=matching_table)
        BestStepComputer.__init__(self, cnf=C, sat=self.sat,params=params)

    def preprocess(self, U:set, f, I0: set, Iend: set):
        # initial values
        self.I0 = set(I0)
        self.Iend = Iend

        # initialise data structures for tracking of information
        self.best_costs = dict()
        self.opt_solvers = dict()

        # initialize costs
        Xbest = I0 | {-l for l in  Iend - I0}
        f_xbest = sum(f(l) for l in Xbest)

        # pre-compute the best cost
        for l in Iend - I0:
            # initialising the best cost
            self.best_costs[l] = f_xbest
            F = Iend | set(-l for l in Iend - I0)

            # setup opitmisation model
            self.opt_solvers[l] = OptHS(f, F, I0)

    def bestStep(self, f, Iend: set, I: set):
        bestExpl, bestLit = None, None

         # update interpretation
        self.I = set(I)

        # best cost
        remaining = list(Iend - I)

        # making sure that opt models are removed
        for i in I.intersection(self.best_costs):
            del self.best_costs[i]
            # delete optimisation model

            self.opt_solvers[i].delete()
            del self.opt_solvers[i]

        if self.params.sort_literals:
            remaining.sort(key=lambda l: self.best_costs[l])

        skipped = 0
        t_greedyBestStep = []

        bestCost = min(self.best_costs.values())

        # all satisfiable subsets found!
        all_sat_subsets = []
        self.time_statisitics["opt"].append([])
        self.time_statisitics["sat"].append([])
        self.time_statisitics["grow"].append([])

        self.call_statistics["hs"].append([])
        self.call_statistics["opt"].append([])
        self.call_statistics["sat"].append([])
        self.call_statistics["grow"].append([])

        # initialising the best cost
        F = I | {-l for l in Iend - I} | {l for l in Iend - I}

        for id, l in enumerate(remaining):
            # print(f"OUS lit {id+1}/{len(remaining)+1}")

            # active optimisation model
            self.hittingset_solver = self.opt_solvers[l]

            A = I | set({-l})

            # expl is None when cutoff (timeout or cost exceeds current best Cost)
            tbestStep = time.time()
            expl, costExpl, sat_subsets = self.bestStepOUSIncrNaive(f, F=F, A=A)
            t_greedyBestStep.append(time.time() - tbestStep)

            # keep the sat_subsets
            all_sat_subsets += [(l, sat_subset) for sat_subset in sat_subsets]

            if expl is None:
                skipped += 1
                continue

            # can only keep the costs of the optHittingSet computer
            if costExpl < self.best_costs[l]:
                self.best_costs[l] = costExpl

            # store explanation
            if costExpl <= bestCost:
                bestExpl = expl
                bestLit = l
                bestCost = costExpl

        # post-process satisfiable subsets
        # optimal propagate it ?

        for l in remaining:
            if l == bestLit:
                continue

            for li, sat_subset in all_sat_subsets:
                # don't add SS twice
                if li == l:
                    continue

                C = F - sat_subset
                self.opt_solvers[l].addCorrectionSet(C)

        # literal already found, remove its cost
        del self.best_costs[bestLit]

        # delete optimisation model
        self.opt_solvers[bestLit].delete()
        del self.opt_solvers[bestLit]

        # statistics
        self.call_statistics["skipped"].append(skipped)
        self.time_statisitics["greedyBestStep"].append(t_greedyBestStep)

        return bestExpl

    def bestStepOUSIncrNaive(self, f, F, A):
        assert self.hittingset_solver is not None, "Making sure model ok!"
        nHS, nOPT, nSAT, nGROW  = 0, 0, 0, 0

        # time spent
        t_opt,t_sat,t_grow  = [], [], []

        # update weights
        self.hittingset_solver.updateObjective(f, A)

        #keeping track of satisfibale subsets
        sat_subsets = list()

        # initial best cost
        bestCost = min(self.best_costs.values())

        while(True):
            # Optimal Hitting set
            topt = time.time()
            HS = self.hittingset_solver.OptHittingSet()
            t_opt.append(time.time() -topt)

            nHS += 1
            nOPT += 1

            tsat = time.time()

            # CHECKING SATISFIABILITY
            sat, HS_model = self.checkSat(HS, phases=self.Iend)

            t_sat.append(time.time() -tsat)

            nSAT += 1

            costHS = sum(f(l) for l in HS)

            if costHS > bestCost:
                # call statistics
                self.call_statistics["hs"][-1].append(nHS)
                self.call_statistics["opt"][-1].append(nOPT)
                self.call_statistics["sat"][-1].append(nSAT)
                self.call_statistics["grow"][-1].append(nGROW)
                # timings
                self.time_statisitics["opt"][-1].append(t_opt)
                self.time_statisitics["grow"][-1].append(t_grow)
                self.time_statisitics["sat"][-1].append(t_sat)
                return None, costHS, sat_subsets

            # OUS FOUND?
            if not sat:
                # call statistics
                self.call_statistics["hs"][-1].append(nHS)
                self.call_statistics["opt"][-1].append(nOPT)
                self.call_statistics["sat"][-1].append(nSAT)
                self.call_statistics["grow"][-1].append(nGROW)
                # timings
                self.time_statisitics["opt"][-1].append(t_opt)
                self.time_statisitics["grow"][-1].append(t_grow)
                self.time_statisitics["sat"][-1].append(t_sat)
                return HS, costHS, sat_subsets

            tgrow = time.time()
            SS = self.grow(f=f, A=A, HS=HS, HS_model=HS_model)
            t_grow.append(time.time() - tgrow)
            nGROW += 1

            # compute the complement
            C = F - SS
            self.hittingset_solver.addCorrectionSet(C)

            # keeping track of subsets
            sat_subsets.append(SS)

    def print_statistics(self):
        super().print_statistics()
        t_explain = self.time_statisitics["explain"][-1]

        # opt: list[list[time]]
        t_opt = self.time_statisitics["opt"][-1]
        t_opt_explain = round(sum(sum(x) for x in t_opt)/t_explain*100)
        t_call_opt = round(sum(sum(x) for x in t_opt)/sum(len(x) for x in t_opt), 3)
        print("\t opt =", round(sum(sum(x) for x in t_opt),2),f"s\t[{t_opt_explain}%]\t",  t_call_opt, "[s/call]")


        # grow: list[list[time]]
        t_grow = self.time_statisitics["grow"][-1]
        # if grow is skipped! because hs is immediatly unsat
        if len(t_grow) > 0:
            t_grow_explain = round(sum(sum(x) for x in t_grow)/t_explain*100)
            t_call_grow = round(sum(sum(x) for x in t_grow)/sum(len(x) for x in t_grow), 3)
            print("\t grow =", round(sum(sum(x) for x in t_grow),2),f"s\t[{t_grow_explain}%]\t",  t_call_grow, "[s/call]")

        # sat: list[list[time]]
        t_sat = self.time_statisitics["sat"][-1]
        t_sat_explain = round(sum(sum(x) for x in t_sat)/t_explain*100)
        t_call_sat = round(sum(sum(x) for x in t_sat)/sum(len(x) for x in t_sat), 3)
        print("\t sat =", round(sum(sum(x) for x in t_sat),2),f"s\t[{t_sat_explain}%]\t",  t_call_sat, "[s/call]")
