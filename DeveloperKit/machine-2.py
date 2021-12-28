
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
            "sq": sq
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

    def sq(exp):
        nonlocal pos
        for c in exp[1][1:-1]:
            if pos >= end or c != input[pos]: return False
            pos += 1
        return True

    result = eval(code["$start"])
    return (result, pos, tree)

print( parse(date_code, "2021-03-04") ) # eval exp ...

"""  Impementation Notes:

Add parse tree building in id rule.

Add reset tree in alt

TODO: upper case rule names and anon underscore rule names.

"""
