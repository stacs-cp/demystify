import logging
import math


class MusDict(object):
    def __init__(self, mus_dict):
        self.mus_dict = mus_dict

    def __len__(self):
        return len(self.mus_dict)

    def contains(self, literal):
        return literal in self.mus_dict
        
    def get(self, literal):
        return self.mus_dict[literal]

    def get_first(self, literal):
        return self.mus_dict[literal][0]

    def get_all(self, literals):
        return [self.get_first(p) for p in literals]

    def filter_literals_by_mus(self, condition):
        return [
            k
            for k in sorted(self.mus_dict.keys())
            if condition(self.get_first(k))
        ]

    def filter_literals(self, condition):
        return [k for k in sorted(self.mus_dict.keys()) if condition(k)]

    def get_literals(self):
        return [k for k in sorted(self.mus_dict.keys())]

    def has_literal(self, literal):
        return (
            len(
                list(
                    k for k in sorted(self.mus_dict.keys()) if str(k) == literal
                )
            )
            > 0
        )

    def minimum(self):
        if len(self.mus_dict) == 0:
            return math.inf

        return min(len(v[0]) for v in self.mus_dict.values())

    def update(self, p, mus):
        if mus is None:
            return

        elif p not in self.mus_dict:
            logging.info("XX found first {} {}".format(p, len(mus)))

            self.mus_dict[p] = [tuple(sorted(mus))]

        elif len(self.mus_dict[p][0]) > len(mus):
            logging.info(
                "XX found new best {} {} {}".format(
                    p, len(self.mus_dict[p][0]), len(mus)
                )
            )

            self.mus_dict[p] = [tuple(sorted(mus))]

        elif p in self.mus_dict and len(self.mus_dict[p][0]) == len(mus):
            newmus = tuple(sorted(mus))
            if not (newmus in self.mus_dict[p]):
                logging.info(
                    "XX add another new best {} {} {}".format(
                        p, len(self.mus_dict[p][0]), len(self.mus_dict[p])
                    )
                )
                self.mus_dict[p].append(tuple(sorted(mus)))
            else:
                logging.info("XX find duplicate {}".format(p))

        else:
            assert len(self.mus_dict[p][0]) < len(mus)
