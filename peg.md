PEGs in a PEG
=============

So I was reading [Bryan Ford’s thesis][ford]
about parsing expression grammars and packrat parsers,
and I thought it would be fun to implement them
and see how easy they really were.

It turns out they can be fairly easy;
this document contains a one-page PEG parser generator
that generates PEG parsers in JavaScript,
along with an explanation of how it works.
If you’ve ever thought
that writing a compiler was deep magic
because parsing would take you way too long to understand,
this should show you
that writing a compiler can be simple,
if you already know how to program.

[ford]: http://pdos.csail.mit.edu/~baford/packrat/thesis/ "Packrat Parsing: a Practical Linear-Time Algorithm with Backtracking"

What Are PEGs?
--------------

A PEG is a formal language description
which describes how to *parse* a language,
by contrast with context-free grammars,
which primarily describe how to *generate* sentences of a language.
This difference
makes it much easier to construct parsers for PEGs;
they can be straightforwardly converted
into simple recursive-descent parsers
performing limited backtracking,
with each nonterminal becoming a parsing function.

PEGs can parse some languages
that context-free grammars can’t,
such as the language `a`<sup>n</sup>`b`<sup>n</sup>`c`<sup>n</sup>,
that is,
some number of `a`s,
followed by the same number of `b`s,
followed by the same number of `c`s.
However, because PEGs can’t handle ambiguity,
and because there’s a linear-time parsing algorithm for them,
it is suspected that PEGs can’t parse
all languages context-free grammars can.
`S → a S a | a S b | b S a | b S b | a` 
is a simple context-free language
that Ford conjectured cannot be parsed with a PEG.
PEGs can parse all languages
that can be parsed with LL(k) or LR(k) parsers.

PEGs are more composable
than LL(k) or LR(k) CFGs;
because PEGs can’t handle ambiguity,
it’s easy to predict the effect
of adding new parsing rules to the grammar.

A Minimal PEG Language
----------------------

The expressions in PEGs minimally contain
(using the TDPL notation in the thesis)
negation `!`, 
ordered choice or alternation `/`, 
concatenation or sequencing (denoted by juxtaposition),
terminal strings (written in single quotes `''`), 
and nonterminals (written as bare words `foo`).

Here’s a relatively minimal grammar
describing a notation for a grammar
with these features,
written in terms of itself:

    (in a minimal parsing expression grammar)
    _              <- sp _ / .
    sp             <- ' ' / '\n' / '\t'.
    grammar        <- _ rule grammar / _ rule.
    rule           <- name _ '<-'_ choice '.'_.
    choice         <- sequence '/'_ choice / sequence.
    sequence       <- term sequence / .
    term           <- '!'_ term / '\'' stringcontents '\''_ / name _.
    stringcontents <- stringchar stringcontents / .
    stringchar     <- !'\\' !'\'' char / '\\' char.
    name           <- namechar name / namechar.
    namechar       <- !'!' !'\'' !sp !'<-' !'/' !'.' char.

This all depends on the primitive nonterminal `char`,
which I’m assuming matches any character,
for some definition of character.

The nonterminal `_` consumes any amount of whitespace.
It’s used everywhere we want to consume whitespace,
generally at the lowest possible level of the grammar,
with the exception of `name`
(on the theory that the whitespace 
is not really part of the name.)
(Even though it has a funny non-alphabetic name,
the language doesn’t treat it specially.
I used to call it `s` but it was distracting.)

There are several cases of the pattern `foos <- foo foos / .`,
which means `foos` is zero or more things that match `foo`.
Because PEGs are greedy and don’t backtrack after returning,
`foos` will only ever parse
the maximum possible number of `foo` items.
It’s not possible for a parsing failure after the `foos`
to cause `foos` to backtrack and return a smaller number of `foo` objects,
the way it could in a parser for a context-free grammar,
although a parsing failure inside the last `foo` will indeed do so.
This allows us to get by
without a separate scanner for this grammar!
One minor variation of this pattern
is found in `grammar` and `name`,
which match *one* or more of their elements,
not *zero* or more.

Note that the above grammar tells us how to parse the language,
but doesn’t tell us anything about its semantics.
But it’s nice and short.

Adding Grouping
---------------

The PEG language as written above is pretty weak.
It doesn’t have grouping or repetition,
although they can be emulated with the use of extra productions,
as in the `foos` pattern explained above.

We can add grouping by redefining `term` like this:

    (in a slightly more powerful parsing expression grammar)
    term           <- '!'_ term / '\'' stringcontents '\''_ / name _ 
                    / '('_ choice ')'_.

This simplifies the grammar only slightly;
we can rewrite `stringcontents` as follows:

    stringcontents <- (!'\\' !'\'' char / '\\' char) stringcontents / .

A Diversion: Adding Repetition
------------------------------

Although it turns out not to be very useful
for what I’ll do next,
adding the capability for repetition to the language
makes it shorter and clearer.

    (in a more powerful PEG)
    sp      <- ' ' / '\n' / '\t'.
    _       <- sp*.
    grammar <- _ (name _ '<-'_ choice '.'_)+.
    choice  <- term* ('/'_ term*)*.
    term    <- ('!'_ term / string / name / '('_ choice ')')_ ('+' / '*' / )_.
    string  <- '\'' (!'\\' !'\'' char / '\\' char)* '\''_.
    meta    <- '!' / '\'' / '<-' / '/' / '.' / '+' / '*' / '(' / ')'.
    name    <- (!meta !sp char)+.

That shrinks the grammar considerably,
while significantly expanding 
the expressiveness of the grammar language it describes.

Adding Result Expressions
-------------------------

In theory, the grammar as written could be useful.
It’s expressive enough to describe
the tree structure of a language,
such as the PEG language defined above.
So you could use it to parse some string
into a syntax tree.

However,
it would be even more useful
to have a version of the grammar language
that can include result expressions
written in some programming language
that compute useful things.
For example,
you could use such a system
to write and maintain a working compiler
from PEG grammars to some programming language,
or from some other language.

A straightforward and readable way to do this
is to label some parts of a sequence with names,
and then to use those names in a result specification
at the end of the sequence.

