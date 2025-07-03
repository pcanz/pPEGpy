# import pPEGpy as peg  # local file
from pPEGpy import peg  # pip install pPEGpy

arith = peg.compile("""
add = num ('+' num)*
num = [0-9]+
""")

p = arith.parse("123+456+789")

print(p)

print(f"p.ptree() =>\n{p.ptree()}")

# -- basic value transform -----

x = p.transform(num=int)

print(f"p.transform(num=int) => \n{x}")

# -- s-expression transform ------


def add_expr(args):
    return ("+", *args)


x = p.transform(add=add_expr, num=int)

print(f"p.transform(add=add_expr, num=int) => \n{x}")

# -- evaluate --------------------

x = p.transform(add=sum, num=int)

print(f"p.transform(add=sum, num=int) => \n{x}")


# -- evaluate using trans --------------------


def p_int(p, i, v):
    return int(v)
    # return int(p.text(i)), i + 1


def p_sum(p, i, v):
    return sum(v)


x = p.transform(add=p_sum, num=p_int)

print(f"p.transform(add=p_sum, num=p_int) => \n{x}")
