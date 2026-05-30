from pPEGpy import peg
# import pPEGpy as peg

print("URI grammar...")

# Equivalent to the regular expression for
# well-formed URI's in RFC 3986.

uri = peg.compile("""
    URI     = (scheme ':')? ('//' auth)? 
               path ('?' query)? ('#' frag)?
    scheme  = ~[:/?#]+
    auth    = ~[/?#]*
    path    = ~[?#]*
    query   = ~'#'*
    frag    = ~[ \t\n\r]*
    """,
    transforms = {'URI': dict}
)

test = "http://www.ics.uci.edu/pub/ietf/uri/#Related"

ok, data = uri.read(test)

print(data)

# => {'scheme': 'http', 'auth': 'www.ics.uci.edu',
#     'path': '/pub/ietf/uri/', 'frag': 'Related'}

# -- parse tree ---------------------------------------

print("uri grammar...")

uri = peg.compile("""
    # Equivalent to the regular expression for
    # well-formed URI's in RFC 3986.
    URI     = (scheme ':')? ('//' auth)? 
               path ('?' query)? ('#' frag)?
    scheme  = ~[:/?#]+
    auth    = ~[/?#]*
    path    = ~[?#]*
    query   = ~'#'*
    frag    = ~[ \t\n\r]*
""")

test = "http://www.ics.uci.edu/pub/ietf/uri/#Related"

parse = uri.parse(test)

print(parse)

"""
url grammar...
URI
│ scheme 'http'
│ auth 'www.ics.uci.edu'
│ path '/pub/ietf/uri/'
│ frag 'Related'
"""

"""
url grammar...
["URI",[["scheme","http"],["auth","www.ics.uci.edu"],["path","/pub/ietf/uri/"],["frag","Related"]]]
"""
