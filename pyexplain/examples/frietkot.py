import itertools
from pyexplain.utils.utils import add_assumptions
import sys

# import numpy
import pandas as pd

from cppy import cnf_to_pysat

from cppy import *
from cppy.model_tools.to_cnf import *

# Relation between 'rows' and 'cols', Boolean Variables in a pandas dataframe
class Relation(object):
    # rows, cols: list of names
    def __init__(self, rows, cols, name=""):
        self.cols = cols
        self.rows = rows
        self.name = name
        rel = BoolVar((len(rows), len(cols)))
        self.df = pd.DataFrame(index=rows, columns=cols)
        for i,r in enumerate(rows):
            for j,c in enumerate(cols):
                self.df.loc[r,c] = rel[i,j]
    # use as: rel['a','b']
    def __getitem__(self, key):
        try:
            return self.df.loc[key]
        except KeyError:
            print(f"Warning: {self.name}{key} not in this relation")
            return False


def exactly_one(lst):
    # return sum(lst) == 1
    # (l1|l2|..|ln) & (-l1|-l2) & ...
    allpairs = [(-a|-b) for a, b in itertools.combinations(lst, 2)]
    return [any(lst)] + allpairs


def exactly_one_at_most(lst):
    allpairs = [(-a|-b) for a, b in itertools.combinations(lst, 2)]
    return any(lst), allpairs


def buildBijectivity(rels):
    bij = []
    bv_bij = []
    for rel in rels:
        # bijection for all columns inside relation
        bv1 = BoolVar()
        bv2 = BoolVar()
        # for each relation
        for col_ids in rel.df:
            # one per column
            atleast, atmost = exactly_one_at_most(rel[:, col_ids])
            [bij.append(implies(bv1, clause)) for clause in atmost]
            bij.append(implies(bv2, atleast))
        bv_bij.append(bv1)
        bv_bij.append(bv2)

        # bijection for all rows inside relation
        bv3 = BoolVar()
        bv4 = BoolVar()
        for (_,row) in rel.df.iterrows():
            # one per row
            atleast, atmost = exactly_one_at_most(row)
            [bij.append(implies(bv3, clause)) for clause in atmost]
            bij.append(implies(bv4, atleast))
        bv_bij.append(bv3)
        bv_bij.append(bv4)
    return bij, bv_bij

# untested
# returns: list of indicators, list of hard constraints
def make_trans(type1, type2, rel12,  type3, rel13, rel23):
    trans = []
    for x in type1:
        for y in type2:
            for z in type3:
                    b0 = BoolVar()
                    t0 = to_cnf(implies(rel13[x, z] & rel23[y, z], rel12[x, y]))
                    [trans.append(implies(b0, clause)) for clause in t0]

                    b1 = BoolVar()
                    t1 = to_cnf(implies(~rel13[x, z] & rel23[y, z], ~rel12[x, y]))
                    [trans.append(implies(b1, clause)) for clause in t1]

                    b2 = BoolVar()
                    t2 = to_cnf(implies(rel13[x, z] & ~rel23[y, z], ~rel12[x, y]))
                    [trans.append(implies(b2, clause)) for clause in t2]
    return [b0,b1,b2], trans


def p93():
    linkedin_connection = ["57", "59", "64", "68", "78"]
    person = ["opal", "neil", "rosie", "arnold", "georgia"]
    facebook_friend = ["120", "130", "140", "150", "160"]
    twitter_follower = ["589", "707", "715", "789", "809"]
    type1 = [-10, 10, -20, 20, -30, 30, -40, 40]
    type_dict = {
        'person':person, 
        'facebook_friend': facebook_friend,
        'twitter_follower': twitter_follower,
        'linkedin_connection': linkedin_connection
    }


    types = [linkedin_connection, person, facebook_friend, twitter_follower]
    n = len(types)
    m = len(types[0])
    assert all(len(types[i]) == m for i in range(n)), "all types should have equal length"

    connected_to = Relation(person, linkedin_connection) # connected_to(person, linkedin_connection)
    person_facebook_friend = Relation(person, facebook_friend) # with(person, facebook_friend)
    followed_by = Relation(person, twitter_follower) # followed_by(person, twitter_follower)
    is_linked_with_1 = Relation(linkedin_connection, facebook_friend) # is_linked_with_1(linkedin_connection, facebook_friend)
    is_linked_with_2 = Relation(linkedin_connection, twitter_follower) # is_linked_with_2(linkedin_connection, twitter_follower)
    is_linked_with_3 = Relation(facebook_friend, twitter_follower) # is_linked_with_3(facebook_friend, twitter_follower)
    rels = [connected_to, person_facebook_friend, followed_by, is_linked_with_1, is_linked_with_2, is_linked_with_3]
    relStrs = ["connected_to", "person_facebook_friend", "followed_by", "is_linked_with_1", "is_linked_with_2", "is_linked_with_3"]

    # Bijectivity
    cnt = 0
    bij, bv_bij = buildBijectivity(rels)

    # Transitivity
    trans = []
    bv_trans =  [BoolVar() for i in range(12)]


    for x in person:
        for y in linkedin_connection:
            for z in facebook_friend:
                t0 = to_cnf(implies(person_facebook_friend[x, z] & is_linked_with_1[y, z], connected_to[x, y]))
                [trans.append(implies(bv_trans[0], clause)) for clause in t0]

                t1 = to_cnf(implies(~person_facebook_friend[x, z] & is_linked_with_1[y, z], ~connected_to[x, y]))
                [trans.append(implies(bv_trans[1], clause)) for clause in t1]

                t2 = to_cnf(implies(person_facebook_friend[x, z] & ~is_linked_with_1[y, z], ~connected_to[x, y]))
                [trans.append(implies(bv_trans[2], clause)) for clause in t2]

    for x in person:
        for y in linkedin_connection:
            for z in twitter_follower:
                t3 = to_cnf(implies(followed_by[x, z] & is_linked_with_2[y, z], connected_to[x, y]))
                [trans.append(implies(bv_trans[3], clause)) for clause in t3]

                t4 = to_cnf(implies(~followed_by[x, z] & is_linked_with_2[y, z], ~connected_to[x, y]))
                [trans.append(implies(bv_trans[4], clause)) for clause in t4]

                t5 = to_cnf(implies(followed_by[x, z] & ~is_linked_with_2[y, z], ~connected_to[x, y]))
                [trans.append(implies(bv_trans[5], clause)) for clause in t5]

    for x in person:
        for y in facebook_friend:
            for z in twitter_follower:
                t6 = to_cnf(implies(followed_by[x, z] & is_linked_with_3[y, z], person_facebook_friend[x, y]))
                [trans.append(implies(bv_trans[6], clause)) for clause in t6]

                t7 = to_cnf(implies(~followed_by[x, z] & is_linked_with_3[y, z], ~person_facebook_friend[x, y]))
                [trans.append(implies(bv_trans[7], clause)) for clause in t7]

                t8 = to_cnf(implies(followed_by[x, z] & ~is_linked_with_3[y, z], ~person_facebook_friend[x, y]))
                [trans.append(implies(bv_trans[8], clause)) for clause in t8]

    for x in linkedin_connection:
        for y in facebook_friend:
            for z in twitter_follower:
                t9 = to_cnf(implies(is_linked_with_2[x, z] & is_linked_with_3[y, z], is_linked_with_1[x, y]))
                [trans.append(implies(bv_trans[9], clause)) for clause in t9]

                t10 = to_cnf(implies(~is_linked_with_2[x, z] & is_linked_with_3[y, z], ~is_linked_with_1[x, y]))
                [trans.append(implies(bv_trans[10], clause)) for clause in t10]

                t11 = to_cnf(implies(is_linked_with_2[x, z] & ~is_linked_with_3[y, z], ~is_linked_with_1[x, y]))
                [trans.append(implies(bv_trans[11], clause)) for clause in t11]

    clues = []
    bv_clues = [BoolVar() for i in range(11)]

    # 0. Opal is connected to 64 LinkedIn connections
    clues.append(implies(bv_clues[0], connected_to["opal","64"]))

    # 1. The person followed by 809 Twitter followers, the person with 140 facebook friends and the person connected to 78 linkedin connections are three different people
    c1a = []
    for a in person:
        for b in person:
            for c in person:
                if not (a == b) and not (a == c) and not (b == c):
                    c1a.append(followed_by[a,"809"] & person_facebook_friend[b,"140"] & connected_to[c,"78"])

    for clause in to_cnf(any(c1a)):
        clues.append(implies(bv_clues[1], clause))

    # 2. Of rosie and neil, one is connected to 68 linkedin connections and the other is followed by 789 twitter followers
    clues.append(implies(bv_clues[2],
        (connected_to["rosie","68"] & followed_by["neil","789"]) | (connected_to["neil","68"] & followed_by["rosie","789"])
    ))

    # 3. The person connected to 57 linkedin connections has 10 facebook friends less than the person followed by 715 twitter followers
    c3a = []
    for d in person:
        for e in facebook_friend:
            for f in person:
                for g in facebook_friend:
                    if int(g) == int(e) - 10:
                        c3a.append(connected_to[d,"57"] & followed_by[f,"715"] & person_facebook_friend[f,e] & person_facebook_friend[d,g])

    for clause in to_cnf(any(c3a)):
        clues.append(implies(bv_clues[3], clause))

    # 4. Arnold isn't followed by 589 twitter followers
    clues.append(implies(bv_clues[4], ~ followed_by["arnold","589"]))

    # 5. The person followed by 809 twitter followers isn't connected to 68 linkedin connections
    c5a = []
    for h in person:
        c5a.append(followed_by[h,"809"] & ~ connected_to[h,"68"])

    for clause in to_cnf(any(c5a)):
        clues.append(implies(bv_clues[5], clause))
    # 6. Of the person connected to 57 linkedin connections and arnold, one has 140 facebook friends and the other is followed by 789 twitter followers
    c6a = []
    for i in person:
        if not (i == "arnold"):
            c6a.append(connected_to[i,"57"] & ((person_facebook_friend[i,"140"] & followed_by["arnold","789"]) | (person_facebook_friend["arnold","140"] & followed_by[i,"789"])))

    for clause in to_cnf(any(c6a)):
        clues.append(implies(bv_clues[6], clause))

    #7. opal doesn't have 150 facebook friends
    clues.append(implies(bv_clues[7], ~ person_facebook_friend["opal","150"]))

    # 8. the person connected to 57 linkedin connections has 10 facebook friends less than georgia
    c8a = []
    for j in person:
        for k in facebook_friend:
            for l in facebook_friend:
                if int(l) == int(k) - 10:
                    c8a.append(connected_to[j,"57"] & person_facebook_friend["georgia",k] & person_facebook_friend[j,l])

    for clause in to_cnf(any(c8a)):
        clues.append(implies(bv_clues[8], clause))
    # 9. The person with 130 facebook friends is either arnold or the person followed by 715 twitter followers
    c9a = []
    for m in person:
        subformula = any(
            followed_by[n,"715"] & (n == m)
            for n in person
        )
        c9a.append(person_facebook_friend[m,"130"] & (("arnold" == m) | subformula))

    for clause in to_cnf(any(c9a)):
        clues.append(implies(bv_clues[9], clause))
    # 10/ the person followed by 789 twitter followers has somewhat less than rosie
    c10a = []
    for o in person:
        for p in type1:
            for q in facebook_friend:
                for r in facebook_friend:
                    if int(p) > 0 and int(r) == int(q) - int(p):
                        c10a.append(followed_by[o,"789"] & person_facebook_friend["rosie",q] & person_facebook_friend[o,r])

    for clause in to_cnf(any(c10a)):
        clues.append(implies(bv_clues[10], clause))

    clueTexts = [
        "Opal is connected to 64 LinkedIn connections",
        "The person followed by 809 Twitter followers, the person with 140 facebook friends and the person connected to 78 linkedin connections are three different people",
        "Of rosie and neil, one is connected to 68 linkedin connections and the other is followed by 789 twitter followers",
        "The person connected to 57 linkedin connections has 10 facebook friends less than the person followed by 715 twitter followers",
        "Arnold isn't followed by 589 twitter followers",
        "The person followed by 809 twitter followers isn't connected to 68 linkedin connections",
        "Of the person connected to 57 linkedin connections and arnold, one has 140 facebook friends and the other is followed by 789 twitter followers",
        "opal doesn't have 150 facebook friends",
        "the person connected to 57 linkedin connections has 10 facebook friends less than georgia",
        "The person with 130 facebook friends is either arnold or the person followed by 715 twitter followers",
        "the person followed by 789 twitter followers has somewhat less than rosie"
    ]

    clues_cnf = cnf_to_pysat(to_cnf(clues))
    bij_cnf = cnf_to_pysat(to_cnf(bij))
    trans_cnf = cnf_to_pysat(to_cnf(trans))

    hard_clauses = [c for c in clues_cnf + bij_cnf + trans_cnf]
    soft_clauses = []
    soft_clauses += [[bv1.name + 1] for bv1 in bv_clues]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_bij]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_trans]

    weights = {}
    weights.update({bv.name + 1: 100 for bv in bv_clues})
    weights.update({bv.name + 1: 60 for bv in bv_trans})
    weights.update({bv.name + 1: 60 for bv in bv_bij})

    explainable_facts = set()
    bvRels = {}
    for rel, relStr in zip(rels, relStrs):
        rowNames = list(rel.df.index)
        columnNames = list(rel.df.columns)

        # production of explanations json file
        for r in rowNames:
            for c in columnNames:
                bvRels[rel.df.at[r, c].name + 1] = {"pred" : relStr.lower(), "subject" : r.lower(), "object": c.lower()}

        # facts to explain
        for item in rel.df.values:
            explainable_facts |= set(i.name+1 for i in item)

    matching_table = {
        'bvRel': bvRels,
        'Transitivity constraint': [bv.name + 1 for bv in bv_trans],
        'Bijectivity': [bv.name + 1 for bv in bv_bij],
        'clues' : {
            bv.name + 1: clueTexts[i] for i, bv in enumerate(bv_clues)
        },
        'types': type_dict,
        'clue_texts': clueTexts
    }

    return hard_clauses, soft_clauses, weights, explainable_facts, matching_table


