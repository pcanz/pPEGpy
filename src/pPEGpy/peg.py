# pPEGpy -- run with Python 3.10+   2025-05-18

from __future__ import annotations  # parser() has a forward ref to Code as type

import array


# -- pPEG grammar ------------------------------------------------------------

peg_grammar = R"""
Peg   = _ rule+
rule  = id _ def _ alt
def   = [:=]+
alt   = seq ('/' _ seq)*
seq   = rep+
rep   = pre sfx? _
pre   = pfx? term
term  = call / quote / class / dot / group / extn
group = '(' _ alt ')'
call  = id _ !def
id    = [a-zA-Z_] [a-zA-Z0-9_]*
pfx   = [~!&]
sfx   = [+?] / '*' nums?
nums  = min ('..' max)?
min   = [0-9]+
max   = [0-9]*
quote = ['] ~[']* ['] 'i'?
class = '[' ~']'* ']'
dot   = '.'_
extn  = '<' ~'>'* '>'
_     = ([ \t\n\r]+ / '#' ~[\n\r]*)*
"""

# -- Parse context for parser run function -----------------------------------


class Parse:
    def __init__(self, code: Code, input: str):
        self.ok = True
        self.code = code
        self.input = input
        self.pos = 0
        self.end = len(input)

        # parse tree arrays -- L = 4 Bytes, H = 2 Bytes, B = 1 Byte
        self.idents = array.array("H")  # rule ident: <<id:12, type:4>>
        self.sizes = array.array("L")  # node shape: <<size:24, depth:8>>
        self.starts = array.array("L")  # input start index
        self.ends = array.array("L")  # input end index

        # run state...
        self.anon = False  # True when running anon rules
        self.deep = 0  # tree depth, deep to avoid name conflict with self.depth()
        self.max_depth = 255  # catch left recursion

        # faults...
        self.max_pos = -1  # peak fail
        self.first = -1  # node at max pos failure
        self.top = -1  # parent of first node
        self.end_pos = -1  # fell short end pos

    def __str__(self):
        if self.ok:
            return show_tree(self)
        else:
            return err_report(self)

    def name(self, i):  # parse tree node name
        ident = self.idents[i]  # [id:0xFFF|type:0xF]
        return self.code.names[ident >> 4]

    def text(self, i):  # parse tree node matched text
        start = self.starts[i]
        end = self.ends[i]
        return self.input[start:end]

    def size(self, i):
        return self.sizes[i] >> 8

    def depth(self, i):
        return self.sizes[i] & 0xFF

    def leaf(self, i):  # is a terminal node?
        return self.idents[i] & 0xF == TERM

    def tree(self):
        ptree = p_tree(self, 0, len(self.ends))
        if not ptree:
            return []
        return ptree[0]

    def itree(self):
        itree = i_tree(self, 0, len(self.ends))
        if not itree:
            return []
        return itree[0]

    def dump(self, filter=1):
        return dump_tree(self, filter)

    def transform(self, i=0, j=-1, **fns):
        if j < 0:
            j = self.size(i)
        return transformer(self, i, j, fns)


# -- the parser function itself -------------------


def parser(code: Code, input: str) -> Parse:
    parse = Parse(code, input)
    if not code.ok:
        parse.ok = False
        return parse
    ok = run(parse, ["id", 0])
    if ok and parse.pos < len(parse.input):
        parse.end_pos = parse.pos
        ok = False
    parse.ok = ok
    if parse.ok:
        prune_tree(parse)  # delete failures and redundant heads
    return parse


# -- the run engine that does all the work ----------------------------


