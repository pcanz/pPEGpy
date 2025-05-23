from pPEGpy import peg

# == grammar testing =============================

tests = [
    [""" # check numeric repeat...
    s = x*3
    x = [a-z]
    """,[
    ('abc', ['s',[['x','a'],['x','b'],['x','c']]]),
    ('ab', [])
    ]],
    [""" # check numeric repeat closed range...
    s = x*3..5
    x = [a-z]
    """,[
    ('abc', ['s',[['x','a'],['x','b'],['x','c']]]),
    ('abcd', ['s',[['x','a'],['x','b'],['x','c'],['x','d']]]),
    ('abcde', ['s',[['x','a'],['x','b'],['x','c'],['x','d'],['x','e']]]),
    ('ab', []),
    ('abcdef', []),
    ]],
    [""" # check numeric repeat open range...
    s = x*2..
    x = [a-z]
    """,[
    ('ab', ['s',[['x','a'],['x','b']]]),
    ('abc', ['s',[['x','a'],['x','b'],['x','c']]]),
    ('abcdefg', ['s',[['x','a'],['x','b'],['x','c'],['x','d'],['x','e'],['x','f'],['x','g']]]),
    ('a', []),
    ]],
    [""" # check roll back nodes have been marked as failed ...
    s = t x*
    t = (x x)*
    x = [a-z]
    """,[
    ('a', ['s',[['t',''],['x','a']]]),
    ('abc', ['s',[['t',[['x','a'],['x','b']]],['x','c']]]),
    ('abcd', ['t',[['x','a'],['x','b'],['x','c'],['x','d']]]),
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
                if tree == []:
                    ok += 1
                else:
                    fail += 1
                    print(f"*** test failed: {grammar}{input}")
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
