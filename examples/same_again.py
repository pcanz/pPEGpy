import pPEGpy as peg

# Context Sensitive Grammars

# using <same name> to match a name rule result the same-again

# basic test...

code = peg.compile("""
    s = x ':' <same x>
    x = [a-z]*
""")

print(code.parse("abc:abc"))

# middle test...

code = peg.compile("""
    p  = x m x_
    x  = [a-z]
    x_ = <same x>
    m  = (x &x)*
""")

p = code.parse("abba")
# p.dump()
print(p)

# Markdown code quotes...

code = peg.compile("""
    Code = tics code tics
    code = ~<same tics>*
    tics = [`]+
""")

p = code.parse("```abc``def```")
# p.dump(0)
print(p)

# Rust raw string syntax:

raw = peg.compile("""
    Raw   = fence '"' raw '"' fence
    raw   = ~('"' <same fence>)*
    fence = '#'+
""")

print(raw.parse("""##"abcc#"x"#def"##"""))

# indented blocks...

blocks = peg.compile("""
    Blk    = inset line (next / inlay)*
    next   = <same inset> !' ' line
    inlay  = &(<same inset> ' ') Blk
    inset  = ' '+
    line   = ~[\n\r]* '\r'? '\n'?
""")

p = blocks.parse("""  line one
  line two
    inset 2.1
      inset 3.1
    inset 2.2
  line three
""")

print(p)