Here’s an extension of the above grammar
that allows for such names and result specifications:

    (in a PEG describing results)
    sp             <- ' ' / '\n' / '\t'.
    _              <- sp _ / .
    grammar        <- _ rule grammar / _ rule.
    rule           <- name _ '<-'_ choice '.'_.
    choice         <- sequence '/'_ choice / sequence.
    sequence       <- term sequence / '->'_ expr / .
    expr           <- '('_ exprcontents ')'_.
    exprcontents   <- (!'(' !')' char / expr) exprcontents / .
    term           <- name _ ':'_ term / '!'_ term / string / name _ 
                    / '('_ choice ')'_.
    string         <- '\'' stringcontents '\''_.
    stringcontents <- !'\\' !'\'' char stringcontents 
                    / '\\' char stringcontents / .
    meta           <- '!' / '\'' / '<-' / '/' / '.' / '(' / ')' / ':' / '->'.
    name           <- namechar name / namechar.
    namechar       <- !meta !sp char.

This adds the possibility
that a term may be preceded by a colon and a name,
and that a sequence may end
with a `->` and a parenthesized expression.

This lets you write things like
`n: expr` 
and `expr _ -> (print("got expr"))`.
It doesn’t place strong requirements 
on the embedded expression, 
so it can be in almost any language, 
but it does require that any parentheses inside of it 
be balanced.
(If that's difficult in a certain case,
due to embedded strings,
maybe you can incorporate some commented-out parentheses
to balance things.)

A Metacircular Compiler-Compiler
--------------------------------

So let’s suppose that we want to use this result-expression facility
to write a compiler for these grammars,
producing a parser for the specified grammar
in, say, JavaScript.
We want to translate each parsing expression
in the grammar language
into an expression in the target language
that parses 
the sub-language defined by that parsing expression.
For example,
we want to translate 
`choice <- sequence '/'_ choice / sequence.`
into a recursive JavaScript function
that parses expressions containing slash-separated `choice`s.
Since it doesn’t specify a result expression,
it’s sort of indeterminate what it should actually do,
other than consume characters from the input stream
until it finds something `choice` can't parse.

So now we have to figure out
what the semantics are
of each of the various actions.

### Whitespace ###

Whitespace is fairly easy:
it is a no-op.

    (in the metacircular compiler-compiler)
    sp <- ' ' / '\n' / '\t'.
    _  <- sp _ / .

### Rules ###

Let’s compile each rule
into a JavaScript function
that parses the language described by that rule,
and the grammar as a whole
into the collection of these functions
plus whatever support code is needed.
(Here I’m going to use double angle-brackets `<<>>`
to name chunks of code that aren’t given until later.)

    rule    <- n: name _ '<-'_ body: choice '.'_
               -> (["function parse_", n, "(input, pos) {\n",
                      <<function prologue>>
                      body, 
                      <<function epilogue>>
                   "}\n"].join('')).
    grammar <- _ r: rule g: grammar -> (r + "\n" + g)
             / _ r: rule -> (r + "\n"
                   <<support code>>
               ).

So a grammar nonterminal named `term`
will be compiled into a function called `parse_term`,
whose body will be the value computed by `choice`,
bracketed by some startup and cleanup code,
and therefore `choice` needs to evaluate to
a string of
zero or more valid JavaScript statements.

These functions
will need to do several things
to implement the semantics of a PEG parser:

1. Advance the input position, 
   starting from the input position the caller passed in,
   and in case of success, 
   communicate the new input position
   to the caller.
2. Save the input position
   (and any other state)
   in order to backtrack
   when a sequence inside a choice fails,
   or after testing a negation condition.
   They may have to save
   several input positions at once
   in cases where there is nested alternation.
3. Compute the value
   given by the result expressions in the grammar
   and, in case of success, 
   pass it back to the caller, 
   along with the new input position.

In order to avoid global variables,
we’re passing in the input string
(which doesn’t change during a parse)
and the current position in it
as arguments to each parsing function.

To package the value computed
along with the new input position,
we’ll return a JavaScript object
with `val` and `pos` properties,
like `{val: "grammar", pos: 37}`.
In case of failure,
we’ll just return `null`.

From here we’ll mostly work bottom-up.

### Names ###

Names are used in two contexts:
at the top level of a rule, 
they define the name of the nonterminal,
and in a term,
they request a call to that nonterminal.
In both cases,
we basically just need the contents of the name.

    (in the metacircular compiler-compiler)
    meta     <- '!' / '\'' / '<-' / '/' / '.' / '(' / ')' / ':' / '->'.
    name     <- c: namechar n: name -> (c + n) / namechar.
    namechar <- !meta !sp char.

In this case,
we presume that the value produced by `char`
(and thus the value produced by `namechar`)
is the character it consumed,
and that in the absence of an explicit result expression,
the result of the whole rule
is that same character.
This can be implemented, for example,
by having a sequence return by default
the value of the last term in it.
(I’m not sure that’s a good default,
because it seems a little error-prone,
but I’ll try it.)

### Nonterminals ###

A reference to a nonterminal
is compiled as a call to its parsing function,
passing in the current position.

    (in the metacircular compiler-compiler)
    term <- labeled / nonterminal / string / negation / parenthesized.
    nonterminal <- n: name _ -> (
        ['  state = parse_', n, '(input, state.pos);\n'].join('')
    ).

This means we need a variable `state`
to store this returned value in,
and it needs to be initialized
with the position passed in by the caller.

    (in function prologue)
    '  var state = { pos: pos };\n',

What do we do with `state.val`?
It depends on where the nonterminal is found.
If it’s preceded by a label,
we want to store it in a variable
under that name
for later use, 
unless it fails.
Let’s have `term`,
just like `choice`,
return a string of zero or more valid JavaScript statements.

    (in the metacircular compiler-compiler)
    labeled <- label: name _ ':'_ value: term -> (
        [value, '  if (state) var ', label, ' = state.val;\n'].join('')).

(Ideally we would undo this saving
if the nonterminal is in an alternative
that fails and ends up being backtracked;
but hopefully the result expressions
of later alternatives
will simply not use that variable.)

Now,
if the nonterminal
was the last thing in a parsing function,
then we want to return the `state.val` it gave us
as our own `state.val`,
and additionally we want to return its `state.pos`
as our `state.pos`;
or, if it failed,
it returned `null`,
in which case we want to return `null`.

So at the end of the function,
we can just return `state`:

    (in function epilogue)
    '  return state;\n',

Now we just need to ensure
that all of the other expression types
(sequence, terminal strings, ordered choice, negation, parenthesized)
update `state` in a manner analogous
to how calls to nonterminals update `state`.

