import demystify.explain

exp = demystify.explain.Explainer()

exp.init_from_essence("./eprime/star-battle.eprime", "./eprime/star-battle-1.param")

res1 = exp.explain_steps(num_steps=1)
print(res1)
print("---------------------------")
res2 = exp.get_choices()
print(res2)