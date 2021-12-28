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

def _parse(code, input):
    pos = 0
    end = len(input)
    tree = [] # build parse tree
    err = ""

    depth = -1
    max_depth = 100
    in_rule = None

    peak_fail = -1
    peak_rule = None

    trace = False
    trace_report = ""
    trace_pos = -1
    line_map = None

    def id(exp):
        nonlocal tree, depth, in_rule, err
        if trace: trace_report(exp)
        start = pos
        stack = len(tree)
        name = exp[1]
        expr = code.get(name)
        if not expr:
            err += f"undefined rule: {name} "
            return False
        if depth == max_depth:
            err += f"recursion max-depth exceeded in: {name} "
            return False
        in_rule = name
        depth += 1
        result = op[expr[0]](expr) # eval(expr) # 
        depth -= 1
        if not result: return False
        size = len(tree)
        if name[0] == '_':  # no results required..
            if len(tree) > stack: tree = tree[0:stack]
            return True
        if size-stack > 1 or name[0] <= "Z":
            tree[stack:] = [[name, tree[stack:]]]
            return True
        if size == stack:
            tree.append([name, input[start:pos]])
            return True
        return True  # elide redundant rule name

    def seq(exp):
        start = pos
        for arg in exp[1]:
            if not op[arg[0]](arg): return False
            # if not eval(arg): return False
        return True

    def alt(exp):
        nonlocal pos, tree, peak_fail, peak_rule
        start = pos
        stack = len(tree)
        for arg in exp[1]:
            if op[arg[0]](arg): return True
            # if eval(arg): return True
            if pos > start and pos > peak_fail:
                peak_fail = pos
                peak_rule = in_rule
            if len(tree) > stack: tree = tree[0:stack]   
            pos = start # reset, try next arg
        return False

    def rep(exp):
        [_rep, [expr, [_sfx, sfx]]] = exp
        min, max = 0, 0  # sfx == "*" 
        if  sfx == "+": min = 1
        elif sfx == "?": max = 1
        return rep_(["rep_", expr, min, max])
        
    def rep_(exp):
        nonlocal pos, tree
        [_, expr, min, max] = exp
        count = 0
        while True:
            start = pos
            stack = len(tree)
            result = op[expr[0]](expr)  # eval(expr) 
            if result == False: break
            if pos == start: break # no progress
            count += 1
            if count == max: break # max 0 means any
        if count < min: return False
        if result == False: # last repeat loop eval
            if len(tree) > stack: tree = tree[0:stack]
            pos = start
        return True

    def pre(exp):
        nonlocal pos, tree
        [_pre, [[_pfx, sign], term]] = exp
        start = pos
        stack = len(tree)
        result = op[term[0]](term) # eval(term) # 
        if len(tree) > stack: tree = tree[0:stack]
        pos = start # reset
        if sign == "~":
            if result == False and start < end:
                pos += 1; # match a character
                return True
            return False
        if sign == "!": return not result
        return result # &

    def sq(exp):
        nonlocal pos
        for c in exp[1][1:-1]:
            if pos >= end or c != input[pos]: return False
            pos += 1
        return True

    def dq(exp):
        nonlocal pos
        for c in exp[1][1:-1]:
            if pos >= end: return False
            if c == " ":
                space = code.get("_space_")
                if space:
                    if not op[space[0]](space): return False
                    # if not eval(space): return False
                else:
                    while pos < end and input[pos] <= " ": pos += 1
                continue
            if c != input[pos]: return False
            pos += 1
        return True

    def chs(exp):
        nonlocal pos
        if pos >= end: return False
        str = exp[1]
        n = len(str)
        ch = input[pos]
        i = 1 # "[...]"
        while i < n-1:       
            if i+2 < n-1 and str[i+1] == '-':
                if ch < str[i] or ch > str[i+2]:
                    i += 3
                    continue
            elif ch != str[i]: 
                i += 1
                continue
            pos += 1
            return True
        return False

    def chs_(exp):
        nonlocal pos, tree
        if pos >= end: return False
        [_, str, min, max] = exp
        n = len(str)
        start, count = pos, 0
        while pos < end:
            ch = input[pos]
            i = 1 # "[...]"
            while i < n-1:       
                if i+2 < n-1 and str[i+1] == '-':
                    if ch < str[i] or ch > str[i+2]:
                        i += 3
                        continue
                elif ch != str[i]: 
                    i += 1
                    continue
                pos += 1           
                break
            if pos == start: break # fail, no further progress
            start = pos
            count += 1
            if count == max: break # max 0 means any
        if count < min: return False
        return True
        

    # -- utils ------------------------------------------------

    def trace_report(exp):
        nonlocal err, trace_pos, line_map
        if exp[0] != "id": return
        if pos == trace_pos:
            trace_report += f" {exp[1]}"
            return
        trace_pos = pos
        trace_report += f"{line_report(input, pos)} {exp[1]}"

    def line_report(input, pos):
        num = " "+line_col(input, pos)+": "
        before = input[0:pos]
        if pos > 40: before = "... "+input[pos-30:pos]
        inset = "\n"+num+" "*len(before)
        before = " "*len(num) + before
        after = input[pos:]
        if pos+40 < len(input): after = input[pos:pos+30]+" ..."
        line = "\n"
        for c in before+after:
            if c < " ":
                if c == "\n": c = "¬" 
                else: c = " "
            line += c
        return line+inset+"^"

    def line_col(input, pos):
        if not line_map: make_line_map()
        line = 1
        while line_map[line] < pos: line += 1
        col = pos - line_map[line-1]
        return str(line)+"."+str(col)

    def make_line_map():
        nonlocal line_map
        line_map = [-1] # eol before start
        for i in range(len(input)):
            if input[i] == "\n": line_map.append(i)
        line_map.append(len(input)+1) # eof after end

    # -- _parse ---------------------------------------

    op = {
        "id": id,
        "seq": seq,
        "alt": alt,
        "rep": rep,
        "rep_": rep_,
        "pre": pre,
        "sq": sq,
        "dq": dq,
        "chs": chs,
        "chs_": chs_,
    }

    result = id(code["$start"])

    if trace:
        print(err)
    if pos < end:
        err += "parse failed: "
        details = ""
        if peak_fail > pos:
           pos = peak_fail
           details = f"{peak_rule} " 
        if result:
            err += "fell short at:"
            result = False
        err += f"{line_report(input, pos)} {details}"
    if not result: return Peg(result, err, tree)
    return Peg(result, err, tree[0])

