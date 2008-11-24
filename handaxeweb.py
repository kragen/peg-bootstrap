#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Handaxeweb: Minimal literate programming system.

Sometime in probably 1995, I saw a literate programming system in ten
lines or so of awk.  I can’t find it, so here’s my reconstruction in
Python.

"""
import sys, re
chunks = {}
def expand(chunkname, outfile):
    for line in re.split('(\n)', chunks.get(chunkname, '')):
        chunkmo = re.match(r'<<(.*)>>$', line)
        if chunkmo:
            expand(chunkmo.group(1), outfile)
        else:
            outfile.write(line)
def parse(infile):
    for line in infile:
        chunkmo = re.match(r'<<(.*)>>=$', line)
        if chunkmo:
            chunkname = chunkmo.group(1)
            for line in infile:
                if re.match(r'@$', line): break
                chunks[chunkname] = chunks.get(chunkname, '') + line
if __name__ == '__main__':
    if len(sys.argv) > 1:
        mainchunk = sys.argv[1]
    else:
        mainchunk = '*'
    parse(sys.stdin)
    expand(mainchunk, sys.stdout)
