# import pPEGpy as peg  # local file
from pPEGpy import peg  # pip install pPEGpy

print("Arith operator expression example....")

arith = peg.compile("""
  exp = add 
  add = sub ('+' sub)*
  sub = mul ('-' mul)*
  mul = div ('*' div)*
  div = pow ('/' pow)*
  pow = val ('^' val)*
  grp = '(' exp ')'
  val = _ (sym / num / grp) _
  sym = [a-zA-Z]+
  num = [0-9]+
  _   = [ \t\n\r]*
""")

tests = [" 1 + 2 * 3 ", "x^2^3 - 1"]
for test in tests:
    p = arith.parse(test)
    print(p)

# add
# │ num '1'
# │ mul
# │ │ num '2'
# │ │ num '3'

# sub
# │ pow
# │ │ sym 'x'
# │ │ num '2'
# │ │ num '3'
# │ num '1'

# 1+2*3 ==> (+ 1 (* 2 3))
# ["add",[["num","1"],["mul",[["num","2"],["num","3"]]]]]

# x^2^3+1 ==> (+ (^ x 2 3) 1)
# ["add",[["pow",[["sym","x"],["num","2"],["num","3"]]],["num","1"]]]


# -- transform examples ----------------------------------------------

def prod(ns): # product of list
    x = 1
    for n in ns:
        x *= n
    return x

# -- grammar ---------------------

arith = peg.compile(
    """
    sum  = prod ('+' prod)*
    prod = int ('*' int)*
    int  = [0-9]+
    """,
    transforms={"int": int, "sum": sum, "prod": prod},
)

expr = "1+2*3"

# p = arith.parse(expr)
# print(p)
# p.print_trace()

ok, num = arith.read(expr)
print(f"{expr} = {num}")


# -- transform ----------------------

ops = {
    "+": lambda x, y: x + y,
    "-": lambda x, y: x - y,
    "*": lambda x, y: x * y,
    "**": lambda x, y: x ** y,
    "/": lambda x, y: x / y,
    "//": lambda x, y: x // y,
}

# left reduce: (a op b op c op d)
#          ==> (((a op b) op c) op d)
#          ==> (op (op (op a b) c) d)

def xfy(exp):
    x = exp[0]
    i = 1
    while i < len(exp):
        fn = ops.get(exp[i])
        if not fn:
            raise Exception(f"Undefined op {exp[i]}")
        x = fn(x, exp[i + 1])
        i += 2
    return x

# right reduce: (a op b op c op d)
#          ==> (((a op b) op c) op d)
#          ==> (op (op (op a b) c) d)
    
def yfx(exp):
    x = exp[-1]
    i = len(exp)-2
    while i > 0:
        fn = ops.get(exp[i])
        if not fn:
            raise Exception(f"Undefined op {exp[i]}")
        x = fn(exp[i - 1], x)
        i -= 2
    return x

# -- grammar ----------------------

arith = peg.compile(
    """
    sum  = prod (add prod)*
    prod = pow (mul pow)*
    pow  = int (exp int)*
    int  = [0-9]+
    add  = [+-]
    mul  = '//' / [*/]
    exp  = '**'
    """,
    transforms=dict(
        sum=xfy, prod=xfy, pow=yfx,
        int=int, add=str, mul=str, exp=str
    )
)

expr = "1+2**3**2//2"

ok, x = arith.read(expr)

print(f"{expr} = {x}")

