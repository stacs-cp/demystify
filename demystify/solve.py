import logging
import sys
import math
import io
import pprint
from sortedcontainers import *

from .prettyprint import print_explanation

from .MUS import musdict_minimum, checkWhichLitsAMUSProves

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


def explain(solver, lits, reason, classid, enumerateclass = True):
    exp = ""
    exp += "<p>Setting " + ", ".join(str(l) for l in lits) + " because:</p>\n"
    if len(reason) == 0:
        exp += "<p>The basic design of the problem</p>"
    else:
        exp += "<ul>\n"            
        for i,clause in enumerate(sorted(reason)):
            if enumerateclass:
                class_str = classid + str(i)
            else:
                class_str = classid
            exp += "<li class='" + class_str + "'>" + str(solver.explain(clause)) + "</li>\n"
            exp += '<script>hoverByClass("{}","black")</script>\n'.format(class_str)
        exp += "</ul>\n"

    return exp

def list_counter(l):
    d = dict()
    for i in l:
        d[i] = d.get(i, 0) + 1
    return d

class_counter = 0
def unique_class_id():
    global class_counter
    class_counter += 1
    return "cl_" + str(class_counter) + "_"

def html_step(outstream, solver, p, choices, bestchoice):
    classid = unique_class_id()
    print_explanation(outstream, solver, bestchoice, p, classid)
    print("Smallest mus size:", len(bestchoice),  file=outstream)
    print(explain(solver, p, bestchoice, classid), file=outstream)

    if len(choices) > 1:
            others = io.StringIO()
            classid = unique_class_id()
            for c in (c for c in choices if c != bestchoice):
                print_explanation(others, solver, c, p, classid)
                print("Smallest mus size:", len(c),  file=others)
                print(explain(solver, p, c, classid), file=others)
            print(hidden("{} methods of deducing the same value were found:".format(len(choices)),
                    others.getvalue()
                    ), file=others)

def html_solve(outstream, solver, puzlits, MUSFind, steps=math.inf, *, gofast = False, fulltrace=False, forcechoices = None, skip=-1, merge=1, force=None):
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
.pii {background-color:lightblue}
.nii {background-color: orange}
.pik {font-weight: bolder}
td {border-width: 3; border-style: solid; border-color:transparent}