def p20():
    month = ["1", "2", "3", "4", "5"]
    home  = ["the_other_home", "hughenden", "wolfenden", "markmanor", "barnhill"]
    type1 = ["the_other_type1", "circle_drive", "bird_road", "grant_place", "fifth_avenue"]
    type2 = ["the_other_type2", "victor", "lady_grey", "brunhilde", "abigail"]
    # isa int differences between values of type month
    type3 = [-1, 1, -2, 2, -3, 3, -4, 4]
    type_dict = {
        'month':month, 
        'home': home,
        'type1': type1,
        'type2': type2
    }

    types = [month, home, type1, type2]
    n = len(types)
    m = len(types[0])
    assert all(len(types[i]) == m for i in range(n)), "all types should have equal length"

    # relations between types
    investigated_in = Relation(home, month) # investigated_in(home, month)
    on = Relation(home, type1) # on(home, type1)
    haunted_by = Relation(home, type2) # haunted_by(home, type2)
    is_linked_with_1 = Relation(month, type1) # is_linked_with_1(month, type1)
    is_linked_with_2 = Relation(month, type2) # is_linked_with_2(month, type2)
    is_linked_with_3 = Relation(type1, type2) # is_linked_with_3(type1, type2)

    rels = [investigated_in, on, haunted_by, is_linked_with_1, is_linked_with_2, is_linked_with_3]

    # Bijectivity
    bij, bv_bij = buildBijectivity(rels)

    # Transitivity
    trans = []
    bv_trans =  [BoolVar() for i in range(12)]
    for x in home:
        for y in month:
            for z in type1:
                t0 = to_cnf(implies(on[x, z] & is_linked_with_1[y, z], investigated_in[x, y]))
                [trans.append(implies(bv_trans[0], clause)) for clause in t0]

                t1 = to_cnf(implies(~on[x, z] & is_linked_with_1[y, z], ~investigated_in[x, y]))
                [trans.append(implies(bv_trans[1], clause)) for clause in t1]

                t2 = to_cnf(implies(on[x, z] & ~is_linked_with_1[y, z], ~investigated_in[x, y]))
                [trans.append(implies(bv_trans[2], clause)) for clause in t2]

    for x in home:
        for y in month:
            for z in type2:
                t3 = to_cnf(implies(haunted_by[x, z] & is_linked_with_2[y, z], investigated_in[x, y]))
                [trans.append(implies(bv_trans[3], clause)) for clause in t3]

                t4 = to_cnf(implies(~haunted_by[x, z] & is_linked_with_2[y, z], ~investigated_in[x, y]))
                [trans.append(implies(bv_trans[4], clause)) for clause in t4]

                t5 = to_cnf(implies(haunted_by[x, z] & ~is_linked_with_2[y, z], ~investigated_in[x, y]))
                [trans.append(implies(bv_trans[5], clause)) for clause in t5]

    for x in home:
        for y in type1:
            for z in type2:
                t6 = to_cnf(implies(haunted_by[x, z] & is_linked_with_3[y, z], on[x, y]))
                [trans.append(implies(bv_trans[6], clause)) for clause in t6]

                t7 = to_cnf(implies(~haunted_by[x, z] & is_linked_with_3[y, z], ~on[x, y]))
                [trans.append(implies(bv_trans[7], clause)) for clause in t7]

                t8 = to_cnf(implies(haunted_by[x, z] & ~is_linked_with_3[y, z], ~on[x, y]))
                [trans.append(implies(bv_trans[8], clause)) for clause in t8]


    for x in month:
        for y in type1:
            for z in type2:
                t9 = to_cnf(implies(is_linked_with_2[x, z] & is_linked_with_3[y, z], is_linked_with_1[x, y]))
                [trans.append(implies(bv_trans[9], clause)) for clause in t9]

                t10 = to_cnf(implies(~is_linked_with_2[x, z] & is_linked_with_3[y, z], ~is_linked_with_1[x, y]))
                [trans.append(implies(bv_trans[10], clause)) for clause in t10]

                t11 = to_cnf(implies(is_linked_with_2[x, z] & ~is_linked_with_3[y, z], ~is_linked_with_1[x, y]))
                [trans.append(implies(bv_trans[11], clause)) for clause in t11]

    clues = []
    bv_clues = [BoolVar() for i in range(11)]

    # 0. The home visited in April was either Markmanor or the home haunted by Brunhilde
    c0a = []
    for q in home:
        subformula = any(
            haunted_by[r,"brunhilde"]
            for r in home if r == q
        )
        c0a.append(  investigated_in[q,"4"] & (("markmanor" == q) | subformula ))

    for clause in to_cnf(any(c0a)):
        clues.append(implies(bv_clues[0], clause))

    # # 1. Hughenden wasn't investigated in march
    clues.append(implies(bv_clues[1],  ~ investigated_in["hughenden","3"]))

    # # 2. The home on Circle Drive was investigated sometime before Wolfenden
    c2a = []
    for a in home:
        for b in type3:
            for c in month:
                for d in month:
                    if b > 0 and int(d) == int(c) - b:
                        c2a.append(on[a,"circle_drive"] & investigated_in["wolfenden",c] & investigated_in[a,d])

    for clause in to_cnf(any(c2a)):
        clues.append(implies(bv_clues[2], clause))

    # # 3. Of the building haunted by Lady Grey and the building haunted by Victor, one was Markmanor and the other was visited in January
    c3a = []
    for e in home:
        for f in home:
            if not (e == f):
                c3a.append(
                    haunted_by[e,"lady_grey"] & haunted_by[f,"victor"] & ((("markmanor" == e) & investigated_in[f,"1"]) | (("markmanor" == f) & investigated_in[e,"1"]))
                )

    for clause in to_cnf(any(c3a)):
        clues.append(implies(bv_clues[3], clause))

    # # 4. The house haunted by Victor was visited 1 month after the house haunted by Lady Grey
    c4a = []
    for g in home:
        for h in month:
            for i in home:
                for j in month:
                    if int(j) == int(h) + 1:
                        c4a.append(
                            haunted_by[g,"victor"] & haunted_by[i,"lady_grey"] & investigated_in[i,h] & investigated_in[g,j]
                        )
    
    for clause in to_cnf(any(c4a)):
        clues.append(implies(bv_clues[4], clause))

    # # 5. Of the home on Bird Road and Barnhill, one was visited in January and the other was haunted by Brunhilde
    c5a = []
    for k in home:
        if not k == "barnhill":
            c5a.append(on[k,"bird_road"] & ((investigated_in[k,"1"] & haunted_by["barnhill","brunhilde"]) | (investigated_in["barnhill","1"] & haunted_by[k,"brunhilde"])))
    
    for clause in to_cnf(any(c5a)):
        clues.append(implies(bv_clues[5], clause))

    # # 6. Markmanor was visited 1 month after the home on Grant Place
    c6a = []
    for l in month:
        for m in home:
            for n in month:
                if int(n) == int(l) + 1:
                    c6a.append(on[m,"grant_place"] & investigated_in[m,l] & investigated_in["markmanor",n])
    
    for clause in to_cnf(any(c6a)):
        clues.append(implies(bv_clues[6], clause))

    # # 7. The house visited in march wasn't located on Circle Drive
    c7a = []
    for o in home:
        c7a.append(investigated_in[o,"3"] & ~ on[o,"circle_drive"])

    for clause in to_cnf(any(c7a)):
        clues.append(implies(bv_clues[7], clause))

    # # 8. Hughenden wasn't haunted by Abigail
    clues.append(implies(bv_clues[8], ~ haunted_by["hughenden","abigail"]))

    # # 9. Wolfenden was haunted by Brunhilde
    clues.append(implies(bv_clues[9], haunted_by["wolfenden","brunhilde"]))

    # # 10. The building visited in May wasn't located on Fifth Avenue
    c10a = []
    for p in home:
        c10a.append(investigated_in[p,"5"] & ~ on[p,"fifth_avenue"])
    
    for clause in to_cnf(any(c10a)):
        clues.append(implies(bv_clues[10], clause))

    clueTexts = [
        "Hughenden wasn't investigated in march",
        "The home on Circle Drive was investigated sometime before Wolfenden",
        "Of the building haunted by Lady Grey and the building haunted by Victor, one was Markmanor and the other was visited in January",
        "The house haunted by Victor was visited 1 month after the house haunted by Lady Grey",
        "Of the home on Bird Road and Barnhill, one was visited in January and the other was haunted by Brunhilde",
        "Markmanor was visited 1 month after the home on Grant Place",
        "The house visited in march wasn't located on Circle Drive",
        "Hughenden wasn't haunted by Abigail",
        "Wolfenden was haunted by Brunhilde",
        "The building visited in May wasn't located on Fifth Avenue",
        "The home visited in April was either Markmanor or the home haunted by Brunhilde"
    ]

    clues_cnf = cnf_to_pysat(to_cnf(clues))
    bij_cnf = cnf_to_pysat(to_cnf(bij))
    trans_cnf = cnf_to_pysat(to_cnf(trans))

    hard_clauses = [c for c in clues_cnf + bij_cnf + trans_cnf]
    soft_clauses = []
    soft_clauses += [[bv1.name + 1] for bv1 in bv_clues]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_bij]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_trans]

    weights = {}
    weights.update({bv.name + 1: 100 for bv in bv_clues})
    weights.update({bv.name + 1: 60 for bv in bv_trans})
    weights.update({bv.name + 1: 60 for bv in bv_bij})

    explainable_facts = set()
    bvRels = {}
    for rel, relStr in zip(rels, ["investigated_in", "on", "haunted_by", "is_linked_with_1", "is_linked_with_2", "is_linked_with_3"]):
        rowNames = list(rel.df.index)
        columnNames = list(rel.df.columns)

        # production of explanations json file
        for r in rowNames:
            for c in columnNames:
                bvRels[rel.df.at[r, c].name + 1] = {"pred" : relStr.lower(), "subject" : r.lower(), "object": c.lower()}

        # facts to explain
        for item in rel.df.values:
            explainable_facts |= set(i.name+1 for i in item)

    matching_table = {
        'bvRel': bvRels,
        'Transitivity constraint': [bv.name + 1 for bv in bv_trans],
        'Bijectivity': [bv.name + 1 for bv in bv_bij],
        'clues' : {
            bv.name + 1: clueTexts[i] for i, bv in enumerate(bv_clues)
        },
        'types': type_dict,
        'clue_texts': clueTexts
    }

    return hard_clauses, soft_clauses, weights, explainable_facts, matching_table


