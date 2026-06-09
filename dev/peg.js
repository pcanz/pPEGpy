// pPEGpy -- JavaScript translation of peg.py (ES2020+)

// -- pPEG grammar -------------------------------------------------------

const peg_grammar = `
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
_     = ([ \\t\\n\\r]+ / '#' ~[\\n\\r]*)*
`;

// -- rule type ----------------------------------------------------------

const DEFS = ["=", ":", ":=", "=:"];
const EQ = 0, ANON = 1, HEAD = 2, TERM = 3;

// -- parse tree nodes ---------------------------------------------------

const FAULT  = 0xF000;
const FAIL   = 0x2000;
const DROP   = 0x1000;
const ID_VAL = 0x0FFF;

class Node {
    constructor(id, depth, start, end) {
        this.id    = id;
        this.depth = depth;
        this.start = start;
        this.end   = end;
    }
    idx()   { return this.id & ID_VAL; }
    fault() { return (this.id & FAULT) !== 0; }
    clone() { return new Node(this.id, this.depth, this.start, this.end); }
    toString() {
        const id   = this.id & ID_VAL;
        const fail = (this.id & FAIL) > 0 ? "!" : " ";
        const drop = (this.id & DROP) > 0 ? "-" : " ";
        return `${this.start}..${this.end} ${this.depth} ${fail}${drop} ${id}`;
    }
}

// -- Parse context for parser run function ------------------------------

class Parse {
    constructor(code, input, start = -1, end = -1) {
        this.ok    = true;
        this.code  = code;
        this.input = input;
        this.pos   = start < 0 ? 0 : start;
        this.end   = end   < 0 ? input.length : end;

        this.trace = [];
        this.tree  = null;

        this.anon     = false;
        this.rule     = 0;
        this.deep     = 0;
        this.max_deep = 255;

        this.index     = 0;
        this.max_pos   = 0;
        this.max_trace = 0;
        this.max_tree  = 0;

        this.max_seq_pos = 0;
        this.max_seq_op  = null;
        this.expected    = null;

        this.fell_short = false;
        this.empty_alt  = null;

        this.extra_state = {};
    }

    toString() {
        return this.ok ? show_tree(this) : err_report(this);
    }

    name(i)  { return this.code.names[this.tree[i].id & ID_VAL]; }
    text(i)  { return this.input.slice(this.tree[i].start, this.tree[i].end); }

    leaf(i) {
        if (this.code.defs[this.tree[i].id & ID_VAL] === HEAD) return false;
        if (i + 1 >= this.tree.length) return true;
        return this.tree[i + 1].depth <= this.tree[i].depth;
    }

    ptree() {
        const [pt] = p_tree(this, 0, 0);
        if (!pt || pt.length === 0) return [];
        return pt[0];
    }

    transform() {
        if (!(this.ok && this.tree)) return [false, this];
        const [result] = transformer(this, 0, 0);
        if (result.length === 1) return [true, result[0]];
        return [true, result];
    }

    print_trace() { dump_trace(this); }
    print_tree()  { dump_tree(this); }

    run(id) { return run(this, ["id", id]); }

    match(id, node) {
        const pos = this.pos;
        const end = this.end;
        this.end = this.pos;
        this.pos = node.start;
        const result = this.run(id);
        const pos1 = this.pos;
        this.end = end;
        this.pos = pos;
        return result && pos1 === pos;
    }
}

// -- the parser function itself -----------------------------------------

function parser(code, input, start = -1, end = -1) {
    const parse = new Parse(code, input, start, end);
    if (!code.ok) {
        parse.ok = false;
        return parse;
    }
    let ok = run(parse, ["id", 0]);
    if (!ok) parse.trace[0].id |= FAIL;
    if (ok && parse.pos < parse.end) {
        parse.fell_short = true;
        ok = false;
    }
    parse.ok = ok;
    parse.tree = ok ? prune_tree(parse) : prune_trace(parse);
    return parse;
}

// -- the run engine that does all the work ------------------------------

