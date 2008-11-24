PEGs in a PEG
=============

So I was reading Bryan Ford’s dissertation
about parsing expression grammars and packrat parsers,
and I thought it would be fun to implement them
and see how easy they really were.

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
    stringchar     <- !'\\' char / '\\' char.
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

    stringcontents <- (!'\\' char / '\\' char) stringcontents / .

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
    string  <- '\'' (!'\\' char / '\\' char)* '\''.
    meta    <- '!' / '\'' / '<-' / '/' / '.' / '+' / '*' / '(' / ')'.
    name    <- (!meta !sp char)+.

That shrinks the grammar considerably,
while significantly expanding 
the expressiveness of the grammar language it describes.

Adding Actions
--------------

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
    sequence       <- term sequence / ('->'_ expr / ) / .
    expr           <- '('_ exprcontents ')'_.
    exprcontents   <- (!'(' !')' char / expr) exprcontents / .
    term           <- name _ ':'_ term / '!'_ term / string / name _ 
                    / '('_ choice ')'_.
    string         <- '\'' stringcontents '\''.
    stringcontents <- !'\\' char stringcontents / '\\' char stringcontents / .
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
                   "\n}\n"].join('')).
    grammar <- _ r: rule g: grammar -> (r + "\n" + g)
             / _ r: rule -> (r + "\n" +
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
    term <- labeled / negation / string / nonterminal / parenthesized.
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
(sequence, ordered choice, negation, terminal strings, parenthesized)
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

XXX fixed up to here to not mainstream repetition or put names later

### Sequence ###

Sequences are relatively simple.
Given a sequence of two expressions `foo bar`,
we first parse `foo` from the current position,
and if that succeeded,
we parse `bar` from the new position.
If it fails,
the sequence as a whole fails,
and there is no current position.

This is easier to do
in the version of the grammar that doesn’t use `*`
to define `sequence`,
since it treats sequences of arbitrary numbers of things
as nested sequences of two items,
the innermost of which is empty.

    (in the bare grammar)
    sequence <- qterm sequence / .

The case of an empty sequence
doesn’t update `state` at all.
In the case of a non-empty sequence,
we execute `foo`,
and if `foo` doesn’t set `state` to `null`,
we execute `bar`.

    (in the metacircular compiler-compiler)
    sequence <- qterm: foo sequence: bar -> (
                         [foo, '  if (state) {\n', bar, '}\n'].join(''))
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
    string <- '\'' (!'\\' char / '\\': a char: b -> (a + b))*: string '\'' -> (
        ["  state = literal(input, state.pos, '", string.join(''), "');\n"
        ].join('')).

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

The remaining expression types
(ordered choice, negation, and repetition with `+` and `*`)
all can require backtracking.
So we have to save a state
and possibly restore that state.

The paradigm for them all
is ordered choice, or alternation.
If the first alternative succeeds,
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

We can use the same trick
as with `sequence`
to transform an N-way choice 
like `negation / string / terminal / parenthesized`
into a nested 2-way choice
like `negation / (string / (terminal / parenthesized))`.
This is a little bit needlessly inefficient,
since we’ll be using potentially three stack entries
instead of one,
but it will do for now.

    (in the metacircular compiler-compiler)
    choice <- sequence: a '/'_ choice: b -> (
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
    negation <- '!'_ qterm: t -> (
        ['  stack.push(state);\n',
         t,
         '  if (state) {\n',
         '    stack.pop();\n',
         '    state = null;\n',
         '  } else {\n',
         '    state = stack.pop();\n',
         '  }\n'].join('')).

`negation` is defined as negating a `qterm`
because `!x+` has two possible stupid meanings:
if `!` negates a `term`, then it is equivalent to `(!x)+`,
which will try to match `x` at the same point repeatedly until it succeeds,
which will either happen never or immediately;
but if `!` negates a `qterm`, then it is equivalent to `!(x+)`,
which is just a particularly obtuse way to write `!x`.

You can use a double negative like `!!'->'`
to write a “zero-width positive lookahead assertion” in Perl lingo.
So that should compile into this:

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
`state` is `null` iff the next couple of characters weren’t `->`.
Then, after the first `if`,
`state` is `null` iff the next couple of characters *were* `->`.
Then, after the second `if`,
it is again `null` iff the next couple of characters weren’t `->`.
And if it isn’t `null`,
it’s the `state` you started with.

### Repetition with `*` ###

It is clearly possible
to factor out repetitions
into uses of a “helper” production,
like the `stringcontents`/`stringchar` and `name`/`namechar` productions
in the first grammar given.

But it is also possible
to implement `*` and `+` directly,
and I think that is simpler.

The template for `*` is fairly familiar:

    (in the metacircular compiler-compiler)
    zero_or_more <- term: body '*' -> ([
        <<the implementation of *>>
    ].join('')).

To implement `*`, we write a loop.
As long as we aren’t failing,
we continue the loop.
As soon as we fail,
we exit the loop
and backtrack to the state
when we started the latest iteration of the loop.

We’ll use the same stack for repetition
that we used for ordered choice.
We’ll accumulate the values produced by `body`
on different iterations of the loop
in the `val` property of the state on the stack.

    (in the implementation of *)
    '  stack.push({pos: state.pos, val: []});\n',
    '  for (;;) {\n',
         body,
    '    if (!state) break;\n',
    '    var loopstate = stack[stack.length - 1];\n',
    '    loopstate.val.push(state.val);\n',
    '    loopstate.pos = state.pos;\n',
    '  }\n',
    '  state = stack.pop()\n'

If there are multiple loops in a function,
there will be multiple `var loopstate` declarations,
but that won’t create multiple independent `loopstate` variables,
because JavaScript is stupid that way;
that’s why we store `loopstate` on `stack`, annoying as it is.
However,
it’s apparently valid 
to have multiple declarations of the same variable!
So we don’t need to stick it in the function prologue.

### Repetition with `+` ###

The only difference between `+` and `*`
is what they do in the case of no iterations.
`*` evaluates to an empty list;
`+` fails.

So a really simple way to implement `+`
is by performing `*`,
and then failing if it evaluated to an empty list:

    (in the metacircular compiler-compiler)
    one_or_more <- term: body '+' -> ([
        <<the implementation of *>>
        ,'  if (state.val.length == 0) state = null;\n'
    ].join('')).

### Result Expressions ###

A result expression
gives a JavaScript expression
to evaluate
to get the value that a sequence parses to.
Normally, it uses variable bindings
produced by labels.
That may become
the value of the term (if the sequence is inside parentheses)
or the value returned by a whole parsing function.

    (in the metacircular compiler-compiler)
    result_expression <- '->' expr: result -> (
        ['  state.val = ', result, ';\n'].join('')
    ).

The expression is delimited by parentheses `()`.
But the outermost pair of parentheses
are dropped,
while inner parentheses are retained.
This requires two productions
with minimal differences between them:

    expr       <- '('_ (!'(' !')' char / inner_expr)*: contents ')'_ 
                  -> (contents.join('')).
    inner_expr <- '('_ (!'(' !')' char / inner_expr)*: contents ')'_ 
                  -> ('(' + contents.join('') + ')').

### Parenthesized Expressions ###

Parenthesized expressions
don’t need any real special handling,
or rather the special handling
consists of the `stack` variable everything uses to backtrack;
the parentheses are only there
to direct the parser how to parse `/` and `*` and so on.

    parenthesized <- '('_ choice: body ')'_ -> (body).

The Whole Metacircular Compiler-Compiler
----------------------------------------

Here’s the whole thing,
extracted from this document:
(note, this is out of date, needs updating)

    (in the output metacircular compiler-compiler)
    sp <- ' ' / '\n' / '\t'.
    _ <- sp*.
    grammar <- _ (name: name _ '<-' _ choice: body '.' _
                  -> (["function parse_", name, "(input, pos) {\n",
                         '  var state = { pos: pos };',
                         '  var stack = [];\n',
                         body, 
                         '  return state;',
                       "\n}\n"].join('')))+: functions
               -> (functions.join("\n")
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
    meta     <- '!' / '\'' / '<-' / '/' / '.' / '+' / '*' / '(' / ')' 
              / ':' / '->'.
    name     <- (!meta !sp char)+: chars -> (chars.join('')).
    term <- negation / string / nonterminal / parenthesized.
    nonterminal <- name: name _ -> (
        ['  state = parse_', name, '(input, state.pos);\n'].join('')
    ).
    label <- ':'_ name: label _ -> (
        '  if (state) var ', label, ' = state.val;\n').
    bare_qterm = zero_or_more / one_or_more / term.
    qterm <- bare_qterm: a label: b -> (a + b) / bare_qterm.
    sequence <- qterm: foo sequence: bar -> (
                         [foo, '  if (state) {\n', bar, '}\n'].join(''))
                   / result_expression
                   / -> ('').
    string <- '\'' (!'\\' char / '\\': a char: b -> (a + b))*: string '\'' -> (
        ["  state = literal(input, state.pos, '", string.join(''), "');\n"
        ].join('')).
    choice <- sequence: a '/'_ choice: b -> (
        ['  stack.push(state);\n',
         a,
         '  if (!state) {\n',
         '    state = stack.pop();\n',
         b,
         '  } else {\n',
         '    stack.pop();\n', // discard unnecessary saved state
         '  }\n'].join(''))
                  / sequence.
    negation <- '!'_ qterm: t -> (
        ['  stack.push(state);\n',
         t,
         '  if (state) {\n',
         '    stack.pop();\n',
         '    state = null;\n',
         '  } else {\n',
         '    state = stack.pop();\n',
         '  }\n'].join('')).
    zero_or_more <- term: body '*' -> ([
        '  stack.push({pos: state.pos, val: []});\n',
        '  for (;;) {\n',
             body,
        '    if (!state) break;\n',
        '    var loopstate = stack[stack.length - 1];\n',
        '    loopstate.val.push(state.val);\n',
        '    loopstate.pos = state.pos;\n',
        '  }\n',
        '  state = stack.pop()\n'
    ].join('')).
    one_or_more <- term: body '+' -> ([
        '  stack.push({pos: state.pos, val: []});\n',
        '  for (;;) {\n',
             body,
        '    if (!state) break;\n',
        '    var loopstate = stack[stack.length - 1];\n',
        '    loopstate.val.push(state.val);\n',
        '    loopstate.pos = state.pos;\n',
        '  }\n',
        '  state = stack.pop()\n'
        ,'  if (state.val.length == 0) state = null;\n'
    ].join('')).
    result_expression <- '->' expr: result -> (
        ['  state.val = ', result, ';\n'].join('')
    ).
    expr       <- '('_ (!'(' !')' char / inner_expr)*: contents ')'_ 
                  -> (contents.join('')).
    inner_expr <- '('_ (!'(' !')' char / inner_expr)*: contents ')'_ 
                  -> ('(' + contents.join('') + ')').
    parenthesized <- '('_ choice: body ')'_ -> (body).

That’s 88 lines of code,
constituting a compiler
that could compile itself into JavaScript,
if only it worked.

TODO
----

- arrays (done)
- move labels to before expressions, as in Ford’s thesis, rather than
  after (or possibly use [label])
- fixing `+` (done)
- result expressions (done)
- factor out loopbody?  like,  
  loopbody <- term: body -> (loop body code).  
  zero_or_more <- loopbody: body -> (body).
  one_or_more <- loopbody: body -> (body + 'if ...').
- memoization
- hand-compile it
- test it
- recompile it with itself
- fix bugs
- include self-compiled version here for bootstrapping

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