def run(parse: Parse, expr: list):
    match expr:
        case ["id", idx]:
            # execute anon ids....
            if parse.anon:
                return run(parse, parse.code.codes[idx])
            defx = parse.code.defs[idx]
            if defx == ANON:
                parse.anon = True
                ok = run(parse, parse.code.codes[idx])
                parse.anon = False
                return ok

            # all other ids.............
            pos = parse.pos
            depth = parse.deep
            parse.deep += 1
            if parse.deep > parse.max_depth:
                raise SystemExit(f"*** run away recursion, in: {parse.code.names[idx]}")

            # parse tree array - enter node ------------
            index = len(parse.starts)
            parse.starts.append(pos)
            parse.idents.append((idx << 4) | defx)
            parse.ends.append(0)  # assign at index after run
            parse.sizes.append(0)  # assign at index after run

            # -- run -----------------------
            rule = parse.code.codes[idx]
            ok = run(parse, rule)  # ok = True/False
            # ------------------------------

            if not ok and parse.pos >= parse.max_pos:
                parse.top = index  # parent of peak failure
                if parse.pos > parse.max_pos:
                    parse.max_pos = parse.pos
                    parse.first = index  # root of peak failure

            # parse tree ---------------
            parse.ends[index] = parse.pos
            size = len(parse.ends) - index
            parse.sizes[index] = (size << 8) | depth
            if not ok:
                parse.idents[index] |= FAIL  # fail flag

            parse.deep -= 1
            return ok

        case ["alt", list]:
            pos = parse.pos
            max = pos
            for x in list:
                if run(parse, x):
                    if parse.pos > pos:  # treat empty match as failure
                        return True
                if parse.pos > pos:
                    max = pos
                parse.pos = pos  # reset (essential)
            parse.pos = max  # to be caught in id
            return False

        case ["seq", list]:
            for i, x in enumerate(list):
                if not run(parse, x):
                    return False
            return True

        case ["rept", min, max, exp]:
            pos = parse.pos
            if not run(parse, exp):
                if min == 0:
                    parse.pos = pos  # reset
                    return True  # * ?
                return False  # +
            if max == 1:
                return True  # ?
            count = 1
            pos1 = parse.pos
            while True:
                result = run(parse, exp)
                if parse.pos == pos1:
                    break
                if not result:
                    parse.pos = pos1  # reset loop last try
                    break
                pos1 = parse.pos
                count += 1
                if count == max:
                    break
            if min > 0 and count < min:
                return False
            return True

        case ["pred", op, term]:  # !x &x
            pos = parse.pos
            result = run(parse, term)
            parse.pos = pos  # reset
            if op == "!":
                return not result
            return result

        case ["neg", term]:  # ~x
            if parse.pos >= parse.end:
                return False
            pos = parse.pos
            result = run(parse, term)
            parse.pos = pos  # reset
            if result:
                return False
            parse.pos += 1
            return True

        case ["quote", str, i]:
            for ch in str:  # 'abc' compiler strips quotes
                if parse.pos >= parse.end:
                    return False
                char = parse.input[parse.pos]
                if i:
                    char = char.upper()
                if char != ch:
                    return False
                parse.pos += 1
            return True

        case ["class", chars]:
            if parse.pos >= parse.end:
                return False
            char = parse.input[parse.pos]
            max = len(chars) - 1  # eg [a-z0-9_]
            i = 1
            while i < max:
                a = chars[i]
                if i + 2 < max and chars[i + 1] == "-":
                    if char >= a and char <= chars[i + 2]:
                        parse.pos += 1
                        return True
                    i += 3
                else:
                    if char == a:
                        parse.pos += 1
                        return True
                    i += 1
            return False

        case ["dot"]:
            if parse.pos >= parse.end:
                return False
            parse.pos += 1
            return True

        case ["extn", chars]:  # TODO compile into function call
            args = chars[1:-1].split()
            extra = parse.code.extras.get(args[0], None)
            if extra:
                return extra(parse, args)
            print(f"extn args: {args}")
            return False

        case ["ext", fn]:
            return fn(parse)

        case _:
            raise Exception("*** crash: run: undefined expression...")


# -- prune parse tree -- removes failures and redundant nodes -------------------

# failures are included in the parse tree to help with debug and fault reporting
# it is more efficient to delete redundant nodes as a separate pass at the end..


def prune_tree(parse):
    # These were too tricky for me to combine!  So two steps...
    _, i = prune(parse, 1, 0, len(parse.ends), 0, 0)  # step 1 delete failures
    _, j = prune(parse, 2, 0, i, 0, 0)  # step 2 delete redundant nodes
    while j < len(parse.ends):  # array API has no len/cap access
        parse.idents.pop()
        parse.sizes.pop()
        parse.starts.pop()
        parse.ends.pop()