function run(parse, expr) {
    const op = expr[0];

    if (op === "id") {
        const idx = expr[1];
        if (parse.anon) {
            return run(parse, parse.code.codes[idx]);
        }

        const defx = parse.code.defs[idx];
        if (defx === ANON) {
            parse.anon = true;
            const ok = run(parse, parse.code.codes[idx]);
            parse.anon = false;
            return ok;
        }

        parse.rule = idx;
        const pos   = parse.pos;
        const depth = parse.deep;
        parse.deep++;
        if (parse.deep > parse.max_deep) {
            throw new Error(`*** run away recursion, in: ${parse.code.names[idx]}`);
        }

        const index = parse.index;
        parse.index++;
        parse.trace.push(new Node(idx, depth, pos, 0));

        if (defx === TERM) parse.anon = true;
        let ok = run(parse, parse.code.codes[idx]);
        if (defx === TERM) parse.anon = false;

        parse.trace[index].end = parse.pos;
        if (!ok) {
            parse.trace[index].id |= FAIL;
            if (parse.pos > pos && parse.pos > parse.max_pos) {
                parse.max_pos   = parse.pos;
                parse.max_trace = index;
                parse.expected  = null;
                if (parse.max_seq_pos === parse.pos) {
                    parse.expected = parse.max_seq_op;
                }
            }
        }

        parse.deep--;
        return ok;
    }

    if (op === "alt") {
        const list = expr[1];
        let pos = parse.pos;
        let max = pos;
        for (let i = 0; i < list.length; i++) {
            if (run(parse, list[i])) {
                if (pos === parse.pos && i !== list.length - 1) {
                    parse.empty_alt = [list, i];
                }
                return true;
            }
            if (parse.pos > pos) max = parse.pos;
            parse.pos = pos;
        }
        parse.pos = max;
        return false;
    }

    if (op === "seq") {
        const list  = expr[1];
        const pos   = parse.pos;
        let index   = parse.index;
        const depth = parse.deep;
        for (let i = 0; i < list.length; i++) {
            if (!run(parse, list[i])) {
                if (i > 0 && parse.pos >= parse.max_pos) {
                    parse.max_seq_pos = parse.pos;
                    parse.max_seq_op  = list[i];
                }
                while (index < parse.index) {
                    const node = parse.trace[index];
                    if (node.depth === depth) node.id |= DROP;
                    index++;
                }
                return false;
            }
        }
        return true;
    }

    if (op === "rept") {
        const min = expr[1], max = expr[2], exp = expr[3];
        let pos   = parse.pos;
        if (!run(parse, exp)) {
            if (min === 0) { parse.pos = pos; return true; }
            return false;
        }
        if (max === 1) return true;
        let count = 1;
        while (true) {
            pos = parse.pos;
            const result = run(parse, exp);
            if (parse.pos === pos) break;
            if (!result) { parse.pos = pos; break; }
            count++;
            if (count === max) break;
        }
        if (min > 0 && count < min) return false;
        return true;
    }

    if (op === "pred") {
        const oper = expr[1], term = expr[2];
        let index  = parse.index;
        const pos  = parse.pos;
        const result = run(parse, term);
        parse.pos = pos;
        while (index < parse.index) { parse.trace[index].id |= DROP; index++; }
        return oper === "!" ? !result : result;
    }

    if (op === "neg") {
        const term = expr[1];
        if (parse.pos >= parse.end) return false;
        let index  = parse.index;
        const pos  = parse.pos;
        const result = run(parse, term);
        parse.pos = pos;
        while (index < parse.index) { parse.trace[index].id |= DROP; index++; }
        if (result) return false;
        parse.pos++;
        return true;
    }

    if (op === "quote") {
        const str = expr[1], ci = expr[2];
        for (let k = 0; k < str.length; k++) {
            if (parse.pos >= parse.end) return false;
            let char = parse.input[parse.pos];
            if (ci) char = char.toUpperCase();
            if (char !== str[k]) return false;
            parse.pos++;
        }
        return true;
    }

    if (op === "class") {
        const chars = expr[1];
        if (parse.pos >= parse.end) return false;
        const char = parse.input[parse.pos];
        const max  = chars.length - 1;
        let i = 1;
        while (i < max) {
            const a = chars[i];
            if (i + 2 < max && chars[i + 1] === "-") {
                if (char >= a && char <= chars[i + 2]) { parse.pos++; return true; }
                i += 3;
            } else {
                if (char === a) { parse.pos++; return true; }
                i++;
            }
        }
        return false;
    }

    if (op === "dot") {
        if (parse.pos >= parse.end) return false;
        parse.pos++;
        return true;
    }

    if (op === "noop") return true;

    if (op === "ext") {
        const fn   = expr[1];
        const args = expr[2];
        return fn(parse, args);
    }

    throw new Error(`*** crash: run: undefined expression: ${JSON.stringify(expr)}`);
}

