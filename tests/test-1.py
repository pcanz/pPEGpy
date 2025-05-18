# import pPEG  #  needs an env var > export PYTHONPATH=..../pPEGpy/

# from pPEGpy import pPEG  # needs a pip package

import sys  # use this hack to import the pPEG.py file module...

sys.path.insert(1, ".")  # import from current working directory
import pPEG


# -- example shown in main pPEG README.md -------------------------

sexp = pPEG.compile("""
    list  = " ( " elem* " ) "
    elem  = list / atom " "
    atom  = ~[() \t\n\r]+
""")

test = """
    (foo bar (blat 42) (f(g(x))))
"""

p = sexp.parse(test)

print(p)

"""
["list",[["atom","foo"],["atom","bar"],
    ["list",[["atom","blat"],["atom","42"]]],
    ["list",[["atom","f"],
        ["list",[["atom","g"],["atom","x"]]]]]]]
"""

# -- example shown in the PEGpy README.md -----------------------------------------------

print("....")

# import pPEG

# Equivalent to the regular expression for well-formed URI's in RFC 3986.

pURI = pPEG.compile("""
    URI     = (scheme ':')? ('//' auth)? path ('?' query)? ('#' frag)?
    scheme  = ~[:/?#]+
    auth    = ~[/?#]*
    path    = ~[?#]*
    query   = ~'#'*
    frag    = ~[ \t\n\r]*
""")

if not pURI.ok:
    print(pURI)  # raise Exception("URI grammar error: "+pURI.err)

test = "http://www.ics.uci.edu/pub/ietf/uri/#Related"
uri = pURI.parse(test)

if uri.ok:
    print(uri.ptree)
else:
    print(uri.err)

"""
["URI",[["scheme","http"],["auth","www.ics.uci.edu"],["path","/pub/ietf/uri/"],["frag","Related"]]]
"""

# -- try numerical range repeat feature and comments ------------------

print("....")

date = pPEG.compile("""
# check comments are working...
    date  = year '-' month '-' day
    year  = [0-9]*4
    month = [0-9]*1.. # more comments...
    day   = [0-9]*1..2
    # last comment.
""")


print(date.parse("2012-04-05"))  # ok
print(date.parse("2012-4-5"))  # ok

print(date.parse("201234-04-056"))  # *4 year '-' fails

print(date.parse("2012-0456-056"))  # month *1.. ok, day fails

print("....")

# -- try case insensitve strings -------------------------------------

icase = pPEG.compile("""
    s = "AbC"i
""")

print(icase.parse("aBC"))

print("....")

# -- check string escapes (so that grammars can be raw strings) --------

icase = pPEG.compile(r"""
    s = "a\tb\nc\td"
""")

print(icase.parse("""a\tb\nc\td"""))

print("....")
