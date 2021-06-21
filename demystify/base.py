import itertools
import functools


from typing import Sequence

from .utils import flatten

from .config import CONFIG

from sortedcontainers import *


# Represent 'var == val'
@functools.total_ordering
class Lit:
    def __init__(self, var, val: int, equal: bool):
        self.var = var
        self.val = val
        self.equal = equal

    def __repr__(self) -> str:
        if self.equal:
            return "{} is {}".format(self.var, self.val)
        else:
            return "{} is not {}".format(self.var, self.val)

    def __eq__(self, other) -> bool:
        return (self.var, self.val, self.equal) == (
            other.var,
            other.val,
            other.equal,
        )

    def __lt__(self, other) -> bool:
        return (self.var, self.val, self.equal) < (
            other.var,
            other.val,
            other.equal,
        )

    def __hash__(self):
        return (self.var, self.val, self.equal).__hash__()

    def neg(self):
        return Lit(self.var, self.val, not self.equal)


def EqVal(var, val: int) -> Lit:
    return Lit(var, val, True)


def NeqVal(var, val: int) -> Lit:
    return Lit(var, val, False)


class DummyClause:
    def __init__(self, name: str, clause: Sequence[str], clausenames=None):
        self._name = name
        self._clause = clause
        self._clausenames = clausenames
        self._frozen = tuple([tuple(sorted(self._clause))])
        self._lits = tuple(SortedSet(flatten(self._frozen)))

    def explain(self, knownvars):
        if self._clausenames is None:
            return self._name

        remainingchoices = []

        for i in range(len(self._clause)):
            if self._clause[i].neg() not in knownvars:
                remainingchoices.append(self._clausenames[i])

        exp = self._name + " (Choices are: " + ", ".join(remainingchoices) + ")"

        return exp

    def clauseset(self):
        return self._frozen

    def lits(self):
        return self._lits

    def __eq__(self, other):
        return self._name == other._name

    def __hash__(self):
        return self._name.__hash__()

    def __lt__(self, other):
        return self._name < other._name

    def __repr__(self):
        return self._name + "!"


class Clause:
    def __init__(self, name: str, clause: Sequence[str], clausenames=None):
        self._name = name
        self._clause = clause
        self._clausenames = clausenames
        self._frozen = tuple([tuple(sorted(self._clause))])
        self._lits = tuple(SortedSet(flatten(self._frozen)))

    def explain(self, knownvars):
        if self._clausenames is None:
            return self._name

        remainingchoices = []

        for i in range(len(self._clause)):
            if self._clause[i].neg() not in knownvars:
                remainingchoices.append(self._clausenames[i])

        exp = self._name + " (Choices are: " + ", ".join(remainingchoices) + ")"

        return exp

    def clauseset(self):
        return self._frozen

    def lits(self):
        return self._lits

    def __eq__(self, other):
        return self.clauseset() == other.clauseset()

    def __hash__(self):
        return self.clauseset().__hash__()

    def __lt__(self, other):
        return self.clauseset() < other.clauseset()

    def __repr__(self):
        return self._name + ":" + str(self.clauseset())


class ClauseList:
    def __init__(
        self, name, clauses, usedlits=None, namelits=None, fromClauses=False
    ):
        self._name = name
        if fromClauses:
            self._clauses = tuple(
                sorted(itertools.chain([c.clauseset() for c in clauses]))
            )
        else:
            self._clauses = tuple(sorted([tuple(sorted(c)) for c in clauses]))

        self._usedlits = usedlits
        self._namelits = namelits

        self._lits = tuple(sorted(flatten(self._clauses)))

    def explain(self, knownvars):
        if self._usedlits is None:
            return self._name

        remainingchoices = []
        for i in range(len(self._usedlits)):
            if self._usedlits[i].neg() not in knownvars:
                remainingchoices.append(self._namelits[i])

        return (
            self._name + " (Choices are: " + ", ".join(remainingchoices) + ")"
        )

    def clauseset(self):
        return self._clauses

    def lits(self):
        return self._lits

    def __eq__(self, other):
        return self.clauseset() == other.clauseset()

    def __hash__(self):
        return self.clauseset().__hash__()

    def __lt__(self, other):
        return self.clauseset() < other.clauseset()

    def __repr__(self):
        return self._name + ": ".join([str(c) for c in self.clauseset()])


# Constraints to say each variable takes a single value
def cellHasValue(var, dom):
    clauses = []
    clauses.append(
        Clause(
            "{} must have some value".format(var),
            [EqVal(var, d) for d in dom],
            [str(d) for d in dom],
        )
    )

    if CONFIG["OneClauseAtMost"]:
        for v in dom:
            clauses.append(
                ClauseList(
                    "{} cannot take more than one value".format(var),
                    [
                        [NeqVal(var, d1), NeqVal(var, d2)]
                        for (d1, d2) in itertools.combinations(dom, 2)
                    ],
                    [EqVal(var, d) for d in dom],
                    [str(d) for d in dom],
                )
            )
    else:
        for (d1, d2) in itertools.combinations(dom, 2):
            clauses.append(
                Clause(
                    "{} cannot be both {} and {}".format(var, d1, d2),
                    [NeqVal(var, d1), NeqVal(var, d2)],
                )
            )

    return clauses


