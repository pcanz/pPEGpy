# pPEGpy -- run with Python 3.10+

from __future__ import annotations  # parser() has a forward ref to Code as type

from dataclasses import dataclass  # for parse tree Node

# -- pPEG grammar ------------------------------------------------------------

peg_grammar = R"""
Peg   = _ rule+
rule  = id _ def _ alt
def   = '=' ':'? / ':' '='?
alt   = seq ('/' _ seq)*
seq   = rep+
rep   = pre sfx? _
pre   = pfx? term
term  = call / quote / class / dot / group / extn
group = '(' _ alt ')'
call  = id _ !def
id    = [a-zA-Z_] [a-zA-Z0-9_-]*
pfx   = [~!&]
sfx   = [+?] / '*' nums?
nums  = min ('..' max)?
min   = [0-9]+
max   = [0-9]*
quote = ['] ~[']* ['] 'i'?
class = '[' ~']'* ']'
dot   = '.'
extn  = '<' ~'>'* '>'
_     = ([ \t\n\r]+ / '#' ~[\n\r]*)*
"""

# -- rule type ------------------------------------------------------------

DEFS = ["=", ":", ":=", "=:"]

EQ = 0  # =    dynamic children: 0 => TERM, 1 => redundant, 2.. => HEAD
ANON = 1  # :    rule name and results not in the parse tree
HEAD = 2  # :=   parent node with any number of children
TERM = 3  # =:   terminal leaf node text match

# -- parse tree nodes -----------------------------------------------------

FAULT = 0xF000  # any flag bit (top nibble in 16 bit id)
FAIL = 0x2000  # rule failed to match
DROP = 0x1000  # back-track seq failed
ID_VAL = 0xFFF  # 12 bit id mask (only expect to need 10 bits)


@dataclass
class Node:
    id: int
    depth: int
    start: int
    end: int
    
    def idx(self):
        return self.id & ID_VAL

    def fault(self):
        return self.id & FAULT != 0
        
    def clone(n: Node):
        return Node(n.id, n.depth, n.start, n.end)

    def __str__(self):
        id = self.id & ID_VAL
        fail = "!" if self.id & FAIL > 0 else " "
        drop = "-" if self.id & DROP > 0 else " "
        return f"{self.start}..{self.end} {self.depth} {fail}{drop} {id}"


# -- Parse context for parser run function ----------------------------------


class Parse:
    def __init__(self, code: Code, input: str, start=-1, end=-1):
        self.ok = True
        self.code = code
        self.input = input
        self.pos = 0 if start < 0 else start
        self.end = len(input) if end < 0 else end

        # tree node: [start, end, id, depth]
        self.trace = []  # trace nodes parse record, debug and error reporting
        self.tree = None  # tree is trace pruned of redundant nodes

        # run state...
        self.anon = False  # True when running anon rules
        self.rule = 0  # current rule idx
        self.deep = 0  # tree depth, deep to avoid name conflict with self.depth()
        self.max_deep = 255  # catch left recursion

        # faults...
        self.index = 0  # parse tree length, for fall-back resets
        self.max_pos = 0  # peak fail pos
        self.max_trace = 0  # peak fail trace index
        self.max_tree = 0  # peak fail tree index (adjusted in prune)

        # expected seq fail candidates ...
        self.max_seq_pos = 0  # seq fail pos
        self.max_seq_op = None  # seq fail op code
        self.expected = None  # max_seq_op at max_pos

        # special case faults ...
        self.fell_short = False  # end_pos = -1  # fell short end pos
        self.empty_alt = None  # (alt, index)

        # state for extensions ...
        self.extra_state = {}

    def __str__(self):
        if self.ok:
            return show_tree(self)
        else:
            return err_report(self)

    # -- parse tree methods ---------------------------

    def name(self, i):  # parse tree node name
        return self.code.names[self.tree[i].id & ID_VAL]

    def text(self, i):  # parse tree node matched text
        return self.input[self.tree[i].start : self.tree[i].end]

    def leaf(self, i):  # is a terminal node?
        if self.code.defs[self.tree[i].id & ID_VAL] == HEAD:
            return False
        if i + 1 >= len(self.tree):
            return True
        return self.tree[i + 1].depth <= self.tree[i].depth

    def ptree(self):
        pt, _ = p_tree(self, 0, 0)
        if not pt:
            return []
        return pt[0]

    def transform(self):
        if not (self.ok and self.tree):
            return (False, self)
        result, _ = transformer(self, 0, 0)
        if len(result) == 1:
            return (True, result[0])
        return (True, result)

    def print_trace(self):
        return dump_trace(self)

    def print_tree(self):
        return dump_tree(self)

    def run(self, id):
        return run(self, ["id", id])


