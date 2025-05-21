from pPEGpy import peg

"""
This Python version of a pPEG parser is a simple interpreter, it is not optimized
in any way.

But this new version does use a flat array of integers for the internal parse tree,
which should be a very efficient in a system programming language.
"""

peg_grammar = R"""
Peg   = _ rule+
rule  = id _ def _ alt
def   = [:=]+
alt   = seq ('/' _ seq)*
seq   = rep+
rep   = pre sfx? _
pre   = pfx? term
term  = call / quote / class / dot / group / extn
group = '(' _ alt ')'
call  = id _ !def
id    = [a-zA-Z_] [a-zA-Z0-9_]*
pfx   = [~!&]
sfx   = [+?] / '*' nums?
nums  = min ('..' max)?
min   = [0-9]+
max   = [0-9]*
quote = ['] ~[']* ['] 'i'?
class = '[' ~']'* ']'
dot   = '.'_
extn  = '<' ~'>'* '>'
_     = ([ \t\n\r]+ / '#' ~[\n\r]*)*
"""

# Previous version....
#
# pPEG_grammar = """
#     Peg   = _ rule+
#     rule  = id _'='_ alt

#     alt   = seq ('/'_ seq)*
#     seq   = rep (' ' rep)* _
#     rep   = pre sfx?
#     pre   = pfx? term
#     term  = call / quote / class / group / extn

#     id    = [a-zA-Z_] [a-zA-Z0-9_]*
#     pfx   = [&!~]
#     sfx   = [+?] / '*' range?
#     range = num (dots num?)?
#     num   = [0-9]+
#     dots  = '..'

#     call  = id !" ="
#     sq    = "'" ~"'"* "'" 'i'?
#     dq    = '"' ~'"'* '"' 'i'?
#     chs   = '[' ~']'* ']'
#     group = "( " alt " )"
#     extn  = '<' ~'>'* '>'

#     _space_ = ('#' ~[\n\r]* / [ \t\n\r]+)*
# """


def peg_test():
    return peg.compile(peg_grammar)


def date_test():
    return peg.compile("""
    date  = year '-' month '-' day
    year  = [0-9]+
    month = [0-9]+
    day   = [0-9]+
    """)


quote = peg.compile("""
    q = '"' ~["]* '"'
""")
# print( quote.parse('"1234567890123456789012345678901234567890"') )


def quote_test():
    return quote.parse('"01234567890123456789012345678901234567890123456789"')


import timeit

tests = [["peg_test()", 1000], ["date_test()", 10000], ["quote_test()", 100000]]
for t in tests:
    print(t[0] + " x" + str(t[1]))
    print(timeit.timeit(t[0], number=t[1], globals=locals()))


"""
on MacBook air 2025 -- with array parse tree

peg_test() x1000    ~ 1.3 ms
1.2992404999677092
date_test() x10000  ~ 1.8 ms
1.8291782920714468
quote_test() x100000 ~ 1.6 us, 50 chars, ~30 ns/char ~30 MB/s
1.6071688750525936
"""

"""
on iMac M1 2021  -- original parse tree

pPEG_test() x1000     1.52 ms
1.528595957905054
date_test() x10000    0.21  ms  
2.1664990838617086
quote_test() x100000  12 us
1.2145623341202736

"""
