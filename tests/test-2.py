from pPEGpy import peg

# NOTE: These examples have not yet been updates....


def fx(exp, env):
    print("fx", exp[1])
    return True


g2 = peg.compile(
    """
    s = 'a' <x> 'b'
    """,
    {"x": fx},
)

p2 = g2.parse("ab")

print(p2)

g3 = peg.compile("""
    expr  = var (op var)* <infix>
    op    = " " (op_1L / op_AL / op_aR) " "
    var   = [a-zA-Z0-9]+
    op_1L = [-+]
    op_AL = [*/]
    op_aR = '^'
""")

p3 = g3.parse("1+2*3")

print(p3)
