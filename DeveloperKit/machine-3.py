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
        ["rep", [["chs", "[0-9]"],["sfx", "+"]]],
    "month":
        ["rep", [["chs", "[0-9]"],["sfx", "+"]]],
    "day":
        ["rep", [["chs", "[0-9]"],["sfx", "+"]]],
    "$start":
        ["id", "date"]
}

class Env():
    def __init__(self, code, input):
        self.code = code
        self.input = input
        self.pos = 0
        self.end = len(input)
        self.tree = [] # build parse tree

def parse(code, input):
    env = Env(code, input)
    result = eval(code["$start"], env)
    return (result, env.pos, env.tree)

def id(exp, env):
    name = exp[1]
    start = env.pos
    stack = len(env.tree)
    name = exp[1]
    expr = env.code[name]
    result = eval(expr, env)
    if not result: return False
    size = len(env.tree)
    if size-stack > 1:
        env.tree[stack:] = [[name, env.tree[stack:]]]
        return True
    if size == stack:
        env.tree.append([name, env.input[start:env.pos]])
        return True
    return True  # elide redundant rule name

def seq(exp, env):
    for arg in exp[1]:
        if not eval(arg, env): return False
    return True

def alt(exp, env):
    start = env.pos
    stack = len(env.tree)
    for arg in exp[1]:
        if eval(arg, env): return True
        if len(env.tree) > stack:
            env.tree = env.tree[0:stack]       
        env.pos = start
    return False

def rep(exp, env):
    [_rep, [expr, [_sfx, sfx]]] = exp
    min, max = 0, 0  # sfx == "*" 
    if  sfx == "+": min = 1
    elif sfx == "?": max = 1
    count = 0
    while True:
        start = env.pos
        result = eval(expr, env)
        if result == False: break
        if env.pos == start: break # no progress
        count += 1
        if count == max: break # max 0 means any
    if count < min: return False
    return True

def sq(exp, env):
    for c in exp[1][1:-1]:
        if env.pos >= env.end or c != env.input[env.pos]:
            return False
        env.pos += 1
    return True

def dq(exp, env):
    for c in exp[1][1:-1]:
        if c == " ":
            while env.pos < env.end and env.input[env.pos] <= " ": env.pos += 1
            continue
        if env.pos >= env.end or c != env.input[env.pos]: return False
        env.pos += 1
    return True

def chs(exp, env):
    if env.pos >= env.end: return False
    str = exp[1]
    n = len(str)
    ch = env.input[env.pos]
    i = 1 # "[...]"
    while i < n-1:       
        if i+2 < n-1 and str[i+1] == '-':
            if ch < str[i] or ch > str[i+2]:
                i += 3
                continue
        elif ch != str[i]: 
            i += 1
            continue
        env.pos += 1
        return True
    return False

instruct = {
    "id": id,
    "seq": seq,
    "alt": alt,
    "rep": rep,
    "sq": sq,
    "dq": dq,
    "chs": chs,
}

def eval(exp, env):
    print(exp, exp[0])
    return instruct[exp[0]](exp, env)

print( parse(date_code, "2021-03-04") ) # eval exp ...

"""  Impementation Notes:

Adds rep, dq, and chs instructions

"""