def prune(parse, step, i, j, k, depth):  #  -> (i, k)
    while i < j:  # read: i..j  ==>  write: k..
        ident = parse.idents[i]
        fail = (ident & 8) != 0
        size = parse.size(i)
        if fail:  # step == 1
            i += size
            continue
        start = parse.starts[i]
        end = parse.ends[i]
        if size == 1:
            i1 = i + 1
            k1 = k + 1
        else:
            elide = (step == 2) and (ident & 7) == EQ
            if elide and i + 1 < j and size - 1 == parse.size(i + 1):
                i += 1
                continue
            i1, k1 = prune(parse, step, i + 1, i + size, k + 1, depth + 1)
            size = k1 - k
        if size == 1 and (ident & 3) != HEAD:
            ident = (ident & 0xFFF8) | TERM  # leaf node
        parse.idents[k] = ident
        parse.starts[k] = start
        parse.ends[k] = end
        parse.sizes[k] = (size << 8) | (depth & 0xFF)
        k = k1
        i = i1
    return (i, k)


# -- ptree json -----------------------------------------------------------------


def p_tree(parse: Parse, i, j):
    arr = []
    while i < j:
        if parse.leaf(i):
            arr.append([parse.name(i), parse.text(i)])
        else:
            arr.append([parse.name(i), p_tree(parse, i + 1, i + parse.size(i))])
        i += parse.size(i)
    return arr


# -- itree json -----------------------------------------------------------------


def i_tree(p: Parse, i, j):
    arr = []
    while i < j:
        size = p.size(i)
        args = None if p.leaf(i) else i_tree(p, i + 1, i + size)
        arr.append([p.name(i), p.starts[i], p.ends[i], args])
        i += size
    return arr


# -- ptree line diagram --------------------------------------------------------


def show_tree(parse: Parse) -> str:
    lines = []
    for i in range(0, len(parse.ends)):
        value = f" {repr(parse.text(i))}" if parse.leaf(i) else ""
        lines.append(f"{indent_bars(parse.depth(i))}{parse.name(i)}{value}")
    return "\n".join(lines)


# -- debug dump of parse tree nodes --------------------------------------------


def dump_tree(parse: Parse, filter=1) -> None:
    print("Node Size Span    Tree                                  Input...", end="")
    failed = False  # flag any failed nodes (for an end note)
    pos = 0  # to fill in any anon text matched between nodes
    for i in range(0, len(parse.ends)):
        ident = parse.idents[i]
        id = ident >> 4
        name = parse.code.names[id]
        fail = (ident & FAIL) != 0
        if fail:
            failed = True  # just for a note at end of the dump output
        start = parse.starts[i]
        end = parse.ends[i]
        shape = parse.sizes[i]
        size = shape >> 8
        depth = shape & 0xFF
        if fail:
            if filter == 1 and start == end:
                continue
            name = "!" + name
        anon = ""
        if pos < start:
            anon = f" -> {parse.input[pos:start]!r}"
        pos = end
        print(anon)  # appends '-> anon' to end of line for previous node
        # now for the node print out....
        init = f"{i:3} {size:3} {start:3}..{end}"
        value = f"{repr(parse.input[start:end])}" if ident & 3 == TERM else ""
        report = f"{init:16}  {indent_bars(depth)}{name} {value}"
        etc = ""  # truncate long lines...
        if end - start > 30:
            end = start + 30
            etc = "..."
        text = f"{parse.input[start:end]!r}{etc}"
        print(f"{report:70} {text}", end="")
        # next loop: print(anon) to append -> text at end of this line
    anon = ""
    if pos < parse.max_pos:  # final last node anon text...
        anon = f" -> {parse.input[pos : parse.max_pos]!r}"
    print(anon)
    if filter == 1 and failed:
        print(
            "Note: empty failures have been omitted (use parse.dump(0) to see everything)."
        )


# -- Parse error reporting ---------------------------------------------------


def show_pos(parse, info=""):
    pos = max(parse.pos, parse.max_pos)
    sol = line_start(parse, pos - 1)
    eol = line_end(parse, pos)
    ln = line_number(parse.input, sol)
    left = f"line {ln} | {parse.input[sol + 1 : pos]}"
    prior = ""  # show previous line...
    if sol > 0:
        sol1 = line_start(parse, sol - 1)
        prior = f"line {ln - 1} | {parse.input[sol1 + 1 : sol]}\n"
    if pos == parse.end:
        return f"{prior}{left}\n{' ' * len(left)}^ {info}"
    return f"{prior}{left}{parse.input[pos]}{parse.input[pos + 1 : eol]}\n{' ' * len(left)}^ {info}"


