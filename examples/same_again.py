import pPEG

# Context Sensitive Grammars

# using <@name> to match a name rule result the same-again

# Markdown code quotes...

code = pPEG.compile("""
    Code = tics code tics
    code = ~<@tics>*
    tics = [`]+
""")

print(code.parse("```abcc``def```"))

# Rust raw string syntax:

raw = pPEG.compile("""
    Raw   = fence '"' raw '"' fence
    raw   = ~('"' <@fence>)*
    fence = '#'+
""")

print(raw.parse('''##"abcc#"x"#def"##'''))

# indented blocks...

blocks = pPEG.compile("""
    Blk    = indent line (<@inset> !' ' line / Blk)*
    indent = &(<@inset> ' ') inset
    inset  = ' '+
    line   = ~[\n\r]* '\r'? '\n'
""")

print(blocks.parse("""  line one
  line two
    inset 2.1
      inset 3.1
    inset 2.2
  line three
"""))


# -- <quote> extension ----------

q = pPEG.compile("""
    q = [']+ <quote>
""")

print(q.parse("'''abc''def'''"))

# => ['quote', "abc''def"]

# -- <quoter> extension ----------

qr = pPEG.compile("""
    q = [#]+ "'" <quoter>
""")

print(qr.parse("##'abc#'xx'#def'##"))

# => ['quoter', "abc#'xx'#def"]