// -- prune parse tree -- removes failures and redundant nodes -----------

function prune_tree(parse) {
    const tree = [];
    prune(parse, 0, 0, 0, tree);
    return tree;
}

function prune(p, i, d, n, tree) {
    const j = p.trace.length;
    while (i < j) {
        const dep = p.trace[i].depth;
        if (dep < d) break;
        const id = p.trace[i].id;
        if (id & FAULT) {
            i++;
            while (i < j && p.trace[i].depth > dep) i++;
            continue;
        }
        const count = child_count(p, i + 1, dep + 1);
        if (count === 1 && p.code.defs[id & ID_VAL] !== HEAD) {
            i = prune(p, i + 1, dep + 1, n + 1, tree);
            continue;
        }
        const node = p.trace[i].clone();
        node.depth = dep - n;
        tree.push(node);
        i++;
    }
    return i;
}

function child_count(p, i, d) {
    let count = 0;
    const j   = p.trace.length;
    while (i < j) {
        const dep = p.trace[i].depth;
        if (dep < d) break;
        if (dep === d) {
            if (p.trace[i].id & FAULT) {
                i++;
                while (i < j && p.trace[i].depth > dep) i++;
                continue;
            }
            count++;
            if (count > 1) return count;
        }
        i++;
    }
    return count;
}

// -- prune trace for failed parse -- keeps faults, removes redundant ----

function prune_trace(parse) {
    const tree = [];
    tidy(parse, 0, 0, 0, tree);
    return tree;
}

function tidy(p, i, d, n, tree) {
    const j = p.trace.length;
    while (i < j) {
        const dep  = p.trace[i].depth;
        if (dep < d) break;
        const node = p.trace[i];
        const id   = node.id;
        if ((id & FAULT) && node.start === node.end) {
            i++;
            while (i < j && p.trace[i].depth > dep) i++;
            continue;
        }
        const count = child_trim_count(p, i + 1, dep + 1);
        if (count === 1 && p.code.defs[id & ID_VAL] !== HEAD) {
            i = tidy(p, i + 1, dep + 1, n + 1, tree);
            continue;
        }
        const clone = p.trace[i].clone();
        clone.depth = dep - n;
        if (i === p.max_trace) p.max_tree = tree.length;
        tree.push(clone);
        i++;
    }
    return i;
}

function child_trim_count(p, i, d) {
    let count = 0;
    const j   = p.trace.length;
    while (i < j) {
        const dep  = p.trace[i].depth;
        if (dep < d) break;
        if (dep === d) {
            const node = p.trace[i];
            const id   = node.id;
            if ((id & FAULT) && node.start === node.end) {
                i++;
                while (i < j && p.trace[i].depth > dep) i++;
                continue;
            }
            count++;
            if (count > 1) return count;
        }
        i++;
    }
    return count;
}

// -- show trace node ----------------------------------------------------

function show_trace(parse) {
    for (let i = 0; i < parse.trace.length; i++) show_trace_node(parse, i);
}

function show_trace_node(parse, index) {
    const node = parse.trace[index];
    const name = parse.code.names[node.id & ID_VAL];
    const fail = (node.id & FAIL) === 0 ? 0 : 1;
    const drop = (node.id & DROP) === 0 ? 0 : 1;
    console.log(`${name} fail=${fail}${drop} ${node.start}..${node.end}`);
}

// -- ptree json ---------------------------------------------------------

function p_tree(parse, i, d) {
    const arr = [];
    while (i < parse.tree.length) {
        const dep = parse.tree[i].depth;
        if (dep < d) break;
        if (parse.leaf(i)) {
            arr.push([parse.name(i), parse.text(i)]);
            i++;
        } else {
            const [children, i1] = p_tree(parse, i + 1, dep + 1);
            arr.push([parse.name(i), children]);
            i = i1;
        }
    }
    return [arr, i];
}

// -- ptree line diagram -------------------------------------------------

