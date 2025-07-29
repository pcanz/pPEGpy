# pPEGpy -- run with Python 3.10+

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
# pPEGpy-19.py  2025-06-19 => PyPi 0.3.12
# - add trans() function to apply transforms to core parse tree
# - FAIL flag only, remove FALL and FELL flags
# + add more op-tests.py, peg-test.py tests
# pPEGpy-20.py  2025-06-28 => PyPi 0.3.13
# - tree nodes: [start,end,id,depth]
# - revise error report
# - remove trans method
# - add transform fn arity, 1 fn(val) or 3 fn(p,i,val)
# pPEGpy-21.py  2025-07-01 => PyPi 0.3.14
# - move all extensions external -- extras.py
# - parse start=i option, no error for a prefix match
# - empty leaf => trace.pop()
# - dump ignore DROP flag, no filter
# - print trace before error report
# pPEGpy-22.py  2025-07-04 => PyPi 0.3.15
# - seq fall-back only DROP siblings (FAULT=FAIL|DROP covers children)
# - dump shows DROP flag (if not FAIL)
# + parse.empty_alt TODO better err_report
# - fix err_report when FIRST >= len(trace) (empty node fail at end)
# pPEGpy-23.py  2025-07-07 => PyPi 0.3.16
# - simplify state to flags, use p.code.defs for defx
# pPEGpy-24.py  2025-07-16 => PyPi 0.3.17
# - fix DROP to OR with FAIL
# - add first_depth and top_count to improve err report
# - add trim=True to dump() to elide failed nodes that are empty

# TODO
# - source code map
# - binary (not Unicode)  <binary>  and/or  compile(..., ASCII=True)??

# - pPEGpy repo: examples, tests, ...

from __future__ import annotations  # parser() has a forward ref to Code as type

import inspect  # for transform method to check fn arity

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

# -- rule types ------------------------------------------------------------

DEFS = ["=", ":", ":=", "=:"]

EQ = 0  # =    dynamic children: 0 => TERM, 1 => redundant, >1 => HEAD
ANON = 1  # :    rule name and results not in the parse tree
HEAD = 2  # :=   parent node with any number of children
TERM = 3  # =:   terminal leaf node text match

# -- parse state flags -----------------------------------------------------

OK = 0  # all clear
INIT = 1  # id call entered
DROP = 8  # -    cancel flag
FAIL = 16  # !    fail flag

# -- Parse context for parser run function ----------------------------------