# -- the parser function itself -------------------


def parser(code: Code, input: str, start=-1, end=-1) -> Parse:
    parse = Parse(code, input, start, end)
    if not code.ok:  # bad code..
        parse.ok = False
        return parse
    ok = run(parse, ["id", 0])
    if not ok:
        parse.trace[0].id |= FAIL
    if ok and parse.pos < parse.end:
        parse.fell_short = True
        ok = False
    parse.ok = ok
    if parse.ok:
        parse.tree = prune_tree(parse)  # delete trace faults and redundant nodes
    else:
        parse.tree = prune_trace(parse)  # keeps faults but deletes redundant nodes
    return parse


# -- the run engine that does all the work ----------------------------

def run(parse: Parse, expr: list) -> bool:
    match expr:
        case ["id", idx]:
            # execute anon ids....
            if parse.anon:
                ok = run(parse, parse.code.codes[idx])
                return ok
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
            if parse.deep > parse.max_deep:
                raise SystemExit(f"*** run away recursion, in: {parse.code.names[idx]}")

            # parse tree array - enter node ------------
            index = parse.index  # this node == len(parse.nodes)
            parse.index += 1
            parse.trace.append(Node(idx, depth, pos, 0))

            # -- run -----------------------
            rule = parse.code.codes[idx]
            ok = run(parse, rule)  # ok = True | False
            # ------------------------------

            # -- parse trace:  ---------------
            parse.trace[index].end = parse.pos
            if not ok:
                parse.trace[index].id |= FAIL
                if (
                    parse.pos > pos and parse.pos > parse.max_pos
                ):  # first non-empty max hit
                    parse.max_pos = parse.pos
                    parse.max_trace = index
                    parse.expected = None
                    if parse.max_seq_pos == parse.pos:
                        parse.expected = parse.max_seq_op

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
            pos = parse.pos
            index = parse.index
            depth = parse.deep
            for i, x in enumerate(list):
                if not run(parse, x):
                    if i > 0 and parse.pos >= parse.max_pos:
                        parse.max_seq_pos = parse.pos
                        parse.max_seq_op = x  # candidate for "expected"
                    while index < parse.index:
                        node = parse.trace[index]
                        if node.depth == depth:
                            node.id |= DROP  # or FAIL, required fo inline back-track
                        index += 1
                    return False
            return True

        case ["rept", min, max, exp]:
            pos = parse.pos
            index = parse.index
            if not run(parse, exp):
                if min == 0:
                    parse.pos = pos  # reset
                    return True  # * ?
                return False  # +
            if max == 1:
                return True  # ?
            count = 1
            while True:
                pos = parse.pos
                index = parse.index
                result = run(parse, exp)
                if parse.pos == pos:
                    break
                if not result:
                    parse.pos = pos  # reset loop last try
                    break
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
                parse.trace[index].id |= DROP
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
                parse.trace[index].id |= DROP
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


def prune_tree(parse):
    tree = []
    prune(parse, 0, 0, 0, tree)
    return tree


