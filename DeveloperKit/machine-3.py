"""
    Step 3: 
    date grammar, 
    7-instruction parser machine,
"""

date_grammar = """
    date  = year '-' month '-' day
    year  = [0-9]+
    month = [0-9]+
    day   = [0-9]+
"""

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
    return env["tree"]

def eval(exp, env):
    print(exp, env["pos"])
    instruct = {
        "id": id,
        "seq": seq,
        "alt": alt,
        "rep": rep,
        "sq": sq,
        "dq": dq,
        "chs": chs
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
    start = env["pos"]
    stack = len(env["tree"])
    for arg in exp[1]:
        if not eval(arg, env):
            if len(env["tree"]) > stack:
                env["tree"] = env["tree"][0:stack]
            env["pos"] = start           
            return False
    return True

def alt(exp, env):
    for arg in exp[1]:
        if eval(arg, env): return True
    return False

def rep(exp, env):
    [_rep, [expr, [_sfx, sfx]]] = exp
    min, max = 0, 0  # sfx == "*" 
    if  sfx == "+": min = 1
    elif sfx == "?": max = 1
    start = env["pos"]
    stack = len(env["tree"])
    count, pos = 0, start
    while True:
        result = eval(expr, env)
        if result == False: break
        if pos == env["pos"]: break # no progress
        count += 1
        if count == max: break # max 0 means any
        pos = env["pos"]
    if count < min:
        if len(env["tree"]) > stack:
            env["tree"] = env["tree"][0:stack]
        env["pos"] = start
        return False
    return True

def sq(exp, env):
    pos = env["pos"]
    input = env["input"]
    end = len(input)
    for c in exp[1][1:-1]:
        if pos >= end or c != input[pos]: return False
        pos += 1
    env["pos"] = pos
    return True

def dq(exp, env):
    pos = env["pos"]
    input = env["input"]
    end = len(input)
    for c in exp[1][1:-1]:
        if pos >= end: return False
        if c == " ":
            while pos < end and input[pos] <= " ": pos += 1
            continue
        if c != input[pos]: return False
        pos += 1
    env["pos"] = pos
    return True

def chs(exp, env):
    pos = env["pos"]
    str = exp[1]
    n, end = len(str), len(env["input"])
    if pos >= end: return False
    ch = env["input"][pos]
    i = 1 # "[...]"
    while i < n-1:       
        if i+2 < n-1 and str[i+1] == '-':
            if ch < str[i] or ch > str[i+2]:
                i += 3
                continue
        elif ch != str[i]: 
            i += 1
            continue
        env["pos"] += 1
        return True
    return False

print( parse(date_code, "2021-03-04") ) # eval exp ...

"""  Impementation Notes:

From step 1:

TODO seq does not correct the current pos after a failure

alt assumes the current pos is correct after a failure

sq needs to check for end of input

sq needs to skip the quotes quote marks

From Step 2:

Add parse tree building, all this is in id rule.

TODO: upper case rule names and anon umderscore rule names.

Step 3:

Adds rep, dq, and chs rules.

rep needs to reset current pos and reset tree

rep assumes eval failure will have reset current pos and tree

    seq does not do this, fix that here (the TODO from step 1).

"""