class Parse:
    def __init__(self, code: Code, input: str, start=-1, end=-1, **opt):
        self.ok = True
        self.code = code
        self.input = input
        self.pos = 0 if start < 0 else start
        self.end = len(input) if end < 0 else end  # opt.get("end", len(input))

        # tree node: [start, end, id, depth]
        self.state = []  # trace state bit flags: OK|INIT|DROP|FAIL
        self.trace = []  # trace nodes retained for debug and error reporting
        self.tree = None  # tree is trace pruned of failed and redundant nodes

        # run state...
        self.anon = False  # True when running anon rules
        self.rule = 0
        self.deep = 0  # tree depth, deep to avoid name conflict with self.depth()
        self.max_depth = 255  # catch left recursion

        # faults...
        self.index = 0  # parse tree length, for fall-back resets
        self.max_pos = -1  # peak fail
        self.first = -1  # node at max pos failure
        self.top = -1  # parent of first node

        self.first_depth = 0
        self.top_count = 0

        self.end_pos = -1  # fell short end pos
        self.empty_alt = None  # (alt, index)
        self.debug = []

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

    def id(self, i, trace=False):  # [start, end, id, depth]
        if trace or self.tree is None:
            return self.trace[i][2]
        return self.tree[i][2]

    def name(self, i, trace=False):  # parse tree node name
        return self.code.names[self.id(i, trace)]

    def defx(self, i, trace=False):  # rule defx: EQ|ANON|HEAD|TERM
        return self.code.defs[self.id(i, trace)]

    def span(self, i, trace=False):  # [start, end, id, depth]
        if trace or self.tree is None:
            return (self.trace[i][0], self.trace[i][1])
        return (self.tree[i][0], self.tree[i][1])

    def text(self, i, trace=False):  # parse tree node matched text
        start, end = self.span(i, trace)
        return self.input[start:end]

    def size(self, trace=False):
        if trace or self.tree is None:
            return len(self.trace)
        return len(self.tree)

    def depth(self, i, trace=False):  # [start, end, id, depth]
        if trace or self.tree is None:
            return self.trace[i][3]
        return self.tree[i][3]  # depth of node in parse tree

    def leaf(self, i, trace=False):  # is a terminal node?
        if trace or self.tree is None:
            return self.state[i] == TERM
        if i + 1 < len(self.tree) and self.depth(i + 1) > self.depth(i):
            return False
        return True

    def next(self, i, trace=False):  # next node in parse tree
        nodes = self.tree
        if trace or nodes is None:
            nodes = self.trace
        d = self.depth(i)
        while i < len(nodes) - 1 and self.depth(i + 1) > d:
            i += 1
        return i + 1  # next node at same depth or deeper

    def status(self, i, trace=True):  # trace state flags OK|INIT|DROP|FAIL
        if trace or self.tree is None:
            return self.state[i]
        print(f"! status {trace=} called on pruned tree")
        return OK  # pruned self.tree has no state

    def fault(self, i, trace=True):  # trace state flags OK|INIT|DROP|FAIL
        if trace or self.tree is None:
            return self.state[i] != OK
        print("! fault called on pruned tree")
        return FAIL  # pruned self.tree has no state

    def ptree(self, trace=False):
        if trace or self.tree is None:
            return []  # no pruned tree
        ptree, _ = p_tree(self, 0, 0)
        if not ptree:
            return []
        return ptree[0]

    def itree(self, trace=False):
        if trace or self.tree is None:
            return []  # no pruned tree
        itree, _ = i_tree(self, 0, 0)
        if not itree:
            return []
        return itree[0]

    def dump(self):
        return dump_tree(self, trace=True)

    def run(self, id):
        return run(self, ["id", id])

    def transform(self, **fns):
        if self.tree is None:
            return []  # no pruned tree
        self.transforms = fns
        result, _ = transformer(self, 0, 0)
        return result


# -- the parser function itself -------------------


def parser(code: Code, input: str, start=-1, end=-1, **opt) -> Parse:
    parse = Parse(code, input, start, end, **opt)
    if not code.ok:
        parse.ok = False
        return parse
    ok = run(parse, ["id", 0])
    if ok and start == -1 and parse.pos < len(parse.input):
        parse.end_pos = parse.pos
        ok = False
    parse.ok = ok
    if opt.get("debug"):
        parse.dump()
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
            parse.rule = idx
            pos = parse.pos
            depth = parse.deep
            parse.deep += 1
            if parse.deep > parse.max_depth:
                raise SystemExit(f"*** run away recursion, in: {parse.code.names[idx]}")

            # parse tree array - enter node ------------
            index = parse.index  # this node == len(parse.nodes)
            parse.index += 1
            parse.state.append(INIT)
            parse.trace.append([pos, 0, idx, depth])

            # -- run -----------------------
            rule = parse.code.codes[idx]
            ok = run(parse, rule)  # ok = True | False
            # ------------------------------

            # -- parse trace:  [start, end, id, depth, defx] ----------
            parse.trace[index][1] = parse.pos

            if ok:
                parse.state[index] = OK
            else:
                parse.state[index] = FAIL
                if parse.pos >= parse.max_pos:
                    parse.top = index  # parent of peak failure
                    if parse.trace[index][3] == parse.first_depth:
                        parse.top_count += 1
                    if parse.pos > parse.max_pos:
                        parse.max_pos = parse.pos
                        parse.top_count = 0
                        parse.first = index  # root of peak failure
                        parse.first_depth = parse.trace[index][3]

            parse.deep -= 1
            return ok

        case ["alt", list]:
            pos = parse.pos
            max = pos
            for i, x in enumerate(list):
                if run(parse, x):
                    if pos == parse.pos and i != len(list) - 1:  # for err report
                        parse.empty_alt = (list, i)
                    return True
                if parse.pos > pos:
                    max = parse.pos
                parse.pos = pos  # reset (essential)
            parse.pos = max  # to be caught in id
            return False

        case ["seq", list]:
            index = parse.index
            depth = parse.deep
            for i, x in enumerate(list):
                if not run(parse, x):
                    while index < parse.index:  # parse tree fall-back
                        if parse.trace[index][3] == depth:
                            parse.state[index] |= DROP
                        index += 1
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
            while index < parse.index:  # parse tree fall-back
                parse.state[index] |= DROP
                index += 1
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
            while index < parse.index:  # parse tree fall-back
                parse.state[index] |= DROP
                index += 1
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
    tree = []
    prune(parse, 0, 0, 0, tree)
    parse.tree = tree


