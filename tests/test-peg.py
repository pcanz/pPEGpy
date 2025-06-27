# from pPEGpy import peg
import pPEGpy as peg

# == grammar testing =============================

tests = [
    [""" # 0: check numeric repeat...
    s = x*3
    x = [a-z]
    """,[
    ('abc', ['s',[['x','a'],['x','b'],['x','c']]]),
    ('ab', [])
    ]],
    [""" # 1: check numeric repeat closed range...
    s = x*3..5
    x = [a-z]
    """,[
    ('abc', ['s',[['x','a'],['x','b'],['x','c']]]),
    ('abcd', ['s',[['x','a'],['x','b'],['x','c'],['x','d']]]),
    ('abcde', ['s',[['x','a'],['x','b'],['x','c'],['x','d'],['x','e']]]),
    ('ab', []),
    ('abcdef', []),
    ]],
    [""" # 2: check numeric repeat open range...
    s = x*2..
    x = [a-z]
    """,[
    ('ab', ['s',[['x','a'],['x','b']]]),
    ('abc', ['s',[['x','a'],['x','b'],['x','c']]]),
    ('abcdefg', ['s',[['x','a'],['x','b'],['x','c'],['x','d'],['x','e'],['x','f'],['x','g']]]),
    ('a', []),
    ]],
    [""" # 3: check * any and ? optional ...
    s = x* '|' y?
    x = [a-z]+
    y = [a-z]+
    """,[
    ('abc|def', ['s',[['x','abc'],['y','def']]]),
    ('|', ['s','|']),
    ]],
    [""" # 4: check empty alternatives ...
    s = x* / y? / z
    x = [0-9]+
    y = [a-z]+
    z = [A-Z]*
    """,[
    ('123', ['x','123']),
    ('abc', []),
    ('ABC', []),
    ('1aB', []),
    ('', ['s', '']),
    ]],
    [""" # 5: check fall back nodes have been marked as failed ...
    s = t x*
    t = (x x)*
    x = [a-z]
    """,[
    ('a', ['s',[['t',''],['x','a']]]),
    ('ab', ['t',[['x','a'],['x','b']]]),
    ('abc', ['s',[['t',[['x','a'],['x','b']]],['x','c']]]),
    ('abcd', ['t',[['x','a'],['x','b'],['x','c'],['x','d']]]),
    ]],
    [""" # 6: check rule types, elide redundant...
    s = x? y
    x = 'x'+
    y = 'y'*
    """,[
    ('xy', ['s',[['x','x'],['y','y']]]),
    ('yy', ['y','yy']),
    ]],
    [""" # 7: check rule types, Cap rule...
    S = x? y
    x = 'x'+
    y = 'y'*
    """,[
    ('xy', ['S',[['x','x'],['y','y']]]),
    ('yy', ['S',[['y','yy']]]),
    ]],
    [""" # 8: check rule types, := rule...
    s := x? y
    x = 'x'+
    y = 'y'*
    """,[
    ('xy', ['s',[['x','x'],['y','y']]]),
    ('yy', ['s',[['y','yy']]]),
    ]],
    [""" # 9: check !x fall back...
    s = !x y / z
    x = 'x' 'y'
    y = .*
    z = .*
    """,[
    ('xy', ['z','xy']),
    ('yy', ['y','yy']),
    ('', ['y','']),
    ('x', ['y','x']),
    ]],
    [""" # 10: check ~x fall back...
    s = ~x / y
    x = 'x'
    y = .*
    """,[
    ('xy', ['y','xy']),
    ('y', ['s','y']),
    ('', ['y','']),
    ]],
    [""" # 11: check empty end ...
    s = .*
    """,[
    ('xy', ['s','xy']),
    ('', ['s','']),
    ]]
]  # fmt:skip

# == test runner =============================================


def run_tests():
    ok = 0
    fail = 0
    for t, test in enumerate(tests):
        grammar, examples = test
        code = peg.compile(grammar)
        if not code.ok:
            fail += 1
            print(f"*** grammar failed: {grammar}\n{code}")
            continue
        for e, example in enumerate(examples):
            input, tree = example
            p = code.parse(input)
            if p.ok:
                if verify(t, e, p.tree(), tree):
                    ok += 1
                else:
                    fail += 1
            else:  # parse failed...
                # if tree == []:
                if verify(t, e, [], tree):
                    ok += 1
                else:
                    fail += 1
                    # print(f"*** test failed: {grammar}{input}")
    if fail == 0:
        print(f"OK passed all {ok} tests.")
    else:
        print(f"*** Failed {fail} of {ok + fail} tests.")


def verify(t, e, t1, t2):
    if t1 == t2:
        return True
    print(f"*** test {t} failed example {e}:")
    print(f"expected: {t2}")
    print(f".....saw: {t1}")
    return False


# == run tests ==================================================================

print("Running tests...")
run_tests()
