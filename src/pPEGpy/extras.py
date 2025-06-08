# -- compile extension --------------------------------------


def extra_fn(code, extend):
    args = extend[1:-1].split()  # <command args...>
    op, n = extra_fns.get(args[0], (None, 0))  # (fn, n)
    if op is None:
        raise NameError(f"*** Undefined extension: {extend} ...")
    op_args = [op]
    for i in range(1, n + 1):
        op_args.append(code.name_id(args[i]))
    return op_args


# == extension functions ==============================================


def dump_fn(parse):  # <dump>
    parse.dump(1)
    return True


def eq_fn(parse, id1, id2):  # <eq x y>
    x = None
    y = None
    n = len(parse.starts) - 1
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
    n = len(parse.starts) - 1
    d = parse.deep  # depth(n)
    hits = 0
    while n >= 0:
        k = parse.depth(n)
        # <@name> may be in it's own rule, if so adjust it's depth....
        if hits == 0 and k < d:
            d -= 1
            continue
        if parse.id(n) == id:
            hits += 1
            if k > d or parse.fail(n) or parse.ends[n] > pos:
                n -= 1
                continue
            start = parse.starts[n]
            end = parse.ends[n]
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


# -- Python style indent, inset, undent ----------------


def indent_fn(parse):  # TODO parse.inset => parse.extra_state['inset']
    pos = parse.pos
    if pos >= parse.end:
        return False
    char = parse.input[pos]
    pos += 1
    if char == " ":
        while parse.input[pos] == " ":
            pos += 1
    elif char == "\t":
        while parse.input[pos] == "\t":
            pos += 1
    else:
        return False
    inset = parse.inset[-1]
    if len(inset) >= pos - parse.pos:
        return False
    parse.inset.append(parse.input[parse.pos : pos])
    parse.pos = pos
    return True


def inset_fn(parse):
    inset = parse.inset[-1]
    pos = parse.pos
    if pos + len(inset) >= parse.end:
        return False
    for x in inset:
        if parse.input[pos] != x:  # TODO err report
            return False
        pos += 1
    parse.pos = pos
    return True


def undent_fn(parse):
    if len(parse.inset) < 1:  # TODO err
        print("*** <undent> err, empty inset stack...")
        return False
    parse.inset.pop()
    return True


# -- function map -------------------

extra_fns = {
    "dump": (dump_fn, 0),
    "undefined": (dump_fn, 0),
    "same": (same_fn, 1),
    "eq": (eq_fn, 2),
    "indent": (indent_fn, 0),
    "inset": (inset_fn, 0),
    "undent": (undent_fn, 0),
}