function show_tree(parse) {
    const lines = [];
    for (let i = 0; i < parse.tree.length; i++) {
        const value = parse.leaf(i) ? ` ${JSON.stringify(parse.text(i))}` : "";
        lines.push(`${indent_bars(parse.tree[i].depth)}${parse.name(i)}${value}`);
    }
    return lines.join("\n");
}

// -- print debug dump of trace nodes ------------------------------------

function dump_trace(parse) {
    console.log("   Span    Trace...");
    let pos = 0;
    let i   = 0;
    while (i < parse.trace.length) {
        const start      = parse.trace[i].start;
        const end        = parse.trace[i].end;
        let   depth      = parse.trace[i].depth;
        const next_depth = depth_of(parse, i + 1);
        if (pos < start) {
            const value = format_span(parse.input, pos, start);
            console.log(`${String(pos).padStart(4)}..${String(start).padEnd(4)} ${indent_bars(depth)}${value}`);
            pos = start;
        }
        dump_node(parse, i, start, end, depth);
        if (pos < end && depth >= next_depth) pos = end;
        while (depth > next_depth) {
            const parent     = parent_of(parse, i, depth);
            const parent_end = parse.trace[parent].end;
            if (pos < parent_end) {
                const value = format_span(parse.input, pos, parent_end);
                console.log(`${String(pos).padStart(4)}..${String(parent_end).padEnd(4)} ${indent_bars(depth)}${value}`);
                pos = parent_end;
            }
            depth--;
        }
        i++;
    }
    const eot = parse.end;
    if (pos < eot) {
        const max_node = parse.trace[parse.max_trace];
        const depth    = max_node.depth;
        const value    = `\x1b[1;41m!${format_span(parse.input, pos, eot)}\x1b[0m`;
        console.log(`${String(pos).padStart(4)}..${String(eot).padEnd(4)} ${indent_bars(depth)}${value}`);
    }
}

function dump_node(parse, i, start, end, depth) {
    const id = parse.trace[i].id;
    let name;
    if (id & FAIL) {
        if (start === end) return;
        name = "\x1b[1;31m!" + parse.code.names[id & ID_VAL] + "\x1b[0m";
    } else if (id & DROP) {
        name = "\x1b[1;31m-" + parse.code.names[id & ID_VAL] + "\x1b[0m";
    } else {
        name = parse.code.names[id];
    }
    let value = format_span(parse.input, start, end);
    if (i + 1 < parse.trace.length && parse.trace[i + 1].depth > depth) {
        value = "\x1b[2;38;5;253m" + value + "\x1b[0m";
    }
    console.log(`${String(start).padStart(4)}..${String(end).padEnd(4)} ${indent_bars(depth)}${name} ${value}`);
}

function format_span(input, start, end) {
    if (end - start < 50) return JSON.stringify(input.slice(start, end));
    return JSON.stringify(input.slice(start, start + 30)) +
           " ... " +
           JSON.stringify(input.slice(start + 30, end));
}

function parent_of(parse, i, d) {
    while (i > 0) {
        i--;
        if (parse.trace[i].depth < d) return i;
    }
    return 0;
}

function depth_of(parse, i) {
    return i < parse.trace.length ? parse.trace[i].depth : 0;
}

// -- dump tree ----------------------------------------------------------

function dump_tree(parse) {
    for (let i = 0; i < parse.tree.length; i++) dump_tree_node(parse, i);
    const eot = parse.end;
    let pos   = parse.max_pos;
    if (pos === 0) pos = parse.tree[parse.tree.length - 1].end;
    if (pos < eot) {
        const max_node = parse.tree[parse.max_tree];
        const depth    = max_node.depth;
        const value    = format_span(parse.input, pos, eot);
        console.log(`${indent_bars(depth)}\x1b[1;41m${value.slice(1, -1)}\x1b[0m`);
    }
}

function dump_tree_node(parse, i) {
    const node = parse.tree[i];
    const id   = node.id;
    if ((id & FAULT) && node.start === node.end) return;
    const name  = parse.code.names[id & ID_VAL];
    const value = (i + 1 === parse.tree.length || parse.tree[i + 1].depth <= node.depth)
        ? format_span(parse.input, node.start, node.end)
        : "";
    console.log(`${indent_bars(node.depth)}${name} ${value}`);
}

