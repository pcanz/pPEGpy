from pPEGpy import peg

print("json grammar...")

json = peg.compile("""
    json   = value
    value  =  _ (Str / Arr / Obj / num / lit) _
    Obj    = '{'_ (memb (','_ memb)*)? '}'
    memb   = Str ':' value
    Arr    = '[' (value (',' value)*)? ']'
    Str    = '"' chars* '"'
    chars  = ~[\u0000-\u001f\\"]+ / '\\' esc
    esc    = ["\\/bfnrt] / 'u' [0-9a-fA-F]*4
    num    = _int _frac? _exp?
    _int   = '-'? ([1-9] [0-9]* / '0')
    _frac  = '.' [0-9]+
    _exp   = [eE] [+-]? [0-9]+
    lit    = 'true' / 'false' / 'null'
    _      = [ \t\n\r]*
""")

#  Obj Arr Str need to be caps (they can be empty)

p = json.parse("""
  { "answer": 42,
    "mixed": [1, 2.3, "a\\tstring", true, [4, 5]],
    "empty": {}
  }
""")

print(p)

"""
json grammar...
Obj
│ memb
│ │ Str
│ │ │ chars 'answer'
│ │ num '42'
│ memb
│ │ Str
│ │ │ chars 'mixed'
│ │ Arr
│ │ │ num '1'
│ │ │ num '2.3'
│ │ │ Str
│ │ │ │ chars 'a'
│ │ │ │ esc 't'
│ │ │ │ chars 'string'
│ │ │ lit 'true'
│ │ │ Arr
│ │ │ │ num '4'
│ │ │ │ num '5'
│ memb
│ │ Str
│ │ │ chars 'empty'
│ │ Obj
"""

"""
json grammar...
["Obj",[["memb",[["Str",[["chars","answer"]]],["num","42"]]],["memb",[["Str",[["chars","mixed"]]],["Arr",[["num","1"],["num","2.3"],["Str",[["chars","a"],["esc","t"],["chars","string"]]],["lit","true"],["Arr",[["num","4"],["num","5"]]]]]]],["memb",[["Str",[["chars","empty"]]],["Obj","{}"]]]]]
"""
