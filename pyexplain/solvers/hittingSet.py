# gurobi imports
import gurobipy as gp
from gurobipy import GRB

class OptUxHS(object):
    def __init__(self, F, weights):
        self.allLits = list(F)
        self.nAllLits = len(self.allLits)

        # optimisation model
        self.opt_model = gp.Model('OptHittingSet')
        self.opt_model.Params.OutputFlag = 0
        self.opt_model.Params.LogToConsole = 0
        self.opt_model.Params.Threads = 1
        # VARIABLE -- OBJECTIVE
        x = self.opt_model.addMVar(
            shape=self.nAllLits,
            vtype=GRB.BINARY,
            obj=[weights[l] for l in self.allLits],
            name="x")

        self.opt_model.update()

    def addCorrectionSet(self, C: set):
        """Add new constraint of the form to the optimization model,
        mapped back to decision variable lit => x[i].

            sum x[j] * hij >= 1

        Args:
            C (set): set of assumption literals.
        """
        x = self.opt_model.getVars()

        Ci = [self.allLits.index(lit) for lit in C]

        # add new constraint sum x[j] * hij >= 1
        self.opt_model.addConstr(gp.quicksum(x[i] for i in Ci) >= 1)

    def OptHittingSet(self):
        """Compute conditional Optimal hitting set.

        Returns:
            set: Conditional optimal hitting mapped to assumption literals.
        """
        self.opt_model.optimize()
        x = self.opt_model.getVars()
        hs = set(lit for i, lit in enumerate(self.allLits) if x[i].x == 1)
        return hs

    def updateObjective(self, f, A: set):
        """Update objective of subset A {I + (-Iend\-I )}, a set of assumption
        literals s.t C u A is unsatisfiable.

        Costs of literals in A should be set to f(lit) and others not in A,
        should be set to INF.

        Args:
            f (func): A cost function mapping literal to a int cost (> 0).
            A (set): A set of assumption literals.
        """
        x = self.opt_model.getVars()
        # update the objective weights
        for xi, lit in zip(x, self.allLits):
            if lit in A:
                xi.setAttr(GRB.Attr.Obj, f(lit))
            else:
                xi.setAttr(GRB.Attr.Obj, GRB.INFINITY)
        self.opt_model.update()

    def delete(self):
        if self.opt_model:
            self.opt_model.dispose()

    def dispose(self):
        self.opt_model.dispose()


class OptHS(object):
    def __init__(self, f, F, A, best_cost=None):
        self.allLits = list(F)
        self.nAllLits = len(self.allLits)

        # optimisation model
        self.opt_model = gp.Model('OptHittingSet')
        self.opt_model.Params.OutputFlag = 0
        self.opt_model.Params.LogToConsole = 0
        self.opt_model.Params.Threads = 1
        # VARIABLE -- OBJECTIVE
        x = self.opt_model.addMVar(
            shape=self.nAllLits,
            vtype=GRB.BINARY,
            obj=[f(l) if l in A else GRB.INFINITY for l in self.allLits],
            name="x")

        if best_cost:
            self.opt_model.Params.CUTOFF = best_cost

        self.opt_model.update()

    def addCorrectionSet(self, C: set):
        """Add new constraint of the form to the optimization model,
        mapped back to decision variable lit => x[i].

            sum x[j] * hij >= 1

        Args:
            C (set): set of assumption literals.
        """
        x = self.opt_model.getVars()

        Ci = [self.allLits.index(lit) for lit in C]

        # add new constraint sum x[j] * hij >= 1
        self.opt_model.addConstr(gp.quicksum(x[i] for i in Ci) >= 1)

    def OptHittingSet(self):
        """Compute conditional Optimal hitting set.

        Returns:
            set: Conditional optimal hitting mapped to assumption literals.
        """
        self.opt_model.optimize()

        if self.opt_model.Status == GRB.OPTIMAL:
            x = self.opt_model.getVars()
            hs = set(lit for i, lit in enumerate(self.allLits) if x[i].x == 1)
            return hs
        else:
            return None

    def updateObjective(self, f, A: set):
        """Update objective of subset A {I + (-Iend\-I )}, a set of assumption
        literals s.t C u A is unsatisfiable.

        Costs of literals in A should be set to f(lit) and others not in A,
        should be set to INF.

        Args:
            f (func): A cost function mapping literal to a int cost (> 0).
            A (set): A set of assumption literals.
        """
        x = self.opt_model.getVars()
        # update the objective weights
        for xi, lit in zip(x, self.allLits):
            if lit in A:
                xi.setAttr(GRB.Attr.Obj, f(lit))
            else:
                xi.setAttr(GRB.Attr.Obj, GRB.INFINITY)
        self.opt_model.update()

    def delete(self):
        if self.opt_model:
            self.opt_model.dispose()

    def dispose(self):
        self.opt_model.dispose()


