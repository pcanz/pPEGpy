# import pPEGpy as peg  # local file
from pPEGpy import peg  # pip install pPEGpy

import extras

extensions = extras.extensions()

p = peg.compile(
    """
    p  = x1 m <same x1> / x?
    m  = (x &x)*
    x1 = x
    x  : [a-z]
    """,
    same=extras.same,
    # **extensions
)

t = p.parse("abba")

t.dump()

print(t)

print("=====================")

p = peg.compile(
    """
    p  = x1 m x2 / x1?
    m  = (x &x)*
    x1 = x
    x2 = <same x1>
    x  : [a-z]
    """,
    same=extras.same,
)

t = p.parse("abba")

t.dump()

print(t)

print("=====================")

code = peg.compile(
    """
    p  = x1 m x2 <eq x2 x1>
    m  = (x &x)*  # <match m p>
    x1 = x
    x2 = x
    x  : [a-z]
""",
    eq=extras.eq,
)

p = code.parse("racecar")  # "abba")  #
p.dump(0)
print(p)

print("=====================")

code = peg.compile(
    """
    Code = t1 code t1
    code = ~(t2 <eq t1 t2>)*
    t1   = '`'+
    t2   = '`'+
    """,
    **extensions,
)

p = code.parse(R"```a``y``z```", debug=1)
# p.dump(0)
print(p)


print("=====================")

pal = peg.compile(
    """
    p  = x1 m x2 / x1?
    m  = (x &x)*  #  m => p 
    x1 = x
    x2 = <same x1>
    x  : [a-z]
    """,
    same=extras.same,
)


def palindrome(s):
    t = pal.parse(s)
    return t.transform(m=palindrome)


x = palindrome("racecar")

print(x)
