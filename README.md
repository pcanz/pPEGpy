# pPEGpy

This is an implementation of [pPEG] in Python.

A single file Python module with no dependencies.

##  Example

``` py
import pPEG

# Equivalent to the regular expression for well-formed URI's in RFC 3986.

pURI = pPEG.compile("""
    URI     = (scheme ':')? ('//' auth)? path ('?' query)? ('#' frag)?
    scheme  = ~[:/?#]+
    auth    = ~[/?#]*
    path    = ~[?#]*
    query   = ~'#'*
    frag    = ~[ \t\n\r]*
""")

if not pURI.ok: raise Exception("URI grammar error: "+pURI.err)

test = "http://www.ics.uci.edu/pub/ietf/uri/#Related";

uri = pURI.parse(test)

if uri.ok: print(uri.ptree)
else: print(uri.err)

"""
["URI",[["scheme","http"],["auth","www.ics.uci.edu"],["path","/pub/ietf/uri/"],["frag","Related"]]]
"""
```

##  Usage

The pPEG.py implementation is a single file with no dependencies.

Put a copy of the pPEG.py file into the same directory as your application, or use a PYTHONPATH shell environment variable for Python3 to load the pPEG.py module.

Not yet available for `pip` install.

Basic usage:
    
    import pPEG

    my_parser = pPEG.compile(""... my grammar rules...""")

For the grammar rules see the [pPEG] documentation, then:

    my_parse = my_parser.parse(""...input string...")

    print(my_parse)  # prints the ptree result or an error message

Common usage:

    import pPEG

    my_parser = pPEG.compile(""... my grammar rules...""")

    if not my_parser.ok: raise Exception(my_parser.err)

    # -- use my-parser in my application .......

    my_parse = my_parser('...input string...}')

    if not my_parse.ok:
        print(my_parse.err)
        .... handle parse failure ... 
    else:    
        process(my_parse.ptree)

The `ptree` parse tree type is JSON data, as defined in [pPEG].



[pPEG]: https://github.com/pcanz/pPEG
