import logging
import math
import os

from .parse import parse_json, parse_essence
from .mus import CascadeMUSFinder, checkWhichLitsAMUSProves
from .musforqes import ForqesMUSFinder
from .utils import flatten, in_flattened, intsqrt, lowsqrt
from .base import EqVal, NeqVal

from sortedcontainers import SortedSet

from demystify import mus


class SolveError(Exception):
    pass


class ExplainError(Exception):
    pass


class Explainer(object):
    def __init__(self, mus_finder=None, merge=1, skip=0, debug=False, steps_explained=0):
        self.steps_explained = steps_explained
        self.mus_finder_name = mus_finder
        self.merge = merge
        self.skip = skip

        if debug:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(levelname)s:%(pathname)s:%(lineno)d:%(name)s:%(message)s",
            )

        self.params = None
        self.puzzle = None
        self.solver = None
        self.solution = None
        self.explained = []

    def init_from_json(self, puzzle_json):
        self.puzzle, self.solver = parse_json(puzzle_json)
        self.solution = self._get_puzzle_solution()
        self.unexplained = self.solution
        self._set_mus_finder()

    def init_from_essence(self, eprime, eprimeparam):
        self.puzzle, self.solver, self.params = parse_essence(
            eprime, eprimeparam
        )
        self.name = os.path.basename(eprime)
        self.solution = self._get_puzzle_solution()
        self.unexplained = self.solution
        self._set_mus_finder()

    def explain_steps(self, lit_choice=None, mus_choice=None, num_steps=None):
        if not self.puzzle or not self.solver or not self.solution:
            raise ExplainError("Puzzle has not been correctly initialised.")

        steps = []
        if num_steps is not None:
            for i in range(1, num_steps + 1):
                if len(self.unexplained) <= 0:
                    break
                if i == 1:
                    steps.append(
                        self.explain_step(
                            lit_choice=lit_choice, mus_choice=mus_choice
                        )
                    )
                else:
                    steps.append(self.explain_step(self))
        else:
            first_step = True
            while len(self.unexplained) > 0:
                if first_step:
                    steps.append(
                        self.explain_step(
                            lit_choice=lit_choice, mus_choice=mus_choice
                        )
                    )
                    first_step = False
                else:
                    steps.append(self.explain_step(self))

        return {"name": self.name, "params": self.params, "steps": steps}

    def explain_step(self, lit_choice=None, mus_choice=None, update=True):
        step_dict = {}
        step_dict["stepNumber"] = self.steps_explained + 1

        mus_dict = self.mus_finder.smallestMUS(self.unexplained)

        smallest = mus_dict.minimum()

        if smallest <= self.merge:
            if smallest <= self.skip:
                skipped = mus_dict.filter_literals_by_mus(
                    lambda mus: len(mus) <= self.skip
                )

                step_dict["skippedDeductions"] = [
                    self._get_deduction([p], mus_dict.get_first(p))
                    for p in sorted(skipped)
                ]

                self._add_known(skipped)

                mus_dict = self.mus_finder.smallestMUS(self.unexplained)
                smallest = mus_dict.minimum()

            merged = mus_dict.filter_literals_by_mus(
                lambda mus: len(mus) <= self.merge
            )

            step_dict["puzzleState"] = self._get_puzzle_state(
                merged, mus_dict.get_all(merged)
            )

            step_dict["simpleDeductions"] = [
                self._get_deduction([p], mus_dict.get_first(p))
                for p in sorted(merged)
            ]

            self._add_known(merged)
        else:
            lit_choices = mus_dict.filter_literals_by_mus(
                lambda mus: len(mus) == smallest
            )

            if lit_choice is not None:
                if mus_dict.has_literal(lit_choice):
                    lit_choices = mus_dict.filter_literals(
                        lambda lit: lit == str(lit_choice)
                    )

            (
                best_lit,
                best_mus,
                best_proven_lits,
                proven_dict,
            ) = self._choose_mus(lit_choices, mus_dict)

            choices, proven_lit_choices = self._choices_list(mus_dict)

            if mus_choice is not None:
                best_proven_lits = proven_lit_choices[mus_choice]
                best_mus = mus_dict.get(lit_choices[mus_choice])[0]
            else:
                (
                    best_lit,
                    best_mus,
                    best_proven_lits,
                    proven_dict,
                ) = self._choose_mus(lit_choices, mus_dict)

            step_dict = self._get_step_dict(best_proven_lits, best_mus)
            step_dict["otherChoices"] = choices
            self._add_known(best_proven_lits)

        self.steps_explained += 1

        return step_dict

    def get_choices(self):
        mus_dict = self.mus_finder.smallestMUS(self.unexplained)
        smallest = mus_dict.minimum()

        if smallest <= self.merge:
            return {"name": self.name, "params": self.params, "steps": []}
            
        choices_explanations, _ = self._choices_list(mus_dict)
        return {"name": self.name, "params": self.params, "steps": [choices_explanations]}
    
    def _choices_list(self, mus_dict):
        smallest = mus_dict.minimum()
        choices = []
        proven_lit_choices = []

        if smallest <= self.merge:
            return []
        else:
            lit_choices = mus_dict.filter_literals_by_mus(
                lambda mus: len(mus) == smallest
            )

            (
                _,
                _,
                _,
                proven_dict,
            ) = self._choose_mus(lit_choices, mus_dict)

            for p in lit_choices:
                muses = tuple(SortedSet(mus_dict.get(p)))
                choices.append(self._get_step_dict(proven_dict[p][muses[0]], muses[0]))
                proven_lit_choices.append(proven_dict[p][muses[0]])
        
        return choices, proven_lit_choices

    def _add_known(self, lits):
        for p in lits:
            # Tell we solver we know this
            self.solver.addLit(p)
            # Remove from the things we have to calculate
            self.explained.append(p)
            self.unexplained.remove(p)

    def _get_step_dict(self, proven_lits, mus):
        step_dict = {}

        step_dict["puzzleState"] = self._get_puzzle_state(proven_lits, mus)
        step_dict["deduction"] = self._get_deduction(proven_lits, mus)
        step_dict["smallestMUSSize"] = len(mus)

        return step_dict

    def _get_deduction(self, lits, mus):
        exp = {}
        exp["decision"] = (
            "Setting " + ", ".join(str(l) for l in lits) + " because:"
        )
        exp["reason"] = []

        if len(mus) == 0:
            exp["reason"].append("The basic design of the problem")
        else:
            for _, clause in enumerate(sorted(mus)):
                exp["reason"].append(str(self.solver.explain(clause)))

        return exp

    def _get_puzzle_state(self, lits, mus):
        state = []

        vars = self.solver.puzzle().vars()
        known = self.solver.getKnownLits()
        involved = [m.clauseset() for m in flatten(mus)]

        for matrix in vars:
            state.append(
                self._get_puzzle_matrix(
                    matrix,
                    SortedSet(known),
                    involved,
                    SortedSet(flatten(involved)),
                    SortedSet(lits),
                )
            )

        return {"matrices": state}

    def _get_puzzle_matrix(self, matrix, known, involved, involvedset, targets):
        output_matrix = []
        matrixRow = 0

        for _, row in enumerate(matrix.varmat()):
            output_matrix.append({"cells": []})
            for cell in row:
                output_matrix[matrixRow]["cells"].append(
                    self._get_cell_values(
                        cell, known, involved, involvedset, targets
                    )
                )
            matrixRow += 1

        return {"rows": output_matrix}

    def _get_cell_values(self, variable, known, involved, involvedset, targets):
        cell = []
        dom = variable.dom()

        splitsize = 1
        domsize = len(dom)
        if intsqrt(domsize) is not None:
            splitsize = intsqrt(domsize)
        elif domsize % 2 == 0:
            splitsize = domsize // 2
        else:
            splitsize = lowsqrt(domsize)

        for dsublist in [
            dom[i: i + splitsize] for i in range(0, len(dom), splitsize)
        ]:

            cell_values = []

            for d in dsublist:
                value = {}
                markers = []
                status = ""
                explanations = []
                poslit = EqVal(variable, d)
                neglit = NeqVal(variable, d)
                if neglit in targets:
                    markers.append("nit")
                    status = "negative"
                elif poslit in targets:
                    markers.append("pit")
                    status = "positive"
                # Put this neglit check here, as we want to skip displaying it
                # we already know it is gone
                elif neglit in known:
                    markers.append("nik")
                elif poslit in involvedset:
                    markers.append("pii")
                    status = "involved"
                elif neglit in involvedset:
                    markers.append("nii")

                if poslit in known:
                    markers.append("pik")

                for i, clause in enumerate(involved):

                    if in_flattened(clause, poslit) or in_flattened(clause, neglit):

                        explanations.append(str(i))
                        # We want this to be "the" explanation that makes d
                        # postlit or neglit in targets

                value["markers"] = markers
                value["value"] = d
                value["status"] = status
                value["explanations"] = explanations

                if not "nik" in value["markers"]:
                    cell_values.append(value)

            if len(cell_values) != 0:
                cell.append({"cellValues": cell_values})

        return {"cellRows": cell}

    def _get_puzzle_solution(self, no_domains=None, allow_incomplete=False):

        logging.debug(self.solver.solve(getsol=True))

        if allow_incomplete:
            solution = self.solver.solveAll([])
        else:
            solution = self.solver.solveSingle([])

        logging.debug(solution)

        if solution is None:
            raise SolveError("Your problem has no solution!")

        if solution == "Multiple" and not allow_incomplete:
            raise SolveError("Your problem has multiple solutions!")

        if no_domains:
            logging.debug("NODOMAINS", len(solution))
            solution = [p for p in solution if p.equal]
            logging.debug("!!", len(solution))

        return solution

    def _choose_mus(self, candidates, mus_dict):
        best_lit = None
        best_mus = None
        best_proven_lits = None
        best_mus_stat = (math.inf, math.inf, math.inf)
        proven_dict = {}

        checked = set([])

        for b in candidates:
            proven_dict[b] = {}
            for mus in mus_dict.get(b):

                mus_lits = SortedSet.union(
                    SortedSet(), *(SortedSet(m.lits()) for m in mus)
                )

                # TODO: Filter out duplicated MUSes
                #if mus in checked:
                #    continue
                #checked.add(mus)

                unexplained_in_mus = SortedSet(
                    p
                    for p in self.unexplained
                    if p in mus_lits or p.neg() in mus_lits
                )

                # Explictly add 'b', for the case where the MUS is size 0 in
                # particular
                if (len(mus), len(unexplained_in_mus)) < best_mus_stat:
                    proven_lits = SortedSet(
                        checkWhichLitsAMUSProves(
                            self.solver, unexplained_in_mus, mus
                        )
                    ).union(SortedSet([b]))
                else:
                    proven_lits = SortedSet([b])

                proven_dict[b][mus] = proven_lits

                musval = (len(mus), len(unexplained_in_mus), -len(proven_lits))

                if musval < best_mus_stat:
                    best_mus_stat = musval
                    best_lit = b
                    best_mus = mus
                    best_proven_lits = proven_lits

        return best_lit, best_mus, best_proven_lits, proven_dict

    def _set_mus_finder(self):
        if self.mus_finder_name == "forqes":
            self.mus_finder = ForqesMUSFinder(self.solver)
        else:
            self.mus_finder = CascadeMUSFinder(self.solver)