@functools.total_ordering
class Var:
    def __init__(self, name: str, dom: Sequence[int], location):
        self._dom = dom
        self._name = str(name)
        self._location = location

    def dom(self):
        return self._dom

    # partial allows some variables to be unassigned
    def modelToAssignment(self, model, partial=False):
        poslits = [k for k in self._dom if EqVal(self, k) in model]
        neglits = [k for k in self._dom if NeqVal(self, k) in model]

        # Nothing should ever be assigned more than once!
        assert len(poslits) <= 1
        if partial:
            # If assigned return that, else return values not yet
            # removed
            if len(poslits) > 0:
                return poslits

            nonneg = [k for k in self._dom if not (k in neglits)]
            if len(nonneg) > 0:
                return nonneg
            else:
                return self._dom

        # Sanity check: Only one thing in a variable should be defined in a solution
        assert len(poslits) == 1
        return poslits[0]

    def assignmentToModel(self, assignment, partial=False):
        if assignment is None:
            return []
        else:
            if partial == False:
                assert assignment in self._dom
                return EqVal(self, assignment)
            else:
                assert SortedSet(assignment).issubset(SortedSet(self._dom))
                lits = [
                    NeqVal(self, d) for d in self._dom if not (d in assignment)
                ]
                if len(assignment) == 1:
                    lits.append([EqVal(self, assignment[0])])
                return lits

    def __repr__(self):
        return self._name

    def __eq__(self, other):
        return self._name == other._name

    def __lt__(self, other):
        return self._name < other._name

    def __hash__(self):
        return self._name.__hash__()


class VarMatrix:
    def __init__(self, varname, dim, dom, *, varmat=None):
        self.varname = varname
        self._dim = dim
        self._domain = tuple(dom)
        if varmat is None:
            self._vars = [
                [Var(varname((i, j)), dom, (i, j)) for j in range(dim[1])]
                for i in range(dim[0])
            ]
        else:
            self._vars = varmat
        self._constraints = flatten(
            [cellHasValue(v, dom) for v in flatten(self._vars)]
        )

    def varmat(self):
        return self._vars

    def varlist(self):
        return flatten(self._vars)

    def domain(self):
        return self._domain

    def dim(self):
        return self._dim

    def xdim(self):
        return self._dim[0]

    def ydim(self):
        return self._dim[1]

    # Simple wrapper
    def __getitem__(self, arg):
        return self._vars[arg]

    def constraints(self):
        return self._constraints

    def modelToAssignment(self, model, partial=False):
        return [
            [var.modelToAssignment(model, partial) for var in row]
            for row in self._vars
        ]

    def assignmentToModel(self, assignment, partial=False):
        return [
            [
                var.assignmentToModel(avar, partial)
                for (var, avar) in zip(row, arow)
            ]
            for (row, arow) in zip(self._vars, assignment)
        ]


class SavileRowVars:
    def __init__(self, vars):
        self._vars = [vars]

    def varmat(self):
        return self._vars

    def modelToAssignment(self, model, partial=False):
        return [
            [var.modelToAssignment(model, partial) for var in row]
            for row in self._vars
        ]

    def assignmentToModel(self, assignment, partial=False):
        return [
            [
                var.assignmentToModel(avar, partial)
                for (var, avar) in zip(row, arow)
            ]
            for (row, arow) in zip(self._vars, assignment)
        ]


class Puzzle:
    def __init__(self, vars):
        # The variables of the problem (as a list of matrices)
        self._vars = vars
        # The Clause / Clause Sets
        self._constraints = []
        # A place where we store the added constraints as a SortedSet. This
        # lets us filter out any repeats. This is not required for
        # correctness, but improves efficiency greatly
        self._constraintset = SortedSet()

    def addConstraint(self, constraint):
        cset = constraint.clauseset()
        if cset in self._constraintset:
            return False
        self._constraintset.add(cset)
        self._constraints.append(constraint)

    def addConstraints(self, constraints):
        for c in constraints:
            self.addConstraint(c)

    def constraints(self):
        return self._constraints

    def vars(self):
        return self._vars

    def modelToAssignment(self, model, partial=False):
        return [v.modelToAssignment(model, partial) for v in self._vars]

    def assignmentToModel(self, assignment, partial=False):
        return flatten(
            [
                v.assignmentToModel(a, partial)
                for (v, a) in zip(self._vars, assignment)
            ]
        )