def prune(p, i, d, n, tree):  #  -> i,  builds tree from trace
    # p:Parse, contains the trace array of nodes
    # i:int = trace index, next candidate trace node
    # d:int = parent.depth
    # n:int = depth reduction to account for deleted ancestor trace nodes
    # tree:array = parse tree built from trace (by appending clones of trace nodes).
    # returns index of next trace node to process (next i)
    j = len(p.trace)
    while i < j:
        dep = p.trace[i].depth
        if dep < d:
            break
        id = p.trace[i].id
        if id & FAULT:  # skip over FAIL or DROP trace nodes
            i += 1
            while i < j and p.trace[i].depth > dep:
                i += 1  # skip over any children...
            continue
        count = child_count(p, i + 1, dep + 1)
        if (
            count == 1 and p.code.defs[id & ID_VAL] != HEAD
        ):  # single child => skip redundant node
            i = prune(p, i + 1, dep + 1, n + 1, tree)
            continue
        node = p.trace[i].clone()
        node.depth = dep - n
        tree.append(node)
        i += 1
    return i


def child_count(p, i, d):
    count = 0
    j = len(p.trace)
    while i < j:
        dep = p.trace[i].depth
        if dep < d:  # no more children at this depth
            break
        if dep == d:
            if p.trace[i].id & FAULT:
                i += 1
                while i < j and p.trace[i].depth > dep:
                    i += 1
                continue
            count += 1
            if count > 1:  # second child
                return count
        i += 1
    return count


# -- prune trace for failed parse -- keeps failures but removes redundant nodes -------

# failures are included in parse tree fault reporting
# redundant nodes are removed to simplify the parse tree for easier reading
# the full trace is too much for fault reporting, but is needed for debugging.


def prune_trace(parse):
    tree = []
    tidy(parse, 0, 0, 0, tree)
    return tree


def tidy(p, i, d, n, tree):  #  -> i,  builds tree from trace
    # p:Parse, contains the trace array of nodes
    # i:int = trace index, next candidate trace node
    # d:int = parent.depth
    # n:int = depth reduction to account for deleted ancestor trace nodes
    # tree:array = parse tree built from trace (by appending clones of trace nodes).
    # returns index of next trace node to process (next i)
    j = len(p.trace)
    while i < j:  # and (dep := p.depth(i)) >= d:
        dep = p.trace[i].depth
        if dep < d:
            break
        node = p.trace[i]
        id = node.id
        if (id & FAULT) and node.start == node.end:  # skip over empty faults
            i += 1  # TODO delete while loop
            while i < j and p.trace[i].depth > dep:
                i += 1  # skip over any children...
            continue
        count = child_trim_count(p, i + 1, dep + 1)
        if (
            count == 1 and p.code.defs[id & ID_VAL] != HEAD
        ):  # single child => skip redundant node
            i = tidy(p, i + 1, dep + 1, n + 1, tree)
            continue
        node = p.trace[i].clone()
        node.depth = dep - n
        if i == p.max_trace:
            p.max_tree = len(tree)
        tree.append(node)
        i += 1
    return i


def child_trim_count(p, i, d):
    count = 0
    j = len(p.trace)
    while i < j:
        dep = p.trace[i].depth
        if dep < d:  # no more children at this depth
            break
        if dep == d:
            node = p.trace[i]
            id = node.id
            if (id & FAULT) and node.start == node.end:  # skip over empty faults
                i += 1  # TODO delete while loop
                while i < j and p.trace[i].depth > dep:
                    i += 1  # skip over any children...
                continue
            count += 1
            if count > 1:  # second child
                return count
        i += 1
    return count

# -- show trace node --------------------------------------------------------

def show_trace(parse):  # TODO delete all this...
    for i in range(0,len(parse.trace)):
        show_trace_node(parse, i)
        
def show_trace_node(parse, index):
    node = parse.trace[index]
    name = parse.code.names[node.id & ID_VAL]
    fail = 0 if node.id & FAIL == 0 else 1
    drop = 0 if node.id & DROP == 0 else 1
    print(f"{name} {fail=}{drop} {node.start}..{node.end}")
    

# -- ptree json -----------------------------------------------------------------


def p_tree(parse, i, d) -> tuple[list, int]:
    arr = []
    while i < len(parse.tree):
        dep = parse.tree[i].depth
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


# -- ptree line diagram --------------------------------------------------------