def p19():
    orbital_period = ["orbital_period_1", "orbital_period_2", "orbital_period_3", "orbital_period_4", "orbital_period_5"]
    year = ["21", "30", "42", "47", "58"]
    comet = ["the_other_comet", "gostroma", "trosny", "casputi", "sporrin"]
    type1 = ["the_other_type1", "whitaker", "tillman", "underwood", "parks"]
    cycle = ["2008", "2009", "2010", "2011", "2012"]
    type_dict = {
        'orbital_period':orbital_period, 
        'year': year,
        'comet': comet,
        'type1': type1,
        'cycle': cycle        
    }
    
    types = [year, orbital_period, comet, type1, cycle]
    n = len(types)
    m = len(types[0])
    assert all(len(types[i]) == m for i in range(n)), "all types should have equal length"

    of = Relation(orbital_period, year, "of")
    has = Relation(comet, orbital_period, "has")
    discovered_by = Relation(comet, type1, "discovered_by")
    discovered_in = Relation(comet, cycle, "discoverd_in")
    is_linked_with_1 = Relation(year, comet, "is_linked_with_1")
    is_linked_with_2 = Relation(year, type1, "is_linked_with_2")
    is_linked_with_3 = Relation(year, cycle, "is_linked_with_3")
    is_linked_with_4 = Relation(orbital_period, type1, "is_linked_with_4")
    is_linked_with_5 = Relation(orbital_period, cycle, "is_linked_with_5")
    is_linked_with_6 = Relation(type1, cycle, "is_linked_with_6")

    rels = [of,
            has,
            discovered_by,
            discovered_in,
            is_linked_with_1,
            is_linked_with_2,
            is_linked_with_3,
            is_linked_with_4,
            is_linked_with_5,
            is_linked_with_6
    ]

    relStrs = [
        "of",
        "has",
        "discovered_by",
        "discovered_in",
        "is_linked_with_1",
        "is_linked_with_2",
        "is_linked_with_3",
        "is_linked_with_4",
        "is_linked_with_5",
        "is_linked_with_6"
    ]

    # Bijectivity
    bij, bv_bij = buildBijectivity(rels)

    # Transitivity
    trans = []
    bv_trans =  [BoolVar() for i in range(30)]

    # deze was missing, 'has' is wel omgedraaid...
    for x in orbital_period:
        for y in year:
            for z in comet:
                t27 = to_cnf(implies(has[z, x] & is_linked_with_1[y, z], of[x, y]))
                [trans.append(implies(bv_trans[27], clause)) for clause in t27]

                t28 = to_cnf(implies(~has[z, x] & is_linked_with_1[y, z], ~of[x, y]))
                [trans.append(implies(bv_trans[28], clause)) for clause in t28]

                t29 = to_cnf(implies(has[z, x] & ~is_linked_with_1[y, z], ~of[x, y]))
                [trans.append(implies(bv_trans[29], clause)) for clause in t29]

    for x in orbital_period:
        for y in year:
            for z in type1:
                t0 = to_cnf(implies(is_linked_with_4[x, z] & is_linked_with_2[y, z], of[x, y]))
                [trans.append(implies(bv_trans[0], clause)) for clause in t0]

                t1 = to_cnf(implies(~is_linked_with_4[x, z] & is_linked_with_2[y, z], ~of[x, y]))
                [trans.append(implies(bv_trans[1], clause)) for clause in t1]

                t2 = to_cnf(implies(is_linked_with_4[x, z] & ~is_linked_with_2[y, z], ~of[x, y]))
                [trans.append(implies(bv_trans[2], clause)) for clause in t2]

    for x in orbital_period:
        for y in year:
            for z in cycle:
                t3 = to_cnf(implies(is_linked_with_5[x, z] & is_linked_with_3[y, z], of[x, y]))
                [trans.append(implies(bv_trans[3], clause)) for clause in t3]

                t4 = to_cnf(implies(~is_linked_with_5[x, z] & is_linked_with_3[y, z], ~of[x, y]))
                [trans.append(implies(bv_trans[4], clause)) for clause in t4]

                t5 = to_cnf(implies(is_linked_with_5[x, z] & ~is_linked_with_3[y, z], ~of[x, y]))
                [trans.append(implies(bv_trans[5], clause)) for clause in t5]

    for x in comet:
        for y in orbital_period:
            for z in type1:
                t6 = to_cnf(implies(discovered_by[x, z] & is_linked_with_4[y, z], has[x, y]))
                [trans.append(implies(bv_trans[6], clause)) for clause in t6]

                t7 = to_cnf(implies(~discovered_by[x, z] & is_linked_with_4[y, z], ~has[x, y]))
                [trans.append(implies(bv_trans[7], clause)) for clause in t7]

                t8 = to_cnf(implies(discovered_by[x, z] & ~is_linked_with_4[y, z], ~has[x, y]))
                [trans.append(implies(bv_trans[8], clause)) for clause in t8]

    for x in comet:
        for y in orbital_period:
            for z in cycle:
                t9 = to_cnf(implies(discovered_in[x, z] & is_linked_with_5[y, z], has[x, y]))
                [trans.append(implies(bv_trans[9], clause)) for clause in t9]

                t10 = to_cnf(implies(~discovered_in[x, z] & is_linked_with_5[y, z], ~has[x, y]))
                [trans.append(implies(bv_trans[10], clause)) for clause in t10]

                t11 = to_cnf(implies(discovered_in[x, z] & ~is_linked_with_5[y, z], ~has[x, y]))
                [trans.append(implies(bv_trans[11], clause)) for clause in t11]
    
    for x in comet:
        for y in type1:
            for z in cycle:
                t12 = to_cnf(implies(discovered_in[x, z] & is_linked_with_6[y, z], discovered_by[x, y]))
                [trans.append(implies(bv_trans[12], clause)) for clause in t12]

                t13 = to_cnf(implies(~discovered_in[x, z] & is_linked_with_6[y, z], ~discovered_by[x, y]))
                [trans.append(implies(bv_trans[13], clause)) for clause in t13]

                t14 = to_cnf(implies(discovered_in[x, z] & ~is_linked_with_6[y, z], ~discovered_by[x, y]))
                [trans.append(implies(bv_trans[14], clause)) for clause in t14]

    for x in comet:
        for y in type1:
            for z in year:
                t15 = to_cnf(implies(is_linked_with_1[z, x] & is_linked_with_2[z, y], discovered_by[x, y]))
                [trans.append(implies(bv_trans[15], clause)) for clause in t15]

                t16 = to_cnf(implies(~is_linked_with_1[z, x] & is_linked_with_2[z, y], ~discovered_by[x, y]))
                [trans.append(implies(bv_trans[16], clause)) for clause in t16]

                t17 = to_cnf(implies(is_linked_with_1[z, x] & ~is_linked_with_2[z, y], ~discovered_by[x, y]))
                [trans.append(implies(bv_trans[17], clause)) for clause in t17]

    for x in comet:
        for y in cycle:
            for z in year:
                t18 = to_cnf(implies(is_linked_with_1[z, x] & is_linked_with_3[z, y], discovered_in[x, y]))
                [trans.append(implies(bv_trans[18], clause)) for clause in t18]

                t19 = to_cnf(implies(~is_linked_with_1[z, x] & is_linked_with_3[z, y], ~discovered_in[x, y]))
                [trans.append(implies(bv_trans[19], clause)) for clause in t19]

                t20 = to_cnf(implies(is_linked_with_1[z, x] & ~is_linked_with_3[z, y], ~discovered_in[x, y]))
                [trans.append(implies(bv_trans[20], clause)) for clause in t20]

    for x in year:
        for y in type1:
            for z in cycle:
                t21 = to_cnf(implies(is_linked_with_3[x, z] & is_linked_with_6[y, z], is_linked_with_2[x, y]))
                [trans.append(implies(bv_trans[21], clause)) for clause in t21]

                t22 = to_cnf(implies(~is_linked_with_3[x, z] & is_linked_with_6[y, z], ~is_linked_with_2[x, y]))
                [trans.append(implies(bv_trans[22], clause)) for clause in t22]

                t23 = to_cnf(implies(is_linked_with_3[x, z] & ~is_linked_with_6[y, z], ~is_linked_with_2[x, y]))
                [trans.append(implies(bv_trans[23], clause)) for clause in t23]

    for x in orbital_period:
        for y in type1:
            for z in cycle:
                t24 = to_cnf(implies(is_linked_with_5[x, z] & is_linked_with_6[y, z], is_linked_with_4[x, y]))
                [trans.append(implies(bv_trans[24], clause)) for clause in t24]

                t25 = to_cnf(implies(~is_linked_with_5[x, z] & is_linked_with_6[y, z], ~is_linked_with_4[x, y]))
                [trans.append(implies(bv_trans[25], clause)) for clause in t25]

                t26 = to_cnf(implies(is_linked_with_5[x, z] & ~is_linked_with_6[y, z], ~is_linked_with_4[x, y]))
                [trans.append(implies(bv_trans[26], clause)) for clause in t26]

    # clues
    clues = []
    bv_clues = [BoolVar() for i in range(11)]

    # fix orbital_period/year coupling
    for i in range(5):
        clues += [ of[orbital_period[i], year[i]] ]

    # 0. The comet discovered by Whitaker doesn't have an orbital period of 30 years
    c0a = []
    # manual ALT
    for a in comet:
        subformula0 = any(
            of[b,"30"] & has[a,b]
            for b in orbital_period
        )
        #c0a.append(discovered_by[a,"whitaker"] & ~ subformula0)
        c0a.append(discovered_by[a,"whitaker"] & all(~of[b,"30"] | ~has[a,b] for b in orbital_period))

    for cl in to_cnf(any(c0a)):
        clues.append(implies(bv_clues[0], cl))

    # 1. Gostroma was discovered 1 cycle after the comet discovered by Tillman
    c1a = []
    for c in cycle:
        for d in comet:
            for e in cycle:
                if int(e) ==  int(c) + 1:
                    c1a.append(discovered_by[d,"tillman"] & discovered_in[d,c] & discovered_in["gostroma",e])

    for cl in to_cnf(any(c1a)):
        clues.append(implies(bv_clues[1], cl))

    # 2. Of the comet discovered by Underwood and the comet with an orbital period of 42 years, one was found in 2009 and the other is Trosny
    c2a = []
    for f in comet:
        for g in comet:
            for h in orbital_period:
                if not (f == g):
                    #discovered_by[f,"underwood"] & of[h,"42"] & has[g,h] & ((discovered_in[f,"2009"] & ("trosny" == g)) | (discovered_in[g,"2009"] & ("trosny" == f)))
                    if f == "trosny":
                        c2a.append( discovered_by[f,"underwood"] & of[h,"42"] & has[g,h] & discovered_in[g,"2009"] )
                    elif g == "trosny":
                        c2a.append( discovered_by[f,"underwood"] & of[h,"42"] & has[g,h] & discovered_in[f,"2009"] )

    for cl in to_cnf(any(c2a)):
        clues.append(implies(bv_clues[2], cl))

    # 3. The comet with an orbital period of 21 years is either the comet discovered by Whitaker or Casputi
    c3a = []
    for i in comet:
        for j in orbital_period:
            if i == "casputi":
                c3a.append( of[j,"21"] & has[i,j] )
            else:
                c3a.append( of[j,"21"] & has[i,j] & discovered_by[i,"whitaker"] )

    for cl in to_cnf(any(c3a)):
        clues.append(implies(bv_clues[3], cl))

    # 4. The comet discovered in 2010 doesn't have an orbital period of 21 years
    c4a = []
    for l in comet:
        subformula4a = any(
            of[m,"21"] & has[l,m]
            for m in orbital_period
        )
        c4a.append(discovered_in[l,"2010"] & (~subformula4a))

    for cl in to_cnf(any(c4a)):
        clues.append(implies(bv_clues[4], cl))

    # 5. The comet discovered by Tillman, the comet discovered in 2011 and Casputi are three different comets
    c5a = []
    for n in comet:
        for o in comet:
            if (not (n == o)) and (not (n == "casputi")) and (not (o == "casputi")):
                c5a.append(discovered_by[n,"tillman"] & discovered_in[o,"2011"])

    for cl in to_cnf(any(c5a)):
        clues.append(implies(bv_clues[5], cl))

    # 6. Sporrin wasn't found in 2010
    c6a = [~discovered_in["sporrin","2010"]]
    for cl in to_cnf(any(c6a)):
        clues.append(implies(bv_clues[6], cl))

    # 7. Whitaker's comet was discovered in 2010
    c7a = []
    for p in comet:
        c7a.append(discovered_in[p,"2010"] & discovered_by[p,"whitaker"])

    for cl in to_cnf(any(c7a)):
        clues.append(implies(bv_clues[7], cl))

    # 8. The comet discovered by Parks was discovered 1 cycle before Whitaker's comet
    c8a = []
    for q in comet:
        for r in cycle:
            for s in comet:
                for t in cycle:
                    if int(t) == int(r) - 1:
                        c8a.append(discovered_by[q,"parks"] & discovered_in[s,r] & discovered_by[s,"whitaker"]& discovered_in[q,t])

    for cl in to_cnf(any(c8a)):
        clues.append(implies(bv_clues[8], cl))

    # 9. The comet discovered in 2011 doesn't have an orbital period of 47 years
    c9a = []
    for u in comet:
        subformula9 = any(
            of[v, "47"] & has[u,v]
            for v in orbital_period
        )
        c9a.append(discovered_in[u,"2011"] & ~subformula9)

    for cl in to_cnf(any(c9a)):
        clues.append(implies(bv_clues[9], cl))

    # 10. The comet discovered by Underwood has an orbital period of either 47 or 58 years
    c10a = []
    for w in comet:
        for x in orbital_period:
            c10a.append(discovered_by[w,"underwood"] & (of[x,"47"] | of[x,"58"]) & has[w,x])

    for cl in to_cnf(any(c10a)):
        clues.append(implies(bv_clues[10], cl))

    clueTexts = [
        "The comet discovered by Whitaker doesn't have an orbital period of 30 years",
        "Gostroma was discovered 1 cycle after the comet discovered by Tillman",
        "Of the comet discovered by Underwood and the comet with an orbital period of 42 years, one was found in 2009 and the other is Trosny",
        "The comet with an orbital period of 21 years is either the comet discovered by Whitaker or Casputi",
        "The comet discovered in 2010 doesn't have an orbital period of 21 years",
        "The comet discovered by Tillman, the comet discovered in 2011 and Casputi are three different comets",
        "Sporrin wasn't found in 2010",
        "Whitaker's comet was discovered in 2010",
        "The comet discovered by Parks was discovered 1 cycle before Whitaker's comet",
        "The comet discovered in 2011 doesn't have an orbital period of 47 years",
        "The comet discovered by Underwood has an orbital period of either 47 or 58 years"
    ]

    clues_cnf = cnf_to_pysat(to_cnf(clues))
    bij_cnf = cnf_to_pysat(to_cnf(bij))
    trans_cnf = cnf_to_pysat(to_cnf(trans))

    hard_clauses = [c for c in clues_cnf + bij_cnf + trans_cnf]
    soft_clauses = []
    soft_clauses += [[bv1.name + 1] for bv1 in bv_clues]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_bij]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_trans]

    weights = {}
    weights.update({bv.name + 1: 100 for bv in bv_clues})
    weights.update({bv.name + 1: 60 for bv in bv_trans})
    weights.update({bv.name + 1: 60 for bv in bv_bij})

    explainable_facts = set()
    bvRels = {}
    for rel, relStr in zip(rels, relStrs):
        rowNames = list(rel.df.index)
        columnNames = list(rel.df.columns)

        # production of explanations json file
        for r in rowNames:
            for c in columnNames:
                bvRels[rel.df.at[r, c].name + 1] = {"pred" : relStr.lower(), "subject" : r.lower(), "object": c.lower()}

        # facts to explain
        for item in rel.df.values:
            explainable_facts |= set(i.name+1 for i in item)

    matching_table = {
        'bvRel': bvRels,
        'Transitivity constraint': [bv.name + 1 for bv in bv_trans],
        'Bijectivity': [bv.name + 1 for bv in bv_bij],
        'clues' : {
            bv.name + 1: clueTexts[i] for i, bv in enumerate(bv_clues)
        },
        'types': type_dict,
        'clue_texts': clueTexts
    }

    return hard_clauses, soft_clauses, weights, explainable_facts, matching_table