# -- compile parser code -----------------------------------------------------------

def _compile(ptree): # ptree -> code

    def emit_id(exp):
        rule = code.get(exp[1])
        if not rule:
            raise Exception("missing rule: "+name)
        return exp

    def emit_seq(exp):
        return ["seq", list(map(optimize, exp[1]))]
    def emit_alt(exp):
        return ["alt", list(map(optimize, exp[1]))]

    def emit_rep(exp):
        [_rep, [expr, [_sfx, sfx]]] = exp
        min, max = 0, 0  # sfx == "*" 
        if  sfx == "+": min = 1
        elif sfx == "?": max = 1
        if expr[0] == "chs":
            return ["chs_", expr[1], min, max]
        return ["rep_", expr, min, max]

    emiter = {
        "id": emit_id,
        "seq": emit_seq,
        "alt": emit_alt,
        "rep": emit_rep,
    }

    def optimize(exp):
        emit = emiter.get(exp[0])
        if emit: return emit(exp)
        return exp

    code = {}
    for rule in ptree[1]:
        [_rule, [[_id, name], exp]] = rule
        code[name] = exp

    for name in code:
        code[name] = optimize(code[name])

    [_rule, [[_id, start], _exp]] = ptree[1][0]
    code["$start"] = ["id", start]
    return code

pPEG_code = _compile(pPEG_ptree) # ; print(pPEG_code)

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

class Peg:
    def __init__(self, ok, err, ptree, parse = None):
        self.ok = ok
        self.err = err
        self.ptree = ptree
        self.parse = parse
    def __repr__(self):
        if self.ok: return f"{self.ptree}"
        return f"{self.err}"
        # return f"Peg(ok: {self.ok}, err: {self.err}, ptree: {self.ptree})" 

# -- test ----------------------------------------

def test():
    # peg = compile(pPEG_grammar)
    date = compile("""
    date  = year '-' month '-' day
    year  = [0-9]+
    month = [0-9]+
    day   = [0-9]+
    """)

if __name__ == '__main__':
    date = compile("""
    # yes we have comments...
    date  = year '-' month '-' day
    year  = [0-9]+
    month = [0-9]+
    day   = [0-9]+
    """)

    print( date.parse("2012-03-04") )

    # import scalene
    # scalene_profiler.start()
    # test()
    # scalene_.profiler.stop()


    # import timeit
    # number = 10000
    # print("timeit bench mark x"+str(number))
    # print(timeit.timeit("test()", number=number, globals=locals()))

"""  Impementation Notes:

Done: _compile optimizations
    - check all grammar rule names are defined
    - use instruction functions and eliminate eval(exp)

Using eval():
    3.0  ms to compile(pPEG_grammar)
    0.46 ms to compile(date)

Using eval(): but with construct-once instruct dict....
    2.1  ms to compile(pPEG_grammar)
    0.31 ms to compile(date)

Using op[exp[0]](exp): ---  on iMac M1
    1.72 ms  to compile(pPEG_grammar) 1.69 with min, max rep_, 1.66 with chs_
    0.26 ms to compile(date) 0.25 with min,max rep_, 0.24 with chs_

Using op[exp[0]](exp): --- on MacBook 2017 1.3GH i5
    3.66 ms  to compile(pPEG_grammar)
    0.55 ms to compile(date)


TODO extra features in pPEG
    - numeric repeat range
    - case insensitive string matching

TODO: _compile optimizations
    - compile repeat *+? into max min values for rep instruction
    - extend other instructions with min, max repeats and ~ negation
    - compute an first-char guard for the alt instruction


"""

