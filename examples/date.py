from pPEGpy import peg
# import pPEGpy as peg

print("First a simple date grammar -------------------------------------\n")
print("-  rules only uses sequence, or choice, with quoted literal match")

date_grammar = """
    Date  = year '-' month '-' day
    year  = d d d d
    month = d d 
    day   = d d
    d     = '0'/'1'/'2'/'3'/'4'/'5'/'6'/'7'/'8'/'9'
"""
print(date_grammar)

date = peg.compile(date_grammar)
p = date.parse("2021-04-05")
print(p)

print("\nTwo small changes to the digit d rule ----------------------------\n")
print("-  now uses the shorthand [0-9] for the choice of digit")
print("-  define the rule with a colon to make the 'd' rule anonymous")


date_grammar = """
    Date  = year '-' month '-' day
    year  = d d d d
    month = d d 
    day   = d d
    d     : [0-9]
"""
print(date_grammar)

date = peg.compile(date_grammar)
p = date.parse("2021-04-05")
print(p)

print("\nNow a variation using * numeric repeat ------------------------\n")
print("-  same parse tree, but no need for an anonymous rule")

date_grammar = """
    Date  = year '-' month '-' day
    year  = [0-9]*4
    month = [0-9]*2 
    day   = [0-9]*2
"""
print(date_grammar)

date = peg.compile(date_grammar)
p = date.parse("2021-04-05")
print(p)
