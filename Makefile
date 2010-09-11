all: peg.md.html metacircular.peg bootstrap.js \
	crosscompiler.peg output.js crosscompiler.js
clean:
	rm peg.md.html metacircular.peg bootstrap.js \
		crosscompiler.peg crosscompiler.js

# FWIW note that mkhtml.py has its own Make-like mtime-comparison
# logic internally.
%.md.html: %.md mkhtml.py
	./mkhtml.py $<

metacircular.peg: peg.md handaxeweb.lua
	./handaxeweb.lua 'the metacircular compiler-compiler' < $< > $@

bootstrap.js: peg.md handaxeweb.lua
	./handaxeweb.lua 'the bunch-of-functions version' < $< > $@

output.js: metacircular.peg pegcompile.js bootstrap.js 
	./pegcompile.js < $< > $@

handaxeweb.lua: handaxeweb.md
	./build_handaxeweb

crosscompiler.peg: peg.md handaxeweb.lua
	./handaxeweb.lua 'the metacircular compiler-compiler' 2 < $< > $@

crosscompiler.js: crosscompiler.peg pegcompile.js bootstrap.js
	./pegcompile.js < $< > $@

