import pPEG  # > export PYTHONPATH=mypath.../pPEGpy/

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

date = pPEG.compile("""
# check comments are working...
    date  = year '-' month '-' day
    year  = [0-9]*4
    month = [0-9]*1.. # more comments...
    day   = [0-9]*1..2
    # last comment.
""")

print( date.parse("2012-04-05") )
print( date.parse("2012-4-5") )

print( date.parse("201234-04-056") )

print( date.parse("2012-0456-056") )

icase = pPEG.compile("""
    s = "AbC"i
""")

print( icase.parse("aBC") )

print("....")
