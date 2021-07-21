from demystify import explain
exp = explain.Explainer()

exp.init_from_essence("./eprime/star-battle.eprime", "./eprime/star-battle-1.param")

lit_choice = {}
lit_choice["row"] = 4
lit_choice["column"] = 5
lit_choice["value"] = 0

res = exp.explain_steps(num_steps=1, lit_choice=lit_choice)
print(res)