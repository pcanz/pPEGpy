import pPEG

print("CSV example....")

csv = pPEG.compile("""
    CSV     = Hdr Row+
    Hdr     = Row
    Row     = field (',' field)* '\r'? '\n'
    field   = _string / _text / ''

    _text   = ~[,\n\r]+
    _string = '"' (~["] / '""')* '"'
""")

test = """A,B,C
a1,b1,c1
a2,"b,2",c2
a3,b3,c3
"""

p = csv.parse(test);

print(p)

"""
CSV example....
["CSV",[["Hdr",[["Row",[["field","A"],["field","B"],["field","C"]]]]],
    ["Row",[["field","a1"],["field","b1"],["field","c1"]]],
    ["Row",[["field","a2"],["field","\"b,2\""],["field","c2"]]],
    ["Row",[["field","a3"],["field","b3"],["field","c3"]]],["field",""]]]
"""