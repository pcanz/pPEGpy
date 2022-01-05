import pPEG

g1 = pPEG.compile("""
    Date  = year '-' month '-' day
    year  = [0-9]*4
    month = [0-9]*2 
    day   = [0-9]*2
""")

p1 = g1.parse("2022-01-04")

print(p1)

def fx(exp, env):
    print("fx", exp[1])
    return True

g2 = pPEG.compile("""
    s = 'a' <x> 'b'
""",
{'x': fx})

p2 = g2.parse("ab")

print(p2)

g3 = pPEG.compile("""
    expr  = var (op var)* <infix>
    op    = " " (op_1L / op_AL / op_aR) " "
    var   = [a-zA-Z0-9]+
    op_1L = [-+]
    op_AL = [*/]
    op_aR = '^'
""")

p3 = g3.parse("1+2*3")

print(p3)

