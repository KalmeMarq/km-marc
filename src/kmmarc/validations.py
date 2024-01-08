import json
import re

def parse_validations(builtin_valids = None):
    with open("validations.json", "r", encoding="utf-8") as f:
        jsondata = json.load(f)

    for key in builtin_valids:
        if key not in jsondata:
            jsondata[key] = builtin_valids[key]

    def process():
        for key in jsondata:
            obj = jsondata[key]
            if "$ref" in obj:
                ref = obj['$ref']
                jsondata[key] = jsondata[ref]

    process()
    
    def validate(code, value):
        obj = jsondata[code]
        if obj['type'] == 'enum':
            return obj['values'].count(value) > 0
        elif obj['type'] == 'regex':
            return len(re.findall(obj['value'], value)) != 0

    return lambda code, value : validate(code, value)

if __name__ == '__main__':
    valids = parse_validations({
        '200.c': {
            'type': 'enum',
            'values': ["JSON", "ISO"]
        }
    })
    print(valids('200.a', "EN"))
    print(valids('200.b', "123456789"))
    print(valids('200.d', "ES"))