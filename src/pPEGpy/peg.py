# pPEGpy -- run with Python 3.10+   2025-06-09

# pPEGpy-12.py => copy to pPEGpyas peg.py github repo v0.3.2, and PyPi upload.
# pPEGpy-13.py  -- add extension functions: <@name> <dump> => PyPi 0.3.4
#  -- fix roll back, add test-peg  => PyPi 0.3.5
#  -- improve dump to show !fail or -roll back  => PyPi 0.3.6
# pPEGpy-14.py -- change roll-back, use seq reset => PyPi 0.3.7
#  -- simplify Code to take a boot=ptree optional argument
#  -- add a parse debug option to dump the parse tree
# pPEGpy-15.py => PyPi 0.3.8
# pPEGpy-16.py  2025-06-09  => PyPi 0.3.9 failed with extras file => 0.3.10
#  -- improve transform
#  -- dump 1 default, 2 filter failures
#  -- extras.py file for extension functions -- abandoned, append here
# pPEGpy-17.py  2025-06-09
# - nodes, spans  simplify tree into two arrays rather than four
# - improve <indent>
# - external extensions
# pPEGpy-18.py  2025-06-17 => PyPi 0.3.11
# - simplify trace parse tree to used depth only (no size)


# TODO
# - keep trace and build new pruned tree
# - add a <match rule> extra to enable palindrome grammar

from __future__ import annotations  # parser() has a forward ref to Code as type

import array

# import extras  # extension functions # included at the end of this file

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

# -- rule types ------------------------------------------------------------------

DEFS = ["=", ":", ":=", "=:"]

EQ = 0  # =    dynamic children: 0 => TERM, 1 => redundant, >1 => HEAD
ANON = 1  # :    rule name and results not in the parse tree
HEAD = 2  # :=   parent node with any number of children
TERM = 3  # =:   terminal leaf node text match

FAIL = 0xC  #      failure flag bits: FALL | FELL
FALL = 0x8  #      match failed: !rule
FELL = 0x4  #      fall-back cancel: -rule


# -- Parse context for parser run function -----------------------------------


class Parse:
    def __init__(self, code: Code, input: str, **opt):
        self.ok = True
        self.code = code
        self.input = input
        self.pos = 0
        self.end = len(input)

        # parse tree arrays -- Q = 64 bits, L = 32 bits
        self.nodes = array.array("L")  # <<dx:8, id:12, depth:12>>
        self.spans = array.array("Q")  # <<start:32, end:32>>

        # run state...
        self.anon = False  # True when running anon rules
        self.deep = 0  # tree depth, deep to avoid name conflict with self.depth()
        self.max_depth = 255  # catch left recursion

        # faults...
        self.index = 0  # parse tree length, for fall-back resets
        self.max_pos = -1  # peak fail
        self.first = -1  # node at max pos failure
        self.top = -1  # parent of first node
        self.end_pos = -1  # fell short end pos

        # transform map...
        self.transforms = None  # for parse.transform(...)

        # extensions state...
        self.extra_state = {}

    def __str__(self):
        if self.ok:
            return show_tree(self)
        else:
            return err_report(self)

    # -- parse tree methods ---------------------------

    def id(self, i):  # <<dx:8, id:12, depth:12>>
        return (self.nodes[i] >> 12) & 0xFFF

    def name(self, i):  # parse tree node name
        return self.code.names[self.id(i)]

    def span(self, i):
        w = self.spans[i]
        return (w >> 32, w & 0xFFFF_FFFF)

    def text(self, i):  # parse tree node matched text
        start, end = self.span(i)
        return self.input[start:end]

    def depth(self, i):  # <<dx:8, id:12, depth:12>>
        return self.nodes[i] & 0xFFF

    def leaf(self, i):  # is a terminal node?
        return (self.nodes[i] >> 24) & 0x3 == TERM

    def fail(self, i):  # failed node?  FAIL = 0xC == fail 0x8 | fall back 0x4
        return ((self.nodes[i] >> 24) & FAIL) != 0

    def defn(self, i):  # rule type EQ|HEAD|TERM|ANON
        return (self.nodes[i] >> 24) & 3

    def dx(self, i):  # <<dx:8, id:12, depth:12>>
        return self.nodes[i] >> 24

    def tree(self):
        ptree, _ = p_tree(self, 0, 0)
        if not ptree:
            return []
        return ptree[0]

    def itree(self):
        itree, _ = i_tree(self, 0, 0)
        if not itree:
            return []
        return itree[0]

    def dump(self, filter=1):
        return dump_tree(self, filter)

    def transform(self, **fns):
        self.transforms = fns
        result, _ = transformer(self, 0, 0)
        return result