// -- Parse error reporting ----------------------------------------------

function show_pos(parse, info = "") {
    const pos  = Math.max(parse.pos, parse.max_pos);
    const sol  = line_start(parse, pos - 1);
    const eol  = line_end(parse, pos);
    const ln   = line_number(parse.input, sol);
    const text = clean_chars(parse.input.slice(sol + 1, pos));
    const left = `line ${ln} | ${text}`;
    let prior  = "";
    if (sol > 0) {
        const sol1  = line_start(parse, sol - 1);
        const text2 = clean_chars(parse.input.slice(sol1 + 1, sol));
        prior = `line ${ln - 1} | ${text2}\n`;
    }
    if (pos === parse.end) {
        return `${prior}${left}\n${" ".repeat(left.length)}^ ${info}`;
    }
    return `${prior}${left}${parse.input.slice(pos, eol)}\n${" ".repeat(left.length)}^ ${info}`;
}

function clean_chars(txt) {
    const cs = [];
    for (const c of txt) cs.push(c < " " ? " " : c);
    return cs.join("");
}

function line_start(parse, sol) {
    while (sol >= 0 && parse.input[sol] !== "\n") sol--;
    return sol;
}

function line_end(parse, eol) {
    while (eol < parse.end && parse.input[eol] !== "\n") eol++;
    return eol;
}

function indent_bars(size) {
    return "\x1b[38;5;253m" + "│ ".repeat(size) + "\x1b[0m";
}

function line_number(input, i) {
    if (i < 0) return 1;
    if (i >= input.length) i = input.length - 1;
    let n = 1;
    while (i >= 0) {
        while (i >= 0 && input[i] !== "\n") i--;
        n++;
        i--;
    }
    return n;
}

function rule_info(parse) {
    if (parse.fell_short) return "unexpected input, parse ok on input before this";
    let note = " failed";
    if (parse.expected) {
        note = ` failed, expected: ${code_show(parse, parse.expected)}`;
    }
    const node = parse.trace[parse.max_trace];
    const name = parse.code.names[node.id & ID_VAL];
    return src_map(parse, name, note);
}

function code_show(parse, op) {
    if (op[0] === "quote") {
        const quo = "'" + op[1] + "'";
        return op[2] ? quo + "i" : quo;
    }
    if (op[0] === "id") return parse.code.names[op[1]];
    return op;
}

function src_map(parse, name, note = "") {
    const peg_parse = parse.code.peg_parse;
    if (!peg_parse) return name + note + " in boot-code...";
    const lines = [name + note];
    for (let i = 0; i < peg_parse.tree.length - 1; i++) {
        if (peg_parse.name(i) !== "rule") continue;
        if (peg_parse.text(i + 1) === name) {
            lines.push(peg_parse.text(i).trim());
            break;
        }
    }
    return lines.join("\n");
}

function empty_alt_report(parse) {
    if (parse.empty_alt === null) return "";
    const [list, i] = parse.empty_alt;
    const opt = list[i];
    const msg = `\n*** in: ${JSON.stringify(list)}`;
    if (opt[0] === "id") {
        return `${msg}\n    alternative '${parse.name(opt[1])}' was an empty '' match!`;
    }
    return `${msg}\n    alternative ${i} was an empty '' match!`;
}

function err_report(parse) {
    const at_pos = `at: ${Math.max(parse.pos, parse.max_pos)} of: ${parse.end}`;
    if (parse.code.err.length > 0) {
        const title = `*** grammar failed ${at_pos}`;
        const errs  = parse.code.err.join("\n");
        return `${title}\n${errs}\n${show_pos(parse)}`;
    }
    parse.print_tree();
    const title = `*** parse failed ${at_pos}` + empty_alt_report(parse);
    return `${title}\n${show_pos(parse, rule_info(parse))}`;
}

// == pPEG ptree is compiled into a Code object ==========================

class Code {
    constructor(peg_parse, { boot = null, transforms = {}, extras = {} } = {}) {
        this.peg_parse  = peg_parse;
        this.ptree      = peg_parse ? peg_parse.ptree() : boot;
        this.names      = [];
        this.rules      = [];
        this.codes      = [];
        this.defs       = [];
        this.extras     = extras;
        this.transforms = transforms;
        this.err        = [];
        this.ok         = true;
        this.compose();
    }

