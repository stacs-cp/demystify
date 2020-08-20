import logging
import sys

from .prettyprint import print_explanation

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

def html_solve(outstream, solver, puzlits, MUS):
    trace = []

    # Set up Javascript
    print("""
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
    """)

    step = 1
    # Now, we need to check each one in turn to see which is 'cheapest'
    while len(puzlits) > 0:
        logging.info("Starting Step %s", step)
        logging.info("Current state %s", solver.getCurrentDomain())
        musdict = MUS.smallestMUS(puzlits)
        smallest = min([len(v) for v in musdict.values()])
        print("<h3>Step {}</h3>".format(step))
        step += 1
        if smallest == 1:
            lits = [k for k in sorted(musdict.keys()) if len(musdict[k]) == 1]
            print_explanation(outstream, solver, [musdict[l] for l in lits], lits)

            print("Doing", len(lits), " simple deductions ")

            exps = "\n".join([explain(solver, p, musdict[p]) for p in sorted(lits)])
            print(hidden("Show why", exps))

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
            print(explain(solver, p, musdict[p]))
            if len(mins) > 1:
                print(hidden("There were {} choices of the same size".format(len(mins)-1),
                    "\n".join([explain(solver, p, musdict[p]) for p in mins[1:]])))
            else:
                print("<p>No other choices</p>")
            solver.addLit(p)
            puzlits.remove(p)
        
        print("<hr>")
    
    logging.info("Trace: %s", trace)
    logging.info("Trace Quality: %s", [(i,len(j)) for (i,j) in trace])
    return trace