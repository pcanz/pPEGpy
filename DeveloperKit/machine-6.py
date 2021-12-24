"""
    Step 6: 
    full pPEG grammar,
    uses pPEG ptree from step 5 
    export grammar compile API
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

    _space_ = ('#' ~[\n\r]* / [ \t\n\r]*)*
"""

pPEG_ptree = ["Peg", [["rule", [["id", "Peg"], ["seq", [["dq", "\" \""], ["rep", [["seq", [["id", "rule"], ["dq", "\" \""]]], ["sfx", "+"]]]]]]], ["rule", [["id", "rule"], ["seq", [["id", "id"], ["dq", "\" = \""], ["id", "alt"]]]]], ["rule", [["id", "alt"], ["seq", [["id", "seq"], ["rep", [["seq", [["dq", "\" / \""], ["id", "seq"]]], ["sfx", "*"]]]]]]], ["rule", [["id", "seq"], ["seq", [["id", "rep"], ["rep", [["seq", [["dq", "\" \""], ["id", "rep"]]], ["sfx", "*"]]]]]]], ["rule", [["id", "rep"], ["seq", [["id", "pre"], ["rep", [["id", "sfx"], ["sfx", "?"]]]]]]], ["rule", [["id", "pre"], ["seq", [["rep", [["id", "pfx"], ["sfx", "?"]]], ["id", "term"]]]]], ["rule", [["id", "term"], ["alt", [["id", "call"], ["id", "sq"], ["id", "dq"], ["id", "chs"], ["id", "group"], ["id", "extn"]]]]], ["rule", [["id", "id"], ["seq", [["chs", "[a-zA-Z_]"], ["rep", [["chs", "[a-zA-Z0-9_]"], ["sfx", "*"]]]]]]], ["rule", [["id", "pfx"], ["chs", "[&!~]"]]], ["rule", [["id", "sfx"], ["alt", [["chs", "[+?]"], ["seq", [["sq", "'*'"], ["rep", [["id", "range"], ["sfx", "?"]]]]]]]]], ["rule", [["id", "range"], ["seq", [["id", "num"], ["rep", [["seq", [["id", "dots"], ["rep", [["id", "num"], ["sfx", "?"]]]]], ["sfx", "?"]]]]]]], ["rule", [["id", "num"], ["rep", [["chs", "[0-9]"], ["sfx", "+"]]]]], ["rule", [["id", "dots"], ["sq", "'..'"]]], ["rule", [["id", "call"], ["seq", [["id", "id"], ["pre", [["pfx", "!"], ["dq", "\" =\""]]]]]]], ["rule", [["id", "sq"], ["seq", [["dq", "\"'\""], ["rep", [["pre", [["pfx", "~"], ["dq", "\"'\""]]], ["sfx", "*"]]], ["dq", "\"'\""], ["rep", [["sq", "'i'"], ["sfx", "?"]]]]]]], ["rule", [["id", "dq"], ["seq", [["sq", "'\"'"], ["rep", [["pre", [["pfx", "~"], ["sq", "'\"'"]]], ["sfx", "*"]]], ["sq", "'\"'"], ["rep", [["sq", "'i'"], ["sfx", "?"]]]]]]], ["rule", [["id", "chs"], ["seq", [["sq", "'['"], ["rep", [["pre", [["pfx", "~"], ["sq", "']'"]]], ["sfx", "*"]]], ["sq", "']'"]]]]], ["rule", [["id", "group"], ["seq", [["dq", "\"( \""], ["id", "alt"], ["dq", "\" )\""]]]]], ["rule", [["id", "extn"], ["seq", [["sq", "'<'"], ["rep", [["pre", [["pfx", "~"], ["sq", "'>'"]]], ["sfx", "*"]]], ["sq", "'>'"]]]]], ["rule", [["id", "_space_"], ["rep", [["alt", [["seq", [["sq", "'#'"], ["rep", [["pre", [["pfx", "~"], ["chs", "[\n\r]"]]], ["sfx", "*"]]]]], ["rep", [["chs", "[ \t\n\r]"], ["sfx", "*"]]]]], ["sfx", "*"]]]]]]]

def parse(grammar_code, input):
    env = {
        "rules": grammar_code,
        "input": input,
        "pos": 0, # cursor position
        "tree": [], # build parse tree

        "trace": False,
        "trace_pos": -1,
        "line_map": None
    }
    start = env["rules"]["$start"]
    result = eval(start, env)
    return {"ok": result, "err": env["pos"], "ptree": env["tree"][0]}

def eval(exp, env):
    # print(exp, env["pos"])
    instruct = {
        "id": id,
        "seq": seq,
        "alt": alt,
        "rep": rep,
        "pre": pre,
        "sq": sq,
        "dq": dq,
        "chs": chs
    }
    return instruct[exp[0]](exp, env)

