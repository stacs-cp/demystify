from .optux import OptUx

from pysat.examples.hitman import Hitman
from pysat.examples.rc2 import RC2
from pysat.formula import WCNFPlus
from pysat.solvers import Solver

import multiprocessing as mp

"""
    Reimplementing some of the methods of the OptUx optimal MUS extractor to 
    adapt it for repeated uses. Further optimisation of this should be possible
    (TODO).
"""


class OptUxExt(OptUx):
    def __init__(
        self,
        formula,
        verbose=0,
        solver="g3",
        adapt=False,
        exhaust=False,
        minz=False,
        trim=False,
        maxSize=float("inf"),
    ):
        """
        Constructor.
        """
        # verbosity level
        self.verbose = verbose

        # constructing a local copy of the formula
        self.formula = WCNFPlus()
        self.formula.hard = formula.hard[:]
        self.formula.wght = formula.wght[:]
        self.formula.topw = formula.topw
        self.formula.nv = formula.nv

        self.known = []
        self.assume = []
        self.maxSize = maxSize

        # top variable identifier
        self.topv = formula.nv

        # processing soft clauses
        self._process_soft(formula)
        self.formula.nv = self.topv

        # creating an unweighted copy
        unweighted = self.formula.copy()
        unweighted.wght = [1 for w in unweighted.wght]

        # hitting set enumerator
        self.hitman = Hitman(
            weights=self.weights,
            solver=solver,
            htype="sorted",
            mxs_adapt=adapt,
            mxs_exhaust=exhaust,
            mxs_minz=minz,
            mxs_trim=trim,
        )

        # SAT oracle bootstrapped with the hard clauses
        self.oracle = Solver(name=solver, bootstrap_with=unweighted.hard)

        # Also create the RC2 solver at this point.
        self.maxSATOracle = RC2(
            unweighted,
            incr=True,
            solver=solver,
            adapt=adapt,
            exhaust=exhaust,
            minz=minz,
            trim=trim,
            verbose=0,
        )

    def initialise(self, assume, known, maxSize=float("inf")):
        """
        Set up for the FORQES algorithm: some of which was original done in
        __init__ but now needs to be re-done repeatedly.
        """
        unweighted = self.formula.copy()

        self.known = known
        self.assume = assume
        self.maxSize = maxSize

        for assumption in assume:
            unweighted.append([assumption])

        for knownlit in known:
            unweighted.append([knownlit])

        unweighted.wght = [1 for w in unweighted.wght]

        # Pipe objects to get return values from forked processes.
        parent_pipe, child_pipe = mp.Pipe()

        # Fork a process for enumerating disjoint MCSes
        # (including unit-size MCSes), so that we don't need to recreate the
        # RC2 solver.
        disjoint = mp.Process(
            target=self._disjoint, args=(assume, known, child_pipe)
        )

        disjoint.start()
        res = parent_pipe.recv()
        disjoint.join()

        to_hit = res[0]
        self.units = res[1]
        success = res[2]

        if success == 1:
            return False

        if self.verbose > 2:
            print(
                "c mcses: {0} unit, {1} disj".format(
                    len(self.units), len(to_hit) + len(self.units)
                )
            )

        self.hitman.init(to_hit, weights=self.weights)
        return True

    def _disjoint(self, assume, known, pipe):
        # these will store disjoint MCSes
        # (unit-size MCSes are stored separately)
        to_hit, units = [], []

        for assumption in assume:
            self.maxSATOracle.add_clause([assumption])

        for knownlit in known:
            self.maxSATOracle.add_clause([knownlit])

        # iterating over MaxSAT solutions
        while True:
            # a new MaxSAT model
            model = self.maxSATOracle.compute()

            if model is None:
                # no model => no more disjoint MCSes
                break

            # extracting the MCS corresponding to the model
            falsified = list(
                filter(lambda l: model[abs(l) - 1] == -l, self.sels)
            )

            # unit size or not?
            if len(falsified) > 1:
                to_hit.append(falsified)
            else:
                units.append(falsified[0])

            # blocking the MCS;
            # next time, all these clauses will be satisfied
            for l in falsified:
                self.maxSATOracle.add_clause([l])

            if len(to_hit) > self.maxSize:
                pipe.send(([], [], 1))
                pipe.close()
                return

            # reporting the MCS
            if self.verbose > 3:
                print(
                    "c mcs: {0} 0".format(
                        " ".join([str(self.smap[s]) for s in falsified])
                    )
                )

        # RC2 will be destroyed next; let's keep the oracle time
        self.disj_time = self.maxSATOracle.oracle_time()

        pipe.send((to_hit, units, 0))
        pipe.close()
        return

    def compute(self):
        """
        This method implements the main look of the implicit hitting set
        paradigm of Forqes to compute a best-cost MUS. The result MUS is
        returned as a list of integers, each representing a soft clause
        index. This extended version takes additional assumptions for the
        purposes of Demystify.
        """
        while True:
            # computing a new optimal hitting set
            hs = self.hitman.get()

            if hs is None:
                # no more hitting sets exist
                break
            if len(hs) > self.maxSize:
                return False

            # setting all the selector polarities to true
            self.oracle.set_phases(self.sels)

            # testing satisfiability of the {self.units + hs} subset
            res = self.oracle.solve(
                assumptions=hs + self.assume + self.known + self.units
            )

            if res == False:
                # the candidate subset of clauses is unsatisfiable,
                # i.e. it is an optimal MUS we are searching for;
                # therefore, blocking it and returning
                self.hitman.block(hs)
                self.cost = self.hitman.oracle.cost + len(self.units)
                return sorted(map(lambda s: self.smap[s], self.units + hs))
            else:
                # the candidate subset is satisfiable,
                # thus extracting a correction subset
                model = self.oracle.get_model()
                cs = list(filter(lambda l: model[abs(l) - 1] == -l, self.sels))

                # hitting the new correction subset
                self.hitman.hit(cs, weights=self.weights)