def p25():
    month = ["3", "4", "5", "6", "7"]
    application = ["the_other_application", "flowcarts", "vitalinks", "bubble_boms", "angry_ants"]
    type1 = ["the_other_type1", "vortia", "apptastic", "gadingo", "digibits"]
    download = ["2300000", "4200000", "5500000", "6800000", "8900000"]
    type_dict = {
        'month':month, 
        'application': application,
        'download': download,
        'type1': type1,     
    }
    types = [month, application, type1, download]
    n = len(types)
    m = len(types[0])
    assert all(len(types[i]) == m for i in range(n)), "all types should have equal length"

    released_in = Relation(application, month) # released_in(application, month)
    made_by = Relation(application, type1) # made_by(application, type1)
    application_download = Relation(application, download) # with(application, download)
    is_linked_with_1 = Relation(month, type1) # is_linked_with_1(month, type1)
    is_linked_with_2 = Relation(month, download) # is_linked_with_2(month, download)
    is_linked_with_3 = Relation(type1, download) # is_linked_with_3(type1, download)

    rels = [released_in, made_by, application_download, is_linked_with_1, is_linked_with_2, is_linked_with_3]

    # Bijectivity
    bij, bv_bij = buildBijectivity(rels)


    # Transitivity
    trans = []
    bv_trans =  [BoolVar() for i in range(12)]
    for x in application:
        for y in month:
            for z in type1:
                t0 = to_cnf(implies(made_by[x, z] & is_linked_with_1[y, z], released_in[x, y]))
                [trans.append(implies(bv_trans[0], clause)) for clause in t0]

                t1 = to_cnf(implies(~made_by[x, z] & is_linked_with_1[y, z], ~released_in[x, y]))
                [trans.append(implies(bv_trans[1], clause)) for clause in t1]

                t2 = to_cnf(implies(made_by[x, z] & ~is_linked_with_1[y, z], ~released_in[x, y]))
                [trans.append(implies(bv_trans[2], clause)) for clause in t2]

    for x in application:
        for y in month:
            for z in download:
                t3 = to_cnf(implies(application_download[x, z] & is_linked_with_2[y, z], released_in[x, y]))
                [trans.append(implies(bv_trans[3], clause)) for clause in t3]

                t4 = to_cnf(implies(~application_download[x, z] & is_linked_with_2[y, z], ~released_in[x, y]))
                [trans.append(implies(bv_trans[4], clause)) for clause in t4]

                t5 = to_cnf(implies(application_download[x, z] & ~is_linked_with_2[y, z], ~released_in[x, y]))
                [trans.append(implies(bv_trans[5], clause)) for clause in t5]

    for x in application:
        for y in type1:
            for z in download:
                t6 = to_cnf(implies(application_download[x, z] & is_linked_with_3[y, z], made_by[x, y]))
                [trans.append(implies(bv_trans[6], clause)) for clause in t6]

                t7 = to_cnf(implies(~application_download[x, z] & is_linked_with_3[y, z], ~made_by[x, y]))
                [trans.append(implies(bv_trans[7], clause)) for clause in t7]

                t8 = to_cnf(implies(application_download[x, z] & ~is_linked_with_3[y, z], ~made_by[x, y]))
                [trans.append(implies(bv_trans[8], clause)) for clause in t8]

    for x in month:
        for y in type1:
            for z in download:
                t9 = to_cnf(implies(is_linked_with_2[x, z] & is_linked_with_3[y, z], is_linked_with_1[x, y]))
                [trans.append(implies(bv_trans[9], clause)) for clause in t9]

                t10 = to_cnf(implies(~is_linked_with_2[x, z] & is_linked_with_3[y, z], ~is_linked_with_1[x, y]))
                [trans.append(implies(bv_trans[10], clause)) for clause in t10]

                t11 = to_cnf(implies(is_linked_with_2[x, z] & ~is_linked_with_3[y, z], ~is_linked_with_1[x, y]))
                [trans.append(implies(bv_trans[11], clause)) for clause in t11]

    # clues
    clues = []
    bv_clues = [BoolVar() for i in range(8)]

    # .Of Flowcarts and the application with 5500000 downloads, one was made by Vortia and the other was released in May
    c0a = []
    for a in application:
        if not ("flowcarts" == a):
            c0a.append(application_download[a,"5500000"] & ((made_by["flowcarts","vortia"] & released_in[a,"5"]) | (made_by[a,"vortia"] & released_in["flowcarts","5"])))

    for cl in to_cnf(any(c0a)):
        clues.append(implies(bv_clues[0], cl))

    # .The app released in July, the app developed by Apptastic and Vitalinks are three different games
    c1a = []
    for b in application:
        for c in application:
            if (not (b == c)) and (not (b == "vitalinks")) and (not(c == "vitalinks")):
                c1a.append(released_in[b,"7"] & made_by[c,"apptastic"])
    
    for cl in to_cnf(any(c1a)):
        clues.append(implies(bv_clues[1], cl))

    # .Neither the game released by Gadingo nor the apptastic app has 2300000 downloads
    c2a = []
    for d in application:
        subformula = any(
            application_download[e, "2300000"]  & made_by[e,"apptastic"]
            for e in application
        )
        c2a.append(made_by[d,"gadingo"] & application_download[d,"2300000"] & ~ subformula)

    for cl in to_cnf(any(c2a)):
        clues.append(implies(bv_clues[2], cl))

    # .The five apps are Bubble Boms, the app released in April, the app released in July, the application released by Apptastic and the app released by Digibits
    c3a = []
    for f in application:
        for g in application:
            for h in application:
                for i in application:
                    if (not ("bubble_boms" == f)) and (not("bubble_boms" == g)) and  (not("bubble_boms" == h)) and (not("bubble_boms" == i)) and (not(f == g)) and (not (f == h)) and (not (f == i)) and (not (g == h)) and (not (g == i)) and (not (h == i)):
                        c3a.append(
                            released_in[f,"4"] & released_in[g,"7"] & made_by[h,"apptastic"] & made_by[i,"digibits"]
                        )
    for cl in to_cnf(any(c3a)):
        clues.append(implies(bv_clues[3], cl))

    # .Vortia's app came out in march
    c4a = []
    for j in application:
        c4a.append(released_in[j,"3"] & made_by[j,"vortia"])
    
    for cl in to_cnf(any(c4a)):
        clues.append(implies(bv_clues[4], cl))

    # .Angry Ants was released 2 months earlier than the app with 6800000 downloads
    c5a = []
    for k in month:
        for l in application:
            for m in month:
                if int(m) == int(k) - 2:
                    c5a.append(
                        application_download[l,"6800000"] & released_in[l,k] & released_in["angry_ants",m]
                    )
    for cl in to_cnf(any(c5a)):
        clues.append(implies(bv_clues[5], cl))

    # .Flowcarts doesn't have 4200000 downloads
    clues.append(implies(bv_clues[6], ~application_download["flowcarts","4200000"]))

    # .The game released in July is either the game with 6800000 downloads or the app released by Gadingo
    c7a = []
    for n in application:
        subformula1=any(
            application_download[o, "6800000"]
            for o in application if o == n
        )
        subformula2=any(
            made_by[p,"gadingo"]
            for p in application if p == n
        )
        c7a.append(released_in[n,"7"] & (subformula1 | subformula2))

    for cl in to_cnf(any(c7a)):
        clues.append(implies(bv_clues[7], cl))

    clueTexts = [
        "Of Flowcarts and the application with 5500000 downloads, one was made by Vortia and the other was released in May",
        "The app released in July, the app developed by Apptastic and Vitalinks are three different games",
        "Neither the game released by Gadingo nor the apptastic app has 2300000 downloads",
        "The five apps are Bubble Boms, the app released in April, the app released in July, the application released by Apptastic and the app released by Digibits",
        "Vortia's app came out in march",
        "Angry Ants was released 2 months earlier than the app with 6800000 downloads",
        "Flowcarts doesn't have 4200000 downloads",
        "The game released in July is either the game with 6800000 downloads or the app released by Gadingo"
    ]

    clues_cnf = cnf_to_pysat(to_cnf(clues))
    bij_cnf = cnf_to_pysat(to_cnf(bij))
    trans_cnf = cnf_to_pysat(to_cnf(trans))

    hard_clauses = [c for c in clues_cnf + bij_cnf + trans_cnf]
    soft_clauses = []
    soft_clauses += [[bv1.name + 1] for bv1 in bv_clues]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_bij]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_trans]

    weights = {}
    weights.update({bv.name + 1: 100 for bv in bv_clues})
    weights.update({bv.name + 1: 60 for bv in bv_trans})
    weights.update({bv.name + 1: 60 for bv in bv_bij})

    explainable_facts = set()
    bvRels = {}
    for rel, relStr in zip(rels, ["released_in", "made_by", "application_download", "is_linked_with_1", "is_linked_with_2", "is_linked_with_3"]):
        rowNames = list(rel.df.index)
        columnNames = list(rel.df.columns)

        # production of explanations json file
        for r in rowNames:
            for c in columnNames:
                bvRels[rel.df.at[r, c].name + 1] = {"pred" : relStr.lower(), "subject" : r.lower(), "object": c.lower()}

        # facts to explain
        for item in rel.df.values:
            explainable_facts |= set(i.name+1 for i in item)

    matching_table = {
        'bvRel': bvRels,
        'Transitivity constraint': [bv.name + 1 for bv in bv_trans],
        'Bijectivity': [bv.name + 1 for bv in bv_bij],
        'clues' : {
            bv.name + 1: clueTexts[i] for i, bv in enumerate(bv_clues)
        },
        'types': type_dict,
        'clue_texts': clueTexts
    }

    return hard_clauses, soft_clauses, weights, explainable_facts, matching_table


def p18():
    type1 = ["the_other_type1", "glendale", "olema", "evansdale", "lakota"]
    person = ["the_other_person", "al_allen", "kelly_kirby", "bev_baird", "ed_ewing"]
    candidate = ["the_other_candidate", "academic", "teacher", "writer", "doctor"]
    vote = ["8500", "9000", "9500", "10000", "10500"] # isa int
    type2 = [-500, 500, -1000, 1000, -1500, 1500, -2000, 2000] # differences between values of type vote
    type_dict = {
        'person':person, 
        'candidate': candidate,
        'vote': vote,
        'type1': type1,     
    }
    types = [type1, person, candidate, vote]
    n = len(types)
    m = len(types[0])
    assert all(len(types[i]) == m for i in range(n)), "all types should have equal length"

    person_type1 = Relation(person, type1) # from(person, type1)
    acts_as = Relation(person, candidate) # acts_as(person, candidate)
    finished_with = Relation(person, vote) # finished_with(person, vote)
    received = Relation(candidate, vote) # received(candidate, vote)
    is_linked_with_1 = Relation(type1, candidate) # is_linked_with_1(type1, candidate)
    is_linked_with_2 = Relation(type1, vote) # is_linked_with_2(type1, vote)

    rels = [person_type1, acts_as, finished_with, received, is_linked_with_1, is_linked_with_2]

    # Bijectivity
    bij, bv_bij = buildBijectivity(rels)

    # Transitivity
    trans = []
    bv_trans =  [BoolVar() for i in range(12)]
    for x in person:
        for y in type1:
            for z in candidate:
                t0 = to_cnf(implies(acts_as[x, z] & is_linked_with_1[y, z], person_type1[x, y]))
                [trans.append(implies(bv_trans[0], clause)) for clause in t0]

                t1 = to_cnf(implies(~acts_as[x, z] & is_linked_with_1[y, z], ~person_type1[x, y]))
                [trans.append(implies(bv_trans[1], clause)) for clause in t1]

                t2 = to_cnf(implies(acts_as[x, z] & ~is_linked_with_1[y, z], ~person_type1[x, y]))
                [trans.append(implies(bv_trans[2], clause)) for clause in t2]

    for x in person:
        for y in type1:
            for z in vote:
                t3 = to_cnf(implies(finished_with[x, z] & is_linked_with_2[y, z], person_type1[x, y]))
                [trans.append(implies(bv_trans[3], clause)) for clause in t3]

                t4 = to_cnf(implies(~finished_with[x, z] & is_linked_with_2[y, z], ~person_type1[x, y]))
                [trans.append(implies(bv_trans[4], clause)) for clause in t4]

                t5 = to_cnf(implies(finished_with[x, z] & ~is_linked_with_2[y, z], ~person_type1[x, y]))
                [trans.append(implies(bv_trans[5], clause)) for clause in t5]

    for x in person:
        for y in candidate:
            for z in vote:
                t6 = to_cnf(implies(finished_with[x, z] & received[y, z], acts_as[x, y]))
                [trans.append(implies(bv_trans[6], clause)) for clause in t6]

                t7 = to_cnf(implies(~finished_with[x, z] & received[y, z], ~acts_as[x, y]))
                [trans.append(implies(bv_trans[7], clause)) for clause in t7]

                t8 = to_cnf(implies(finished_with[x, z] & ~received[y, z], ~acts_as[x, y]))
                [trans.append(implies(bv_trans[8], clause)) for clause in t8]

    for x in candidate:
        for y in vote:
            for z in type1:
                t9 = to_cnf(implies(is_linked_with_1[z, x] & is_linked_with_2[z, y], received[x, y]))
                [trans.append(implies(bv_trans[9], clause)) for clause in t9]

                t10 = to_cnf(implies(~is_linked_with_1[z, x] & is_linked_with_2[z, y], ~received[x, y]))
                [trans.append(implies(bv_trans[10], clause)) for clause in t10]

                t11 = to_cnf(implies(is_linked_with_1[z, x] & ~is_linked_with_2[z, y], ~received[x, y]))
                [trans.append(implies(bv_trans[11], clause)) for clause in t11]

    clues = []
    bv_clues = [BoolVar() for i in range(12)]

    # 0. Al allen is from glendale
    clues.append(implies(bv_clues[0], person_type1["al_allen","glendale"]))

    # # 1. Kelly Kirby finished 1000 votes ahead of the person who acts as the academic
    c1a = []
    for a in vote:
        for b in person:
            for c in vote:
                if int(c) == int(a) + 1000:
                    c1a.append(acts_as[b,"academic"] & finished_with[b,a] & finished_with["kelly_kirby",c])

    for cl in to_cnf(any(c1a)):
        clues.append(implies(bv_clues[1], cl))
    # # 2.The academic received 500 votes less than the teacher
    c2a = []
    for d in vote:
        for e in vote:
            if int(e) == int(d) - 500:
                c2a.append(received["teacher",d] & received["academic",e])

    for cl in to_cnf(any(c2a)):
        clues.append(implies(bv_clues[2], cl))

    # # 3. The candidate who received 10500 votes isn't the writer
    c3a = []
    for f in candidate:
        if not ("writer" == f):
            c3a.append(received[f, "10500"])

    for cl in to_cnf(any(c3a)):
        clues.append(implies(bv_clues[3], cl))
    # 4. Kelly Kirby isn't from Olema
    clues.append(implies(bv_clues[4],  ~ person_type1["kelly_kirby","olema"]))

    # # 5. The glendale native finished somewhat ahead of the Olema native
    c5a = []
    for g in person:
        for h in type2:
            for i in vote:
                for j in person:
                    for k in vote:
                        if int(h) > 0 and int(k) == int(i) + int(h):
                            c5a.append(finished_with[j,i] & person_type1[j,"olema"] & finished_with[g,k] & person_type1[g,"glendale"])

    for cl in to_cnf(any(c5a)):
        clues.append(implies(bv_clues[5], cl))
    # # 6. Bev Baird ended up with 8500 votes
    clues.append(implies(bv_clues[6],  finished_with["bev_baird","8500"]))

    # # 7. Ed Ewing finished 500 votes ahead of the Evansdale native
    c7a = []
    for l in vote:
        for m in person:
            for n in vote:
                if int(n) == int(l) + 500:
                    c7a.append(finished_with[m,l] & person_type1[m,"evansdale"] & finished_with["ed_ewing",n])

    for cl in to_cnf(any(c7a)):
        clues.append(implies(bv_clues[7], cl))
    # # 8. The man who received 9500 votes isn't the doctor

    c8a = []
    for o in candidate:
        if not (o == "doctor"):
            c8a.append(received[o,"9500"])

    for cl in to_cnf(any(c8a)):
        clues.append(implies(bv_clues[8], cl))
    # # 9. Of the person acting as academic and Al Allen, one ended up with 10000 votes and the other ended up with 8500 votes
    c9a = []
    for p in person:
        if not (p == "al_allen"):
            c9a.append(acts_as[p,"academic"] & ((finished_with[p,"10000"] & finished_with["al_allen","8500"]) | (finished_with["al_allen","10000"] & finished_with[p,"8500"])))

    for cl in to_cnf(any(c9a)):
        clues.append(implies(bv_clues[9], cl))
    # # 10. The politician who finished with 10500 votes isn't from Lakota
    c10a = []
    for q in person:
        c10a.append(finished_with[q,"10500"] & ~ person_type1[q,"lakota"])

    for cl in to_cnf(any(c10a)):
        clues.append(implies(bv_clues[10], cl))
    # # 11. The person acting as doctor was either the politician who finished with 10000 votes or Kelly Kirby
    c11a = []
    for r in person:
        subformula = any(
            finished_with[s,"10000"] & (s == r)
            for s in person
        )
        c11a.append(acts_as[r,"doctor"] & (subformula | ("kelly_kirby" == r)))

    for cl in to_cnf(any(c11a)):
        clues.append(implies(bv_clues[11], cl))

    clueTexts =[
        "Al allen is from glendale",
        "Kelly Kirby finished 1000 votes ahead of the person who acts as the academic",
        "The academic received 500 votes less than the teacher",
        "The candidate who received 10500 votes isn't the writer",
        "Kelly Kirby isn't from Olema",
        "The glendale native finished somewhat ahead of the Olema native",
        "Bev Baird ended up with 8500 votes",
        "Ed Ewing finished 500 votes ahead of the Evansdale native",
        "The man who received 9500 votes isn't the doctor",
        "Of the person acting as academic and Al Allen, one ended up with 10000 votes and the other ended up with 8500 votes",
        "The politician who finished with 10500 votes isn't from Lakota",
        "The person acting as doctor was either the politician who finished with 10000 votes or Kelly Kirby"
    ]

    clues_cnf = cnf_to_pysat(to_cnf(clues))
    bij_cnf = cnf_to_pysat(to_cnf(bij))
    trans_cnf = cnf_to_pysat(to_cnf(trans))

    hard_clauses = [c for c in clues_cnf + bij_cnf + trans_cnf]
    soft_clauses = []
    soft_clauses += [[bv1.name + 1] for bv1 in bv_clues]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_bij]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_trans]

    weights = {}
    weights.update({bv.name + 1: 100 for bv in bv_clues})
    weights.update({bv.name + 1: 60 for bv in bv_trans})
    weights.update({bv.name + 1: 60 for bv in bv_bij})

    explainable_facts = set()
    bvRels = {}
    for rel, relStr in zip(rels, ["person_type1", "acts_as", "finished_with", "received", "is_linked_with_1", "is_linked_with_2"]):
        rowNames = list(rel.df.index)
        columnNames = list(rel.df.columns)

        # production of explanations json file
        for r in rowNames:
            for c in columnNames:
                bvRels[rel.df.at[r, c].name + 1] = {"pred" : relStr.lower(), "subject" : r.lower(), "object": c.lower()}

        # facts to explain
        for item in rel.df.values:
            explainable_facts |= set(i.name+1 for i in item)

    matching_table = {
        'bvRel': bvRels,
        'Transitivity constraint': [bv.name + 1 for bv in bv_trans],
        'Bijectivity': [bv.name + 1 for bv in bv_bij],
        'clues' : {
            bv.name + 1: clueTexts[i] for i, bv in enumerate(bv_clues)
        },
        'types': type_dict,
        'clue_texts': clueTexts
    }

    return hard_clauses, soft_clauses, weights, explainable_facts, matching_table


