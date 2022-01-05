import pPEG

print("Arith operatpr expression example....")

arith = pPEG.compile("""
  exp = add 
  add = sub ('+' sub)*
  sub = mul ('-' mul)*
  mul = div ('*' div)*
  div = pow ('/' pow)*
  pow = val ('^' val)*
  grp = '(' exp ')'
  val = " " (sym / num / grp) " "
  sym = [a-zA-Z]+
  num = [0-9]+
""")

tests = [
    " 1 + 2 * 3 ",
    "x^2^3 - 1"
];

for test in tests:
    p = arith.parse(test)
    print(p)


# 1+2*3 ==> (+ 1 (* 2 3))
# ["add",[["num","1"],["mul",[["num","2"],["num","3"]]]]]

# x^2^3+1 ==> (+ (^ x 2 3) 1)
# ["add",[["pow",[["sym","x"],["num","2"],["num","3"]]],["num","1"]]]
