import math
import logging
import sys
import math


class OCUSMUSFinder:
    def __init__(self, solver):
        self._solver = solver
        self._bestcache = {}

        # Internals for OCUS
        p_clauses = solver._cnf.clauses
        p_ass = [[c] for c in solver._conlits]
        p_weights = {c: 20 for c in solver._conlits}  # Demystify has no weighting so weight everything equally.
        p_user_vars = solver._varsmt

    def smallestMUS(self, puzlits):
        pass
        # TO DO
