# import pPEGpy as peg  # local file
from pPEGpy import peg  # pip install pPEGpy

print("Arith operator expression example....")

arith = peg.compile("""
  exp = add 
  add = sub ('+' sub)*
  sub = mul ('-' mul)*
  mul = div ('*' div)*
  div = pow ('/' pow)*
  pow = val ('^' val)*
  grp = '(' exp ')'
  val = _ (sym / num / grp) _
  sym = [a-zA-Z]+
  num = [0-9]+
  _   = [ \t\n\r]*
""")

tests = [" 1 + 2 * 3 ", "x^2^3 - 1"]
for test in tests:
    p = arith.parse(test)
    print(p)

# add
# │ num '1'
# │ mul
# │ │ num '2'
# │ │ num '3'

# sub
# │ pow
# │ │ sym 'x'
# │ │ num '2'
# │ │ num '3'
# │ num '1'

# 1+2*3 ==> (+ 1 (* 2 3))
# ["add",[["num","1"],["mul",[["num","2"],["num","3"]]]]]

# x^2^3+1 ==> (+ (^ x 2 3) 1)
# ["add",[["pow",[["sym","x"],["num","2"],["num","3"]]],["num","1"]]]
