from pPEGpy import peg  # Parse, Code, run

# == low level parser machine op code tests =============================

# -- test instruction basics and corner cases ---------------


tests = [
  (["quote", "''"], "x", 0)
, (["quote", "''"], "", 0)
, (["quote", "'x'"], "", 0, False)
, (["quote", "'x'"], "x", 1)
, (["quote", "'x'"], "xyz", 1)
, (["quote", "'xyz'"], "xyz", 3)
, (["quote", "'xyz'"], "xk", 1, False)
 
, (["class", "[]"], "x", 0, False)
, (["class", "[]"], "", 0, False)
, (["class", "[x]"], "x", 1)
, (["class", "[x]"], "z", 0, False)
, (["class", "[xy]"], "x", 1)
, (["class", "[xy]"], "y", 1)

, (["seq", [["quote", "'x'"], ["quote", "'y'"]]], "xy", 2)
, (["seq", [["quote", "'x'"], ["quote", "'y'"]]], "", 0, False)
, (["seq", [["quote", "'x'"], ["quote", "'y'"]]], "k", 0, False)
, (["seq", [["quote", "'x'"], ["quote", "'y'"]]], "xk", 1, False)
 
, (["alt", [["quote", "'x'"], ["quote", "'y'"]]], "x", 1)
, (["alt", [["quote", "'x'"], ["quote", "'y'"]]], "yz", 1)
, (["alt", [["quote", "'x'"], ["quote", "'y'"]]], "", 0, False)
, (["alt", [["quote", "'x'"], ["quote", "'y'"]]], "k", 0, False)
, (["alt", [["quote", "''"], ["quote", "'y'"]]], "y", 1,)  # if alt fails an empty match

, (["rep", [["quote", "'x'"], ["sfx", "*"]]], "xxx", 3)
, (["rep", [["quote", "'x'"], ["sfx", "*"]]], "", 0)
, (["rep", [["quote", "'x'"], ["sfx", "+"]]], "", 0, False)
, (["rep", [["quote", "'x'"], ["sfx", "+"]]], "x", 1)
, (["rep", [["quote", "'x'"], ["sfx", "?"]]], "x", 1)
, (["rep", [["quote", "'x'"], ["sfx", "?"]]], "k", 0)
, (["rep", [["quote", "'x'"], ["sfx", "?"]]], "xxx", 1)
, (["rep", [["quote", "''"], ["sfx", "*"]]], "xxx", 0)  # check for no-progress loop break

, (["pre", [["pfx", "!"], ["quote", "'x'"]]], "y", 0)
, (["pre", [["pfx", "!"], ["quote", "'x'"]]], "x", 0, False)
, (["pre", [["pfx", "&"], ["quote", "'x'"]]], "x", 0)
, (["pre", [["pfx", "&"], ["quote", "'x'"]]], "y", 0, False)
, (["pre", [["pfx", "~"], ["quote", "'x'"]]], "x", 0, False)
, (["pre", [["pfx", "~"], ["quote", "'x'"]]], "y", 1)
, (["pre", [["pfx", "~"], ["quote", "'xyz'"]]], "xyz", 0, False)
, (["pre", [["pfx", "~"], ["quote", "'xyz'"]]], "pqr", 1)

]  # fmt:skip

# == test runner =============================================


def run_tests():
    ok = 0
    fail = 0
    for test in tests:
        if test_run(*test):
            ok += 1
        else:
            fail += 1
    if fail == 0:
        print(f"OK passed all {ok} tests.")
    else:
        print(f"*** Failed {fail} of {ok + fail} tests.")


def test_run(expr, input, end, expect=True):
    test_ptree = ["peg", [["rule", [["id", "s"], expr]]]]
    code = peg.Code(None, {}, test_ptree)  # boot_compile(test_ptree)
    if code.err:
        print(f"*** test failed to compile: {test_ptree}\n{code.err}")
        return False
    parse = peg.Parse(code, input)
    result = peg.run(parse, ["id", 0])
    failed = (expect and not result) or (not expect and result)
    if failed or parse.pos != end:
        print(f'*** test failed: {expr} "{input}" pos: {parse.pos} expected: {end}')
        return False
    return True


# == run tests ==================================================================

print("Running tests...")
run_tests()
