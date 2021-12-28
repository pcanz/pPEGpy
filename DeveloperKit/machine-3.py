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

def parse(code, input):
    pos = 0
    end = len(input)
    tree = [] # build parse tree

    def eval(exp):
        print(exp, exp[0])
        instruct = {
            "id": id,
            "seq": seq,
            "alt": alt,
            "rep": rep,
            "sq": sq,
            "dq": dq,
            "chs": chs
        }
        return instruct[exp[0]](exp)

    def id(exp):
        nonlocal tree
        start = pos
        stack = len(tree)
        name = exp[1]
        expr = code[name]
        result = eval(expr)
        if not result: return False
        size = len(tree)
        if size-stack > 1:
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

    result = eval(code["$start"])
    return (result, pos, tree)

print( parse(date_code, "2021-03-04") ) # eval exp ...

"""  Impementation Notes:

Adds rep, dq, and chs instructions

"""