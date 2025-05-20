# pPEGpy

This is an implementation of [pPEG] in Python.

The package pPEGpy was created with: uv init --lib

from pPEGpy import peg 

The peg.py file (in src/pPEGpy/) is a module with no dependencies.

##  Example

``` python
from pPEGpy import peg

sexp = peg.compile("""
    sexp  = _ list _
    list  = '(' _ elem* ')' _
    elem  = list / atom
    atom  = ~[() \t\n\r]+ _
    _     = [ \t\n\r]*
""")

test = """
    (foo bar (blat 42) (f(g(x))))
"""

p = sexp.parse(test)

print(p)
```

```
list
│ atom 'foo '
│ atom 'bar '
│ list
│ │ atom 'blat '
│ │ atom '42'
│ list
│ │ atom 'f'
│ │ list
│ │ │ atom 'g'
│ │ │ atom 'x'
```
ptree:
```
["list",[["atom","foo"],["atom","bar"],
    ["list",[["atom","blat"],["atom","42"]]],
    ["list",[["atom","f"],
        ["list",[["atom","g"],["atom","x"]]]]]]]
```

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
ptree:
```
["URI",[["scheme","http"],["auth","www.ics.uci.edu"],["path","/pub/ietf/uri/"],["frag","Related"]]]
```

##  Usage

The pPEG.py implementation is a single file with no dependencies.

Put a copy of the pPEG.py file into the same directory as your application, or use a PYTHONPATH shell environment variable for Python to load the pPEG.py module.

Not yet available for `pip` install.

Basic usage:

``` py    
    from pPEGpy import peg

    my_parser = peg.compile(""... my_grammar rules...""")

    # For the grammar rules see the [pPEG] documentation, then:

    parse = my_parser.parse(""...input string...")

    print(parse)  # prints the ptree result or an error message
```
Common usage:

``` py
    from pPEGpy import peg

    my_parser = peg.compile(""... my grammar rules...""")

    # -- use my-parser in my application .......

    my_parse = my_parser.parse('...input string...}')

    if not my_parse.ok:
        print(my_parse.err)
        .... handle parse failure ... 
    else:    
        process(my_parse.ptree)
```

The `ptree` parse tree type is JSON data, as defined in [pPEG].

## Package Notes

in pPEGpy:  

> uv init --lib

> uv build

> pip install -e .

The -e option allows local editing of the peg.py file.

The uv init --lib made the project name lower case ppegpy, I edited the name back to pPEGpy in several places (.toml, src/pPEGpy/)

For some unknown reason uv init --lib did not create the .venv or .vscode directories that I expected (it did build these when I tried it out earlier).  Is this because this directory was a github clone from my gitub repo??


### Bare File

The peg.py file in: pPEGpy/src/pPEGy/peg.py is the only file you really need.

If you put a copy of this file into the directory with your programs you can import the file directly.  Very simple and easy.  But that does not work across directories, to import the bare peg.py file from another directory requires a hack like this:

import sys

sys.path.insert(1, ".")  # import from current working directory
import pPEG

To simplify that (at the cost of all the Python packaging complications!) you can build a pacakage pPEGpy and install it as with pip, as above.

When pPEGpy is published on PyPi it can be installed with pip in the usual way.


### Development Tools?

Pylance could not resolve import from pPEGy  ??? 

Yet the files ran with > python3 date.py

Reading the doumentation leaad to this:

> python -m pip install {package_name}

~/D/p/pPEGpy[127]►python3 -m pip install pPEGpy         (master|💩?) 12:02
Defaulting to user installation because normal site-packages is not writeable
Requirement already satisfied: pPEGpy in /Users/petercashin/Library/Python/3.12/lib/python/site-packages (0.3.2)

[notice] A new release of pip is available: 24.2 -> 25.1.1
[notice] To update, run: pip install --upgrade pip


---

[pPEG]: https://github.com/pcanz/pPEG
