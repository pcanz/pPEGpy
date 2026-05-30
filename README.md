# pPEGpy

This is an implementation of a portable PEG parser in Python.

For documentation see [pPEG], the portable PEG project.

The `pPEGpy` package can be installed from PyPi with:
Woops, lost my PyPi access credentials, so can't update PyPi yet...
See Notes below for how to clone and install this repo.
```
> pip install pPEGpy                  # version 3.18+  but not yet!
```
Note the spelling of `pPEGpy`, there are unrelated packages with similar names. 

For other ways to use the `pPEGpy` grammar-parser see the Package Notes below.

##  Examples

``` python
from pPEGpy import peg

print("Hello world!")

greet = peg.compile("""
    greet = _ hail _ whom _
    hail  = 'Hello' / 'Hi'
    whom  = 'you' / 'world!'
    _     = [ \t\n\r]*
    """,
    transforms = {"greet": dict}
)

ok, words = greet.read("Hello world!")

print(words) # => {'hail': 'Hello', 'whom': 'world!'}
```
Run this example, then edit to see what works or fails.

Comment out the transforms on line 11 to see the parse tree printed out as JSON.

More examples:
``` python
from pPEGpy import peg

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
```

``` python
import pPEGpy as peg

print("CSV example....")

csv = peg.compile("""
    CSV     = Row+
    Row     = field (',' field)* _nl
    field   = _string / _text

    _text   = ~[,\n\r]*
    _string = '"' (~["] / '""')* '"'
    _nl     = '\n' / '\r' '\n'?
    """,
    transforms = {
        'CSV':list, 'Row':list, 'field':str
    }
)

test = """A,B,C
a1,b1,c1
a2,"b,2",c2
a3,b3,c3
"""

ok, data = csv.read(test)

print(data)

# [['A', 'B', 'C'],
#  ['a1', 'b1', 'c1'],
#  ['a2', '"b,2"', 'c2'],
#  ['a3', 'b3', 'c3']]

# -- parse tree --------

p = csv.parse(test);

print(p)

# CSV
# │ Row
# │ │ field 'A'
# │ │ field 'B'
# │ │ field 'C'
# │ Row
# │ │ field 'a1'
# │ │ field 'b1'
# │ │ field 'c1'
# │ Row
# │ │ field 'a2'
# │ │ field '"b,2"'
# │ │ field 'c2'
# │ Row
# │ │ field 'a3'
# │ │ field 'b3'
# │ │ field 'c3'
```


## Package Notes

To experiment you can clone the GitHub repository [pPEGpy].

These command lines can be used to build a local package:
```
> cd <your pPEGpy directory>
> uv init --lib

> uv build
> pip install -e .

> python3 examples/date.py
> ...
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