# -- the parser function itself -------------------


def parser(code: Code, input: str, **opt) -> Parse:
    parse = Parse(code, input, **opt)
    if not code.ok:
        parse.ok = False
        return parse
    ok = run(parse, ["id", 0])
    if ok and parse.pos < len(parse.input):
        parse.end_pos = parse.pos
        ok = False
    parse.ok = ok
    debug = opt.get("debug")
    if debug:
        parse.dump(debug)
    if parse.ok:
        prune_tree(parse)  # delete failures and redundant heads
    return parse


# -- the run engine that does all the work ----------------------------


def run(parse: Parse, expr: list) -> bool:
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
            index = parse.index  # this node == len(parse.nodes)
            parse.index += 1  # <<dx:8, id:12, depth:12>>
            parse.nodes.append(defx << 24 | idx << 12 | depth)
            parse.spans.append(pos << 32)

            # -- run -----------------------
            rule = parse.code.codes[idx]
            ok = run(parse, rule)  # ok = True | False
            # ------------------------------

            if not ok and parse.pos >= parse.max_pos:
                parse.top = index  # parent of peak failure
                if parse.pos > parse.max_pos:
                    parse.max_pos = parse.pos
                    parse.first = index  # root of peak failure

            # parse tree ---------------
            parse.spans[index] |= parse.pos
            if not ok:  # <<dx:8, id:12, depth:12>>
                parse.nodes[index] |= FALL << 24

            parse.deep -= 1
            return ok

        case ["alt", list]:
            pos = parse.pos
            max = pos
            for x in list:
                if run(parse, x):
                    if parse.pos > pos:  # treat empty match as failure
                        return True  # TODO report a warning for this
                if parse.pos > pos:
                    max = pos
                parse.pos = pos  # reset (essential)
            parse.pos = max  # to be caught in id
            return False

        case ["seq", list]:
            index = parse.index
            for i, x in enumerate(list):
                if not run(parse, x):
                    while index < parse.index:  # fall-back
                        parse.nodes[index] |= FELL << 24
                        index += 1  # cancel parse tree nodes
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
            index = parse.index
            pos = parse.pos
            result = run(parse, term)
            parse.pos = pos  # reset
            i = index  # parse tree fall-back
            while i < parse.index:
                parse.nodes[i] |= FELL << 24
                i += 1
            if op == "!":
                return not result
            return result

        case ["neg", term]:  # ~x
            if parse.pos >= parse.end:
                return False
            index = parse.index
            pos = parse.pos
            result = run(parse, term)
            parse.pos = pos  # reset
            i = index  # parse tree fall-back
            while i < parse.index:
                parse.nodes[i] |= FELL << 24
                i += 1
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

        case ["ext", fn, *args]:  # compiled from <some extension>
            return fn(parse, *args)  # TODO reset fall-back on failure

        case _:
            raise Exception("*** crash: run: undefined expression...")


# -- prune parse tree -- removes failures and redundant nodes -------------------

# failures are included in the trace parse tree to help with debug and fault reporting
# redundant nodes are removed to simplify the parse tree for use in applications


