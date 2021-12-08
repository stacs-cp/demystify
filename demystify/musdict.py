import logging
import math
from demystify.base import Lit, DummyClause

class MusDict(dict):
    # Expects dict of form {Lit:[(DummyClause,)}
    def __init__(self, mus_dict={}):
        for k, v in mus_dict.items():
            self[k] = v

    def contains(self, literal):
        return literal in self

    def get(self, literal):
        return self[literal]

    def get_first(self, literal):
        return self[literal][0]

    def get_all(self, literals):
        return [self.get_first(p) for p in literals]

    def filter_literals_by_mus(self, condition):
        return [
            k
            for k in sorted(self.keys())
            if condition(self.get_first(k))
        ]

    def filter_literals(self, condition):
        return [k for k in sorted(self.keys()) if condition(k)]

    def get_literals(self):
        return [k for k in sorted(self.keys())]

    def has_literal(self, literal):
        return (
            len(
                list(
                    k for k in sorted(self.keys()) if str(k) == literal
                )
            )
            > 0
        )

    def minimum(self):
        if len(self) == 0:
            return math.inf

        return min(len(v[0]) for v in self.values())

    def update(self, p:Lit, mus:[DummyClause]):
        if mus is None:
            return

        elif p not in self:
            logging.info("XX found first {} {}".format(p, len(mus)))

            self[p] = [tuple(sorted(mus))]

        elif len(self[p][0]) > len(mus):
            logging.info(
                "XX found new best {} {} {}".format(
                    p, len(self[p][0]), len(mus)
                )
            )

            self[p] = [tuple(sorted(mus))]

        elif p in self and len(self[p][0]) == len(mus):
            newmus = tuple(sorted(mus))
            if not (newmus in self[p]):
                logging.info(
                    "XX add another new best {} {} {}".format(
                        p, len(self[p][0]), len(self[p])
                    )
                )
                self[p].append(tuple(sorted(mus)))
            else:
                logging.info("XX find duplicate {}".format(p))

        else:
            assert len(self[p][0]) < len(mus)

    def remove_duplicates(self):
        checked = set([])
        # TODO: Filter out duplicated MUSes
        # if mus in checked:
        #    continue
        # checked.add(mus)
        removed = 0
        for k in sorted(self.keys()):
            for v in sorted(list(self.get(k))):
                # Empty MUSes arise from values implied by the problem, we do not filter them
                if len(v) > 0:
                    if v in checked:
                        self.get(k).remove(v)
                        removed += 1
                    else:
                        checked.add(v)

            if len(self.get(k)) == 0:
                del self[k]

        logging.info("Remove dups: %s removed, %s left", removed, len(checked))
