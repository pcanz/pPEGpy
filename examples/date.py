import pPEG

print("date example ....")

dg = pPEG.compile("""
    Date  = year '-' month '-' day
    year  = d d d d
    month = d d 
    day   = d d
    d     = [0-9]
""") # '0'/'1'/'2'/'3'/'4'/'5'/'6'/'7'/'8'/'9'

p = dg.parse("2021-4-05  xxx")

print(p)

dt = pPEG.compile("""
    Date  = year '-' month '-' day
    year  = [0-9]*4
    month = [0-9]*1.. 
    day   = [0-9]*1..2
""")

d = dt.parse("2021-04-0567")

print(d)
