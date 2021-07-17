import time
from pyexplain.solvers.bestStep import BestStepComputer
from pyexplain.solvers.hittingSet import OptHS
from pysat.formula import CNF
from pyexplain.explain.csp_explain import CSPExplain
from pyexplain.solvers.params import BestStepParams


class GreedyExplain(CSPExplain, BestStepComputer):
    def __init__(self, C: CNF, params: BestStepParams, verbose=False, matching_table=None):
        CSPExplain.__init__(self, C=C, verbose=verbose, matching_table=matching_table)
        BestStepComputer.__init__(self, cnf=C, sat=self.sat,params=params)
        self.SSes = None
        self.best_costs = None

    def preprocess(self, U:set, f, I0: set, Iend: set):
        # initialise data structures for tracking of information
        self.SSes = set()
        self.I0 = set(I0)
        self.Iend = set(Iend)
        self.best_costs = dict()

        # initialize costs
        Xbest = I0 | {-l for l in  Iend - I0}
        f_xbest = sum(f(l) for l in Xbest)

        # pre-compute the best cost
        for l in Iend - I0:
            # initialising the best cost
            self.best_costs[l] = f_xbest

        # end-interperation
        self.fullSS = set(Iend)

    def bestStep(self, f, Iend, I: set):
        bestExpl, bestLit = None, None
        self.I = set(I)

        # best cost
        remaining = list(Iend - I)
        for i in I:
            if i in self.best_costs:
                del self.best_costs[i]

        if self.params.sort_literals:
            remaining.sort(key=lambda l: self.best_costs[l])

        bestCost = min(self.best_costs.values())

        skipped = 0
        t_greedyBestStep = []
        self.time_statisitics["opt"].append([])
        self.time_statisitics["sat"].append([])
        self.time_statisitics["grow"].append([])

        self.call_statistics["hs"].append([])
        self.call_statistics["opt"].append([])
        self.call_statistics["sat"].append([])
        self.call_statistics["grow"].append([])

        for id, l in enumerate(remaining):
            # print(f"OUS lit {id+1}/{len(remaining)+1}", flush=True, end='\r')
            # initialising the best cost
            F = I | {-l, l}

            # expl is None when cutoff (timeout or cost exceeds current best Cost)
            A = I | set({-l})

            tbestStep = time.time()
            expl, costExpl = self.bestStepOUS(f, F=F, A=A)
            t_greedyBestStep.append(time.time() - tbestStep)

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

        # literal already found, remove its cost
        del self.best_costs[bestLit]

        if self.verbose > 0:
            print('\t Average time to explanation=', round(sum(t_greedyBestStep)/len(t_greedyBestStep), 2), "s")

        # statistics
        self.call_statistics["skipped"].append(skipped)
        self.time_statisitics["greedyBestStep"].append(t_greedyBestStep)

        return bestExpl

    def process_SSes(self, H):
        self.SSes |= H

        # post-processing the MSSes
        keep = set()
        for m1 in self.SSes:
            keep_m1 = True
            for m2 in self.SSes:
                if m1 != m2 and m1 < m2:
                    keep_m1 = False
            if keep_m1:
                keep.add(m1)
        self.SSes = keep

    def bestStepOUS(self, f, F, A, best_cost=None):
        # initial running varaibles
        nHS, nOPT, nSAT, nGROW  = 0, 0, 0, 0

        # time spent
        t_opt,t_sat,t_grow  = [], [], []

        H, HS, C, SSes = set(), set(), set(), set()

        # initial best cost
        bestCost = min(self.best_costs.values())

        # Start with OPTIMISATION mode

        # OPTIMISATION MODEL
        self.hittingset_solver = OptHS(f, F, A, best_cost)

        # lit to explain!
        lit_expl = next(iter(F - A))
        tpreseed = time.time()
        if self.params.reuse_SSes:
            for SS in self.SSes:
                if SS.issubset(self.fullSS):
                    continue

                if lit_expl not in SS or -lit_expl not in SS:
                    continue

                ss = SS & F

                if any(ss.issubset(MSS) for MSS in SSes):
                    continue

                C = F - ss

                if C not in H:
                    nHS += 1
                    H.add(C)
                    SSes.append(ss)
                    self.hittingset_solver.addCorrectionSet(C)

        self.time_statisitics["preseeding"].append(time.time() - tpreseed)

        while(True):
            topt = time.time()

            HS = self.hittingset_solver.OptHittingSet()
            print("HS=",HS)
            t_opt.append(time.time() -topt)
            nOPT += 1
            nHS += 1

            tsat = time.time()
            sat, HSModel = self.checkSat(HS, phases=self.Iend)
            t_sat.append(time.time() -tsat)
            nSAT += 1

            costHS = sum(f(l) for l in HS)

            # cut the search if cost exceeds treshold
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
                return None, costHS

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
                # cleaning up!
                self.hittingset_solver.dispose()

                #postprocessing
                if self.params.reuse_SSes:
                    tpost = time.time()
                    self.process_SSes(SSes)
                    self.time_statisitics["postprocessing"].append(time.time() - tpost)

                return HS, costHS

            tgrow = time.time()
            SS = self.grow(f=f, A=A, HS=HS, HS_model=HSModel)
            print("SS=",SS)
            
            t_grow.append(time.time() - tgrow)
            nGROW += 1

            C = F - SS
            print("F-SS", C)
            H.add(frozenset(C))
            self.hittingset_solver.addCorrectionSet(C)

            if self.params.reuse_SSes:
                SSes.add(frozenset(SS))

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

        # POSTprocessing time!
        if len(self.time_statisitics["postprocessing"]) > 0:
            t_post_processing = self.time_statisitics["postprocessing"][-1]
            t_post_explain =  round(t_post_processing /t_explain*100)
            print("\t post =", round(t_post_processing, 2), f"\t[{t_post_explain}%]\t")