While we're on the topic of nonterminals,
we should probably define the one predefined nonterminal,
`char`:

    (in support code)
    + 'function parse_char(input, pos) {\n'
    + '  if (pos >= input.length) return null;\n'
    + '  return { pos: pos + 1, val: input[pos] };\n'
    + '}\n'

### Sequence ###

Sequences are relatively simple.
Given a sequence of two expressions `foo bar`,
we first parse `foo` from the current position,
and if that succeeded,
we parse `bar` from the new position.
If it fails,
the sequence as a whole fails,
and there is no current position.

This is one of the things
that is easier to do
if you don’t try to write your grammar with features like `*`,
since it treats sequences of arbitrary numbers of things
as nested sequences of two items,
the innermost of which is empty.

    (in the bare grammar)
    sequence <- term sequence / '->'_ expr / .

The case of an empty sequence
doesn’t update `state` at all.
In the case of a non-empty sequence,
we execute `foo`,
and if `foo` doesn’t set `state` to `null`,
we execute `bar`.

    (in the metacircular compiler-compiler)
    sequence <- foo: term  bar: sequence -> (
                         [foo, '  if (state) {\n', bar, '  }\n'].join(''))
                   / result_expression
                   / -> ('').

The `result_expression` case 
is one of the last things explained,
so ignore it for now.

### Terminal Strings ###

A “terminal” or literal string like `'->'`
either matches some characters in the input
or fails to do so.
Rather than inserting code into every parsing function
to compare parts of the input,
making the parsing functions less readable,
we’ll factor this out into a single “literal” function:

    (in support code)
    + 'function literal(input, pos, string) {\n'
    + '  if (input.substr(pos, string.length) == string) {\n'
    + '    return { pos: pos + string.length, val: string };\n'
    + '  } else return null;\n'
    + '}\n'

So then we just need to emit code to call this function
and update `state` appropriately
when we encounter a terminal string.
As it happens,
the translation from string syntax in the PEG language
to string syntax in JavaScript
is the null transformation.
If we were compiling to some other language,
such as C,
this might pose some difficulty.

    (in the metacircular compiler-compiler)
    string <- '\'' s: stringcontents '\''_ -> (
        ["  state = literal(input, state.pos, '", s, "');\n"].join('')).
    stringcontents <-   !'\\' !'\'' c: char  s: stringcontents -> (c + s)
                    / b: '\\'       c: char  s: stringcontents -> (b + c + s)
                    / -> ('').

As we iterate through the characters or backslash-escapes
inside the string, we convert them to strings —
either by default,
or explicitly by concatenating the backslash
to the character that follows it.
Then we call `literal`
with the current position
and it either returns `null`
or gives us the new position and the value it matched
as our new `state`.

### Ordered Choice ###

Two of the remaining expression types
(ordered choice, negation, but not terminal strings and parenthesized)
can require backtracking.
So we have to save a state
and possibly restore that state.

Here’s how ordered choice works;
negation is fairly similar.
In ordered choice,
if the first alternative succeeds,
we don’t try the others;
but if it fails,
we restore the previously saved state.

This is complicated somewhat
by the fact that we might be inside a parenthesized expression,
so there may be a stack of previously saved states,
even inside the same function.

So on entry to the function, we create a stack:

    (in function prologue)
    '  var stack = [];\n',

The grammar entry treats N-way choices
like `labeled / negation / string / nonterminal / parenthesized`
as nested 2-way choices
like `labeled / (negation / (string / (nonterminal / parenthesized)))`.
This is a little bit needlessly inefficient,
since we’ll be using potentially four stack entries
instead of one,
but it will do for now.

    (in the metacircular compiler-compiler)
    choice <- a: sequence '/'_  b: choice -> (
        ['  stack.push(state);\n',
         a,
         '  if (!state) {\n',
         '    state = stack.pop();\n',
         b,
         '  } else {\n',
         '    stack.pop();\n', // discard unnecessary saved state
         '  }\n'].join(''))
                  / sequence.

It’s only safe to push `state`
rather than a copy of `state`
because we never mutate the existing `state`;
we only make new `state` objects.

### Negation ###

Negation `!x`
is implemented by saving the parse state,
trying to parse `x`,
failing if parsing `x` succeeded,
and otherwise proceeding from the saved parse state.

    (in the metacircular compiler-compiler)
    negation <- '!'_ t: term -> (
        ['  stack.push(state);\n',
         t,
         '  if (state) {\n',
         '    stack.pop();\n',
         '    state = null;\n',
         '  } else {\n',
         '    state = stack.pop();\n',
         '  }\n'].join('')).

You can use a double negative like `!!'->'`
to write a “zero-width positive lookahead assertion” in Perl lingo.
That compiles into this:

    (in the output of the compiler-compiler)
      stack.push(state);
      stack.push(state);
      state = literal(input, state.pos, '->');
      if (state) {
        stack.pop();
        state = null;
      } else {
        state = stack.pop();
      }
      if (state) {
        stack.pop();
        state = null;
      } else {
        state = stack.pop();
      }

The initial `state` is assumed to be non-`null`.
So after the call to `literal`,
`state` is non-`null` iff the next couple of characters were `->`.
Then, after the first `if`,
`state` is non-`null` iff the next couple of characters *weren’t* `->`.
Then, after the second `if`,
it is again non-`null` iff the next couple of characters were `->`.
And if it’s non-`null`,
it’s the `state` you started with.

So that does the right thing,
perhaps a bit verbosely.

### Result Expressions ###

A result expression
gives a JavaScript expression
to evaluate
to get the value that a sequence parses to.
Normally, it uses variable bindings
produced by labels.
The value it returns
may become
the value of the term (if the sequence is inside parentheses)
or the value returned by a whole parsing function.

    (in the metacircular compiler-compiler)
    result_expression <- '->'_ result: expr -> (
        ['  if (state) state.val = ', result, ';\n'].join('')
    ).

The expression is delimited by parentheses `()`.
But the outermost pair of parentheses
are dropped,
while inner parentheses are retained.
This requires two outer `expr` productions
with minimal differences between them:

    expr         <- '('_ e: exprcontents ')'_ -> (e).
    inner        <- '('_ e: exprcontents ')'  -> ('(' + e + ')').
    exprcontents <- c: (!'(' !')' char / inner)  e: exprcontents -> (c + e)
                  / -> ('').

The outer one 
needs to eat up trailing whitespace,
since it might be followed by `/` with space around it or something,
while the inner one 
should avoid eating up trailing whitespace,
since it might be significant in JavaScript
(e.g. it might be inside a string).

