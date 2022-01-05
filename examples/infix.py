import pPEG

# operator expressions from GO lang.

exp = pPEG.compile("""
    exp   = " " opx " "
    opx   = pre (op pre)* <infix>
    pre   = pfx? var
    var   = val / id / "(" exp ")"
    val   = [0-9]+
    id    = [a-z]+
    pfx   = [-+]
    op    = " " (op_1L/op_2L/op_4L/op_5L/op_3L) " "
    op_1L = '||'
    op_2L = '&&'
    op_3L = '<'/'>'/'>='/'<='/'=='/'!='
    op_4L = [-+|^]
    op_5L = [*/%&]/'<<'/'>>'/'&^'
""")

def show(eg):
    print(eg, "=>", exp.parse(eg), "\n")

show("1+2*3")

show("1+2-3*4+1")

show("x+1>n*3&&p!=q||x/4<42")

"""
1+2*3 => ['+', [['val', '1'], ['*', [['val', '2'], ['val', '3']]]]] 

1+2-3*4+1 => ['+', [['-', [['+', [['val', '1'], ['val', '2']]], ['*', [['val', '3'], ['val', '4']]]]], ['val', '1']]] 

x+1>n*3&&p!=q||x/4<42 => ['||', [['&&', [['>', [['+', [['id', 'x'], ['val', '1']]], ['*', [['id', 'n'], ['val', '3']]]]], ['!=', [['id', 'p'], ['id', 'q']]]]], ['<', [['/', [['id', 'x'], ['val', '4']]], ['val', '42']]]]] 
"""