def line_start(parse, sol):
    while sol >= 0 and parse.input[sol] != "\n":
        sol -= 1
    return sol


def line_end(parse, eol):
    while eol < parse.end and parse.input[eol] != "\n":
        eol += 1
    return eol


def indent_bars(size):
    # return '| '*size
    # return '\u2502 '*size
    # return '\x1B[38;5;253m\u2502\x1B[0m '*size
    return "\x1b[38;5;253m" + "\u2502 " * size + "\x1b[0m"


def line_number(input, i):
    if i < 0:
        return 1
    if i >= len(input):
        i = len(input) - 1
    n = 1
    while i >= 0:
        while i >= 0 and input[i] != "\n":
            i -= 1
        n += 1
        i -= 1
    return n


def rule_info(parse):
    if parse.top > parse.first and parse.end_pos > -1:
        return "unexpected ending"
    target = parse.first
    if parse.first < len(parse.ends) - 1 and parse.top < parse.first:
        target = parse.top
    name = parse.name(target)
    if parse.starts[target] == parse.ends[target]:
        note = " expected"
    else:
        note = " failed"
    return src_map(parse, name, note)


def src_map(parse, name, note=""):
    peg_parse = parse.code.peg_parse
    if not peg_parse:
        return name + note + " in boot-code..."
    lines = [name + note]
    # show grammar rule....
    for i in range(0, len(peg_parse.ends)):
        if peg_parse.name(i) != "rule":
            continue
        if peg_parse.text(i + 1) != name:
            continue
        lines.append(f"{peg_parse.text(i)}")
    return "\n".join(lines)


def err_report(parse):
    note = "... for more details use: parse.dump() ..."
    at_pos = f"at: {max(parse.pos, parse.max_pos)} of: {parse.end}  {note}"
    if parse.code and parse.code.err:
        title = f"*** grammar failed {at_pos}"
        errs = "\n".join(parse.code.err)
        return f"{title}\n{errs}\n{show_pos(parse)}"
    title = f"*** parse failed {at_pos}"
    return f"""{title}\n{show_pos(parse, rule_info(parse))}"""


# == pPEG ptree is compiled into a Code object with instructions for parser ======================


class Code:
    def __init__(self, peg_parse, extras=None, boot=None):
        self.peg_parse = peg_parse  # Parse of Peg grammar (None for boot)
        self.ptree = boot or peg_parse.tree()
        self.names = []  # rule name
        self.rules = []  # rule body expr
        self.codes = []  # compiled expr
        self.defs = []  # rule type, defn symbol
        self.extras = extras  # extension functions
        self.err = []
        self.ok = True
        self.compose()

    def compose(self):
        names_defs_rules(self)
        self.codes = [emit(self, x) for x in self.rules]
        if self.err:
            self.ok = False

    def __str__(self):
        if not self.ok:
            return f"code error: {self.err}"
        lines = []
        for i, rule in enumerate(self.names):
            lines.append(f"{i:2}: {rule} {DEFS[self.defs[i]]} {self.codes[i]}")
        return "\n".join(lines)

    def parse(self, input):
        return parser(self, input)

    def errors(self):
        return "\n".join(self.err)


# -- rule types ------------------------------------------------------------------

DEFS = ["=", ":", ":=", "=:"]

EQ = 0  # =    dynamic children: 0 => TERM, 1 => redundant, >1 => HEAD
ANON = 1  # :    rule name and results not in the parse tree
HEAD = 2  # :=   parent node with any number of children
TERM = 3  # =:   terminal leaf node text match

FAIL = 8  #      flag bit

# -- compile Parse into Code parser instructions -----------------------------------


def names_defs_rules(code: Code) -> None:
    for rule in code.ptree[1]:
        match rule:
            case ["rule", [["id", name], ["def", defn], expr]]:
                code_rule_defs(code, name, defn, expr)
            case ["rule", [["id", name], expr]]:  # core peg grammar bootstrap
                code_rule_defs(code, name, "=", expr)
            case _:
                code.err.append(f"Expected 'rule', is this a Peg ptree?\n {rule}")
                break


