"""
  Step 4: 
    pPEG boot grammar, 
    full 8-instruction parser machine,
    trace rule calls line report
    generates bootstrap ptree for step 5
"""

boot_grammar = """
    Peg   = " " (rule " ")+
    rule  = id " = " alt

    alt   = seq (" / " seq)*
    seq   = rep (' ' rep)*
    rep   = pre sfx?
    pre   = pfx? term
    term  = id / sq / dq / chs / group

    id    = [a-zA-Z]+
    pfx   = [&!~]
    sfx   = [+?*]

    sq    = "'" ~"'"* "'"
    dq    = '"' ~'"'* '"'
    chs   = '[' ~']'* ']'
    group = "( " alt " )"
"""

boot_code = {
    "Peg":
        ["seq",[["dq","\" \""], ["rep",[
            ["seq",[["id","rule"], ["dq","\" \""]]], ["sfx","+"]]]]],
    "rule":
        ["seq",[["id","id"],["dq","\" = \""],["id","alt"]]],
    "alt":
        ["seq",[["id","seq"],
            ["rep",[["seq",[["dq","\" / \""],["id","seq"]]],["sfx","*"]]]]],
    "seq":
        ["seq",[["id","rep"],
            ["rep",[["seq",[["sq","' '"],["id","rep"]]],["sfx","*"]]]]],
    "rep":
        ["seq",[["id","pre"],["rep",[["id","sfx"],["sfx","?"]]]]],
    "pre":
        ["seq",[["rep",[["id","pfx"],["sfx","?"]]],["id","term"]]],
    "term":
        ["alt",[["id","id"],["id","sq"],["id","dq"],["id","chs"],["id","group"]]],
    "id":
        ["rep",[["chs","[a-zA-Z_]"],["sfx","+"]]],
    "pfx":
        ["chs","[&!~]"],
    "sfx":
        ["chs","[+?*]"],
    "sq":
        ["seq",[["dq","\"'\""],
            ["rep",[["pre",[["pfx","~"],["dq","\"'\""]]],["sfx","*"]]],
            ["dq","\"'\""]]],
    "dq":
        ["seq",[["sq","'\"'"],
            ["rep",[["pre",[["pfx","~"],["sq","'\"'"]]],["sfx","*"]]],
            ["sq","'\"'"]]],
    "chs":
        ["seq",[["sq","'['"],
            ["rep",[["pre",[["pfx","~"],["sq","']'"]]],["sfx","*"]]],
            ["sq","']'"]]],
    "group":
        ["seq",[["dq","\"( \""],["id","alt"],["dq","\" )\""]]],
    "$start":
        ["id", "Peg"]
}

def parse(code, input):
    pos = 0
    end = len(input)
    tree = [] # build parse tree

    trace = False
    trace_pos = -1
    line_map = None

    def eval(exp):
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
        return instruct[exp[0]](exp)

    def id(exp):
        nonlocal tree
        if trace: trace_report(exp)
        start = pos
        stack = len(tree)
        name = exp[1]
        expr = code[name]
        result = eval(expr)
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
        for arg in exp[1]:
            if not eval(arg): return False
        return True

    def alt(exp):
        nonlocal pos, tree
        start = pos
        stack = len(tree)
        for arg in exp[1]:
            if eval(arg): return True
            if len(tree) > stack: tree = tree[0:stack]       
            pos = start
        return False

    def rep(exp):
        [_rep, [expr, [_sfx, sfx]]] = exp
        min, max = 0, 0  # sfx == "*" 
        if  sfx == "+": min = 1
        elif sfx == "?": max = 1
        count = 0
        while True:
            start = pos
            result = eval(expr)
            if result == False: break
            if pos == start: break # no progress
            count += 1
            if count == max: break # max 0 means any
        if count < min: return False
        return True

    def pre(exp):
        nonlocal pos, tree
        [_pre, [[_pfx, sign], term]] = exp
        start = pos
        stack = len(tree)
        result = eval(term)
        if len(tree) > stack: tree = tree[0:stack]
        pos = start # reset
        if sign == "~":
            if result == False and start < end:
                pos += 1; # match a character
                return True;
            return False;
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

    def trace_report(exp):
        nonlocal trace_pos, line_map
        if exp[0] != "id": return
        if pos == trace_pos:
            print(f" {exp[1]}", end="")
            return
        trace_pos = pos
        if line_map == None:
            line_map = make_line_map(input)
        report = line_report(input, pos, line_map)
        print(f"{report} {exp[1]}",end="")

    result = eval(code["$start"])
    return (result, pos, tree)

# -- utils ------------------------------------------------

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


import json

print( json.dumps(parse(boot_code, boot_grammar)) ) 

"""
[true, 357, [["Peg", [["rule", [["id", "Peg"], ["seq", [["dq", "\" \""], ["rep", [["seq", [["id", "rule"], ["dq", "\" \""]]], ["sfx", "+"]]]]]]], ["rule", [["id", "rule"], ["seq", [["id", "id"], ["dq", "\" = \""], ["id", "alt"]]]]], ["rule", [["id", "alt"], ["seq", [["id", "seq"], ["rep", [["seq", [["dq", "\" / \""], ["id", "seq"]]], ["sfx", "*"]]]]]]], ["rule", [["id", "seq"], ["seq", [["id", "rep"], ["rep", [["seq", [["sq", "' '"], ["id", "rep"]]], ["sfx", "*"]]]]]]], ["rule", [["id", "rep"], ["seq", [["id", "pre"], ["rep", [["id", "sfx"], ["sfx", "?"]]]]]]], ["rule", [["id", "pre"], ["seq", [["rep", [["id", "pfx"], ["sfx", "?"]]], ["id", "term"]]]]], ["rule", [["id", "term"], ["alt", [["id", "id"], ["id", "sq"], ["id", "dq"], ["id", "chs"], ["id", "group"]]]]], ["rule", [["id", "id"], ["rep", [["chs", "[a-zA-Z]"], ["sfx", "+"]]]]], ["rule", [["id", "pfx"], ["chs", "[&!~]"]]], ["rule", [["id", "sfx"], ["chs", "[+?*]"]]], ["rule", [["id", "sq"], ["seq", [["dq", "\"'\""], ["rep", [["pre", [["pfx", "~"], ["dq", "\"'\""]]], ["sfx", "*"]]], ["dq", "\"'\""]]]]], ["rule", [["id", "dq"], ["seq", [["sq", "'\"'"], ["rep", [["pre", [["pfx", "~"], ["sq", "'\"'"]]], ["sfx", "*"]]], ["sq", "'\"'"]]]]], ["rule", [["id", "chs"], ["seq", [["sq", "'['"], ["rep", [["pre", [["pfx", "~"], ["sq", "']'"]]], ["sfx", "*"]]], ["sq", "']'"]]]]], ["rule", [["id", "group"], ["seq", [["dq", "\"( \""], ["id", "alt"], ["dq", "\" )\""]]]]]]]]]
"""

"""  Impementation Notes:

Adds pre, and uses pPEG boot grammar instead of simple date grammar.

fix id for uppercase and anon underscore rule names (the TODO form step 2)

The core parser machine (direct ptree interpreter) is now complete.

add trace rule call line report

TODO: fault err report for parse failure

"""
