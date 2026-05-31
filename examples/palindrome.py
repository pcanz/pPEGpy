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
    extras = {'same': extras.same}
)

t = p.parse("abba")

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
    extras = {'same': extras.same}
)

t = p.parse("abba")

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
    extras = {'eq': extras.eq}
)

p = code.parse("racecar")  # "abba")  #
print(p)

print("=====================")

code = peg.compile(
    """
    Code = t1 code t1
    code = ~(t2 <eq t1 t2>)*
    t1   = '`'+
    t2   = '`'+
    """,
    extras = {'eq': extras.eq}
)

p = code.parse(R"```a``y``z```")
print(p)


print("=====================")

def palindrome(s):
    ok,  = pal.read(s)
    return t.transform(m=palindrome)


pal = peg.compile(
    """
    p  = x1 m x2 / x1?
    m  = (x &x)* <is p> 
    x1 = x
    x2 = <same x1>
    x  : [a-z]
    """,
    transforms = {'m': palindrome}
    extras = {'same': extras.same}
)

x = palindrome("racecar")

print(x)
