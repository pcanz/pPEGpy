"""
    Step 6: 
    full pPEG grammar,
    pPEG ptree from step 5 
    export grammar pPEG.compile API
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

pPEG_ptree = ["Peg", [["rule", [["id", "Peg"], ["seq", [["dq", "\" \""], ["rep", [["seq", [["id", "rule"], ["dq", "\" \""]]], ["sfx", "+"]]]]]]], ["rule", [["id", "rule"], ["seq", [["id", "id"], ["dq", "\" = \""], ["id", "alt"]]]]], ["rule", [["id", "alt"], ["seq", [["id", "seq"], ["rep", [["seq", [["dq", "\" / \""], ["id", "seq"]]], ["sfx", "*"]]]]]]], ["rule", [["id", "seq"], ["seq", [["id", "rep"], ["rep", [["seq", [["dq", "\" \""], ["id", "rep"]]], ["sfx", "*"]]]]]]], ["rule", [["id", "rep"], ["seq", [["id", "pre"], ["rep", [["id", "sfx"], ["sfx", "?"]]]]]]], ["rule", [["id", "pre"], ["seq", [["rep", [["id", "pfx"], ["sfx", "?"]]], ["id", "term"]]]]], ["rule", [["id", "term"], ["alt", [["id", "call"], ["id", "sq"], ["id", "dq"], ["id", "chs"], ["id", "group"], ["id", "extn"]]]]], ["rule", [["id", "id"], ["seq", [["chs", "[a-zA-Z_]"], ["rep", [["chs", "[a-zA-Z0-9_]"], ["sfx", "*"]]]]]]], ["rule", [["id", "pfx"], ["chs", "[&!~]"]]], ["rule", [["id", "sfx"], ["alt", [["chs", "[+?]"], ["seq", [["sq", "'*'"], ["rep", [["id", "range"], ["sfx", "?"]]]]]]]]], ["rule", [["id", "range"], ["seq", [["id", "num"], ["rep", [["seq", [["id", "dots"], ["rep", [["id", "num"], ["sfx", "?"]]]]], ["sfx", "?"]]]]]]], ["rule", [["id", "num"], ["rep", [["chs", "[0-9]"], ["sfx", "+"]]]]], ["rule", [["id", "dots"], ["sq", "'..'"]]], ["rule", [["id", "call"], ["seq", [["id", "id"], ["pre", [["pfx", "!"], ["dq", "\" =\""]]]]]]], ["rule", [["id", "sq"], ["seq", [["dq", "\"'\""], ["rep", [["pre", [["pfx", "~"], ["dq", "\"'\""]]], ["sfx", "*"]]], ["dq", "\"'\""], ["rep", [["sq", "'i'"], ["sfx", "?"]]]]]]], ["rule", [["id", "dq"], ["seq", [["sq", "'\"'"], ["rep", [["pre", [["pfx", "~"], ["sq", "'\"'"]]], ["sfx", "*"]]], ["sq", "'\"'"], ["rep", [["sq", "'i'"], ["sfx", "?"]]]]]]], ["rule", [["id", "chs"], ["seq", [["sq", "'['"], ["rep", [["pre", [["pfx", "~"], ["sq", "']'"]]], ["sfx", "*"]]], ["sq", "']'"]]]]], ["rule", [["id", "group"], ["seq", [["dq", "\"( \""], ["id", "alt"], ["dq", "\" )\""]]]]], ["rule", [["id", "extn"], ["seq", [["sq", "'<'"], ["rep", [["pre", [["pfx", "~"], ["sq", "'>'"]]], ["sfx", "*"]]], ["sq", "'>'"]]]]], ["rule", [["id", "_space_"], ["rep", [["alt", [["seq", [["sq", "'#'"], ["rep", [["pre", [["pfx", "~"], ["chs", "[\n\r]"]]], ["sfx", "*"]]]]], ["rep", [["chs", "[ \t\n\r]"], ["sfx", "+"]]]]], ["sfx", "*"]]]]]]]

class Peg: # parse result...
    def __init__(self, ok, err, ptree, parse = None):
        self.ok = ok
        self.err = err
        self.ptree = ptree
        self.parse = parse

    def __repr__(self):
        if self.ok: return f"{self.ptree}"
        return f"{self.err}"

class Env(): # parser machine environment...
    def __init__(self, code, input):
        self.code = code
        self.input = input
        self.pos = 0
        self.end = len(input)
        self.tree = [] # build parse tree
        self.err = ""

        self.depth = -1
        self.max_depth = 100
        self.in_rule = None

        self.peak_fail = -1
        self.peak_rule = None

        self.trace = False
        self.trace_pos = -1
        self.line_map = None

def _parse(code, input):
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
    if env.depth == env.max_depth:
        env.err += f"recursion max-depth exceeded in: {name} "
        return False
    env.in_rule = name
    env.depth += 1
    result = eval(expr, env)
    env.depth -= 1
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
            if env.pos > start and env.pos > env.peak_fail:
                env.peak_fail = env.pos
                env.peak_rule = env.in_rule
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
        if env.pos > start and env.pos > env.peak_fail:
            env.peak_fail = env.pos
            env.peak_rule = env.in_rule
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

# -- compiler --------------------------------------------------------------

def _compile(ptree): # ptree -> code
    code = {}        # trivial skeleton for simple interpreter instructions
    for rule in ptree[1]:
        [_rule, [[_id, name], exp]] = rule
        code[name] = exp
    [_rule, [[_id, start], _exp]] = ptree[1][0]
    code["$start"] = ["id", start]
    return code

pPEG_code = _compile(pPEG_ptree)  #; print(pPEG_code)

# -- pPEG.compile grammar API ----------------------------------------------------------

def compile(grammar):
    peg = _parse(pPEG_code, grammar)
    if not peg.ok:
        peg.err = "grammar error: "+peg.err
        peg.parse = lambda _ : peg
        return peg
    code = _compile(peg.ptree)
    def parser(input):
        return _parse(code, input)
    return Peg(True, None, peg, parser)  # {"ok": True,  "parse": parser }

# -- test ----------------------------------------

date = compile("""
    date  = year '-' month '-' day
    year  = [0-9]+
    month = [0-9]+
    day   = [0-9]+
""")

print( date.parse("2012-03-04") )


"""  Impementation Notes:

Uses pPEG ptree from step 5

Uses parser machine from step 5

Add: fault reports
    - max recusion depth
    - failure info in seq

Add: API pEPG.compile(grammar), and Peg.parse(input)   
    - _parse private interal parser machine 
    - _compile private internal ptree -> code

TODO extra features in pPEG
    - _space_ to enable comments
    - numeric repeat range
    - case insensitive string matching

TODO: _compile optimizations
    - check all grammar rule names are defined
    - use instruction functions and eliminate eval(exp)
    - compile repeat *+? into max min values for rep instruction
    - extend other instructions with min, max repeats and ~ negation
    - compute an first-char guard for the alt instruction


"""