</style>
<!-- from https://stackoverflow.com/questions/12786810/hover-on-element-and-highlight-all-elements-with-the-same-class -->
<script>
function hoverByClass(classname,colorover,colorout="transparent"){
	var elms=document.getElementsByClassName(classname);
	for(var i=0;i<elms.length;i++){
		elms[i].addEventListener("mouseover", function(){
			for(var k=0;k<elms.length;k++){
				elms[k].style.borderColor=colorover;
                elms[k].style.borderWidth=3
                elms[k].style.borderStyle="solid"
			}
		});
		elms[i].addEventListener("mouseout", function(){
			for(var k=0;k<elms.length;k++){
				elms[k].style.borderColor=colorout;
			}
		});
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
<h3>How to read Demystify output:</h3>
<ul>
<li> Values in the grids are removed when we know they are no longer allowed</li>
<li> They become <b>bold</b> when we know the value which occurs in some cell</li>
<li> Each step either shows:</li>
<ul> 
<li> A number of 'simple deductions' merged together (simple deductions involve MUSes of size 1) </li>
<li> A single "interesting" deduction (to find interesting deductions, try searching for the words 'Smallest mus')</li>
</ul>
<li> Colours used are when explaining MUSes are:</li>
<ul>
<li> The values which are being deduced in this step are coloured as:</li>
<ul>
<li> <span style="background-color:red">Red</span>: This value is being REMOVED in this step</li>
<li> <span style="background-color:green">Green</span>: This value is deduced as the CORRECT answer in this step</li>
</ul>
<li> The values which are involved in the reasoning in this step are coloured as:</li>
<ul>
<li> <span style="background-color:lightblue">Light blue</span>: This value is not yet known, but is involved in the reasoning of this step</li>
<li> <span style="background-color:orange">Orange</span>: This value, which is already known, is involved in the MUS in this step</li>
</ul>
<li> Putting the mouse on a literal will highlight all constraints it is involved in, putting the mouse on a constraint will highlight all the literals in that constraint (which have not already been removed)</li>
</ul>
</ul>
    """
    , file=outstream)

    step = 1
    forcestep = 0
    # Now, we need to check each one in turn to see which is 'cheapest'
    # puzlits is a list which contains all the 'literals' whose values we have to find.
    while len(puzlits) > 0 and step <= steps:
        logging.info("Starting Step %s", step)
        logging.info("Current state %s", solver.getCurrentDomain())

        begin_stats = solver.get_stats()

        # Go and find the MUSes
        musdict = MUSFind.smallestMUS(puzlits)
        end_stats = solver.get_stats()

        stats_diff = {"solveCount": end_stats["solveCount"] - begin_stats["solveCount"],
                      "solveTime": end_stats["solveTime"] - begin_stats["solveTime"] }
        # Find size of smallest MUS
        smallest = musdict_minimum(musdict)
        print("<h3>Step {} </h3>".format(step), file=outstream)
        print("Solver Calls: {} <br>".format(stats_diff["solveCount"]), file=outstream)
        total_calls += stats_diff["solveCount"]


        if smallest <= skip:
            # Find all literals where the explanation is of size <= skip
            lits = [k for k in sorted(musdict.keys()) if len(musdict[k][0]) <= skip]
            print("Skip displaying tiny MUSes..")

            # Go make explantions for each literal
            exps = "\n".join([explain(solver, [p], musdict[p][0], unique_class_id()) for p in sorted(lits)])
            # Print them out
            print(hidden("Show hidden", exps), file=outstream)
            for p in lits:
                # Tell we solver we know this
                solver.addLit(p)
                # Remove from the things we have to calculate
                puzlits.remove(p)

        elif smallest <= merge:
            step += 1

            classid = unique_class_id()

            lits = [k for k in sorted(musdict.keys()) if len(musdict[k][0]) <= merge]
            print_explanation(outstream, solver, [musdict[l][0] for l in sorted(lits)], sorted(lits), classid)

            print("Doing", len(lits), " simple deductions ", file=outstream)

            exps = "\n".join([explain(solver, [p], musdict[p][0], str(classid) + str(val), enumerateclass=False) for (val,p) in enumerate(sorted(lits))])
            print(hidden("Show why", exps), file=outstream)

            for p in lits:
                solver.addLit(p)
                puzlits.remove(p)
        else:
            step += 1

            # print(list(str(k) for k in sorted(musdict.keys())), "::", force)

            # Set default value
            basemins = [k for k in sorted(musdict.keys()) if len(musdict[k][0]) == smallest]

            # Consider overriding 'basemins' value with 'force'
            if force is not None:
                inforces = list(f for f in force if len(list(k for k in sorted(musdict.keys()) if str(k) == f)) > 0)
                if len(inforces) > 0:
                    basemins = [k for k in sorted(musdict.keys()) if str(k) == inforces[0]]
                    force.remove(inforces[0])
                    if len(force) == 0:
                        force = None
                    print("force = ", force)

            fullinfo = {lit: list_counter(musdict[lit]) for lit in basemins}
            if fulltrace:
                ftrace.append(fullinfo)

            bestlit = None
            bestmus = None
            bestdeletedlits = None
            bestmusstat = (math.inf, math.inf, math.inf)
            deleteddict = {}
            for b in basemins:
                deleteddict[b] = {}
                for mus in musdict[b]:
                    muslits = SortedSet.union(SortedSet(),*(SortedSet(m.lits()) for m in mus))
                    puzlitsinmus = SortedSet(p for p in puzlits if p in muslits or p.neg() in muslits)
                    # Explictly add 'b', for the case where the MUS is size 0 in particular
                    deletedlits = SortedSet(checkWhichLitsAMUSProves(solver, puzlitsinmus, mus)).union(SortedSet([b]))
                    deleteddict[b][mus] = deletedlits
                    musval = (len(mus), len(puzlitsinmus), -len(deletedlits))
                    if musval < bestmusstat:
                        bestmusstat = musval
                        bestlit = b
                        bestmus = mus
                        bestdeletedlits = deletedlits

            assert not gofast


            choices = tuple(SortedSet(musdict[bestlit]))
            #passkeys = checkWhichLitsAMUSProves(solver, puzlits, choices[0])
            html_step(outstream, solver, bestdeletedlits, choices, bestmus)

            trace.append((bestmusstat, bestmus))

            if not gofast:
                if len(basemins) > 1:
                    others = io.StringIO()
                    for p in (p for p in basemins if p != bestlit):
                        choices = tuple(SortedSet(musdict[p]))
                        html_step(others, solver, deleteddict[p][choices[0]], choices, choices[0])
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
            
            if forcechoices is None:
                logging.info("Choosing {}".format(bestdeletedlits))
                for k in bestdeletedlits:
                    solver.addLit(k)
                    puzlits.remove(k)

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
    logging.info("Trace Sorted: %s", sorted([(i,len(j)) for (i, j) in trace]))

    if fulltrace:
        return (trace, ftrace)
    else:
        return trace
