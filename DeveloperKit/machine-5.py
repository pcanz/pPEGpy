"""
    Step 5: 
    full pPEG grammar,
    bootstrap ptree from step 4 
    _compile to translate pPEG ptree into parser code,
"""

pPEG_grammar = """
    Peg   = " " (rule " ")+
    rule  = id " = " alt

    alt   = seq (" / " seq)*
    seq   = rep (" " rep)*
    rep   = pre sfx?
    pre   = pfx? term
    term  = call / sq / dq / chs / group / extn

    id    = [a-zA-Z_] [a-zA-Z0-9_]*
    pfx   = [&!~]
    sfx   = [+?] / '*' range?
    range = num (dots num?)?
    num   = [0-9]+
    dots  = '..'

    call  = id !" ="
    sq    = "'" ~"'"* "'" 'i'?
    dq    = '"' ~'"'* '"' 'i'?
    chs   = '[' ~']'* ']'
    group = "( " alt " )"
    extn  = '<' ~'>'* '>'

    _space_ = ('#' ~[\n\r]* / [ \t\n\r]+)*
"""

boot_ptree = ["Peg",[
    ["rule",[["id","Peg"],["seq",[["dq","\" \""],["rep",[["seq",[["id","rule"],["dq","\" \""]]],
        ["sfx","+"]]]]]]],
    ["rule",[["id","rule"],["seq",[["id","id"],["dq","\" = \""],["id","alt"]]]]],
    ["rule",[["id","alt"],["seq",[["id","seq"],["rep",[["seq",[["dq","\" / \""],["id","seq"]]],
        ["sfx","*"]]]]]]],
    ["rule",[["id","seq"],["seq",[["id","rep"],["rep",[["seq",[["sq","' '"],["id","rep"]]],
        ["sfx","*"]]]]]]],
    ["rule",[["id","rep"],["seq",[["id","pre"],["rep",[["id","sfx"],["sfx","?"]]]]]]],
    ["rule",[["id","pre"],["seq",[["rep",[["id","pfx"],["sfx","?"]]],["id","term"]]]]],
    ["rule",[["id","term"],["alt",[["id","id"],["id","sq"],["id","dq"],["id","chs"],["id","group"]]]]],
    ["rule",[["id","id"],["rep",[["chs","[a-zA-Z_]"],["sfx","+"]]]]],
    ["rule",[["id","pfx"],["chs","[&!~]"]]],["rule",[["id","sfx"],["chs","[+?*]"]]],
    ["rule",[["id","sq"],["seq",[["dq","\"'\""],["rep",[["pre",[["pfx","~"],["dq","\"'\""]]],
        ["sfx","*"]]],["dq","\"'\""]]]]],
    ["rule",[["id","dq"],["seq",[["sq","'\"'"],["rep",[["pre",[["pfx","~"],["sq","'\"'"]]],
        ["sfx","*"]]],["sq","'\"'"]]]]],
    ["rule",[["id","chs"],["seq",[["sq","'['"],["rep",[["pre",[["pfx","~"],["sq","']'"]]],
        ["sfx","*"]]],["sq","']'"]]]]],
    ["rule",[["id","group"],["seq",[["dq","\"( \""],["id","alt"],["dq","\" )\""]]]]]]]

class Peg: # parse result...
    def __init__(self, ok, err, ptree, parse = None):
        self.ok = ok
        self.err = err
        self.ptree = ptree
        self.parse = parse
    def __repr__(self):
        if self.ok: return f"{self.ptree}"
        return f"{self.err}"
        # return f"Peg(ok: {self.ok}, err: {self.err}, ptree: {self.ptree})" 

class Env(): # parser machine environment...
    def __init__(self, code, input):
        self.code = code
        self.input = input
        self.pos = 0
        self.end = len(input)
        self.tree = [] # build parse tree

        self.trace = False
        self.trace_pos = -1
        self.line_map = None

def parse(code, input):
    env = Env(code, input)
    result = eval(code["$start"], env)
    return Peg(result, None, env.tree[0])

# -- instruction functions -------------------------------

