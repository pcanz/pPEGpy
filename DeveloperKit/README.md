#   A pPEG Parser Machine Developer Kit

This directory contains JavaScript code samples for the incremental development of a pPEG parser machine, as explained in [pPEG-machine].

Each step has a code file that can be run with Node.js.

####  Step 1:   [Machine-1]

    First toy parser for date grammar example
    No parse tree generation
    4-instruction parser machine
    50 LOC grammar and parser code
    50 LOC parser machine

####  Step 2:     [Machine-2]

    Toy parser for date grammar example
    now generating a parse tree.
    4-instruction parser machine,
    100 LOC parser machine

####  Step 3:     [Machine-3]

    More instructions, date grammar example 
    7-instruction parser machine,
    130 LOC parser machine

####  Step 4:     [Machine-4]

    Parser for pPEG boot grammar
    full 8-instruction parser machine,
    150 LOC parser machine

####  Step 5:     [Machine-5]

    Parser for full pPEG grammar, 
    8-instruction parser machine,
    parser_code from pPEG ptree,
    export grammar compile API
    200 LOC parser machine        

####  Full pPEG implementation:     [Machine-6]

    Full code for pPEG parser machine.
     50 LOC pPEG grammar source and Json ptree
    250 LOC parser machine
    250 LOC compiler
    250 LOC fault and trace reporting
    130 LOC built-in extensions
    950 LOC total

[pPEG-machine]: https://github.com/pcanz/pPEG/blob/master/docs/pPEG-machine.md

[Machine-1]: https://github.com/pcanz/pPEGjs/blob/master/DeveloperKit/machine-1.js
[Machine-2]: https://github.com/pcanz/pPEGjs/blob/master/DeveloperKit/machine-2.js
[Machine-3]: https://github.com/pcanz/pPEGjs/blob/master/DeveloperKit/machine-3.js
[Machine-4]: https://github.com/pcanz/pPEGjs/blob/master/DeveloperKit/machine-4.js
[Machine-5]: https://github.com/pcanz/pPEGjs/blob/master/DeveloperKit/machine-5.js
[Machine-6]: https://github.com/pcanz/pPEGjs/blob/master/pPEG.mjs