def show_tree(parse: Parse) -> str:
    lines = []
    for i in range(0, len(parse.tree)):
        value = f" {repr(parse.text(i))}" if parse.leaf(i) else ""
        lines.append(f"{indent_bars(parse.tree[i].depth)}{parse.name(i)}{value}")
    return "\n".join(lines)


# -- print debug dump of trace nodes --------------------------------------------


def dump_trace(parse: Parse) -> None:
    print("   Span    Trace...")
    pos = 0  # input index last displayed
    i = 0  # trace node index
    while i < len(parse.trace):
        start = parse.trace[i].start
        end = parse.trace[i].end
        depth = parse.trace[i].depth
        next_depth = depth_of(parse, i + 1)
        if pos < start:
            value = format_span(parse.input, pos, start)
            print(f"{pos:>4}..{start:<4d} {indent_bars(depth)}{value}")
            pos = start
        dump_node(parse, i, start, end, depth)
        if pos < end and depth >= next_depth:
            pos = end
        while depth > next_depth:  # fill in text gap ...
            parent = parent_of(parse, i, depth)
            parent_end = parse.trace[parent].end
            if pos < parent_end:
                value = format_span(parse.input, pos, parent_end)
                print(f"{pos:>4}..{parent_end:<4d} {indent_bars(depth)}{value}")
                pos = parent_end
            depth -= 1
        i += 1
    eot = parse.end
    if pos < eot:  # show end text after pos: !'...end-text...'
        max_node = parse.trace[parse.max_trace]
        depth = max_node.depth
        value = f"\x1b[1;41m!{format_span(parse.input, pos, eot)}\x1b[0m"
        print(f"{pos:>4}..{eot:<4d} {indent_bars(depth)}{value}")


def dump_node(parse, i, start, end, depth):
    id = parse.trace[i].id
    if id & FAIL:
        if start == end:
            return  # skip empty fails
        name = "\x1b[1;31m!" + parse.code.names[id & ID_VAL] + "\x1b[0m"
    elif id & DROP:
        name = "\x1b[1;31m-" + parse.code.names[id & ID_VAL] + "\x1b[0m"
    else:
        name = parse.code.names[id]
    value = format_span(parse.input, start, end)
    if i + 1 < len(parse.trace) and parse.trace[i + 1].depth > depth:
        value = "\x1b[2;38;5;253m" + value + "\x1b[0m"
    print(f"{start:>4}..{end:<4d} {indent_bars(depth)}{name} {value}")


def format_span(input, start, end) -> str:
    if end - start < 50:
        return f"{repr(input[start:end])}"
    else:
        return f"{repr(input[start : start + 30])} ... {repr(input[start + 30 : end])}"


def parent_of(parse, i, d):
    while i > 0:
        i -= 1
        if parse.trace[i].depth < d:
            return i
    return 0


def depth_of(parse, i):
    if i < len(parse.trace):
        return parse.trace[i].depth
    return 0


# -- dump tree -----------------------------


def dump_tree(parse: Parse) -> None:
    for i in range(0, len(parse.tree)):
        dump_tree_node(parse, i)
    eot = parse.end
    pos = parse.max_pos
    if pos == 0:  # no max fail ...
        pos = parse.tree[-1].end
    if pos < eot:
        max_node = parse.tree[parse.max_tree]
        depth = max_node.depth
        value = format_span(parse.input, pos, eot)
        print(f"{indent_bars(depth)}\x1b[1;41m{value[1:-1]}\x1b[0m")


def dump_tree_node(parse, i):
    node = parse.tree[i]
    id = node.id
    if (id & FAULT) and node.start == node.end:
        return  # skip empty fails
    # if id & FAIL:
    #     name = "\x1b[1;31m!" + parse.code.names[id & ID_VAL] + "\x1b[0m"
    # elif id & DROP:
    #     name = "\x1b[1;31m-" + parse.code.names[id & ID_VAL] + "\x1b[0m"
    # else:
    #     name = parse.code.names[id]
    name = parse.code.names[id & ID_VAL]
    value = ""
    if i + 1 == len(parse.tree) or parse.tree[i + 1].depth <= node.depth:
        value = format_span(parse.input, node.start, node.end)
    print(f"{indent_bars(node.depth)}{name} {value}")


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
    if parse.fell_short:  # end_pos == parse.pos:  # parse did not fail
        return "unexpected input, parse ok on input before this"
    note = " failed"
    if parse.expected:
        note = f" failed, expected: {code_show(parse, parse.expected)}"
    node = parse.trace[parse.max_trace]
    name = parse.code.names[node.id & ID_VAL]
    return src_map(parse, name, note)


