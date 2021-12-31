    
import pPEG  # >export PYTHONPATH=.../pPEGpy/

pPEG_grammar = """
    Peg   = " " (rule " ")+
    rule  = id " = " alt

    alt   = seq (" / " seq)*
    seq   = rep (" " rep)*
    rep   = pre sfx?
    pre   = pfx? term
    term  = call / sq / dq / chs / group / extn

    id    = [a-zA-Z_] [a-zA-Z0-9_]*
    pfx   = [&!~]
    sfx   = [+?] / '*' range?
    range = num (dots num?)?
    num   = [0-9]+
    dots  = '..'

    call  = id !" ="
    sq    = "'" ~"'"* "'" 'i'?
    dq    = '"' ~'"'* '"' 'i'?
    chs   = '[' ~']'* ']'
    group = "( " alt " )"
    extn  = '<' ~'>'* '>'

    _space_ = ('#' ~[\n\r]* / [ \t\n\r]+)*
"""

def pPEG_test():
    peg = pPEG.compile(pPEG_grammar)

def date_test():
    date = pPEG.compile("""
    date  = year '-' month '-' day
    year  = [0-9]+
    month = [0-9]+
    day   = [0-9]+
    """)

quote = pPEG.compile("""
    q = '"' ~["]* '"'
""")
# print( quote.parse('"1234567890123456789012345678901234567890"') )

def quote_test():
    p = quote.parse('"01234567890123456789012345678901234567890123456789"')

import timeit
tests =  [["pPEG_test()", 1000], ["date_test()", 10000], ["quote_test()", 100000]] 
for t in tests:
    print(t[0]+" x"+str(t[1]))
    print(timeit.timeit(t[0], number=t[1], globals=locals()))

"""

on iMac M1 2021 

pPEG_test() x1000     1.52 ms
1.528595957905054
date_test() x10000    0.21  ms  
2.1664990838617086
quote_test() x100000  12 us
1.2145623341202736

"""
