import math

from itertools import combinations
from smt.base import *
from smt.utils import intsqrt

def buildCage(name, cells, dom):
    constraints = []
    for i1 in range(len(cells)):
        for i2 in range(i1 + 1, len(cells)):
            c1 = cells[i1]
            c2 = cells[i2]
            for v in dom:
                constraints.append(
                    Clause(
                        "{} and {} cannot both be {} as they are both in {}".format(
                            c1, c2, v, name
                        ),
                        [NeqVal(c1,v),NeqVal(c2,v)],
                    )
                )

    for v in dom:
        constraints.append(
            Clause(
                "Some cell in {} must be {}".format(name, v),
                [EqVal(c,v) for c in cells],
                [str(c) for c in cells]
            )
        )

    return constraints


def alldiffRowsCols(varmat):
    (x,y)=varmat.dim()
    dom = varmat.domain()

    constraints = []

    for col in range(y):
        constraints += buildCage("column {}".format(col+1), [varmat[i][col] for i in range(x)], dom)

    for row in range(x):
        constraints += buildCage("row {}".format(row+1), [varmat[row][i] for i in range(y)], dom)


    return constraints

# This requires a square matrix, of length n*n for some n
def boxConstraints(varmat):
    (x,y) = varmat.dim()

    s = intsqrt(x)

    assert x==y
    assert s*s==x

    constraints = []
    for i in range(0, s*s, s):
        for j in range(0, s*s, s):
            v = [varmat[i+x][j+y] for x in range(s) for y in range(s)]
            constraints += buildCage("the cage starting at top-left position ({},{})".format(i,j), v, varmat.domain())
    
    return constraints

def basicSudoku(varmat):
    constraints = []

    constraints += alldiffRowsCols(varmat)
    constraints += boxConstraints(varmat)

    return constraints