def id(exp, env):
    if env["trace"]: trace(exp, env)
    name = exp[1]
    start = env["pos"]
    stack = len(env["tree"])
    expr = env["rules"][name]
    if not expr: raise Exception("undefined rule: "+name)
    result = eval(expr, env)
    if not result: return False
    size = len(env["tree"])
    if name[0] == '_':  # no results required..
        if len(env["tree"]) > stack:
            env["tree"] = env["tree"][0:stack]
        return True
    if size-stack > 1 or name[0] <= "Z":
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

def rep(exp, env):
    [_rep, [expr, [_sfx, sfx]]] = exp
    min, max = 0, 0  # sfx == "*" 
    if  sfx == "+": min = 1
    elif sfx == "?": max = 1
    count, pos = 0, env["pos"]
    while True:
        result = eval(expr, env)
        if result == False: break
        if pos == env["pos"]: break # no progress
        count += 1
        if count == max: break # max 0 means any
        pos = env["pos"]
    if count < min: return False
    return True

def pre(exp, env):
    [_pre, [[_pfx, sign], term]] = exp
    start = env["pos"]
    stack = len(env["tree"])
    result = eval(term, env)
    if len(env["tree"]) > stack:
        env["tree"] = env["tree"][0:stack]
    env["pos"] = start # reset
    if sign == "~":
        if result == False and start < len(env["input"]):
            env["pos"] += 1; # match a character
            return True;
        return False;
    if sign == "!": return not result
    return result # &

def sq(exp, env):
    input = env["input"]
    end = len(input)
    for c in exp[1][1:-1]:
        pos = env["pos"]
        if pos >= end or c != input[pos]: return False
        env["pos"] = pos+1
    return True

def dq(exp, env):
    input = env["input"]
    end = len(input)
    for c in exp[1][1:-1]:
        pos = env["pos"]
        if pos >= end: return False
        if c == " ":
            while pos < end and input[pos] <= " ": pos += 1
            env["pos"] = pos
            continue
        if c != input[pos]: return False
        env["pos"] = pos+1
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

# -- trace reporting -----------------------------------------

def trace(exp, env):
    if exp[0] != "id": return
    pos = env["pos"]
    if pos == env["trace_pos"]:
        print(f" {exp[1]}", end="")
        return
    env["trace_pos"] = pos
    report = line_report(env, pos)
    print(f"{report} {exp[1]}",end="")

def line_report(env, pos):
    input = env["input"]
    end = len(input)
    num = " "+line_col(env, pos)+": "
    before = input[0:pos]
    if pos > 30: before = "... "+input[pos-25:pos]
    inset = "\n"+num+" "*len(before)
    before = " "*len(num) + before
    after = input[pos:]
    if pos+35 < end: after = input[pos:pos+30]+" ..."
    line = "\n"
    for c in before+after:
        if c < " ": c = " "
        line += c
    return line+inset+"^"

def line_col(env, pos):
    line_map = env["line_map"]
    if line_map == None:
        line_map = make_line_map(env)
        env["line_map"] = line_map
    line = 1
    while line_map[line] < pos: line += 1
    col = pos - line_map[line-1]
    return str(line)+"."+str(col)

def make_line_map(env):
    input = env["input"]
    line_map = [-1] # eol before start
    for i in range(len(input)):
        if input[i] == "\n": line_map.append(i)
    line_map.append(len(input)+1) # eof after end
    return line_map

# -- compiler --------------------------------------------------------------

def compiler(ptree): # ptree -> code
    code = {}        # trivial skeleton for simple interpreter instructions
    for rule in ptree[1]:
        [_rule, [[_id, name], exp]] = rule
        code[name] = exp
    [_rule, [[_id, start], _exp]] = ptree[1][0]
    code["$start"] = ["id", start]
    return code

pPEG_code = compiler(pPEG_ptree)  #; print(pPEG_code)

def compile(grammar):
    peg = parse(pPEG_code, grammar)
    print(peg)
    if not peg["ok"]: return peg
    code = compiler(peg["ptree"])
    print(code)   
    def parser(input):
        return parse(code, input)
    return {"ok": True,  "parse": parser }

# -- test ----------------------------------------

date = compile("""
    date  = year '-' month '-' day
    year  = [0-9]+
    month = [0-9]+
    day   = [0-9]+
""")

print( date["parse"]("2012-03-04") )


"""  Impementation Notes:

Uses pPEG ptree from step 5

Uses parser machine from step 5



TODO extra features in pPEG yet to be implemented
- numeric repeat range
- case insensitive string matching

TODO API grammar compile function

"""