def id(exp, env):
    if env.trace: trace_report(exp, env)
    name = exp[1]
    start = env.pos
    stack = len(env.tree)
    name = exp[1]
    expr = env.code[name]
    result = eval(expr, env)
    if not result: return False
    size = len(env.tree)
    if name[0] == '_':  # no results required..
        if len(env.tree) > stack: env.tree = env.tree[0:stack]
        return True
    if size-stack > 1 or name[0] <= "Z":
        env.tree[stack:] = [[name, env.tree[stack:]]]
        return True
    if size == stack:
        env.tree.append([name, env.input[start:env.pos]])
        return True
    return True  # elide redundant rule name

def seq(exp, env):
    start = env.pos
    stack = len(env.tree)
    for arg in exp[1]:
        if not eval(arg, env):
            if len(env.tree) > stack:
                env.tree = env.tree[0:stack]       
            env.pos = start 
            return False
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

def pre(exp, env):
    [_pre, [[_pfx, sign], term]] = exp
    start = env.pos
    stack = len(env.tree)
    result = eval(term, env)
    if len(env.tree) > stack: env.tree = env.tree[0:stack]
    env.pos = start # reset
    if sign == "~":
        if result == False and start < env.end:
            env.pos += 1; # match a character
            return True;
        return False;
    if sign == "!": return not result
    return result # &

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
    "pre": pre,
    "sq": sq,
    "dq": dq,
    "chs": chs,
}

def eval(exp, env):
    # print(exp, exp[0])
    return instruct[exp[0]](exp, env)

# -- utils ------------------------------------------------

def trace_report(exp, env):
    if exp[0] != "id": return
    if env.pos == env.trace_pos:
        print(f" {exp[1]}", end="")
        return
    env.trace_pos = env.pos
    if env.line_map == None:
        env.line_map = make_line_map(env.input)
    report = line_report(env.input, env.pos, env.line_map)
    print(f"{report} {exp[1]}",end="")

def line_report(input, pos, line_map):
    num = " "+line_col(input, pos, line_map)+": "
    before = input[0:pos]
    if pos > 30: before = "... "+input[pos-25:pos]
    inset = "\n"+num+" "*len(before)
    before = " "*len(num) + before
    after = input[pos:]
    if pos+35 < len(input): after = input[pos:pos+30]+" ..."
    line = "\n"
    for c in before+after:
        if c < " ": c = " "
        line += c
    return line+inset+"^"

def line_col(input, pos, line_map):
    line = 1
    while line_map[line] < pos: line += 1
    col = pos - line_map[line-1]
    return str(line)+"."+str(col)

def make_line_map(input):
    line_map = [-1] # eol before start
    for i in range(len(input)):
        if input[i] == "\n": line_map.append(i)
    line_map.append(len(input)+1) # eof after end
    return line_map

# -- ptree -> code compiler ------------------------------------------------

def _compile(ptree): # ptree -> code
    code = {}        # trivial skeleton for simple interpreter instructions
    for rule in ptree[1]:
        [_rule, [[_id, name], exp]] = rule
        code[name] = exp
    [_rule, [[_id, start], _exp]] = ptree[1][0]
    code["$start"] = ["id", start]
    return code

boot_code = _compile(boot_ptree)  # ; print(boot_code)

pPEG_boot = parse(boot_code, pPEG_grammar)

print(pPEG_boot)

pPEG_code = _compile(pPEG_boot.ptree)

pPEG_pPEG = parse(pPEG_code, pPEG_grammar)

import json

pPEG_boot_ptree = json.dumps(pPEG_boot.ptree)

pPEG_pPEG_ptree = json.dumps(pPEG_pPEG.ptree)

print("boot success: ", pPEG_boot_ptree == pPEG_pPEG_ptree)

print( json.dumps(pPEG_boot.ptree) ) 

print( json.dumps(pPEG_pPEG.ptree) ) 


"""  Impementation Notes:

Uses boot ptree from step 4 -- compile into code

Add: Peg class for return values: {ok, err, ptree, parse}

Uses parser machine from step 4, with Peg result

Bootstrap pPEG parses pPEG

TODO extra features in pPEG yet to be implemented
- _space_ to enable comments
- numeric repeat range
- case insensitive string matching

TODO fault reporting

TODO API grammar compile function

"""