def p16():
    type1 = ["the_other_type1", "rings", "mobile_phones", "flashlights", "rubber_balls"]
    juggler = ["the_other_juggler", "howard", "otis", "gerald", "floyd"]
    type2 = ["the_other_type2", "quasqueton", "kingsburg", "carbon", "nice"]
    spot = ["1", "2", "3", "4", "5"]
    type_dict = {
        'spot':spot, 
        'juggler': juggler,
        'type2': type2,
        'type1': type1,     
    }
    used = Relation(juggler, type1)
    juggler_type2 = Relation(juggler, type2) #from
    went = Relation(juggler, spot) 
    type1_type2 = Relation(type1, type2) #is_linked_with_1
    type1_spot = Relation(type1, spot) #is_linked_with_2
    type2_spot = Relation(type2, spot) #is_linked_with_3

    types = [type1, juggler, type2, spot]
    n = len(types)
    m = len(types[0])
    assert all(len(types[i]) == m for i in range(n)), "all types should have equal length"

    rels = [used, juggler_type2, went, type1_type2, type1_spot, type2_spot]

    # Bijectivity
    bij, bv_bij = buildBijectivity(rels)

    # Transitivity
    trans = []
    bv_trans =  [BoolVar() for i in range(12)]
    for x in juggler:
        for y in type1:
            for z in type2:
                t0 = to_cnf(implies(juggler_type2[x, z] & type1_type2[y, z], used[x, y]))
                [trans.append(implies(bv_trans[0], clause)) for clause in t0]

                t1 = to_cnf(implies(~juggler_type2[x, z] & type1_type2[y, z], ~used[x, y]))
                [trans.append(implies(bv_trans[1], clause)) for clause in t1]

                t2 = to_cnf(implies(juggler_type2[x, z] & ~type1_type2[y, z], ~used[x, y]))
                [trans.append(implies(bv_trans[2], clause)) for clause in t2]

    for x in juggler:
        for y in type1:
            for z in spot:
                t3 = to_cnf(implies(went[x, z] & type1_spot[y, z], used[x, y]))
                [trans.append(implies(bv_trans[3], clause)) for clause in t3]

                t4 = to_cnf(implies(~went[x, z] & type1_spot[y, z], ~used[x, y]))
                [trans.append(implies(bv_trans[4], clause)) for clause in t4]

                t5 = to_cnf(implies(went[x, z] & ~type1_spot[y, z], ~used[x, y]))
                [trans.append(implies(bv_trans[5], clause)) for clause in t5]

    for x in juggler:
        for y in type2:
            for z in spot:
                t6 = to_cnf(implies(went[x, z] & type2_spot[y, z], juggler_type2[x, y]))
                [trans.append(implies(bv_trans[6], clause)) for clause in t6]

                t7 = to_cnf(implies(~went[x, z] & type2_spot[y, z], ~juggler_type2[x, y]))
                [trans.append(implies(bv_trans[7], clause)) for clause in t7]

                t8 = to_cnf(implies(went[x, z] & ~type2_spot[y, z], ~juggler_type2[x, y]))
                [trans.append(implies(bv_trans[8], clause)) for clause in t8]

    for x in type1:
        for y in type2:
            for z in spot:
                t9 = to_cnf(implies(type1_spot[x, z] & type2_spot[y, z], type1_type2[x, y]))
                [trans.append(implies(bv_trans[9], clause)) for clause in t9]

                t10 = to_cnf(implies(~type1_spot[x, z] & type2_spot[y, z], ~type1_type2[x, y]))
                [trans.append(implies(bv_trans[10], clause)) for clause in t10]

                t11 = to_cnf(implies(type1_spot[x, z] & ~type2_spot[y, z], ~type1_type2[x, y]))
                [trans.append(implies(bv_trans[11], clause)) for clause in t11]

    clues = []
    bv_clues = [BoolVar() for i in range(10)]
    # 0. The juggler who went fourth was either the performer from Quasqueton or the juggler who used rings
    c0a = []
    for a in juggler:
        formule1 = any(
            juggler_type2[b,"quasqueton"] & (b == a)
            for b in juggler
        )
        formule2 = any(
            used[c, "rings"] & (c == a)
            for c in juggler
        )
        c0a.append(went[a, "4"] & (formule1 | formule2))

    for cl in to_cnf(any(c0a)):
        clues.append(implies(bv_clues[0], cl))
    # # 1. The juggler who used flashlights performed one spot after the person who used mobile phones
    c1a = []
    for d in juggler:
        for e in spot:
            for f in juggler:
                for g in spot:
                    if (int(g) == int(e) + 1):
                        c1a.append(used[d,"flashlights"] & used[f,"mobile_phones"] & went[f,e] & went[d,g])

    for cl in to_cnf(any(c1a)):
        clues.append(implies(bv_clues[1], cl))

    # # 2. The performer from Kingsburg performed one spot before Howard
    c2a = []
    for h in juggler:
        for i in spot:
            for j in spot:
                if (int(j) == int(i) - 1):
                    c2a.append(juggler_type2[h,"kingsburg"] & went["howard",i] & went[h,j])

    for cl in to_cnf(any(c2a)):
        clues.append(implies(bv_clues[2], cl))

    # # 3. Otis wasn't from Carbon
    clues.append(implies(bv_clues[3], juggler_type2["otis","carbon"]))

    # # 4. Of the performer who went second and the juggler who used rings, one was from Carbon and the other is Howard
    c4a = []
    for k in juggler:
        for l in juggler:
            if not (k == l):
                c4a.append(went[k,"2"] & used[l,"rings"] & ((juggler_type2[k,"carbon"] & ("howard" == l)) | (juggler_type2[l,"carbon"] & ("howard" == k))))
    # print(any(c4a))
    # print(to_cnf(any(c4a)))

    for cl in to_cnf(any(c4a)):
        clues.append(implies(bv_clues[4], cl))

    # # 5. The performer who went third, Gerald and the person from Kingsburg are three different people
    c5a = []
    for m in juggler:
        for n in juggler:
            if not (m == "gerald") and not(m == n) and not("gerald" == n):
                c5a.append(went[m,"3"] & juggler_type2[n,"kingsburg"])

    for cl in to_cnf(any(c5a)):
        clues.append(implies(bv_clues[5], cl))
    # # 6. Floyd was either the juggler who went second or the juggler from Quasqueton
    c6a = []
    for o in juggler:
        c6a.append(went[o,"2"] & (o == "floyd"))

    c6b = []
    for p in juggler:
        c6b.append(juggler_type2[p,"quasqueton"] & (p == "floyd"))

    for cl in to_cnf(any(c6a) | any(c6b)):
        clues.append(implies(bv_clues[6], cl))

    # # 7. The person who went third used rings
    c7a = []
    for q in juggler:
        c7a.append(went[q,"3"] & used[q,"rings"])

    for cl in to_cnf(any(c7a)):
        clues.append(implies(bv_clues[7], cl))

    # # 8. The juggler who went second wasn't from Nice
    c8a = []
    for r in juggler:
        c8a.append(went[r, "2"] & ~juggler_type2[r, "nice"])

    for cl in to_cnf(any(c8a)):
        clues.append(implies(bv_clues[8], cl))

    # # 9. Floyd juggles rubber balls
    clues.append(implies(bv_clues[9], used["floyd","rubber_balls"]))


    clueTexts =[
        "The juggler who went fourth was either the performer from Quasqueton or the juggler who used rings",
        "The juggler who used flashlights performed one spot after the person who used mobile phones",
        "The performer from Kingsburg performed one spot before Howard",
        "Otis wasn't from Carbon",
        "Of the performer who went second and the juggler who used rings, one was from Carbon and the other is Howard",
        "The performer who went third, Gerald and the person from Kingsburg are three different people",
        "Floyd was either the juggler who went second or the juggler from Quasqueton",
        "The person who went third used rings",
        "The juggler who went second wasn't from Nice",
        "Floyd juggles rubber balls"
    ]

    clues_cnf = cnf_to_pysat(to_cnf(clues))
    bij_cnf = cnf_to_pysat(to_cnf(bij))
    trans_cnf = cnf_to_pysat(to_cnf(trans))

    hard_clauses = [c for c in clues_cnf + bij_cnf + trans_cnf]
    soft_clauses = []
    soft_clauses += [[bv1.name + 1] for bv1 in bv_clues]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_bij]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_trans]

    weights = {}
    weights.update({bv.name + 1: 100 for bv in bv_clues})
    weights.update({bv.name + 1: 60 for bv in bv_trans})
    weights.update({bv.name + 1: 60 for bv in bv_bij})

    explainable_facts = set()
    bvRels = {}
    for rel, relStr in zip(rels, ["used", "juggler_type2", "went", "type1_type2", "type1_spot", "type2_spot"]):
        rowNames = list(rel.df.index)
        columnNames = list(rel.df.columns)

        # production of explanations json file
        for r in rowNames:
            for c in columnNames:
                bvRels[rel.df.at[r, c].name + 1] = {"pred" : relStr.lower(), "subject" : r.lower(), "object": c.lower()}

        # facts to explain
        for item in rel.df.values:
            explainable_facts |= set(i.name+1 for i in item)

    matching_table = {
        'bvRel': bvRels,
        'Transitivity constraint': [bv.name + 1 for bv in bv_trans],
        'Bijectivity': [bv.name + 1 for bv in bv_bij],
        'clues' : {
            bv.name + 1: clueTexts[i] for i, bv in enumerate(bv_clues)
        },
        'types': type_dict,
        'clue_texts': clueTexts
    }

    return hard_clauses, soft_clauses, weights, explainable_facts, matching_table


