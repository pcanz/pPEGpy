from pPEGpy import peg  # pip install pPEGpy
# import pPEGpy as peg  # for Parse, Code, run


# == unit tests for run function =============================================


def test_run(expr, input, end, expect=True):
    test_ptree = ["peg", [["rule", [["id", "s"], expr]]]]
    code = peg.Code(None, __boot__=test_ptree)  # boot_compile(test_ptree)
    if code.err:
        print(f"*** test failed to compile: {test_ptree}\n{code.err}")
        return
    parse = peg.Parse(code, input)
    result = peg.run(parse, ["id", 0])  # , EQ])
    failed = (expect and not result) or (not expect and result)
    if failed or parse.pos != end:
        print(f'*** test failed: {expr} "{input}" pos: {parse.pos} expected: {end}')


# -- test instruction basics and corner cases ---------------


def run_code_tests():
    test_run(["quote", "''"], "x", 0)
    test_run(["quote", "''"], "", 0)
    test_run(["quote", "'x'"], "", 0, False)
    test_run(["quote", "'x'"], "x", 1)
    test_run(["quote", "'x'"], "xyz", 1)
    test_run(["quote", "'xyz'"], "xyz", 3)
    test_run(["quote", "'xyz'"], "xkz", 1, False)

    test_run(["class", "[]"], "x", 0, False)
    test_run(["class", "[]"], "", 0, False)
    test_run(["class", "[x]"], "x", 1)
    test_run(["class", "[x]"], "z", 0, False)
    test_run(["class", "[xy]"], "x", 1)
    test_run(["class", "[xy]"], "y", 1)
    test_run(["class", "[xy]"], "z", 0, False)

    test_run(["seq", [["quote", "'x'"], ["quote", "'y'"]]], "xy", 2)
    test_run(["seq", [["quote", "'x'"], ["quote", "'y'"]]], "", 0, False)
    test_run(["seq", [["quote", "'x'"], ["quote", "'y'"]]], "k", 0, False)
    test_run(["seq", [["quote", "'x'"], ["quote", "'y'"]]], "xk", 1, False)
    test_run(["seq", [["quote", "'x'"], ["quote", "'y'"]]], "xyz", 2)

    test_run(["alt", [["quote", "'x'"], ["quote", "'y'"]]], "x", 1)
    test_run(["alt", [["quote", "'x'"], ["quote", "'y'"]]], "yz", 1)
    test_run(["alt", [["quote", "'x'"], ["quote", "'y'"]]], "", 0, False)
    test_run(["alt", [["quote", "'x'"], ["quote", "'y'"]]], "k", 0, False)
    test_run(["alt", [["quote", "''"], ["quote", "'y'"]]], "y", 0)

    test_run(["rep", [["quote", "'x'"], ["sfx", "*"]]], "xxx", 3)
    test_run(["rep", [["quote", "'x'"], ["sfx", "*"]]], "", 0)
    test_run(["rep", [["quote", "'x'"], ["sfx", "+"]]], "", 0, False)
    test_run(["rep", [["quote", "'x'"], ["sfx", "+"]]], "x", 1)
    test_run(["rep", [["quote", "'x'"], ["sfx", "?"]]], "x", 1)
    test_run(["rep", [["quote", "'x'"], ["sfx", "?"]]], "k", 0)
    test_run(["rep", [["quote", "'x'"], ["sfx", "?"]]], "xxx", 1)
    test_run(["rep", [["quote", "''"], ["sfx", "*"]]], "xxx", 0)

    test_run(["pre", [["pfx", "!"], ["quote", "'x'"]]], "y", 0)
    test_run(["pre", [["pfx", "!"], ["quote", "'x'"]]], "x", 0, False)
    test_run(["pre", [["pfx", "&"], ["quote", "'x'"]]], "x", 0)
    test_run(["pre", [["pfx", "&"], ["quote", "'x'"]]], "y", 0, False)

    test_run(["pre", [["pfx", "~"], ["quote", "'x'"]]], "x", 0, False)
    test_run(["pre", [["pfx", "~"], ["quote", "'x'"]]], "y", 1)
    test_run(["pre", [["pfx", "~"], ["quote", "'xyz'"]]], "xyz", 0, False)
    test_run(["pre", [["pfx", "~"], ["quote", "'xyz'"]]], "pqr", 1)


# == run test ==================================================================

print("Running tests...")
run_code_tests()  # parser machine tests, run before bootstrap
print("... tests done.")
