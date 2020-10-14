import logging
import sys
import math
import io
import pprint
import uuid

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


def explain(solver, lit, reason, classid):
    exp = ""
    exp += "<p>Setting " + str(lit) + " because:</p>\n"
    exp += "<ul>\n"
    for i,clause in enumerate(sorted(reason)):
        exp += "<li class='" + classid + str(i) + "'>" + str(solver.explain(clause)) + "</li>\n"
        exp += '<script>hoverByClass("{}","pink")</script>\n'.format(classid+str(i))
    exp += "</ul>\n"

    return exp

def list_counter(l):
    d = dict()
    for i in l:
        d[i] = d.get(i, 0) + 1
    return d

def html_step(outstream, solver, p, choices):
    classid = uuid.uuid4().hex[:8]
    print_explanation(outstream, solver, choices[0], [p], classid)
    print("Smallest mus size:", len(choices[0]),  file=outstream)
    print(explain(solver, p, choices[0], classid), file=outstream)

    if len(choices) > 1:
            others = io.StringIO()
            classid = uuid.uuid4().hex[:8]
            for c in choices[1:]:
                print_explanation(others, solver, c, [p], classid)
                print("Smallest mus size:", len(c),  file=others)
                print(explain(solver, p, c, classid), file=others)
            print(hidden("{} methods of deducing the same value were found:".format(len(choices)),
                    others.getvalue()
                    ), file=others)

def html_solve(outstream, solver, puzlits, MUS, steps=math.inf, *, gofast = False, fulltrace=False, forcechoices = None):
    trace = []
    ftrace = []
    total_calls = 0

    # Set up Javascript
    print("""
<!DOCTYPE html>
<html>
<head>
<style>
.nit {background-color: red}
.pit {background-color: green}
.nik {color:white}
.pii {background-color:blue}
.nii {background-color: orange}
.pik {font-weight: bolder}
td {border-width: 3; border-style: solid; border-color:transparent}

</style>
<!-- from https://stackoverflow.com/questions/12786810/hover-on-element-and-highlight-all-elements-with-the-same-class -->
<script>
function hoverByClass(classname,colorover,colorout="transparent"){
	var elms=document.getElementsByClassName(classname);
	for(var i=0;i<elms.length;i++){
		elms[i].onmouseover = function(){
			for(var k=0;k<elms.length;k++){
				elms[k].style.borderColor=colorover;
                elms[k].style.borderWidth=3
                elms[k].style.borderStyle="solid"
			}
		};
		elms[i].onmouseout = function(){
			for(var k=0;k<elms.length;k++){
				elms[k].style.borderColor=colorout;
			}
		};
	}
}
</script>
       
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
</head>
<body>
    """
    , file=outstream)

    step = 1
    forcestep = 0
    # Now, we need to check each one in turn to see which is 'cheapest'
    while len(puzlits) > 0 and step <= steps:
        logging.info("Starting Step %s", step)
        logging.info("Current state %s", solver.getCurrentDomain())

        begin_stats = solver.get_stats()
        musdict = MUS.smallestMUS(puzlits)
        end_stats = solver.get_stats()

        stats_diff = {"solveCount": end_stats["solveCount"] - begin_stats["solveCount"],
                      "solveTime": end_stats["solveTime"] - begin_stats["solveTime"] }
        smallest = musdict_minimum(musdict)
        print("<h3>Step {} </h3>".format(step), file=outstream)
        print("Solver Calls: {} <br>".format(stats_diff["solveCount"]), file=outstream)
        total_calls += stats_diff["solveCount"]
        step += 1
        if smallest == 1:
            classid = uuid.uuid4().hex[:8]

            lits = [k for k in sorted(musdict.keys()) if len(musdict[k][0]) == 1]
            print_explanation(outstream, solver, [musdict[l][0] for l in lits], lits, classid)

            print("Doing", len(lits), " simple deductions ", file=outstream)

            exps = "\n".join([explain(solver, p, musdict[p][0], classid) for p in sorted(lits)])
            print(hidden("Show why", exps), file=outstream)

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
                choices = tuple(sorted(set(musdict[p])))
                html_step(outstream, solver, p, choices)

                trace.append((smallest, mins))
                if forcechoices is None:
                    logging.info("Choosing {}".format(p))
                    solver.addLit(p)
                    puzlits.remove(p)

            if not gofast:
                if len(basemins) > 1:
                    others = io.StringIO()
                    for p in basemins[1:]:
                        choices = tuple(sorted(set(musdict[p])))
                        html_step(others, solver, p, choices)
                        print("<br>\n", file=others)
                    

                    print(
                        hidden(
                            "Found {} candidates with MUS size {} (see other choices)".format(len(basemins), smallest),
                            others.getvalue()
                        ), file=outstream
                    )
                else:
                    print("<p>Only 1 candidate with MUS size {} found</p>".format(smallest), file=outstream)
                logging.info("Minimal choices : {} {}".format(len(basemins), basemins))
            
            if forcechoices is not None:
                print("<h3>FORCING CHOICE TO {}</h3>".format(forcechoices[forcestep]), file=outstream)
                solver.addLit(forcechoices[forcestep])
                puzlits.remove(forcechoices[forcestep])
                forcestep += 1

            print(hidden("verbose choices info", "<pre>" + pprint.PrettyPrinter(compact=True).pformat(fullinfo) + "</pre>"), file=outstream)

        print("<hr>", file=outstream)

    logging.info("Total Solver Calls %d", total_calls)
    logging.info("Trace: %s", trace)
    logging.info("Trace Quality: %s", [(i, len(j)) for (i, j) in trace])
    logging.info("Trace Sorted: %s", sorted([(i, len(j)) for (i, j) in trace]))

    if fulltrace:
        return (trace, ftrace)
    else:
        return trace
