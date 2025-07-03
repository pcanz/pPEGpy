# pPEGpy

This is an implementation of a portable PEG parser in Python.

For documentation see [pPEG], the portable PEG project.

The `pPEGpy` package can be installed from PyPi with:
```
> pip install pPEGpy
```
Note the spelling of `pPEGpy`, there are unrelated packages with similar names. 

For other ways to use the `pPEGpy` grammar-parser see the Package Notes below.

##  Example

``` python
from pPEGpy import peg

sexp = peg.compile("""
    sexp  = _ list
    list  = '(' _ elem* ')' _
    elem  = list / atom _
    atom  = ~[() \t\n\r]+
    _     = [ \t\n\r]*
""")

test = """
    (foo bar (blat 42) (f(g(x))))
"""

p = sexp.parse(test)

print(p)
```
This prints a parse tree diagram:
```
list
│ atom 'foo'
│ atom 'bar'
│ list
│ │ atom 'blat'
│ │ atom '42'
│ list
│ │ atom 'f'
│ │ list
│ │ │ atom 'g'
│ │ │ atom 'x'
```
Application can use a `ptree`:
```
ptree = p.ptree()

print(ptree)  # =>

["list",[["atom","foo"],["atom","bar"],
    ["list",[["atom","blat"],["atom","42"]]],
    ["list",[["atom","f"],
        ["list",[["atom","g"],["atom","x"]]]]]]]
```
Another example:

``` python
from pPEGpy import peg

# Equivalent to the regular expression for well-formed URI's in RFC 3986.

pURI = peg.compile("""
    URI     = (scheme ':')? ('//' auth)? path ('?' query)? ('#' frag)?
    scheme  = ~[:/?#]+
    auth    = ~[/?#]*
    path    = ~[?#]*
    query   = ~'#'*
    frag    = ~[ \t\n\r]*
""")

test = "http://www.ics.uci.edu/pub/ietf/uri/#Related"
uri = pURI.parse(test)

print(uri)
```
```
URI
│ scheme 'http'
│ auth 'www.ics.uci.edu'
│ path '/pub/ietf/uri/'
│ frag 'Related'
```
p-tree:
```
["URI",[["scheme","http"],["auth","www.ics.uci.edu"],
        ["path","/pub/ietf/uri/"],["frag","Related"]]]
```

##  Usage

Common usage:

``` py
    from pPEGpy import peg

    my_parser = peg.compile(""... my pPEG grammar rules...""")

    # -- use my-parser in my application .......

    my_parse = my_parser.parse('...input string...}')

    if not my_parse.ok:
        # handle parse failure ... 
        print(my_parse)
    else:    
        ptree = my_parse.ptree()
        process(ptree)
```
The `ptree` parse tree type is JSON data, as defined in [pPEG].

## Package Notes

To experiment you can clone the GitHub repository [pPEGpy].

These command lines can be used to build a local package:
```
> cd <your pPEGpy directory>
> uv init --lib
> uv build
> pip install -e .
```
The -e option allows local editing of the local files.

The repo includes an `examples/` folder, try running the `date.py` for example. 

### Bare File

The `peg.py` file in: `pPEGpy/src/pPEGy/peg.py` is the only file you really need.

If you put a copy of this file into a folder together with your own programs you can import the grammar-parser directly with `import peg`.  Very simple and easy.

But that does not work across directories, to import the bare `peg.py` file from another directory requires a hack like this:
```
import sys
sys.path.insert(1, <path to your copy of peg.py>)
import peg
```
To avoid that (at the cost of all the Python packaging complications!) you can build a package `pPEGpy` and install it with pip, as above.


---

[pPEG]: https://github.com/pcanz/pPEG

[pPEGpy]: https://github.com/pcanz/pPEGpy/tree/master 

