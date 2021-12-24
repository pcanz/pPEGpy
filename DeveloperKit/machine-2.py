
"""
    Step 2: 
    date grammar, 
    4-instruction parser machine,
    generating a parse tree.
"""

date_grammar = """
    date  = year '-' month '-' day
    year  = d d d d
    month = d d
    day   = d d
    d     = '0'/'1'/'2'/'4'/'5'/'6'/'7'/'8'/'9'
"""

date_ptree = ["Peg",[
    ["rule", [["id", "date"],
        ["seq", [["id", "year"], ["sq", "'-'"],
            ["id", "month"], ["sq", "'-'"], ["id", "day"]]]]],
    ["rule", [["id", "year"],
        ["seq", [["id", "d"],["id", "d"],
            ["id", "d"],["id", "d"]]]]],
    ["rule", [["id", "month"],
        ["seq", [["id", "d"], ["id", "d"]]]]],
    ["rule", [["id", "day"],
        ["seq", [["id", "d"], ["id", "d"]]]]],
    ["rule", [["id", "d"],
        ["alt", [["sq", "'0'"], ["sq", "'1'"], ["sq", "'2'"],
            ["sq", "'3'"], ["sq", "'4'"], ["sq", "'5'"], ["sq", "'6'"],
            ["sq", "'7'"], ["sq", "'8'"], ["sq", "'9'"]]]]]
]]

date_code = {
    "date":
        ["seq", [["id", "year"], ["sq", "'-'"],
            ["id", "month"], ["sq", "'-'"], ["id", "day"]]],
    "year":
        ["seq", [["id", "d"],["id", "d"],
            ["id", "d"],["id", "d"]]],
    "month":
        ["seq", [["id", "d"], ["id", "d"]]],
    "day":
        ["seq", [["id", "d"], ["id", "d"]]],
    "d":
        ["alt", [["sq", "'0'"], ["sq", "'1'"], ["sq", "'2'"],
            ["sq", "'3'"], ["sq", "'4'"], ["sq", "'5'"], ["sq", "'6'"],
            ["sq", "'7'"], ["sq", "'8'"], ["sq", "'9'"]]],
    "$start": ["id", "date"]
}


def parse(grammar_code, input):
    env = {
        "rules": grammar_code,
        "input": input,
        "pos": 0, # cursor position
        "tree": [], # build parse tree
    }
    start = env["rules"]["$start"]
    result = eval(start, env)
    return (result, env["pos"], env["tree"])

def eval(exp, env):
    print(exp, exp[0])
    instruct = {
        "id": id,
        "seq": seq,
        "alt": alt,
        "sq": sq
    }
    return instruct[exp[0]](exp, env)

def id(exp, env):
    name = exp[1]
    start = env["pos"]
    stack = len(env["tree"])
    expr = env["rules"][name]
    if not expr: raise Exception("undefined rule: "+name)
    result = eval(expr, env)
    if not result: return False
    size = len(env["tree"])
    if size-stack > 1:
        env["tree"][stack:] = [[name, env["tree"][stack:]]]
        return True
    if size == stack:
        env["tree"].append([name, env["input"][start:env["pos"]]])
        return True
    return True  # elide redundant rule name

def seq(exp, env):
    for arg in exp[1]:
        if not eval(arg, env): return False
    return True

def alt(exp, env):
    start = env["pos"]
    stack = len(env["tree"])
    for arg in exp[1]:
        if eval(arg, env): return True
        if len(env["tree"]) > stack:
            env["tree"] = env["tree"][0:stack]       
        env["pos"] = start
    return False

def sq(exp, env):
    input = env["input"]
    end = len(input)
    for c in exp[1][1:-1]:
        pos = env["pos"]
        if pos >= end or c != input[pos]: return False
        env["pos"] = pos+1
    return True

print( parse(date_code, "2021-03-04") ) # eval exp ...

"""  Impementation Notes:

Add parse tree building, all this is in id rule.

Add reset tree in alt

TODO: upper case rule names and anon underscore rule names.

"""
