# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`pPEGpy` is a portable PEG (Parsing Expression Grammar) parser implemented in Python 3.10+. The entire implementation lives in one file: `src/pPEGpy/peg.py`. There are no external dependencies.

## Commands

```bash
# Build the package
uv build

# Install locally (editable)
pip install -e .

# Run a specific test suite
python3 tests/peg-tests.py
python3 tests/test-1.py
python3 tests/op-tests.py

# Run an example
python3 examples/date.py
python3 examples/json.py
```

There is no test runner framework — each test file is a standalone script that prints pass/fail to stdout.

## Architecture

### Public API (`peg.py`)

- `peg.compile(grammar, transforms={}, extras={})` → `Code` — parses a grammar string and returns a compiled parser.
- `Code.parse(input)` → `Parse` — runs the parser; `str(parse)` shows a tree diagram or error report.
- `Code.read(input)` → `(ok, result)` — shorthand for `parse(input).transform()`.

### Bootstrap sequence

The PEG grammar is self-describing. Startup does two things:
1. `peg_ptree` (a hardcoded list) bootstraps the initial `Code` object (`peg_code`).
2. `compile(peg_grammar)` then re-parses the grammar string using `peg_code`, replacing it with a fully self-hosted `Code`. Both live at module level.

### Core classes

| Class/type | Purpose |
|---|---|
| `Code` | Compiled grammar: holds `names`, `codes`, `defs`, `transforms`, `extras` arrays indexed by rule id |
| `Parse` | Parser run context and result: `trace` (every node visited), `tree` (pruned result), position state, fault tracking |
| `Node` | Dataclass for a single parse tree node: `id`, `depth`, `start`, `end` |

### Rule definition types

Rules are compiled to one of four types (stored in `Code.defs`):

| Token | Constant | Behaviour |
|---|---|---|
| `=` | `EQ` | Dynamic: `_name` → ANON, `Uppercase` → HEAD, else by child count |
| `:` | `ANON` | Anonymous — matched text consumed but node not included in tree |
| `:=` | `HEAD` | Always creates a parent node, even with zero children (needed for empty-match rules) |
| `=:` | `TERM` | Terminal — inner expressions run anonymously, result is raw text |

The `EQ` heuristic: a rule with a single child is collapsed (elided) unless it is `HEAD`. Rules starting with `_` are always `ANON`. Rules starting with an uppercase letter are always `HEAD`.

### The `run()` engine

`run(parse, expr)` is a recursive pattern-match dispatch over `expr` types:
`["id", idx]`, `["alt", list]`, `["seq", list]`, `["rept", min, max, exp]`, `["pred", op, term]`, `["neg", term]`, `["quote", str, i]`, `["class", chars]`, `["dot"]`, `["noop"]`, `["ext", fn, args]`.

Every `id` call appends a `Node` to `parse.trace`. After the run, `prune_tree` (success) or `prune_trace` (failure) strips faults and redundant single-child nodes to produce `parse.tree`.

### Extensions

Grammar rules can embed `<command args...>` syntax. At compile time, `extension_op` looks up `args[0]` in the `extras` dict passed to `compile()`. Extension functions have signature `fn(parse, args) -> bool`.

The built-in `<to Type>` extension (`Object`/`Array`/`String`/`Number`) installs a transform automatically so no Python-side `transforms` dict entry is needed.

### Transforms

`transforms` maps rule names to callables applied during `Parse.transform()`:
- `"rule": fn` — `fn(val)` replaces the node entirely.
- `"rule:": fn` — `fn(val)` is called but the result is wrapped as `[name, result]`.

`val` is the matched string for leaf nodes, or a list of child results for branch nodes.

### `extras.py` (not imported by default)

`examples/extras.py` provides reusable extension functions: `dump`, `same`, `eq`, `match`, `indent`, `inset`, `dedent`. Import and pass `extras.extensions()` to `compile()` to use them.