def code_rule_defs(code, name, defn, expr):
    if name in code.names:
        code.err.append(f"duplicate rule name: {name}")
    code.names.append(name)
    code.rules.append(expr)
    try:
        defx = DEFS.index(defn)
    except ValueError:
        defx = FAIL
        code.err.append(f"undefined: {name} {defn} ...")
    if defx == EQ:
        if name[0] == "_":
            defx = ANON
        elif name[0] >= "A" and name[0] <= "Z":
            defx = HEAD
    code.defs.append(defx)


def emit(code, expr):
    match expr:
        case ["id", name]:
            try:
                idx = code.names.index(name)
            except ValueError:
                code.err.append(f"undefined rule: {name}")
                code_rule_defs(code, name, "=", ["extn", "<undefined>"])
                code.codes.append(["extn", "<undefined>"])
                return ["id", len(code.names) - 1]
            return ["id", idx]
        case ["alt", nodes]:
            return ["alt", [emit(code, x) for x in nodes]]
        case ["seq", nodes]:
            return ["seq", [emit(code, x) for x in nodes]]
        case ["rep", [exp, ["sfx", op]]]:
            min = 0
            max = 0
            if op == "+":
                min = 1
            elif op == "?":
                max = 1
            return ["rept", min, max, emit(code, exp)]
        case ["rep", [exp, ["min", min]]]:
            min = int(min)
            return ["rept", min, min, emit(code, exp)]
        case ["rep", [exp, ["nums", [["min", min], ["max", max]]]]]:
            min = int(min)
            max = 0 if not max else int(max)
            return ["rept", min, max, emit(code, exp)]
        case ["pre", [["pfx", pfx], exp]]:
            if pfx == "~":
                return ["neg", emit(code, exp)]
            return ["pred", pfx, emit(code, exp)]
        case ["quote", str]:
            if str[-1] != "i":
                return ["quote", escape(str[1:-1], code), False]
            return ["quote", escape(str[1:-2].upper(), code), True]
        case ["class", str]:
            return ["class", escape(str, code)]
        case ["dot", _]:
            return ["dot"]
        case ["extn", _]:
            return expr
        case _:
            raise Exception(f"*** crash: emit: undefined expression: {expr}")


def escape(s, code):
    r = ""
    i = 0
    while i < len(s):
        c = s[i]
        i += 1
        if c == "\\" and i < len(s):
            k = s[i]
            i += 1
            if k == "n":
                c = "\n"
            elif k == "r":
                c = "\r"
            elif k == "t":
                c = "\t"
            elif k == "x":
                c, i = hex_value(2, s, i)
            elif k == "u":
                c, i = hex_value(4, s, i)
            elif k == "U":
                c, i = hex_value(8, s, i)
            else:
                i -= 1
            if c is None:
                code.err.append(f"bad escape code: {s}")
                return s
        r += c
    return r


def hex_value(n, s, i):
    if i + n > len(s):
        return (None, i)
    try:
        code = int(s[i : i + n], 16)
    except Exception:
        return (None, i)
    return (chr(code), i + n)


# -- parse.transform -----------------------------------------------------------


def transformer(p: Parse, i, j, fns):
    vals = []
    while i < j:
        name = p.name(i)
        fn = fns.get(name)
        if p.leaf(i):
            text = p.text(i)
            i += 1
            if fn:
                vals.append(apply(name, fn, text))
            else:
                vals.append([name, text])
        else:
            k = i + p.size(i)
            result = transformer(p, i + 1, k, fns)
            i = k
            if fn:
                vals.append(apply(name, fn, result))
            else:
                vals.append([name, result])
    if len(vals) == 1:
        return vals[0]
    return vals


def apply(name, fn, args):
    result = None
    try:
        result = fn(args)
    except Exception as err:
        raise SystemExit(f"{name}({args})\n{err}")
    return result


# -- peg_grammar ptree -- bootstrap generated ---------------------------------------------------------