    compose() {
        define_rules(this);
        for (const expr of this.rules) {  // NOT map(): extensions need codes.length
            this.codes.push(emit(this, expr));
        }
        if (this.err.length > 0) this.ok = false;
    }

    toString() {
        if (!this.ok) return `code error: ${this.err}`;
        const lines = [];
        for (let i = 0; i < this.names.length; i++) {
            lines.push(`${String(i).padStart(2)}: ${this.names[i]} ${DEFS[this.defs[i]]} ${JSON.stringify(this.codes[i])}`);
        }
        return lines.join("\n");
    }

    parse(input, start = -1, end = -1) { return parser(this, input, start, end); }
    errors()                           { return this.err.join("\n"); }
    id_name(id)                        { return this.names[id]; }
    read(input)                        { return this.parse(input).transform(); }

    name_id(name) {
        const idx = this.names.indexOf(name);
        if (idx >= 0) return idx;
        this.err.push(`undefined rule: ${name}`);
        code_rule_defs(this, name, "=", ["extn", "<undefined>"]);
        return this.names.length - 1;
    }
}

// -- compile Parse into Code parser instructions ------------------------

function define_rules(code) {
    for (const rule of code.ptree[1]) {
        if (rule[0] !== "rule") {
            code.err.push(`Expected 'rule', is this a Peg ptree?\n ${JSON.stringify(rule)}`);
            break;
        }
        const body = rule[1];
        if (body.length === 3 && body[0][0] === "id" && body[1][0] === "def") {
            code_rule_defs(code, body[0][1], body[1][1], body[2]);
        } else if (body.length === 2 && body[0][0] === "id") {
            code_rule_defs(code, body[0][1], "=", body[1]);
        } else {
            code.err.push(`Expected 'rule', is this a Peg ptree?\n ${JSON.stringify(rule)}`);
            break;
        }
    }
}

function code_rule_defs(code, name, defn, expr) {
    if (code.names.includes(name)) code.err.push(`duplicate rule name: ${name}`);
    code.names.push(name);
    code.rules.push(expr);
    let defx = DEFS.indexOf(defn);
    if (defx < 0) {
        defx = EQ;
        code.err.push(`undefined: ${name} ${defn}`);
    }
    if (defx === EQ) {
        if (name[0] === "_") {
            defx = ANON;
        } else if (name[0] >= "A" && name[0] <= "Z") {
            defx = HEAD;
        }
    }
    code.defs.push(defx);
}

function emit(code, expr) {
    const op = expr[0];

    if (op === "id") {
        return ["id", code.name_id(expr[1])];
    }
    if (op === "alt") {
        return ["alt", expr[1].map(x => emit(code, x))];
    }
    if (op === "seq") {
        return ["seq", expr[1].map(x => emit(code, x))];
    }
    if (op === "rep") {
        const [exp, suffix] = expr[1];
        const sfxOp = suffix[0];
        if (sfxOp === "sfx") {
            let min = 0, max = 0;
            if (suffix[1] === "+") min = 1;
            else if (suffix[1] === "?") max = 1;
            return ["rept", min, max, emit(code, exp)];
        }
        if (sfxOp === "min") {
            const min = parseInt(suffix[1], 10);
            return ["rept", min, min, emit(code, exp)];
        }
        if (sfxOp === "nums") {
            const [minNode, maxNode] = suffix[1];
            const min = parseInt(minNode[1], 10);
            const max = (maxNode && maxNode[1]) ? parseInt(maxNode[1], 10) : 0;
            return ["rept", min, max, emit(code, exp)];
        }
    }
    if (op === "pre") {
        const [pfxNode, exp] = expr[1];
        const pfx = pfxNode[1];
        if (pfx === "~") return ["neg", emit(code, exp)];
        return ["pred", pfx, emit(code, exp)];
    }
    if (op === "quote") {
        const str = expr[1];
        if (str[str.length - 1] !== "i") {
            return ["quote", escape(str.slice(1, -1), code), false];
        }
        return ["quote", escape(str.slice(1, -2).toUpperCase(), code), true];
    }
    if (op === "class") {
        return ["class", escape(expr[1], code)];
    }
    if (op === "dot") {
        return ["dot"];
    }
    if (op === "extn") {
        return extension_op(code, expr[1]);
    }
    throw new Error(`*** crash: emit: undefined expression: ${JSON.stringify(expr)}`);
}