### Parenthesized Expressions ###

Parenthesized expressions
don’t need any real special handling,
or rather the special handling
consists of the `stack` variable everything uses to backtrack;
the parentheses are only there
to direct the parser how to parse `/` and `!` and so on.

    parenthesized <- '('_ body: choice ')'_ -> (body).

The Whole Metacircular Compiler-Compiler
----------------------------------------

Here’s the whole thing,
extracted from this document:

    (in the output metacircular compiler-compiler)
    sp <- ' ' / '\n' / '\t'.
    _  <- sp _ / .
    rule    <- n: name _ '<-'_ body: choice '.'_
               -> (["function parse_", n, "(input, pos) {\n",
                      '  var state = { pos: pos };\n',
                      '  var stack = [];\n',
                      body, 
                      '  return state;\n',
                   "}\n"].join('')).
    grammar <- _ r: rule g: grammar -> (r + "\n" + g)
             / _ r: rule -> (r + "\n"
                   + 'function parse_char(input, pos) {\n'
                   + '  if (pos >= input.length) return null;\n'
                   + '  return { pos: pos + 1, val: input[pos] };\n'
                   + '}\n'
                   + 'function literal(input, pos, string) {\n'
                   + '  if (input.substr(pos, string.length) == string) {\n'
                   + '    return { pos: pos + string.length, val: string };\n'
                   + '  } else return null;\n'
                   + '}\n'
               ).
    meta     <- '!' / '\'' / '<-' / '/' / '.' / '(' / ')' / ':' / '->'.
    name     <- c: namechar n: name -> (c + n) / namechar.
    namechar <- !meta !sp char.
    term <- labeled / nonterminal / string / negation / parenthesized.
    nonterminal <- n: name _ -> (
        ['  state = parse_', n, '(input, state.pos);\n'].join('')
    ).
    labeled <- label: name _ ':'_ value: term -> (
        [value, '  if (state) var ', label, ' = state.val;\n'].join('')).
    sequence <- foo: term  bar: sequence -> (
                         [foo, '  if (state) {\n', bar, '  }\n'].join(''))
                   / result_expression
                   / -> ('').
    string <- '\'' s: stringcontents '\''_ -> (
        ["  state = literal(input, state.pos, '", s, "');\n"].join('')).
    stringcontents <-   !'\\' !'\'' c: char  s: stringcontents -> (c + s)
                    / b: '\\'       c: char  s: stringcontents -> (b + c + s)
                    / -> ('').
    choice <- a: sequence '/'_  b: choice -> (
        ['  stack.push(state);\n',
         a,
         '  if (!state) {\n',
         '    state = stack.pop();\n',
         b,
         '  } else {\n',
         '    stack.pop();\n', // discard unnecessary saved state
         '  }\n'].join(''))
                  / sequence.
    negation <- '!'_ t: term -> (
        ['  stack.push(state);\n',
         t,
         '  if (state) {\n',
         '    stack.pop();\n',
         '    state = null;\n',
         '  } else {\n',
         '    state = stack.pop();\n',
         '  }\n'].join('')).
    result_expression <- '->'_ result: expr -> (
        ['  if (state) state.val = ', result, ';\n'].join('')
    ).
    expr         <- '('_ e: exprcontents ')'_ -> (e).
    inner        <- '('_ e: exprcontents ')'  -> ('(' + e + ')').
    exprcontents <- c: (!'(' !')' char / inner)  e: exprcontents -> (c + e)
                  / -> ('').
    parenthesized <- '('_ body: choice ')'_ -> (body).

That’s 66 lines of code,
constituting a compiler
that can compile itself into JavaScript,
if you have a way to execute it.

Bootstrapping to JavaScript
---------------------------

But, to actually execute this compiler-compiler,
you need a version already running,
so you can compile the compiler-compiler to JavaScript.

### Hand-compiling: a blind alley ###

