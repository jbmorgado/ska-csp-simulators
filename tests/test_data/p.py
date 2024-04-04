import json

with open("system-parameters.json", "r", encoding="utf-8") as f:
    r = f.read()
    print(f" {r} - {type(r)}")
    k = json.loads(r)
    print(k)
