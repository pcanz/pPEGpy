
# == extension functions ==============================================

def dump(parse):  # <dump>
    parse.print_trace()
    return True


def eq(parse, args):  # <eq x y>
    id1 = parse.code.name_id(args[1])
    id2 = parse.code.name_id(args[2])
    x = None
    y = None
    n = len(parse.trace) - 1
    while n >= 0:
        node = parse.trace[n]
        if node.fault(): #parse.fault(n) != 0:
            n -= 1
            continue
        id = node.idx()
        if x is None and id == id1:
            x = n
        if y is None and id == id2:
            y = n
        if x and y:
            xnode = parse.trace[x]
            ynode = parse.trace[y]
            dx = xnode.depth  # parse.depth(x)
            dy = ynode.depth  # parse.depth(y)
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
    xnode = parse.trace[x]
    xstart = xnode.start
    xend = xnode.end
    ynode = parse.trace[y]
    ystart = ynode.start
    yend = ynode.end
    if xend-xstart != yend-ystart:
        return False
    for i in range(0, xend-xstart):
        if parse.input[xstart+i] != parse.input[ystart+i]:
            return False
    return True


def same(parse, args):  # <same x>
    id = parse.code.name_id(args[1])
    pos = parse.pos
    n = len(parse.trace) - 1
    d = parse.deep  # depth(n)
    hits = 0
    while n >= 0:
        node = parse.trace[n]
        k = node.depth
        # <same name> may be in it's own rule, if so adjust it's depth....
        if hits == 0 and k < d:
            d -= 1
            continue
        if node.idx() == id:
            hits += 1
            start = node.start
            end = node.end
            # if k > d or parse.fault(n) != 0 or end > pos:
            if k > d or node.fault() or end > pos:
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

# -- <match rule> -----------------------------------

def match(parse, args): # <match rule>
    node = parse.trace[-1]
    pos = parse.pos
    if node.start == pos:
        return True # nothing to match
    id = parse.code.name_id(args[1])
    return parse.match(id, node)


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
        "eq": eq,
        "match": match,
        "indent": indent,
        "inset": inset,
        "dedent": dedent,
    }