class CondOptHS(object):
    def __init__(self, U: set, Iend: set, I: set):
        """
        # Optimisation model:

        The constrained optimal hitting set is described by:

        - x_l={0,1} is a boolean decision variable if the literal is selected
                    or not.

        - w_l=f(l) is the cost assigned to having the literal in the hitting
                   set (INF otherwise).

        - c_lj={0,1} is 1 (0) if the literal l is (not) present in hitting set j.

        Objective:

             min sum(x_l * w_l) over all l in Iend + (-Iend \ -I)

        Subject to:

            (1) sum x_l * c_lj >= 1 for all hitting sets j.

                = Hitting set must hit all sets-to-hit.

            (2) sum x_l == 1 for l in (-Iend \ -I)

        Args:

            U (set): User variables over a vocabulary V

            Iend (set): Cautious consequence, the set of literals that hold in
                        all models.

            I (set): partial interpretation subset of Iend.

        """
        Iexpl = Iend - I
        notIexpl = set(-lit for lit in Iexpl)

        self.allLits = list(Iend) + list(notIexpl)
        self.nAllLits = len(self.allLits)

        # optimisation model
        self.opt_model = None
        self.opt_model = gp.Model('CondOptHittingSet')
        self.opt_model.Params.OutputFlag = 0
        self.opt_model.Params.LogToConsole = 0
        self.opt_model.Params.Threads = 1

        # VARIABLE -- OBJECTIVE
        x = self.opt_model.addMVar(
            shape=self.nAllLits,
            vtype=GRB.BINARY,
            obj=[GRB.INFINITY] * self.nAllLits,
            name="x")

        # CONSTRAINTS
        # every explanation contains 1 neg Lit.
        posnegIexpl = range(len(Iend), self.nAllLits)

        self.opt_model.addConstr(
            x[posnegIexpl].sum() == 1
        )

        # update model
        self.opt_model.update()

    def addCorrectionSet(self, C: set):
        """Add new constraint of the form to the optimization model,
        mapped back to decision variable lit => x[i].

            sum x[j] * hij >= 1

        Args:
            C (set): set of assumption literals.
        """
        x = self.opt_model.getVars()
        Ci = [self.allLits.index(lit) for lit in C]

        # add new constraint sum x[j] * hij >= 1
        self.opt_model.addConstr(gp.quicksum(x[i] for i in Ci) >= 1)

    def CondOptHittingSet(self):
        """Compute conditional Optimal hitting set.

        Returns:
            set: Conditional optimal hitting mapped to assumption literals.
        """
        self.opt_model.optimize()

        x = self.opt_model.getVars()
        hs = set(lit for i, lit in enumerate(self.allLits) if x[i].x == 1)

        return hs

    def block(self, hs):
        x = self.opt_model.getVars()
        Ci = [self.allLits.index(lit) for lit in hs]

        # add new constraint sum x[j] * hij >= 1
        self.opt_model.addConstr(gp.quicksum(x[i] for i in Ci) != len(hs))

    def updateObjective(self, f, A: set):
        """Update objective of subset A {I + (-Iend\-I )}, a set of assumption
        literals s.t C u A is unsatisfiable.

        Costs of literals in A should be set to f(lit) and others not in A,
        should be set to INF.

        Args:
            f (func): A cost function mapping literal to a int cost (> 0).
            A (set): A set of assumption literals.
        """
        x = self.opt_model.getVars()

        # update the objective weights
        for xi, lit in zip(x, self.allLits):
            if lit in A:
                xi.setAttr(GRB.Attr.Obj, f(lit))
            else:
                xi.setAttr(GRB.Attr.Obj, GRB.INFINITY)

        self.opt_model.update()

    def delete(self):
        if self.opt_model:
            self.opt_model.dispose()

    def __del__(self):
        # print("disposing")
        if self.opt_model:
            self.opt_model.dispose()

def greedyHittingSet(H, f):
    # trivial case: empty
    if len(H) == 0:
        return set()

    # the hitting set
    C = set()

    # build vertical sets
    V = dict()  # for each element in H: which sets it is in

    for i, h in enumerate(H):
        # special case: only one element in the set, must be in hitting set
        # h = hi& A
        if len(h) == 1:
            C.add(next(iter(h)))
        else:
            for e in h:
                if not e in V:
                    V[e] = set([i])
                else:
                    V[e].add(i)

    # special cases, remove from V so they are not picked again
    for c in C:
        if c in V:
            del V[c]
        if -c in V:
            del V[-c]

    while len(V) > 0:
        # special case, one element left
        if len(V) == 1:
            C.add(next(iter(V.keys())))
            break

        # get element that is in most sets, using the vertical views
        (c, cover) = max(V.items(), key=lambda tpl: len(tpl[1]))
        c_covers = [tpl for tpl in V.items() if len(tpl[1]) == len(cover)]

        if len(c_covers) > 1:
            # OMUS : find set of unsatisfiable clauses in hitting set with least total cost
            # => get the clause with the most coverage but with the least total weight
            (c, cover) = max(c_covers, key=lambda tpl: f(tpl[0]))

        del V[c]

        if -c in V:
            del V[-c]

        C.add(c)

        # update vertical views, remove covered sets
        for e in list(V):
            # V will be changed in this loop
            V[e] -= cover
            # no sets remaining with this element?
            if len(V[e]) == 0:
                del V[e]

    return C
