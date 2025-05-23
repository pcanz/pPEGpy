import pPEGpy as peg

# Context Sensitive Grammars

# using <@name> to match a name rule result the same-again

# basic test...

code = peg.compile("""
    s = x ':' <@x> ':' atx etc
    x = [a-z]*
    atx = <@x>
    etc = .*
""")

print(code.parse("abc:abc:abcdef"))

# Markdown code quotes...

code = peg.compile("""
    Code = tics code tics
    code = ~<@tics>*
    tics = [`]+
""")

print(code.parse("```abcc``def```"))

# Rust raw string syntax:

raw = peg.compile("""
    Raw   = fence '"' raw '"' fence
    raw   = ~('"' <@fence>)*
    fence = '#'+
""")

print(raw.parse("""##"abcc#"x"#def"##"""))

# indented blocks...

blocks = peg.compile("""
    Blk    = inset line (more / inlay)*
    more   = <@inset> !' ' line
    inlay  = &(<@inset> ' ') Blk
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
