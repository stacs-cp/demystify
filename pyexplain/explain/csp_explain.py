from pyexplain.utils.utils import get_expl
import time
from pyexplain.solvers.bestStep import optimalPropagate
from ..solvers.params import BestStepParams, ExplanationComputer
from pysat.formula import CNF
from pysat.solvers import Solver

import json
from pathlib import Path

class CSPExplain(object):
    def __init__(self, C: CNF, verbose=0, matching_table=None):
        self.cnf = C

        self.verbose = verbose

        if self.verbose > 0:
            print("Expl:")
            print("\tcnf:", len(C.clauses), C.nv)
            print("\n\tcnf:", C.clauses)

        # Initialise the sat solver with the cnf
        self.sat = Solver(bootstrap_with=C.clauses)
        assert self.sat.solve(), f"CNF is unsatisfiable"

        # explanation sequence
        self.E = []

        # matching table
        self.matching_table = matching_table

        # initial interpretation
        self.I0 = None
        self.I = None
        self.Iend = None

        # keeping track of the statistics
        self.time_statisitics = {
            "totalTime": 0,
            "hs": [],
            "opt": [],
            "sat": [],
            "grow": [],
            "explain": [],
            "cumul_explain": [],
            "prop": [],
            "mus":[],
            "greedyBestStep":[],
            "preprocess":0,
            "preseeding":[],
            "postprocessing":[],
            "timeout": 0,
            "timedout": False
        }

        # keep track of the calls
        self.call_statistics = {
            "hs": [],
            "opt": [],
            "sat": [],
            "grow": [],
            "skipped": [],
            "prop": 0,
            "explained":0,
        }

    def bestStep(self, f, Iend, I):
        raise NotImplementedError("Please implemnt this method")

    def preprocess(self, U: set, f, I0: set, Iend: set):
        # checking everything is correct
        if self.verbose > 0:
            print("\tU:", len(U))
            print("\tf:", f)
            print("\tI0:", len(I0))
            print("\tIend:", len(Iend))

    def reset_statistics(self):
        # keeping track of the statistics
        self.time_statisitics = {
            "totalTime": 0,
            "hs": [],
            "opt": [],
            "sat": [],
            "grow": [],
            "explain": [],
            "cumul_explain": [],
            "prop": [],
            "mus":[],
            "greedyBestStep":[],
            "preprocess":0,
            "preseeding":[],
            "postprocessing":[],
            "timeout": 0,
            "timedout": False
        }

        # keep track of the calls
        self.call_statistics = {
            "hs": [],
            "opt": [],
            "sat": [],
            "grow": [],
            "skipped": [],
            "prop": 0,
            "explained":0
        }


    def explain(self, U: set, f, I0: set):
        # check literals of I are all user vocabulary
        assert all(True if abs(lit) in U else False for lit in I0), f"Part of supplied literals not in U (user variables): {lits for lit in I if lit not in U}"

        # Initialise the sat solver with the cnf
        assert self.sat.solve(assumptions=I0), f"CNF is unsatisfiable with given assumptions {I0}."

        # Explanation sequence
        self.E = []

        I0 = set(I0)
        tstart_explain = time.time()

        # Most precise intersection of all models of C project on U
        tstart = time.time()
        Iend = optimalPropagate(U=U, I=I0, sat=self.sat)
        self.time_statisitics["prop"].append(time.time() - tstart)

        # keep track of information
        tstart = time.time()
        self.preprocess(U, f, I0, Iend)
        self.time_statisitics["preprocess"] = time.time() - tstart

        I = set(I0) # copy
        while(len(Iend - I) > 0):
            # finding the next best epxlanation
            tstart = time.time()
            expl = self.bestStep(f, Iend, I)
            self.time_statisitics["explain"].append(time.time() - tstart)
            self.time_statisitics["cumul_explain"].append(time.time() - tstart_explain)

            # difficulty of explanation
            costExpl = sum(f(l) for l in expl)

            # facts & constraints used
            Ibest = I & expl

            tstart = time.time()
            # New information derived "focused" on
            Nbest = optimalPropagate(U=U, I=Ibest, sat=self.sat) - I
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
                print(f"\n\tElapsed time=", round(time.time() - tstart_explain), "s")
                print(get_expl(self.matching_table, Ibest, Nbest))

        self.time_statisitics["totalTime"] = time.time() - tstart_explain

    def print_statistics(self):
        print("texpl=", round(self.time_statisitics["explain"][-1], 2), "s\n")

    def to_json_expl(self, f, explanation):
        constraints = list(explanation["constraints"])
        derived = list(explanation["derived"])

        json_explanation = {
            "cost": sum(f(l) for l in constraints),
            "clue": None,
            "assumptions": [],
            "derivations": []
        }

        for fact in derived:
            json_fact = self.matching_table['bvRel'][abs(fact)]
            json_fact["value"] = True if fact > 0 else False
            json_explanation["derivations"].append(json_fact)

        clue = []
        nTrans = 0
        nBij = 0
        nClue = 0

        for c in constraints:
            if(c in self.matching_table['Transitivity constraint']):
                nTrans += 1
            elif(c in self.matching_table['Bijectivity']):
                nBij += 1
            elif(c in self.matching_table['clues']):
                nClue += 1
                clue.append(self.matching_table['clues'][c])
            else:
                json_fact = self.matching_table['bvRel'][abs(c)]
                json_fact["value"] = True if c > 0 else False
                json_explanation["assumptions"].append(json_fact)


        if nClue == 0:
            if nTrans == 0 and nBij == 1:
                json_explanation["clue"] = "Bijectivity"
            elif nTrans == 1 and nBij == 0:
                json_explanation["clue"] = "Transitivity constraint"
            else:
                json_explanation["clue"] = "Combination of logigram constraints"
        elif nClue == 1:
            if nTrans + nBij >= 1:
                json_explanation["clue"] = "Clue and implicit Constraint"
            else:
                json_explanation["clue"] = clue[0]
        else:
            json_explanation["clue"] = "Multiple clues"

        return json_explanation


    def export_explanations(self, f, fname):
        assert self.matching_table is not None, "Matching table for explanations not available"

        if not Path(fname).parent.exists():
            Path(fname).parent.mkdir()

        file_path = Path(fname)
        json_explanations = []

        for explanation in self.E:
            json_explanation = self.to_json_expl(f, explanation)
            json_explanations.append(json_explanation)

        with file_path.open('w') as fp:
            json.dump(json_explanations, fp, indent=2)

    def export_statistics(self, params: BestStepParams=None, fname=""):
        if fname == "":
            return

        json_statistics = {
            "time": self.time_statisitics,
            "numbers": self.call_statistics,
            "explanation": self.E,
            'params': params.to_dict() if params is not None else dict()
        }
        print(fname)
        if not Path(fname).parent.exists():
            Path(fname).parent.mkdir(parents=True)

        file_path = Path(fname)

        with file_path.open('w') as f:
            json.dump(json_statistics, f)


    def __del__(self):
        if hasattr(self, 'sat') and self.sat:
            self.sat.delete()