def p13():
    dollar = ["750", "1000", "1250", "1500", "1750"]
    piece = ["the_other_piece", "valencia", "waldarama", "tombawomba", "sniffletoe"]
    person = ["kelly", "isabel", "lucas", "nicole", "herman"]
    city = ["the_other_type2", "vancouver", "ypsilanti", "mexico_city", "st_moritz"]
    diffdollar = [-250, 250, -500, 500, -750, 750, -1000, 1000]
    type_dict = {
        'dollar':dollar, 
        'piece': piece,
        'person': person,
        'city': city,     
    }

    types = [dollar, piece, person, city]
    n = len(types)
    m = len(types[0])
    assert all(len(types[i]) == m for i in range(n)), "all types should have equal length"

    #type1 = person
    #type2 = city
    #type3 = diffdollar

    # from(piece, type1) = piece_person  = Relation(piece, person)
    # is_linked_with_1(dollar, type1)     dollar_person = Relation(dollar, person)
    # is_linked_with_2(dollar, type2)    dollar_city = Relation(dollar, city)
    # is_linked_with_3(type1, type2)    person_city = Relation(person, city)

    cost = Relation(piece, dollar)
    go_to = Relation(piece, city)
    piece_person = Relation(piece, person)
    dollar_person = Relation(dollar, person)
    dollar_city = Relation(dollar, city)
    person_city = Relation(person, city)
    rels = [cost, go_to, piece_person, dollar_person, dollar_city, person_city]

    # Bijectivity
    bij, bv_bij = buildBijectivity(rels)

    # Transitivity
    trans = []
    bv_trans =  [BoolVar() for i in range(12)]

    for x in piece:
        for y in dollar:
            for z in city:
                t0 = to_cnf(implies(go_to[x, z] & dollar_city[y, z], cost[x, y]))
                [trans.append(implies(bv_trans[0], clause)) for clause in t0]

                t1 = to_cnf(implies(~go_to[x, z] & dollar_city[y, z], ~cost[x, y]))
                [trans.append(implies(bv_trans[1], clause)) for clause in t1]

                t2 = to_cnf(implies(go_to[x, z] & ~dollar_city[y, z], ~cost[x, y]))
                [trans.append(implies(bv_trans[2], clause)) for clause in t2]

    for x in piece:
        for y in dollar:
            for z in person:
                t3 = to_cnf(implies(piece_person[x, z] & dollar_person[y, z], cost[x, y]))
                [trans.append(implies(bv_trans[3], clause)) for clause in t3]

                t4 = to_cnf(implies(~piece_person[x, z] & dollar_person[y, z], ~cost[x, y]))
                [trans.append(implies(bv_trans[4], clause)) for clause in t4]

                t5 = to_cnf(implies(piece_person[x, z] & ~dollar_person[y, z], ~cost[x, y]))
                [trans.append(implies(bv_trans[5], clause)) for clause in t5]

    for x in piece:
        for y in person:
            for z in city:
                t6 = to_cnf(implies(go_to[x, z] & person_city[y, z], piece_person[x, y]))
                [trans.append(implies(bv_trans[6], clause)) for clause in t6]

                t7 = to_cnf(implies(~go_to[x, z] & person_city[y, z], ~piece_person[x, y]))
                [trans.append(implies(bv_trans[7], clause)) for clause in t7]

                t8 = to_cnf(implies(go_to[x, z] & ~person_city[y, z], ~piece_person[x, y]))
                [trans.append(implies(bv_trans[8], clause)) for clause in t8]

    for x in dollar:
        for y in person:
            for z in city:
                t9 = to_cnf(implies(dollar_city[x, z] & person_city[y, z], dollar_person[x, y]))
                [trans.append(implies(bv_trans[9], clause)) for clause in t9]

                t10 = to_cnf(implies(~dollar_city[x, z] & person_city[y, z], ~dollar_person[x, y]))
                [trans.append(implies(bv_trans[10], clause)) for clause in t10]

                t11 = to_cnf(implies(dollar_city[x, z] & ~person_city[y, z], ~dollar_person[x, y]))
                [trans.append(implies(bv_trans[11], clause)) for clause in t11]

    clues = []
    bv_clues = [BoolVar() for i in range(11)]

    # 0. Kelly's piece didn't cost $1250
    c0a = []
    for a in piece:
        c0a.append(~cost[a, "1250"] & piece_person[a, "kelly"])

    for clause in to_cnf(any(c0a)):
        clues.append(implies(bv_clues[0], clause))

    #type1 = person
    #type2 = city
    #type3 = diffdollar
    # from(piece, type1) = piece_person  = Relation(piece, person)
    # is_linked_with_1(dollar, type1)     dollar_person = Relation(dollar, person)
    # is_linked_with_2(dollar, type2)    dollar_city = Relation(dollar, city)
    # is_linked_with_3(type1, type2)    person_city = Relation(person, city)

    # 1. Valencia cost somewhat more than Isabel's dummy
    c1a = []
    for b in diffdollar:
        for c in dollar:
            for d in piece:
                for e in dollar:
                    if (b > 0) and int(e) == int(c) + b:
                        c1a.append(cost[d, c] & piece_person[d, "isabel"] & cost["valencia",e])


    for clause in to_cnf(any(c1a)):
        clues.append(implies(bv_clues[1], clause))

    # 2. The puppet going to Vancouver, the $750 dummy and the $1500 piece are three different dummies
    c2a = []
    for f in piece:
        for g in piece:
            for h in piece:
                if not (f == g) and not (f ==h) and not (g == h):
                    c2a.append(go_to[f,"vancouver"] & cost[g,"750"] & cost[h,"1500"])

    for clause in to_cnf(any(c2a)):
        clues.append(implies(bv_clues[2], clause))

    # 3. Waldarama didn't cost $750 or $1500
    clues.append(implies(bv_clues[3], ~ (cost["waldarama","750"] | cost["waldarama","1500"])))


    # 4. Kelly's puppet isn't going to Ypsilanti
    c4a = []
    for i in piece:
        c4a.append(~ go_to[i,"ypsilanti"] & piece_person[i,"kelly"])

    for clause in to_cnf(any(c4a)):
        clues.append(implies(bv_clues[4], clause))

    # 5. The dummy going to Mexico City is either Tombawomba or Lucas's puppet
    c5a = []
    for j in piece:
        subformule = [((k == j) & piece_person[k, "lucas"]) for k in piece]
        c5a.append(go_to[j,"mexico_city"] & (("tombawomba" == j) | any(subformule) ))

    for clause in to_cnf(any(c5a)):
        clues.append(implies(bv_clues[5], clause))


    # 6. Nicole's puppet, the $1000 piece and the puppet going to Ypsilanti are three different dummies
    c6a = []
    for l in piece:
        for m in piece:
            for n in piece:
                if not (l == m) and not (l == n) and not (m == n):
                    c6a.append(piece_person[l,"nicole"] & cost[m,"1000"] & go_to[n,"ypsilanti"])

    for clause in to_cnf(any(c6a)):
        clues.append(implies(bv_clues[6], clause))

    # 7. Of the $750 puppet and the piece going to Mexico City, one is Tombawomba and the other is Isabel's puppet
    c7a = []
    for o in piece:
        for p in piece:
            if not o == p:
                # (?q [piece]: tombawomba = o & q = p & from(q,isabel))
                formule1 = any(
                    [("tombawomba" == o) & (q == p) & piece_person[q,"isabel"] for q in piece]
                )
                # (?r [piece]: tombawomba = p & r = o & from(r,isabel))
                formule2 = any(
                    [("tombawomba" == p) & (r == o) & piece_person[r,"isabel"] for r in piece]
                )
                groteformule = formule1 | formule2
                c7a.append(go_to[p, "mexico_city"] & groteformule & cost[o, "750"])

    for clause in to_cnf(any(c7a)):
        clues.append(implies(bv_clues[7], clause))

    # 8. The puppet going to Ypsilanti cost $250 more than the puppet going to St. Moritz.
    c8a = []
    for s in piece:
        for t in dollar:
            for u in piece:
                for v in dollar:
                    if int(v) == int(t) + 250:
                        c8a.append(go_to[s,"ypsilanti"] & go_to[u,"st_moritz"] & cost[u,t] & cost[s,v])

    for clause in to_cnf(any(c8a)):
        clues.append(implies(bv_clues[8], clause))

    # 9. Of the $1000 dummy and the $1250 dummy, one is from Herman and the other is going to Mexico City
    c9a = []
    for w in piece:
        for x in piece:
            if not (w == x):
                c9a.append((piece_person[w,"herman"] & go_to[x,"mexico_city"] | piece_person[x,"herman"] & go_to[w,"mexico_city"]) & cost[x,"1250"] & cost[w,"1000"])

    for clause in to_cnf(any(c9a)):
        clues.append(implies(bv_clues[9], clause))

    # 10. Sniffletoe sold for $1000
    clues.append(implies(bv_clues[9], cost["sniffletoe","1000"]))

    clueTexts =[
        "Kelly's piece didn't cost $1250",
        "Valencia cost somewhat more than Isabel's dummy",
        "The puppet going to Vancouver, the $750 dummy and the $1500 piece are three different dummies",
        "Waldarama didn't cost $750 or $1500",
        "Kelly's puppet isn't going to Ypsilanti",
        "The dummy going to Mexico City is either Tombawomba or Lucas's puppet",
        "Nicole's puppet, the $1000 piece and the puppet going to Ypsilanti are three different dummies",
        "Of the $750 puppet and the piece going to Mexico City, one is Tombawomba and the other is Isabel's puppet",
        "The puppet going to Ypsilanti cost $250 more than the puppet going to St. Moritz.",
        "Of the $1000 dummy and the $1250 dummy, one is from Herman and the other is going to Mexico City",
        "Sniffletoe sold for $1000"
    ]

    clues_cnf = cnf_to_pysat(to_cnf(clues))
    bij_cnf = cnf_to_pysat(to_cnf(bij))
    trans_cnf = cnf_to_pysat(to_cnf(trans))

    hard_clauses = [c for c in clues_cnf + bij_cnf + trans_cnf]
    soft_clauses = []
    soft_clauses += [[bv1.name + 1] for bv1 in bv_clues]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_bij]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_trans]

    weights = {}
    weights.update({bv.name + 1: 100 for bv in bv_clues})
    weights.update({bv.name + 1: 60 for bv in bv_trans})
    weights.update({bv.name + 1: 60 for bv in bv_bij})

    explainable_facts = set()
    bvRels = {}
    for rel, relStr in zip(rels, ["cost", "go_to", "piece_person", "dollar_person", "dollar_city", "person_city"]):
        rowNames = list(rel.df.index)
        columnNames = list(rel.df.columns)

        # production of explanations json file
        for r in rowNames:
            for c in columnNames:
                bvRels[rel.df.at[r, c].name + 1] = {"pred" : relStr.lower(), "subject" : r.lower(), "object": c.lower()}

        # facts to explain
        for item in rel.df.values:
            explainable_facts |= set(i.name+1 for i in item)

    matching_table = {
        'bvRel': bvRels,
        'Transitivity constraint': [bv.name + 1 for bv in bv_trans],
        'Bijectivity': [bv.name + 1 for bv in bv_bij],
        'clues' : {
            bv.name + 1: clueTexts[i] for i, bv in enumerate(bv_clues)
        },
        'types': type_dict,
        'clue_texts': clueTexts
    }

    return hard_clauses, soft_clauses, weights, explainable_facts, matching_table


