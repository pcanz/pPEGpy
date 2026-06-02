# import pPEGpy as peg  # local file
from pPEGpy import peg  # pip install pPEGpy

import extras

extensions = extras.extensions()

print("=====================")

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

print("=== Markdown code ==================")

p = peg.compile(
    """
    markup = ticks code ticks
    code   = ~<same ticks>*
    ticks  = '`'+
    """,
    extras = {'same': extras.same}
)

t = p.parse("```x``xx```")

print(t)


print("=== Rust raw code ==================")

p = peg.compile(
    """
    raw   = 'r' marks '"' text '"' marks
    text  = ~('"' <same marks>)*
    marks = '#'*
    """,
    extras = {'same': extras.same}
)

t = p.parse("""r##"xx #"x"# xx"##""")

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
    m  = (x &x)*
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


print("== middle finder ===================")

middle = peg.compile(
    """
    middle = x inner x / x
    inner  = (. &.)* <match middle>
    x      = [a-z]
    """,
    extras = {'match': extras.match}
)

p = middle.parse("abcdcba")
print(p)

print("== palindrome using transform ===================")

def palindrome(pal, s):
    ok, _ = pal.read(s)
    if not ok:
        raise Exception(f"{s} is not a palindrome")
    return s

pal = peg.compile(
    """
    p  = x px x / x
    px = (. &.)*
    x  = [a-z]
    """,
    transforms = {'px': lambda s: palindrome(pal, s)},
    extras = {'same': extras.same}
)

x = palindrome(pal, "racecar")

print(x)


print("== Better version using <match rule> ==================")


pal = peg.compile(
    """
    p  = x px z / x
    px = (. &.)* <match p>
    z  = <same x>
    x  = [a-z]
    """,
    extras = {'same': extras.same, 'match':extras.match}
)

p = pal.parse("racecar")

print(p)

