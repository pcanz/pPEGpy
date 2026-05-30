import pPEGpy as peg

print("CSV example....")

csv = peg.compile("""
    CSV     = Row+
    Row     = field (',' field)* _nl
    field   = _string / _text

    _text   = ~[,\n\r]*
    _string = '"' (~["] / '""')* '"'
    _nl     = '\n' / '\r' '\n'?
    """,
    transforms = {
        'CSV':list, 'Row':list, 'field':str
    }
)

test = """A,B,C
a1,b1,c1
a2,"b,2",c2
a3,b3,c3
"""

ok, data = csv.read(test)

print(data)

# [['A', 'B', 'C'],
#  ['a1', 'b1', 'c1'],
#  ['a2', '"b,2"', 'c2'],
#  ['a3', 'b3', 'c3']]

# -- parse tree --------

p = csv.parse(test);

print(p)

# CSV
# │ Row
# │ │ field 'A'
# │ │ field 'B'
# │ │ field 'C'
# │ Row
# │ │ field 'a1'
# │ │ field 'b1'
# │ │ field 'c1'
# │ Row
# │ │ field 'a2'
# │ │ field '"b,2"'
# │ │ field 'c2'
# │ Row
# │ │ field 'a3'
# │ │ field 'b3'
# │ │ field 'c3'