def p12():
    """
    Logic grid puzzle: 'p12' in CPpy
    Based on... to check originally, currently part of ZebraTutor
    Probably part of Jens Claes' master thesis, from a 'Byron...' booklet
    """
    # type1 = drink
    # type2 = food
    drink = ["the_other_type1", "water", "lemonade", "iced_tea", "orange_soda"]
    order = ["the_other_order", "homer", "glen", "wallace", "oliver"]
    dollar = ["5", "6", "7", "8", "9"]
    food = ["the_other_type2", "sloppy_joe", "spaghetti", "hamburger", "turkey_plate"]
    type_dict = {
        'dollar':dollar, 
        'drink': drink,
        'order': order,
        'food': food,     
    }
    types = [drink, order, dollar, food]
    n = len(types)
    m = len(types[0])
    assert all(len(types[i]) == m for i in range(n)), "all types should have equal length"

    order_drink = Relation(order, drink) #with
    cost = Relation(order, dollar)
    ordered = Relation(order, food)
    drink_dollar = Relation(drink, dollar) #     is_linked_with_1(type1, dollar)
    drink_food = Relation(drink, food) #     is_linked_with_2(type1, type2)
    dollar_food = Relation(dollar, food) #     is_linked_with_3(dollar, type2)
    rels = [order_drink, cost, ordered, drink_dollar, drink_food, dollar_food]

    # Bijectivity
    cnt = 0
    bij, bv_bij = buildBijectivity(rels)

    # Transitivity
    trans = []
    bv_trans =  [BoolVar() for i in range(12)]

    for x in order:
        for y in drink:
            for z in dollar:
                t0 = to_cnf(implies(cost[x, z] & drink_dollar[y, z], order_drink[x, y]))
                [trans.append(implies(bv_trans[0], clause)) for clause in t0]

                t1 = to_cnf(implies(~cost[x, z] & drink_dollar[y, z], ~order_drink[x, y]))
                [trans.append(implies(bv_trans[1], clause)) for clause in t1]

                t2 = to_cnf(implies(cost[x, z] & ~drink_dollar[y, z], ~order_drink[x, y]))
                [trans.append(implies(bv_trans[2], clause)) for clause in t2]

    for x in order:
        for y in drink:
            for z in food:
                t3 = to_cnf(implies(ordered[x, z] & drink_food[y, z], order_drink[x, y]))
                [trans.append(implies(bv_trans[3], clause)) for clause in t3]

                t4 = to_cnf(implies(~ordered[x, z] & drink_food[y, z], ~order_drink[x, y]))
                [trans.append(implies(bv_trans[4], clause)) for clause in t4]

                t5 = to_cnf(implies(ordered[x, z] & ~drink_food[y, z], ~order_drink[x, y]))
                [trans.append(implies(bv_trans[5], clause)) for clause in t5]

    for x in order:
        for y in dollar:
            for z in food:
                t6 = to_cnf(implies(ordered[x, z] & dollar_food[y, z], cost[x, y]))
                [trans.append(implies(bv_trans[6], clause)) for clause in t6]

                t7 = to_cnf(implies(~ordered[x, z] & dollar_food[y, z], ~cost[x, y]))
                [trans.append(implies(bv_trans[7], clause)) for clause in t7]

                t8 = to_cnf(implies(ordered[x, z] & ~dollar_food[y, z], ~cost[x, y]))
                [trans.append(implies(bv_trans[8], clause)) for clause in t8]

    for x in drink:
        for y in dollar:
            for z in food:
                t9 = to_cnf(implies(drink_food[x, z] & dollar_food[y, z], drink_dollar[x, y]))
                [trans.append(implies(bv_trans[9], clause)) for clause in t9]

                t10 = to_cnf(implies(~drink_food[x, z] & dollar_food[y, z], ~drink_dollar[x, y]))
                [trans.append(implies(bv_trans[10], clause)) for clause in t10]

                t11 = to_cnf(implies(drink_food[x, z] & ~dollar_food[y, z], ~drink_dollar[x, y]))
                [trans.append(implies(bv_trans[11], clause)) for clause in t11]

    clues = []
    bv_clues = [BoolVar() for i in range(8)]
    # 0. The order with the lemonade cost $1 more than the order with the water
    c0a = []
    for a in order:
        for b in dollar:
            for c in order:
                for d in dollar:
                    if int(d) == int(b) + 1:
                        c0a.append(order_drink[a, "lemonade"] & order_drink[c, "water"] & cost[c, b] & cost[a, d])
    for clause in to_cnf(any(c0a)):
        clues.append(implies(bv_clues[0], clause))

    # 1. Homer paid $7
    clues.append(implies(bv_clues[0], cost["homer", "7"]))

    # 2. Glen paid $3 less than whoever ordered the sloppy joe
    c2a = []
    for e in dollar:
        for f in order:
            for g in dollar:
                if int(g) == int(e) - 3:
                    c2a.append(ordered[f,"sloppy_joe"] & cost[f, e] & cost["glen", g])

    for clause in to_cnf(any(c2a)):
        clues.append(implies(bv_clues[2], clause))

    # 3. Wallace didn't have the iced tea
    clues.append(implies(bv_clues[3], ~order_drink["wallace","iced_tea"]))

    # 4. Of the diner who paid $6 and Homer, one ordered the spaghetti and the other drank the water
    c4a = []
    for h in order:
        c4a.append(cost[h, "6"] & (ordered[h,"spaghetti"] & order_drink["homer", "water"] | ordered["homer", "spaghetti"] & order_drink[h, "water"]))

    for clause in to_cnf(any(c4a)):
        clues.append(implies(bv_clues[4], clause))

    # 5. Oliver ordered the hamburger
    clues.append(implies(bv_clues[5], ordered["oliver","hamburger"]))

    # 6. The five diners were whoever ordered the turkey plate, Oliver, Glen, the person who got the iced tea and the person who paid $5
    c6a = []
    for i in order:
        for j in order:
            for k in order:
                if not (i == "oliver") and not (i == "glen") and not (i == j) and not (i == k) and not ("oliver" == j) and not ("oliver" == k) and not("glen" == j) and not ("glen" == k) and not (j == k):
                    c6a.append(ordered[i,"turkey_plate"] & order_drink[j,"iced_tea"] & cost[k, "5"])

    for clause in to_cnf(any(c6a)):
        clues.append(implies(bv_clues[6], clause))

    # 7. Glen didn't have the orange soda
    clues.append(implies(bv_clues[7], ~order_drink["glen", "orange_soda"]))

    clueTexts = [
        "The order with the lemonade cost $1 more than the order with the water",
        "Homer paid $7",
        "Glen paid $3 less than whoever ordered the sloppy joe",
        "Wallace didn't have the iced tea",
        "Of the diner who paid $6 and Homer, one ordered the spaghetti and the other drank the water",
        "Oliver ordered the hamburger",
        "The five diners were whoever ordered the turkey plate, Oliver, Glen, the person who got the iced tea and the person who paid $5",
        "Glen didn't have the orange soda"
    ]

    clues_cnf = cnf_to_pysat(to_cnf(clues))
    bij_cnf = cnf_to_pysat(to_cnf(bij))
    trans_cnf = cnf_to_pysat(to_cnf(trans))

    hard_clauses = [c for c in clues_cnf + bij_cnf + trans_cnf]
    soft_clauses = []
    soft_clauses += [[bv1.name + 1] for bv1 in bv_clues]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_bij]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_trans]

    weights = {}
    weights.update({bv.name + 1: 100 for bv in bv_clues})
    weights.update({bv.name + 1: 60 for bv in bv_trans})
    weights.update({bv.name + 1: 60 for bv in bv_bij})

    explainable_facts = set()
    bvRels = {}
    for rel, relStr in zip(rels, ["order_drink", "cost", "ordered", "drink_dollar", "drink_food", "dollar_food"]):
        rowNames = list(rel.df.index)
        columnNames = list(rel.df.columns)

        # production of explanations json file
        for r in rowNames:
            for c in columnNames:
                bvRels[rel.df.at[r, c].name + 1] = {"pred" : relStr.lower(), "subject" : r.lower(), "object": c.lower()}

        # facts to explain
        for item in rel.df.values:
            explainable_facts |= set(i.name+1 for i in item)

    matching_table = {
        'bvRel': bvRels,
        'Transitivity constraint': [bv.name + 1 for bv in bv_trans],
        'Bijectivity': [bv.name + 1 for bv in bv_bij],
        'clues' : {
            bv.name + 1: clueTexts[i] for i, bv in enumerate(bv_clues)
        },
        'types': type_dict,
        'clue_texts': clueTexts
    }

    return hard_clauses, soft_clauses, weights, explainable_facts, matching_table


def pastaPuzzle():
    """
    Logic grid puzzle: 'pasta' in CPpy
    Based on... to check originally, currently part of ZebraTutor
    Probably part of Jens Claes' master thesis, from a 'Byron...' booklet
    """
    # type1 = sauce
    # type2 = pasta
    # type3 = differences between values of type dollar
    # type4 = differences between values of type dollar
    # type5 = differences between values of type dollar
    dollar = ['4', '8', '12', '16']
    person = ['angie', 'damon', 'claudia', 'elisa']
    sauce = ['the_other_type1', 'arrabiata_sauce', 'marinara_sauce', 'puttanesca_sauce'] # type1
    pasta = ['capellini', 'farfalle', 'tagliolini', 'rotini']  # type2
    type_dict = {
        'dollar':dollar, 
        'person': person,
        'sauce': sauce,
        'pasta': pasta,     
    }
    types = [dollar, person, sauce, pasta]
    n = len(types)
    m = len(types[0])
    assert all(len(types[i]) == m for i in range(n)), "all types should have equal length"

    chose = Relation(person, sauce)
    paid = Relation(person, dollar)
    ordered = Relation(person, pasta)
    sauce_dollar = Relation(sauce, dollar) # is_linked_with_1(sauce, dollar)
    sauce_pasta = Relation(sauce, pasta) # is_linked_with_2(sauce, pasta)
    dollar_pasta = Relation(dollar, pasta) # is_linked_with_3(dollar, pasta)
    rels = [chose, paid, ordered, sauce_dollar, sauce_pasta, dollar_pasta]

    # Bijectivity
    cnt = 0
    bij = []
    bv_bij = []

    for rel in rels:
        # bijection for all columns inside relation
        bv1 = BoolVar()
        bv2 = BoolVar()
        # for each relation
        for col_ids in rel.df:
            # one per column
            atleast, atmost = exactly_one_at_most(rel[:, col_ids])
            [bij.append(implies(bv1, clause)) for clause in atmost]
            bij.append(implies(bv2, atleast))
        bv_bij.append(bv1)
        bv_bij.append(bv2)

        # bijection for all rows inside relation
        bv3 = BoolVar()
        bv4 = BoolVar()
        for (_,row) in rel.df.iterrows():
            # one per row
            atleast, atmost = exactly_one_at_most(row)
            [bij.append(implies(bv3, clause)) for clause in atmost]
            bij.append(implies(bv4, atleast))
        bv_bij.append(bv3)
        bv_bij.append(bv4)

    # Transitivity
    trans = []
    bv_trans =  [BoolVar() for i in range(12)]


    for x in person:
        for y in sauce:
            for z in dollar:
                t0 = to_cnf(implies(paid[x, z] & sauce_dollar[y, z], chose[x, y]))
                [trans.append(implies(bv_trans[0], clause)) for clause in t0]

                t1 = to_cnf(implies(~paid[x, z] & sauce_dollar[y, z], ~chose[x, y]))
                [trans.append(implies(bv_trans[1], clause)) for clause in t1]

                t2 = to_cnf(implies(paid[x, z] & ~sauce_dollar[y, z], ~chose[x, y]))
                [trans.append(implies(bv_trans[2], clause)) for clause in t2]

    for x in person:
        for y in sauce:
            for z in pasta:
                t3 = to_cnf(implies(ordered[x, z] & sauce_pasta[y, z], chose[x, y]))
                [trans.append(implies(bv_trans[3], clause)) for clause in t3]

                t4 = to_cnf(implies(~ordered[x, z] & sauce_pasta[y, z], ~chose[x, y]))
                [trans.append(implies(bv_trans[4], clause)) for clause in t4]

                t5 = to_cnf(implies(ordered[x, z] & ~sauce_pasta[y, z], ~chose[x, y]))
                [trans.append(implies(bv_trans[5], clause)) for clause in t5]

    for x in person:
        for y in dollar:
            for z in pasta:
                t6 = to_cnf(implies(ordered[x, z] & dollar_pasta[y, z], paid[x, y]))
                [trans.append(implies(bv_trans[6], clause)) for clause in t6]

                t7 = to_cnf(implies(~ordered[x, z] & dollar_pasta[y, z], ~paid[x, y]))
                [trans.append(implies(bv_trans[7], clause)) for clause in t7]

                t8 = to_cnf(implies(ordered[x, z] & ~dollar_pasta[y, z], ~paid[x, y]))
                [trans.append(implies(bv_trans[8], clause)) for clause in t8]


    for x in sauce:
        for y in dollar:
            for z in pasta:
                t9 = to_cnf(implies(sauce_pasta[x, z] & dollar_pasta[y, z], sauce_dollar[x, y]))
                [trans.append(implies(bv_trans[9], clause)) for clause in t9]

                t10 = to_cnf(implies(~sauce_pasta[x, z] & dollar_pasta[y, z], ~sauce_dollar[x, y]))
                [trans.append(implies(bv_trans[10], clause)) for clause in t10]

                t11 = to_cnf(implies(sauce_pasta[x, z] & ~dollar_pasta[y, z], ~sauce_dollar[x, y]))
                [trans.append(implies(bv_trans[11], clause)) for clause in t11]

    clues = []
    bv_clues = [BoolVar() for i in range(8)]

    # 0.The person who ordered capellini paid less than the person who chose arrabiata sauce
    clue0 = to_cnf(any([ordered[a, "capellini"] & chose[d, "arrabiata_sauce"] & paid[d, c] & paid[a, e]
                for a in person
                for b in [-4, 4, -8, 8,  -12, 12]
                for c in dollar
                for d in person
                for e in dollar if (b > 0) and (int(e) == int(c)-b)]))
    [clues.append(implies(bv_clues[0], cl)) for cl in clue0 ]

    # 1. The person who chose arrabiata sauce ordered farfalle
    clue1 = to_cnf( any( [ chose[f,  "arrabiata_sauce"] & ordered[f, "farfalle"] for f in person]))
    [clues.append(implies(bv_clues[1], cl)) for cl in clue1 ]

    # 2. The person who ordered tagliolini paid less than the person who chose marinara sauce
    c2a = []
    for g in person:
        for h in [-4, 4, -8, 8, -12, 12]:
            if h > 0:
                for i in dollar:
                    for j in person:
                        for k in dollar:
                            if int(k) == int(i) - h:
                                c2a.append(ordered[g, "tagliolini"] & chose[j, "marinara_sauce"] & paid[j, i] & paid[g, k])
    c2a = to_cnf(any(c2a))
    [clues.append(implies(bv_clues[2], clause)) for clause in c2a]

    #  3. The person who ordered tagliolini paid more than Angie
    c3a = []
    for l in person:
        for m in [-4, 4, -8, 8, -12, 12]:
            if m > 0:
                for n in dollar:
                    for o in dollar:
                        if int(o) == int(n) + m:
                            c3a.append(ordered[l, "tagliolini"] & paid["angie", n] & paid[l, o])
    c3a = to_cnf(any(c3a))
    [clues.append(implies(bv_clues[3], clause)) for clause in c3a]

    #  4. The person who ordered rotini is either the person who paid $8 more than Damon or the person who paid $8 less than Damon
    #list with: for every person: two options
    c4a = []
    for p in person:
        formule1 = any(
            [paid["damon", r] & paid[q,s] for q in person for r in dollar for s in dollar if (int(s) == int(r) - 8) and (q == p)]
        )
        formule2 = any(
            [paid["damon", r] & paid[q,s] for q in person for r in dollar for s in dollar if (int(s) == int(r) + 8) and (q == p)]
        )
        groteformule = formule1 | formule2
        c4a.append(ordered[p, "rotini"] & groteformule)
    c4a = to_cnf(any(c4a))

    for clause in c4a:
        clues.append(implies(bv_clues[4], clause))

    # 5. Claudia did not choose puttanesca sauce
    c5a = to_cnf(implies(bv_clues[5],  ~chose["claudia", "puttanesca_sauce"]))
    clues.append(c5a)

    #  6. The person who ordered capellini is either Damon or Claudia
    c6a = to_cnf(any([ordered[p, 'capellini'] & ( (p == 'claudia') | (p == 'damon')) for p in person]))
    [clues.append(implies(bv_clues[6], clause)) for clause in c6a]

    # 7. The person who chose arrabiata sauce is either Angie or Elisa => XOR
    c7a = to_cnf(any([chose[p, 'arrabiata_sauce'] &  ( (p == 'angie') | (p == 'elisa'))  for p in person]))
    [clues.append(implies(bv_clues[7], clause)) for clause in c7a]

    clueTexts = [
        "The person who ordered capellini paid less than the person who chose arrabiata sauce",
        "The person who chose arrabiata sauce ordered farfalle",
        "The person who ordered tagliolini paid less than the person who chose marinara sauce",
        "The person who ordered tagliolini paid more than Angie",
        "The person who ordered rotini is either the person who paid $8 more than Damon or the person who paid $8 less than Damon",
        "Claudia did not choose puttanesca sauce",
        "The person who ordered capellini is either Damon or Claudia",
        "The person who chose arrabiata sauce is either Angie or Elisa"
    ]

    clues_cnf = cnf_to_pysat(to_cnf(clues))
    bij_cnf = cnf_to_pysat(to_cnf(bij))
    trans_cnf = cnf_to_pysat(to_cnf(trans))

    hard_clauses = [c for c in clues_cnf + bij_cnf + trans_cnf]
    soft_clauses = []
    soft_clauses += [[bv1.name + 1] for bv1 in bv_clues]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_bij]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_trans]

    weights = {}
    weights.update({bv.name + 1: 100 for bv in bv_clues})
    weights.update({bv.name + 1: 60 for bv in bv_trans})
    weights.update({bv.name + 1: 60 for bv in bv_bij})

    explainable_facts = set()
    bvRels = {}
    for rel, relStr in zip(rels, ["chose", "paid", "ordered", "sauce_dollar", "sauce_pasta", "dollar_pasta"]):
        rowNames = list(rel.df.index)
        columnNames = list(rel.df.columns)

        # production of explanations json file
        for r in rowNames:
            for c in columnNames:
                bvRels[rel.df.at[r, c].name + 1] = {"pred" : relStr.lower(), "subject" : r.lower(), "object": c.lower()}

        # facts to explain
        for item in rel.df.values:
            explainable_facts |= set(i.name+1 for i in item)

    # for rel in rels:
    #     rowNames = list(rel.df.index)
    #     columnNames = list(rel.df.columns)
    #     for r in rowNames:
    #         for c in columnNames:
    #             print(r, c, rel.df.at[r, c].name + 1)

    #print(explainable_facts)

    matching_table = {
        'bvRel': bvRels,
        'Transitivity constraint': [bv.name + 1 for bv in bv_trans],
        'Bijectivity': [bv.name + 1 for bv in bv_bij],
        'clues' : {
            bv.name + 1: clueTexts[i] for i, bv in enumerate(bv_clues)
        },
        'types': type_dict,
        'clue_texts': clueTexts
    }

    return hard_clauses, soft_clauses, weights, explainable_facts, matching_table