def prune(p, i, d, n, tree):  #  -> i,  builds tree from trace
    # d = depth of parent node, n = delta depth (deleted redundant nodes)
    # read from i: with depth: dep  ==>  append to tree with depth: dep-n
    j = len(p.trace)
    while i < j and (dep := p.depth(i)) >= d:
        if p.fault(i):
            i += 1
            while i < j and p.depth(i) > dep:
                i += 1  # skip over any children...
            continue
        count = child_count(p, i + 1, dep + 1)
        if count == 1 and p.defx(i) != HEAD:  # single child => redundant node
            i = prune(p, i + 1, dep + 1, n + 1, tree)
            continue
        start, end, idx, _ = p.trace[i]  # adjust depth for deleted nodes
        tree.append([start, end, idx, dep - n])  # append to pruned tree
        i += 1
    return i


def child_count(p, i, d):
    count = 0
    j = len(p.trace)
    while i < j:
        dep = p.depth(i)
        if dep < d:  # no more children at this depth
            break
        if dep == d:
            if p.fault(i):
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
    while i < len(parse.tree):
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
    while i < len(parse.tree):
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
    for i in range(0, len(parse.tree)):
        value = f" {repr(parse.text(i))}" if parse.leaf(i) else ""
        lines.append(f"{indent_bars(parse.depth(i))}{parse.name(i)}{value}")
    return "\n".join(lines)


# -- debug dump of parse tree nodes --------------------------------------------


def dump_tree(parse: Parse, trace=True, trim=True) -> None:
    print("Node  Span    Tree                                 Input...", end="")
    pos = 0  # to fill in any anon text matched between nodes
    for i in range(0, parse.size()):
        name = parse.name(i, trace)
        state = parse.status(i, trace) if trace else OK  # dump tree
        start, end = parse.span(i, trace)
        depth = parse.depth(i, trace)
        if state & FAIL != 0:
            if trim and start == end:
                continue
            name = "!" + name
        elif state & DROP != 0:
            name = "-" + name
        elif state != OK:  # should not happen
            name = "?" + name
        anon = ""
        if pos < start:
            anon = f" -> {parse.input[pos:start]!r}"
        pos = end
        print(anon)  # appends '-> anon' to end of line for previous node
        # now for the node print out....
        init = f"{i:3} {start:3}..{end}"
        value = f"{repr(parse.input[start:end])}" if parse.leaf(i) else ""
        report = f"{init:12}  {indent_bars(depth)}{name} {value}"
        etc = ""  # truncate long lines...
        if end - start > 30:
            end = start + 30
            etc = "..."
        text = f"{parse.input[start:end]!r}{etc}"
        print(f"{report:65} {text}", end="")
        # next loop: print(anon) to append -> text at end of this line
    anon = ""  # final last node anon text...
    if pos < parse.max_pos:
        anon = f" -> {parse.input[pos : parse.max_pos]!r}"
        pos = parse.max_pos
    anon += f" <> {parse.input[pos:]!r}"
    if len(anon) > 80:
        anon = anon[0:50] + "..."
    print(anon + "\n")


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
    return f"{prior}{left}{parse.input[pos:eol]}\n{' ' * len(left)}^ {info}"


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
    if top > first:
        return "unexpected ending"
    target = first
    if parse.top_count > 0 and parse.first_depth > 0:
        target -= 1  # find parent of alt fails at same depth
        while parse.depth(target) >= parse.first_depth:
            target -= 1
    name = parse.name(target, trace=True)
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
    for i in range(0, len(peg_parse.tree) - 1):
        if peg_parse.name(i) != "rule":
            continue
        if peg_parse.text(i + 1) == name:
            lines.append(f"{peg_parse.text(i).strip()}")
            break
    return "\n".join(lines)


