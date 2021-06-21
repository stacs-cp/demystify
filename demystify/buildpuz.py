import math
from sortedcontainers import *

from itertools import combinations
from demystify.base import *
from demystify.utils import intsqrt
from demystify.config import CONFIG


def buildNeq(name, c1, c2, dom):
    constraints = []
    for v in dom:
        constraints.append(
            Clause(
                "{} and {} cannot both be {} as they are both {}".format(
                    c1, c2, v, name
                ),
                [NeqVal(c1, v), NeqVal(c2, v)],
            )
        )
    return constraints


def buildLess(c1, c2, dom):
    constraints = []
    for v1 in dom:
        for v2 in dom:
            if v1 >= v2:
                constraints.append(
                    Clause(
                        "{} and {} cannot be {} and {} as they must be ordered".format(
                            c1, c2, v1, v2
                        ),
                        [NeqVal(c1, v1), NeqVal(c2, v2)],
                    )
                )
        constraints.append(
            Clause(
                "{} must be less than {} if {} is {}".format(c1, v1, c2, v1),
                [EqVal(c1, i) for i in dom if i < v1] + [NeqVal(c2, v1)],
            )
        )
        constraints.append(
            Clause(
                "{} must be greater than {} if {} is {}".format(c2, v1, c1, v1),
                [EqVal(c2, i) for i in dom if i > v1] + [NeqVal(c1, v1)],
            )
        )

    return constraints


def buildDiffBy(name, c1, c2, diff, dom):
    constraints = []
    for v1 in dom:
        for v2 in range(v1 - diff, v1 + diff + 1):
            if v2 in dom:
                constraints.append(
                    Clause(
                        "{} and {} cannot be {} and {} as they must differ by at least {} and are {}".format(
                            c1, c2, v1, v2, diff, name
                        ),
                        [NeqVal(c1, v1), NeqVal(c2, v2)],
                    )
                )
    return constraints


def buildCage(name, cells, dom):
    constraints = []
    if CONFIG["OneClauseAtMost"]:
        for v in dom:
            constraints.append(
                ClauseList(
                    "At most one cell in {} can be {}".format(name, v),
                    [
                        [NeqVal(c1, v), NeqVal(c2, v)]
                        for (c1, c2) in itertools.combinations(cells, 2)
                    ],
                    [EqVal(c, v) for c in cells],
                    [str(c) for c in cells],
                )
            )
    else:
        for (c1, c2) in itertools.combinations(cells, 2):
            constraints += buildNeq(name, c1, c2, dom)

    for v in dom:
        constraints.append(
            Clause(
                "Some cell {} must be {}".format(name, v),
                [EqVal(c, v) for c in cells],
                [str(c) for c in cells],
            )
        )

    return constraints


def alldiffRowsCols(varmat):
    (x, y) = varmat.dim()
    dom = varmat.domain()

    constraints = []

    for col in range(y):
        constraints += buildCage(
            "in column {}".format(col + 1),
            [varmat[i][col] for i in range(x)],
            dom,
        )

    for row in range(x):
        constraints += buildCage(
            "in row {}".format(row + 1), [varmat[row][i] for i in range(y)], dom
        )

    return constraints


def diagonalConstraints(varmat):
    (x, y) = varmat.dim()
    assert x == y
    dom = varmat.domain()

    constraints = []

    constraints += buildCage(
        "in \ diagonal", [varmat[i][i] for i in range(x)], dom
    )

    constraints += buildCage(
        "in / diagonal", [varmat[x - 1 - i][i] for i in range(x)], dom
    )

    return constraints


# This requires a square matrix, of length n*n for some n
def boxConstraints(varmat):
    (x, y) = varmat.dim()

    s = intsqrt(x)

    assert x == y
    assert s * s == x

    constraints = []
    for i in range(0, s * s, s):
        for j in range(0, s * s, s):
            v = [varmat[i + x][j + y] for x in range(s) for y in range(s)]
            constraints += buildCage(
                "the cage starting at top-left position ({},{})".format(i, j),
                v,
                varmat.domain(),
            )

    return constraints


