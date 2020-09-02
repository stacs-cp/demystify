import logging
import sys
import math

from .prettyprint import print_explanation

from .MUS import musdict_minimum

# Make a unique id
id_counter = 0


def get_id():
    global id_counter
    id_counter += 1
    return "id{}".format(id_counter)


# Make a div which starts hidden
def hidden(name, content):
    id = get_id()
    s = ""
    s += """<input type='submit' value='{}' onclick="toggle('{}');">""".format(name, id)
    s += "<div id={} style='display:none;'>\n".format(id)
    s += content
    s += "\n</div>\n"
    return s


def explain(solver, lit, reason):
    exp = ""
    exp += "<p>Setting " + str(lit) + " because:</p>\n"
    exp += "<ul>\n"
    for clause in sorted(reason):
        exp += "<li>" + str(solver.explain(clause)) + "</li>\n"
    exp += "</ul>\n"

    return exp

def list_counter(l):
    d = dict()
    for i in l:
        d[i] = d.get(i, 0) + 1
    return d

def html_step(outstream, solver, p, mus):
    print_explanation(outstream, solver, mus, [p])
    print("Smallest mus size:", len(mus),  file=outstream)
    print(explain(solver, p, mus), file=outstream)

def html_solve(outstream, solver, puzlits, MUS, steps=math.inf, *, gofast = False, fulltrace=False):
    trace = []
    ftrace = []

    # Set up Javascript
    print(
        """
    <script>
    toggle = function(id) {
        div = document.getElementById(id)
        if( div.style.display == "none" ) {
           div.style.display = "block";
        } else {
           div.style.display = "none";
        }
    };

    hide = function(id) {
        div = document.getElementById(id)
        div.style.display = "none";
    };
    </script>
    """
    )

    step = 1
    # Now, we need to check each one in turn to see which is 'cheapest'
    while len(puzlits) > 0 and step <= steps:
        logging.info("Starting Step %s", step)
        logging.info("Current state %s", solver.getCurrentDomain())
        musdict = MUS.smallestMUS(puzlits)
        smallest = musdict_minimum(musdict)
        print("<h3>Step {}</h3>".format(step))
        step += 1
        if smallest == 1:
            lits = [k for k in sorted(musdict.keys()) if len(musdict[k][0]) == 1]
            print_explanation(outstream, solver, [musdict[l][0] for l in lits], lits)

            print("Doing", len(lits), " simple deductions ")

            exps = "\n".join([explain(solver, p, musdict[p][0]) for p in sorted(lits)])
            print(hidden("Show why", exps))

            for p in lits:
                solver.addLit(p)
                puzlits.remove(p)
        else:
            # Find first thing with smallest value
            basemins = [k for k in sorted(musdict.keys()) if len(musdict[k][0]) == smallest]
            fullinfo = {lit: list_counter(musdict[lit]) for lit in basemins}
            if fulltrace:
                ftrace.append(fullinfo)

            if gofast:
                mins = basemins
            else:
                mins = [basemins[0]]

            for p in mins:
                choices = tuple(sorted(set(list(musdict[p]))))
                html_step(outstream, solver, p, choices[0])

                trace.append((smallest, mins))
                solver.addLit(p)
                puzlits.remove(p)

            if not gofast:
                if len(basemins) > 1:
                    print(
                        hidden(
                            "There were {} choices of the same size".format(len(basemins) - 1),
                            "\n".join([explain(solver, p, musdict[p][0]) for p in basemins[1:]]),
                        )
                    )
                else:
                    print("<p>No other choices</p>")
            
            print("Choice Info: {}".format(fullinfo))

        print("<hr>")

    logging.info("Trace: %s", trace)
    logging.info("Trace Quality: %s", [(i, len(j)) for (i, j) in trace])
    logging.info("Trace Sorted: %s", sorted([(i, len(j)) for (i, j) in trace]))

    if fulltrace:
        return (trace, ftrace)
    else:
        return trace
