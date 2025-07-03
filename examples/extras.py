# == extension functions ==============================================


def dump(parse):  # <dump>
    parse.dump(1)
    return True


def eq(parse, args):  # <eq x y>
    id1 = parse.code.name_id(args[1])
    id2 = parse.code.name_id(args[2])
    x = None
    y = None
    n = len(parse.trace) - 1
    while n >= 0:
        if parse.fault(n) != 0:
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
            elif y < x:
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


def same(parse, args):  # <same x>
    id = parse.code.name_id(args[1])
    pos = parse.pos
    n = len(parse.trace) - 1
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
            if k > d or parse.fault(n) != 0 or end > pos:
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


def fork(parse, args):  # <fork x y>
    x = parse.code.name_id(args[1])
    parse.link(x)  # link node for x
    y = parse.code.name_id(args[2])
    return parse.run(y)


# -- Python style indent, inset, dedent ----------------


def inset_stack(parse):
    stack = parse.extra_state.get("inset")
    if stack is None:
        stack = [""]
        parse.extra_state["inset"] = stack
    return stack


def indent(parse):
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


def inset(parse):
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


def dedent(parse):
    inset_stack(parse).pop()
    return True


# -- function map -------------------


def extensions():
    return {
        "dump": dump,
        "undefined": dump,
        "same": same,
        "fork": fork,
        "eq": eq,
        "indent": indent,
        "inset": inset,
        "dedent": dedent,
    }
