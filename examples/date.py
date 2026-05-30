import pPEGpy as peg

print(f"peg imported from: {peg.__file__}")

date = peg.compile("""
    date  = year '-' month '-' day
    year  = [0-9]*4
    month = [0-9]*2
    day   = [0-9]*2
    """,
    transforms = {
    'date':dict, 'year:':int, 'month:':int, 'day:':int
    }
)

ok, x = date.read('2026-02-03')

print(x) # => {'year': 2026, 'month': 2, 'day': 3}

# -- datetime example ---------------------

import datetime as dt

date = peg.compile(
    "date  = [0-9]*4 '-' [0-9]*2 '-' [0-9]*2",
    transforms = {'date': dt.date.fromisoformat}
)

ok, data = date.read("2026-03-04") 

if ok: print(data)  # => 2026-03-04

# -- parse tree with errors -----------------------

p = date.parse('2026-03-0x04x')

print('parse result:\n', p)
print('trace....')
p.print_trace()
print('tree....')
p.print_tree()



