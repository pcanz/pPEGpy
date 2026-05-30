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
