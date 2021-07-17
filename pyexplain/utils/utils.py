from .exceptions import CostFunctionError


def add_assumptions(cnf):
    flat = set(abs(i) for lst in cnf for i in lst)
    max_lit = max(flat)

    cnf_ass = []
    assumptions = []
    for id, cl in enumerate(cnf):
        ass = max_lit + id + 1
        cl.append(-ass)
        assumptions.append(ass)
        cnf_ass.append(cl)

    return cnf_ass, assumptions


def get_expl(matching_table, Ibest, Nbest=None):
    if matching_table is None:
        return

    s = ""
    if not 'Transitivity constraint' in matching_table:
        s = " /\\ ".join([matching_table[i] for i in Ibest])
        if Nbest:
            s += " =>" + ", ".join([matching_table[i] for i in Nbest])
            s = "\nOptimal Explanation:\n--------------------\n\t"+ s
    else:
        for i in Ibest:
            if(i in matching_table['Transitivity constraint']):
                s+= "trans: " + str(i) + "\n"
            elif(i in matching_table['Bijectivity']):
                s+= "bij: " + str(i) + "\n"
                print("bij", i)
            elif(i in matching_table['clues']):
                s+= "clues n°"+ matching_table['clues'][i] + "\n"
            else:
                s+= "Fact: " + str(i) + "\n"
    return s


def get_user_vars(cnf):
    """Flattens cnf into list of different variables.

    Args:
        cnf (CNF): CNF object

    Returns:
        set: lits of variables present in cnf.
    """
    U = set(abs(l) for lst in cnf.clauses for l in lst)
    return U


def cost_puzzle(U, I, cost_clue):
    """
    U = user variables
    I = initial intepretation

    bij/trans/clues = subset of user variables w/ specific cost.
    """
    litsU = set(abs(l) for l in U) | set(-abs(l) for l in U)
    assert all(i in U or -i in U for i in I), "Making sure all literals are in user defined variables"

    def cost_lit(lit):
        if lit not in litsU:
            raise CostFunctionError(U, lit)
        elif lit in cost_clue:
            return cost_clue[lit]
        else:
            # lit in
            return 1

    return cost_lit


def cost(U, I):
    litsU = set(abs(l) for l in U) | set(-abs(l) for l in U)
    I0 = set(I)

    def cost_lit(lit):
        if lit not in litsU:
            raise CostFunctionError(U, lit)
        elif lit in I0 or -lit in I0:
            return 20
        else:
            return 1

    return cost_lit