// -- compile extensions -------------------------------------------------

function extension_op(code, extend) {
    const args = extend.slice(1, -1).split(/\s+/);
    const fn   = code.extras[args[0]];
    if (fn) return ["ext", fn, args];
    if (args[0] === "to") return transform_ext(code, args);
    const e = `*** Undefined extension: ${extend}`;
    code.err.push(e);
    return ["err", e];
}

function to_number(s) {
    const n = parseInt(s, 10);
    if (!isNaN(n) && String(n) === s.trim()) return n;
    return parseFloat(s);
}

const builtin_transforms = {
    Object: x => {
        if (Array.isArray(x)) {
            const obj = {};
            for (const [k, v] of x) obj[k] = v;
            return obj;
        }
        return {};
    },
    Array:  x => (Array.isArray(x) ? x : []),
    String: x => String(x),
    Number: to_number,
};

function transform_ext(code, args) {
    let name  = code.names[code.codes.length];
    let fname = args[1];
    if (fname[0] === ":") {
        name  += ":";
        fname  = fname.slice(1);
    }
    const fn = builtin_transforms[fname];
    if (!fn) code.err.push(`*** Undefined transform: ${fname}`);
    code.transforms[name] = fn;
    return ["noop"];
}

// -- escape codes -------------------------------------------------------

function escape(s, code) {
    let r = "";
    let i = 0;
    while (i < s.length) {
        let c = s[i];
        i++;
        if (c === "\\" && i < s.length) {
            const k = s[i];
            i++;
            if      (k === "n") { c = "\n"; }
            else if (k === "r") { c = "\r"; }
            else if (k === "t") { c = "\t"; }
            else if (k === "x") { const [v, j] = hex_value(2, s, i); c = v; i = j; }
            else if (k === "u") { const [v, j] = hex_value(4, s, i); c = v; i = j; }
            else if (k === "U") { const [v, j] = hex_value(8, s, i); c = v; i = j; }
            else { i--; }
            if (c === null) {
                code.err.push(`bad escape code: ${s}`);
                return s;
            }
        }
        r += c;
    }
    return r;
}

function hex_value(n, s, i) {
    if (i + n > s.length) return [null, i];
    const hex = s.slice(i, i + n);
    const cp  = parseInt(hex, 16);
    if (isNaN(cp)) return [null, i];
    return [String.fromCodePoint(cp), i + n];
}

// -- parse.transform ----------------------------------------------------

function transformer(p, i, d) {
    const vals = [];
    while (i < p.tree.length) {
        const dep = p.tree[i].depth;
        if (dep < d) break;
        if (p.leaf(i)) {
            vals.push(apply_type(p, i, p.text(i)));
            i++;
        } else {
            const [result, j] = transformer(p, i + 1, dep + 1);
            vals.push(apply_type(p, i, result));
            i = j;
        }
    }
    return [vals, i];
}

function apply_type(p, i, val) {
    try {
        const name     = p.name(i);
        const [fn, con] = transform_fn(p, name);
        if (!fn) return [name, val];
        const result = fn(val);
        if (con === ":") return [name, result];
        return result;
    } catch (err) {
        const name = p.name(i);
        throw new Error(`*** transform failed: ${name}(${val})\n${err}`);
    }
}

function transform_fn(p, name) {
    let fn = p.code.transforms[name];
    if (fn) return [fn, "."];
    fn = p.code.transforms[name + ":"];
    if (fn) return [fn, ":"];
    return [null, "."];
}

// -- peg_grammar ptree -- bootstrap generated ---------------------------

