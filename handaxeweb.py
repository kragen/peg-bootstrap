#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Handaxeweb: a minimal literate programming system.

This is inspired by a literate programming system in ten or so lines
of awk that I saw back in 1995 or so, and of course also by noweb and
the Haskell ‘Bird Style’ literate program convention.  I would have
just used the little awk script if I could find it.

Any text that is indented four or more spaces is program text, from
which the first four spaces will be stripped off; anything else is a
comment.

That’s all you need to know to use it, but two directives provide
support for reordering, if an indented line says just ‘(in some chunk
name)’, then that line will be dropped and all following program lines
will go into ‘some chunk name’ until the next such directive.  And to
include the contents of that chunk name somewhere else, any line that
says ‘<<some chunk name>>’, with at least four spaces of indentation
before it, will be replaced by that chunk’s contents, consistently
indented.

If your editor doesn’t like to make lines consisting just of four
spaces, then tough titties, you aren’t going to get blank lines in
your output.

(Aha!  I found the awk program I was thinking of, the one that
inspired me, too late to save me any work.  Phil Bewig posted it to
comp.programming.literate on 1996-05-27, under the title “The Essence
of Literate Programming”, message-id <pbewigDs1Ewq.G03@netcom.com>.
Here’s the program and a bit of commentary, extracted from that post:

    (in the awk script)
    /^<<.+>>=$/ {
        name = substr($0, 3, length($0) - 5)
        while (getline > 0) {
            if (length($0) == 0) next
            chunk[name, ++count[name]] = $0 } }
    END { tangle("*", ""); printf "\n" }
    function tangle(name, prefix,    i, tag, suffix) {
        for (i = 1; i <= count[name]; i++) {
            if (i == 2) gsub(/[^ \t]/, " ", prefix)
            if (match(chunk[name,i], /<<.+>>/)) {
                tag = substr(chunk[name,i], RSTART + 2, RLENGTH - 4)
                if (tag in count) {
                    suffix = substr(chunk[name,i], RSTART + RLENGTH)
                    tangle(tag, prefix substr(chunk[name,i], 1, RSTART - 1))
                    printf "%s", suffix }
                else printf "%s%s", prefix, chunk[name,i] }
            else printf "%s%s", prefix, chunk[name,i]
            if (i < count[name]) printf "\n" } }

    (in Phil Bewig’s commentary on it)
    The essence of literate programming is rearranging chunks of code, and
    a dozen and a half lines of awk is all you need for that.
    
    Of course, with so little code it's not possible for everything to be
    perfect. … Even so, this microscopic system provides a useful tool
    that encompasses the essence of literate programming.

So it turns out it was 18 lines of awk, not 10.  To my surprise,
Handaxeweb has a couple extra features:
- it can extract chunks by different names;
- it can append to existing chunks.

)

"""
import sys, re

def main(outfile, infile, chunkname):
    chunks = parse(infile)
    outfile.write(expand(chunks, chunkname, ''))

def parse(infile):
    "Make a chunks table from infile, skipping any commentary."
    chunkname, chunks = '*', {}
    for line in infile:
        newchunk = re.match(r' {4,}\(in (.*)\)\s*$', line)
        if newchunk:
            chunkname = newchunk.group(1)
        elif re.match(r' {4}', line):
            chunks[chunkname] = chunks.get(chunkname, '') + line[4:]
    return chunks

def expand(chunks, chunkname, indent):
    """Return the named chunk with any chunk-references recursively
    expanded and with 'indent' prepended to every line."""
    raw = chunks.get(chunkname, '')
    output = re.sub(r'(?m)^(\s*)<<(.*)>>[ \t]*\n',
                    lambda mo: expand(chunks, mo.group(2), mo.group(1)),
                    raw)
    # (?=.) prevents adding an indent after the last newline in chunk
    return re.sub(r'(?m)^(?=.)', indent, output)

if __name__ == '__main__':
    chunkname = '*'
    if len(sys.argv) > 1: chunkname = sys.argv[1]
    main(sys.stdout, sys.stdin, chunkname)