def knightsMove(varmat):
    constraints = []
    (x, y) = varmat.dim()

    for i1 in range(x):
        for j1 in range(y):
            for knight in (
                (1, 2),
                (1, -2),
                (-1, -2),
                (-1, 2),
                (2, 1),
                (2, -1),
                (-2, 1),
                (-2, -1),
            ):
                other = (i1 + knight[0], j1 + knight[1])
                if 0 <= other[0] < x and 0 <= other[1] < y:
                    constraints += buildNeq(
                        "seperated by knights move",
                        varmat[i1][j1],
                        varmat[other[0]][other[1]],
                        varmat.domain(),
                    )

    return constraints


def kingsMove(varmat):
    constraints = []
    (x, y) = varmat.dim()

    for i1 in range(x):
        for j1 in range(y):
            for king in (
                (-1, -1),
                (-1, 0),
                (-1, 1),
                (0, -1),
                (0, 1),
                (1, -1),
                (1, 0),
                (1, 1),
            ):
                other = (i1 + king[0], j1 + king[1])
                if 0 <= other[0] < x and 0 <= other[1] < y:
                    constraints += buildNeq(
                        "seperated by kings move",
                        varmat[i1][j1],
                        varmat[other[0]][other[1]],
                        varmat.domain(),
                    )

    return constraints


def adjDiffByMat(varmat, diff):
    constraints = []
    (x, y) = varmat.dim()

    for i1 in range(x):
        for j1 in range(y):
            for adj in ((-1, 0), (1, 0), (0, 1), (0, -1)):
                other = (i1 + adj[0], j1 + adj[1])
                if 0 <= other[0] < x and 0 <= other[1] < y:
                    constraints += buildDiffBy(
                        "adjacent",
                        varmat[i1][j1],
                        varmat[other[0]][other[1]],
                        diff,
                        varmat.domain(),
                    )
    return constraints


def diffByDist(varmat, dist, difference):
    constraints = []
    (x, y) = varmat.dim()

    for i1 in range(x):
        for j1 in range(y):
            for diffi in range(-dist, dist + 1):
                for diffj in range(-dist, dist + 1):
                    other = (i1 + diffi, j1 + diffj)
                    if (
                        (abs(diffi) + abs(diffj) == dist)
                        and 0 <= other[0] < x
                        and 0 <= other[1] < y
                    ):
                        constraints += buildDiffBy(
                            "dist {}".format(dist),
                            varmat[i1][j1],
                            varmat[other[0]][other[1]],
                            difference,
                            varmat.domain(),
                        )
    return constraints


def thermometer(varmat, l):
    constraints = []
    for i in range(len(l) - 1):
        p1 = l[i]
        p2 = l[i + 1]
        constraints += buildLess(
            varmat[p1[0]][p1[1]], varmat[p2[0]][p2[1]], varmat.domain()
        )
    return constraints


def thermometers(varmat, l):
    constraints = []
    for t in l:
        constraints += thermometer(varmat, t)
    return constraints


def basicSudoku(varmat):
    constraints = []

    constraints += alldiffRowsCols(varmat)
    constraints += boxConstraints(varmat)

    return constraints


def basicXSudoku(varmat):
    constraints = []

    constraints += alldiffRowsCols(varmat)
    constraints += boxConstraints(varmat)
    constraints += diagonalConstraints(varmat)

    return constraints


def basicMiracle(varmat):
    constraints = []

    constraints += basicSudoku(varmat)

    constraints += knightsMove(varmat)
    constraints += kingsMove(varmat)

    constraints += adjDiffByMat(varmat, 1)
    return constraints


def basicMiracle2(varmat, thermometers):
    constraints = []

    constraints += basicSudoku(varmat)

    constraints += knightsMove(varmat)

    for t in thermometers:
        constraints += thermometer(varmat, t)

    return constraints


def buildJigsaw(varmat, jigsaw):
    constraints = []
    constraints += alldiffRowsCols(varmat)

    size = 9

    jigsawrows = [jigsaw[i : i + size] for i in range(0, size * size, size)]

    for val in SortedSet(jigsaw):
        cells = []
        for i in range(9):
            for j in range(9):
                if jigsawrows[i][j] == val:
                    cells.append(varmat[i][j])
        constraints += buildCage(
            "cage {}".format(val),
            cells,
            varmat.domain(),
        )

    return constraints
