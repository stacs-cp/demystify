import logging
import sys

from .prettyprint import print_explanation


def html_solve(outstream, solver, puzlits, MUS):
    trace = []
    # Now, we need to check each one in turn to see which is 'cheapest'
    while len(puzlits) > 0:
        musdict = MUS.smallestMUS(puzlits)
        smallest = min([len(v) for v in musdict.values()])

        logging.info([(v,len(musdict[v])) for v in sorted(musdict.keys())])

        if smallest == 1:
            lits = [k for k in sorted(musdict.keys()) if len(musdict[k]) == 1]
            print_explanation(outstream, solver, [musdict[l] for l in lits], lits)

            print("Doing", len(lits), " simple deductions ")

            for p in lits:
                solver.addLit(p)
                puzlits.remove(p)
        else:
            # Find first thing with smallest value
            mins = [k for k in sorted(musdict.keys()) if len(musdict[k]) == smallest]
            p = mins[0]
            print_explanation(outstream, solver, musdict[p], [p])
            print("Smallest mus size:", smallest)
            trace.append((smallest, mins))
            print("<p>Setting ", p," because:</p>")
            print("<ul>")
            for clause in sorted(musdict[p]):
                logging.info(clause.clauseset())
                print("<li>", solver.explain(clause), "</li>")
            print("</ul>")
            solver.addLit(p)
            puzlits.remove(p)
        
        print("<hr>")