I started by trying to compile it by hand,
using YASnippet,
but after not very long, I gave up on that approach.
Here are the hand-compiled versions of
`sp <- ' ' / '\n' / '\t'.` 
and `_  <- sp _ / .`

    (in the hand-compiled metacircular compiler-compiler)
    function parse_sp(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      state = literal(input, state.pos, ' ');
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = literal(input, state.pos, '\n');
      if (!state) {
        state = stack.pop();
      state = literal(input, state.pos, '\t');
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      return state;
    }
    function parse__(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      state = parse_sp(input, state.pos);
      if (state) {
      state = parse__(input, state.pos);
      }
      if (!state) {
        state = stack.pop();
      } else {
        stack.pop();
      }
      return state;
    }

After thus inflating two lines of grammar 
into 35 lines of JavaScript, 
I knew I needed a better way.
At that rate,
the whole thing would be about 1200 lines.
That’s too much to debug,
even if YASnippet makes it relatively easy to type,
unless there's no easier way.

But there is.

### A Bunch of Functions ###

So, instead,
I'm writing one function 
for each interesting recognition rule from the grammar,
returning the same result expressions
that the parsing function will.
Then I can construct 
a sort of abstract syntax tree of the grammar
out of calls to these functions,
and it will only be a little larger than the grammar itself.

For example, 
the first rule `sp <- ' ' / '\n' / '\t'.`
will become:

    (in the ASTs made of function calls)
    var sp_rule = rule('sp', choice(string(' '), choice(string('\\n'), 
                                                        string('\\t'))));

This is a bit of a cheat;
the innermost choice really parses as
`choice(sequence(string('\\n'), ''), sequence(string('\\t'), ''))`
but I'm hoping that doesn’t matter for now.

Then at the end I can combine all of the variables
into a grammar.

First I need the functions, though.

I’m omitting `sp`
(likewise `_`, `meta`)
because they don’t produce interesting values.

    (in the bunch-of-functions version)
    function rule(n, body) {
      return (["function parse_", n, "(input, pos) {\n",
                      '  var state = { pos: pos };\n',
                      '  var stack = [];\n',
                      body, 
                      '  return state;\n',
                   "}\n"].join(''));
    }

    function grammar2(r, g) {
      return (r + "\n" + g);
    }

    function grammar1(r) {
      return (r + "\n"
                   <<support code>>
               );
    }

I’m omitting `name`
(likewise `expr`, `inner`, `exprcontents`, `stringcontents`)
because it just copies a character string from the input
into the output.
I can do that myself.
And I’m omitting `term`
because it just returns one of its children's values.

    function nonterminal(n) {
      return ['  state = parse_', n, '(input, state.pos);\n'].join('');
    }
    function labeled(label, value) {
      return [value, '  if (state) var ', label, ' = state.val;\n'].join('');
    }
    function sequence(foo, bar) {
      return [foo, '  if (state) {\n', bar, '  }\n'].join('');
    }
    function string(s) {
      return ["  state = literal(input, state.pos, '", s, "');\n"].join('');
    }
    function choice(a, b) {
      return [
         '  stack.push(state);\n',
         a,
         '  if (!state) {\n',
         '    state = stack.pop();\n',
         b,
         '  } else {\n',
         '    stack.pop();\n', // discard unnecessary saved state
         '  }\n'].join('');
    }
    function negation(t) {
      return [
         '  stack.push(state);\n',
         t,
         '  if (state) {\n',
         '    stack.pop();\n',
         '    state = null;\n',
         '  } else {\n',
         '    state = stack.pop();\n',
         '  }\n'].join('');
    }
    function result_expression(result) {
      return ['  state.val = ', result, ';\n'].join('');
    }

We’ll also need the support code
from the `grammar` rule.

    function parse_char(input, pos) {
      if (pos >= input.length) return null;
      return { pos: pos + 1, val: input[pos] };
    }
    function literal(input, pos, string) {
      if (input.substr(pos, string.length) == string) {
        return { pos: pos + string.length, val: string };
      } else return null;
    }

Then,
after all those functions are defined,
we can call them to build up the ASTs.

    <<the ASTs made of function calls>>

The rule for `_` is quite straightforward:

    (in the ASTs made of function calls)
    var __rule = rule('_',
                      choice(sequence(nonterminal('sp'), nonterminal('_')), 
                             ''));

The rule for `rule`
contains a rather long sequence,
which will be treated 
as a deeply nested bunch
of two-element sequences.
But it’s hard to read and write it that way,
so I’m going to define a helper function `nseq`
to make a sequence of an arbitrary number
of sequence elements.

    function nseq() {
      var rv = arguments[arguments.length-1];
      for (var ii = arguments.length-2; ii >= 0; ii--)
        rv = sequence(arguments[ii], rv);
      return rv;
    }

This will fail (returning `null`) 
if we call it with no arguments,
so let’s be sure not do that.
Now we can define the rule for `rule`:

    var rule_rule = rule('rule',
        nseq(labeled('n', nonterminal('name')), nonterminal('_'),
             string('<-'), nonterminal('_'),
             labeled('body', nonterminal('choice')), 
             string('.'), nonterminal('_'),
             result_expression(
                "[\"function parse_\", n, \"(input, pos) {\\n\",\n" +
                "                      '  var state = { pos: pos };\\n',\n" +
                "                      '  var stack = [];\\n',\n" +
                "                      body, \n" +
                "                      '  return state;\\n',\n" +
                "                   \"}\\n\"].join('')")));

`rule_rule` is clearly pretty verbose;
it's 12 lines, 
and the corresponding `rule` function is 8 lines,
for a total of 20 lines for the “hand-compiled” version
of the original 7-line `rule` rule.
That’s a manageable expansion factor of about 3×.

So, on to `grammar`.
I’ve played fast and loose
with leading whitespace here,
in order to retain some modicum of readability.

    var grammar_rule = rule('grammar',
        choice(
            nseq(nonterminal('_'),
                 labeled('r', nonterminal('rule')),
                 labeled('g', nonterminal('grammar')),
                 result_expression('r + "\\n" + g')),
            nseq(nonterminal('_'),
                 labeled('r', nonterminal('rule')),
                 result_expression('r + "\\n"\n' +
            "+ 'function parse_char(input, pos) {\\n'\n" +
            "+ '  if (pos >= input.length) return null;\\n'\n" +
            "+ '  return { pos: pos + 1, val: input[pos] };\\n'\n" +
            "+ '}\\n'\n" +
            "+ 'function literal(input, pos, string) {\\n'\n" +
            "+ '  if (input.substr(pos, string.length) == string) {\\n'\n" +
            "+ '    return { pos: pos + string.length, val: string };\\n'\n" +
            "+ '  } else return null;\\n'\n" +
            "+ '}\\n'"))));

The quoting of the support code
is kind of confusing;
the original is one long string,
containing a bunch of `\n` newlines,
broken up into lines for readability,
joined by the `+` operator.
This version
is also one long string,
containing the lines of the original long string,
also broken up into lines for readability,
joined by the `+` operator.
So there are two levels of quoting.
The inner level has the `+` on the left and uses single quotes `''`,
and the outer level has the `+` on the right and uses double quotes `""`.

The next rule is `meta`,
and it has a lot of `choice`s.
So we define something like `nseq`,
but for `choice`s.

    function nchoice() {
      var rv = arguments[arguments.length-1];
      for (var ii = arguments.length-2; ii >= 0; ii--)
        rv = choice(arguments[ii], rv);
      return rv;
    }

    var meta_rule = rule('meta',
      nchoice(string('!'), string('\\\''), string('<-'), string('/'),
              string('.'), string('('),    string(')'),  string(':'),
              string('->')));


The next few rules
are straightforward translations from the grammar.

    var name_rule = rule('name', 
        choice(nseq(labeled('c', nonterminal('namechar')),
                    labeled('n', nonterminal('name')),
                    result_expression('c + n')),
               nonterminal('namechar')));
    var namechar_rule = rule('namechar',
        nseq(negation(nonterminal('meta')),
             negation(nonterminal('sp')), nonterminal('char')));
    var term_rule = rule('term',
        nchoice(nonterminal('labeled'), nonterminal('nonterminal'), 
                nonterminal('string'),  nonterminal('negation'),
                nonterminal('parenthesized')));
    var nonterminal_rule = rule('nonterminal',
        nseq(labeled('n', nonterminal('name')), nonterminal('_'),
             result_expression("['  state = parse_', n, " +
                               "'(input, state.pos);\\n'].join('')")));
    var labeled_rule = rule('labeled',
        nseq(labeled('label', nonterminal('name')), nonterminal('_'),
             string(':'), nonterminal('_'),
             labeled('value', nonterminal('term')),
             result_expression("[value, '  if (state) var ', " +
                               "label, ' = state.val;\\n'].join('')")));
    var sequence_rule = rule('sequence',
        nchoice(nseq(labeled('foo', nonterminal('term')),
                     labeled('bar', nonterminal('sequence')),
                     result_expression("[foo, '  if (state) {\\n', " +
                                       "bar, '  }\\n'].join('')")),
                nonterminal('result_expression'),
                sequence(result_expression("''"))));

That’s 29 lines,
transliterating 12 lines from the grammar,
and now the transliteration is halfway done.

    var string_rule = rule('string',
        nseq(string("\\'"), labeled('s', nonterminal('stringcontents')),
             string("\\'"), nonterminal('_'),
             result_expression('["  state = literal(input, state.pos, ' +
                               '\'", s, "\');\\n"].join(\'\')')));
    var stringcontents_rule = rule('stringcontents',
        nchoice(nseq(negation(string("\\\\")), negation(string("\\'")),
                     labeled('c', nonterminal('char')),
                     labeled('s', nonterminal('stringcontents')),
                     result_expression('c + s')),
                nseq(labeled('b', string("\\\\")),
                     labeled('c', nonterminal('char')),
                     labeled('s', nonterminal('stringcontents')),
                     result_expression('b + c + s')),
                result_expression("''")));

For `choice` I’m omitting not only whitespace
but also a comment.

    var choice_rule = rule('choice',
        choice(nseq(labeled('a', nonterminal('sequence')),
                    string('/'), nonterminal('_'),
                    labeled('b', nonterminal('choice')),
                    result_expression(
                        "['  stack.push(state);\\n',\n" +
                        " a,\n" +
                        " '  if (!state) {\\n',\n" +
                        " '    state = stack.pop();\\n',\n" +
                        " b,\n" +
                        " '  } else {\\n',\n" +
                        " '    stack.pop();\\n',\n" +
                        " '  }\\n'].join('')")),
               nonterminal('sequence')));
    var negation_rule = rule('negation',
        nseq(string('!'), nonterminal('_'), labeled('t', nonterminal('term')),
             result_expression(
                        "['  stack.push(state);\\n',\n" +
                        " t,\n" +
                        " '  if (state) {\\n',\n" +
                        " '    stack.pop();\\n',\n" +
                        " '    state = null;\\n',\n" +
                        " '  } else {\\n',\n" +
                        " '    state = stack.pop();\\n',\n" +
                        " '  }\\n'].join('')")));
    var result_expression_rule = rule('result_expression',
        nseq(string('->'), nonterminal('_'), 
             labeled('result', nonterminal('expr')),
             result_expression("['  if (state) state.val = ', " +
                               "result, ';\\n'].join('')")));
    var expr_rule = rule('expr',
        nseq(string('('), nonterminal('_'),
             labeled('e', nonterminal('exprcontents')),
             string(')'), nonterminal('_'),
             result_expression('e')));
    var inner_rule = rule('inner',
        nseq(string('('), nonterminal('_'),
             labeled('e', nonterminal('exprcontents')),
             string(')'),
             result_expression("'(' + e + ')'")));
    var exprcontents_rule = rule('exprcontents',
        choice(
            nseq(labeled('c',
                         choice(nseq(negation(string('(')),
                                     negation(string(')')),
                                     nonterminal('char')),
                                nonterminal('inner'))),
                 labeled('e', nonterminal('exprcontents')),
                 result_expression('c + e')),
            result_expression("''")));
    var parenthesized_rule = rule('parenthesized',
        nseq(string('('), nonterminal('_'),
             labeled('body', nonterminal('choice')),
             string(')'), nonterminal('_'),
             result_expression('body')));

So that’s all the rules.
Now we just need to assemble them into a grammar,
using a technique similar to `nseq` and `nchoice`.

    function ngrammar() {
      var rv = grammar1(arguments[arguments.length-1]);
      for (var ii = arguments.length-2; ii >= 0; ii--)
        rv = grammar2(arguments[ii], rv);
      return rv;
    }

    var all_rules = ngrammar(sp_rule, __rule, rule_rule, grammar_rule, 
                             meta_rule, name_rule, namechar_rule, term_rule,
                             nonterminal_rule, labeled_rule, sequence_rule,
                             string_rule, stringcontents_rule, choice_rule,
                             negation_rule, result_expression_rule, expr_rule,
                             inner_rule, exprcontents_rule, parenthesized_rule);

Now the variable `all_rules`
has a working parser in it
in JavaScript.

### The Output Parser in JavaScript ###

Here’s what’s in `all_rules`
after a couple of iterations.
It’s ten pages long (660 lines),
and the compile takes 
about 3–5 seconds on my machine.
I’m including it here
to facilitate future bootstrapping.

    (in output.js)
    function parse_sp(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      state = literal(input, state.pos, ' ');
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = literal(input, state.pos, '\n');
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      state = literal(input, state.pos, '\t');
      if (state) {
      }
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      return state;
    }

    function parse__(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      state = parse_sp(input, state.pos);
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      }
      }
      if (!state) {
        state = stack.pop();
      } else {
        stack.pop();
      }
      return state;
    }

    function parse_rule(input, pos) {
      var state = { pos: pos };
      var stack = [];
      state = parse_name(input, state.pos);
      if (state) var n = state.val;
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      state = literal(input, state.pos, '<-');
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      state = parse_choice(input, state.pos);
      if (state) var body = state.val;
      if (state) {
      state = literal(input, state.pos, '.');
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      if (state) state.val = ["function parse_", n, "(input, pos) {\n",
                      '  var state = { pos: pos };\n',
                      '  var stack = [];\n',
                      body, 
                      '  return state;\n',
                   "}\n"].join('');
      }
      }
      }
      }
      }
      }
      }
      return state;
    }

    function parse_grammar(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      state = parse__(input, state.pos);
      if (state) {
      state = parse_rule(input, state.pos);
      if (state) var r = state.val;
      if (state) {
      state = parse_grammar(input, state.pos);
      if (state) var g = state.val;
      if (state) {
      if (state) state.val = r + "\n" + g;
      }
      }
      }
      if (!state) {
        state = stack.pop();
      state = parse__(input, state.pos);
      if (state) {
      state = parse_rule(input, state.pos);
      if (state) var r = state.val;
      if (state) {
      if (state) state.val = r + "\n"
                   + 'function parse_char(input, pos) {\n'
                   + '  if (pos >= input.length) return null;\n'
                   + '  return { pos: pos + 1, val: input[pos] };\n'
                   + '}\n'
                   + 'function literal(input, pos, string) {\n'
                   + '  if (input.substr(pos, string.length) == string) {\n'
                   + '    return { pos: pos + string.length, val: string };\n'
                   + '  } else return null;\n'
                   + '}\n'
               ;
      }
      }
      } else {
        stack.pop();
      }
      return state;
    }

    function parse_meta(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      state = literal(input, state.pos, '!');
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = literal(input, state.pos, '\'');
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = literal(input, state.pos, '<-');
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = literal(input, state.pos, '/');
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = literal(input, state.pos, '.');
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = literal(input, state.pos, '(');
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = literal(input, state.pos, ')');
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = literal(input, state.pos, ':');
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      state = literal(input, state.pos, '->');
      if (state) {
      }
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      return state;
    }

    function parse_name(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      state = parse_namechar(input, state.pos);
      if (state) var c = state.val;
      if (state) {
      state = parse_name(input, state.pos);
      if (state) var n = state.val;
      if (state) {
      if (state) state.val = c + n;
      }
      }
      if (!state) {
        state = stack.pop();
      state = parse_namechar(input, state.pos);
      if (state) {
      }
      } else {
        stack.pop();
      }
      return state;
    }

    function parse_namechar(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      state = parse_meta(input, state.pos);
      if (state) {
        stack.pop();
        state = null;
      } else {
        state = stack.pop();
      }
      if (state) {
      stack.push(state);
      state = parse_sp(input, state.pos);
      if (state) {
        stack.pop();
        state = null;
      } else {
        state = stack.pop();
      }
      if (state) {
      state = parse_char(input, state.pos);
      if (state) {
      }
      }
      }
      return state;
    }

    function parse_term(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      state = parse_labeled(input, state.pos);
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = parse_nonterminal(input, state.pos);
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = parse_string(input, state.pos);
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = parse_negation(input, state.pos);
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      state = parse_parenthesized(input, state.pos);
      if (state) {
      }
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      return state;
    }

    function parse_nonterminal(input, pos) {
      var state = { pos: pos };
      var stack = [];
      state = parse_name(input, state.pos);
      if (state) var n = state.val;
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      if (state) state.val = ['  state = parse_', n, '(input, state.pos);\n'].join('')
    ;
      }
      }
      return state;
    }

    function parse_labeled(input, pos) {
      var state = { pos: pos };
      var stack = [];
      state = parse_name(input, state.pos);
      if (state) var label = state.val;
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      state = literal(input, state.pos, ':');
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      state = parse_term(input, state.pos);
      if (state) var value = state.val;
      if (state) {
      if (state) state.val = [value, '  if (state) var ', label, ' = state.val;\n'].join('');
      }
      }
      }
      }
      }
      return state;
    }

    function parse_sequence(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      state = parse_term(input, state.pos);
      if (state) var foo = state.val;
      if (state) {
      state = parse_sequence(input, state.pos);
      if (state) var bar = state.val;
      if (state) {
      if (state) state.val = [foo, '  if (state) {\n', bar, '  }\n'].join('');
      }
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = parse_result_expression(input, state.pos);
      if (state) {
      }
      if (!state) {
        state = stack.pop();
      if (state) state.val = '';
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      return state;
    }

    function parse_string(input, pos) {
      var state = { pos: pos };
      var stack = [];
      state = literal(input, state.pos, '\'');
      if (state) {
      state = parse_stringcontents(input, state.pos);
      if (state) var s = state.val;
      if (state) {
      state = literal(input, state.pos, '\'');
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      if (state) state.val = ["  state = literal(input, state.pos, '", s, "');\n"].join('');
      }
      }
      }
      }
      return state;
    }

    function parse_stringcontents(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      stack.push(state);
      state = literal(input, state.pos, '\\');
      if (state) {
        stack.pop();
        state = null;
      } else {
        state = stack.pop();
      }
      if (state) {
      stack.push(state);
      state = literal(input, state.pos, '\'');
      if (state) {
        stack.pop();
        state = null;
      } else {
        state = stack.pop();
      }
      if (state) {
      state = parse_char(input, state.pos);
      if (state) var c = state.val;
      if (state) {
      state = parse_stringcontents(input, state.pos);
      if (state) var s = state.val;
      if (state) {
      if (state) state.val = c + s;
      }
      }
      }
      }
      if (!state) {
        state = stack.pop();
      stack.push(state);
      state = literal(input, state.pos, '\\');
      if (state) var b = state.val;
      if (state) {
      state = parse_char(input, state.pos);
      if (state) var c = state.val;
      if (state) {
      state = parse_stringcontents(input, state.pos);
      if (state) var s = state.val;
      if (state) {
      if (state) state.val = b + c + s;
      }
      }
      }
      if (!state) {
        state = stack.pop();
      if (state) state.val = '';
      } else {
        stack.pop();
      }
      } else {
        stack.pop();
      }
      return state;
    }

    function parse_choice(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      state = parse_sequence(input, state.pos);
      if (state) var a = state.val;
      if (state) {
      state = literal(input, state.pos, '/');
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      state = parse_choice(input, state.pos);
      if (state) var b = state.val;
      if (state) {
      if (state) state.val = ['  stack.push(state);\n',
         a,
         '  if (!state) {\n',
         '    state = stack.pop();\n',
         b,
         '  } else {\n',
         '    stack.pop();\n', // discard unnecessary saved state
         '  }\n'].join('');
      }
      }
      }
      }
      if (!state) {
        state = stack.pop();
      state = parse_sequence(input, state.pos);
      if (state) {
      }
      } else {
        stack.pop();
      }
      return state;
    }

    function parse_negation(input, pos) {
      var state = { pos: pos };
      var stack = [];
      state = literal(input, state.pos, '!');
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      state = parse_term(input, state.pos);
      if (state) var t = state.val;
      if (state) {
      if (state) state.val = ['  stack.push(state);\n',
         t,
         '  if (state) {\n',
         '    stack.pop();\n',
         '    state = null;\n',
         '  } else {\n',
         '    state = stack.pop();\n',
         '  }\n'].join('');
      }
      }
      }
      return state;
    }

    function parse_result_expression(input, pos) {
      var state = { pos: pos };
      var stack = [];
      state = literal(input, state.pos, '->');
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      state = parse_expr(input, state.pos);
      if (state) var result = state.val;
      if (state) {
      if (state) state.val = ['  if (state) state.val = ', result, ';\n'].join('')
    ;
      }
      }
      }
      return state;
    }

    function parse_expr(input, pos) {
      var state = { pos: pos };
      var stack = [];
      state = literal(input, state.pos, '(');
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      state = parse_exprcontents(input, state.pos);
      if (state) var e = state.val;
      if (state) {
      state = literal(input, state.pos, ')');
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      if (state) state.val = e;
      }
      }
      }
      }
      }
      return state;
    }

    function parse_inner(input, pos) {
      var state = { pos: pos };
      var stack = [];
      state = literal(input, state.pos, '(');
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      state = parse_exprcontents(input, state.pos);
      if (state) var e = state.val;
      if (state) {
      state = literal(input, state.pos, ')');
      if (state) {
      if (state) state.val = '(' + e + ')';
      }
      }
      }
      }
      return state;
    }

    function parse_exprcontents(input, pos) {
      var state = { pos: pos };
      var stack = [];
      stack.push(state);
      stack.push(state);
      stack.push(state);
      state = literal(input, state.pos, '(');
      if (state) {
        stack.pop();
        state = null;
      } else {
        state = stack.pop();
      }
      if (state) {
      stack.push(state);
      state = literal(input, state.pos, ')');
      if (state) {
        stack.pop();
        state = null;
      } else {
        state = stack.pop();
      }
      if (state) {
      state = parse_char(input, state.pos);
      if (state) {
      }
      }
      }
      if (!state) {
        state = stack.pop();
      state = parse_inner(input, state.pos);
      if (state) {
      }
      } else {
        stack.pop();
      }
      if (state) var c = state.val;
      if (state) {
      state = parse_exprcontents(input, state.pos);
      if (state) var e = state.val;
      if (state) {
      if (state) state.val = c + e;
      }
      }
      if (!state) {
        state = stack.pop();
      if (state) state.val = '';
      } else {
        stack.pop();
      }
      return state;
    }

    function parse_parenthesized(input, pos) {
      var state = { pos: pos };
      var stack = [];
      state = literal(input, state.pos, '(');
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      state = parse_choice(input, state.pos);
      if (state) var body = state.val;
      if (state) {
      state = literal(input, state.pos, ')');
      if (state) {
      state = parse__(input, state.pos);
      if (state) {
      if (state) state.val = body;
      }
      }
      }
      }
      }
      return state;
    }

    function parse_char(input, pos) {
      if (pos >= input.length) return null;
      return { pos: pos + 1, val: input[pos] };
    }
    function literal(input, pos, string) {
      if (input.substr(pos, string.length) == string) {
        return { pos: pos + string.length, val: string };
      } else return null;
    }