def code_show(parse, op):
    match op:
        case ["quote", str, case]:
            quo = "'" + str + "'"
            return quo if not case else quo + "i"
        case ["id", idx]:
            return parse.code.names[idx]
        case _:
            return op


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
        return f"{msg}\n    alternative '{parse.name(opt[1])}' was an empty '' match!"
    return f"{msg}\n    alternative {i} was an empty '' match!"


def err_report(parse):
    at_pos = f"at: {max(parse.pos, parse.max_pos)} of: {parse.end}"
    if parse.code.err:
        title = f"*** grammar failed {at_pos}"
        errs = "\n".join(parse.code.err)
        return f"{title}\n{errs}\n{show_pos(parse)}"
    parse.print_tree()
    title = f"*** parse failed {at_pos}" + empty_alt_report(parse)
    return f"""{title}\n{show_pos(parse, rule_info(parse))}"""


# == pPEG ptree is compiled into a Code object with instructions for parser ======================


class Code:
    def __init__(self, peg_parse, *, boot=None, transforms={}, extras={}):
        self.peg_parse = peg_parse  # Parse of Peg grammar (None for boot)
        self.ptree = peg_parse.ptree() if peg_parse else boot
        self.names = []  # rule name
        self.rules = []  # rule body expr
        self.codes = []  # compiled expr
        self.defs = []  # rule defn -> defx: EQ|ANON|HEAD|TERM
        self.extras = extras  # extension functions
        self.transforms = transforms  # transform fns 'rule':fn, or 'rule:':fn
        self.err = []
        self.ok = True
        self.compose()

    def compose(self):
        define_rules(self)
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

    def parse(self, input, start=-1, end=-1):
        return parser(self, input, start, end)

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

    def read(self, input):
        return self.parse(input).transform()


# -- compile Parse into Code parser instructions -----------------------------------


def define_rules(code: Code) -> None:
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
        code.err.append(f"undefined: {name} {defn}")
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
        e = f"*** Undefined extension: {extend}"
        code.err.append(e)
        return ["err", e]
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
        dep = p.tree[i].depth
        if dep < d:  # no more children at this depth
            break
        if p.leaf(i):
            vals.append(apply_type(p, i, p.text(i)))
            i += 1
        else:
            result, j = transformer(p, i + 1, dep + 1)
            vals.append(apply_type(p, i, result))
            i = j
    return vals, i


def apply_type(p, i, val):
    try:
        name = p.name(i)
        fn, con = transform_fn(p, name)
        if not fn:  # default, no transform
            return [name, val]
        result = fn(val)
        if con == ":":
            return [name, result]
        return result
    except Exception as err:
        raise SystemExit(f"*** transform failed: {name}={fn.__name__}({val})\n{err}")


def transform_fn(p, name):
    fn = p.code.transforms.get(name)
    if fn:
        return fn, "."
    fn = p.code.transforms.get(name + ":")
    if fn:
        return fn, ":"
    return None, "."


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

peg_code = Code(None, boot=peg_ptree)  # peg boot grammar


def compile(grammar, transforms={}, extras={},) -> Code:
    parse = parser(peg_code, grammar)
    if not parse.ok:
        raise SystemExit("*** grammar fault...\n" + err_report(parse))
    code = Code(parse, transforms=transforms, extras=extras)
    if not code.ok:
        raise SystemExit("*** grammar errors...\n" + code.errors())
    return code


peg_code = compile(peg_grammar)  # bootstrap full grammar