def prune_tree(parse):
    _, k = prune(parse, 0, 0, 0, 0)
    while k < len(parse.nodes):  # array API has no len/cap access
        parse.nodes.pop()
        parse.spans.pop()


def prune(p, i, d, n, k):  #  -> (i, k)
    # read from i: (i, dep)  ==>  write to k: (k, dep-n)
    # d = depth of parent node, n = delta depth (deleted redundant nodes)
    j = len(p.nodes)
    while i < j and (dep := p.depth(i)) >= d:
        if p.fail(i):
            i += 1
            while i < len(p.nodes) and p.depth(i) > dep:
                i += 1  # skip over any children...
            continue
        count = child_count(p, i + 1, dep + 1)
        if count == 1 and p.defn(i) != HEAD:  # single child => redundant node
            i, k = prune(p, i + 1, dep + 1, n + 1, k)
            continue
        dx = p.dx(i)  # <<dx:8, id:12, depth:12>>
        if count == 0 and dx != HEAD:
            dx = TERM  # leaf node
        p.nodes[k] = dx << 24 | p.id(i) << 12 | dep - n
        p.spans[k] = p.spans[i]
        k += 1
        i += 1
    return (i, k)


def child_count(p, i, d):
    count = 0
    j = len(p.nodes)
    while i < j:
        dep = p.depth(i)
        if dep < d:  # no more children at this depth
            break
        if dep == d:
            if p.fail(i):
                i += 1
                while i < j and p.depth(i) > dep:
                    i += 1
                continue
            count += 1
            if count > 1:  # second child
                return count
        i += 1
    return count


# -- ptree json -----------------------------------------------------------------


def p_tree(parse, i, d) -> tuple[list, int]:
    arr = []
    while i < len(parse.nodes):
        dep = parse.depth(i)
        if dep < d:  # no more children at this depth
            break
        if parse.leaf(i):
            arr.append([parse.name(i), parse.text(i)])
            i += 1
        else:
            children, i1 = p_tree(parse, i + 1, dep + 1)
            arr.append([parse.name(i), children])
            i = i1
    return arr, i


# -- itree json -----------------------------------------------------------------


def i_tree(parse, i, d) -> tuple[list, int]:
    arr = []
    while i < len(parse.nodes):
        dep = parse.depth(i)
        if dep < d:  # no more children at this depth
            break
        start, end = parse.span(i)
        if parse.leaf(i):
            arr.append([parse.name(i), start, end, None])
            i += 1
        else:
            children, i1 = i_tree(parse, i + 1, dep + 1)
            arr.append([parse.name(i), start, end, children])
            i = i1
    return arr, i


# -- ptree line diagram --------------------------------------------------------


def show_tree(parse: Parse) -> str:
    lines = []
    for i in range(0, len(parse.nodes)):
        value = f" {repr(parse.text(i))}" if parse.leaf(i) else ""
        lines.append(f"{indent_bars(parse.depth(i))}{parse.name(i)}{value}")
    return "\n".join(lines)


# -- debug dump of parse tree nodes --------------------------------------------