TODO
----

- memoization
- performance measurement
- profiling
- re-add repetition `+` and `*`
- factor out loopbody?  like,  
  loopbody <- term: body -> (loop body code).  
  zero_or_more <- loopbody: body -> (body).
  one_or_more <- loopbody: body -> (body + 'if ...').

Other Interesting PEGs
----------------------

[Ierusalemschy][ier] gives this grammar
for parsing Excel-style CSV files:

    (in the LPEG notation with captures)
    record <- (<field> (',' <field>)*)->{} (%nl / !.)
    field <- <escaped> / <nonescaped>
    nonescaped <- { [^,"%nl]* }
    escaped <- '"' {~ ([^"] / '""'->'"')* ~} '"'

The `{}` capture pieces of text
and `{~ ~}` capture and replace them.
`*` is for repetition, 
`%nl` is `'\n'`,
`""` are equivalent to `''`,
`.` is our `char`,
`[abc]` is a character class equivalent to `( 'a' / 'b' / 'c' )`,
and `->{}` means “make a list of the results”.
In the notation I’ve used for PEGs here,
without repetition features,
this looks like this:

    (in csv.peg)
    record <- d: (f: field ',' r: record -> ([f].concat(r)) 
                / f: field               -> ([f])) ('\n' / !char)
              -> (d).
    field <- escaped / nonescaped.
    normal_char <- !',' !'"' !'\n' char.
    nonescaped <- c: normal_char s: nonescaped -> (c + s) / normal_char.
    escaped_inner_char <- !'"' char / '""' -> ('"').
    escaped_inner <- c: escaped_inner_char s: escaped_inner -> (c + s) 
                   / escaped_inner_char.
    escaped <- '"' s: escaped_inner '"' -> (s).

That’s 2½ times as big,
which is unreasonable.
If we have `*` repetition that makes JavaScript Arrays,
we can write it with only a bit more ugliness
than in LPEG:

    (in csvstar.peg)
    record <- h: field t: (',' field)* ('\n' / !char) -> ([h].concat(t)).
    field <- escaped / nonescaped.
    nonescaped <- s: (!',' !'"' !'\n' char)* -> (s.join('')).
    escaped <- '"' s: (!'"' char / '""' -> ('"'))* '"' -> (s.join('')).

[ier]: http://www.inf.puc-rio.br/~roberto/docs/peg.pdf "A Text Pattern-Matching Tool based on Parsing Expression Grammars, 2008, SP&amp;E"

Thanks
------

Thanks to D. Val Schorre for inventing META-II,
of which this is a refinement,
in 1964 or a bit before;
to Bob M. McClure for inventing [TMG](http://www.multicians.org/tmg.html),
the TransMoGrifier,
also in 1964,
and to Doug McIlroy for maintaining it afterwards,
which not only carried META-II forward,
but also 
[helped Thompson write B](http://plan9.bell-labs.com/who/dmr/chist.html) 
which became C;
to Romuald Ireneus 'Scibor-Marchocki, who 
[apparently ported TMG to 
TMGL](http://www.geocities.com/ResearchTriangle/2363/tmg011.html);
to Bryan Ford for resurrecting TMG’s parsing schema
and enhancing it into the form of parsing expression grammars,
in 2002;
to Alan Kay for bringing META-II back to public attention;
to Alessandro Warth and Yoshiki Ohshima for developing OMeta
and showing that PEGs can be extended
to a wide variety of non-parsing tasks.

To [Aristotle Pagaltzis](http://plasmasturm.org/)
for innumerable improvements 
to the readability and correctness
of this document.

To Andy Isaacson
for further improvements
in the readability of this document.

<link rel="stylesheet" href="style.css" />
<style type="text/css">
p code {background-color: #f0f0f0; border: 1px solid #e3e3e3; padding: 1px;}
</style>