peg_ptree = ['Peg', [
['rule', [['id', 'Peg'], ['def', '='], ['seq', [['id', '_'], ['rep', [['id', 'rule'], ['sfx', '+']]]]]]],
['rule', [['id', 'rule'], ['def', '='], ['seq', [['id', 'id'], ['id', '_'], ['id', 'def'], ['id', '_'], ['id', 'alt']]]]],
['rule', [['id', 'def'], ['def', '='], ['rep', [['class', '[:=]'], ['sfx', '+']]]]],
['rule', [['id', 'alt'], ['def', '='], ['seq', [['id', 'seq'], ['rep', [['seq', [['quote', "'/'"], ['id', '_'], ['id', 'seq']]], ['sfx', '*']]]]]]],
['rule', [['id', 'seq'], ['def', '='], ['rep', [['id', 'rep'], ['sfx', '+']]]]],
['rule', [['id', 'rep'], ['def', '='], ['seq', [['id', 'pre'], ['rep', [['id', 'sfx'], ['sfx', '?']]], ['id', '_']]]]],
['rule', [['id', 'pre'], ['def', '='], ['seq', [['rep', [['id', 'pfx'], ['sfx', '?']]], ['id', 'term']]]]],
['rule', [['id', 'term'], ['def', '='], ['alt', [['id', 'call'], ['id', 'quote'], ['id', 'class'], ['id', 'dot'], ['id', 'group'], ['id', 'extn']]]]],
['rule', [['id', 'group'], ['def', '='], ['seq', [['quote', "'('"], ['id', '_'], ['id', 'alt'], ['quote', "')'"]]]]],
['rule', [['id', 'call'], ['def', '='], ['seq', [['id', 'id'], ['id', '_'], ['pre', [['pfx', '!'], ['id', 'def']]]]]]],
['rule', [['id', 'id'], ['def', '='], ['seq', [['class', '[a-zA-Z_]'], ['rep', [['class', '[a-zA-Z0-9_]'], ['sfx', '*']]]]]]],
['rule', [['id', 'pfx'], ['def', '='], ['class', '[~!&]']]],
['rule', [['id', 'sfx'], ['def', '='], ['alt', [['class', '[+?]'], ['seq', [['quote', "'*'"], ['rep', [['id', 'nums'], ['sfx', '?']]]]]]]]],
['rule', [['id', 'nums'], ['def', '='], ['seq', [['id', 'min'], ['rep', [['seq', [['quote', "'..'"], ['id', 'max']]], ['sfx', '?']]]]]]],
['rule', [['id', 'min'], ['def', '='], ['rep', [['class', '[0-9]'], ['sfx', '+']]]]],
['rule', [['id', 'max'], ['def', '='], ['rep', [['class', '[0-9]'], ['sfx', '*']]]]],
['rule', [['id', 'quote'], ['def', '='], ['seq', [['class', "[']"], ['rep', [['pre', [['pfx', '~'], ['class', "[']"]]], ['sfx', '*']]], ['class', "[']"], ['rep', [['quote', "'i'"], ['sfx', '?']]]]]]],
['rule', [['id', 'class'], ['def', '='], ['seq', [['quote', "'['"], ['rep', [['pre', [['pfx', '~'], ['quote', "']'"]]], ['sfx', '*']]], ['quote', "']'"]]]]],
['rule', [['id', 'dot'], ['def', '='], ['seq', [['quote', "'.'"], ['id', '_']]]]],
['rule', [['id', 'extn'], ['def', '='], ['seq', [['quote', "'<'"], ['rep', [['pre', [['pfx', '~'], ['quote', "'>'"]]], ['sfx', '*']]], ['quote', "'>'"]]]]],
['rule', [['id', '_'], ['def', '='], ['rep', [['alt', [['rep', [['class', '[ \\t\\n\\r]'], ['sfx', '+']]], ['seq', [['quote', "'#'"], ['rep', [['pre', [['pfx', '~'], ['class', '[\\n\\r]']]], ['sfx', '*']]]]]]], ['sfx', '*']]]]]
]]  # fmt: skip

# == pPEG compile API =========================================================

peg_code = Code(None, {}, peg_ptree)  # boot compile


def compile(grammar, extras=None) -> Code:
    parse = parser(peg_code, grammar)
    if not parse.ok:
        raise SystemExit("*** grammar fault...\n" + err_report(parse))
    code = Code(parse, extras)
    if not code.ok:
        raise SystemExit("*** grammar errors...\n" + code.errors())
    return code


peg_code = compile(peg_grammar)  # to improve grammar error reporting