const peg_ptree = ["Peg", [
["rule", [["id", "Peg"], ["def", "="], ["seq", [["id", "_"], ["rep", [["id", "rule"], ["sfx", "+"]]]]]]]  ,
["rule", [["id", "rule"], ["def", "="], ["seq", [["id", "id"], ["id", "_"], ["id", "def"], ["id", "_"], ["id", "alt"]]]]]  ,
["rule", [["id", "def"], ["def", "="], ["rep", [["class", "[:=]"], ["sfx", "+"]]]]]  ,
["rule", [["id", "alt"], ["def", "="], ["seq", [["id", "seq"], ["rep", [["seq", [["quote", "'/'"], ["id", "_"], ["id", "seq"]]], ["sfx", "*"]]]]]]]  ,
["rule", [["id", "seq"], ["def", "="], ["rep", [["id", "rep"], ["sfx", "+"]]]]]  ,
["rule", [["id", "rep"], ["def", "="], ["seq", [["id", "pre"], ["rep", [["id", "sfx"], ["sfx", "?"]]], ["id", "_"]]]]]  ,
["rule", [["id", "pre"], ["def", "="], ["seq", [["rep", [["id", "pfx"], ["sfx", "?"]]], ["id", "term"]]]]]  ,
["rule", [["id", "term"], ["def", "="], ["alt", [["id", "call"], ["id", "quote"], ["id", "class"], ["id", "dot"], ["id", "group"], ["id", "extn"]]]]]  ,
["rule", [["id", "group"], ["def", "="], ["seq", [["quote", "'('"], ["id", "_"], ["id", "alt"], ["quote", "')'"]]]]]  ,
["rule", [["id", "call"], ["def", "="], ["seq", [["id", "id"], ["id", "_"], ["pre", [["pfx", "!"], ["id", "def"]]]]]]]  ,
["rule", [["id", "id"], ["def", "="], ["seq", [["class", "[a-zA-Z_]"], ["rep", [["class", "[a-zA-Z0-9_]"], ["sfx", "*"]]]]]]]  ,
["rule", [["id", "pfx"], ["def", "="], ["class", "[~!&]"]]]  ,
["rule", [["id", "sfx"], ["def", "="], ["alt", [["class", "[+?]"], ["seq", [["quote", "'*'"], ["rep", [["id", "nums"], ["sfx", "?"]]]]]]]]]  ,
["rule", [["id", "nums"], ["def", "="], ["seq", [["id", "min"], ["rep", [["seq", [["quote", "'..'"], ["id", "max"]]], ["sfx", "?"]]]]]]]  ,
["rule", [["id", "min"], ["def", "="], ["rep", [["class", "[0-9]"], ["sfx", "+"]]]]]  ,
["rule", [["id", "max"], ["def", "="], ["rep", [["class", "[0-9]"], ["sfx", "*"]]]]]  ,
["rule", [["id", "quote"], ["def", "="], ["seq", [["class", "[']"], ["rep", [["pre", [["pfx", "~"], ["class", "[']"]]], ["sfx", "*"]]], ["class", "[']"], ["rep", [["quote", "'i'"], ["sfx", "?"]]]]]]]  ,
["rule", [["id", "class"], ["def", "="], ["seq", [["quote", "'['"], ["rep", [["pre", [["pfx", "~"], ["quote", "']'"]]], ["sfx", "*"]]], ["quote", "']'"]]]]]  ,
["rule", [["id", "dot"], ["def", "="], ["seq", [["quote", "'.'"], ["id", "_"]]]]]  ,
["rule", [["id", "extn"], ["def", "="], ["seq", [["quote", "'<'"], ["rep", [["pre", [["pfx", "~"], ["quote", "'>'"]]], ["sfx", "*"]]], ["quote", "'>'"]]]]]  ,
["rule", [["id", "_"], ["def", "="], ["rep", [["alt", [["rep", [["class", "[ \\t\\n\\r]"], ["sfx", "+"]]], ["seq", [["quote", "'#'"], ["rep", [["pre", [["pfx", "~"], ["class", "[\\n\\r]"]]], ["sfx", "*"]]]]]]], ["sfx", "*"]]]]]
]];

// == pPEG compile API ===================================================

let peg_code = new Code(null, { boot: peg_ptree });

function compile(grammar, transforms = {}, extras = {}) {
    const parse = parser(peg_code, grammar);
    if (!parse.ok) throw new Error("*** grammar fault...\n" + err_report(parse));
    const code = new Code(parse, { transforms, extras });
    if (!code.ok) throw new Error("*** grammar errors...\n" + code.errors());
    return code;
}

peg_code = compile(peg_grammar);  // bootstrap full grammar

module.exports = { compile, Code, Parse };