def dump_tree(parse: Parse, filter=1) -> None:
    print("Node Span    Tree                                  Input...", end="")
    pos = 0  # to fill in any anon text matched between nodes
    for i in range(0, len(parse.nodes)):
        name = parse.name(i)
        fail = parse.fail(i)
        start, end = parse.span(i)
        depth = parse.depth(i)
        if fail:
            if filter == 2 and start == end:
                continue
            if parse.dx(i) & FALL != 0:  # real failure
                name = "!" + name
            else:  # FELL fall back
                name = "-" + name
        anon = ""
        if pos < start:
            anon = f" -> {parse.input[pos:start]!r}"
        pos = end
        print(anon)  # appends '-> anon' to end of line for previous node
        # now for the node print out....
        init = f"{i:3} {start:3}..{end}"
        value = f"{repr(parse.input[start:end])}" if parse.dx(i) & 3 == TERM else ""
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
    if filter == 2:
        print(
            "Note: empty failures have been omitted (use parse.dump(1) to see everything)."
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
    if parse.end_pos == parse.pos:  # parse did not fail
        return "unexpected input, parse ok on input before this"
    first = parse.first  # > peak failure
    top = parse.top  # >= root failure
    if top > first:  # and parse.end_pos > -1:
        return "unexpected ending"
    target = first
    if first < len(parse.nodes) - 1 and top < first:
        target = top
    name = parse.name(target)
    start, end = parse.span(target)
    if start == end:
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
    for i in range(0, len(peg_parse.nodes)):
        if peg_parse.name(i) != "rule":
            continue
        if peg_parse.text(i + 1) != name:
            continue
        lines.append(f"{peg_parse.text(i).strip()}")
    return "\n".join(lines)


def err_report(parse):
    note = "... for more details use: parse.dump(1) ..."
    at_pos = f"at: {max(parse.pos, parse.max_pos)} of: {parse.end}  {note}"
    if parse.code and parse.code.err:
        title = f"*** grammar failed {at_pos}"
        errs = "\n".join(parse.code.err)
        return f"{title}\n{errs}\n{show_pos(parse)}"
    title = f"*** parse failed {at_pos}"
    return f"""{title}\n{show_pos(parse, rule_info(parse))}"""


# == pPEG ptree is compiled into a Code object with instructions for parser ======================


class Code:
    def __init__(self, peg_parse, **opt):
        self.peg_parse = peg_parse  # Parse of Peg grammar (None for boot)
        self.ptree = peg_parse.tree() if peg_parse else opt["boot"]
        self.names = []  # rule name
        self.rules = []  # rule body expr
        self.codes = []  # compiled expr
        self.defs = []  # rule type, defn symbol
        self.extras = opt.get("extras", None)  # extension functions
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

    def parse(self, input, **opt):
        return parser(self, input, **opt)

    def errors(self):
        return "\n".join(self.err)

    def name_id(self, name):
        try:
            idx = self.names.index(name)
            return idx
        except ValueError:
            self.err.append(f"undefined rule: {name}")
            code_rule_defs(self, name, "=", ["extn", "<undefined>"])
            return len(self.names) - 1

    def id_name(self, id):  # TODO handle IndexError
        return self.names[id]


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
        defx = FALL
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
            id = code.name_id(name)
            return ["id", id]
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
        case ["extn", extend]:
            return ["ext", *extra_fn(code, extend)]
        case _:
            raise Exception(f"*** crash: emit: undefined expression: {expr}")


# -- compile extension --------------------------------------


def extra_fn(code, extend):
    args = extend[1:-1].split()  # <command args...>
    if code.extras:
        fn = code.extras.get(args[0])
        if fn:
            return [fn, *args[1:]]
    op, n = extra_fns.get(args[0], (None, 0))  # (fn, n) n = number of id args
    if op is None:
        raise NameError(f"*** Undefined extension: {extend} ...")
    op_args = [op]
    for i in range(1, n + 1):
        op_args.append(code.name_id(args[i]))
    return op_args


# -- escape codes ----------------------


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


def transformer(p: Parse, i, d) -> tuple[list, int]:
    vals = []
    while i < len(p.nodes):
        dep = p.depth(i)
        if dep < d:  # no more children at this depth
            break
        name = p.name(i)
        fn = p.transforms.get(name)
        if p.leaf(i):
            text = p.text(i)
            i += 1
            if fn:
                vals.append(apply(name, fn, text))
            else:
                vals.append([name, text])
        else:
            result, i = transformer(p, i + 1, dep + 1)
            if fn:
                vals.append(apply(name, fn, result))
            else:
                vals.append([name, result])
    if len(vals) == 1:
        return vals[0], i
    return vals, i


def apply(name, fn, args):
    result = None
    try:
        result = fn(args)
    except Exception as err:
        raise SystemExit(f"*** transform failed: {name}({args})\n{err}")
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

peg_code = Code(None, boot=peg_ptree)  # boot compile


def compile(grammar, **fns) -> Code:
    parse = parser(peg_code, grammar)
    if not parse.ok:
        raise SystemExit("*** grammar fault...\n" + err_report(parse))
    code = Code(parse, extras=fns)
    if not code.ok:
        raise SystemExit("*** grammar errors...\n" + code.errors())
    return code


peg_code = compile(peg_grammar)  # to improve grammar error reporting


# == extension functions ==============================================


def dump_fn(parse):  # <dump>
    parse.dump(1)
    return True


def eq_fn(parse, id1, id2):  # <eq x y>
    x = None
    y = None
    n = len(parse.nodes) - 1
    while n >= 0:
        if parse.fail(n):
            n -= 1
            continue
        id = parse.id(n)
        if x is None and id == id1:
            x = n
        if y is None and id == id2:
            y = n
        if x and y:
            dx = parse.depth(x)
            dy = parse.depth(y)
            if x < y:
                if dx <= dy:
                    break
                else:
                    x = None  # try again
            if y < x:
                if dy <= dx:
                    break
                else:
                    y = None  # try again
        n -= 1
    if x is None or y is None:
        return False  # TODO err no x or y found
    if parse.text(x) == parse.text(y):
        return True
    return False


def same_fn(parse, id):  # <same x>
    pos = parse.pos
    n = len(parse.nodes) - 1
    d = parse.deep  # depth(n)
    hits = 0
    while n >= 0:
        k = parse.depth(n)
        # <same name> may be in it's own rule, if so adjust it's depth....
        if hits == 0 and k < d:
            d -= 1
            continue
        if parse.id(n) == id:
            hits += 1
            start, end = parse.span(n)
            if k > d or parse.fail(n) or end > pos:
                n -= 1
                continue
            if pos + end - start > parse.end:
                return False
            for i in range(start, end):
                if parse.input[i] != parse.input[pos]:
                    return False
                pos += 1
            parse.pos = pos
            return True
        n -= 1
    return hits == 0  # no prior to be matched


# -- Python style indent, inset, dedent ----------------


def inset_stack(parse):
    stack = parse.extra_state.get("inset")
    if stack is None:
        stack = [""]
        parse.extra_state["inset"] = stack
    return stack


def indent_fn(parse):
    pos = parse.pos
    while True:
        if pos >= parse.end:
            return False
        char = parse.input[pos]
        if not (char == " " or char == "\t"):
            break
        pos += 1
    stack = inset_stack(parse)
    inset = stack[-1]
    if pos - parse.pos <= len(inset):
        return False
    new_inset = parse.input[parse.pos : pos]
    for i, c in enumerate(inset):  # check same inset prefix
        if inset[i] != new_inset[i]:
            raise ValueError(
                f"Bad <indent> {inset=!r} {new_inset=!r} at {pos} of {parse.end}"
            )
    stack.append(new_inset)
    parse.pos = pos
    return True


def inset_fn(parse):
    inset = inset_stack(parse)[-1]
    pos = parse.pos
    if pos + len(inset) >= parse.end:
        return False
    for x in inset:
        if parse.input[pos] != x:
            return False
        pos += 1
    parse.pos = pos
    return True


def dedent_fn(parse):
    inset_stack(parse).pop()
    return True


# -- function map -------------------

extra_fns = {  # => (fn, n) n = number of id args
    "dump": (dump_fn, 0),
    "undefined": (dump_fn, 0),
    "same": (same_fn, 1),
    "eq": (eq_fn, 2),
    "indent": (indent_fn, 0),
    "inset": (inset_fn, 0),
    "dedent": (dedent_fn, 0),
}
