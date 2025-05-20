from pPEGpy import peg

# -- example shown in main pPEG README.md -------------------------

sexp = peg.compile("""
    sexp  = _ list _
    list  = '(' _ elem* ')' _
    elem  = list / atom
    atom  = ~[() \t\n\r]+ _
    _     = [ \t\n\r]*
""")

test = """
    (foo bar (blat 42) (f(g(x))))
"""

p = sexp.parse(test)

print(p)

"""
list
│ atom 'foo '
│ atom 'bar '
│ list
│ │ atom 'blat '
│ │ atom '42'
│ list
│ │ atom 'f'
│ │ list
│ │ │ atom 'g'
│ │ │ atom 'x'
"""

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

pURI = peg.compile("""
    URI     = (scheme ':')? ('//' auth)? path ('?' query)? ('#' frag)?
    scheme  = ~[:/?#]+
    auth    = ~[/?#]*
    path    = ~[?#]*
    query   = ~'#'*
    frag    = ~[ \t\n\r]*
""")

test = "http://www.ics.uci.edu/pub/ietf/uri/#Related"
uri = pURI.parse(test)

print(uri)

"""
URI
│ scheme 'http'
│ auth 'www.ics.uci.edu'
│ path '/pub/ietf/uri/'
│ frag 'Related'
"""

"""
["URI",[["scheme","http"],["auth","www.ics.uci.edu"],["path","/pub/ietf/uri/"],["frag","Related"]]]
"""

# -- try numerical range repeat feature and comments ------------------

print("....")

date = peg.compile("""
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

icase = peg.compile("""
    s = 'AbC'i
""")

print(icase.parse("aBC"))

print("....")
# -- check string escapes (so that grammars can be raw strings) --------

icase = peg.compile(r"""
    s = 'a\tb\nc\td'
""")

print(icase.parse("""a\tb\nc\td"""))

print("....")

"""
list
│ atom 'foo '
│ atom 'bar '
│ list
│ │ atom 'blat '
│ │ atom '42'
│ list
│ │ atom 'f'
│ │ list
│ │ │ atom 'g'
│ │ │ atom 'x'
....
URI
│ scheme 'http'
│ auth 'www.ics.uci.edu'
│ path '/pub/ietf/uri/'
│ frag 'Related'
....
date
│ year '2012'
│ month '04'
│ day '05'
date
│ year '2012'
│ month '4'
│ day '5'
*** parse failed at: 4 of: 13  ... for more details use: parse.dump() ...
line 1 | 201234-04-056
             ^ date failed
date  = year '-' month '-' day

*** parse failed at: 12 of: 13  ... for more details use: parse.dump() ...
line 1 | 2012-0456-056
                     ^ day failed
day   = [0-9]*1..2
    # last comment.

....
s 'aBC'
....
s 'a\tb\nc\td'
....
"""