def empty_alt_report(parse):
    if parse.empty_alt is None:
        return ""
    list, i = parse.empty_alt
    opt = list[i]
    msg = f"\n*** in: {list}"
    if opt[0] == "id":
        return f"{msg}\n    alternative '{parse.name(opt[1], trace=True)}' was an empty '' match!"
    return f"{msg}\n    alternative {i} was an empty '' match!"


def err_report(parse, trace=True):
    at_pos = f"at: {max(parse.pos, parse.max_pos)} of: {parse.end}"
    if parse.code.err:
        title = f"*** grammar failed {at_pos}"
        errs = "\n".join(parse.code.err)
        return f"{title}\n{errs}\n{show_pos(parse)}"
    if trace:
        parse.dump()
    title = f"*** parse failed {at_pos}" + empty_alt_report(parse)
    return f"""{title}\n{show_pos(parse, rule_info(parse))}"""


# == pPEG ptree is compiled into a Code object with instructions for parser ======================


class Code:
    def __init__(self, peg_parse, __boot__=None, **extras):
        self.peg_parse = peg_parse  # Parse of Peg grammar (None for boot)
        self.ptree = peg_parse.ptree() if peg_parse else __boot__
        self.names = []  # rule name
        self.rules = []  # rule body expr
        self.codes = []  # compiled expr
        self.defs = []  # rule defn -> defx: EQ|ANON|HEAD|TERM
        self.extras = extras  # opt.get("extras", None)  # extension functions
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

    def parse(self, input, start=-1, end=-1, **opt):
        return parser(self, input, start, end, **opt)

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
        defx = EQ
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
    extras = code.extras
    op = extras.get(args[0], None)
    if op is None:
        code.err.append(f"*** Undefined extension: {extend} ...")
        return ["err", f"*** Undefined extension: {extend} ..."]
    return [op, args]


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
    while i < len(p.tree):
        dep = p.depth(i)
        if dep < d:  # no more children at this depth
            break
        name = p.name(i)
        fn = p.transforms.get(name)
        if p.leaf(i):
            text = p.text(i)
            if fn:
                vals.append(apply(name, fn, p, i, text))
            else:
                vals.append([name, text])
            i += 1
        else:
            result, j = transformer(p, i + 1, dep + 1)
            if fn:
                vals.append(apply(name, fn, p, i, result))
            else:
                vals.append([name, result])
            i = j
    if len(vals) == 1:
        return vals[0], i
    return vals, i


def apply(name, fn, p, i, args):
    result = None
    arity = fn_arity(fn)
    try:
        if arity == 1:
            result = fn(args)
        elif arity == 3:
            result = fn(p, i, args)
        else:
            note = "1: fn(value) or 3: fn(parse, index, value)"
            raise SystemExit(
                f"*** transform {name}={fn.__name__} has {arity=}, expected: {note} ..."
            )
    except Exception as err:
        raise SystemExit(f"*** transform failed: {name}={fn.__name__}({args})\n{err}")
    return result


def fn_arity(fn) -> int:
    try:
        sig = inspect.signature(fn)
        arity = len(sig.parameters)
        if arity > 1 and str(sig).split(", ")[1] == "/":
            arity = 1
        return arity
    except ValueError:
        return 1  # Python built-in? assume arity == 1


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

peg_code = Code(None, __boot__=peg_ptree)  # boot compile


def compile(grammar, **opt) -> Code:
    parse = parser(peg_code, grammar)
    if not parse.ok:
        raise SystemExit("*** grammar fault...\n" + err_report(parse, trace=False))
    code = Code(parse, **opt)
    if not code.ok:
        raise SystemExit("*** grammar errors...\n" + code.errors())
    return code


peg_code = compile(peg_grammar)  # to improve grammar error reporting
