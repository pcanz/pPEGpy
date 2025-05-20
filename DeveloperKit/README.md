#   A pPEG Parser Machine Developer Kit

This directory contains Python code samples for the incremental development of a pPEG parser machine, as explained in [pPEG-machine].

The parse tree and trace features need to be updated. A new parse tree based on arrays of integer index values replaces the original Python array structure. A standard ptree can be build from this new internal parse tree.  The new internal tree can include failed nodes and a dump of the parse tree after a failed parse shows what happened and this replaces the old trace feature described here. 

Each step has a code file that can be run as a Python script

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
    60 LOC parser machine

####  Step 3:     [Machine-3]

    More instructions, date grammar example 
    7-instruction parser machine,
    100 LOC parser machine

####  Step 4:     [Machine-4]

    Parser for pPEG boot grammar
    8-instruction parser machine,
    170 LOC parser machine

####  Step 5:     [Machine-5]

    Parser for full pPEG grammar, 
    8-instruction parser machine,
    parser_code from pPEG ptree,
    export grammar compile API
    200 LOC parser machine        

####  Step 6:     [Machine-6]

    Parser for full pPEG grammar, 
    8-instruction parser machine,
    parser_code from pPEG ptree,
    export grammar compile API
    250 LOC parser machine        

####  Step 7:     [Machine-7]

    Parser for full pPEG grammar, 
    8-instruction parser machine,
    parser_code from pPEG ptree,
    export grammar compile API
    250 LOC parser machine        

####  Full pPEG implementation:     [Machine-8]

    Full code for pPEG parser machine.
     50 LOC pPEG grammar source and Json ptree
    250 LOC parser machine
    100 LOC compiler
    100 LOC fault and trace reporting
    120 LOC extensions
    700 LOC total

[pPEG-machine]: https://github.com/pcanz/pPEG/blob/master/docs/pPEG-machine.md

[Machine-1]: https://github.com/pcanz/pPEGpy/blob/master/DeveloperKit/machine-1.py
[Machine-2]: https://github.com/pcanz/pPEGpy/blob/master/DeveloperKit/machine-2.py
[Machine-3]: https://github.com/pcanz/pPEGpy/blob/master/DeveloperKit/machine-3.py
[Machine-4]: https://github.com/pcanz/pPEGpy/blob/master/DeveloperKit/machine-4.py
[Machine-5]: https://github.com/pcanz/pPEGpy/blob/master/DeveloperKit/machine-5.py
[Machine-6]: https://github.com/pcanz/pPEGpy/blob/master/DeveloperKit/machine-6.py
[Machine-7]: https://github.com/pcanz/pPEGpy/blob/master/DeveloperKit/machine-7.py
[Machine-8]: https://github.com/pcanz/pPEGpy/blob/master/pPEG.py