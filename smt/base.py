import itertools

from typing import Sequence

from .utils import flatten

# Represent 'var == val'
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
        return (self.var, self.val, self.equal) == (other.var, other.val, other.equal)
    
    def __hash__(self):
        return (self.var, self.val, self.equal).__hash__()

    def neg(self):
        return Lit(self.var, self.val, not self.equal)

def EqVal(var, val: int) -> Lit:
    return Lit(var, val, True)

def NeqVal(var, val: int) -> Lit:
    return Lit(var, val, False)

class Clause:
    def __init__(self, name:str, clause:Sequence[str], clausenames=None):
        self._name = name
        self._clause = clause
        self._clausenames = clausenames
        self._frozen = frozenset([frozenset(self._clause)])

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

    def __eq__(self, other):
        return self.clauseset() == other.clauseset()

    def __hash__(self):
        return self.clauseset().__hash__()

class ClauseList:
    def __init__(self, name, clauses):
        self._name = name
        self._clauses = frozenset([frozenset(c) for c in clauses])

    def explain(self, _):
        return self._name

    def clauseset(self):
        return self._clauses

    def __eq__(self, other):
        return self.clauseset() == other.clauseset()

    def __hash__(self):
        return self.clauseset().__hash__()

# Constraints to say each variable takes a single value
def cellHasValue(var,dom):
    clauses = []
    clauses.append(
        Clause(
            "{} must have some value".format(var),
            [EqVal(var, d) for d in dom],
            [str(d) for d in dom],
        )
    )

    for (d1,d2) in itertools.combinations(dom, 2):
        clauses.append(
            Clause(
                "{} cannot be both {} and {}".format(var, d1, d2),
                [NeqVal(var, d1), NeqVal(var, d2)],
            )
        )

    return clauses

class Var:
    def __init__(self, name:str, dom:Sequence[int]):
        self._dom = dom
        #self._lits = {k:Bool("{} is {}".format(name,k)) for k in dom}
        self._name = str(name)
    
    def dom(self):
        return self._dom

    # partial allows some variables to be unassigned
    def modelToAssignment(self, model, partial=False):
        lits = [k for k in self._dom if EqVal(self, k) in model]
        # Nothing should ever be assigned more than once!
        assert len(lits) <= 1
        if partial:
            if len(lits) > 0:
                return lits[0]
            else:
                return None

        # Sanity check: Only one thing in a variable should be defined in a solution
        assert len(lits) == 1
        return lits[0]

    def assignmentToModel(self, assignment):
        if assignment is None:
            return []
        else:
            assert assignment in self._dom
            return EqVal(self, assignment)

    def __repr__(self):
        return self._name

class VarMatrix:
    def __init__(self, varname, dim, dom):
        self.varname = varname
        self._dim = dim
        self._domain = tuple(dom)
        self._vars = [[Var(varname((i,j)), dom) for j in range(dim[1])] for i in range(dim[0])]
        self._constraints = flatten([cellHasValue(v, dom) for v in flatten(self._vars)])

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
        return [[var.modelToAssignment(model, partial) for var in row] for row in self._vars]

    def assignmentToModel(self, assignment):
        return [[var.assignmentToModel(avar) for (var,avar) in zip(row,arow)] for (row, arow) in zip(self._vars, assignment)]


class Puzzle:
    def __init__(self, vars):
        # The variables of the problem (as a list of matrices)
        self._vars = vars
        # The Clause / Clause Sets
        self._constraints = []
        # A place where we store the added constraints as a set. This
        # lets us filter out any repeats. This is not required for
        # correctness, but improves efficiency greatly
        self._constraintset = set()

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


    def modelToAssignment(self, model, partial = False):
        return [v.modelToAssignment(model, partial) for v in self._vars]

    def assignmentToModel(self, assignment):
        return flatten([v.assignmentToModel(a) for (v,a) in zip(self._vars, assignment)])
