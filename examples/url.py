from pPEGpy import peg

print("url grammar...")

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