def originProblem():
    """
    Logic grid puzzle: 'origin' in CPpy
    Based on... to check originally, currently part of ZebraTutor
    Probably part of Jens Claes' master thesis, from a 'Byron...' booklet
    """

    person = ['Mattie', 'Ernesto', 'Roxanne', 'Zachary', 'John']
    age = ['109', '110', '111', '112', '113']
    city = ['Brussels', 'Tehama', 'Zearing', 'Plymouth', 'Shaver Lake']
    birthplace = ['Mexico', 'Oregon', 'Kansas', 'Washington', 'Alaska']
    type_dict = {
        'age':age, 
        'person': person,
        'city': city,
        'birthplace': birthplace,     
    }
    types = [person, age, city, birthplace]
    n = len(types)
    m = len(types[0])
    assert all(len(types[i]) == m for i in range(n)), "all types should have equal length"

    is_old = Relation(person, age)
    lives_in = Relation(person, city)
    native = Relation(person, birthplace)
    age_city = Relation(age, city)
    age_birth = Relation(age, birthplace)
    city_birth = Relation(city, birthplace)

    # Bijectivity
    cnt = 0
    bij = []
    # bv_bij = [BoolVar() for i in range(60)]

    bv_bij = []

    for rel in [is_old, lives_in, native, age_city, age_birth, city_birth]:
        # for each relation
        bv1 = BoolVar()
        bv2 = BoolVar()
        for col_ids in rel.df:
            # one per column
            atleast, atmost = exactly_one_at_most(rel[:, col_ids])
            [bij.append(implies(bv1, clause)) for clause in atmost]
            bij.append(implies(bv2, atleast))
        bv_bij.append(bv1)
        bv_bij.append(bv2)

        bv3 = BoolVar()
        bv4 = BoolVar()
        for (_,row) in rel.df.iterrows():
            # one per row
            atleast, atmost = exactly_one_at_most(row)
            [bij.append(implies(bv3, clause)) for clause in atmost]
            bij.append(implies(bv4, atleast))
        bv_bij.append(bv3)
        bv_bij.append(bv4)

    # Transitivity
    trans = []
    bv_trans =  [BoolVar() for i in range(12)]
    for x in person:
        for z in birthplace:
            for y in age:
                # ! x y z:  from(x, z) & is_linked_with_1(y, z) => is_old(x, y).
                t0 = to_cnf(implies( native[x, z] & age_birth[y, z], is_old[x, y]))
                [trans.append(implies(bv_trans[0], clause)) for clause in t0]

                 # ! x y z:  ~from(x, z) & is_linked_with_1(y, z) => ~is_old[x, y].
                t1 = to_cnf(implies( ~native[x, z] & age_birth[y, z], ~is_old[x, y]))
                [trans.append(implies(bv_trans[1], clause)) for clause in t1]

                 # ! x y z:  from(x, z) & ~is_linked_with_1(y, z) => ~is_old[x, y].
                t2 = to_cnf(implies( native[x, z] & ~age_birth[y, z], ~is_old[x, y]))
                [trans.append(implies(bv_trans[2], clause)) for clause in t2]

    for x in person :
        for y in age :
            for z in city :

                # ! x y z:  lives_in(x, z) & is_linked_with_2(y, z) => is_old[x, y].
                t3 = to_cnf(implies( lives_in[x, z] & age_city[y, z], is_old[x, y]))
                [trans.append(implies(bv_trans[3], clause)) for clause in t3]

                # ! x y z:  ~lives_in(x, z) & is_linked_with_2(y, z) => ~is_old(x, y).
                t4 = to_cnf(implies( ~lives_in[x, z] & age_city[y, z], ~is_old[x, y]))
                [trans.append(implies(bv_trans[4], clause)) for clause in t4]

                # ! x y z:  lives_in(x, z) & ~is_linked_with_2(y, z) => ~is_old(x, y).
                t5 = to_cnf(implies( lives_in[x, z] & ~age_city[y, z], ~is_old[x, y]))
                [trans.append(implies(bv_trans[5], clause)) for clause in t5]

    for x in person :
        for y in birthplace :
            for z in city :
                #  ! x y z:  lives_in(x, z) & is_linked_with_3(y, z) => from(x, y).
                t6 =to_cnf(implies( lives_in[x, z] & city_birth[z, y] , native[x, y] ))
                [trans.append(implies(bv_trans[6], clause)) for clause in t6]

                # ! x y z:  ~lives_in(x, z) & is_linked_with_3(y, z) => ~from(x, y).
                t7 = to_cnf(implies( ~lives_in[x, z] & city_birth[z, y] , ~native[x, y]))
                [trans.append(implies(bv_trans[7], clause)) for clause in t7]

                # ! x y z:  lives_in(x, z) & ~is_linked_with_3(y, z) => ~from(x, y).
                t8 = to_cnf(implies( lives_in[x, z] & ~city_birth[z, y] , ~native[x, y] ))
                [trans.append(implies(bv_trans[8], clause)) for clause in t8]

    for x in age :
        for y in birthplace:
            for z in city :
                #  ! x y z:  is_linked_with_2(x, z) & is_linked_with_3(y, z) => is_linked_with_1(x, y).
                t9 = to_cnf(implies( age_city[x, z] & city_birth[z, y], age_birth[x, y]))
                [trans.append(implies(bv_trans[9], clause)) for clause in t9]

                # ! x y z:  ~is_linked_with_2(x, z) & is_linked_with_3(y, z) => ~is_linked_with_1(x, y).
                t10 = to_cnf(implies( ~age_city[x, z] & city_birth[z, y], ~age_birth[x, y]))
                [trans.append(implies(bv_trans[10], clause)) for clause in t10]

                # ! x y z:  is_linked_with_2(x, z) & ~is_linked_with_3(y, z) => ~is_linked_with_1(x, y).
                t11 = to_cnf(implies( age_city[x, z] & ~city_birth[z, y], ~age_birth[x, y]))
                [trans.append(implies(bv_trans[11], clause)) for clause in t11]

    clues = []
    bv_clues = [BoolVar() for i in range(10)]
    clues.append(implies(bv_clues[0], is_old['Mattie', '113']))

    # The person who lives in Tehama is a native of either Kansas or Oregon
    c1a = to_cnf([implies(lives_in[p, 'Tehama'], native[p, 'Kansas'] | native[p, 'Oregon']) for p in person])

    [clues.append(implies(bv_clues[1], clause)) for clause in c1a]

    # The Washington native is 1 year older than Ernesto
    c2a = to_cnf([implies(age_birth[a, 'Washington'], is_old['Ernesto', str(int(a)-1)]) for a in age])
    [clues.append(implies(bv_clues[2], clause)) for clause in c2a]

    # Roxanne is 2 years younger than the Kansas native
    c3a = to_cnf([implies(is_old['Roxanne', a], age_birth[str(int(a)+2), 'Kansas']) for a in age])
    [clues.append(implies(bv_clues[3], clause)) for clause in c3a]

    # The person who lives in Zearing isn't a native of Alaska
    c4a = to_cnf([implies(lives_in[p, 'Zearing'], ~native[p, 'Alaska']) for p in person])
    [clues.append(implies(bv_clues[4], clause)) for clause in c4a]

    # The person who is 111 years old doesn't live in Plymouth
    c5a = to_cnf([implies(is_old[p, '111'], ~lives_in[p, 'Plymouth']) for p in person])
    [clues.append(implies(bv_clues[5], clause)) for clause in c5a]

    # The Oregon native is either Zachary or the person who lives in Tehama
    c6a = to_cnf([implies(native[p, 'Oregon'], (p == 'Zachary') | lives_in[p, 'Tehama']) for p in person])
    [clues.append(implies(bv_clues[6], clause)) for clause in c6a]

    # The person who lives in Shaver Lake is 1 year younger than Roxanne
    c7a = to_cnf([implies(age_city[a, 'Shaver Lake'], is_old['Roxanne', str(int(a)+1)]) for a in age])
    [clues.append(implies(bv_clues[7], clause)) for clause in c7a]

    # The centenarian who lives in Plymouth isn't a native of Alaska
    c8a = to_cnf([implies(lives_in[p, 'Plymouth'], ~native[p, 'Alaska']) for p in person])
    [clues.append(implies(bv_clues[8], clause)) for clause in c8a]

    # Of the person who lives in Tehama and Mattie, one is a native of Alaska and the other is from Kansas
    c9a = to_cnf([implies(lives_in[p, 'Tehama'],
                          (p != 'Mattie') &
                          ((native['Mattie', 'Alaska'] & native[p, 'Kansas']) |
                           (native[p, 'Alaska'] & native['Mattie', 'Kansas']))) for p in person])
    [clues.append(implies(bv_clues[9], clause)) for clause in c9a]

    # match clue in cnf to textual representation
    clueTexts = [
        "Mattie is 113 years old",
        "The person who lives in Tehama is a native of either Kansas or Oregon",
        "The Washington native is 1 year older than Ernesto",
        "Roxanne is 2 years younger than the Kansas native",
        "The person who lives in Zearing isn't a native of Alaska",
        "The person who is 111 years old doesn't live in Plymouth",
        "The Oregon native is either Zachary or the person who lives in Tehama",
        "The person who lives in Shaver Lake is 1 year younger than Roxanne",
        "The centenarian who lives in Plymouth isn't a native of Alaska",
        "Of the person who lives in Tehama and Mattie, one is a native of Alaska and the other is from Kansas"
    ]

    rels = [is_old, lives_in, native, age_city, age_birth, city_birth]

    clues_cnf = cnf_to_pysat(to_cnf(clues))
    bij_cnf = cnf_to_pysat(to_cnf(bij))
    trans_cnf = cnf_to_pysat(to_cnf(trans))
    # print(len(clues_cnf))

    hard_clauses = [c for c in clues_cnf + bij_cnf + trans_cnf]
    soft_clauses = []
    soft_clauses += [[bv1.name + 1] for bv1 in bv_clues]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_bij]
    soft_clauses += [[bv1.name + 1]  for bv1 in bv_trans]

    weights = {}
    weights.update({bv.name + 1: 100 for bv in bv_clues})
    weights.update({bv.name + 1: 60 for bv in bv_trans})
    weights.update({bv.name + 1: 60 for bv in bv_bij})

    explainable_facts = set()
    bvRels = {}
    for rel, relStr in zip(rels, ["is_old", "lives_in", "native", "age_city", "age_birth", "city_birth"]):
        rowNames = list(rel.df.index)
        columnNames = list(rel.df.columns)
        for r in rowNames:
            for c in columnNames:
                # print(relStr, "row=",r, "col=", c, rel.df.at[r, c])
                bvRels[rel.df.at[r, c].name + 1] = {"pred" : relStr.lower(), "subject" : r.lower(), "object": c.lower()}
        for item in rel.df.values:
            explainable_facts |= set(i.name+1 for i in item)


    matching_table = {
        'bvRel': bvRels,
        'Transitivity constraint': [bv.name + 1 for bv in bv_trans],
        'Bijectivity': [bv.name + 1 for bv in bv_bij],
        'clues' : {
            bv.name + 1: clueTexts[i] for i, bv in enumerate(bv_clues)
        },
        'types': type_dict,
        'clue_texts': clueTexts
    }

    return hard_clauses, soft_clauses, weights, explainable_facts, matching_table


def simpleProblem():
    (mayo, ketchup, andalouse) = BoolVar(3)

    c0 = mayo
    c1 = ~mayo | ~andalouse | ketchup
    c2 = ~mayo | andalouse | ketchup
    c3 = ~ketchup | ~andalouse

    constraints = [c0, c1, c2, c3]
    cnf = cnf_to_pysat(constraints)
    explainable_facts = set([mayo.name+1, ketchup.name+1,andalouse.name+1])

    # setup for running the puzzle
    f_cnf = [list(c) for c in cnf]
    f_user_vars = explainable_facts

    # add assumptions for toggling on/off constraints
    f_cnf_ass, assumptions = add_assumptions(f_cnf)

    weights = {l:20 for l in assumptions}
    # weights.update({})

    return f_cnf_ass, [[l] for l in assumptions], weights, f_user_vars, None


def frietKotProblem():
    # Construct the model.
    (mayo, ketchup, curry, andalouse, samurai) = BoolVar(5)
    offset = samurai.name+1

    Nora = mayo | ketchup
    Leander = ~samurai | mayo
    Benjamin = ~andalouse | ~curry | ~samurai
    Behrouz = ketchup | curry | andalouse
    Guy = ~ketchup | curry | andalouse
    Daan = ~ketchup | ~curry | andalouse
    Celine = ~samurai
    Anton = mayo | ~curry | ~andalouse
    Danny = ~mayo | ketchup | andalouse | samurai
    Luc = ~mayo | samurai

    allwishes = [Nora, Leander, Benjamin, Behrouz, Guy, Daan, Celine, Anton, Danny, Luc]
    cnf = cnf_to_pysat(allwishes)
    explainable_facts = set([mayo.name+1, ketchup.name+1,andalouse.name+1, curry.name+1, samurai.name+1])

    # setup for running the puzzle
    f_cnf = [list(c) for c in cnf]
    f_user_vars = explainable_facts

    # add assumptions for toggling on/off constraints
    f_cnf_ass, assumptions = add_assumptions(f_cnf)

    weights = {l:20 for l in assumptions}
    # weights.update({})

    return f_cnf_ass, [[l] for l in assumptions], weights, f_user_vars, None
