all: peg.md.html metacircular.peg bootstrap.js \
	crosscompiler.peg output.js crosscompiler.js stage3.js ichbins-sexp.json
clean:
	rm peg.md.html metacircular.peg bootstrap.js \
		crosscompiler.peg crosscompiler.js stage2.js stage3.js \
		ichbins-parser.peg ichbins-parser.js ichbins-sexp.json

# FWIW note that mkhtml.py has its own Make-like mtime-comparison
# logic internally.
%.md.html: %.md mkhtml.py
	./mkhtml.py $<

metacircular.peg: peg.md handaxeweb.lua
	./handaxeweb.lua 'the metacircular compiler-compiler' < $< > $@

bootstrap.js: peg.md handaxeweb.lua
	./handaxeweb.lua 'the bunch-of-functions version' < $< > $@

output.js: metacircular.peg pegcompile.js bootstrap.js 
	node ./pegcompile.js bootstrap.js < $< > $@

stage2.js: metacircular.peg pegcompile.js output.js
	node ./pegcompile.js output.js < $< > $@

# output.js is the grammar compiled into JS with the bootstrap.
# stage2.js is the grammar compiled into JS with a compiled copy of itself;
# most kinds of errors will tend to cause output.js to fail to run successfully,
# so stage2.js won’t be generated.
# However, some kinds of errors might manifest by generating an output parser
# that either doesn’t work at all or works incorrectly; and it is of course
# possible that output.js will differ from stage2.js in innocuous ways
# because they are the outputs of different prorams.
# So we generate a stage3.js using stage2.js: the grammar compiled into JS
# with a compiled version of itself that was itself compiled with itself.
# This should be byte-identical to stage2.js, or there is a bug.
# XXX this Makefile should go into peg.md!
stage3.js: metacircular.peg pegcompile.js stage2.js
	node ./pegcompile.js stage2.js < $< > $@
	diff -u stage2.js $@

handaxeweb.lua: handaxeweb.md
	./build_handaxeweb

crosscompiler.peg: peg.md handaxeweb.lua
	./handaxeweb.lua 'the metacircular compiler-compiler' 2 < $< > $@

crosscompiler.js: crosscompiler.peg pegcompile.js bootstrap.js
	node ./pegcompile.js bootstrap.js < $< > $@

ichbins-parser.peg: peg.md
	./handaxeweb.lua $@ < $< > $@

ichbins-parser.js: ichbins-parser.peg pegcompile.js stage3.js
	node ./pegcompile.js stage3.js < ichbins-parser.peg > $@

ichbins-sexp.json: ichbins-parser.js pegcompile.js ichbins-sexp
	node ./pegcompile.js ichbins-parser.js < ichbins-sexp > $@
