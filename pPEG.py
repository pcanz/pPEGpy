"""
    pPEG is a portable PEG grammar parser generator

    This is the only file you need.

    pPEG.compile(grammar) -> <Peg>

    <Peg>.parse(input) -> <Peg> 

    Peg .ok boolean 
        .err string
        .ptree parse tree
        .parse input -> Peg
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
    """ pPEG.compile(grammar) result, or Peg.parse(input) result """
    def __init__(self, ok, err, ptree, parse = None):
        self.ok = ok       # boolean
        self.err = err     # error string
        self.ptree = ptree # pPEG parse tree
        self.parse = parse # input -> Peg

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
        self.in_rule = [None]*self.max_depth

        self.peak_fail = -1
        self.peak_rule = None
        self.peak_expect = None

        self.trace = False
        self.trace_pos = -1
        self.line_map = None

def _parse(code, input):
    env = Env(code, input)
    result = id(code["$start"], env)
    if env.trace:
        print(env.err)
    pos = env.pos
    err = env.err
    if pos < env.end or not result:
        err += "parse failed: "
        details = ""
        if env.peak_fail >= pos:
            pos = env.peak_fail
            details = f"{env.peak_rule} {expected(env.peak_expect)} "
        else:
            details = f"{env.peak_rule or env.in_rule[0]} "
        if result:
            err += "fell short at:"
            result = False
        err += f"{line_report(env, pos)} {details}"
    if not result: return Peg(result, err, env.tree)
    return Peg(result, err, env.tree[0])

# -- instruction functions -------------------------------

def id(exp, env):
    if env.trace: trace_report(exp, env)
    start = env.pos
    stack = len(env.tree)
    name = exp[1]
    expr = env.code[name]
    if env.depth == env.max_depth:
        env.err += f"recursion max-depth exceeded in: {name} "
        return False
    env.depth += 1
    env.in_rule[env.depth] = name
    result = expr[0](expr, env)
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
        if not arg[0](arg, env):
            if env.pos > start and env.pos > env.peak_fail:
                env.peak_fail = env.pos
                env.peak_rule = env.in_rule[env.depth]
                env.peak_expect = arg
            if len(env.tree) > stack:
                env.tree = env.tree[0:stack]
            env.pos = start      
            return False
    return True

def alt(exp, env):
    start = env.pos
    stack = len(env.tree)
    for arg in exp[1]:
        if arg[0](arg, env): return True
        # if env.pos > start and env.pos > env.peak_fail:
        #     env.peak_fail = env.pos
        #     env.peak_rule = env.in_rule[env.depth]
        if len(env.tree) > stack:
            env.tree = env.tree[0:stack]       
        env.pos = start
    return False

def rep(exp, env):
    [_rep, [expr, [_sfx, sfx]]] = exp
    min, max = 0, 0  # sfx == "*" 
    if  sfx == "+": min = 1
    elif sfx == "?": max = 1
    return rep_(["rep_", expr, min, max], env)

def rep_(exp, env):
    [_, expr, min, max] = exp
    count = 0
    while True:
        start = env.pos
        result = expr[0](expr, env)
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
    result = term[0](term, env)
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

def sq_(exp, env):
    str = exp[1]
    pos = env.pos
    if len(exp) > 2:  # icase
        end = pos+len(str)
        if end > env.end: return False
        nxt = env.input[pos:end]
        if nxt.upper() == str:
            env.pos = end
            return True
        return False
    if env.input.startswith(str, pos):
        env.pos = pos+len(str)
        return True
    return False

def dq(exp, env):
    space = env.code.get("_space_")
    for c in exp[1][1:-1]:
        if c == " ":
            if space:
                if not space[0](space, env): return False
            else:
                while env.pos < env.end and env.input[env.pos] <= " ": env.pos += 1
            continue
        if env.pos >= env.end or c != env.input[env.pos]: return False
        env.pos += 1
    return True

def dq_(exp, env):
    str = exp[1]
    space = env.code.get("_space_")
    icase = len(exp) > 2
    for c in str:
        if c == " ":
            if space:
                if not space[0](space, env): return False
            else:
                while env.pos < env.end and env.input[env.pos] <= " ": env.pos += 1
            continue
        if env.pos >= env.end: return False
        x = env.input[env.pos]       
        if icase: x = x.upper()
        if c != x: return False
        env.pos += 1
    return True

def chs(exp, env):
    if env.pos >= env.end: return False
    str = exp[1]
    n = len(str)-1
    ch = env.input[env.pos]
    i = 1 # "[...]"
    while i < n:       
        if i+2 < n and str[i+1] == '-':
            if ch < str[i] or ch > str[i+2]:
                i += 3
                continue
        elif ch != str[i]: 
            i += 1
            continue
        env.pos += 1
        return True
    return False

def chs_(exp, env): # ~[x]*
    [_chs, str, neg, min, max] = exp
    n = len(str)-1
    input, end = env.input, env.end
    pos = env.pos
    count = 0
    while True:
        if pos >= end: break
        ch = input[pos]
        i, hit = 1, False
        while i < n:  # "[...]"     
            if i+2 < n and str[i+1] == '-':
                if ch < str[i] or ch > str[i+2]:
                    i += 3
                    continue
            elif ch != str[i]: 
                i += 1
                continue
            break
        if i < n: hit = True
        if hit == neg: break # neg == ~ => Ture
        pos += 1
        count += 1
        if count == max: break # max 0 means any
    env.pos = pos
    if count < min: return False
    return True

op = {
    "id": id,
    "seq": seq,
    "alt": alt,
    "rep": rep,
    "rep_": rep_,
    "pre": pre,
    "sq": sq,
    "sq_": sq_,
    "dq": dq,
    "dq_": dq_,
    "chs": chs,
    "chs_": chs_,
}

# def eval(exp, env):
#     # print(exp, exp[0])
#     return op[exp[0]](exp, env)

# -- utils ------------------------------------------------

def trace_report(exp, env): 
    # if exp[0] != "id": return
    if env.pos == env.trace_pos:
        print(f" {exp[1]}", end="")
        return
    env.trace_pos = env.pos
    report = line_report(env, env.pos)
    print(f"{report} {exp[1]}",end="")

def line_report(env, pos):
    input = env.input
    if env.line_map == None:
        env.line_map = make_line_map(input)
    num = " "+line_col(input, pos, env.line_map)+": "
    before = input[0:pos]
    if pos > 30: before = "... "+input[pos-25:pos]
    inset = "\n"+num+" "*len(before)
    before = " "*len(num) + before
    after = input[pos:]
    if pos+35 < len(input): after = input[pos:pos+30]+" ..."
    line = "\n"
    for c in before+after:
        if c < " ":
            if c == "\n": c = '¬'
            elif c == "\t": c = '·'
            else: c = " "
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

# -- display expr ---------------------------------------------

def expected(exp):
    expect = display(exp)
    if not expect: return ''
    return f" expected: {expect}"

op_display = {
    "id": lambda exp: exp[1],
    "seq": lambda exp: ' '.join(list(map(display,exp[1]))),
    "alt": lambda exp: '/'.join(list(map(display,exp[1]))),
    "rep": lambda exp: show_rep(exp),
    "rep_": lambda exp: show_rep_(exp),
    "pre": lambda exp: show_pre(exp),
    "sq": lambda exp: exp[1],
    "dq": lambda exp: exp[1],
    "sq_": lambda exp: f"'{exp[1]}'",
    "dq_": lambda exp: f'"{exp[1]}"',
    "chs": lambda exp: exp[1],
    "chs_": lambda exp: show_chs_(exp),
}

def display(exp):
    name = exp[0].__name__ 
    show = op_display.get(name)
    if not show: return ''
    return show(exp)

def show_rep(exp):  # e*
    [_rep, [expr, [_sfx, sfx]]] = exp
    return f"{display(expr)}{sfx}"

def show_rep_(exp):  # e*
    [_, expr, min, max] = exp
    return f"{display(expr)}{sfx(min,max)}"

def show_pre(exp):  # !e
    [_pre, [[_pfx, sign], term]] = exp
    return f"{display(term)}"

def show_chs_(exp):  # ~[x]*
    [_chs, str, neg, min, max] = exp
    if neg: return f"~{str}{sfx(min,max)}"
    return f"~{str}{sfx(min,max)}"

def sfx(min, max):
    if min == 1 and max == 1: return ''
    if min == 0 and max == 0: return "*"
    if min == 1 and max == 0: return "+"
    if min == 0 and max == 1: return "?"
    if max == 0: return f"*{min}.."
    return f"*{min}..{max}"

# -- compile parser code -----------------------------------------------------------

def _compile(ptree): # ptree -> code
    code = {}
    for rule in ptree[1]:
        [_rule, [[_id, name], exp]] = rule
        code[name] = exp
    
    code["$err"] = ""

    def emit_id(exp):
        rule = code.get(exp[1])
        if not rule:
            code["$err"] += "missing rule: "+name+"\n"
            #raise Exception("missing rule: "+name)
        return [op[exp[0]], exp[1]]

    def emit_seq(exp):
        return [op["seq"], list(map(optimize, exp[1]))]
    def emit_alt(exp):
        return [op["alt"], list(map(optimize, exp[1]))]

    def emit_rep(exp):
        # sfx   = [+?] / '*' range?
        # range = num (dots num?)?
        [_rep, [expr, [sfx, data]]] = exp
        min, max = 0, 0  # sfx data == "*"
        if sfx == "sfx":
            if  data == "+": min = 1
            elif data == "?": max = 1
        elif sfx == "num": # *N => ["num", N]
            min = int(data)
            max = min
        elif sfx == "range":    # *N..M
            if len(data) == 2:  # *N.. => ["range", [["num", N], ["dots", ".."]]]
                [[_num, N], _dots] = data
                min = int(N)
            else: # *N..M => ["range", [["num", N], ["dots", ".."], ["num", M]]]
                [[_num, N], _dots, [_, M]] = data
                min = int(N)
                max = int(M)
        if expr[0] == "chs":
            return [op["chs_"], expr[1], False, min, max]
        if expr[0] == "pre":
            [_pre, [[_pfx, sign], term]] = expr
            if sign == "~":
                if term[0] == "chs":
                    return [op["chs_"], term[1], True, min, max]
                if term[0] == 'sq' and len(term[1]) == 3:  # "'x'"
                    return [op["chs_"], term[1], True, min, max]
                if term[0] == 'dq' and len(term[1]) == 3 and term[1][1] != " ":  # '"x"':
                    return [op["chs_"], term[1], True, min, max]
        return [op["rep_"], optimize(expr), min, max]

    def emit_pre(exp):
        [_pre, [[_pfx, sign], term]] = exp
        return [op[_pre], [[_pfx, sign], optimize(term)]]

    def emit_sq_dq(exp): # TODO escapes not correct for Unicodes ....
        str = exp[1]
        icase = False
        if str[-1:] == "i":
            str = str[1:-2].upper()
            icase = True
        else:
            str = str[1:-1]
        str = bytes(str, "utf-8").decode("unicode_escape")
        if icase: return [op[exp[0]+'_'], str, True]
        return [op[exp[0]+'_'], str]

    def emit_leaf(exp):
        return [op[exp[0]], exp[1]]

    emiter = {
        "id": emit_id,
        "seq": emit_seq,
        "alt": emit_alt,
        "rep": emit_rep,
        "pre": emit_pre,
        "sq": emit_sq_dq,
        "dq": emit_sq_dq,
        "chs": emit_leaf,
    }

    def optimize(exp):
        return emiter[exp[0]](exp)

    for name in code:
        code[name] = optimize(code[name])

    [_rule, [[_id, start], _exp]] = ptree[1][0]
    code["$start"] = [op["id"], start]
    return code

pPEG_code = _compile(pPEG_ptree) # ; print(pPEG_code)

# -- pPEG.compile grammar API ----------------------------------------------------------

def compile(grammar):
    """ pPEG.compile function returns a pPEG.Peg parser object """
    peg = _parse(pPEG_code, grammar)
    if not peg.ok:
        peg.err = "grammar error: "+peg.err
        peg.parse = lambda _ : peg
        return peg
    code = _compile(peg.ptree)
    if code["$err"]: return Peg(False, code["$err"], peg, lambda _ : peg)
    return Peg(True, None, peg, lambda input: _parse(code, input))


